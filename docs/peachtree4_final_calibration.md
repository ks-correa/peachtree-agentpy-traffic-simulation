# PEACHTREE-4 — Final B2 calibration and parameter freeze

**A. CALIBRATION_FROZEN_READY_FOR_B1_VALIDATION**. Calibration **FROZEN**. Structure3U **FROZEN and byte-identical**. Next phase: **PEACHTREE-5 VALIDATION B1**, not another calibration or structural audit. No B1 data accessed.

## 1–9. Bounds, search, objective, parameters, boundary audit and sensitivity

Bounds copied from existing B2-only parameter-estimation distributions before optimization. v0 P50/P95; other parameters P10/P90 of their documented samples. Physical positivity is respected; no literature bounds were invented because B2 provides ranges. The existing Time_Headway estimate is a front-to-front seed for the net-gap IDM T parameter, not direct identity; acceleration/braking distributions provide bounds, not perfect parameter identification.

| parameter | current_value | lower | upper | source | reason | classification | sample_n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v0 | 12.512 | 4.813 | 13.827 | outputs/b2_parameter_estimates.csv; existing B2 quantiles | Prespecified P85 positive speed of no-leader normal-lane road observations; next signal GREEN or no next signal; exclude saturation and kinematic jumps. P50/P95 bounds. Amendment before any successful rollout: original sample mostly starts, not free cruise.; positive physical range, unchanged prior empirical bounds | DATASET_DERIVED | 3453 |
| T | 2.356 | 1.550 | 4.530 | outputs/b2_parameter_estimates.csv; existing B2 quantiles | Median valid reported Time_Headway in cleaned moving GREEN CF sample at or above median strictly positive CF speed; front-to-front seed, then calibrated net-gap parameter; positive physical range, unchanged prior empirical bounds | DATASET_DERIVED | 12010 |
| s0 | 2.086 | 1.128 | 4.941 | outputs/b2_parameter_estimates.csv; existing B2 quantiles | Median positive cleaned CF bumper gap at exactly reported zero speed; positive physical range, unchanged prior empirical bounds | DATASET_DERIVED | 6390 |
| a | 2.622 | 0.049 | 3.417 | outputs/b2_parameter_estimates.csv; existing B2 quantiles | Median strictly positive nonsaturated cleaned CF acceleration; positive physical range, unchanged prior empirical bounds | DATASET_DERIVED | 10628 |
| b | 2.625 | 0.034 | 3.426 | outputs/b2_parameter_estimates.csv; existing B2 quantiles | Median absolute strictly negative nonsaturated cleaned CF acceleration; positive physical range, unchanged prior empirical bounds | DATASET_DERIVED | 13710 |

Evaluated parameter sets: **139**. Stage A40 reproducible Latin Hypercube points plus unchanged baseline; Stage B bounded Nelder-Mead from the best2 LHS candidates, at most50 calls each. Every set is scored on all5 development seeds **5000–5004**, using their arithmetic mean, never the best seed. All candidates and all seed/component outcomes remain in CSVs. Local budget termination is finite completion, not proof of global convergence. The final set is the minimum predeclared score among all valid evaluated sets; there is no manual/visual override or second calibration.

Final development objective: **0.08672011**. Six domains have equal1/6 weight. Components are normalized before averaging within domain: mean errors relative to REAL means; W1 by REAL IQR; KS by1; stopping/incidence/episode errors relative to REAL; flow by REAL departures. Scale/weight files were hashed before the first optimizer call and never changed. Queues have zero calibration weight because REAL context and SIM TARGET populations differ.

| component | error |
| --- | --- |
| component_speed_mean | 0.018 |
| component_speed_KS | 0.093 |
| component_speed_W1 | 0.039 |
| component_headway_mean | 0.080 |
| component_headway_KS | 0.091 |
| component_headway_W1 | 0.201 |
| component_travel_mean | 0.024 |
| component_travel_W1 | 0.105 |
| component_stopped_fraction | 0.069 |
| component_vehicles_stopped | 0.009 |
| component_stop_episodes | 0.219 |
| component_stop_duration_W1 | 0.176 |
| component_flow_histogram | 0.158 |
| component_flow_cumulative | 0.004 |
| component_section_mean | 0.083 |
| E_speed | 0.050 |
| E_headway | 0.124 |
| E_travel | 0.064 |
| E_stopping | 0.118 |
| E_temporal_flow | 0.081 |
| E_section_travel | 0.083 |

| parameter | PRE | FINAL |
| --- | --- | --- |
| v0 | 12.512 | 13.827 |
| T | 2.356 | 1.986 |
| s0 | 2.086 | 2.218 |
| a | 2.622 | 3.060 |
| b | 2.625 | 2.191 |

delta remains4. Release1.6s, effective references, schedules/offsets, FIFO, arrivals, scope, lanes, population, stopped0.1m/s and queue threshold remain unchanged. CheckedCalibrationModel delegates physical dynamics and adds invariant assertions only.

| parameter | value | lower | upper | unit_bound_position | BOUNDARY_HIT | rule |
| --- | --- | --- | --- | --- | --- | --- |
| v0 | 13.827 | 4.813 | 13.827 | 1.000 | UPPER | within0.1% of frozen interval; no expansion |
| T | 1.986 | 1.550 | 4.530 | 0.146 | NO | within0.1% of frozen interval; no expansion |
| s0 | 2.218 | 1.128 | 4.941 | 0.286 | NO | within0.1% of frozen interval; no expansion |
| a | 3.060 | 0.049 | 3.417 | 0.894 | NO | within0.1% of frozen interval; no expansion |
| b | 2.191 | 0.034 | 3.426 | 0.636 | NO | within0.1% of frozen interval; no expansion |

BOUNDARY_HIT means within0.1% of the frozen interval; this flags uncertainty and never expands bounds. Sensitivity is Spearman on the40 valid LHS points, excluding the locally clustered sample. Descriptor WELL/MODERATELY/WEAKLY_INFORMED uses max absolute parameter→domain/total correlation >=0.6 / >=0.3 / otherwise. These are exploratory search-response descriptors, not proof of unique or causal identification; p-values are descriptive, no multiple-comparison inference claimed.

| parameter | error_domain | Spearman_rho | p_value | n | classification |
| --- | --- | --- | --- | --- | --- |
| v0 | E_speed | -0.703 | 0.000 | 40 | WELL_INFORMED |
| v0 | E_headway | -0.195 | 0.229 | 40 | WELL_INFORMED |
| v0 | E_travel | -0.558 | 0.000 | 40 | WELL_INFORMED |
| v0 | E_stopping | -0.176 | 0.278 | 40 | WELL_INFORMED |
| v0 | E_temporal_flow | -0.600 | 0.000 | 40 | WELL_INFORMED |
| v0 | E_section_travel | -0.416 | 0.008 | 40 | WELL_INFORMED |
| v0 | objective | -0.595 | 0.000 | 40 | WELL_INFORMED |
| T | E_speed | 0.321 | 0.043 | 40 | MODERATELY_INFORMED |
| T | E_headway | 0.186 | 0.252 | 40 | MODERATELY_INFORMED |
| T | E_travel | 0.385 | 0.014 | 40 | MODERATELY_INFORMED |
| T | E_stopping | 0.494 | 0.001 | 40 | MODERATELY_INFORMED |
| T | E_temporal_flow | 0.339 | 0.033 | 40 | MODERATELY_INFORMED |
| T | E_section_travel | 0.343 | 0.030 | 40 | MODERATELY_INFORMED |
| T | objective | 0.479 | 0.002 | 40 | MODERATELY_INFORMED |
| s0 | E_speed | 0.331 | 0.037 | 40 | MODERATELY_INFORMED |
| s0 | E_headway | 0.258 | 0.107 | 40 | MODERATELY_INFORMED |
| s0 | E_travel | 0.310 | 0.051 | 40 | MODERATELY_INFORMED |
| s0 | E_stopping | 0.116 | 0.477 | 40 | MODERATELY_INFORMED |
| s0 | E_temporal_flow | 0.335 | 0.035 | 40 | MODERATELY_INFORMED |
| s0 | E_section_travel | 0.271 | 0.091 | 40 | MODERATELY_INFORMED |
| s0 | objective | 0.362 | 0.022 | 40 | MODERATELY_INFORMED |
| a | E_speed | -0.423 | 0.007 | 40 | MODERATELY_INFORMED |
| a | E_headway | 0.236 | 0.143 | 40 | MODERATELY_INFORMED |
| a | E_travel | -0.477 | 0.002 | 40 | MODERATELY_INFORMED |
| a | E_stopping | -0.305 | 0.055 | 40 | MODERATELY_INFORMED |
| a | E_temporal_flow | -0.516 | 0.001 | 40 | MODERATELY_INFORMED |
| a | E_section_travel | -0.460 | 0.003 | 40 | MODERATELY_INFORMED |
| a | objective | -0.508 | 0.001 | 40 | MODERATELY_INFORMED |
| b | E_speed | 0.410 | 0.009 | 40 | WELL_INFORMED |
| b | E_headway | -0.562 | 0.000 | 40 | WELL_INFORMED |
| b | E_travel | 0.519 | 0.001 | 40 | WELL_INFORMED |
| b | E_stopping | -0.293 | 0.066 | 40 | WELL_INFORMED |
| b | E_temporal_flow | -0.137 | 0.399 | 40 | WELL_INFORMED |
| b | E_section_travel | 0.648 | 0.000 | 40 | WELL_INFORMED |
| b | objective | 0.327 | 0.039 | 40 | WELL_INFORMED |

## 10–17. Primary REAL/PRE/FINAL metrics and tradeoffs

| metric | REAL_B2 | PRECALIBRATION | FINAL_CALIBRATED | absolute_change | relative_change | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| speed_mean_ft_s | 15.919 | 14.737 | 16.139 | 1.402 | 0.095 | CLOSER_TO_REAL |
| speed_W1_ft_s | 0.000 | 1.344 | 1.132 | -0.212 | -0.157 | LOWER_ERROR |
| speed_KS | 0.000 | 0.094 | 0.093 | -0.001 | -0.007 | LOWER_ERROR |
| headway_mean_ft | 48.564 | 54.322 | 52.342 | -1.981 | -0.036 | CLOSER_TO_REAL |
| headway_W1_ft | 0.000 | 6.818 | 6.141 | -0.678 | -0.099 | LOWER_ERROR |
| headway_KS | 0.000 | 0.108 | 0.090 | -0.018 | -0.164 | LOWER_ERROR |
| travel_mean_s | 54.162 | 58.283 | 53.103 | -5.180 | -0.089 | CLOSER_TO_REAL |
| travel_W1_s | 0.000 | 4.124 | 2.109 | -2.015 | -0.489 | LOWER_ERROR |
| operational_stopped | 0.274 | 0.215 | 0.256 | 0.041 | 0.192 | CLOSER_TO_REAL |
| vehicles_stopped_fraction | 0.781 | 0.716 | 0.786 | 0.070 | 0.098 | CLOSER_TO_REAL |
| stop_episodes | 319.000 | 234.300 | 249.267 | 14.967 | 0.064 | CLOSER_TO_REAL |
| complete_stop_duration_mean_s | 12.595 | 15.259 | 15.462 | 0.203 | 0.013 | FARTHER_FROM_REAL |
| stop_duration_W1_s | 0.000 | 2.828 | 3.153 | 0.325 | 0.115 | HIGHER_ERROR |
| section_travel_mean_s | 33.378 | 38.772 | 36.239 | -2.533 | -0.065 | CLOSER_TO_REAL |
| throughput_total | 274.000 | 274.000 | 274.000 | 0.000 | 0.000 | UNCHANGED |
| throughput_temporal_L1_normalized | 0.000 | 0.236 | 0.155 | -0.080 | -0.341 | LOWER_ERROR |
| cumulative_departure_mean_abs_normalized | 0.000 | 0.006 | 0.004 | -0.002 | -0.330 | LOWER_ERROR |
| objective | 0.000 | 0.137 | 0.086 | -0.051 | -0.374 | LOWER_ERROR |

REAL and SIM share frozen target cohort/scope/window for primary domains. Complete travel excludes initial agents; throughput includes them. Headway retains the existing cleaned same-lane/road definition and in-scope leader requirement. Stop durations use complete contiguous episodes, preserving censoring. Section travel is recomputed with the same effective cut pair and linear crossing interpolation for both REAL and SIM: historical3U section means used different REAL cuts and are not reused for this objective. This is a measurement-comparability correction, not a structural change.

absolute_change is signed FINAL−PRE; relative_change divides by PRE and is undefined when PRE=0. Improvement means lower KS/W1/temporal/objective errors, or a scalar closer to REAL. All worsened metrics remain visible. No10% pass threshold or TRAIN validation claim. Lower total objective can involve tradeoffs between domains.

## 18. Secondary queue diagnostics

| metric | REAL_B2 | PRECALIBRATION | FINAL_CALIBRATED | absolute_change | relative_change | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| queue_mean | 0.608 | 0.668 | 0.772 | 0.104 | 0.156 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| queue_P90 | 2.000 | 3.000 | 3.000 | 0.000 | 0.000 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| queue_max | 9.000 | 7.000 | 10.000 | 3.000 | 0.429 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| queue_spatial_mean_ft | 12.157 | 13.835 | 16.207 | 2.371 | 0.171 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| queue_spatial_P90_ft | 40.122 | 59.670 | 62.446 | 2.777 | 0.047 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| clearance_mean_s | 9.653 | 13.772 | 13.186 | -0.586 | -0.043 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| residual_5s_mean | 0.157 | 0.486 | 0.404 | -0.082 | -0.169 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| residual_10s_mean | 0.062 | 0.000 | 0.000 | 0.000 | NA | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| propagation_mean_s | 0.710 | 0.885 | 0.824 | -0.062 | -0.070 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| queue_at_green_onset_mean | 2.137 | 3.343 | 3.647 | 0.304 | 0.091 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |
| stopped_queue_clearance_mean_s | 2.582 | 3.674 | 3.580 | -0.094 | -0.025 | SECONDARY_DIAGNOSTIC_POPULATION_LIMIT |

Queue means/P90/extents use the unchanged3T observed occupied-lane snapshot definition. REAL all-observed arterial context differs from SIM TARGET; diagnostic differences cannot reopen structure. Green onset membership, stopped clearance, empirical-exit discharge clearance and residual5/10s retain source censoring and definitions. No queue threshold, band or follower delay was fitted.

## 19–23. Final TRAIN replications, temporal diagnostics, intervals and QA

30 FINAL runs use **4000–4029**, disjoint from development and unused for selection. An additional30 PRE runs use the same evaluation seeds for a paired comparison. Parameters are hash-locked before these rollouts and unchanged afterwards. Every rollout checks conservation, no overlap/negative speed, finite states/acceleration, valid signals/exits and reduced boundaries.30 final invariant results are in final_30_replica_runs.csv.

Mean/SD/t-based95% CI of simulation means are in final_30_replica_summary.csv, not confidence intervals for REAL or validation. Temporal comparison contains all60 PRE/FINAL seed results at10/30/60s for speed, operational stopped fraction, active vehicles and throughput, with RMSE/MAE/bias/correlation. Empty-clock speed/stopped fractions remain undefined; occupancy/throughput zero is meaningful. Correlation is undefined for constant/insufficient series. Final-seed4000 plots are a predeclared illustration, not selected by appearance; all30 numerical results remain available.

TRAIN tests retain all168 previous cases and add calibration-scope/freeze/seed/invariant tests. Final QA: 189 collected, 163 passed, 26 skipped, zero failures/errors. Exact details are in outputs/peachtree4/test_report.json. Historical actual-source fixtures remain skipped before setUpClass. UI shows final five parameters READ ONLY and BASELINE CALIBRATED — TRAIN B2; TEST B1 LOCKED, E1/E2/E3 disabled. UI_IMPLEMENTED_NOT_BROWSER_VALIDATED; automated checks do not establish visual browser validation.

## 24–28. Freeze, holdout and exit decision

Structural freeze intact: **YES**. Calibration freeze: **FROZEN**. B1 LOCKED: **YES**. All earlier artifacts/reports remain byte-identical; preservation manifest verifies this. Both freezes record hashes, values, rules, dates, bounds and seeds. The final parameters must not change during B1 validation. A worse B1 result will be a validation outcome, never permission to fit B1 or start another calibration.

**A. CALIBRATION_FROZEN_READY_FOR_B1_VALIDATION**. Next step: **PEACHTREE-5 VALIDATION B1**. Future validation must be titled **TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE**, acknowledging prior feasibility-summary exposure. Stop here without opening B1, implementing E1/E2/E3, modifying structure or executing a second calibration.
