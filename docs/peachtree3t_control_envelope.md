# PEACHTREE-3T — Controlled envelope / queue head reconstruction

Decision: **B. NEEDS_STRUCTURAL_REVISION**. Remaining discrepancy: **STRUCTURAL**. No final IDM calibration, B1 validation or scenarios authorized by this result. `structural_model_freeze.json` explicitly says NOT_FROZEN.

1. Local_Y is the longitudinal front-center coordinate in feet (official Peachtree metadata attribute definition, printed page13); Local_X is its lateral coordinate. Neither is the vehicle centroid.
2. Front=Local_Y; center=Y−sign·length/2; rear=Y−sign·length. NB sign+1, SB−1. Rear/center are straight longitudinal projections; turning geometry is not reconstructed from length alone.
3. First physical stopped heads, separate intersection/direction/lane groups:

| intersection | direction | lane | n | n_cycles | median | SD | P10 | P90 | IQR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 1 | 8 | 8 | 644.652 | 3.365 | 641.291 | 649.130 | 4.353 |
| 2 | 2 | 2 | 7 | 7 | 644.441 | 4.020 | 640.363 | 648.915 | 4.663 |
| 2 | 4 | 1 | 9 | 9 | 777.354 | 4.417 | 772.502 | 780.043 | 1.282 |
| 2 | 4 | 2 | 9 | 9 | 777.354 | 5.352 | 774.427 | 781.925 | 0.000 |
| 3 | 2 | 1 | 9 | 9 | 1180.280 | 17.491 | 1167.678 | 1184.410 | 3.739 |
| 3 | 2 | 2 | 9 | 9 | 1184.431 | 3.551 | 1182.243 | 1189.355 | 5.833 |
| 3 | 4 | 1 | 7 | 7 | 1243.161 | 7.672 | 1236.654 | 1253.580 | 10.151 |
| 3 | 4 | 2 | 5 | 5 | 1248.548 | 13.375 | 1233.948 | 1260.871 | 21.520 |

Same-control/lane REAL versus30-seed SIM head positions (median per seed before averaging; no inter-junction pooling):

| intersection | direction | lane | sim_seed_median_mean | sim_seed_median_SD | n_seeds | real_median | real_SD | real_head_cycles | sim_minus_real_ft |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 1 | 625.695 | 0.000 | 30 | 644.652 | 3.365 | 8 | -18.958 |
| 2 | 2 | 2 | 625.693 | 0.000 | 30 | 644.441 | 4.020 | 7 | -18.748 |
| 2 | 4 | 1 | 784.128 | 0.000 | 30 | 777.354 | 4.417 | 9 | 6.774 |
| 2 | 4 | 2 | 784.122 | 0.000 | 30 | 777.354 | 5.352 | 9 | 6.768 |
| 3 | 2 | 1 | 1162.069 | 0.000 | 30 | 1180.280 | 17.491 | 9 | -18.211 |
| 3 | 2 | 2 | 1162.068 | 0.000 | 30 | 1184.431 | 3.551 | 9 | -22.363 |
| 3 | 4 | 1 | 1247.636 | 0.003 | 30 | 1243.161 | 7.672 | 7 | 4.475 |
| 3 | 4 | 2 | 1247.784 | 0.200 | 30 | 1248.548 | 13.375 | 5 | -0.764 |

4. Each head/cycle contributes one median position, not hundreds of independent frames. Within-cycle SD, between-cycle variance and outliers are saved. All groups have only5–9 cycles. 12th NB lane1 includes a distant sparse-queue head; it is retained as an outlier, not used to infer a painted stop bar. Repeated identical SB coordinates also require caution about source coding/position precision. Outlier labels use1.5IQR; IQR=0 can make several distinct values flagged. No positions were deleted to improve SIM fit.
5. P10–P90 observational head bands are STOP_ZONE candidates, not physically identified stop points. Bands are classification only; no vehicle is stopped, clipped or fixed because it is inside one. Sample sizes do not establish a surveyed lane-specific reference.
6–7. 11th/12th observational envelopes:

| intersection | direction | lane | approach_start | entry | exit | discharge_end | stop_low | stop_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 1 | 400.000 | 649.846 | 777.753 | 1172.939 | 641.291 | 649.130 |
| 2 | 2 | 2 | 400.000 | 649.846 | 777.753 | 1172.939 | 640.363 | 648.915 |
| 2 | 4 | 1 | 1172.939 | 777.245 | 647.878 | 597.878 | 772.502 | 780.043 |
| 2 | 4 | 2 | 1172.939 | 777.245 | 647.878 | 597.878 | 774.427 | 781.925 |
| 3 | 2 | 1 | 777.753 | 1184.777 | 1246.452 | 1346.452 | 1167.678 | 1184.410 |
| 3 | 2 | 2 | 777.753 | 1184.777 | 1246.452 | 1346.452 | 1182.243 | 1189.355 |
| 3 | 4 | 1 | 1400.000 | 1241.529 | 1172.939 | 777.753 | 1236.654 | 1253.580 |
| 3 | 4 | 2 | 1400.000 | 1241.529 | 1172.939 | 777.753 | 1233.948 | 1260.871 |

ENTRY uses B2 adjacent section→intersection transition median. EXIT uses B2 annotation extent. APPROACH begins at the preceding observed junction exit or frozen ingress. DISCHARGE extends to the next observed junction entry/retained exit. These are annotation envelopes, not lane centerline surveys. INTERSECTION_ENTRY_REFERENCE, INTERSECTION_EXIT_REFERENCE, SIGNAL_CONTROL_REFERENCE and QUEUE_HEAD_REFERENCE remain distinct. STOP bands can overlap annotated interior; zone labels prioritize interior rather than concealing overlap.
8. Y1174–1192 NB is below the own12th exit1246.452 and lies across the observed road/int coding seam. Heads above1168.9155 are observed under own12th RED; using next_line at that proxy reassigns control too soon. Raw int/section/movement/source lane, front, head/follower flags are in problem_12th_NB_frames.csv; no inference from appearance was used. Unrecoverable lane0 remains OUTSIDE/unknown, not reassigned arbitrarily. Summary:

| phase | source_lane | int_id | section_id | movement | frames |
| --- | --- | --- | --- | --- | --- |
| GREEN | 0 | 3 | 0 | 1 | 633 |
| GREEN | 1 | 0 | 3 | 1 | 276 |
| GREEN | 2 | 0 | 3 | 1 | 274 |
| RED | 0 | 3 | 0 | 1 | 1425 |
| RED | 1 | 0 | 3 | 1 | 1674 |
| RED | 2 | 0 | 3 | 1 | 1543 |
| UNCONTROLLED | 0 | 3 | 0 | 1 | 7 |
| UNCONTROLLED | 0 | 3 | 0 | 2 | 1556 |
| UNCONTROLLED | 0 | 3 | 0 | 3 | 9 |
| UNCONTROLLED | 11 | 0 | 3 | 1 | 441 |
| YELLOW | 0 | 3 | 0 | 1 | 33 |
| YELLOW | 1 | 0 | 3 | 1 | 19 |
| YELLOW | 2 | 0 | 3 | 1 | 17 |

9. GREEN stopped vehicle-frame classification:

| classification | vehicle_frames |
| --- | --- |
| A_RESIDUAL_PREVIOUS_RED | 2413 |
| B_BLOCKED_BY_STOPPED_LEADER | 2717 |
| E_UNKNOWN | 2229 |

A requires membership in the previous RED onset cohort and no earlier movement onset. B requires an observed same-lane/direction stopped leader; C is an incompatible turn/local movement. D requires a stopped leader in the retained discharge zone; E preserves unknown cause. This is association, not causal proof. No green=free-flow assumption.
10–12. Initial RED queue membership is frozen at GREEN−0.1s. Release is movement onset >0.1m/s with contiguous tracking; stopped-queue clearance is the first simultaneous all-moving snapshot; discharge clearance is the last initial member past observational junction EXIT. Missing traces/crossings are censored, never filled with zero. Snapshot discharge timing has0.1s resolution. Means:

| series | queue_at_green_onset | time_to_first_release_s | time_to_stopped_queue_clearance_s | time_to_queue_clearance_s | remaining_stopped_after_5s | remaining_stopped_after_10s |
| --- | --- | --- | --- | --- | --- | --- |
| NEW_REDUCED_SCOPE | 3.331 | 1.600 | 3.563 | 14.029 | 0.507 | 0.000 |
| REAL_B2 | 2.137 | 1.671 | 2.582 | 9.653 | 0.157 | 0.062 |

13. Existing1.6s pooled release is retained. Group samples are5–8 valid releases; differing medians are candidates for future study, not fitted strata. Neither the B2 head band nor these delays supplies a physical stop bar:

| intersection | direction | lane | n | median | P25 | P75 | IQR | policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 1 | 8 | 1.350 | 1.000 | 1.625 | 0.625 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |
| 2 | 2 | 2 | 5 | 0.900 | 0.700 | 1.900 | 1.200 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |
| 2 | 4 | 1 | 7 | 1.200 | 0.700 | 1.750 | 1.050 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |
| 2 | 4 | 2 | 7 | 0.600 | 0.350 | 1.450 | 1.100 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |
| 3 | 2 | 1 | 6 | 1.000 | 0.375 | 1.250 | 0.875 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |
| 3 | 2 | 2 | 7 | 1.100 | 0.550 | 1.550 | 1.000 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |
| 3 | 4 | 1 | 6 | 2.600 | 1.900 | 3.000 | 1.100 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |
| 3 | 4 | 2 | 5 | 2.100 | 1.800 | 3.700 | 1.900 | KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE |

14–15. START-UP PROPAGATION (follower onset minus leader onset), never cognitive reaction time:

| series | count | mean | median | std |
| --- | --- | --- | --- | --- |
| NEW_REDUCED_SCOPE | 3912 | 0.888 | 0.900 | 0.304 |
| REAL_B2 | 58 | 0.710 | 0.550 | 1.092 |

Negative lags are retained as observations, not clipped. This audit does not establish a stable gap-conditioned mechanism independent of IDM, so no propagation hold was added.
16. Main structural discrepancy: a point proxy loses own-intersection association while real front heads remain controlled, especially12th NB. HIGH confidence for association/measurement error; insufficient independent evidence for the replacement physical signal reference.
17. Physical references modified: NO. Current632.5395/777.262 (11th NB/SB) and1168.9155/1240.7775 (12th NB/SB) remain unchanged; their physical validity is unresolved. No mouth/head median was substituted as a stop bar.
18. Implemented immutable SignalControlEnvelope, front/rear semantics, contiguous bracketing lane0 recovery, front-most stopped chain using Following/spatial gap, cycle head bands, residual/release/discharge/propagation diagnostics and rendering overlays. All physics remain existing AgentPy. CONTROL_ENVELOPE_REVISION is a measurement-only mode consuming the identical NEW_REDUCED_SCOPE state stream; no claimed dynamic correction.
19–26. Paired seeds3000–3029: 90 new diagnostic rollouts of existing modes. General metrics come from preserved3S same-seed/same-scope results, avoiding duplicate calculations; queue dynamics are remeasured in3T. The30 revision rows share the exact NEW state stream by construction, explicitly tagged, not represented as an independent experiment. Before/after physical metrics are identical, and no success is claimed from measurement relabeling:

| metric | CONTROL_ENVELOPE_REVISION | NEW_REDUCED_SCOPE | OLD | REVISED | REAL_B2 |
| --- | --- | --- | --- | --- | --- |
| speed_mean_ft_s | 14.759 | 14.759 | 15.061 | 14.569 | 15.919 |
| speed_KS | 0.094 | 0.094 | 0.100 | 0.094 | 0.000 |
| speed_W1_ft_s | 1.328 | 1.328 | 1.182 | 1.543 | 0.000 |
| headway_mean_ft | 53.253 | 53.253 | 57.431 | 55.975 | 48.564 |
| headway_KS | 0.096 | 0.096 | 0.109 | 0.097 | 0.000 |
| headway_W1_ft | 5.924 | 5.924 | 9.224 | 8.068 | 0.000 |
| travel_mean_s | 58.393 | 58.393 | 57.192 | 59.155 | 54.162 |
| travel_W1_s | 4.235 | 4.235 | 3.197 | 4.994 | 0.000 |
| operational_stopped | 0.214 | 0.214 | 0.199 | 0.211 | 0.274 |
| vehicles_stopped_fraction | 0.713 | 0.713 | 0.679 | 0.713 | 0.781 |
| stop_episodes | 233.600 | 233.600 | 217.833 | 233.600 | 319.000 |
| complete_stop_duration_mean_s | 15.201 | 15.201 | 14.708 | 15.201 | 12.595 |
| stop_duration_W1_s | 2.790 | 2.790 | 2.556 | 2.790 | 0.000 |
| queue_mean | 0.661 | 0.661 | 0.610 | 0.657 | 0.608 |
| queue_P90 | 2.133 | 2.133 | 2.000 | 2.000 | 2.000 |
| queue_max | 8.000 | 8.000 | 8.000 | 8.000 | 9.000 |
| queue_spatial_mean_ft | 13.559 | 13.559 | 12.481 | 13.469 | 12.157 |
| residual_5s_mean | 0.507 | 0.507 | 0.222 | 0.507 | 0.157 |
| residual_10s_mean | 0.000 | 0.000 | 0.000 | 0.000 | 0.062 |
| clearance_mean_s | 14.030 | 14.030 | 12.881 | 14.262 | 9.653 |
| propagation_mean_s | 0.888 | 0.888 | 0.879 | 0.888 | 0.710 |
| throughput_total | 274.000 | 274.000 | 274.000 | 274.000 | 274.000 |
| throughput_temporal_L1_normalized | 0.250 | 0.250 | 0.230 | 0.257 | 0.000 |
| section_travel_mean_s | 38.983 | 38.983 | 37.760 | 39.142 | 34.214 |

REAL general speed/headway/travel metrics use the frozen target cohort. REAL physical queue audit uses all observed arterial class2/3 context; SIM contains target agents only. Queue means/P90/spatial lengths use observed occupied-lane approach snapshots, not a full-clock demand-normalized mean; coverage and omitted agents limit causal interpretation. Queue max is per lane; old pooled queue proxy is retained separately. Clearance distributions omit censored observations and report observed counts in replica outputs. Temporal throughput uses the same30s bins as3S. Throughput total is observed demand, not road capacity. Section travel metric follows the unchanged3S definition. These limits prohibit a parametric-only conclusion.
27. TRAIN runner report: outputs/peachtree3t/test_report.json; all122 prior cases retained. New semantic/chain/envelope/holdout tests added; no legacy actual-source fixtures run. Final exact totals are in that report.
28. B1 LOCKED. No B1 behavioral data opened. Prior artifacts are hashed, and the preservation check identifies only intentional UI source changes. Historical exposure remains acknowledged: future validation must be called TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.
29. Remaining difference: STRUCTURAL, not defensibly PARAMETRIC. This does not prove an absent propagation mechanism; it identifies unresolved control geometry before such attribution.
30. B. NEEDS_STRUCTURAL_REVISION. No structural freeze is issued. Scope/dt/signals/IDM/demand are unchanged; the JSON contains the current constraints and explicit NOT_FROZEN status.
31. Next step: independently identify lane-specific painted control references from official scaled geometry/ortho or additional authorized TRAIN evidence, then formal structural revision and the same paired diagnostics. Do not choose coordinates by fit. Do not recalibrate IDM, open B1, expand the corridor or implement E1/E2/E3 now.

UI: Show control envelopes / Show queue heads are rendering-only overlays. Reduced boundaries remain400→1346.452 NB and1400→597.878 SB. TEST locked and scenarios disabled. **UI_IMPLEMENTED_NOT_BROWSER_VALIDATED**; automated unit/AppTest/Canvas checks do not establish visual browser validation.
