# TRAIN calibration methodology

TRAIN=B2 only. B1 is locked for estimation, rule changes, optimization, visuals
and performance comparison. The future label is exactly:
TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.
This development phase is not validation.

## Freeze and amendments

The original scope freeze preceded all calibration. Original v1 is retained as
`outputs/baseline_scope_freeze_v1.json`. Frame931 had a true source same-lane
front-to-back overlap0.4328m; first collision-free snapshot under the declared
approach-lane carry is frame936 (93.4s). There was no successful original rollout.
v2 explicitly changed this start by0.5s and corrected the desired-speed sample:
the original no-leader GREEN median conflated queue starts with free flow.
`baseline_freeze_amendment_v2.json` records that decision before any successful
rollout. No positions were moved and no agents discarded. Scope, cohorts and
intersections were not changed. There are21 initial agents and253 later entries;
two of276 eligible TRAIN vehicles already left before the model starts. Window
ends1032.7s; horizon939.3s. Cut-to-cut targets exclude initial agents consistently.

The free-speed implementation initially omitted the already declared road lane
transition +/-1s filter. It was corrected, the old TRAIN calibration retained in
`outputs/archive/train_calibration_v2`, and the exact same finite search and30
final seeds repeated. `b2_quality_correction.json` records this correction.
No percentile was selected from an optimizer or visual result.

## Seeds and bounds

For v0 use the prespecified P85 of positive no-leader normal-lane road speed with
the next signal GREEN or no downstream controlled line. Exclude exact acceleration
saturation, global-coordinate kinematic jumps and road lane transitions +/-1s.
Bounds P50/P95; uncertain representativeness remains a limitation. Leader-gap
quality exclusions apply to CF samples, not to an explicitly leader-free sample.
T uses median valid reported Time_Headway for cleaned GREEN CF at/above median
strictly positive CF speed. It is a front-to-front seed, not identification of
net desired IDM time gap. s0 uses median positive clean standstill bumper gap.
a/b use median positive/absolute negative clean acceleration. Their bounds are
P10/P90. All five are then CALIBRATED, pooled classes2/3. Delta4 is
LITERATURE_DERIVED. Safe insertion and yellow decisions use the same parameters.

Raw source time epochs are not decoded; reconstructed frame-relative acquisition
time is used. Only routing metadata is read for non-B2 raw records before behavior
is parsed. Legacy mixed CSVs are routed by acquisition label before returning
TRAIN numerical values. Immutable source hashes are preserved.

## Objective

Fit aggregates, never position(t). Report separately:

1. absolute mean speed relative error;
2. full speed-distribution Wasserstein-1 / TRAIN speed IQR;
3. front-to-front headway Wasserstein-1 / TRAIN headway IQR;
4. absolute mean cut-to-cut travel time relative error;
5. absolute stopped-fraction difference;
6. exit histogram absolute residual sum / real total exits, bins30s.

Arithmetic mean of six dimensionless terms plus unfinished active/pending fraction.
This composite is transparent bookkeeping, not a validation threshold. Its equal
weights are a declared modeling assumption. Speed/stopping are vehicle-time
weighted; travel is vehicle weighted. Headways use cleaned CF in B2 and simulated
same-road-section normal-lane leaders with a downstream controlled line. These
samples are not matched trajectories; quality-selection differences can matter.
Queue proxy is a connected exactly-stopped lane chain, with positive net gap
bounded by TRAIN standstill P90. Numerical rest tolerance is1e-6m/s, not an
empirically identified perception threshold. This continuous IDM vs exact source
zero distinction is especially important for observed stopping mismatch.

## Search and uncertainty

Fixed development seeds10,11,12, scored by their mean. Candidate1 is the seed
estimate;16 deterministic Latin-hypercube points use seed20261009. Bounded Powell
then gets40 function evaluations on unit-scaled empirical bounds. Total57
candidates,171 development rollouts. The globally best evaluated parameter set
is retained, never a best seed. This is a finite local search, not proof of a
global optimum or uniquely identifiable parameters. Search plan is written before
evaluations; every candidate/seed/component/runtime/code hash is logged.

Final seeds1000–1029 are fixed in advance. Report mean, sample SD and two-sided
Student-t95% CI for the replicate mean. These intervals cover boundary-speed RNG
variation, not model discrepancy, source uncertainty or generalization. Reference
seed10 was fixed before fitting and is used for figures/UI, not selected by fit.
Full source/simulation samples are used for objectives; only UI ECDF point exports
are reduced to501 quantiles. Real boundary demand is an exogenous condition;
sampled boundary speeds are not historical internal evolution.

## Decision

Use magnitudes, distributions, temporal residuals, headway, travel, stopping,
conservation and safety together. No arbitrary WAPE cutoff. A strong unresolved
TRAIN mismatch stops the project before B1; scenarios remain unavailable.

## Sources

IDM: [Treiber et al.2000](https://arxiv.org/abs/cond-mat/0002177),
[author's equations and integration guide](https://mtreiber.de/MicroApplet/IDM.html).
AgentPy: [model lifecycle](https://agentpy.readthedocs.io/en/stable/reference_model.html),
[seeded generators](https://agentpy.readthedocs.io/en/stable/guide_random.html).
