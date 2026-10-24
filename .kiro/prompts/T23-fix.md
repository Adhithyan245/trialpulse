Task T23-fix: the sentence splitter breaks decimals.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
File you may edit: trialpulse/gate/tryit.py only.

Result: 7 passed, 1 failed (test_recompute_matches_cited_value_passes). The reviewer ran
run(trial, "P-07", 15, "HRV fell to 51.6 ms on day 12.") and got TWO claims:
  "HRV fell to 51."   (assessment, cites hrv_rmssd)
  "6 ms on day 12."   (value, cites resting_hr -> recompute fails "AI said 6 ms")
The split must happen only at . ! or ? that is followed by whitespace or the end of the
text (never inside a number such as 51.6 or 35.0). Use re.split(r"(?<=[.!?])\s+", text)
and drop empty parts. Do not change the tests. When finished, list the file and stop.
