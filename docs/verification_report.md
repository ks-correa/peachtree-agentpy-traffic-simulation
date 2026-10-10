# PEACHTREE-3 verification report

Decision: **B. BASELINE_NEEDS_REVISION**. Engine and conservation pass, but TRAIN stopping is strongly underestimated, mean headway is inflated and temporal throughput/section travel residuals remain. Continuous IDM rest vs source exact-zero measurement, omitted local interactions and simplified lane changes require TRAIN-only revision before B1.

| Indicator | Real B2 | Simulated mean (30 seeds) | SD | IC95 mean |
|---|---:|---:|---:|---|
| mean_speed_ft_s | 16.486892 | 16.439338 | 0.063178 | [16.415747, 16.462929] |
| mean_headway_ft | 48.563698 | 54.600038 | 0.207653 | [54.522499, 54.677576] |
| mean_travel_time_s | 60.758256 | 60.786095 | 0.244366 | [60.694847, 60.877343] |
| stopped_fraction | 0.099158 | 0.012859 | 0.000427 | [0.012700, 0.013019] |
| vehicles_exited | 274.000000 | 274.000000 | 0.000000 | [274.000000, 274.000000] |

## Engine and statistical checks

Real AgentPy subclasses and lifecycle are exercised, not a custom loop pretending
to be AgentPy. Synthetic A–H checks cover free acceleration, slow leader response,
red stopping before the reference, green release, nonoverlap, EXITED, identical
seed results and SI/dt consistency. Additional tests reject invalid initial
overlap, wrong dt, nonfinite parameters and unsafe insertion. Permuting agent
creation order produces the same spatial result. All ticks check conservation;
all30 final runs have21 initial+253 entered=274 exited, zero remaining/pending and
zero acceleration safety interventions. No negative speed or overlap exceptions.

57 evaluated candidates ×3 fixed development seeds =
171 rollouts, then30 fixed final seeds. Powell reached the prespecified
finite budget; this is not a global convergence guarantee. Each normalized error
is exported separately. Throughput totals agree but temporal-bin discrepancies
remain; total agreement alone is not fidelity. KS distances are descriptive,
not significance claims on autocorrelated repeated frames.

Full-route travel excludes initial agents. Separate post-search section diagnostic
uses the same two reference cuts: observed 34.214s,
simulated 37.741s,262 pairs each. This was
not an objective used to choose parameters. Section mismatch reinforces revision.

## Emergent numerical evidence

Maximum active population 35; maximum exactly-stopped
vehicles 8; maximum connected queue proxy
5; maximum negative-acceleration count
29. Signal-stopped/following/free-flow exposures
and changing collective speed are exported. Formation and release are numeric
series, not just an animation. Backward braking-wave causality has not been
established; spatial states and braking counts provide instrumentation.

## Tests and interface

87 collected: **61 passed, 26 skipped,
0 failures/errors**. All56 historical cases are retained, including the50 that
passed in the earlier phase.20 historical actual-source/mixed-metric cases are
now skipped before setUpClass to respect B1 closure, alongside6 prior unavailable
I80 cases.30 safe historical cases and31 new cases ran. Use
`python -m scripts.run_train_tests`; do not run legacy source fixtures unfiltered.

Streamlit AppTest passed rendering, TRAIN-only CSV paths, Run/Pause/Reset,
seed-triggered AgentPy execution, disabled E1/E2/E3 and visual-speed independence
from engine summaries. Canvas JavaScript executes with a mocked DOM/2D context,
updates playback cards and persists time via requestAnimationFrame. This is not
visual browser QA. Real browser inventory was empty; no screenshot or actual
browser rendering check could be completed. UI server runs locally on port8501.
The interface is implemented and component tested; visual fidelity is unverified.

## Revisions and methodological incidents

The first attempt failed on real initial B2 overlap before a successful rollout;
original freeze retained, explicit start/desired-speed amendment applied before
search. Road-transition quality-filter implementation corrected and same search
repeated; previous TRAIN artifacts retained. Serialization export failed on NumPy
int64 once, then was corrected; completed optimization and replicas were preserved.
After the final search only recorder columns were added; reference export was
rerun without tuning. Calibration and current code hashes are both retained.

An accidental shell header read of `peachtree_quality_filters.csv` displayed
legacy B1 filter rows. No B1 speed/headway/travel/throughput performance was opened
for development, no B1 data entered estimation or optimizer, and no B1 metrics
were loaded by Streamlit. This incident is disclosed instead of claiming zero
B1-derived material was ever displayed. B1 remains locked for model use. Hashing
mixed immutable source bytes is an integrity check, not behavioral analysis.

Yellow's comfortable-distance assumption was frozen before search. Detailed
TRAIN onset diagnostics came afterward:63 onset observations,18 yellow crossings.
This chronology does not identify an observed behavioral decision boundary; keep
yellow classified ASSUMPTION and audit it in a TRAIN-only revision.

## Limits and next decision

Stopped fraction is strongly understated. Continuous IDM approaches rest and
raw NGSIM contains exact-zero plateaus; distinguish source measurement semantics
from physical dwell before revising. This is a hypothesis, not an established
cause. Omitting local/turning streams and discretionary changes can also inflate
headways and alter discharge. Do not fix fit visually or choose a better seed.
Final CI covers RNG variability only, not model discrepancy. No arbitrary WAPE
acceptance threshold. Frozen hashes verified; scope/classes/intersections unchanged.

Remain in TRAIN revision. **Do not open B1 or implement E1/E2/E3.** Future
validation label: TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.
