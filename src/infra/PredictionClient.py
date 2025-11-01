"""Utilities for working with prediction datasets and MT5 account state."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Mapping, Tuple
from collections import deque
import polars as pl
import datetime

from .PredictionParser import PredictionData, PredictionParser
from .mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

class PredictionClient:
    """High-level helper for loading predictions and related MT5 state."""

    def __init__(self, base: mtBase, predictions_dir: Path | str = "predictions") -> None:
        self._base = base
        self._parser = PredictionParser(predictions_dir)
        self._predictions: List[PredictionData] = []
        self._prediction_df: Optional[pl.DataFrame] = None

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

        for file_path in files:
            try:
                parsed = self._parser.parse_json_file(file_path)
            except Exception as exc:  # noqa: BLE001 - propagate feedback and continue
                print(f"Failed to parse {file_path}: {exc}", file=sys.stderr)
                continue

            predictions.extend(parsed)

        self._predictions = predictions
        self._prediction_df = None
        return predictions

    def predictions_to_frame(
        self,
        predictions: Optional[Sequence[PredictionData]] = None,
    ) -> pl.DataFrame:
        """Convert predictions into a Polars DataFrame with derived metadata."""
        if predictions is None:
            predictions = self._predictions

        if not predictions:
            self._prediction_df = pl.DataFrame()
            return self._prediction_df

        rows: List[Dict[str, object]] = []
        for pred in predictions:
            row: Dict[str, object] = {
                "symbol": pred.symbol,
                "last_training_day": pred.last_training_day.isoformat(),
                "last_close_price": pred.last_close_price,
                "n_trading_days": pred.n_trading_days,
                "score": pred.score,
                "sl_pct": pred.sl_pct,
                "tp_pct": pred.tp_pct,
                "magic": pred.magic,
                "source_file": pred.source
            }
            rows.append(row)

        df = pl.DataFrame(rows)
        if not df.is_empty():
            df = df.with_columns(
                pl.col("last_training_day").strptime(pl.Date, fmt="%Y-%m-%d"),
                pl.col("magic").cast(pl.Int64),
            )

        self._prediction_df = df
        return df

    @staticmethod
    def latest_predictions(predictions: List[PredictionData]) -> List[PredictionData]:
        """Return the newest training-day predictions from a list of PredictionData objects."""
        if not predictions:
            return []

        # Find the maximum training day
        max_day = max(pred.last_training_day for pred in predictions)
        
        # Filter predictions to only include those with the maximum training day
        latest = [pred for pred in predictions if pred.last_training_day == max_day]
        
        # Sort by score in descending order
        latest.sort(key=lambda pred: pred.score, reverse=True)
        
        return latest

    def log_predictions(self, predictions: List[PredictionData] | PredictionData, indent: int = 2) -> None:
        indent_str = ' ' * indent
        if predictions is None or (isinstance(predictions, (list, tuple)) and not predictions):
            logger.info("No predictions to log.")
            return
        if not isinstance(predictions, (list, tuple)):
            predictions = [predictions]

        logger.info(f"{indent_str}Loaded {len(predictions)} predictions:")
        for i, pred in enumerate(predictions, 1):
            sym = getattr(pred, "symbol", None) or ""
            d   = getattr(pred, "last_training_day", None)
            d_s = "" if not d else (d.strftime("%d-%b-%Y") if isinstance(d, (datetime.date, datetime.datetime)) else str(d))
            p   = getattr(pred, "last_close_price", None); p_s = "" if p is None else f"{p:.4f}"
            n   = getattr(pred, "n_trading_days", None);   n_s = "" if n is None else str(n)
            s   = getattr(pred, "score", None);            s_s = "" if s is None else f"{s:.4f}"
            sl  = getattr(pred, "sl_pct", None);           sl_s = "" if sl is None else f"{sl:.2f}%"
            tp  = getattr(pred, "tp_pct", None);           tp_s = "" if tp is None else f"{tp:.2f}%"
            m   = getattr(pred, "magic", None) or ""
            src = getattr(pred, "source", None) or ""

            logger.info((
                f"\n{indent_str}Prediction {i}:"
                f"\n{indent_str}  Symbol: {sym}"
                f"\n{indent_str}  Last trading day: {d_s}"
                f"\n{indent_str}  Price: {p_s}"
                f"\n{indent_str}  N Trading Days: {n_s}"
                f"\n{indent_str}  Score: {s_s}"
                f"\n{indent_str}  SL%: {sl_s}"
                f"\n{indent_str}  TP%: {tp_s}"
                f"\n{indent_str}  Magic: {m}"
                f"\n{indent_str}  Source: {src}"
            ).strip())