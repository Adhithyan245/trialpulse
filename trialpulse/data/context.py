"""Loaders for the environmental context data: county short-sleep prevalence
and hospital readmission summaries. Stdlib + pandas only."""
from __future__ import annotations

import pandas as pd


def county_short_sleep(path: str = "data/raw/places-sleep/data.csv") -> dict:
    """Return county -> short-sleep prevalence (float)."""
    df = pd.read_csv(path)
    return {str(row["county"]): float(row["prevalence"]) for _, row in df.iterrows()}


def _to_float(value) -> float | None:
    s = str(value).strip()
    if s == "" or s.upper() == "N/A":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def readmission_summary(path: str = "data/raw/readmissions/data.csv") -> dict:
    """Summarize readmission data.

    Returns a dict with:
      hospitals: unique facility_id count
      measures: measure -> {"with_ratio": n, "above_1": n}, numeric ratios only
      heart_failure_above_1: count for READM-30-HF-HRRP with excess_ratio > 1
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    hospitals = df["facility_id"].nunique()

    measures: dict[str, dict] = {}
    heart_failure_above_1 = 0
    for _, row in df.iterrows():
        measure = row["measure"]
        ratio = _to_float(row["excess_ratio"])
        bucket = measures.setdefault(measure, {"with_ratio": 0, "above_1": 0})
        if ratio is not None:
            bucket["with_ratio"] += 1
            if ratio > 1:
                bucket["above_1"] += 1
                if measure == "READM-30-HF-HRRP":
                    heart_failure_above_1 += 1

    return {
        "hospitals": int(hospitals),
        "measures": measures,
        "heart_failure_above_1": int(heart_failure_above_1),
    }
