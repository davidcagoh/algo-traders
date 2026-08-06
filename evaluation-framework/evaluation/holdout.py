"""Mechanically-enforced holdout sealing.

Literature: same corpus as `splits.py`. `STATUS.md` (this repo) states the
2026-06-01 through 2026-12-31 forward window "should not be partially
inspected if it is to remain a valid one-shot gate" — until now that was
enforced by memory only. `seal_holdout`/`guard`/`break_seal` make peeking
mechanically impossible instead of merely discouraged: `guard()` raises on
any read that touches a sealed window, and every guard call — pass or fail
— is logged, so a seal break is always visible and attributable, never
silent (Jadouli 2026's missing-artifacts failure mode, applied to the
holdout itself rather than just to trial results).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


class HoldoutViolation(RuntimeError):
    pass


def _window_hash(name: str, start: str, end: str) -> str:
    blob = json.dumps({"name": name, "start": start, "end": end}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class HoldoutSeal:
    name: str
    start: str  # ISO date/datetime
    end: str
    window_hash: str
    manifest_path: Path
    status: str  # "sealed" or "broken"


def _read_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append_manifest(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True, default=str) + "\n")


def seal_holdout(name: str, start: str, end: str, path: Path) -> HoldoutSeal:
    """Create (or re-affirm) a sealed holdout window, recorded append-only
    at `path`. Sealing an already-sealed window with identical bounds is a
    no-op; sealing with different bounds under the same name raises.
    """
    path = Path(path)
    existing = [e for e in _read_manifest(path) if e["name"] == name]
    window_hash = _window_hash(name, start, end)
    if existing:
        last = existing[-1]
        if last["status"] == "broken":
            raise HoldoutViolation(
                f"holdout {name!r} was already broken at {last['broken_at']} "
                f"(reason: {last.get('reason')!r}); cannot re-seal"
            )
        if last["window_hash"] != window_hash:
            raise HoldoutViolation(
                f"holdout {name!r} is already sealed with different bounds "
                f"({last['start']}..{last['end']}); refusing to change bounds silently"
            )
        return HoldoutSeal(name, start, end, window_hash, path, "sealed")

    entry = {
        "event": "sealed",
        "name": name,
        "start": start,
        "end": end,
        "window_hash": window_hash,
        "sealed_at": _now_iso(),
        "status": "sealed",
    }
    _append_manifest(path, entry)
    return HoldoutSeal(name, start, end, window_hash, path, "sealed")


def _load_seal(name: str, path: Path) -> dict:
    rows = [e for e in _read_manifest(path) if e["name"] == name]
    if not rows:
        raise HoldoutViolation(f"no seal found for holdout {name!r} at {path}")
    return rows[-1]


def guard(
    data: pd.Series | pd.DataFrame,
    name: str,
    path: Path,
    *,
    date_col: str | None = None,
) -> None:
    """Raise `HoldoutViolation` if any timestamp in `data` falls inside the
    sealed window `name`. Every call — pass or fail — is appended to the
    manifest's access log, so reads are always attributable.
    """
    path = Path(path)
    seal = _load_seal(name, path)
    if seal["status"] == "broken":
        _append_manifest(
            path,
            {"event": "guard_pass_after_break", "name": name, "checked_at": _now_iso()},
        )
        return

    if date_col is not None:
        idx = pd.DatetimeIndex(pd.to_datetime(data[date_col]))
    elif isinstance(data, (pd.Series, pd.DataFrame)):
        idx = pd.DatetimeIndex(pd.to_datetime(data.index))
    else:
        raise TypeError("data must be a pandas Series/DataFrame, or pass date_col")

    start = pd.Timestamp(seal["start"])
    end = pd.Timestamp(seal["end"])
    if idx.tz is not None and start.tz is None:
        start = start.tz_localize(idx.tz)
        end = end.tz_localize(idx.tz)

    violated = bool(((idx >= start) & (idx <= end)).any())
    _append_manifest(
        path,
        {
            "event": "guard_violation" if violated else "guard_pass",
            "name": name,
            "checked_at": _now_iso(),
        },
    )
    if violated:
        raise HoldoutViolation(
            f"data touches sealed holdout {name!r} ({seal['start']}..{seal['end']}); "
            "call break_seal() explicitly if this read is intentional"
        )


def break_seal(name: str, path: Path, reason: str, decision_ref: str) -> None:
    """Irreversibly break a seal. Logged, not undoable — a subsequent
    `seal_holdout` with the same name and bounds returns the still-broken
    status via `guard`/`seal_holdout`'s checks above."""
    path = Path(path)
    _load_seal(name, path)  # raises if no seal exists
    _append_manifest(
        path,
        {
            "event": "broken",
            "name": name,
            "status": "broken",
            "broken_at": _now_iso(),
            "reason": reason,
            "decision_ref": decision_ref,
        },
    )
