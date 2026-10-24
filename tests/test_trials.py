import pandas as pd

from trialpulse.data import trials


def test_load_trials_real_file():
    df = trials.load_trials()
    assert len(df) == 3131
    # every phase maps to a label (no NaN / empty label)
    assert df["phase_label"].map(lambda v: isinstance(v, str) and v != "").all()
    # every label is one of the known labels
    known = set(trials.PHASE_LABELS.values())
    assert set(df["phase_label"]).issubset(known)
    # at least one wearable_measurable row
    assert df["wearable_measurable"].sum() >= 1


def test_all_phases_in_csv_are_known():
    """Every distinct phase value in data/raw/trials/data.csv is a key of PHASE_LABELS."""
    df = pd.read_csv(trials.RAW_TRIALS, dtype=str, keep_default_na=False)
    distinct_phases = set(df["phase"].unique())
    phase_keys = set(trials.PHASE_LABELS.keys())
    assert distinct_phases.issubset(phase_keys), f"Unknown phases: {distinct_phases - phase_keys}"


def _make_fetcher():
    page1 = {
        "nextPageToken": "TOKEN2",
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT0001"},
                    "contactsLocationsModule": {
                        "locations": [
                            {"city": "Boston", "state": "Massachusetts"},
                            {"city": "Boston", "state": "Massachusetts"},
                            {"city": "Providence", "state": "Rhode Island"},
                        ]
                    },
                }
            },
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT0002"},
                    # no contactsLocationsModule
                }
            },
        ],
    }
    page2 = {
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT0003"},
                    "contactsLocationsModule": {
                        "locations": [
                            {"city": "Cambridge", "state": "Massachusetts"},
                            {"city": "Worcester", "state": "Massachusetts"},
                        ]
                    },
                }
            }
        ],
    }

    calls = {"n": 0}

    def fetch_json(url):
        if "pageToken=TOKEN2" in url:
            return page2
        calls["n"] += 1
        return page1

    return fetch_json


def test_fetch_locations_follows_token_and_filters():
    locations = trials.fetch_locations(fetch_json=_make_fetcher())
    assert locations["NCT0001"] == ["Boston"]  # RI dropped, deduped
    assert locations["NCT0002"] == []  # no module
    assert locations["NCT0003"] == ["Cambridge", "Worcester"]


def test_load_locations_writes_then_reads(tmp_path, monkeypatch):
    cache = tmp_path / "derived" / "trial_locations.json"
    monkeypatch.setattr(trials, "LOCATIONS_CACHE", str(cache))

    first = trials.load_locations(fetch_json=_make_fetcher())
    assert cache.exists()
    assert first["NCT0001"] == ["Boston"]

    # second call reads cache; a fetcher that would raise must not be called
    def boom(url):
        raise AssertionError("should not fetch")

    second = trials.load_locations(fetch_json=boom)
    assert second == first


def test_public_metrics_exact_counts(tmp_path):
    df = pd.DataFrame(
        [
            {"nct_id": "NCT0001", "phase": "PHASE1", "conditions": "Heart Failure",
             "phase_label": trials.PHASE_LABELS["PHASE1"], "wearable_measurable": True},
            {"nct_id": "NCT0002", "phase": "PHASE1", "conditions": "Flu",
             "phase_label": trials.PHASE_LABELS["PHASE1"], "wearable_measurable": False},
            {"nct_id": "NCT0003", "phase": "PHASE3", "conditions": "Asthma",
             "phase_label": trials.PHASE_LABELS["PHASE3"], "wearable_measurable": True},
        ]
    )
    locations = {
        "NCT0001": ["Boston", "Cambridge"],
        "NCT0002": ["Boston"],
        "NCT0003": [],
    }
    ej = tmp_path / "ej.csv"
    ej.write_text(
        "municipality,population,minority_pct,limited_english_hh_pct,"
        "block_group_income,ej,criteria\n"
        "boston,100,10,0,50000,Yes,Income\n"
        "Boston,200,20,0,40000,Yes,Minority\n"
        "Lowell,300,30,0,30000,Yes,Income\n",
        encoding="utf-8",
    )

    m = trials.public_metrics(df, locations, ej_path=str(ej))
    assert m["total_trials"] == 3
    assert m["by_phase"] == {
        trials.PHASE_LABELS["PHASE1"]: 2,
        trials.PHASE_LABELS["PHASE3"]: 1,
    }
    assert m["wearable_measurable_trials"] == 2
    assert m["trials_with_ma_city"] == 2
    assert m["top_cities"] == [["Boston", 2], ["Cambridge", 1]]
    assert m["ej_block_groups"] == 3
    assert m["ej_municipalities"] == 2  # boston (case-insensitive) + lowell
    # NCT0001 and NCT0002 both have Boston which matches EJ (case-insensitive)
    assert m["trials_in_ej_municipalities"] == 2
