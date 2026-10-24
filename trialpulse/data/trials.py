"""Loaders for the public ClinicalTrials.gov portal data and the real
statistics the app shows. Stdlib + pandas only."""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable

import pandas as pd

from trialpulse.data import context

RAW_TRIALS = "data/raw/trials/data.csv"
RAW_EJ = "data/raw/ej/data.csv"
LOCATIONS_CACHE = "data/derived/trial_locations.json"

PHASE_LABELS = {
    "PHASE1": "Phase 1 (first in people, safety)",
    "PHASE2": "Phase 2 (does it work, dosing)",
    "PHASE3": "Phase 3 (large confirmation)",
    "PHASE4": "Phase 4 (after approval)",
    "PHASE1, PHASE2": "Phase 1/2",
    "PHASE2, PHASE3": "Phase 2/3",
    "NA": "Not applicable (device or behavioral)",
    "EARLY_PHASE1": "Early Phase 1 (exploratory)",
    "": "Not stated",
}

WEARABLE_CONDITION_TERMS = (
    "heart failure",
    "atrial fibrillation",
    "hypertension",
    "insomnia",
    "sleep",
    "copd",
    "asthma",
    "long covid",
    "post-acute",
    "obesity",
    "diabetes",
    "depression",
    "anxiety",
    "parkinson",
    "multiple sclerosis",
    "cardiovascular",
    "stroke",
    "fatigue",
    "chronic pain",
)

_API_URL = (
    "https://clinicaltrials.gov/api/v2/studies?query.locn=Massachusetts"
    "&filter.overallStatus=RECRUITING&pageSize=1000"
    "&fields=NCTId,LocationCity,LocationState"
)


def load_trials(path: str = RAW_TRIALS) -> pd.DataFrame:
    """Load the trials CSV, adding phase_label and wearable_measurable columns."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df["phase_label"] = df["phase"].map(
        lambda p: PHASE_LABELS.get(p, PHASE_LABELS[""])
    )

    def _wearable(conditions: str) -> bool:
        low = (conditions or "").lower()
        return any(term in low for term in WEARABLE_CONDITION_TERMS)

    df["wearable_measurable"] = df["conditions"].map(_wearable)
    return df


def _default_fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "TrialPulse/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_locations(fetch_json: Callable[[str], dict] | None = None) -> dict:
    """Return nct_id -> sorted unique Massachusetts city names.

    Follows nextPageToken until absent. fetch_json is a callable(url) -> dict.
    """
    if fetch_json is None:
        fetch_json = _default_fetch_json

    result: dict[str, set] = {}
    page_token = None
    while True:
        url = _API_URL
        if page_token:
            url = url + "&pageToken=" + page_token
        data = fetch_json(url)
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            nct_id = ident.get("nctId")
            if not nct_id:
                continue
            cities = result.setdefault(nct_id, set())
            locations_module = protocol.get("contactsLocationsModule")
            if not locations_module:
                continue
            for loc in locations_module.get("locations", []) or []:
                if loc.get("state") == "Massachusetts":
                    city = loc.get("city")
                    if city:
                        cities.add(city)
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return {nct_id: sorted(cities) for nct_id, cities in result.items()}


def load_locations(
    refresh: bool = False, fetch_json: Callable[[str], dict] | None = None
) -> dict:
    """Read LOCATIONS_CACHE if present and not refreshing, else fetch and cache."""
    if not refresh and os.path.exists(LOCATIONS_CACHE):
        with open(LOCATIONS_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)

    locations = fetch_locations(fetch_json=fetch_json)
    os.makedirs(os.path.dirname(LOCATIONS_CACHE), exist_ok=True)
    with open(LOCATIONS_CACHE, "w", encoding="utf-8") as f:
        json.dump(locations, f, indent=2)
    return locations


def public_metrics(trials_df: pd.DataFrame, locations: dict, ej_path: str = RAW_EJ) -> dict:
    """Compute the public statistics the app shows."""
    total_trials = int(len(trials_df))

    by_phase: dict[str, int] = {}
    for label in trials_df["phase_label"]:
        by_phase[label] = by_phase.get(label, 0) + 1

    wearable_measurable_trials = int(trials_df["wearable_measurable"].sum())

    # city counts across trials present in trials_df
    nct_ids = set(trials_df["nct_id"])
    city_counts: dict[str, int] = {}
    trials_with_ma_city = 0
    for nct_id in trials_df["nct_id"]:
        cities = locations.get(nct_id) or []
        if cities:
            trials_with_ma_city += 1
        for city in cities:
            city_counts[city] = city_counts.get(city, 0) + 1

    top_cities = sorted(city_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    top_cities = [[city, count] for city, count in top_cities]

    # EJ data
    ej_df = pd.read_csv(ej_path, dtype=str, keep_default_na=False)
    ej_block_groups = int(len(ej_df))
    ej_muni_lower = {m.lower() for m in ej_df["municipality"] if m}
    ej_municipalities = len(ej_muni_lower)

    trials_in_ej_municipalities = 0
    for nct_id in trials_df["nct_id"]:
        cities = locations.get(nct_id) or []
        if any(c.lower() in ej_muni_lower for c in cities):
            trials_in_ej_municipalities += 1

    return {
        "total_trials": total_trials,
        "by_phase": by_phase,
        "wearable_measurable_trials": wearable_measurable_trials,
        "trials_with_ma_city": trials_with_ma_city,
        "top_cities": top_cities,
        "ej_block_groups": ej_block_groups,
        "ej_municipalities": ej_municipalities,
        "trials_in_ej_municipalities": trials_in_ej_municipalities,
    }


def build_public_metrics(
    out: str = "data/derived/metrics_public.json", refresh: bool = False
) -> dict:
    """Load everything, merge public_metrics with context data, write JSON, return it."""
    trials_df = load_trials()
    locations = load_locations(refresh=refresh)
    metrics = public_metrics(trials_df, locations)
    metrics["short_sleep_by_county"] = context.county_short_sleep()
    metrics["readmissions"] = context.readmission_summary()

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    return metrics


if __name__ == "__main__":
    print(json.dumps(build_public_metrics(), indent=2))
