"""Discoverable string addresses for every series in the data manifest."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


class SeriesNotFound(KeyError):
    """Raised when a query cannot be resolved to a stored series."""


class AmbiguousSeries(KeyError):
    """Raised when a shorthand query matches more than one stored series."""


@dataclass(frozen=True)
class SeriesRef:
    id: str
    table: str
    member: str | None
    field: str
    member_column: str | None
    description: str
    path: str
    start: str | None
    end: str | None


_TABLE_LAYOUTS: dict[str, tuple[str | None, tuple[str, ...], str]] = {
    "coinmetrics_daily": (
        "asset",
        ("AdrActCnt", "CapMrktCurUSD", "PriceUSD", "SplyCur", "TxCnt"),
        "Coin Metrics network data",
    ),
    "defillama_daily": ("series", ("value",), "DeFiLlama aggregate"),
    "fear_greed_daily": (None, ("fear_greed",), "Crypto Fear & Greed Index"),
    "fred": ("series", ("value",), "FRED macroeconomic series"),
    "funding_binance": ("symbol", ("funding_rate",), "Binance perpetual funding"),
    "funding_hyperliquid": (
        "symbol",
        ("funding_rate", "premium"),
        "Hyperliquid perpetual data",
    ),
    "spot_perpetual_basis_1h": (
        "symbol",
        ("close_spot", "close_perpetual", "basis"),
        "Binance spot-perpetual basis",
    ),
    "traditional_daily": (
        "symbol",
        ("open", "high", "low", "close", "adjusted_close", "volume"),
        "Traditional market daily data",
    ),
}

_OHLCV_FIELDS = (
    "open",
    "high",
    "low",
    "close",
    "volume_base",
    "quote_volume",
    "trade_count",
    "taker_buy_volume_base",
    "taker_buy_volume_quote",
)


class SeriesCatalog:
    def __init__(self, manifest_path: str | Path, root: str | Path = ".") -> None:
        self.root = Path(root).resolve()
        manifest = Path(manifest_path)
        self.manifest_path = manifest if manifest.is_absolute() else self.root / manifest
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"market-data manifest not found: {self.manifest_path}")
        self.manifest: dict[str, Any] = json.loads(self.manifest_path.read_text())
        self._descriptions = self._load_descriptions()
        self._refs = self._build()
        self._by_id = {ref.id.lower(): ref for ref in self._refs}

    def _load_descriptions(self) -> dict[str, str]:
        catalog_value = self.manifest.get("catalog")
        if not catalog_value:
            return {}
        path = Path(catalog_value)
        path = path if path.is_absolute() else self.root / path
        if not path.exists():
            return {}
        raw = json.loads(path.read_text())
        descriptions: dict[str, str] = {}
        descriptions.update(raw.get("fred", {}))
        descriptions.update(raw.get("traditional_markets", {}))
        return descriptions

    def _layout(self, table: str) -> tuple[str | None, tuple[str, ...], str] | None:
        if table in _TABLE_LAYOUTS:
            return _TABLE_LAYOUTS[table]
        if table.startswith("spot_"):
            return "symbol", _OHLCV_FIELDS, "Binance spot market"
        if table.startswith("perpetual_"):
            return "symbol", _OHLCV_FIELDS, "Binance perpetual market"
        return None

    def _build(self) -> list[SeriesRef]:
        refs: list[SeriesRef] = []
        for table, metadata in self.manifest.get("tables", {}).items():
            layout = self._layout(table)
            if layout is None:
                continue
            member_column, requested_fields, table_description = layout
            fields = [field for field in requested_fields if field in metadata.get("columns", [])]
            members: list[str | None] = (
                [str(value) for value in metadata.get("members", [])]
                if member_column
                else [None]
            )
            for member in members:
                for field in fields:
                    parts = [table]
                    if member is not None:
                        parts.append(member)
                    parts.append(field)
                    description = self._descriptions.get(member or "", table_description)
                    refs.append(
                        SeriesRef(
                            id=":".join(parts),
                            table=table,
                            member=member,
                            field=field,
                            member_column=member_column,
                            description=description,
                            path=str(metadata["path"]),
                            start=metadata.get("start"),
                            end=metadata.get("end"),
                        )
                    )
        return refs

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(asdict(ref) for ref in self._refs)

    def search(self, query: str = "", limit: int = 30) -> pd.DataFrame:
        words = query.lower().replace(":", " ").split()
        matches = []
        for ref in self._refs:
            haystack = f"{ref.id} {ref.description}".lower().replace(":", " ")
            if all(word in haystack for word in words):
                exact = int(query.lower() in {ref.id.lower(), (ref.member or "").lower()})
                prefix = int(ref.id.lower().startswith(query.lower()))
                matches.append((exact, prefix, ref))
        matches.sort(key=lambda item: (-item[0], -item[1], item[2].id.lower()))
        return pd.DataFrame(asdict(item[2]) for item in matches[:limit])

    @staticmethod
    def _default_field(table: str) -> str | None:
        if table in {"fred", "defillama_daily"}:
            return "value"
        if table.startswith(("spot_", "perpetual_")) or table == "traditional_daily":
            return "close"
        if table.startswith("funding_"):
            return "funding_rate"
        return None

    def resolve(self, query: str) -> SeriesRef:
        value = query.strip()
        if not value:
            raise SeriesNotFound("series query cannot be empty")
        if exact := self._by_id.get(value.lower()):
            return exact

        parts = value.split(":")
        if len(parts) == 2:
            table, second = parts
            default = self._default_field(table)
            shorthand = f"{table}:{second}:{default}" if default else ""
            if shorthand and (exact := self._by_id.get(shorthand.lower())):
                return exact

        member_matches = [ref for ref in self._refs if (ref.member or "").lower() == value.lower()]
        preferred = [
            ref for ref in member_matches if ref.field == self._default_field(ref.table)
        ]
        if len(preferred) == 1:
            return preferred[0]

        suggestions = self.search(value, limit=8)
        ids = suggestions["id"].tolist() if "id" in suggestions else []
        if len(ids) == 1:
            return self._by_id[ids[0].lower()]
        if ids:
            raise AmbiguousSeries(
                f"{value!r} is ambiguous; use a full address. Suggestions: {', '.join(ids)}"
            )
        raise SeriesNotFound(f"no series matches {value!r}")

    def path_for(self, ref: SeriesRef) -> Path:
        path = Path(ref.path)
        return path if path.is_absolute() else self.root / path
