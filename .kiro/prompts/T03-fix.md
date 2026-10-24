Task T03-fix: two small corrections.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/data/trials.py, tests/test_trials.py,
trialpulse/data/generator.py. Nothing else.

1. The real trials file also contains phase "EARLY_PHASE1" (39 trials), which currently
   falls into "Not stated". Add it to PHASE_LABELS as "Early Phase 1 (exploratory)", and
   add a test asserting that every distinct phase value in data/raw/trials/data.csv is a
   key of PHASE_LABELS (read the CSV with pandas, keep_default_na=False).
2. In trialpulse/data/generator.py, a comment still says "(P-07, P-23, days 12..28)";
   the participants are now P-07 and P-20. Fix the comment only.

When finished, list the files you changed and stop.
