"""BrandGuard FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from brandguard.service import BrandService

logger = logging.getLogger(__name__)

_service: BrandService | None = None

ZUULTIMATE_BASE_URL = os.environ.get("ZUULTIMATE_BASE_URL", "http://localhost:8000")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service
    _service = BrandService()
    logger.info("BrandGuard started")
    yield
    logger.info("BrandGuard shutting down")


app = FastAPI(title="BrandGuard", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── Auth dependency ────────────────────────────────────────────────────────────

async def get_tenant(request: Request) -> dict:
    """Validate bearer token against Zuultimate and return tenant context."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth[7:]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{ZUULTIMATE_BASE_URL}/v1/identity/auth/validate",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError as e:
        logger.error("Zuultimate unreachable: %s", e)
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired credentials")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Auth service error")

    return resp.json()


def require_entitlement(entitlement: str):
    """Dependency factory: blocks if tenant lacks the required entitlement."""
    async def _check(tenant: dict = Depends(get_tenant)) -> dict:
        if entitlement not in tenant.get("entitlements", []):
            raise HTTPException(
                status_code=403,
                detail=f"Your plan does not include '{entitlement}'. Upgrade to access this feature.",
            )
        return tenant
    return _check


def _svc() -> BrandService:
    if _service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _service


# ── Models ─────────────────────────────────────────────────────────────────────

class CreateIdentityRequest(BaseModel):
    name: str
    tagline: Optional[str] = None
    mission: Optional[str] = None
    primary_tone: str = "professional"
    voice_attributes: Optional[list[str]] = None
    primary_color: Optional[str] = None
    primary_font: Optional[str] = None


class UpdateVoiceRequest(BaseModel):
    tagline: Optional[str] = None
    mission: Optional[str] = None
    primary_tone: Optional[str] = None
    preferred_words: Optional[list[str]] = None
    avoided_words: Optional[list[str]] = None


class AddGuidelineRequest(BaseModel):
    category: str
    title: str
    description: str
    rule_type: str = "recommendation"
    priority: str = "medium"
    enforcement: str = "advisory"
    applies_to: Optional[list[str]] = None


class AddAssetRequest(BaseModel):
    name: str
    asset_type: str = "logo"
    description: Optional[str] = None
    file_url: Optional[str] = None
    usage_guidelines: Optional[str] = None
    tags: Optional[list[str]] = None


class ValidateContentRequest(BaseModel):
    content: str
    content_type: str = "social_media"


class CheckConsistencyRequest(BaseModel):
    content_samples: list[str]


# ── Basic endpoints (brandguard:basic) ─────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "brandguard", "version": app.version}


@app.get("/health/detailed")
async def health_detailed():
    checks = {}
    status = "ok"

    # Service layer check
    try:
        svc = _svc()
        stats = svc.get_stats()
        checks["service"] = {
            "status": "ok",
            "has_identity": stats.get("has_identity", False),
            "guidelines_count": stats.get("guidelines_count", 0),
        }
    except Exception as e:
        checks["service"] = {"status": "error", "error": str(e)}
        status = "degraded"

    # Telemetry check
    try:
        svc = _svc()
        telemetry = svc.get_telemetry()
        checks["telemetry"] = {"status": "ok" if telemetry else "unavailable"}
    except Exception:
        checks["telemetry"] = {"status": "unavailable"}

    return {"status": status, "service": "brandguard", "version": app.version, "checks": checks}


@app.post("/v1/identity")
async def create_identity(
    body: CreateIdentityRequest,
    tenant: dict = Depends(require_entitlement("brandguard:basic")),
):
    return _svc().create_identity(
        name=body.name,
        tagline=body.tagline,
        mission=body.mission,
        primary_tone=body.primary_tone,
        voice_attributes=body.voice_attributes,
        primary_color=body.primary_color,
        primary_font=body.primary_font,
    )


@app.get("/v1/identity")
async def get_identity(tenant: dict = Depends(require_entitlement("brandguard:basic"))):
    result = _svc().get_identity()
    if result is None:
        raise HTTPException(status_code=404, detail="No brand identity configured")
    return result


@app.put("/v1/identity/voice")
async def update_voice(
    body: UpdateVoiceRequest,
    tenant: dict = Depends(require_entitlement("brandguard:basic")),
):
    return _svc().update_voice(
        tagline=body.tagline,
        mission=body.mission,
        primary_tone=body.primary_tone,
        preferred_words=body.preferred_words,
        avoided_words=body.avoided_words,
    )


@app.post("/v1/guidelines")
async def add_guideline(
    body: AddGuidelineRequest,
    tenant: dict = Depends(require_entitlement("brandguard:basic")),
):
    guideline_id = _svc().add_guideline(
        category=body.category,
        title=body.title,
        description=body.description,
        rule_type=body.rule_type,
        priority=body.priority,
        enforcement=body.enforcement,
        applies_to=body.applies_to,
    )
    return {"id": guideline_id}


@app.get("/v1/guidelines")
async def get_guidelines(
    category: Optional[str] = Query(None),
    tenant: dict = Depends(require_entitlement("brandguard:basic")),
):
    return _svc().get_guidelines(category=category)


@app.post("/v1/assets")
async def add_asset(
    body: AddAssetRequest,
    tenant: dict = Depends(require_entitlement("brandguard:basic")),
):
    asset_id = _svc().add_asset(
        name=body.name,
        asset_type=body.asset_type,
        description=body.description,
        file_url=body.file_url,
        usage_guidelines=body.usage_guidelines,
        tags=body.tags,
    )
    return {"id": asset_id}


@app.get("/v1/assets")
async def get_assets(
    asset_type: Optional[str] = Query(None),
    tenant: dict = Depends(require_entitlement("brandguard:basic")),
):
    return _svc().get_assets(asset_type=asset_type)


@app.get("/v1/stats")
async def get_stats(tenant: dict = Depends(require_entitlement("brandguard:basic"))):
    return _svc().get_stats()


# ── Pro endpoints (brandguard:full) ────────────────────────────────────────────

@app.post("/v1/validate")
async def validate_content(
    body: ValidateContentRequest,
    tenant: dict = Depends(require_entitlement("brandguard:full")),
):
    return _svc().validate_content(body.content, body.content_type)


@app.post("/v1/consistency")
async def check_consistency(
    body: CheckConsistencyRequest,
    tenant: dict = Depends(require_entitlement("brandguard:full")),
):
    return _svc().check_consistency(body.content_samples)


@app.get("/v1/brand-kit")
async def get_brand_kit(tenant: dict = Depends(require_entitlement("brandguard:full"))):
    return _svc().get_brand_kit()


# ── Enterprise endpoints ───────────────────────────────────────────────────────

@app.get("/v1/executive/{executive_code}")
async def get_executive_report(
    executive_code: str,
    tenant: dict = Depends(require_entitlement("brandguard:full")),
):
    if executive_code not in ("CMO", "CCO", "CPO"):
        raise HTTPException(status_code=400, detail="Invalid executive code. Use CMO, CCO, or CPO.")
    return _svc().get_executive_report(executive_code)


@app.post("/v1/autonomous/analyze")
async def run_autonomous_analysis(tenant: dict = Depends(require_entitlement("brandguard:full"))):
    return _svc().run_autonomous_analysis()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("brandguard.app:app", host="0.0.0.0", port=8004, reload=True)
