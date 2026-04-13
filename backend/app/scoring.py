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
    return dict(row) if row else None


# ── Raw DB data pull ──

async def get_exposure_data(onetsoc_code: str) -> dict:
    """Pull all exposure-related data for a SOC code from every relevant table."""
    from app.database import get_pool
    pool = get_pool()
    result: dict = {}

    # Eloundou occupation-level exposure (923 rows)
    try:
        row = await pool.fetchrow(
            "SELECT * FROM eloundou_exposure WHERE soc_code = $1",
            onetsoc_code,
        )
        result["eloundou"] = dict(row) if row else {}
    except Exception as e:
        logger.warning("eloundou_exposure query failed: %s", e)
        result["eloundou"] = {}

    # Felten AIOE score (756 rows)
    try:
        row = await pool.fetchrow(
            "SELECT * FROM aioe_scores WHERE soc_code = $1",
            onetsoc_code,
        )
        result["aioe"] = dict(row) if row else {}
    except Exception as e:
        logger.warning("aioe_scores query failed: %s", e)
        result["aioe"] = {}

    # O*NET tasks with importance ratings
    try:
        rows = await pool.fetch(
            """
            SELECT t.task_id,
                   t.task_statement,
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
    except Exception as e:
        logger.warning("onet_tasks query failed: %s", e)
        result["tasks"] = []

    # AIOE task-level penetration scores (17 998 rows)
    try:
        rows = await pool.fetch(
            "SELECT * FROM aioe_task_penetration WHERE soc_code = $1 LIMIT 200",
            onetsoc_code,
        )
        result["aioe_tasks"] = [dict(r) for r in rows]
    except Exception as e:
        logger.warning("aioe_task_penetration query failed: %s", e)
        result["aioe_tasks"] = []

    # BLS national occupational employment + wages
    try:
        bls_code = onetsoc_code.split(".")[0]   # "15-1252.00" → "15-1252"
        row = await pool.fetchrow(
            """
            SELECT * FROM bls_occupations
            WHERE occ_code = $1 OR occ_code = $2
            LIMIT 1
            """,
            bls_code, onetsoc_code,
        )
        result["bls_national"] = dict(row) if row else {}
    except Exception as e:
        logger.warning("bls_occupations query failed: %s", e)
        result["bls_national"] = {}

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

    # ── Eloundou: score = α + 0.5β  (Eloundou et al. 2023) ──
    alpha = _pick(eloundou,
                  ["human_alpha", "alpha", "ep_alpha", "gpt4_alpha",
                   "computerized_alpha", "exposed_alpha"], None)
    beta  = _pick(eloundou,
                  ["human_beta",  "beta",  "ep_beta",  "gpt4_beta",
                   "computerized_beta",  "exposed_beta"], None)

    if alpha is not None and beta is not None:
        eloundou_score = min(1.0, alpha + 0.5 * beta)
    elif alpha is not None:
        eloundou_score = min(1.0, alpha)
    else:
        # Fall back to any available exposure column
        raw = _pick(eloundou,
                    ["exposure", "score", "exposure_score", "ai_exposure",
                     "computerized", "exposed"], None)
        eloundou_score = min(1.0, raw) if raw is not None else 0.50

    eloundou_available = bool(eloundou)

    # ── AIOE: z-score ≈ −2 … +3, normalise to 0–1 ──
    aioe_raw = _pick(aioe,
                     ["aioe", "aioe_score", "score", "normalized_aioe",
                      "ai_occupational_exposure", "total_aioe"], None)
    if aioe_raw is not None:
        aioe_normalized = max(0.0, min(1.0, (aioe_raw + 2.0) / 5.0))
    else:
        aioe_normalized = eloundou_score   # graceful fallback

    aioe_available = bool(aioe)

    # ── Task-weighted exposure (O*NET importance × AIOE task penetration) ──
    task_exposure = _compute_task_weighted(tasks, aioe_tasks)

    # ── Triangulate ──
    if task_exposure is not None and eloundou_available and aioe_available:
        base = 0.40 * eloundou_score + 0.30 * aioe_normalized + 0.30 * task_exposure
    elif eloundou_available and aioe_available:
        base = 0.55 * eloundou_score + 0.45 * aioe_normalized
    elif eloundou_available:
        base = eloundou_score
    elif aioe_available:
        base = aioe_normalized
    else:
        base = _heuristic_base(user_tasks)

    # ── Context modifiers ──
    size_mod = {
        "1-50":    -0.02,   # Startup: slower, leaner adoption
        "50-500":   0.00,   # Mid: neutral
        "500-5000": +0.04,  # Enterprise: faster budget cycles
        "5000+":    +0.07,  # Large Corp: fastest adoption
    }.get(company_size, 0.0)

    # High AI usage → field already transforming (small positive push)
    ai_mod = (ai_usage - 50) / 1000.0   # −0.05 … +0.05

    final = max(0.02, min(0.97, base + size_mod + ai_mod))

    # ── Years & risk ──
    years_raw = 30.0 * ((1.0 - final) ** 1.5)
    years = max(1, min(30, round(years_raw)))
    risk = (
        "critical" if years <= 5
        else "high"     if years <= 10
        else "moderate" if years <= 18
        else "low"
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

    # ── BLS employment data ──
    tot_emp      = _pick(bls,
                         ["tot_emp", "total_employment", "employment",
                          "employees", "emp_total"], None)
    median_wage  = _pick(bls,
                         ["a_median", "annual_median", "median_annual_wage",
                          "a_mean", "annual_mean_wage", "avg_annual_wage"], None)

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
            "eloundou_score":             round(eloundou_score, 3),
            "eloundou_available":         eloundou_available,
            "aioe_raw":                   round(aioe_raw, 3) if aioe_raw is not None else None,
            "aioe_normalized":            round(aioe_normalized, 3),
            "aioe_available":             aioe_available,
            "task_exposure":              round(task_exposure, 3) if task_exposure is not None else None,
            "tasks_analyzed":             len(tasks),
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

    total_imp = 0.0
    weighted  = 0.0
    for task in tasks:
        imp = float(task.get("importance", 3.0))
        tid = str(task.get("task_id", ""))
        exp = pen_by_task.get(tid, 0.60 if task.get("task_type", "Core") == "Core" else 0.40)
        total_imp += imp
        weighted  += imp * exp

    return (weighted / total_imp) if total_imp > 0 else None


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
        if any(kw in t.get("task_statement", "").lower() for kw in physical_kw)
    )
    ratio = hits / len(tasks)
    return max(5, min(90, round(ratio * 130 + 10)))


def _heuristic_base(user_tasks: list[str]) -> float:
    """Rough fallback when no DB data is available at all."""
    HIGH = {"coding", "data analysis", "writing", "documentation",
            "research", "data entry", "translation", "bookkeeping"}
    LOW  = {"physical", "hands-on", "managing people", "client calls",
            "creative design", "sales", "teaching", "training"}
    if not user_tasks:
        return 0.45
    n   = len(user_tasks)
    hi  = sum(1 for t in user_tasks if any(h in t.lower() for h in HIGH))
    lo  = sum(1 for t in user_tasks if any(l in t.lower() for l in LOW))
    return max(0.15, min(0.85, 0.45 + hi / n * 0.30 - lo / n * 0.20))
