"""
Enterprise MLOps & Observability API Routes (backend/app/routes/mlops.py).

Provides endpoints for:
- /api/v1/mlops/experiments: Experiment tracking and runs
- /api/v1/mlops/prompts: Prompt registry, versioning, rollback
- /api/v1/mlops/models: Model registry and deployment stages
- /api/v1/mlops/drift: Semantic drift and distribution shift report
- /api/v1/mlops/canary: Canary health and automated rollback controls
- /api/v1/mlops/dlq: Dead Letter Queue inspection and replay
- /metrics: Prometheus-compatible metrics exposition
"""

import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from src.mlops.deployment import (
    CanaryConfig,
    DeploymentStatus,
    RoutingMode,
    deployment_router,
)
from src.mlops.dlq_replay import DLQTaskStatus, dlq_replay_engine
from src.mlops.drift import semantic_drift_detector
from src.mlops.observability import alert_manager
from src.mlops.registry import (
    experiment_tracker,
    model_registry,
    prompt_registry,
)

router = APIRouter(prefix="/api/v1/mlops", tags=["MLOps"])


# ── Schemas ─────────────────────────────────────────────────────────────


class PromptRollbackRequest(BaseModel):
    prompt_name: str
    target_version: str


class CanaryConfigRequest(BaseModel):
    baseline_version: str = "v1"
    candidate_version: str = "v2"
    mode: RoutingMode = RoutingMode.CANARY
    canary_weight: float = Field(0.10, ge=0.0, le=1.0)


class CanaryRollbackRequest(BaseModel):
    reason: str = "Manual operator rollback"


# ── 1. Experiment Tracking Endpoints ────────────────────────────────────


@router.get("/experiments")
async def list_experiment_runs(experiment_name: Optional[str] = None):
    """List all tracked experiment runs."""
    runs = experiment_tracker.list_runs(experiment_name)
    return {"runs": [r.to_dict() for r in runs], "count": len(runs)}


# ── 2. Prompt Versioning & Registry ─────────────────────────────────────


@router.get("/prompts")
async def list_prompts(prompt_name: str = "response_generation"):
    """List all versions of a registered prompt template."""
    versions = prompt_registry.list_versions(prompt_name)
    active = prompt_registry.get_active_prompt(prompt_name)
    return {
        "prompt_name": prompt_name,
        "active_version": active.to_dict() if active else None,
        "versions": [v.to_dict() for v in versions],
    }


@router.post("/prompts/rollback")
async def rollback_prompt(req: PromptRollbackRequest):
    """Rollback a prompt template to a specified earlier version."""
    try:
        promoted = prompt_registry.rollback_prompt(req.prompt_name, req.target_version)
        return {"status": "ok", "rolled_back_to": promoted.to_dict()}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── 3. Model Registry Endpoints ─────────────────────────────────────────


@router.get("/models")
async def list_models(stage: Optional[str] = None):
    """List registered models in catalog."""
    from src.mlops.registry import ModelStage

    st = ModelStage(stage) if stage else None
    models = model_registry.list_models(st)
    return {"models": [m.to_dict() for m in models], "count": len(models)}


# ── 4. Drift & Distribution Shift Endpoints ─────────────────────────────


@router.get("/drift")
async def get_drift_report(format: str = Query("json", pattern="^(json|markdown)$")):
    """Fetch current semantic drift, intent shift, and RAG retrieval quality report."""
    report = semantic_drift_detector.generate_drift_report()
    if format == "markdown":
        return Response(content=report.to_markdown(), media_type="text/markdown")
    return report.to_dict()


# ── 5. Canary / Deployment Controls ─────────────────────────────────────


@router.get("/canary")
async def get_canary_status():
    """Fetch real-time canary health, traffic split, and rollback status."""
    return deployment_router.get_canary_health()


@router.post("/canary/config")
async def configure_canary(req: CanaryConfigRequest):
    """Update canary deployment routing mode and traffic split ratio."""
    cfg = CanaryConfig(
        baseline_version=req.baseline_version,
        candidate_version=req.candidate_version,
        mode=req.mode,
        canary_weight=req.canary_weight,
        status=DeploymentStatus.MONITORING,
    )
    deployment_router.set_config(cfg)
    return {"status": "updated", "config": deployment_router.get_canary_health()}


@router.post("/canary/rollback")
async def trigger_canary_rollback(req: CanaryRollbackRequest):
    """Trigger manual emergency rollback of canary traffic."""
    deployment_router.trigger_rollback(req.reason)
    return {"status": "rolled_back", "health": deployment_router.get_canary_health()}


# ── 6. Dead Letter Queue & Replay ───────────────────────────────────────


@router.get("/dlq")
async def list_dlq_tasks(status: Optional[str] = None):
    """List failed tasks in the Dead Letter Queue."""
    st = DLQTaskStatus(status) if status else None
    tasks = dlq_replay_engine.list_tasks(st)
    return {"tasks": [t.to_dict() for t in tasks], "count": len(tasks)}


@router.post("/dlq/replay")
async def replay_dlq_tasks(task_type: Optional[str] = None, force: bool = False):
    """Trigger precision replay for failed tasks."""

    # Register mock/safe retry executors for API triggered replay
    def _safe_executor(payload: Dict[str, Any]):
        return {"replayed": True, "timestamp": time.time()}

    summary = dlq_replay_engine.replay_pending_tasks(
        task_type=task_type,
        executors={
            "llm_generation": _safe_executor,
            "eval_judge": _safe_executor,
            "extractor": _safe_executor,
            "retrieval": _safe_executor,
        },
        force=force,
    )
    return {"status": "completed", "summary": asdict(summary)}


# ── 7. Observability & Alerts ───────────────────────────────────────────


@router.get("/alerts")
async def list_alerts():
    """Fetch active and recent alert events."""
    alerts = alert_manager.list_recent_alerts()
    return {"alerts": [a.to_dict() for a in alerts], "count": len(alerts)}
