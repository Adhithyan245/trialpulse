from trialpulse.data import context


def test_county_short_sleep_real_file():
    result = context.county_short_sleep()
    assert len(result) == 14
    assert "Hampden" in result
    assert result["Hampden"] == 38.4


def test_readmission_summary_counts_only_numeric(tmp_path):
    csv = tmp_path / "readm.csv"
    csv.write_text(
        "facility_id,facility_name,measure,discharges,readmissions,excess_ratio,"
        "predicted_rate,expected_rate,start_date,end_date\n"
        "1,Hosp A,READM-30-HF-HRRP,100,10,1.2,20,18,07/01/2021,06/30/2024\n"
        "1,Hosp A,READM-30-HF-HRRP,100,10,0.9,20,21,07/01/2021,06/30/2024\n"
        "2,Hosp B,READM-30-HF-HRRP,100,10,N/A,20,20,07/01/2021,06/30/2024\n"
        "2,Hosp B,READM-30-PN-HRRP,100,10,,20,20,07/01/2021,06/30/2024\n"
        "2,Hosp B,READM-30-PN-HRRP,100,10,1.5,20,18,07/01/2021,06/30/2024\n",
        encoding="utf-8",
    )
    summary = context.readmission_summary(str(csv))
    assert summary["hospitals"] == 2
    assert summary["measures"]["READM-30-HF-HRRP"]["with_ratio"] == 2
    assert summary["measures"]["READM-30-HF-HRRP"]["above_1"] == 1
    assert summary["measures"]["READM-30-PN-HRRP"]["with_ratio"] == 1
    assert summary["measures"]["READM-30-PN-HRRP"]["above_1"] == 1
    assert summary["heart_failure_above_1"] == 1
