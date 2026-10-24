Task T03: loaders for the public portal data, plus the real statistics the app shows.

You cannot run shell commands or use the web in this project; the reviewer runs the code
and the tests. Everything you need is below. Use the stdlib (csv, json, urllib.request)
and pandas only; no new dependencies.

Files you may create: trialpulse/data/trials.py, trialpulse/data/context.py,
tests/test_trials.py, tests/test_context.py. Do not touch any other file. Files under
data/raw/ are read-only inputs.

Inputs (CSV, header row shown):
- data/raw/trials/data.csv: nct_id,title,phase,conditions,massachusetts_city,status
  3,131 rows. massachusetts_city is EMPTY on every row. phase values include PHASE1,
  PHASE2, PHASE3, PHASE4, "PHASE1, PHASE2", "PHASE2, PHASE3", NA, and empty.
  conditions is a comma-separated string.
- data/raw/ej/data.csv: municipality,population,minority_pct,limited_english_hh_pct,
  block_group_income,ej,criteria   (2,604 environmental-justice block groups)
- data/raw/places-sleep/data.csv: year,county,prevalence,low,high,population (14 counties)
- data/raw/readmissions/data.csv: facility_id,facility_name,measure,discharges,
  readmissions,excess_ratio,predicted_rate,expected_rate,start_date,end_date
  (excess_ratio may be "N/A" or empty; measure e.g. READM-30-HF-HRRP)

ClinicalTrials.gov API v2 (used for site cities). Request:
  GET https://clinicaltrials.gov/api/v2/studies?query.locn=Massachusetts
      &filter.overallStatus=RECRUITING&pageSize=1000&fields=NCTId,LocationCity,LocationState
      [&pageToken=<nextPageToken>]
Response JSON (verified today):
  {"totalCount": 3145, "nextPageToken": "...",   # nextPageToken absent on the last page
   "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT05663151"},
               "contactsLocationsModule": {"locations": [{"city": "Boston",
               "state": "Massachusetts"}]}}}]}
  A study may lack contactsLocationsModule or locations; treat that as no cities.

trialpulse/data/trials.py:
  RAW_TRIALS = "data/raw/trials/data.csv"; RAW_EJ = "data/raw/ej/data.csv"
  LOCATIONS_CACHE = "data/derived/trial_locations.json"
  PHASE_LABELS: dict mapping raw phase to plain language: PHASE1 "Phase 1 (first in
    people, safety)", PHASE2 "Phase 2 (does it work, dosing)", PHASE3 "Phase 3 (large
    confirmation)", PHASE4 "Phase 4 (after approval)", "PHASE1, PHASE2" "Phase 1/2",
    "PHASE2, PHASE3" "Phase 2/3", "NA" "Not applicable (device or behavioral)",
    "" "Not stated".
  WEARABLE_CONDITION_TERMS: tuple of lowercase substrings: "heart failure",
    "atrial fibrillation", "hypertension", "insomnia", "sleep", "copd", "asthma",
    "long covid", "post-acute", "obesity", "diabetes", "depression", "anxiety",
    "parkinson", "multiple sclerosis", "cardiovascular", "stroke", "fatigue",
    "chronic pain".
  load_trials(path=RAW_TRIALS) -> pandas.DataFrame with added columns phase_label and
    wearable_measurable (bool: any term is a substring of conditions.lower()).
  fetch_locations(fetch_json=None) -> dict[str, list[str]]: nct_id -> sorted unique
    Massachusetts city names (only locations whose state == "Massachusetts"). Follows
    nextPageToken until absent. fetch_json is a callable(url) -> dict; default uses
    urllib.request with a 30 s timeout and a User-Agent header. Raise on HTTP errors;
    never invent data.
  load_locations(refresh=False, fetch_json=None) -> dict: read LOCATIONS_CACHE if it
    exists and refresh is False; otherwise call fetch_locations, write the cache
    (create parent folders), and return it.
  public_metrics(trials_df, locations, ej_path=RAW_EJ) -> dict with keys:
    total_trials, by_phase (plain-language label -> count), wearable_measurable_trials,
    trials_with_ma_city (trials in trials_df that have >= 1 city in locations),
    top_cities (list of [city, trial_count], top 10), ej_block_groups,
    ej_municipalities (unique, case-insensitive), trials_in_ej_municipalities (trials with
    >= 1 site city that matches an EJ municipality, case-insensitive).

trialpulse/data/context.py:
  county_short_sleep(path="data/raw/places-sleep/data.csv") -> dict county -> prevalence
  readmission_summary(path="data/raw/readmissions/data.csv") -> dict with keys:
    hospitals (unique facility_id count), measures (dict measure -> {"with_ratio": n,
    "above_1": n}) counting only numeric excess_ratio, heart_failure_above_1 (count for
    READM-30-HF-HRRP with excess_ratio > 1).

Add to trials.py: build_public_metrics(out="data/derived/metrics_public.json",
  refresh=False) that loads everything, merges public_metrics with
  {"short_sleep_by_county": ..., "readmissions": ...} from context.py, writes the JSON
  (create folders) and returns the dict. Add `if __name__ == "__main__":` that calls it
  and prints the JSON.

Tests (no network: pass a fake fetch_json that returns two pages built from small dicts):
- load_trials on the real file: 3,131 rows; every phase maps to a label; at least one
  wearable_measurable row.
- fetch_locations follows nextPageToken across 2 fake pages, keeps only Massachusetts
  cities, de-duplicates, and handles a study with no contactsLocationsModule.
- load_locations writes and then reads the cache (use tmp_path; monkeypatch
  LOCATIONS_CACHE).
- public_metrics on a tiny hand-made DataFrame + locations + an EJ CSV in tmp_path gives
  exact expected counts, including case-insensitive city matching.
- county_short_sleep returns 14 counties with Hampden present; readmission_summary counts
  only numeric ratios (include a tmp CSV with an "N/A" row).

Done when the reviewer's pytest passes. When finished, list every file you changed and stop.
