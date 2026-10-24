Task T02-fix: correct a spec error in the generator and its tests.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/data/generator.py, tests/test_generator.py. Nothing else.

The T02 spec was wrong: with arms alternating A, B, A, ... P-23 is arm A, not B. The two
adverse-pattern participants must be in different arms. Replace P-23 with P-20 everywhere
(P-20 is site S02, arm B, not on the non-wear site): the adverse_pattern event, its
ground_truth entry, and every test that mentions P-23. Keep the arm assignment rule as it
is. Current result: 27 passed, 1 failed (test_forty_participants_sites_and_arms asserts
P-23 is arm B). Change nothing else. When finished, list the files you changed and stop.
