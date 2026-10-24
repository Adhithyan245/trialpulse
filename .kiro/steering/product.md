# TrialPulse
Wearable data for decentralized clinical trials. An AI agent drafts safety-signal
reports from participants' wearable readings and diaries; every report passes
through a reliability gate (PulseEval) before a human medical monitor sees it.

Users: medical monitor (reviews and approves reports), site coordinator
(device-wear compliance), trial sponsor (validation scorecard).

Non-negotiables:
- The AI never decides causality. Drug-to-event causality belongs to the investigator.
- Every claim in a report cites record_ids. Uncited claims are invalid.
- All participant data is synthetic and labelled "Synthetic data" on every screen.
- Public numbers (trials, environmental justice areas) come only from files in data/raw.
Non-goals: diagnosis, treatment advice, real patient data, real WHOOP accounts.
