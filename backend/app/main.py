"""FastAPI application for AI Job Countdown."""

import json
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app import cache
from app import database
from app import scoring
from app.ai_router import (
    get_estimate,
    get_feed,
    get_role_suggestions,
    get_city_suggestions,
    get_task_suggestions,
)
from app.models import (
    CitySuggestionsRequest,
    CitySuggestionsResponse,
    EstimateRequest,
    EstimateResponse,
    FeedItem,
    FeedRequest,
    FeedResponse,
    GeoResponse,
    OccupationMatch,
    RoleSuggestionsRequest,
    RoleSuggestionsResponse,
    TaskSuggestionsRequest,
    TaskSuggestionsResponse,
)

DEBUG = os.getenv("DEBUG", "0") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_pool()
    yield
    await database.close_pool()

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

if DEBUG:
    logger.debug("🐛 Debug mode enabled")

app = FastAPI(
    title="AI Job Countdown API",
    description="Estimates when AI will significantly disrupt a given job role.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Cache key helpers ──

def _estimate_cache_key(req: EstimateRequest) -> str:
    data = {
        "role": req.role.lower().strip(),
        "location": req.location.lower().strip(),
        "company_size": req.company_size,
        "tasks": sorted(t.lower() for t in req.tasks),
        "ai_usage": req.ai_usage,
    }
    return cache.make_key("estimate", json.dumps(data, sort_keys=True))


def _feed_cache_key(req: FeedRequest) -> str:
    tasks_key = "|".join(sorted(t.lower() for t in req.tasks))
    data = {
        "role": req.role.lower().strip(),
        "location": req.location.lower().strip(),
        "company_size": req.company_size,
        "tasks": tasks_key,
    }
    return cache.make_key("feed", json.dumps(data, sort_keys=True))


# ── Geo helper ──

async def _detect_geo(ip: str) -> dict:
    """Call ip-api.com to get city/region/country for an IP address.
    NOTE: X-Forwarded-For is client-spoofable; acceptable for this consumer app.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,city,regionName,country"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                return {"city": "", "region": "", "country": ""}
            return {
                "city": data.get("city", ""),
                "region": data.get("regionName", ""),
                "country": data.get("country", ""),
            }
    except Exception:
        return {"city": "", "region": "", "country": ""}


# ── Health check ──

@app.get("/health")
async def health():
    db_status = "unavailable"
    try:
        pool = database.get_pool()
        await pool.fetchval("SELECT 1")
        db_status = "ok"
    except Exception:
        pass
    return {"status": "ok", "db": db_status}


# ── Geo endpoint ──

@app.get("/api/geo", response_model=GeoResponse)
async def geo(request: Request):
    """Detect the client's city/region from their IP address."""
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else ""
    )
    if DEBUG:
        logger.debug("GET /api/geo  ip=%s", ip)

    cache_key = cache.make_key("geo", ip)

    async def compute():
        return await _detect_geo(ip)

    data = await cache.get_or_compute(cache_key, compute, ttl_seconds=3600)
    if DEBUG:
        logger.debug("GET /api/geo  → %s", data)
    return GeoResponse(**data)


# ── Role suggestions endpoint ──

@app.post("/api/role-suggestions", response_model=RoleSuggestionsResponse)
async def role_suggestions(req: RoleSuggestionsRequest):
    """Return 6 job role pills for the user's city/region."""
    if DEBUG:
        logger.debug("POST /api/role-suggestions  city=%r region=%r", req.city, req.region)
    cache_key = cache.make_key("roles", req.city, req.region)

    async def compute():
        roles = await get_role_suggestions(req.city, req.region)
        return {"roles": roles}

    try:
        data = await cache.get_or_compute(cache_key, compute, ttl_seconds=86400)
        if DEBUG:
            logger.debug("POST /api/role-suggestions  → %s", data)
        return RoleSuggestionsResponse(**data)
    except Exception as e:
        logger.error("Role suggestions error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate suggestions")


# ── City suggestions endpoint ──

@app.post("/api/city-suggestions", response_model=CitySuggestionsResponse)
async def city_suggestions(req: CitySuggestionsRequest):
    """Return 6 city pills for the user's region."""
    if DEBUG:
        logger.debug("POST /api/city-suggestions  city=%r region=%r", req.city, req.region)
    cache_key = cache.make_key("cities", req.city, req.region)

    async def compute():
        cities = await get_city_suggestions(req.city, req.region)
        return {"cities": cities}

    try:
        data = await cache.get_or_compute(cache_key, compute, ttl_seconds=86400)
        if DEBUG:
            logger.debug("POST /api/city-suggestions  → %s", data)
        return CitySuggestionsResponse(**data)
    except Exception as e:
        logger.error("City suggestions error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate suggestions")


# ── Task suggestions endpoint ──

@app.post("/api/task-suggestions", response_model=TaskSuggestionsResponse)
async def task_suggestions(req: TaskSuggestionsRequest):
    """Return 10 task pill suggestions for a role + company size."""
    if DEBUG:
        logger.debug("POST /api/task-suggestions  role=%r size=%r", req.role, req.company_size)
    cache_key = cache.make_key("tasks", req.role.lower(), req.company_size)

    async def compute():
        tasks = await get_task_suggestions(req.role, req.company_size)
        return {"tasks": tasks}

    try:
        data = await cache.get_or_compute(cache_key, compute, ttl_seconds=86400)
        if DEBUG:
            logger.debug("POST /api/task-suggestions  → %s", data)
        return TaskSuggestionsResponse(**data)
    except Exception as e:
        logger.error("Task suggestions error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate suggestions")


# ── Estimate endpoint (with caching) ──

@app.post("/api/estimate", response_model=EstimateResponse)
async def estimate(req: EstimateRequest):
    """Generate an AI disruption estimate for a given job profile."""
    if DEBUG:
        logger.debug(
            "POST /api/estimate  role=%r location=%r size=%r tasks=%s ai=%s%%",
            req.role, req.location, req.company_size, req.tasks, req.ai_usage,
        )
    cache_key = _estimate_cache_key(req)

    async def compute():
        # ── Step 1: deterministic DB scoring ──
        db_computed = None
        try:
            database.get_pool()  # raises RuntimeError if DB not ready
            occ = await scoring.match_occupation(req.role)
            if occ:
                exp_data = await scoring.get_exposure_data(occ["onetsoc_code"])
                scores = scoring.compute_scores(
                    exp_data, req.tasks, req.company_size, req.ai_usage
                )
                db_computed = {
                    "occupation": {
                        "soc_code": occ["onetsoc_code"],
                        "title":    occ["title"],
                        "matched":  True,
                    },
                    **scores,
                }
                if DEBUG:
                    logger.debug(
                        "DB scoring succeeded: soc=%s exposure=%.3f years=%d",
                        occ["onetsoc_code"],
                        scores["data_sources"]["final_exposure"],
                        scores["years"],
                    )
            else:
                logger.info("No SOC match found for role=%r — using LLM fallback", req.role)
        except RuntimeError:
            logger.info("DB pool unavailable — using LLM-only scoring")
        except Exception as e:
            logger.warning("DB scoring failed (%s: %s) — falling back to LLM", type(e).__name__, e)

        # ── Step 2: single LLM call ──
        return await get_estimate(
            role=req.role,
            location=req.location,
            company_size=req.company_size,
            company_name=req.company_name,
            tasks=req.tasks,
            ai_usage=req.ai_usage,
            computed_scores=db_computed,
        )

    try:
        result = await cache.get_or_compute(cache_key, compute, ttl_seconds=3600)
        logger.info("Estimate response: %s", json.dumps(result, default=str))
        return EstimateResponse(**result)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude estimate response: %s", e)
        raise HTTPException(status_code=502, detail="Failed to parse AI response")
    except Exception as e:
        logger.error("Estimate endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Feed endpoint (with caching) ──

@app.post("/api/feed", response_model=FeedResponse)
async def feed(req: FeedRequest):
    """Fetch related news, social posts, and research about AI impact on a role."""
    if DEBUG:
        logger.debug("POST /api/feed  role=%r location=%r tasks=%s", req.role, req.location, req.tasks)
    cache_key = _feed_cache_key(req)

    async def compute():
        items_raw = await get_feed(
            role=req.role,
            location=req.location,
            company_size=req.company_size,
            tasks=req.tasks,
        )
        return items_raw

    try:
        items_raw = await cache.get_or_compute(cache_key, compute, ttl_seconds=3600)
        logger.info("Feed response: %s", json.dumps(items_raw))
        if DEBUG:
            logger.debug("POST /api/feed  → %d items", len(items_raw))
        items = [FeedItem(**item) for item in items_raw]
        return FeedResponse(items=items)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Claude feed response: %s", e)
        raise HTTPException(status_code=502, detail="Failed to parse AI response")
    except Exception as e:
        logger.error("Feed endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
