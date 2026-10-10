"""Aggregate B2 targets and transparent dimensionless TRAIN errors."""
import json
import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance,ks_2samp
from simulation.training_data import ROOT,require_train,load_b2_source,load_b2_cf,read_train_csv,load_inputs
from simulation.parameters import FOOT_M

class TrainTargets:
    def __init__(self,acquisition='B2'):
        require_train(acquisition);self.acquisition='B2';self.inputs=load_inputs()
        self.raw=load_b2_source();self.raw=self.raw[self.raw.t_relative.ge(93.4-1e-8)].copy()
        self.raw['simulation_time']=self.raw.t_relative-93.4
        self.speed=self.raw.v_vel.to_numpy(float)
        clean=load_b2_cf();clean=clean[clean.t_relative.ge(93.4-1e-8)]
        index=self.raw.set_index(['vehicle_id','frame_id'])
        point=index.reindex(pd.MultiIndex.from_frame(clean[['vehicle_id','frame_id']]))
        self.headway=point.space_headway.dropna().to_numpy(float)
        self.stopped=float(self.raw.v_vel.eq(0).mean())
        travel=read_train_csv(ROOT/'outputs/peachtree_fixed_gate_travel_times.csv')
        travel['entry_time_s']=pd.to_numeric(travel.entry_time_s);travel['travel_time_s']=pd.to_numeric(travel.travel_time_s)
        self.travel=travel[travel.entry_time_s.ge(93.4)].travel_time_s.to_numpy(float)
        self.mean_speed=float(np.mean(self.speed));self.mean_travel=float(np.mean(self.travel))
        self.speed_scale=max(1e-6,float(np.quantile(self.speed,.75)-np.quantile(self.speed,.25)))
        self.headway_scale=max(1e-6,float(np.quantile(self.headway,.75)-np.quantile(self.headway,.25)))
        gates=read_train_csv(ROOT/'outputs/peachtree_physical_gate_events.csv')
        gates['t_cross_s']=pd.to_numeric(gates.t_cross_s)
        self.real_exits=gates[gates.event.eq('EXIT')&gates.t_cross_s.ge(93.4)].copy()
        self.real_exits['time']=self.real_exits.t_cross_s-93.4
        self.bins=np.arange(0,self.inputs['horizon_s']+30,30.)
        self.exit_hist=np.histogram(self.real_exits.time,bins=self.bins)[0]
        self.real_ts=self.raw.groupby('simulation_time').agg(mean_speed_ft_s=('v_vel','mean'),vehicles_active=('vehicle_id','size'),
            stopped_fraction=('v_vel',lambda x:x.eq(0).mean())).reset_index()

    def errors(self,model):
        s=model.summary;record=model.recorder
        head=np.asarray(record.headways);speed=np.asarray(record.speeds)
        tt=np.asarray([r['travel_time_s'] for r in record.travels])
        counts=np.histogram([r['exit_time_s'] for r in record.exits],bins=self.bins)[0]
        errors={
            'mean_speed_relative_error':abs(s['mean_speed_ft_s']-self.mean_speed)/self.mean_speed,
            'speed_W1_normalized':wasserstein_distance(self.speed,speed)/self.speed_scale if len(speed) else 1.,
            'headway_W1_normalized':wasserstein_distance(self.headway,head)/self.headway_scale if len(head) else 1.,
            'route_time_relative_error':abs(np.mean(tt)-self.mean_travel)/self.mean_travel if len(tt) else 1.,
            'stopped_fraction_absolute_error':abs(s['stopped_fraction']-self.stopped),
            'throughput_temporal_normalized_error':float(np.abs(counts-self.exit_hist).sum()/max(1,self.exit_hist.sum()))}
        penalty=(s['vehicles_remaining']+s['pending_arrivals'])/max(1,len(self.inputs['entries'])+len(self.inputs['initial']))
        errors['unfinished_fraction_penalty']=penalty
        errors['objective']=float(np.mean([errors[k] for k in errors if k!='unfinished_fraction_penalty'])+penalty)
        return errors

    def comparisons(self,model):
        sim=model.recorder
        rows=[]
        for name,real,pred,unit in [('speed',self.speed,np.asarray(sim.speeds),'ft/s'),
            ('headway',self.headway,np.asarray(sim.headways),'ft'),
            ('route_travel_time',self.travel,np.asarray([r['travel_time_s'] for r in sim.travels]),'s')]:
            rows.append({'indicator':name,'unit':unit,'real_n':len(real),'simulated_n':len(pred),
                'real_mean':float(np.mean(real)),'simulated_mean':float(np.mean(pred)) if len(pred) else np.nan,
                'real_median':float(np.median(real)),'simulated_median':float(np.median(pred)) if len(pred) else np.nan,
                'ks':float(ks_2samp(real,pred,method='asymp').statistic) if len(pred) else np.nan,
                'wasserstein':float(wasserstein_distance(real,pred)) if len(pred) else np.nan})
        rows.append({'indicator':'stopped_fraction','unit':'fraction','real_mean':self.stopped,'simulated_mean':model.summary['stopped_fraction']})
        rows.append({'indicator':'exit_throughput_total','unit':'crossings','real_mean':len(self.real_exits),'simulated_mean':model.exited,
            'note':'Temporal bins, not total alone, are the objective; initial vehicles included consistently'})
        return pd.DataFrame(rows)
