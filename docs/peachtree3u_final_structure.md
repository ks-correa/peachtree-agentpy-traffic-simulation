# PEACHTREE-3U — FINAL STRUCTURAL REVISION AND FREEZE

**A. STRUCTURE_FROZEN_READY_FOR_FINAL_CALIBRATION**. Status **FROZEN**. Next phase: **PEACHTREE-4 FINAL B2 CALIBRATION**. No calibration performed here.

The methodological choice was explicitly predeclared by the user: use the existing3T INTERSECTION_ENTRY_REFERENCE as EFFECTIVE_SIGNAL_CONTROL_REFERENCE. This is the observable annotation boundary from adjacent approach section to intersection envelope. It is not a painted stop bar, physical stop bar or surveyed stop line. No coordinate was recomputed, optimized, chosen from queue-head output or subsequently shifted to improve fit. The original3T CSV is byte-hash pinned in code; references are an immutable mapping.

## 1–2. Effective references and legacy differences

| intersection | direction | EFFECTIVE_SIGNAL_CONTROL_REFERENCE | LEGACY_SIGNAL_PROXY | difference_ft | source | classification | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 649.846 | 632.539 | 17.307 | outputs/peachtree3t/intersection_envelopes.csv: entry | DATASET_DERIVED | Empirical adjacent-section to intersection annotation boundary; not a painted stop bar |
| 2 | 4 | 777.245 | 777.262 | -0.017 | outputs/peachtree3t/intersection_envelopes.csv: entry | DATASET_DERIVED | Empirical adjacent-section to intersection annotation boundary; not a painted stop bar |
| 3 | 2 | 1184.777 | 1168.916 | 15.861 | outputs/peachtree3t/intersection_envelopes.csv: entry | DATASET_DERIVED | Empirical adjacent-section to intersection annotation boundary; not a painted stop bar |
| 3 | 4 | 1241.529 | 1240.777 | 0.752 | outputs/peachtree3t/intersection_envelopes.csv: entry | DATASET_DERIVED | Empirical adjacent-section to intersection annotation boundary; not a painted stop bar |

Legacy proxies remain in all historical modes and in FINAL input provenance. The effective coordinates relocate the virtual signal leader; schedules, offsets, cycle/splits/yellow, units and integration are unchanged. Existing IDM and acceleration feasibility constraints govern braking. There is no zone-stop rule, speed reset or position clipping.

## 3. First queue heads REAL / SIM, by intersection/direction/lane

| intersection | direction | lane | sim_seed_median_mean | sim_seed_median_SD | n_seeds_x | real_median | real_SD | real_head_cycles | sim_minus_real_ft | final_head_median_mean | final_head_median_SD | n_seeds_y | FINAL_minus_REAL_ft |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 1 | 625.695 | 0.000 | 30 | 644.652 | 3.365 | 8 | -18.958 | 643.001 | 0.000 | 30 | -1.651 |
| 2 | 2 | 2 | 625.693 | 0.000 | 30 | 644.441 | 4.020 | 7 | -18.748 | 643.001 | 0.000 | 30 | -1.440 |
| 2 | 4 | 1 | 784.128 | 0.000 | 30 | 777.354 | 4.417 | 9 | 6.774 | 784.112 | 0.000 | 30 | 6.758 |
| 2 | 4 | 2 | 784.122 | 0.000 | 30 | 777.354 | 5.352 | 9 | 6.768 | 784.105 | 0.000 | 30 | 6.751 |
| 3 | 2 | 1 | 1162.069 | 0.000 | 30 | 1180.280 | 17.491 | 9 | -18.211 | 1177.930 | 0.000 | 30 | -2.350 |
| 3 | 2 | 2 | 1162.068 | 0.000 | 30 | 1184.431 | 3.551 | 9 | -22.363 | 1177.930 | 0.000 | 30 | -6.501 |
| 3 | 4 | 1 | 1247.636 | 0.003 | 30 | 1243.161 | 7.672 | 7 | 4.475 | 1248.387 | 0.003 | 30 | 5.226 |
| 3 | 4 | 2 | 1247.784 | 0.200 | 30 | 1248.548 | 13.375 | 5 | -0.764 | 1248.535 | 0.200 | 30 | -0.013 |

REAL uses the existing3T cycle-head observations; FINAL uses the median head position within each seed, then mean/SD across30 paired seeds. The preserved NEW head comparison is also included. Different lane-cycle counts and sparse outliers remain visible. These are diagnostics; references will not be moved to reduce these errors. Front=Local_Y. STOP_ZONE is preserved observational P10–P90 only. Association of Y1174–1192 NB with own12th extends through its envelope to1246.452, including positions after the effective entry; association does not imply a downstream force after crossing.

## 4–9. Paired metrics

| metric | REAL_B2 | NEW_REDUCED_SCOPE | FINAL_STRUCTURE | SD | CI95_low | CI95_high |
| --- | --- | --- | --- | --- | --- | --- |
| speed_mean_ft_s | 15.919 | 14.759 | 14.709 | 0.055 | 14.689 | 14.730 |
| speed_KS | 0.000 | 0.094 | 0.094 | 0.000 | 0.094 | 0.094 |
| speed_W1_ft_s | 0.000 | 1.328 | 1.370 | 0.052 | 1.350 | 1.389 |
| headway_mean_ft | 48.564 | 53.253 | 54.239 | 0.205 | 54.162 | 54.315 |
| headway_KS | 0.000 | 0.096 | 0.107 | 0.003 | 0.106 | 0.108 |
| headway_W1_ft | 0.000 | 5.924 | 6.732 | 0.166 | 6.670 | 6.794 |
| travel_mean_s | 54.162 | 58.393 | 58.397 | 0.230 | 58.311 | 58.483 |
| travel_W1_s | 0.000 | 4.235 | 4.236 | 0.229 | 4.150 | 4.321 |
| operational_stopped | 0.274 | 0.214 | 0.215 | 0.001 | 0.215 | 0.216 |
| stop_episodes | 319.000 | 233.600 | 234.533 | 2.662 | 233.539 | 235.527 |
| vehicles_stopped_fraction | 0.781 | 0.713 | 0.716 | 0.005 | 0.715 | 0.718 |
| complete_stop_duration_mean_s | 12.595 | 15.201 | 15.262 | 0.072 | 15.236 | 15.289 |
| stop_duration_W1_s | 0.000 | 2.790 | 2.832 | 0.056 | 2.811 | 2.852 |
| throughput_total | 274.000 | 274.000 | 274.000 | 0.000 | 274.000 | 274.000 |
| throughput_temporal_L1_normalized | 0.000 | 0.250 | 0.236 | 0.003 | 0.235 | 0.237 |
| queue_mean | 0.608 | 0.661 | 0.669 | 0.004 | 0.668 | 0.671 |
| queue_P90 | 2.000 | 2.133 | 2.967 | 0.183 | 2.898 | 3.035 |
| queue_max | 9 | 8.000 | 7.000 | 0.000 | 7.000 | 7.000 |
| queue_spatial_mean_ft | 12.157 | 13.559 | 13.867 | 0.078 | 13.838 | 13.896 |
| queue_spatial_P90_ft | 40.122 | 47.984 | 59.673 | 0.197 | 59.599 | 59.746 |
| release_mean_s | 1.671 | 1.600 | 1.600 | 0.000 | 1.600 | 1.600 |
| clearance_mean_s | 9.653 | 14.030 | 13.782 | 0.067 | 13.757 | 13.807 |
| residual_5s_mean | 0.157 | 0.507 | 0.485 | 0.012 | 0.480 | 0.489 |
| residual_10s_mean | 0.062 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| propagation_mean_s | 0.710 | 0.888 | 0.884 | 0.003 | 0.882 | 0.885 |
| section_travel_mean_s | 34.214 | 38.983 | 38.783 | 0.076 | 38.755 | 38.812 |
| queue_at_green_onset_mean | 2.137 | 3.331 | 3.346 | 0.022 | 3.338 | 3.355 |
| stopped_queue_clearance_mean_s | 2.582 | 3.563 | 3.673 | 0.020 | 3.666 | 3.681 |

Seeds3000–3029 are fixed, no selection. FINAL is30 fresh AgentPy rollouts. NEW baseline measurements are the preserved same-seed3S/3T results. REAL general speed/headway/travel/stopping use the frozen Through target cohort. REAL physical queue diagnostic uses all observed arterial class2/3 context; target-only sensitivity remains in3T. Queue means/P90/spatial extent use occupied-lane approach snapshots, not full-clock demand-normalized means; source coverage and omitted agents limit magnitude comparisons. Queue max is per lane. Complete stopped duration excludes censored episodes. Residual counts at5/10s preserve missing observations as missing, not zero. Queue discharge clearance is last initial RED-cohort member beyond empirical junction exit, whereas stopped clearance is first simultaneous all-moving snapshot. Separate residual/propagation files preserve both definitions and censoring. Aggregated30-seed CI is uncertainty of simulation mean, not uncertainty of REAL or methodological validity.

Section travel time uses crossings of approved control reference cuts: FINAL now uses effective cuts; NEW retains legacy cuts. Consequently part of the section-time difference is measurement-boundary change; it is not interpreted solely as traffic improvement. Throughput temporal discrepancy uses the same30s bins.274 exiting vehicles represent the observed cohort, not road capacity. Changes may improve or worsen individual metrics; the freeze criterion is not statistical perfection.

## 10–11. Physical invariants

All8 direct control tests passed: RED virtual restriction, first-head stop before reference, no numerical red crossing, GREEN release, correct NB increasing/SB decreasing coordinates, conservation, no overlap. All30 full-cohort runs pass conservation at every tick and no overlap; zero pending/remaining agents at end. A direction-specific RED NB/GREEN SB test additionally checks signal application. Existing physical guards still run every tick. No collision or conservation loss is concealed by statistical summaries.

## 12–15. QA, holdout, freeze and decision

The TRAIN runner retains all151 prior cases, adds FINAL-specific tests and writes outputs/peachtree3u/test_report.json. Actual-source historical fixtures remain skipped before setUpClass. Exact final totals are in that report. UI adds FINAL_STRUCTURE and Show effective control references, while retaining envelope/head toggles and all old modes. UI is a consumer of simulated AgentPy states. TEST B1 LOCKED; E1/E2/E3 disabled. **UI_IMPLEMENTED_NOT_BROWSER_VALIDATED**; AppTest/Canvas tests do not establish browser visual validation.

All previous phase outputs, reports and docs remain byte-identical. Only current UI code changes are intentional; preservation manifest/check is in3U. B1 was not accessed. Future validation retains the name TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.

`structural_model_freeze.json`: **FROZEN**. It records scope, boundaries, controls/schedules, dt, front semantics, arrivals/FIFO, release, states/rules, lane handling, queues/stopped/population, excluded mechanisms and source/code hashes. Runtime checks reject changed structural code or input signature. The five baseline IDM values remain at their original full precision; release remains1.6s and followers IDM only. No new delay or agents.

Remaining differences are **PARAMETRIC / MODEL DISCREPANCY** under this final modelling convention. Statistical mismatch does not authorize another structural review. Reopening requires a reproducible collision, conservation loss, wrong-direction signal, unit error or implementation bug. No PEACHTREE-3V, new geometric audit or painted-bar search is proposed. Stop here; next work is PEACHTREE-4 FINAL B2 CALIBRATION.

## Component provenance

| component | value/rule | classification | source |
| --- | --- | --- | --- |
| dt | 0.100 | DATASET_DERIVED | NGSIM10Hz; existing dt |
| effective control references | {'2/2': 649.846, '2/4': 777.245, '3/2': 1184.777, '3/4': 1241.529} | DATASET_DERIVED | 3T entry artifact; predeclared before3U SIM |
| signal schedules | Existing B2 RED/YELLOW/GREEN clock; no offsets/splits changes | DATASET_DERIVED | B2 exogenous signal inputs; official afternoon files |
| coordinate semantics | front=Local_Y; longitudinal center/rear projections | DATASET_DERIVED | Official metadata printed p13;3T |
| reduced scope | NB400→1346.452; SB1400→597.878 ft | DATASET_DERIVED | 3S frozen directional scope using B2 geometry/body clearance |
| initial snapshot/arrival requests | Existing B2 Through class2/3 cohort | DATASET_DERIVED | B2 exogenous inputs |
| entry speed samples | Existing B2 distributions with paired seeds | DATASET_DERIVED | B2 exogenous inputs |
| IDM v0/T/s0/a/b | {'v0': 12.511824704049223, 'T': 2.3561828489400907, 's0': 2.086210393921371, 'a': 2.6217268525153132, 'b': 2.625114577727408, 'delta': 4.0} | CALIBRATED | CALIBRATED_B2; original baseline full precision unchanged |
| IDM delta | 4.000 | LITERATURE_DERIVED | Existing IDM exponent convention |
| IDM acceleration/ballistic integration | Existing gap/speed law; simultaneous feasible acceleration constraint | LITERATURE_DERIVED | Existing VehicleAgent/IDM ballistic implementation |
| numerical feasibility guard | Constrain acceleration to available displacement; no position or speed reset | ASSUMPTION | Existing implementation safety rule |
| yellow handling | Latched comfortable-stop decision | ASSUMPTION | Existing yellow rule; no changes |
| green release delay | 1.600 | DATASET_DERIVED | B2 pooled simplification; no stratification |
| FIFO safe insertion | Preserve per direction/lane pending order and braking gap | ASSUMPTION | Existing3R correction |
| followers | IDM only; no added propagation delay | ASSUMPTION | Frozen model choice |
| main lanes/bay connector | Two normal lanes; only necessary safe lane11 merge | ASSUMPTION | Existing logical lane handling; sparse B2 lane-change sample |
| stopped | 0.100 | ASSUMPTION | Frozen external operational threshold in m/s |
| standstill queue gap | 4.941 | DATASET_DERIVED | Existing B2 stoodP90 |
| head selection window | 100.000 | ASSUMPTION | Inherited100ft window; observed-entry measurement |
| queue chain | First same-lane stopped head, Following where available, positive frozen-gap chain | ASSUMPTION | 3T reproducible measurement; observational lane0 recovery |
| observational stop zones | Preserved3T lane/cycle P10–P90 bands; no physical force | DATASET_DERIVED | 3T head distributions |
| receiving condition | Free removal at frozen direction-specific cuts | ASSUMPTION | 3S reduced boundary implementation |
| target-only population | Through class2/3; no Background Agents | ASSUMPTION | Frozen cohort modelling scope |
| future green split | NOT_IMPLEMENTED; E1/E2/E3 disabled | EXPERIMENTAL | Future scenario only, outside phase |
