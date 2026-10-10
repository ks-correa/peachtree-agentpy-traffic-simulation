import json,time
from simulation.training_data import load_inputs,ROOT
from simulation.model import run_baseline
from calibration.diagnostics import estimate_parameters
from calibration.objective import TrainTargets

if __name__=='__main__':
 p,bounds,gap=estimate_parameters();target=TrainTargets();start=time.perf_counter()
 model=run_baseline(load_inputs(),p,seed=10,queue_gap=gap)
 report={'seconds':time.perf_counter()-start,'summary':model.summary,'errors':target.errors(model)}
 (ROOT/'outputs/b2_initial_rollout.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,indent=2));print(target.comparisons(model).to_string(index=False))
