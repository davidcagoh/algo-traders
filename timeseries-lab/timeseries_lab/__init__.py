"""Notebook-first access to the repository's shared time-series store."""

from timeseries_lab.catalog import AmbiguousSeries, SeriesNotFound, SeriesRef
from timeseries_lab.lab import TimeSeriesLab
from timeseries_lab.regression import RegressionResult

__all__ = [
    "AmbiguousSeries",
    "RegressionResult",
    "SeriesNotFound",
    "SeriesRef",
    "TimeSeriesLab",
]
