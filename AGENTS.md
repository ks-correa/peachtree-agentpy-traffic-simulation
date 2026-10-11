# Project continuity and frozen scientific results

Continue in this repository. Preserve all historical phases, including PEACHTREE-3 and PEACHTREE-3R. The current scientific decision is outputs/peachtree6/experiment_freeze.json: COMPLETED, recommended E1. Structure (3U), calibration (4) and validation (5) are frozen.

The user authorized and completed B1 validation and subsequent scenario evaluation. B1 remains prohibited for parameter fitting, model/boundary selection, threshold/offset design or behavioral tuning. Reading authorized frozen B1 results and saved states for presentation is allowed; this is not permission to recalibrate or run experiments.

Validation must retain the declaration:
TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.

Do not directly open mixed legacy reports or raw mixed CSVs for behavioral analysis. docs/peachtree_system_reconstruction.md and older feasibility reports contain prior B1 summaries. Prefer isolated B2 sources and frozen phase4/5/6 artifacts. Filename inventory and byte hashing are integrity actions. Do not print raw mixed rows.

For mixed legacy CSVs use simulation.training_data.read_train_csv, routing on B2 before parsing numerical behavior. calibration.structural.full_b2 returns the isolated B2 cache and rejects other acquisitions. Synthetic B1 fixture labels are not actual holdout observations.

Current work is UI, plotting, presentation exports and documentation only unless the user explicitly authorizes new scientific work. No IDM recalibration, threshold changes, offset fitting, stop-line shifts, trajectory replay, new scenarios or scientific-result rewrites. AgentPy and dt=0.1s remain authoritative. BASE/E1/E2/E3 are already implemented and evaluated; do not describe them as pending.

streamlit_app.py is the current entry point. Presentation and Technical modes use the shared complete simulation view and a light Canvas. The UI reproduces frozen seed7000 states; playback changes visual speed only. Current-run indicators and official 30-replica results remain visibly separate. Default demo window is 180s; Full uses the acquisition's official horizon.

For current UI verification run:

python -m scripts.qa_simulation_layout

Reports go under presentation_assets/. Keep scientific test reports intact; do not rerun scientific suites to verify documentation or UI edits. Never run unfiltered historical actual-source fixtures. If later scientific work is explicitly authorized, use the phase-appropriate guarded TRAIN runner; it skips incompatible mixed-source fixtures before setUpClass.

Do not commit the large original datasets excluded by .gitignore. Preserve local files. Historical scientific reports retain their phase-specific statuses; update README and current usage guides instead of rewriting history.
