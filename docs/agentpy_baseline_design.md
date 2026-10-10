# AgentPy baseline — PEACHTREE-3

## Architecture

`simulation/training_data.py` is the TRAIN-only routing boundary. It returns B2
observations for preprocessing and objective construction, never to an agent's
step. `data/b2_exogenous_inputs.json` contains one initial snapshot, boundary
events, pooled boundary-speed distributions, fixed signal schedules and logical
geometry. `simulation/agents.py` and `simulation/model.py` implement real
`ap.Agent` and `ap.Model` subclasses. AgentPy owns setup, update, sim_step, RNG,
termination and reports. `calibration/` owns estimation, aggregate objectives,
finite search and diagnostics. `ui/` consumes simulated states and saved TRAIN
outputs. Root `streamlit_app.py` is only an entry point.

## Coordinates and geometry

Front-center progress is metres along travel direction; speed m/s and acceleration
m/s². US survey foot is 1200/3937 m. NB progresses from Y400 to1400; SB from1400
to400. Two logical arterial lanes each direction; road sections2/3/4 with observed
intersection extents for11th and12th. Stop restrictions use the approved entry
mouth proxies: I2 NB632.5395, SB777.262; I3 NB1168.9155, SB1240.7775 ft. These are
not surveyed painted bars. The Canvas preserves longitudinal order/distances but
its lateral road width is schematic. No local-street agents or invented streets.

## Agent and state

VehicleAgent stores synthetic ID, class, length/width, progress, lane, speed,
acceleration, movement/direction, leader/follower, entry/exit time and state.
ENTERING comes from insertion; FREE_FLOW/FOLLOWING from current leader relation;
STOPPED_SIGNAL requires a signal restriction and numerical rest;
LANE_CHANGING comes from a necessary safe connector merge; EXITED from an actual
boundary crossing. No subjective driver traits. Initial agents have no simulated
full-route entry timestamp, so their partial travel is excluded from full travel
time targets while their exits remain in throughput. The current B2 input uses no
lane11 boundary/initial agents; necessary connector logic is present, discretionary
changes disabled because only21 TRAIN scope events are confirmed.

## One tick and longitudinal behavior

One AgentPy step is0.1s. Update signals at tick start, insert safe arrivals,
determine leaders/followers, evaluate necessary lane changes, calculate all IDM
accelerations on one consistent snapshot, integrate velocities/positions,
detect interpolated boundary crossings, mark EXITED and record metrics.
Spatial chain constraints can reduce acceleration before integration; they never
overwrite a position. Safety reduction is separately counted. Ballistic stopping
within a tick integrates only to speed zero. The proposed leader advance can
limit a follower's allowable displacement independently of agent iteration order.

IDM: a[1−(v/v0)^δ−(s*/s)²], s*=s0+max(0,vT+v(v−vLeader)/(2√ab)).
For free flow omit the interaction term. A red signal is a stationary virtual
leader at its reference cut. Yellow latches a conservative comfortable-stopping
decision when distance ≥s0+v²/(2b); this is an ASSUMPTION, not a fitted choice
model. GREEN releases the signal constraint; real leaders still constrain motion.
UNKNOWN signal raises an error. Signal timing is fixed B2; no optimization.

Every tick checks nonnegative speed, nonoverlap and
initial+entered=active+exited. Unsafe insertion waits outside the domain and logs
delay. There is no trajectory array or raw-data reader in VehicleAgent.

## Playback and evidence

The engine stores numeric speed, headway, stopped fraction, active population,
throughput, queue proxy, travel, braking counts and crossings. Trace snapshots
every0.5s contain simulated states only. Browser requestAnimationFrame interpolates
those snapshots; Run/Pause/Reset and visual speed do not modify physical dt or
calibrated parameters. Frontend cards follow playback time. Sidebar parameters
are read only. Plotly consumes numerical results. TEST B1 is locked and no TEST
metric loader exists in the UI. E1/E2/E3 controls are disabled.

## References

- [AgentPy model lifecycle](https://agentpy.readthedocs.io/en/stable/reference_model.html)
- [AgentPy RNG](https://agentpy.readthedocs.io/en/stable/guide_random.html)
- [IDM equations, ballistic integration and virtual red leader](https://mtreiber.de/MicroApplet/IDM.html)
- [Treiber, Hennecke and Helbing (2000)](https://arxiv.org/abs/cond-mat/0002177)
