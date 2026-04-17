"""
Deterministic exposure scoring using O*NET, Eloundou, AIOE, and BLS database tables.
No LLM calls — pure SQL + arithmetic.

Triangulation formula:
  base = 0.40 × eloundou_score + 0.30 × aioe_normalized + 0.30 × task_exposure
  final = base + company_modifier + ai_usage_modifier
  years = round(30 × (1 − final)^1.5)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Column-value extractor ──

def _pick(row: dict, keys: list[str], default=None):
    """Return the first matching key's value as float, or default."""
    for k in keys:
        v = row.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return default


# ── Occupation matching ──

async def match_occupation(role: str) -> Optional[dict]:
    """
    Fuzzy-match a free-text job title against onet_occupations.
    Returns {onetsoc_code, title, description} or None.
    """
    from app.database import get_pool
    pool = get_pool()
    role_lower = role.lower().strip()
    words = [w for w in role_lower.split() if len(w) > 2]
    broad = words[0] if words else role_lower

    logger.info("[MATCH_OCCUPATION] Input role=%r  →  role_lower=%r  broad=%r", role, role_lower, broad)

    row = await pool.fetchrow(
        """
        SELECT soc_code, title, description,
               CASE
                   WHEN LOWER(title) = $1                   THEN 100
                   WHEN LOWER(title) LIKE '%' || $1 || '%'  THEN 80
                   WHEN $1 LIKE '%' || LOWER(title) || '%'  THEN 70
                   WHEN LOWER(title) LIKE '%' || $2 || '%'  THEN 50
                   ELSE 10
               END AS _score
        FROM onet_occupations
        WHERE LOWER(title) = $1
           OR LOWER(title) LIKE '%' || $1 || '%'
           OR $1 LIKE '%' || LOWER(title) || '%'
           OR LOWER(title) LIKE '%' || $2 || '%'
        ORDER BY _score DESC, LENGTH(title) ASC
        LIMIT 1
        """,
        role_lower, broad,
    )

    if row:
        result = dict(row)
        logger.info(
            "[MATCH_OCCUPATION] HIT  soc_code=%r  title=%r  match_score=%s",
            result.get("soc_code"), result.get("title"), result.get("_score"),
        )
        return result
    else:
        logger.warning("[MATCH_OCCUPATION] MISS — no occupation matched for role=%r", role)
        return None


# ── Raw DB data pull ──

async def get_exposure_data(onetsoc_code: str) -> dict:
    """Pull all exposure-related data for a SOC code from every relevant table."""
    from app.database import get_pool
    pool = get_pool()
    result: dict = {}

    logger.info("[GET_EXPOSURE_DATA] Pulling data for soc_code=%r", onetsoc_code)

    # Eloundou occupation-level exposure (923 rows)
    try:
        row = await pool.fetchrow(
            "SELECT * FROM eloundou_exposure WHERE soc_code = $1",
            onetsoc_code,
        )
        result["eloundou"] = dict(row) if row else {}
        if row:
            logger.info("[DB] eloundou_exposure HIT  columns=%s  values=%s",
                        list(result["eloundou"].keys()), list(result["eloundou"].values()))
        else:
            logger.warning("[DB] eloundou_exposure MISS — no row for soc_code=%r", onetsoc_code)
    except Exception as e:
        logger.warning("eloundou_exposure query failed: %s", e)
        result["eloundou"] = {}

    # Felten AIOE score (756 rows)
    # aioe_scores uses short SOC codes like "15-1252", not "15-1252.00"
    try:
        aioe_code = onetsoc_code.split(".")[0]   # "15-1252.00" → "15-1252"
        logger.info("[DB] aioe_scores querying soc_code=%r  (also trying short=%r)", onetsoc_code, aioe_code)
        row = await pool.fetchrow(
            "SELECT * FROM aioe_scores WHERE soc_code = $1 OR soc_code = $2",
            onetsoc_code, aioe_code,
        )
        result["aioe"] = dict(row) if row else {}
        if row:
            logger.info("[DB] aioe_scores HIT  columns=%s  values=%s",
                        list(result["aioe"].keys()), list(result["aioe"].values()))
        else:
            logger.warning("[DB] aioe_scores MISS — no row for soc_code=%r / %r", onetsoc_code, aioe_code)
    except Exception as e:
        logger.warning("aioe_scores query failed: %s", e)
        result["aioe"] = {}

    # O*NET tasks with importance ratings
    try:
        rows = await pool.fetch(
            """
            SELECT t.task_id,
                   t.task,
                   COALESCE(t.task_type, 'Core') AS task_type,
                   COALESCE(r.data_value, 3.0)   AS importance
            FROM onet_tasks t
            LEFT JOIN onet_task_ratings r
                ON  t.soc_code = r.soc_code
                AND t.task_id      = r.task_id
                AND r.scale_id     = 'IM'
            WHERE t.soc_code = $1
            ORDER BY r.data_value DESC NULLS LAST
            """,
            onetsoc_code,
        )
        result["tasks"] = [dict(r) for r in rows]
        logger.info("[DB] onet_tasks: %d task(s) returned for soc_code=%r", len(result["tasks"]), onetsoc_code)
        if result["tasks"]:
            logger.info("[DB] onet_tasks sample (top 3): %s",
                        [{k: t[k] for k in ("task_id", "task_type", "importance")} for t in result["tasks"][:3]])
    except Exception as e:
        logger.warning("onet_tasks query failed: %s", e)
        result["tasks"] = []

    # AIOE task-level penetration scores — joined by task text (no soc_code column)
    try:
        rows = await pool.fetch(
            """
            SELECT ot.task_id, atp.penetration
            FROM onet_tasks ot
            JOIN aioe_task_penetration atp
                ON LOWER(TRIM(atp.task)) = LOWER(TRIM(ot.task))
            WHERE ot.soc_code = $1
            """,
            onetsoc_code,
        )
        result["aioe_tasks"] = [dict(r) for r in rows]
        logger.info("[DB] aioe_task_penetration: %d task penetration row(s) matched for soc_code=%r",
                    len(result["aioe_tasks"]), onetsoc_code)
        if result["aioe_tasks"]:
            logger.info("[DB] aioe_task_penetration sample (top 3): %s", result["aioe_tasks"][:3])
    except Exception as e:
        logger.warning("aioe_task_penetration query failed: %s", e)
        result["aioe_tasks"] = []

    # BLS national occupational employment + wages
    try:
        bls_code = onetsoc_code.split(".")[0]   # "15-1252.00" → "15-1252"
        logger.info("[DB] bls_occupations querying occupation_code=%r / %r", bls_code, onetsoc_code)
        row = await pool.fetchrow(
            """
            SELECT * FROM bls_occupations
            WHERE occupation_code = $1 OR occupation_code = $2
            LIMIT 1
            """,
            bls_code, onetsoc_code,
        )
        result["bls_national"] = dict(row) if row else {}
        if row:
            logger.info("[DB] bls_occupations HIT  columns=%s  values=%s",
                        list(result["bls_national"].keys()), list(result["bls_national"].values()))
        else:
            logger.warning("[DB] bls_occupations MISS — no row for %r / %r", bls_code, onetsoc_code)
    except Exception as e:
        logger.warning("bls_occupations query failed: %s", e)
        result["bls_national"] = {}

    logger.info("[GET_EXPOSURE_DATA] Done — eloundou=%s  aioe=%s  tasks=%d  aioe_tasks=%d  bls=%s",
                bool(result["eloundou"]), bool(result["aioe"]),
                len(result["tasks"]), len(result["aioe_tasks"]),
                bool(result["bls_national"]))
    return result


# ── Deterministic score computation ──

def compute_scores(
    exposure_data: dict,
    user_tasks: list[str],
    company_size: str,
    ai_usage: int,
) -> dict:
    """
    Compute all exposure scores from DB data + user context.
    Returns a dict that slots directly into the EstimateResponse
    (everything except description and tips, which the LLM generates).
    """
    eloundou   = exposure_data.get("eloundou", {})
    aioe       = exposure_data.get("aioe", {})
    tasks      = exposure_data.get("tasks", [])
    aioe_tasks = exposure_data.get("aioe_tasks", [])
    bls        = exposure_data.get("bls_national", {})

    logger.info(
        "[COMPUTE_SCORES] Inputs — company_size=%r  ai_usage=%d  "
        "user_tasks=%s  db_tasks=%d  eloundou_cols=%s  aioe_cols=%s",
        company_size, ai_usage, user_tasks,
        len(tasks), list(eloundou.keys()), list(aioe.keys()),
    )

    # ── Eloundou: score = α + 0.5β  (Eloundou et al. 2023) ──
    # Real DB columns: human_rating_alpha/beta, dv_rating_alpha/beta
    alpha = _pick(eloundou,
                  ["human_rating_alpha", "dv_rating_alpha",
                   "human_alpha", "alpha", "ep_alpha", "gpt4_alpha",
                   "computerized_alpha", "exposed_alpha"], None)
    beta  = _pick(eloundou,
                  ["human_rating_beta", "dv_rating_beta",
                   "human_beta",  "beta",  "ep_beta",  "gpt4_beta",
                   "computerized_beta",  "exposed_beta"], None)

    logger.info("[ELOUNDOU] Raw values — alpha=%s  beta=%s", alpha, beta)

    gamma = _pick(eloundou,
                  ["dv_rating_gamma", "human_rating_gamma",
                   "gamma", "ep_gamma", "gpt4_gamma"], None)
    logger.info("[ELOUNDOU] Raw values — alpha=%s  beta=%s  gamma=%s", alpha, beta, gamma)

    if alpha is not None and beta is not None:
        eloundou_score = min(1.0, alpha + 0.5 * beta)
        logger.info("[ELOUNDOU] Formula: alpha(%.3f) + 0.5 × beta(%.3f) = %.3f  (capped at 1.0 → %.3f)",
                    alpha, beta, alpha + 0.5 * beta, eloundou_score)
    elif alpha is not None:
        eloundou_score = min(1.0, alpha)
        logger.info("[ELOUNDOU] Only alpha available — eloundou_score = %.3f", eloundou_score)
    else:
        # Fall back to any available exposure column
        raw = _pick(eloundou,
                    ["exposure", "score", "exposure_score", "ai_exposure",
                     "computerized", "exposed"], None)
        eloundou_score = min(1.0, raw) if raw is not None else 0.50
        logger.info("[ELOUNDOU] No alpha/beta — fallback raw=%s  eloundou_score=%.3f",
                    raw, eloundou_score)

    eloundou_available = bool(eloundou)

    # ── AIOE: z-score ≈ −2 … +3, normalise to 0–1 ──
    # Real DB column: observed_exposure (from job_exposure.csv)
    aioe_raw = _pick(aioe,
                     ["observed_exposure", "aioe", "aioe_score", "score",
                      "normalized_aioe", "ai_occupational_exposure", "total_aioe"], None)
    if aioe_raw is not None:
        aioe_normalized = max(0.0, min(1.0, (aioe_raw + 2.0) / 5.0))
        logger.info("[AIOE] Raw z-score=%.3f  formula: (%.3f + 2.0) / 5.0 = %.3f  (clamped 0–1 → %.3f)",
                    aioe_raw, aioe_raw, (aioe_raw + 2.0) / 5.0, aioe_normalized)
    else:
        aioe_normalized = eloundou_score   # graceful fallback
        logger.warning("[AIOE] No raw score found — falling back to eloundou_score=%.3f", aioe_normalized)

    aioe_available = bool(aioe)

    # ── Task-weighted exposure (O*NET importance × AIOE task penetration) ──
    task_exposure = _compute_task_weighted(tasks, aioe_tasks)
    logger.info("[TASK_EXPOSURE] task_exposure=%s", f"{task_exposure:.3f}" if task_exposure is not None else "None (no tasks)")

    # ── Triangulate ──
    if task_exposure is not None and eloundou_available and aioe_available:
        base = 0.40 * eloundou_score + 0.30 * aioe_normalized + 0.30 * task_exposure
        logger.info(
            "[BASE] All 3 sources available — "
            "0.40 × eloundou(%.3f) + 0.30 × aioe(%.3f) + 0.30 × task(%.3f) = %.3f",
            eloundou_score, aioe_normalized, task_exposure, base,
        )
    elif eloundou_available and aioe_available:
        base = 0.55 * eloundou_score + 0.45 * aioe_normalized
        logger.info(
            "[BASE] No task_exposure — "
            "0.55 × eloundou(%.3f) + 0.45 × aioe(%.3f) = %.3f",
            eloundou_score, aioe_normalized, base,
        )
    elif eloundou_available:
        base = eloundou_score
        logger.info("[BASE] Only eloundou available — base=%.3f", base)
    elif aioe_available:
        base = aioe_normalized
        logger.info("[BASE] Only aioe available — base=%.3f", base)
    else:
        base = _heuristic_base(user_tasks)
        logger.warning("[BASE] No DB data at all — heuristic from user_tasks → base=%.3f", base)

    # ── Context modifiers ──
    size_mod = {
        "1-50":    -0.02,   # Startup: slower, leaner adoption
        "50-500":   0.00,   # Mid: neutral
        "500-5000": +0.04,  # Enterprise: faster budget cycles
        "5000+":    +0.07,  # Large Corp: fastest adoption
    }.get(company_size, 0.0)

    # High AI usage → field already transforming (small positive push)
    ai_mod = (ai_usage - 50) / 1000.0   # −0.05 … +0.05

    logger.info(
        "[MODIFIERS] company_size=%r → size_mod=%+.3f | ai_usage=%d → ai_mod=%+.3f",
        company_size, size_mod, ai_usage, ai_mod,
    )

    final = max(0.02, min(0.97, base + size_mod + ai_mod))
    logger.info(
        "[FINAL] base(%.3f) + size_mod(%+.3f) + ai_mod(%+.3f) = %.3f  (clamped 0.02–0.97 → %.3f)",
        base, size_mod, ai_mod, base + size_mod + ai_mod, final,
    )

    # ── Years & risk ──
    years_raw = 30.0 * ((1.0 - final) ** 1.5)
    years = max(1, min(30, round(years_raw)))
    risk = (
        "critical" if years <= 5
        else "high"     if years <= 10
        else "moderate" if years <= 18
        else "low"
    )
    logger.info(
        "[YEARS] 30 × (1 − %.3f)^1.5 = %.2f  → rounded=%d  clamped(1–30)=%d  risk=%r",
        final, years_raw, round(years_raw), years, risk,
    )

    # ── Factor scores (0–100) ──
    repeatability = min(100, max(5,  round(final * 105)))
    creative      = min(100, max(10, round((1.0 - eloundou_score) * 85 + 10)))
    physical      = _score_physical_presence(tasks)
    emotional     = min(100, max(10, round((1.0 - final) * 70 + 15)))
    regulatory    = (
        min(90, max(10, round((2.5 - aioe_raw) / 5.0 * 80 + 10)))
        if aioe_raw is not None
        else (30 if final > 0.6 else 55)
    )
    logger.info(
        "[FACTORS] repeatability=%d  creative=%d  physical=%d  emotional=%d  regulatory=%d",
        repeatability, creative, physical, emotional, regulatory,
    )

    # ── BLS employment data ──
    tot_emp      = _pick(bls,
                         ["tot_emp", "total_employment", "employment",
                          "employees", "emp_total"], None)
    median_wage  = _pick(bls,
                         ["a_median", "annual_median", "median_annual_wage",
                          "a_mean", "annual_mean_wage", "avg_annual_wage"], None)
    logger.info("[BLS] tot_emp=%s  median_wage=%s", tot_emp, median_wage)

    logger.info(
        "[COMPUTE_SCORES] RESULT — years=%d  risk=%r  final_exposure=%.3f  "
        "eloundou=%.3f  aioe_norm=%.3f  task_exp=%s",
        years, risk, final, eloundou_score, aioe_normalized,
        f"{task_exposure:.3f}" if task_exposure is not None else "N/A",
    )

    # Top O*NET tasks by importance for display
    matched_tasks = [t["task"] for t in tasks[:6] if t.get("task")]

    return {
        "years": years,
        "risk":  risk,
        "factors": [
            {"name": "Task Repeatability",       "value": repeatability},
            {"name": "Creative Thinking Required","value": creative},
            {"name": "Physical Presence Needed",  "value": physical},
            {"name": "Emotional Intelligence",    "value": emotional},
            {"name": "Regulatory Protection",     "value": regulatory},
        ],
        "data_sources": {
            "eloundou_alpha":             round(alpha, 3) if alpha is not None else None,
            "eloundou_beta":              round(beta,  3) if beta  is not None else None,
            "eloundou_gamma":             round(gamma, 3) if gamma is not None else None,
            "eloundou_score":             round(eloundou_score, 3),
            "eloundou_available":         eloundou_available,
            "aioe_raw":                   round(aioe_raw, 3) if aioe_raw is not None else None,
            "aioe_normalized":            round(aioe_normalized, 3),
            "aioe_available":             aioe_available,
            "task_exposure":              round(task_exposure, 3) if task_exposure is not None else None,
            "tasks_analyzed":             len(tasks),
            "matched_tasks":              matched_tasks,
            "company_modifier":           round(size_mod, 3),
            "ai_usage_modifier":          round(ai_mod,   3),
            "bls_employment_national":    int(tot_emp)     if tot_emp     is not None else None,
            "bls_median_wage_national":   int(median_wage) if median_wage is not None else None,
            "final_exposure":             round(final, 3),
        },
    }


# ── Helpers ──

def _compute_task_weighted(
    tasks: list[dict], aioe_tasks: list[dict]
) -> Optional[float]:
    """
    Importance-weighted task exposure.
    Uses aioe_task_penetration scores when available;
    falls back to Core=0.60 / Supplemental=0.40 heuristic.
    """
    if not tasks:
        logger.info("[TASK_WEIGHTED] No tasks — returning None")
        return None

    pen_by_task: dict[str, float] = {}
    for at in aioe_tasks:
        tid = at.get("task_id")
        if tid is not None:
            score = _pick(
                at,
                ["penetration", "aioe_penetration", "score",
                 "exposure", "task_score", "task_penetration"],
                None,
            )
            if score is not None:
                pen_by_task[str(tid)] = score

    logger.info(
        "[TASK_WEIGHTED] %d task(s) from onet | %d aioe penetration match(es) | "
        "unmatched tasks will use Core=0.60 / Supplemental=0.40 heuristic",
        len(tasks), len(pen_by_task),
    )

    total_imp = 0.0
    weighted  = 0.0
    for task in tasks:
        imp = float(task.get("importance", 3.0))
        tid = str(task.get("task_id", ""))
        exp = pen_by_task.get(tid, 0.60 if task.get("task_type", "Core") == "Core" else 0.40)
        source = "aioe_db" if tid in pen_by_task else "heuristic"
        logger.debug(
            "[TASK_WEIGHTED] task_id=%s  type=%s  importance=%.1f  exposure=%.3f  source=%s",
            tid, task.get("task_type", "Core"), imp, exp, source,
        )
        total_imp += imp
        weighted  += imp * exp

    result = (weighted / total_imp) if total_imp > 0 else None
    logger.info(
        "[TASK_WEIGHTED] total_importance=%.2f  weighted_sum=%.3f  task_exposure=%s",
        total_imp, weighted, f"{result:.3f}" if result is not None else "None",
    )
    return result


def _score_physical_presence(tasks: list[dict]) -> int:
    """Estimate physical-presence score from O*NET task text keywords."""
    if not tasks:
        return 25
    physical_kw = [
        "hands-on", "physical", "repair", "install", "maintain equipment",
        "operate machine", "on-site", "site visit", "physical inspection",
        "lift", "assemble", "weld", "drive", "handle material", "manual",
        "field work", "outdoor", "construction",
    ]
    hits = sum(
        1 for t in tasks
        if any(kw in t.get("task", "").lower() for kw in physical_kw)
    )
    ratio = hits / len(tasks)
    score = max(5, min(90, round(ratio * 130 + 10)))
    logger.info("[PHYSICAL] %d/%d tasks matched physical keywords → ratio=%.2f  score=%d",
                hits, len(tasks), ratio, score)
    return score


def _heuristic_base(user_tasks: list[str]) -> float:
    """Rough fallback when no DB data is available at all."""
    HIGH = {"coding", "data analysis", "writing", "documentation",
            "research", "data entry", "translation", "bookkeeping"}
    LOW  = {"physical", "hands-on", "managing people", "client calls",
            "creative design", "sales", "teaching", "training"}
    if not user_tasks:
        logger.warning("[HEURISTIC] No user_tasks provided — returning default 0.45")
        return 0.45
    n   = len(user_tasks)
    hi  = sum(1 for t in user_tasks if any(h in t.lower() for h in HIGH))
    lo  = sum(1 for t in user_tasks if any(l in t.lower() for l in LOW))
    result = max(0.15, min(0.85, 0.45 + hi / n * 0.30 - lo / n * 0.20))
    logger.info(
        "[HEURISTIC] n=%d  high_matches=%d  low_matches=%d  "
        "0.45 + (%.0f/%.0f)×0.30 − (%.0f/%.0f)×0.20 = %.3f",
        n, hi, lo, hi, n, lo, n, result,
    )
    return result
