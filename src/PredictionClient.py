"""Utilities for working with prediction datasets and MT5 account state."""

from __future__ import annotations

import sys
import zlib
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Mapping

import polars as pl

from .PredictionParser import PredictionData, PredictionParser
from .mtBase import mtBase
from .common import magic_from


class PredictionClient:
    """High-level helper for loading predictions and related MT5 state."""

    def __init__(self, base: Optional[mtBase] = None, predictions_dir: Path | str = "predictions") -> None:
        self._base = base
        self._parser = PredictionParser(predictions_dir)
        self._predictions: List[PredictionData] = []
        self._sources: List[str] = []
        self._prediction_df: Optional[pl.DataFrame] = None
        self._latest_magic_map: Dict[str, int] = {}

    @property
    def base(self) -> mtBase:
        if self._base is None:
            raise RuntimeError("mtBase instance is required for MT5 operations.")
        return self._base

    @base.setter
    def base(self, value: mtBase) -> None:
        self._base = value

    def load_predictions(self, group: Optional[str] = None) -> List[PredictionData]:
        """Load all available predictions, optionally filtered by group."""
        files = self._parser.find_prediction_files(group)
        predictions: List[PredictionData] = []
        sources: List[str] = []

        for file_path in files:
            try:
                parsed = self._parser.parse_json_file(file_path)
            except Exception as exc:  # noqa: BLE001 - propagate feedback and continue
                print(f"Failed to parse {file_path}: {exc}", file=sys.stderr)
                continue

            predictions.extend(parsed)
            sources.extend([file_path.name] * len(parsed))

        self._predictions = predictions
        self._sources = sources
        self._prediction_df = None
        self._latest_magic_map = {}
        return predictions

    def predictions_to_frame(
        self,
        predictions: Optional[Sequence[PredictionData]] = None,
        include_source: bool = True,
    ) -> pl.DataFrame:
        """Convert predictions into a Polars DataFrame with derived metadata."""
        if predictions is None:
            predictions = self._predictions
            sources = self._sources if include_source else []
        else:
            sources = []

        if not predictions:
            self._prediction_df = pl.DataFrame()
            self._latest_magic_map = {}
            return self._prediction_df

        rows: List[Dict[str, object]] = []
        for idx, pred in enumerate(predictions):
            row: Dict[str, object] = {
                "symbol": pred.symbol,
                "last_training_day": pred.last_training_day.isoformat(),
                "last_close_price": pred.last_close_price,
                "n_trading_days": pred.n_trading_days,
                "score": pred.score,
                "sl_pct": pred.sl_pct,
                "tp_pct": pred.tp_pct,
                "magic": magic_from(pred.symbol, pred.last_training_day),
            }
            if include_source and predictions is self._predictions and idx < len(self._sources):
                row["source_file"] = self._sources[idx]
            rows.append(row)

        df = pl.DataFrame(rows)
        if not df.is_empty():
            df = df.with_columns(
                pl.col("last_training_day").strptime(pl.Date, fmt="%Y-%m-%d"),
                pl.col("magic").cast(pl.Int64),
            )

        self._prediction_df = df
        return df

    def latest_predictions(self, df: Optional[pl.DataFrame] = None) -> pl.DataFrame:
        """Return the newest training-day predictions, one row per symbol."""
        if df is None:
            df = self._prediction_df
        if df is None or df.is_empty():
            return pl.DataFrame()

        max_day = df.select(pl.col("last_training_day").max()).item()
        latest = df.filter(pl.col("last_training_day") == max_day)
        latest = latest.sort("score", descending=True)
        return latest

    def to_market_order_params(
        self,
        df: Optional[pl.DataFrame] = None,
        *,
        defaults: Optional[Mapping[str, object]] = None,
    ) -> List[Dict[str, object]]:
        """Return a list of dictionaries ready for ``place_market_order`` calls."""
        if df is None:
            df = self._prediction_df
        if df is None:
            raise ValueError("No prediction DataFrame available; supply df or call predictions_to_frame first.")
        if not isinstance(df, pl.DataFrame):
            raise TypeError("df must be a Polars DataFrame.")
        if df.is_empty():
            return []

        if defaults is not None and not isinstance(defaults, Mapping):
            raise TypeError("defaults must be a mapping of field names to values.")
        base_defaults = dict(defaults) if defaults else {}

        required_keys = ("symbol", "max_nom_value", "buy_sell", "magic")
        optional_keys = ("sl_pct", "tp_pct")
        allowed_keys = required_keys + optional_keys

        order_params: List[Dict[str, object]] = []

        for idx, row in enumerate(df.to_dicts()):
            params: Dict[str, object] = base_defaults.copy()
            for key in allowed_keys:
                value = row.get(key)
                if value is not None:
                    params[key] = value

            missing = [key for key in required_keys if params.get(key) in (None, "")]
            if missing:
                missing_str = ", ".join(missing).strip()
                raise ValueError(
                    f"Row {idx} is missing required place_market_order fields: {missing_str}."
                )
            
            order_params.append(params)

        return order_params
