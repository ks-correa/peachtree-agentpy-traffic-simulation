"""TRAIN-only structural diagnostics, with identical real/sim measurements."""
import csv,json
from pathlib import Path
import numpy as np
import pandas as pd
from simulation.training_data import ROOT,require_train,load_inputs,load_b2_source
from simulation.parameters import FOOT_M,IDMParameters
from simulation.model import PeachtreeModel
from simulation.network import PeachtreeEnvironment
from simulation.signals import controllers_from_inputs

OUT=ROOT/'outputs/peachtree3r'

def full_b2(acquisition='B2'):
    require_train(acquisition);path=ROOT/'data/b2_all_observed.parquet'
    if not path.exists():
        rows=[]
        with (ROOT/'data/peachtree_full.csv').open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                if int(r['global_time'])-100*int(r['frame_id'])!=1163030300:continue
                rows.append(r)
        d=pd.DataFrame(rows)
        for c in d.columns:
            if c!='location':d[c]=pd.to_numeric(d[c],errors='raise')
        d['acquisition_id']='B2';d['trajectory_key']='B2:'+d.vehicle_id.astype(str);d['t_relative']=(d.frame_id-2)*.1
        d.to_parquet(path,index=False,compression='zstd')
    d=pd.read_parquet(path)
    if not d.acquisition_id.eq('B2').all():raise PermissionError('B1 LOCKED')
    return d

class DiagnosticModel(PeachtreeModel):
    def setup(self,*args,**kwargs):
        self.observations=[];self.arrival_audit=[]
        super().setup(*args,**kwargs)
    def create_agent(self,data,entry_time,initial=False):
        a=super().create_agent(data,entry_time,initial)
        if not initial:
            line=self.network.next_line(a.direction,0.)
            controller=self.controllers[(line.intersection,a.direction)]
            self.arrival_audit.append({'id':a.agent_id,'direction':a.direction,'scheduled_entry_time':data['requested_time_s'],
                'lane':a.lane,
                'actual_entry_time':entry_time,'delay':entry_time-data['requested_time_s'],
                'scheduled_phase':controller.at(data['requested_time_s']),'actual_phase':controller.at(entry_time)})
        return a
    def update(self):
        super().update()
        for a in self.agents:
            line=self.network.next_line(a.direction,a.position);leader=self.leaders.get(a.agent_id)
            self.observations.append((a.agent_id,self.t,self.simulation_time,a.direction,a.lane,self.network.local_y(a.position,a.direction),a.speed/FOOT_M,
                a.acceleration/FOOT_M,a.length/FOOT_M,line.intersection if line else 0,(line.progress_m-a.position)/FOOT_M if line else np.nan,
                self.controllers[(line.intersection,a.direction)].at(self.simulation_time) if line else 'UNCONTROLLED',
                leader.agent_id if leader else '',(leader.position-a.position)/FOOT_M if leader else np.nan,
                (leader.position-leader.length-a.position)/FOOT_M if leader else np.nan,a.initial,getattr(a,'agent_role','TARGET')))

COLUMNS=['id','frame','time','direction','lane','y','speed','acceleration','length','intersection','distance','phase','leader','headway','gap','initial','role']
def rollout(inputs=None,seed=10,trace=False):
    data=load_inputs() if inputs is None else inputs
    p=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text(encoding='utf-8'))
    m=DiagnosticModel({'steps':round(data['horizon_s']/.1),'seed':seed},inputs=data,idm=IDMParameters(**p['parameters']),trace=trace,queue_gap=p['queue_gap_m'])
    m.run(display=False)
    return m,pd.DataFrame(m.observations,columns=COLUMNS)

def contextualize(d,inputs):
    env=PeachtreeEnvironment(inputs['network']);bank=controllers_from_inputs(inputs)
    d=d.copy();d['intersection']=0;d['distance']=np.nan;d['phase']='UNCONTROLLED'
    for direction in [2,4]:
        lines=sorted([x for x in env.stop_lines if x.direction==direction],key=lambda x:x.progress_m,reverse=True)
        for line in lines:
            mask=d.direction.eq(direction)&((line.local_y_ft-d.y)*(1 if direction==2 else -1)).gt(1e-6)
            d.loc[mask,'intersection']=line.intersection;d.loc[mask,'distance']=(line.local_y_ft-d.loc[mask,'y'])*(1 if direction==2 else -1)
            c=bank[(line.intersection,direction)]
            d.loc[mask,'phase']=[c.at(t) for t in d.loc[mask,'time']]
    return d

def real_observations(full,inputs):
    target=load_b2_source();target=target[target.t_relative.ge(inputs['source_window_start_relative_s']-1e-8)].copy()
    d=target.rename(columns={'trajectory_key':'id','frame_id':'frame','lane_id':'lane','local_y':'y','v_vel':'speed','v_acc':'acceleration','v_length':'length','space_headway':'headway'})
    d['time']=d.t_relative-inputs['source_window_start_relative_s'];d['role']='TARGET'
    d=contextualize(d,inputs)
    lookup=full.set_index(['frame_id','vehicle_id'],drop=False)
    lead=lookup.reindex(pd.MultiIndex.from_arrays([d.frame,d.preceding])).reset_index(drop=True);d=d.reset_index(drop=True)
    valid=d.preceding.gt(0)&lead.vehicle_id.notna()&lead.direction.eq(d.direction)&lead.lane_id.eq(d.lane)&lead.section_id.eq(d.section_id)
    gap=(lead.local_y-d.y).abs()-lead.v_length
    valid &= gap.gt(0)&((lead.local_y-d.y)*(np.where(d.direction.eq(2),1,-1))).gt(0)
    d['leader']=np.where(valid,'B2:'+d.preceding.astype(str),'');d['gap']=np.where(valid,gap,np.nan)
    d['physical_headway']=np.where(valid,(lead.local_y-d.y).abs(),np.nan)
    return d,lead,valid

def semantics(real,sim):
    rows=[]
    for label,d in [('REAL_B2',real),('OLD_BASELINE',sim)]:
        speed=d.speed.to_numpy()
        for threshold in [0,.1,.25,.5,1.,2.,3.]:
            rows.append({'series':label,'upper_ft_s':threshold,'exact_zero_fraction':float(np.mean(speed==0)),
                'positive_to_upper_fraction':float(np.mean((speed>0)&(speed<=threshold))),'cumulative_fraction':float(np.mean(speed<=threshold)),
                'n':len(speed),'minimum_positive_ft_s':float(np.min(speed[speed>0]))})
    return pd.DataFrame(rows)

def leader_audit(real,lead,valid,target_keys):
    category=np.where(~valid,'D_UNUSABLE',np.where(('B2:'+lead.vehicle_id.fillna(-1).astype(int).astype(str)).isin(target_keys),'A_TARGET',
        np.where(lead.v_class.isin([2,3])&lead.local_y.between(400,1400),'B_EXCLUDED_CLASS23_IN_BAND','C_OTHER_OBSERVED')))
    real['leader_category']=category
    rows=[]
    for subset,mask in [('ALL_PRECEDING_REFERENCES',real.preceding.gt(0)),('VALID_FOLLOWING',valid),('EXACT_ZERO_VALID_FOLLOWING',valid&real.speed.eq(0)),('NEAR_STOPPED_LE1_VALID_FOLLOWING',valid&real.speed.le(1.))]:
        for cat in ['A_TARGET','B_EXCLUDED_CLASS23_IN_BAND','C_OTHER_OBSERVED','D_UNUSABLE']:
            count=int(np.sum(mask&(category==cat)));rows.append({'subset':subset,'category':cat,'frames':count,'denominator':int(mask.sum()),'fraction':count/max(1,int(mask.sum()))})
    if 'lane' in real and 'int_id' in real:
        road=valid&real.lane.isin([1,2])&real.int_id.eq(0)
        for subset,mask in [('STRICT_ROAD_VALID_FOLLOWING',road),('STRICT_ROAD_EXACT_ZERO_FOLLOWING',road&real.speed.eq(0)),('STRICT_ROAD_OPERATIONAL_FOLLOWING',road&real.speed.le(.1/FOOT_M))]:
            for cat in ['A_TARGET','B_EXCLUDED_CLASS23_IN_BAND','C_OTHER_OBSERVED','D_UNUSABLE']:
                count=int(np.sum(mask&(category==cat)));rows.append({'subset':subset,'category':cat,'frames':count,'denominator':int(mask.sum()),'fraction':count/max(1,int(mask.sum()))})
    return pd.DataFrame(rows)

def initial_audit(real,sim,inputs):
    r=real[real.frame.eq(inputs['source_window_start_frame'])].copy();s=sim[sim.frame.eq(0)].copy()
    rows=[]
    for label,d in [('REAL_B2',r),('OLD_BASELINE',s)]:
        for a in d.itertuples():rows.append({'series':label,'id':a.id,'y_ft':a.y,'speed_ft_s':a.speed,'leader':a.leader,'clearance_ft':a.gap,'intersection':a.intersection,'phase':a.phase,'distance_ft':a.distance})
    return pd.DataFrame(rows)

def main(acquisition='B2'):
    require_train(acquisition);OUT.mkdir(parents=True,exist_ok=True)
    full=full_b2();inputs=load_inputs();m,sim=rollout();real,lead,valid=real_observations(full,inputs)
    sim.to_parquet(OUT/'old_observations.parquet',index=False);real.to_parquet(OUT/'real_observations.parquet',index=False)
    sem=semantics(real,sim);sem.to_csv(OUT/'stop_speed_semantics.csv',index=False)
    audit=leader_audit(real,lead,valid,set(load_b2_source().trajectory_key));audit.to_csv(OUT/'omitted_leader_audit.csv',index=False)
    real.to_parquet(OUT/'real_observations.parquet',index=False)
    pd.DataFrame(m.arrival_audit).to_csv(OUT/'safe_insertion_delay.csv',index=False)
    initial_audit(real,sim,inputs).to_csv(OUT/'initial_condition_audit.csv',index=False)
    print(sem.to_string(index=False));print(audit.to_string(index=False))

if __name__=='__main__':main()
