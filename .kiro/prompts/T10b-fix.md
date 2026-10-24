Task T10b-fix: links_to_drug must ignore negated drug links.

You cannot run shell commands or use the web in this project; the reviewer runs the tests.
Files you may edit: trialpulse/gate/negative_control.py, tests/test_negative_control.py.
Nothing else. Keep all tests passing.

Seen in a real run: the final redraft claim "The pre-dose versus trial-wide comparison and
trial controls do not support a link between the observed physiological shifts and the
study drug." is held by negative_control. It DENIES a drug link, which is exactly the
correct statement, but links_to_drug matches words without polarity.

Fix: split the text into clauses with pulseeval.evaluation.text.clauses (installed;
signature clauses(answer: str) -> list[str]). A clause counts as a drug link only if it
contains an exposure term AND an outcome term AND is not negated. A clause is negated when
it contains any of these (case-insensitive, word boundaries): not, no, never, without,
cannot, unsupported, unrelated, unlikely, "no evidence", "not supported", "not
established", "does not", "do not", "did not", "is not", "are not", or any word ending in
"n't". links_to_drug is true when any clause is a non-negated drug link. Keep the
pre-dose phrase stripping from before.

Tests to add: the sentence above -> False; "There is no evidence that the study drug
caused the HRV drop." -> False; "HRV dropped after the study drug started, and this is not
due to sleep." -> True if the drug clause is not negated by the other clause (if clauses()
keeps them in one clause, assert whatever the implementation returns and leave a comment;
do not weaken the two required False cases); "Resting heart rate rose after the study drug
started." -> True.

When finished, list the files you changed and stop.
