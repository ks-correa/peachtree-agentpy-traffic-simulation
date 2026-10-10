# PEACHTREE-3: approved baseline methodology

Official scope: class2/3 arterial through-cohort around11th/12th, Local_Y400–1400ft.
TRAIN=B2, TEST=B1. B1 is locked from this phase for calibration, selection, visual
adjustment and optimization. The correct future label is temporal/acquisition
holdout validation with prior feasibility summary exposure, never fully blind.

Source hash, geometry, quality filters, clocks, signal series, preprocessing and
predeclared estimation/search criteria are frozen in outputs/baseline_scope_freeze.json.
Source files are untouched. The mixed source is routed by frame/time acquisition
metadata before numeric behavioral values are parsed; B1 data is not returned.

Physical dt=0.1s. Start at B2 relative93.4s (frame936), when the four Through
signals are known, and end at1032.7s. Existing agents use one initial snapshot;
later inputs are observed entry times/boundaries/classes/routes/dimensions.
Entry speeds are sampled from a fixed B2 boundary-speed distribution by direction,
with AgentPy-seeded randomness. Internal position/speed/acceleration histories
are never supplied to the simulation. Waiting upstream when insertion is unsafe
is measured explicitly rather than forcing an overlap or moving an agent.

The longitudinal physics uses SI; US survey foot=1200/3937m. IDM is pooled over
classes2/3. Delta4 is literature-derived; v0,T,s0,a,b are initialized by frozen
B2 criteria and then calibrated using aggregate TRAIN errors. No visual fitting.

The stop-line reference is the previously approved observed intersection-mouth
proxy, not a surveyed painted bar. Lane0 at initialization carries the last valid
B2 approach lane; lane11 through records are represented as logical connectors
requiring safe merge to lane1. Neither assumption adds a street. Discretionary
lane changes remain simplified unless the small B2 sample supports a stable rule.

The reduced cohort omits local/turning streams that affect real traffic. This is
a material limitation, not full-network conservation or proof of counterfactual
benefit. Inputs are exogenous boundary conditions, not trajectory replay.

All data-dependent rules are TRAIN-only. Signals use recorded B2 schedules;
there is no offset/green optimization. E1/E2/E3 remain disabled until a later
baseline validation decision. Model changes and calibration versions are logged.
