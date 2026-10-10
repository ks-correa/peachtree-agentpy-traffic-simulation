# PEACHTREE-5 — TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE

**B. BASELINE_VALIDATED_WITH_LIMITATIONS**. Next: **PEACHTREE-6 SCENARIO EXPERIMENTATION**. No recalibration or scenario execution performed. This is temporal/acquisition holdout validation with acknowledged prior aggregate feasibility exposure, not blind/fully-unseen validation.

## 1–6. Inputs, seeds and immutable parameters

| acquisition | eligible_original_through_cohort | initial_vehicles | arrivals | modeled_vehicles | start_relative_s | start_frame | end_relative_s | horizon_s | signal_schedule_source | entry_speed_source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | 251 | 2 | 249 | 251 | 51.0000 | 515 | 1020.3000 | 969.3000 | B1 OBSERVED EXOGENOUS INPUT | Frozen TRAIN B2 boundary distributions; no B1 speed sample fit |

Initial snapshot and arrivals follow the TRAIN protocol: original eligible class2/3 Through cohort, same gate-event routing/interpolation/normal-lane fallback and body attributes. Start is earliest all-four known Through signal coverage plus the inherited TRAIN0.5s margin: B1 frame515, relative51s, end1020.3s, horizon969.3s. No frame chosen by fit. Directions retain NB400→1346.452 and SB1400→597.878. Controls retain649.846/777.245/1184.777/1241.529ft; no B1 estimate. Initial speeds use the single B1 snapshot. Future entry speeds retain the frozen B2 direction-specific pool, consistent with the permitted B1 input list and frozen arrival-speed policy; no B1 speed distribution fitted. Dimensions are necessary immutable body attributes. Source keys are audit-only, never trajectory handles.

Signals: **B1 OBSERVED EXOGENOUS INPUT**, official1245–0100 Through files for11th/12th NB/SB, with frame-relative mapping. B2 schedules are not copied. All source hashes are retained; original raw frame/time affine routing isolates B1 before numeric behavior parsing. Legacy B1 cohort/gate/CF artifacts are reused with their unchanged filters, not regenerated according to errors. Initial2 + arrivals249 = modeled251; eligible original Through cohort251.

Seeds6000–6029 were frozen before validation, disjoint from all development/TRAIN final seeds. Seed6000 is **ILLUSTRATIVE PREDECLARED SEED**; conclusions use all30 runs. Parameters unchanged: {'v0': 13.826974853949704, 'T': 1.98619700046232, 's0': 2.217577716840254, 'a': 3.060404045733389, 'b': 2.191487875232387}; delta4. Release remains its exact frozen value1.599999999999966s (reported1.6s), stopped0.1m/s, FIFO, lane handling, schedules-as-exogenous and queue definitions unchanged.

The frozen DemandStream constructor rejects acquisitions other than B2. A validation-only adapter supplies a private constructor token with the B1 exogenous payload, then immediately restores public provenance B1. No TRAIN guard/loader/code is modified and no B1 values enter fitting. Parent demand, signals, integration, VehicleAgent and reduced-boundary methods remain identical. A frozen-code measurement adapter binds only B1 signal inputs, with temporary identifier aliases to honor the original literal Following namespace; IDs are restored. These compatibility adapters do not supply real positions/speeds/accelerations after initialization or real exit times to agents.

## 7–18. REAL/SIM, errors, TRAIN versus holdout

| metric | TRAIN_REAL_B2 | TRAIN_SIM_B2 | VALIDATION_REAL_B1 | VALIDATION_SIM_B1 |
| --- | --- | --- | --- | --- |
| speed_mean_ft_s | 15.9189 | 16.1391 | 19.0228 | 19.3509 |
| speed_median_ft_s | nan | nan | 17.9400 | 17.5360 |
| speed_KS | 0.0000 | 0.0931 | 0.0000 | 0.2337 |
| speed_W1_ft_s | 0.0000 | 1.1321 | 0.0000 | 1.0502 |
| headway_mean_ft | 48.5637 | 52.3417 | 59.5521 | 74.7739 |
| headway_KS | 0.0000 | 0.0903 | 0.0000 | 0.1564 |
| headway_W1_ft | 0.0000 | 6.1405 | 0.0000 | 15.3614 |
| travel_mean_s | 54.1619 | 53.1033 | 46.3752 | 45.5224 |
| travel_median_s | nan | nan | 45.7350 | 44.4524 |
| travel_W1_s | 0.0000 | 2.1091 | 0.0000 | 1.4213 |
| operational_stopped | 0.2735 | 0.2563 | 0.3402 | 0.3170 |
| vehicles_stopped_fraction | 0.7810 | 0.7860 | 0.5100 | 0.5224 |
| stop_episodes | 319.0000 | 249.2667 | 204.0000 | 141.9000 |
| complete_stop_duration_mean_s | 12.5948 | 15.4617 | 19.2975 | 25.5547 |
| stop_duration_W1_s | 0.0000 | 3.1530 | 0.0000 | 7.0497 |
| section_travel_mean_s | 33.3779 | 36.2388 | 22.3522 | 25.4592 |
| throughput_total | 274.0000 | 274.0000 | 251.0000 | 251.0000 |
| throughput_temporal_L1_normalized | 0.0000 | 0.1555 | 0.0000 | 0.2130 |
| validation_summary_score | nan | nan | nan | 0.1399 |

| metric | REAL_B1 | mean | SD | CI95_low | CI95_high | absolute_error | relative_error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| speed_mean_ft_s | 19.0228 | 19.3509 | 0.1336 | 19.3010 | 19.4007 | 0.3281 | 0.0172 |
| speed_median_ft_s | 17.9400 | 17.5360 | 0.5141 | 17.3440 | 17.7280 | 0.4040 | 0.0225 |
| speed_KS | 0.0000 | 0.2337 | 0.0001 | 0.2336 | 0.2337 | 0.2337 | nan |
| speed_W1_ft_s | 0.0000 | 1.0502 | 0.0422 | 1.0344 | 1.0659 | 1.0502 | nan |
| headway_mean_ft | 59.5521 | 74.7739 | 0.7302 | 74.5012 | 75.0465 | 15.2218 | 0.2556 |
| headway_KS | 0.0000 | 0.1564 | 0.0063 | 0.1540 | 0.1587 | 0.1564 | nan |
| headway_W1_ft | 0.0000 | 15.3614 | 0.7018 | 15.0993 | 15.6234 | 15.3614 | nan |
| travel_mean_s | 46.3752 | 45.5224 | 0.3139 | 45.4052 | 45.6396 | 0.8528 | 0.0184 |
| travel_median_s | 45.7350 | 44.4524 | 1.0286 | 44.0683 | 44.8365 | 1.2826 | 0.0280 |
| travel_W1_s | 0.0000 | 1.4213 | 0.1550 | 1.3634 | 1.4792 | 1.4213 | nan |
| operational_stopped | 0.3402 | 0.3170 | 0.0026 | 0.3160 | 0.3179 | 0.0233 | 0.0684 |
| vehicles_stopped_fraction | 0.5100 | 0.5224 | 0.0075 | 0.5196 | 0.5253 | 0.0125 | 0.0245 |
| stop_episodes | 204.0000 | 141.9000 | 2.1870 | 141.0834 | 142.7166 | 62.1000 | 0.3044 |
| complete_stop_duration_mean_s | 19.2975 | 25.5547 | 0.3190 | 25.4356 | 25.6738 | 6.2571 | 0.3242 |
| stop_duration_W1_s | 0.0000 | 7.0497 | 0.2982 | 6.9384 | 7.1611 | 7.0497 | nan |
| section_travel_mean_s | 22.3522 | 25.4592 | 0.2853 | 25.3527 | 25.5658 | 3.1070 | 0.1390 |
| throughput_total | 251.0000 | 251.0000 | 0.0000 | 251.0000 | 251.0000 | 0.0000 | 0.0000 |
| throughput_temporal_L1_normalized | 0.0000 | 0.2130 | 0.0075 | 0.2102 | 0.2158 | 0.2130 | nan |
| validation_summary_score | nan | 0.1399 | 0.0039 | 0.1384 | 0.1413 | nan | nan |

Distributions report KS/W1; travel reports median/mean as well. Full errors remain exported. No percentage acceptance threshold. Section travel uses the same effective cuts and interpolation in both acquisitions. Headway retains the original cleaned CF/same-road/in-scope-leader methodology. Complete duration excludes left/right-censored episodes. Queue metrics use unchanged observational chains and real all-arterial context versus simulated TARGET population, so remain SECONDARY_DIAGNOSTIC, never acceptance or fitting objectives.

The B1 **VALIDATION SUMMARY SCORE** uses unchanged B2 weights, scales and normalization constants, with discrepancy numerators versus REAL B1. It is descriptive only; the B2 stopping/episode normalization and different acquisition exposure limit direct causal interpretation. No optimizer, parameter choice, weight change or model modification uses this score.

## 19. Systematic versus generalization discrepancies

| metric | TRAIN_B2_bias | VALIDATION_B1_bias | classification | interpretation |
| --- | --- | --- | --- | --- |
| speed_mean_ft_s | 0.2202 | 0.3281 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |
| headway_mean_ft | 3.7780 | 15.2218 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |
| travel_mean_s | -1.0585 | -0.8528 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |
| operational_stopped | -0.0172 | -0.0233 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |
| vehicles_stopped_fraction | 0.0050 | 0.0125 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |
| stop_episodes | -69.7333 | -62.1000 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |
| complete_stop_duration_mean_s | 2.8669 | 6.2571 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |
| section_travel_mean_s | 2.8609 | 3.1070 | SYSTEMATIC MODEL BIAS | Signs only; sizes and uncertainty retained, no arbitrary validation percentage |

The signs alone classify systematic bias; sizes and intervals are shown separately. Headway high, episodes low and complete stops long persist across acquisitions. B1 speed KS is substantially worse than TRAIN: real has an exact-zero mass whereas many simulated RED-stopped speeds remain positive near zero under IDM. Operational stopped is still exactly<=0.1m/s; no rounding or threshold change conceals that distribution discrepancy. This is a material limitation, not a physical collision or signal failure.

## 20–24. Temporal/emergent behavior, replicas, intervals and tests

All30 runs quantify accumulation, queue formation under RED, observed GREEN releases and clearances, collective speed variation, stop episodes and throughput. emergent_behavior_validation.csv contains every-seed queue-state evidence plus illustrative/source accumulation and repeated-stop counts. Graphs alone are not evidence. Temporal files contain10/30/60s RMSE/MAE/bias/correlation for speed, operational stopped, active vehicles and throughput; undefined correlations/empty speed bins remain missing. Equal251 throughput means demand closure, not capacity validation. The illustrative trace repeats predeclared seed6000 and is not another selection or independent replica.

Mean/SD/95%t CI across30 simulation seeds are in b1_simulation_summary.csv. CI quantifies simulation variability, not uncertainty of REAL. The189 prior tests are preserved. Historical mixed-source feasibility fixtures remain skipped when incompatible with the frozen validation protocol; TRAIN B1 fitting guards remain locked. New validation tests verify integrity, immutable parameters, no optimizer API, acquisition adapters/no replay, scope/metrics/seeds and physical invariants. QA: 205 total, 179 passed, 26 skipped, zero failures/errors. Exact details are in test_report.json.

## 25–29. Integrity, decision, limitations and next phase

Structural and calibration freeze files are byte-identical, verified before opening B1 and after execution. Parameters modified: **NO**. All prior output artifacts remain intact. Existing simulation and calibration files are unchanged; only new validation code and authorized UI updates are added. UI exposes VALIDACIÓN results with TRAIN B2 versus VALIDATION B1 and READ ONLY parameters; E1/E2/E3 are READY FOR NEXT PHASE but remain disabled/not implemented. UI_IMPLEMENTED_NOT_BROWSER_VALIDATED.

**B. BASELINE_VALIDATED_WITH_LIMITATIONS**: speed/travel magnitudes, operational stopping and signal/queue patterns provide useful within-scope compatibility, with significant distribution, headway and stopping episode/duration limitations. Conservation and no-overlap/negative-speed/finite-state checks pass in all30 runs. No qualitative physical failure is observed. This supports comparative experimentation under the frozen scope/assumptions, not full-network or absolute-capacity prediction.

Limitations:
- Headway too high in TRAIN and holdout; long-gap tail remains inaccurate
- Too few stopping episodes and overly long complete stops in both acquisitions
- B1 speed KS is affected by real exact-zero mass versus positive near-zero IDM speeds; operational threshold not changed
- Temporal flow useful but bin discrepancies remain; equal total throughput is demand closure, not capacity validation
- REAL queue context includes non-target arterial vehicles; secondary only
- Restricted Through class2/3 population, omitted turning/local streams and free receiving cuts
- Entry speeds use frozen B2 boundary pool, not newly estimated B1 speeds
- Prior feasibility-summary exposure; no blind or fully-unseen claim
- Comparative experiments only within frozen scope and stated assumptions; no full-network or absolute-capacity claim

NEXT = **PEACHTREE-6 SCENARIO EXPERIMENTATION**. Stop without recalibrating, changing structure/parameters or implementing E1/E2/E3 in this phase. B1 results are accepted as obtained.
