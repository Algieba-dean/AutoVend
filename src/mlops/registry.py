"""
Enterprise MLOps & LLMOps Registry:
1. Experiment Tracking Engine
2. Prompt Versioning & Lifecycle Registry
3. Model Catalog & Deployment Stage Registry
4. Dataset Metadata & Integrity Versioning
"""

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.mlops.pg_store import MLOpsPostgresStore, is_test_env
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MLOPS_STORAGE = PROJECT_ROOT / "storage" / "mlops"


class _RegistryBackend:
    """
    Unified storage backend for MLOps registries.
    - When `storage_dir` is explicitly provided (unit tests), stores JSON in `storage_dir`.
    - Otherwise uses PostgreSQL (`mlops_kv` table) in production/staging (fail-fast if unavailable),
      and falls back to in-memory dict only when `APP_ENV=test/testing`.
    """

    def __init__(self, namespace: str, storage_dir: Optional[Path] = None):
        self.namespace = namespace
        self.storage_dir = Path(storage_dir) if storage_dir else None
        if self.storage_dir is not None:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._mem: Dict[str, Dict[str, Any]] = {}

    def _use_postgres(self) -> bool:
        if self.storage_dir is not None:
            return False
        if not is_test_env():
            if not MLOpsPostgresStore.ensure_ready():
                raise RuntimeError(
                    f"PostgreSQL is required for MLOps {self.namespace} in non-test environments."
                )
            return True
        return MLOpsPostgresStore.ensure_ready()

    def save(self, key: str, payload: Dict[str, Any]) -> None:
        if self.storage_dir is not None:
            fpath = self.storage_dir / f"{key}.json"
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return
        if self._use_postgres():
            MLOpsPostgresStore.kv_upsert(self.namespace, key, payload)
        else:
            self._mem[key] = dict(payload)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if self.storage_dir is not None:
            fpath = self.storage_dir / f"{key}.json"
            if not fpath.exists():
                return None
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        if self._use_postgres():
            all_items = MLOpsPostgresStore.kv_load_all(self.namespace)
            return all_items.get(key)
        return self._mem.get(key)

    def load_all(self, prefix: str = "") -> List[Dict[str, Any]]:
        if self.storage_dir is not None:
            out: List[Dict[str, Any]] = []
            for p in self.storage_dir.glob(f"{prefix}*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        out.append(json.load(f))
                except Exception:
                    continue
            return out
        if self._use_postgres():
            all_items = MLOpsPostgresStore.kv_load_all(self.namespace)
            return [v for k, v in all_items.items() if not prefix or k.startswith(prefix)]
        return [v for k, v in self._mem.items() if not prefix or k.startswith(prefix)]


class PromptStatus(str, Enum):
    """Lifecycle status of a prompt version."""

    DRAFT = "draft"
    CANARY = "canary"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ModelStage(str, Enum):
    """Lifecycle stage of a model in the enterprise catalog."""

    DEV = "dev"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"
    ARCHIVED = "archived"


# ── 1. Experiment Tracking ──────────────────────────────────────────────


@dataclass
class RunRecord:
    """A single tracking run in an experiment."""

    run_id: str
    experiment_name: str
    run_name: str = ""
    status: str = "RUNNING"  # RUNNING, FINISHED, FAILED, KILLED
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    latest_metrics: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    commit_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunRecord":
        return cls(**data)


class ExperimentTracker:
    """
    Lightweight, thread-safe, filesystem-backed experiment tracker.
    Provides MLflow-like logging without heavyweight dependencies.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._backend = _RegistryBackend("experiments", storage_dir=self.storage_dir)
        self._lock = threading.RLock()
        self._active_runs: Dict[str, RunRecord] = {}

    def _get_git_commit(self) -> str:
        try:
            import subprocess

            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            return res.stdout.strip() if res.returncode == 0 else ""
        except Exception:
            return ""

    def start_run(
        self,
        experiment_name: str,
        run_name: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> RunRecord:
        """Start a new experiment tracking run."""
        import uuid

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        record = RunRecord(
            run_id=run_id,
            experiment_name=experiment_name,
            run_name=run_name or f"run_{time.strftime('%Y%m%d_%H%M%S')}",
            status="RUNNING",
            start_time=time.time(),
            tags=tags or {},
            commit_hash=self._get_git_commit(),
        )

        with self._lock:
            self._active_runs[run_id] = record
            self._save_run(record)

        logger.info(f"[MLOps] Started experiment run {run_id} ({experiment_name})")
        return record

    def log_param(self, run_id: str, key: str, value: Any) -> None:
        """Log a parameter or hyperparameter to the active run."""
        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            run.params[key] = value
            self._save_run(run)

    def log_metric(self, run_id: str, key: str, value: float, step: Optional[int] = None) -> None:
        """Log a numerical evaluation or training metric with timestamp."""
        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            if key not in run.metrics:
                run.metrics[key] = []
            run.metrics[key].append({"value": float(value), "step": step, "timestamp": time.time()})
            run.latest_metrics[key] = float(value)
            self._save_run(run)

    def log_artifact(self, run_id: str, name: str, artifact_path: str) -> None:
        """Register an artifact file (e.g. plot, dataset, json report)."""
        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            run.artifacts[name] = str(artifact_path)
            self._save_run(run)

    def end_run(self, run_id: str, status: str = "FINISHED") -> RunRecord:
        """Mark an experiment run as completed."""
        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            run.status = status
            run.end_time = time.time()
            self._save_run(run)
            self._active_runs.pop(run_id, None)

        logger.info(f"[MLOps] Ended run {run_id} with status {status}")
        return run

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Fetch run record by ID."""
        with self._lock:
            if run_id in self._active_runs:
                return self._active_runs[run_id]
            data = self._backend.get(run_id)
            if data:
                return RunRecord.from_dict(data)
            return None

    def list_runs(self, experiment_name: Optional[str] = None) -> List[RunRecord]:
        """List all logged runs, optionally filtered by experiment name."""
        runs: List[RunRecord] = []
        with self._lock:
            for data in self._backend.load_all(prefix="run_"):
                try:
                    rec = RunRecord.from_dict(data)
                    if experiment_name is None or rec.experiment_name == experiment_name:
                        runs.append(rec)
                except Exception:
                    continue
        runs.sort(key=lambda r: r.start_time, reverse=True)
        return runs

    def get_best_run(
        self,
        experiment_name: str,
        metric_name: str,
        mode: str = "max",
    ) -> Optional[RunRecord]:
        """Find the optimal run based on target metric ('max' or 'min')."""
        runs = [
            r
            for r in self.list_runs(experiment_name)
            if metric_name in r.latest_metrics and r.status == "FINISHED"
        ]
        if not runs:
            return None

        reverse = mode.lower() == "max"
        runs.sort(key=lambda r: r.latest_metrics[metric_name], reverse=reverse)
        return runs[0]

    def _save_run(self, run: RunRecord) -> None:
        self._backend.save(run.run_id, run.to_dict())


# ── 2. Prompt Versioning & Lifecycle Registry ───────────────────────────


@dataclass
class PromptVersion:
    """Versioned Prompt Template specification."""

    prompt_name: str
    version: str
    template: str
    input_variables: List[str]
    description: str = ""
    author: str = "system"
    status: PromptStatus = PromptStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    commit_hash: str = ""
    prompt_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptVersion":
        cp = dict(data)
        if isinstance(cp.get("status"), str):
            cp["status"] = PromptStatus(cp["status"])
        return cls(**cp)


class PromptRegistry:
    """
    Enterprise Prompt Registry supporting version control, semantic hashing,
    safe canary deployment, rollback, and template diffing.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._backend = _RegistryBackend("prompts", storage_dir=self.storage_dir)
        self._lock = threading.RLock()

    @staticmethod
    def _compute_hash(template: str) -> str:
        return hashlib.sha256(template.strip().encode("utf-8")).hexdigest()[:12]

    def register_prompt(
        self,
        prompt_name: str,
        template: str,
        input_variables: List[str],
        description: str = "",
        author: str = "developer",
        status: PromptStatus = PromptStatus.DRAFT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PromptVersion:
        """Register a new immutable prompt template version."""
        prompt_hash = self._compute_hash(template)
        with self._lock:
            existing = self.list_versions(prompt_name)
            next_ver_num = 1
            if existing:
                try:
                    vers = [
                        int(p.version.lstrip("v"))
                        for p in existing
                        if p.version.lstrip("v").isdigit()
                    ]
                    if vers:
                        next_ver_num = max(vers) + 1
                except Exception:
                    next_ver_num = len(existing) + 1

            version_str = f"v{next_ver_num}"
            prompt_ver = PromptVersion(
                prompt_name=prompt_name,
                version=version_str,
                template=template,
                input_variables=input_variables,
                description=description,
                author=author,
                status=status,
                created_at=time.time(),
                prompt_hash=prompt_hash,
                metadata=metadata or {},
            )

            # If registered directly as ACTIVE, archive previous active version
            if status == PromptStatus.ACTIVE:
                for p in existing:
                    if p.status == PromptStatus.ACTIVE:
                        p.status = PromptStatus.ARCHIVED
                        self._save_version(p)

            self._save_version(prompt_ver)

        logger.info(
            f"[MLOps] Registered prompt {prompt_name}@{version_str} (status={status.value})"
        )
        return prompt_ver

    def get_prompt_version(self, prompt_name: str, version: str) -> Optional[PromptVersion]:
        """Fetch specific prompt version."""
        data = self._backend.get(f"{prompt_name}_{version}")
        if not data:
            return None
        try:
            return PromptVersion.from_dict(data)
        except Exception as exc:
            logger.error(f"Failed to read prompt version {prompt_name}_{version}: {exc}")
            return None

    def get_active_prompt(self, prompt_name: str) -> Optional[PromptVersion]:
        """Retrieve the currently ACTIVE prompt for production serving."""
        versions = self.list_versions(prompt_name)
        for v in versions:
            if v.status == PromptStatus.ACTIVE:
                return v
        return versions[0] if versions else None

    def list_versions(self, prompt_name: str) -> List[PromptVersion]:
        """List all versions of a prompt, newest first."""
        results: List[PromptVersion] = []
        with self._lock:
            for data in self._backend.load_all(prefix=f"{prompt_name}_v"):
                try:
                    results.append(PromptVersion.from_dict(data))
                except Exception:
                    continue
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    def promote_prompt(
        self,
        prompt_name: str,
        version: str,
        target_status: PromptStatus,
    ) -> PromptVersion:
        """Promote a prompt version to ACTIVE, CANARY, or ARCHIVED."""
        with self._lock:
            target = self.get_prompt_version(prompt_name, version)
            if not target:
                raise ValueError(f"Prompt {prompt_name}@{version} not found")

            if target_status == PromptStatus.ACTIVE:
                for p in self.list_versions(prompt_name):
                    if p.version != version and p.status in (
                        PromptStatus.ACTIVE,
                        PromptStatus.CANARY,
                    ):
                        p.status = PromptStatus.ARCHIVED
                        self._save_version(p)

            target.status = target_status
            self._save_version(target)

        logger.info(f"[MLOps] Promoted prompt {prompt_name}@{version} to {target_status.value}")
        return target

    def rollback_prompt(self, prompt_name: str, target_version: str) -> PromptVersion:
        """Instant rollback of a prompt to an earlier stable version."""
        logger.warning(f"[MLOps] Rolling back prompt {prompt_name} to {target_version}")
        return self.promote_prompt(prompt_name, target_version, PromptStatus.ACTIVE)

    def diff_prompts(self, prompt_name: str, v1: str, v2: str) -> Dict[str, Any]:
        """Generate structured diff between two prompt versions."""
        p1 = self.get_prompt_version(prompt_name, v1)
        p2 = self.get_prompt_version(prompt_name, v2)
        if not p1 or not p2:
            raise ValueError(f"Cannot diff missing prompt versions: {v1}, {v2}")

        import difflib

        diff_lines = list(
            difflib.unified_diff(
                p1.template.splitlines(keepends=True),
                p2.template.splitlines(keepends=True),
                fromfile=f"{prompt_name}@{v1}",
                tofile=f"{prompt_name}@{v2}",
            )
        )
        return {
            "prompt_name": prompt_name,
            "v1": v1,
            "v2": v2,
            "identical": p1.prompt_hash == p2.prompt_hash,
            "unified_diff": "".join(diff_lines),
            "v1_variables": p1.input_variables,
            "v2_variables": p2.input_variables,
        }

    def bootstrap_defaults(self) -> None:
        """Seed registry with standard AutoVend prompt templates if not present."""
        default_templates = {
            "response_generation_welcome": (
                "You are AutoVend, a friendly and professional automotive sales assistant.\n"
                "The customer just started a conversation. Greet them warmly, introduce yourself briefly,\n"
                "and ask about their basic information (name, who will be driving, etc.) to start building their profile.\n"
                "Keep the greeting concise and natural.\n\n"
                "Conversation so far:\n{conversation_history}\n\n"
                "Respond naturally in the same language the user uses.",
                ["conversation_history"],
            ),
            "response_generation_profile": (
                "You are AutoVend, a professional automotive sales assistant.\n"
                "You are gathering the customer's profile information through natural conversation.\n\n"
                "Current profile:\n{profile}\n\nInformation still needed: {missing_profile_fields}\n\n"
                "Conversation so far:\n{conversation_history}\n\n"
                "Continue the conversation naturally, asking about missing profile information.\n"
                "Respond in the same language the user uses.",
                ["profile", "missing_profile_fields", "conversation_history"],
            ),
            "response_generation_needs": (
                "You are AutoVend, an expert automotive sales consultant using SPIN Selling methodology.\n"
                "Customer profile:\n{profile}\n\nCurrent explicit needs:\n{explicit_needs}\n\n"
                "Current implicit needs:\n{implicit_needs}\n\nKey needs still to explore: {missing_needs_fields}\n\n"
                "Conversation so far:\n{conversation_history}\n\nRespond in the same language the user uses.",
                [
                    "profile",
                    "explicit_needs",
                    "implicit_needs",
                    "missing_needs_fields",
                    "conversation_history",
                ],
            ),
            "response_generation_car_selection": (
                "You are AutoVend, an expert automotive sales consultant presenting vehicle recommendations.\n"
                "Customer profile:\n{profile}\n\nCurrent explicit needs:\n{explicit_needs}\n\n"
                "Matched cars:\n{matched_cars}\n\n"
                "Conversation so far:\n{conversation_history}\n\n"
                "Present the matched cars concisely, highlighting why each matches their needs.\n"
                "Respond in the same language the user uses.",
                ["profile", "explicit_needs", "matched_cars", "conversation_history"],
            ),
            "response_generation_reservation": (
                "You are AutoVend, assisting the customer in booking a 4S dealership test drive.\n"
                "Customer profile:\n{profile}\nSelected car:\n{selected_car}\n\n"
                "Reservation details:\n{reservation}\nMissing reservation fields: {missing_reservation_fields}\n\n"
                "Conversation so far:\n{conversation_history}\n\n"
                "Help finalize test-drive date, time, and location smoothly.\n"
                "Respond in the same language the user uses.",
                [
                    "profile",
                    "selected_car",
                    "reservation",
                    "missing_reservation_fields",
                    "conversation_history",
                ],
            ),
        }
        for name, (tmpl, vars_) in default_templates.items():
            if not self.list_versions(name):
                self.register_prompt(
                    prompt_name=name,
                    template=tmpl,
                    input_variables=vars_,
                    description=f"AutoVend standard production template for {name}",
                    author="autovend-system",
                    status=PromptStatus.ACTIVE,
                )

    def _save_version(self, prompt: PromptVersion) -> None:
        self._backend.save(f"{prompt.prompt_name}_{prompt.version}", prompt.to_dict())


# ── 3. Model Registry & Deployment Stage Catalog ────────────────────────


@dataclass
class ModelVersion:
    """Catalog record for a registered AI model endpoint."""

    model_id: str
    version: str
    provider: str  # vllm, openai, deepseek, qwen, groq
    model_name: str
    endpoint_url: Optional[str] = None
    context_window: int = 4096
    stage: ModelStage = ModelStage.DEV
    eval_score: Optional[float] = None
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["stage"] = self.stage.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelVersion":
        cp = dict(data)
        if isinstance(cp.get("stage"), str):
            cp["stage"] = ModelStage(cp["stage"])
        return cls(**cp)


class ModelRegistry:
    """Enterprise Model Catalog managing deployment stages and capabilities."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._backend = _RegistryBackend("models", storage_dir=self.storage_dir)
        self._lock = threading.RLock()

    def register_model(
        self,
        model_id: str,
        version: str,
        provider: str,
        model_name: str,
        endpoint_url: Optional[str] = None,
        context_window: int = 4096,
        stage: ModelStage = ModelStage.DEV,
        eval_score: Optional[float] = None,
        cost_per_1k_input_tokens: float = 0.0,
        cost_per_1k_output_tokens: float = 0.0,
        tags: Optional[Dict[str, str]] = None,
    ) -> ModelVersion:
        """Register a model endpoint in the enterprise catalog."""
        model_ver = ModelVersion(
            model_id=model_id,
            version=version,
            provider=provider,
            model_name=model_name,
            endpoint_url=endpoint_url,
            context_window=context_window,
            stage=stage,
            eval_score=eval_score,
            cost_per_1k_input_tokens=cost_per_1k_input_tokens,
            cost_per_1k_output_tokens=cost_per_1k_output_tokens,
            tags=tags or {},
            created_at=time.time(),
        )
        with self._lock:
            self._save_model(model_ver)

        logger.info(f"[MLOps] Registered model {model_id}@{version} ({provider}/{model_name})")
        return model_ver

    def get_model(self, model_id: str, version: str) -> Optional[ModelVersion]:
        """Fetch model by ID and version."""
        data = self._backend.get(f"{model_id}_{version}")
        if not data:
            return None
        try:
            return ModelVersion.from_dict(data)
        except Exception as exc:
            logger.error(f"Failed to read model {model_id}_{version}: {exc}")
            return None

    def list_models(self, stage: Optional[ModelStage] = None) -> List[ModelVersion]:
        """List all models, optionally filtered by deployment stage."""
        models: List[ModelVersion] = []
        with self._lock:
            for data in self._backend.load_all():
                try:
                    m = ModelVersion.from_dict(data)
                    if stage is None or m.stage == stage:
                        models.append(m)
                except Exception:
                    continue
        models.sort(key=lambda m: m.created_at, reverse=True)
        return models

    def promote_model(self, model_id: str, version: str, stage: ModelStage) -> ModelVersion:
        """Promote a model to STAGING, CANARY, or PRODUCTION."""
        with self._lock:
            model = self.get_model(model_id, version)
            if not model:
                raise ValueError(f"Model {model_id}@{version} not found")

            if stage == ModelStage.PRODUCTION:
                # Demote existing production models of the same model_id
                for m in self.list_models():
                    if (
                        m.model_id == model_id
                        and m.version != version
                        and m.stage == ModelStage.PRODUCTION
                    ):
                        m.stage = ModelStage.ARCHIVED
                        self._save_model(m)

            model.stage = stage
            self._save_model(model)

        logger.info(f"[MLOps] Promoted model {model_id}@{version} to {stage.value}")
        return model

    def bootstrap_defaults(self) -> None:
        """Seed registry with production model catalog records."""
        defaults = [
            {
                "model_id": "qwen2.5-7b-instruct",
                "version": "v1.0",
                "provider": "vllm",
                "model_name": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                "context_window": 32768,
                "stage": ModelStage.PRODUCTION,
                "eval_score": 0.892,
                "cost_per_1k_input_tokens": 0.0,
                "cost_per_1k_output_tokens": 0.0,
                "tags": {"tier": "local", "quantization": "gptq_int4"},
            },
            {
                "model_id": "llama-3.3-70b-versatile",
                "version": "v1.0",
                "provider": "groq",
                "model_name": "llama-3.3-70b-versatile",
                "context_window": 8192,
                "stage": ModelStage.STAGING,
                "eval_score": 0.945,
                "cost_per_1k_input_tokens": 0.00059,
                "cost_per_1k_output_tokens": 0.00079,
                "tags": {"tier": "cloud", "speed": "ultra-fast"},
            },
            {
                "model_id": "deepseek-chat",
                "version": "v3.0",
                "provider": "deepseek",
                "model_name": "deepseek-chat",
                "context_window": 64000,
                "stage": ModelStage.STAGING,
                "eval_score": 0.952,
                "cost_per_1k_input_tokens": 0.00014,
                "cost_per_1k_output_tokens": 0.00028,
                "tags": {"tier": "cloud", "reasoning": "high"},
            },
        ]
        for m in defaults:
            if not self.get_model(m["model_id"], m["version"]):
                self.register_model(**m)

    def _save_model(self, model: ModelVersion) -> None:
        self._backend.save(f"{model.model_id}_{model.version}", model.to_dict())


# ── 4. Dataset Metadata Versioning ──────────────────────────────────────


@dataclass
class DatasetVersion:
    """Versioned metadata record for Golden Evaluation & RAG datasets."""

    dataset_name: str
    version: str
    file_path: str
    sha256_hash: str
    sample_count: int
    schema_fields: List[str]
    description: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetVersion":
        return cls(**data)


class DatasetRegistry:
    """Tracks dataset versions, schema definitions, and cryptographic checksums."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._backend = _RegistryBackend("datasets", storage_dir=self.storage_dir)
        self._lock = threading.RLock()

    @staticmethod
    def _compute_file_hash(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def register_dataset(
        self,
        dataset_name: str,
        version: str,
        file_path: Path | str,
        sample_count: int,
        schema_fields: List[str],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DatasetVersion:
        """Register a dataset version with SHA-256 integrity fingerprint."""
        p = Path(file_path)
        sha256_val = self._compute_file_hash(p) if p.exists() else ""

        ver = DatasetVersion(
            dataset_name=dataset_name,
            version=version,
            file_path=str(p.resolve()) if p.exists() else str(p),
            sha256_hash=sha256_val,
            sample_count=sample_count,
            schema_fields=schema_fields,
            description=description,
            created_at=time.time(),
            metadata=metadata or {},
        )
        with self._lock:
            self._backend.save(f"{dataset_name}_{version}", ver.to_dict())

        logger.info(
            f"[MLOps] Registered dataset {dataset_name}@{version} ({sample_count} samples, hash={sha256_val[:8]}...)"
        )
        return ver

    def bootstrap_defaults(self) -> None:
        """Seed dataset registry with golden evaluation and vehicle catalog datasets."""
        golden_file = PROJECT_ROOT / "data" / "golden_intent.json"
        if golden_file.exists():
            if not self.get_dataset("golden_intent", "v1.0"):
                self.register_dataset(
                    dataset_name="golden_intent",
                    version="v1.0",
                    file_path=golden_file,
                    sample_count=50,
                    schema_fields=["query", "expected_stage", "intent"],
                    description="Golden evaluation dataset for customer intent classification and routing",
                )
        cars_file = PROJECT_ROOT / "data" / "cars.toml"
        if cars_file.exists():
            if not self.get_dataset("vehicle_catalog", "v1.0"):
                self.register_dataset(
                    dataset_name="vehicle_catalog",
                    version="v1.0",
                    file_path=cars_file,
                    sample_count=20,
                    schema_fields=["car_model", "brand", "price", "powertrain_type"],
                    description="Automotive vehicle catalog inventory dataset",
                )

    def get_dataset(self, dataset_name: str, version: str) -> Optional[DatasetVersion]:
        """Fetch dataset version metadata."""
        data = self._backend.get(f"{dataset_name}_{version}")
        if not data:
            return None
        try:
            return DatasetVersion.from_dict(data)
        except Exception:
            return None

    def verify_integrity(self, dataset_name: str, version: str) -> bool:
        """Check if physical file matches registered SHA-256 hash."""
        ver = self.get_dataset(dataset_name, version)
        if not ver:
            return False
        p = Path(ver.file_path)
        if not p.exists():
            return False
        current_hash = self._compute_file_hash(p)
        return current_hash == ver.sha256_hash


@dataclass
class ArtifactBundleVersion:
    """Four-in-one version bundle: Prompt + Graph Topology + Model Routing Policy + pgvector Index."""

    bundle_version: str
    prompt_version: str
    graph_topology_version: str
    model_routing_policy: str
    pgvector_index_version: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArtifactBundleRegistry:
    """Computes and tracks immutable 4-in-1 `artifact_bundle_version` identifiers."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._backend = _RegistryBackend("bundles", storage_dir=self.storage_dir)
        self._lock = threading.RLock()
        self._current: Optional[ArtifactBundleVersion] = None

    def register_bundle(
        self,
        prompt_version: str,
        graph_topology_version: str,
        model_routing_policy: str,
        pgvector_index_version: str,
    ) -> ArtifactBundleVersion:
        raw = f"{prompt_version}|{graph_topology_version}|{model_routing_policy}|{pgvector_index_version}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        bundle_id = f"bundle-{digest}"
        bundle = ArtifactBundleVersion(
            bundle_version=bundle_id,
            prompt_version=prompt_version,
            graph_topology_version=graph_topology_version,
            model_routing_policy=model_routing_policy,
            pgvector_index_version=pgvector_index_version,
        )
        with self._lock:
            self._current = bundle
            self._backend.save(bundle_id, bundle.to_dict())
        return bundle

    def get_current(self) -> ArtifactBundleVersion:
        with self._lock:
            if self._current is not None:
                return self._current
            active_prompt = prompt_registry.get_active_prompt("response_generation_welcome")
            p_ver = active_prompt.version if active_prompt else "v1.0.0"
            return self.register_bundle(
                prompt_version=p_ver,
                graph_topology_version="langgraph-crag-audit-v1",
                model_routing_policy="hybrid-local-control-cloud-synthesis-v1",
                pgvector_index_version="pgvector-hnsw-v1",
            )


# Global Singletons
experiment_tracker = ExperimentTracker()
prompt_registry = PromptRegistry()
model_registry = ModelRegistry()
dataset_registry = DatasetRegistry()
artifact_bundle_registry = ArtifactBundleRegistry()

# Bootstrap default enterprise production artifacts
try:
    prompt_registry.bootstrap_defaults()
    model_registry.bootstrap_defaults()
    dataset_registry.bootstrap_defaults()
except Exception as _bootstrap_err:
    logger.warning(f"[MLOps] Bootstrap default initialization warning: {_bootstrap_err}")
