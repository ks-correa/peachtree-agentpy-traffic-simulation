"""PEACHTREE-3U: predeclared empirical control references, unchanged physics."""
import csv,json,hashlib
from types import MappingProxyType
import pandas as pd
from calibration.receiving_scope import ReducedBoundaryModel,inputs_for
from calibration.structural import COLUMNS
from calibration.control_envelope import SignalControlEnvelope
from simulation.training_data import ROOT,require_train
from simulation.parameters import IDMParameters

REFERENCE_SOURCE=ROOT/'outputs/peachtree3t/intersection_envelopes.csv'
REFERENCE_SHA256='c0a3c8788f80ab74f8af3faff205bfd47a59f1d2027438806906cc734e16520e'
LEGACY=MappingProxyType({(2,2):632.5395,(2,4):777.262,(3,2):1168.9155,(3,4):1240.7775})

def references(acquisition='B2'):
    require_train(acquisition)
    if hashlib.sha256(REFERENCE_SOURCE.read_bytes()).hexdigest()!=REFERENCE_SHA256:
        raise RuntimeError('Frozen predeclared 3T entry artifact changed')
    values={}
    with REFERENCE_SOURCE.open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            key=(int(r['intersection']),int(r['direction']));value=float(r['entry'])
            if key in values and values[key]!=value:raise RuntimeError('Lane entries disagree in original artifact')
            values[key]=value
    if set(values)!=set(LEGACY):raise RuntimeError('Incomplete effective references')
    return MappingProxyType(values)

def final_inputs(acquisition='B2'):
    require_train(acquisition);data=inputs_for('NEW_REDUCED_SCOPE');refs=references()
    for line in data['network']['stop_lines']:
        key=(int(line['intersection']),int(line['direction']))
        line['legacy_signal_proxy_ft']=line['local_y_ft']
        line['local_y_ft']=refs[key]
        line['reference_type']='EFFECTIVE_SIGNAL_CONTROL_REFERENCE'
    data['structural_mode']='FINAL_STRUCTURE'
    data['control_reference_source']={'path':str(REFERENCE_SOURCE.relative_to(ROOT)),'sha256':REFERENCE_SHA256,
        'selection':'PREDECLARED_INTERSECTION_ENTRY_REFERENCE_NOT_SIM_OPTIMIZATION'}
    data['control_envelopes']=pd.read_csv(REFERENCE_SOURCE).to_dict('records')
    freeze=ROOT/'outputs/peachtree3u/structural_model_freeze.json'
    if freeze.exists():
        manifest=json.loads(freeze.read_text())
        if manifest['status']!='FROZEN':raise RuntimeError('Final structure is not frozen')
        for path,expected in manifest['structural_code_hashes'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
                raise RuntimeError('Frozen structural code changed: '+path)
        signature=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if signature!=manifest['structural_input_signature']:raise RuntimeError('Frozen structural inputs changed')
    return data

class FinalStructureModel(ReducedBoundaryModel):
    """The sole physical change is input virtual-control coordinates.

    Envelope association remains available beyond the effective entry, until
    own-junction exit. It labels agents without supplying acceleration or speed.
    """
    def setup(self,*args,**kwargs):
        super().setup(*args,**kwargs)
        self.control_envelopes=tuple(SignalControlEnvelope(**r) for r in self.inputs['control_envelopes'])
    def update(self):
        for a in self.agents:
            y=self.network.local_y(a.position,a.direction)
            a.control_intersection=next((e.intersection for e in self.control_envelopes
                if e.direction==a.direction and e.lane==a.lane and e.contains(y)),0)
        super().update()

def run_final(seed,trace=False,acquisition='B2'):
    require_train(acquisition);data=final_inputs()
    p=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())
    model=FinalStructureModel({'steps':round(data['horizon_s']/.1),'seed':int(seed)},
        inputs=data,idm=IDMParameters(**p['parameters']),trace=trace,queue_gap=p['queue_gap_m'])
    model.run(display=False)
    return model,pd.DataFrame(model.observations,columns=COLUMNS)
