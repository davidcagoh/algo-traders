"""Machine-readable trial ledger.

Literature: Bailey & López de Prado 2014 (DSR needs the real trial count and
cross-trial Sharpe variance, not the survivor count — see `dsr.py`); Harvey,
Liu & Zhu 2016 (multiple-testing thresholds scale with total tests
attempted, including unreported/discarded ones); Jadouli 2026 (missing
artifacts and post-hoc promotion are the audited failure modes — an
append-only ledger closes both); Chauhan 2026 (researcher-menu correction,
i.e. an *effective* trial count that clusters near-duplicate trials rather
than counting each superficial variant as independent).

The ledger is append-only: a line is never rewritten, only added. Discarded
trials still count toward `n_trials()` — that is the entire point. Reading
`n_trials()` from a ledger, rather than from `len(candidates_a_caller_kept)`,
is what fixes the DSR under-deflation bug documented in `dsr.py` and
`../wiki/decisions-archive.md` (2026-08-06).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

Status = Literal["completed", "aborted", "discarded"]
EvidenceStage = Literal["backtest", "paper", "live"]
GateOutcome = Literal["passed", "killed", "pending", "n/a"]

SCHEMA_VERSION = 2


def _canonical_param_hash(params: Mapping[str, Any]) -> str:
    """Stable hash of a params mapping, independent of key order."""
    blob = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TrialRecord:
    trial_id: str
    created_at: str  # ISO 8601
    family: str
    strategy: str
    params: Mapping[str, Any]
    dataset_id: str
    split_id: str
    status: Status
    schema_version: int = SCHEMA_VERSION
    code_ref: str | None = None
    cost_model_id: str | None = None
    sharpe: float | None = None
    n_obs: int | None = None
    returns_artifact: str | None = None
    notes: str = ""
    project: str | None = None
    venue: str | None = None
    evidence_stage: EvidenceStage | None = None
    gate_outcome: GateOutcome | None = None
    param_hash: str = field(default="")

    def __post_init__(self) -> None:
        if not self.param_hash:
            object.__setattr__(self, "param_hash", _canonical_param_hash(self.params))

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> TrialRecord:
        d = dict(d)
        d.pop("schema_version", None)
        return cls(**d)


class DuplicateTrialError(ValueError):
    pass


class LedgerValidationError(ValueError):
    pass


class TrialLedger:
    """Append-only JSONL store of `TrialRecord`s."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, record: TrialRecord, *, allow_rerun: bool = False) -> None:
        if not allow_rerun and self.path.exists():
            for existing in self._iter_raw():
                if (
                    existing.get("strategy") == record.strategy
                    and existing.get("param_hash") == record.param_hash
                    and existing.get("dataset_id") == record.dataset_id
                    and existing.get("split_id") == record.split_id
                ):
                    raise DuplicateTrialError(
                        f"trial with strategy={record.strategy!r} "
                        f"param_hash={record.param_hash[:12]} "
                        f"dataset_id={record.dataset_id} split_id={record.split_id} "
                        "already exists; pass allow_rerun=True to record another attempt"
                    )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(record.to_json_line() + "\n")

    def _iter_raw(self) -> Iterable[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        with open(self.path) as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise LedgerValidationError(f"{self.path}:{lineno}: corrupt line: {e}") from e
        return rows

    def load(self) -> list[TrialRecord]:
        return [TrialRecord.from_dict(r) for r in self._iter_raw()]

    def validate(self) -> list[str]:
        """Return a list of human-readable problems; empty means valid."""
        problems: list[str] = []
        required = {
            "trial_id",
            "created_at",
            "family",
            "strategy",
            "params",
            "dataset_id",
            "split_id",
            "status",
            "param_hash",
        }
        for lineno, row in enumerate(self._iter_raw(), start=1):
            missing = required - row.keys()
            if missing:
                problems.append(f"line {lineno}: missing fields {sorted(missing)}")
            if row.get("status") not in ("completed", "aborted", "discarded"):
                problems.append(f"line {lineno}: invalid status {row.get('status')!r}")
        return problems

    def scope(
        self,
        *,
        family: str | None = None,
        dataset_id: str | None = None,
        since: str | None = None,
        project: str | None = None,
        venue: str | None = None,
        evidence_stage: str | None = None,
        gate_outcome: str | None = None,
    ) -> list[TrialRecord]:
        rows = self.load()
        if family is not None:
            rows = [r for r in rows if r.family == family]
        if dataset_id is not None:
            rows = [r for r in rows if r.dataset_id == dataset_id]
        if since is not None:
            rows = [r for r in rows if r.created_at >= since]
        if project is not None:
            rows = [r for r in rows if r.project == project]
        if venue is not None:
            rows = [r for r in rows if r.venue == venue]
        if evidence_stage is not None:
            rows = [r for r in rows if r.evidence_stage == evidence_stage]
        if gate_outcome is not None:
            rows = [r for r in rows if r.gate_outcome == gate_outcome]
        return rows

    def registry_groups(
        self, **scope_kwargs: Any
    ) -> dict[tuple[str | None, str | None], list[TrialRecord]]:
        """Group trials by (evidence_stage, venue).

        Deliberately not a single ranked leaderboard: killed IS-backtests and
        live-tested strategies are not comparable, and Sharpe scales differ
        by venue. Grouping by (evidence_stage, venue) keeps only
        like-for-like comparisons within a group.
        """
        groups: dict[tuple[str | None, str | None], list[TrialRecord]] = {}
        for row in self.scope(**scope_kwargs):
            key = (row.evidence_stage, row.venue)
            groups.setdefault(key, []).append(row)
        return groups

    def n_trials(self, **scope_kwargs: Any) -> int:
        """Total trial count, including discarded/aborted ones."""
        return len(self.scope(**scope_kwargs))

    def sharpe_variance(self, **scope_kwargs: Any) -> float:
        rows = [r for r in self.scope(**scope_kwargs) if r.sharpe is not None]
        if len(rows) < 2:
            return 0.0
        return float(np.var([r.sharpe for r in rows], ddof=1))

    def to_frame(self, **scope_kwargs: Any) -> pd.DataFrame:
        rows = self.scope(**scope_kwargs)
        if not rows:
            return pd.DataFrame(
                columns=[
                    "trial_id",
                    "created_at",
                    "family",
                    "strategy",
                    "dataset_id",
                    "split_id",
                    "status",
                    "sharpe",
                    "n_obs",
                    "project",
                    "venue",
                    "evidence_stage",
                    "gate_outcome",
                    "param_hash",
                ]
            )
        return pd.DataFrame([asdict(r) for r in rows])


def effective_trials(
    returns: pd.DataFrame, method: str = "cluster", threshold: float = 0.9
) -> tuple[int, int]:
    """Return (raw_n, effective_n) for a (period x trial) returns matrix.

    `effective_n` clusters trials by pairwise |correlation| >= `threshold`
    (single-linkage: any trial within `threshold` of any cluster member
    joins it) and counts clusters, not raw columns. Guards against
    near-duplicate trials (e.g. minor parameter variants of the same
    strategy) inflating the trial count used for DSR/PBO deflation.
    Reports both numbers — do not silently prefer one.
    """
    raw_n = returns.shape[1]
    if raw_n <= 1 or method != "cluster":
        return raw_n, raw_n

    corr = returns.corr().abs().values
    n = corr.shape[0]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if corr[i, j] >= threshold:
                union(i, j)

    clusters = {find(i) for i in range(n)}
    return raw_n, len(clusters)
