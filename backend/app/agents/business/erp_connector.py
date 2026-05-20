"""ERP connector interface. The hackathon ships only the CSV implementation;
real connectors (Accurate, Jurnal.id, Xero) are deferred."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class CSVConnector:
    """Reads `year,free_cash_flow` rows from a CSV."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch_cashflows(self) -> list[float]:
        df = pd.read_csv(self._path)
        if "free_cash_flow" not in df.columns:
            raise ValueError("CSV must have a 'free_cash_flow' column")
        return df["free_cash_flow"].astype(float).tolist()
