# Validation contract — DRAFT / NOT APPROVED / NOT FROZEN

Phase: PEACHTREE-2. No calibration or simulation has occurred.

## Population and space

Proposed TRAIN=B2, TEST=B1, retrospectively independent acquisition keys. Proposed
region: 400 <= Local_Y <= 1400 ft, I2/11th and I3/12th arterial approaches.
Population: class2/3 constant-direction NB/SB through journeys with both fixed-cut
crossings observed. This is a conditional through-cohort abstraction, NOT all
traffic that appears in the region. Omitted turning/local streams influence real
traffic. Scope acceptance is mandatory; otherwise close their observed ports and
revise this draft within Peachtree. Numeric IDs are never linked across acquisitions.

## Clocks and control

t_relative=(frame_id-first_acquisition_frame)*0.1 s. Global_Time is not a calendar.
Controller map: I2=52/11th, I3=53/12th. Use recorded Through phases keyed by
acquisition/frame/direction. UNKNOWN before first event stays unknown. Use a
measurement interval only when all needed phases are known (values in timing CSV).
Do not infer permissive left/right-on-red rules from a shared Through column.

## Inputs vs outcomes

Allowed exogenous TEST inputs for conditional baseline evaluation after approval:
entry-crossing demand, class/dimensions, route direction, initial speed/occupancy,
and recorded signal schedule. Declare this as conditional validation, not demand
prediction. Do not read TEST to fit response, tune filters, choose equations,
thresholds, desired speed or other behavior parameters.

Conservation within the modeled population: N_initial + entered = exited +
remaining. For an empty initial domain this becomes entered = exited + remaining.
Initial occupancy at a chosen known-phase start is an explicitly declared
snapshot/input, not an inferred entry event or an ongoing trajectory replay.

Forbidden inputs: internal historical position/speed sequences, measured future
exit times or route travel times. Never force exits and then claim throughput
prediction. Exit events are scoring targets. Complete-cohort eligibility is an
observational censoring protocol, not proof of a closed full network. Simulated
agents that fail to exit are failures/censored outputs and may not be discarded
to improve scores. Demand selection by retrospective completeness limits claims.

## Fixed measurement plan

| Indicator | Class | Location | Time bin | Unit | Real calculation | Simulation calculation |
|---|---|---|---|---|---|---|
| Speed distribution | PRIMARY | Proposed population within gate band; direction/section strata | 30s and acquisition | ft/s | Same source QC, exposure convention | Independent generated states, same visibility/QC convention |
| Mean speed | PRIMARY | Same interior strata | 30s | ft/s | Observation-time-weighted mean | Time-weighted collected agent speeds |
| Gap/headway distribution | PRIMARY | Same-direction/lane section2/3 approaches, contemporaneous leader | 30s and acquisition | ft or s | Space headway front-to-front; free gap subtracts leader length; moving time headway excludes sentinel | Same geometry/leader definitions |
| Exit throughput | PRIMARY | North cut1400 NB and south cut400 SB | 30s (partial final bin labeled) | crossings/bin | Two consecutive samples crossing defined plane, no first-record substitution | Same detector; no measured exits fed as input |
| Route travel time | PRIMARY | Opposite-cut paired path, length1000ft along Local_Y | Entry cohort/whole acquisition | s | Interpolated exit crossing minus entry crossing | Same entry/exit detectors; non-completers reported |
| Section/intersection traversal | PRIMARY candidate | Fixed annotated boundaries or approved per-lane surveyed detector | Route/approach strata | s | Both entry and exit observed, never source last-first | Same approved logical detector; not metric distances inferred from data extents |
| Confirmed lane changes | SECONDARY | Normal adjacent lanes in same section/direction | 30s, vehicle-minute exposure | events | Fixed operational protocol; bays/context changes separate | Same protocol on generated trajectories |
| Stopped fraction | SECONDARY | Arterial approach band at I2/I3 | 30s | proportion | Exactly v=0; creeping sensitivity only until TRAIN-only criterion approved | Same measurement |
| Acceleration distribution | SECONDARY | Same CF approach sample | 30s and acquisition | ft/s^2 | Saturation mass retained as audit; calibration excludes saturated response | Collect acceleration; report convention differences |
| Active agents | SECONDARY | Same selected region/population | Every frame, summarize30s | vehicles | Canonical IDs inside at each frame | Count matching agents at detector time |
| Queue length | SECONDARY candidate | Connected approach chain referenced to validated stop bar | Signal cycle/1s | vehicles/ft | Threshold/spacing/hysteresis NOT fixed; physical stop bar still to verify | Same future approved protocol |

## QC protocol before fitting

Quality filters CSV defines nonexclusive masks and rates by acquisition.
Source accuracy-based kinematic checks are diagnostics, not confidence intervals.
No filters were selected by prediction errors. Proposed lane-transition window
is +/-1s; saturation excludes exact observed +/-12.27ft/s^2 response. Formal
queue threshold and spatial chain-gap criterion remain unapproved and must be
decided using potential TRAIN and primary literature, then fixed before TEST.

## Evaluation and lifecycle

Use distribution differences, KS and Wasserstein descriptively; no acceptance
threshold was invented. Predeclare tolerances/uncertainty appropriate to course
requirements before fitting/final testing. Resample by vehicles/cycles/windows,
not by independent trajectory rows. Stratify direction/class/section and compare
same initial conditions/demand/control, with stochastic replicates if relevant.

Before freeze: approve scope, incomplete-population implications, eligibility,
signal plan, preprocessing, queue protocol, metrics and tolerances. Freeze must be
a separate explicit user-approved action producing source/processed manifests.
After freeze: TRAIN development only; TEST opened solely by the agreed final
evaluation. A failed TEST is reported, not a reason to adjust rules invisibly.

No freeze is executed by this file or by PEACHTREE-2.
