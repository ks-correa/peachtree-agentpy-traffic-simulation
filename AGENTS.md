# Project data access and phase continuity

Continue in this repository; preserve PEACHTREE-3 and PEACHTREE-3R artifacts.
Current phase decision is in outputs/peachtree3s/decision.json.

B1 remains locked unless the user explicitly authorizes a later validation phase.
Never use B1 for parameter fitting, model/boundary selection, diagnostics or visual
tuning. Do not directly open mixed legacy reports, CSVs or markdown summaries:
docs/peachtree_system_reconstruction.md and older feasibility reports contain B1
behavioral summaries. Prefer the B2-only phase3R/3S artifacts and the official
afternoon 0400pm-0415pm documents. Inventorying filenames and hashing bytes are
integrity actions, not behavioral analysis.

Use simulation.training_data.read_train_csv for mixed legacy CSVs: route on B2
before parsing numerical behavior. calibration.structural.full_b2 returns the
isolated B2 cache and rejects other acquisitions. Do not print raw mixed dataset
rows. Synthetic B1 labels in unit fixtures are not actual holdout data.

For the current suite, run:

python -m scripts.run_train_tests --report outputs/peachtree3s/test_report.json

Never run unfiltered historical actual-source fixtures: the TRAIN runner skips
them before setUpClass to protect the holdout. Keep prior test reports intact.

No IDM recalibration, threshold changes, offset fitting, arbitrary stop-line
shifts, trajectory replay or E1/E2/E3 implementation in this phase. AgentPy and
dt=0.1s remain authoritative. Directional reduced scope is a separate mode; UI
limits await boundary approval. Future validation must be described as:
TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.
