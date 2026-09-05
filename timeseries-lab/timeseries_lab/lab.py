"""High-level notebook API for search, loading, alignment, plots, and regressions."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from timeseries_lab.catalog import SeriesCatalog, SeriesRef
from timeseries_lab.regression import RegressionResult, ols
from timeseries_lab.transforms import apply_transforms, split_query


class TimeSeriesLab:
    def __init__(
        self,
        manifest: str | Path = "data/market/manifest.json",
        *,
        root: str | Path = ".",
        verify_checksums: bool = False,
    ) -> None:
        self.catalog = SeriesCatalog(manifest, root=root)
        self.verify_checksums = verify_checksums
        self._verified: set[Path] = set()
        self._cache: dict[str, pd.Series] = {}

    def search(self, query: str = "", limit: int = 30) -> pd.DataFrame:
        """Search canonical IDs and descriptions; returns a notebook-friendly table."""
        return self.catalog.search(query, limit=limit)

    def describe(self, query: str) -> dict[str, Any]:
        ref = self.catalog.resolve(split_query(query)[0])
        return {
            "id": ref.id,
            "description": ref.description,
            "table": ref.table,
            "member": ref.member,
            "field": ref.field,
            "start": ref.start,
            "end": ref.end,
            "path": str(self.catalog.path_for(ref)),
        }

    def _verify(self, ref: SeriesRef) -> None:
        path = self.catalog.path_for(ref)
        if not self.verify_checksums or path in self._verified:
            return
        expected = self.catalog.manifest["tables"][ref.table].get("sha256")
        if expected:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                raise ValueError(f"checksum mismatch for {path}")
        self._verified.add(path)

    def _read(self, ref: SeriesRef) -> pd.Series:
        if ref.id in self._cache:
            return self._cache[ref.id].copy()
        path = self.catalog.path_for(ref)
        if not path.exists():
            raise FileNotFoundError(f"series data is not available locally: {path}")
        self._verify(ref)
        columns = ["timestamp", ref.field]
        filters = None
        if ref.member_column and ref.member is not None:
            columns.append(ref.member_column)
            filters = [(ref.member_column, "==", ref.member)]
        try:
            frame = pd.read_parquet(path, columns=columns, filters=filters)
        except (TypeError, ValueError):
            frame = pd.read_parquet(path, columns=columns)
            if ref.member_column and ref.member is not None:
                frame = frame[frame[ref.member_column].astype(str) == ref.member]
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        values = pd.to_numeric(frame[ref.field], errors="coerce")
        series = pd.Series(values.to_numpy(), index=frame["timestamp"], name=ref.id)
        series = series.groupby(level=0).last().sort_index()
        self._cache[ref.id] = series
        return series.copy()

    def get(
        self,
        query: str,
        *,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
    ) -> pd.Series:
        """Load one address and apply optional pipe transforms."""
        address, transforms = split_query(query)
        ref = self.catalog.resolve(address)
        result = apply_transforms(self._read(ref), transforms)
        if start is not None:
            result = result.loc[_utc_bound(start) :]
        if end is not None:
            result = result.loc[: _utc_bound(end)]
        result.name = query
        return result

    def __getitem__(self, query: str) -> pd.Series:
        return self.get(query)

    def read_file(
        self,
        path: str | Path,
        *,
        timestamp: str = "timestamp",
        value: str = "value",
        name: str | None = None,
    ) -> pd.Series:
        """Read one ad-hoc CSV, TSV, or Parquet series for immediate analysis."""
        source = Path(path)
        if source.suffix.lower() in {".parquet", ".pq"}:
            frame = pd.read_parquet(source, columns=[timestamp, value])
        elif source.suffix.lower() == ".tsv":
            frame = pd.read_csv(source, sep="\t", usecols=[timestamp, value])
        elif source.suffix.lower() == ".csv":
            frame = pd.read_csv(source, usecols=[timestamp, value])
        else:
            raise ValueError("ad-hoc files must be CSV, TSV, or Parquet")
        index = pd.to_datetime(frame[timestamp], utc=True)
        values = pd.to_numeric(frame[value], errors="coerce")
        result = pd.Series(values.to_numpy(), index=index, name=name or value)
        return result.groupby(level=0).last().sort_index()

    def frame(
        self,
        queries: Mapping[str, str | pd.Series] | Sequence[str | pd.Series],
        *,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
        freq: str | None = None,
        join: str = "outer",
        fill: str | None = None,
        fill_limit: int | None = None,
    ) -> pd.DataFrame:
        """Align unlike calendars into one analysis frame."""
        if join not in {"outer", "inner"}:
            raise ValueError("join must be 'outer' or 'inner'")
        items = (
            queries.items()
            if isinstance(queries, Mapping)
            else (
                (query if isinstance(query, str) else query.name or f"series_{position}", query)
                for position, query in enumerate(queries)
            )
        )
        series = {}
        for name, query in items:
            if isinstance(query, str):
                value = self.get(query, start=start, end=end)
            elif isinstance(query, pd.Series):
                value = _utc_series(query)
                if start is not None:
                    value = value.loc[_utc_bound(start) :]
                if end is not None:
                    value = value.loc[: _utc_bound(end)]
            else:
                raise TypeError("frame values must be series-address strings or pandas Series")
            if freq:
                value = value.resample(freq).last()
            series[str(name)] = value
        result = pd.concat(series, axis=1, join=join).sort_index()
        if fill == "ffill":
            result = result.ffill(limit=fill_limit)
        elif fill == "bfill":
            result = result.bfill(limit=fill_limit)
        elif fill == "interpolate":
            result = result.interpolate(limit=fill_limit)
        elif fill is not None:
            raise ValueError("fill must be None, 'ffill', 'bfill', or 'interpolate'")
        return result

    def correlation(
        self,
        queries: Mapping[str, str | pd.Series] | Sequence[str | pd.Series],
        **kwargs: Any,
    ) -> pd.DataFrame:
        return self.frame(queries, **kwargs).corr()

    def regress(
        self,
        y: str | pd.Series,
        x: Mapping[str, str | pd.Series] | Sequence[str | pd.Series] | pd.Series | pd.DataFrame,
        *,
        add_constant: bool = True,
        hac_lags: int | str | None = "auto",
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
        freq: str | None = None,
        fill: str | None = None,
        fill_limit: int | None = None,
    ) -> RegressionResult:
        dependent = (
            self.get(y, start=start, end=end)
            if isinstance(y, str)
            else _slice_series(_utc_series(y), start, end)
        )
        if isinstance(x, pd.Series):
            independent = _slice_frame(_utc_series(x).to_frame(), start, end)
        elif isinstance(x, pd.DataFrame):
            independent = _slice_frame(_utc_frame(x), start, end)
        else:
            independent = self.frame(
                x,
                start=start,
                end=end,
                freq=freq,
                fill=fill,
                fill_limit=fill_limit,
            )
        if freq:
            dependent = dependent.resample(freq).last()
            if isinstance(x, (pd.Series, pd.DataFrame)):
                independent = independent.resample(freq).last()
        if isinstance(x, (pd.Series, pd.DataFrame)):
            independent = _fill_frame(independent, fill, fill_limit)
        return ols(dependent, independent, add_constant=add_constant, hac_lags=hac_lags)

    def plot(
        self,
        queries: Mapping[str, str | pd.Series] | Sequence[str | pd.Series],
        *,
        normalize: bool = False,
        title: str | None = None,
        **frame_options: Any,
    ) -> Any:
        """Return a Plotly figure that displays automatically in notebooks."""
        try:
            import plotly.express as px
        except ImportError as exc:
            raise RuntimeError("plotting requires `pip install 'algo-timeseries-lab[plot]'`") from exc
        data = self.frame(queries, **frame_options)
        if normalize:
            data = data.apply(_rebase)
        figure = px.line(data, x=data.index, y=list(data.columns), title=title)
        figure.update_layout(xaxis_title="", yaxis_title="Rebased to 100" if normalize else "Value")
        return figure


def _rebase(series: pd.Series) -> pd.Series:
    valid = series.dropna()
    return series / valid.iloc[0] * 100.0 if not valid.empty else series


def _utc_bound(value: str | pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")


def _utc_series(series: pd.Series) -> pd.Series:
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("ad-hoc Series must use a DatetimeIndex")
    result = series.copy()
    result.index = (
        result.index.tz_localize("UTC")
        if result.index.tz is None
        else result.index.tz_convert("UTC")
    )
    return result.sort_index()


def _utc_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("ad-hoc DataFrame must use a DatetimeIndex")
    result = frame.copy()
    result.index = (
        result.index.tz_localize("UTC")
        if result.index.tz is None
        else result.index.tz_convert("UTC")
    )
    return result.sort_index()


def _slice_series(
    series: pd.Series,
    start: str | pd.Timestamp | None,
    end: str | pd.Timestamp | None,
) -> pd.Series:
    if start is not None:
        series = series.loc[_utc_bound(start) :]
    if end is not None:
        series = series.loc[: _utc_bound(end)]
    return series


def _slice_frame(
    frame: pd.DataFrame,
    start: str | pd.Timestamp | None,
    end: str | pd.Timestamp | None,
) -> pd.DataFrame:
    if start is not None:
        frame = frame.loc[_utc_bound(start) :]
    if end is not None:
        frame = frame.loc[: _utc_bound(end)]
    return frame


def _fill_frame(
    frame: pd.DataFrame,
    fill: str | None,
    fill_limit: int | None,
) -> pd.DataFrame:
    if fill == "ffill":
        return frame.ffill(limit=fill_limit)
    if fill == "bfill":
        return frame.bfill(limit=fill_limit)
    if fill == "interpolate":
        return frame.interpolate(limit=fill_limit)
    if fill is not None:
        raise ValueError("fill must be None, 'ffill', 'bfill', or 'interpolate'")
    return frame
