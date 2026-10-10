"""Post-search TRAIN diagnostics only; no parameter modification."""
import json
import numpy as np
import pandas as pd
from simulation.training_data import ROOT,load_b2_source,load_inputs
from simulation.network import PeachtreeEnvironment
from simulation.signals import controllers_from_inputs
from simulation.parameters import FOOT_M

def main():
    inputs=load_inputs();raw=load_b2_source();origin=inputs['source_window_start_relative_s']
    raw=raw[raw.t_relative.ge(origin)].copy();env=PeachtreeEnvironment(inputs['network']);signals=controllers_from_inputs(inputs)
    crossings=[];yellow_onsets=[];section=[]
    for key,q in raw.groupby('trajectory_key'):
        q=q.sort_values('frame_id');direction=int(q.direction.iloc[0]);progress=np.asarray([env.progress(y,direction) for y in q.local_y])
        records=[]
        for line in sorted([line for line in env.stop_lines if line.direction==direction],key=lambda line:line.progress_m):
            at=np.flatnonzero((progress[:-1]<line.progress_m)&(progress[1:]>=line.progress_m)&(np.diff(q.frame_id)==1))
            if len(at):
                i=at[0];fraction=(line.progress_m-progress[i])/(progress[i+1]-progress[i]);time=q.t_relative.iloc[i]-origin+.1*fraction
                record={'trajectory_key':key,'intersection':line.intersection,'direction':direction,'time_s':time,'state':signals[(line.intersection,direction)].at(time)}
                records.append(record);crossings.append(record)
            for interval in signals[(line.intersection,direction)].intervals:
                if interval.state!='YELLOW' or interval.start<0:continue
                at_time=origin+interval.start;ix=np.flatnonzero(np.isclose(q.t_relative,at_time,atol=.00001))
                if not len(ix):continue
                i=ix[0]
                if env.next_line(direction,progress[i])!=line:continue
                end=min(interval.end,inputs['horizon_s']);after=q[q.t_relative.between(at_time,origin+end)]
                yellow_onsets.append({'trajectory_key':key,'intersection':line.intersection,'direction':direction,'yellow_start_simulation_s':interval.start,
                    'distance_m':line.progress_m-progress[i],'speed_m_s':q.v_vel.iloc[i]*FOOT_M,
                    'stopped_within_yellow':bool(after.v_vel.eq(0).any()),'crossed_within_yellow':bool(after.local_y.ge(line.local_y_ft).any() if direction==2 else after.local_y.le(line.local_y_ft).any())})
        if len(records)==2:section.append({'trajectory_key':key,'direction':direction,'travel_time_s':records[1]['time_s']-records[0]['time_s'],'definition':'between same approved signal-reference cuts; both crossings after window start'})
    pd.DataFrame(crossings).to_csv(ROOT/'outputs/b2_observed_signal_crossings.csv',index=False)
    pd.DataFrame(yellow_onsets).to_csv(ROOT/'outputs/b2_yellow_onsets.csv',index=False)
    pd.DataFrame(section).to_csv(ROOT/'outputs/b2_observed_section_times.csv',index=False)
    onset=pd.DataFrame(yellow_onsets);yellow_cross=sum(r['state']=='YELLOW' for r in crossings)
    yellow={'training_acquisition':'B2','yellow_onset_observations':len(onset),'unique_vehicles':onset.trajectory_key.nunique(),
        'yellow_crossings':yellow_cross,'both_stopped_and_crossed_in_interval':int((onset.stopped_within_yellow&onset.crossed_within_yellow).sum()),
        'classification':'ASSUMPTION','implemented_rule':'Stop if remaining distance >= s0+v^2/(2*b); latch until yellow ends. No wall-clock, B1, or offset fitting.',
        'reason':'Sparse conditional per-approach sample, leader/censoring confounding, no identifiable driver intention or stable decision boundary. Onset rows may repeat a vehicle; not independent trials.'}
    (ROOT/'outputs/b2_yellow_diagnostics.json').write_text(json.dumps(yellow,indent=2),encoding='utf-8')
    times=pd.read_csv(ROOT/'outputs/b2_baseline_timeseries.csv');sim_section=pd.read_csv(ROOT/'outputs/b2_simulated_section_times.csv')
    from scipy.stats import wasserstein_distance,ks_2samp
    comparison=pd.read_csv(ROOT/'outputs/b2_real_vs_simulated.csv');comparison=comparison[comparison.indicator.ne('section_travel_time')]
    real=np.asarray([r['travel_time_s'] for r in section]);pred=sim_section.travel_time_s.to_numpy()
    comparison=pd.concat([comparison,pd.DataFrame([{'indicator':'section_travel_time','unit':'s','real_n':len(real),'simulated_n':len(pred),
        'real_mean':real.mean(),'simulated_mean':pred.mean(),'real_median':np.median(real),'simulated_median':np.median(pred),
        'ks':ks_2samp(real,pred,method='asymp').statistic,'wasserstein':wasserstein_distance(real,pred),'note':'Post-search diagnostic, not selected/fitted; between same two signal reference cuts'}])],ignore_index=True)
    comparison.to_csv(ROOT/'outputs/b2_real_vs_simulated.csv',index=False)
    trace=json.loads((ROOT/'outputs/b2_reference_trace.json').read_text());counts={};sample_count=0
    for frame in trace['frames']:
        for a in frame['agents']:counts[a['state']]=counts.get(a['state'],0)+1;sample_count+=1
    residual=pd.read_csv(ROOT/'outputs/b2_throughput_bins.csv');residual['residual']=residual.simulated_exits-residual.real_exits;residual.to_csv(ROOT/'outputs/b2_throughput_residuals.csv',index=False)
    diagnostic={'training_acquisition':'B2','max_active':int(times.vehicles_active.max()),'max_stopped':int(times.stopped_vehicles.max()),
        'max_queue_proxy':int(times.queue_proxy_vehicles.max()),'speed_collective_min_ft_s':float(times.mean_speed_ft_s[times.vehicles_active>0].min()),
        'speed_collective_max_ft_s':float(times.mean_speed_ft_s[times.vehicles_active>0].max()),'max_braking_vehicles':int(times.braking_vehicles.max()) if 'braking_vehicles' in times else None,
        'state_exposure_counts_at_half_second':counts,'sample_agent_snapshots':sample_count,
        'section_time_observed_n':len(section),'section_time_observed_mean_s':float(np.mean([x['travel_time_s'] for x in section])),
        'section_time_simulated_n':len(sim_section),'section_time_simulated_mean_s':float(sim_section.travel_time_s.mean()),
        'throughput_bin_residual_min':int(residual.residual.min()),'throughput_bin_residual_max':int(residual.residual.max()),
        'interpretation':'Accumulation, collective speed variation, stopping and release numerically observed. Braking/spatial traces instrumented; lag association is not causal proof of a backward wave.'}
    (ROOT/'outputs/b2_emergent_diagnostics.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
    print(json.dumps({'yellow':yellow,'emergent':diagnostic},indent=2))
if __name__=='__main__':main()
