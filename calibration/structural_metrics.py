"""Explicit measurement definitions shared by REAL/OLD/REVISED; no fitting."""
import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance,ks_2samp
from simulation.parameters import FOOT_M

STOP_M_S=.1
STOP_FT_S=STOP_M_S/FOOT_M
DISTANCE_EDGES=[0,50,100,200,np.inf]

def stopped(speed_ft_s):return np.asarray(speed_ft_s)<=STOP_FT_S

def stop_episodes(d):
    rows=[]
    for key,q in d.sort_values(['id','frame']).groupby('id',sort=False):
        q=q.reset_index(drop=True);mask=stopped(q.speed);starts=np.flatnonzero(mask&np.r_[True,~mask[:-1]|(np.diff(q.frame)!=1)])
        for start in starts:
            end=start
            while end+1<len(q) and mask[end+1] and q.frame.iloc[end+1]==q.frame.iloc[end]+1:end+=1
            onset=q.iloc[start];release=q.iloc[end+1] if end+1<len(q) and q.frame.iloc[end+1]==q.frame.iloc[end]+1 else None
            rows.append({'id':key,'start_time':onset.time,'end_time':q.time.iloc[end]+.1,'duration_s':(end-start+1)*.1,
                'distance_ft':onset.distance,'intersection':onset.intersection,'direction':onset.direction,'onset_phase':onset.phase,
                'release_phase':release.phase if release is not None else 'CENSORED','left_censored':start==0,'right_censored':release is None})
    return pd.DataFrame(rows,columns=['id','start_time','end_time','duration_s','distance_ft','intersection','direction','onset_phase','release_phase','left_censored','right_censored'])

def phase_stopping(d,label):
    d=d[d.intersection.isin([2,3])].copy();d['distance_band']=pd.cut(d.distance,DISTANCE_EDGES,right=False).astype(str)
    d['operational_stopped']=stopped(d.speed);d['exact_zero']=d.speed.eq(0)
    rows=[]
    for cols,z in d.groupby(['intersection','direction','phase','distance_band']):
        rows.append(dict(series=label,intersection=cols[0],direction=cols[1],phase=cols[2],distance_band=cols[3],n=len(z),operational_stopped_fraction=z.operational_stopped.mean(),exact_zero_fraction=z.exact_zero.mean()))
    return pd.DataFrame(rows)

def crossings(d,inputs):
    rows=[]
    for key,q in d.sort_values(['id','frame']).groupby('id',sort=False):
        direction=int(q.direction.iloc[0]);sign=1 if direction==2 else -1;y=q.y.to_numpy()*sign;t=q.time.to_numpy()
        for line in inputs['network']['stop_lines']:
            if int(line['direction'])!=direction:continue
            ref=line['local_y_ft']*sign
            hits=np.flatnonzero((y[:-1]<ref)&(y[1:]>=ref)&(np.diff(q.frame)==1))
            if len(hits):
                j=hits[0];when=t[j]+.1*(ref-y[j])/(y[j+1]-y[j]);rows.append({'id':key,'direction':direction,'intersection':line['intersection'],'time':when,'lane':int(q.lane.iloc[j])})
    return pd.DataFrame(rows,columns=['id','direction','intersection','time','lane'])

def queues(d,label,gap_ft,horizon):
    # Lane chain must connect to the nearest operationally stopped approach head.
    rows=[];times=np.arange(round(horizon/.1)+1)*.1
    valid=d[d.intersection.isin([2,3])&d.lane.isin([1,2])].copy();valid['is_stop']=stopped(valid.speed)
    counted={}
    for (frame,intersection,direction,lane),q in valid.groupby(['frame','intersection','direction','lane'],sort=False):
        q=q.sort_values('distance');count=0;last=None
        for a in q.itertuples():
            if not a.is_stop:break
            if last is not None and a.distance-last.distance-last.length>gap_ft:break
            count+=1;last=a
        if count:counted[(round(float(q.time.iloc[0]),1),int(intersection),int(direction))]=counted.get((round(float(q.time.iloc[0]),1),int(intersection),int(direction)),0)+count
    for inter in [2,3]:
        for direction in [2,4]:
            values=np.array([counted.get((round(t,1),inter,direction),0) for t in times])
            rows.append({'series':label,'intersection':inter,'direction':direction,'mean':values.mean(),'median':np.median(values),'P90':np.quantile(values,.9),'max':values.max(),'duration_above_zero_s':np.sum(values>0)*.1})
    timeline=pd.DataFrame([{'time':t,'intersection':inter,'direction':direction,'queue':counted.get((round(t,1),inter,direction),0)} for inter in [2,3] for direction in [2,4] for t in times]);timeline['series']=label
    return pd.DataFrame(rows),timeline

def temporal(real,sim,real_exits,sim_exits,horizon,label):
    rows=[];through=[]
    events=pd.concat([pd.DataFrame({'time':real_exits,'delta':-1}),pd.DataFrame({'time':sim_exits,'delta':1})])
    event_max=float(events.groupby('time').delta.sum().sort_index().cumsum().abs().max()) if len(events) else 0.
    for width in [10.,30.,60.]:
        edges=np.r_[np.arange(0,horizon,width),horizon+1e-7];n=len(edges)-1
        data=[]
        for d,exits in [(real,real_exits),(sim,sim_exits)]:
            q=d.copy();q['operational_stopped']=stopped(q.speed);q['tick']=np.rint(q.time/.1).astype(int)
            frame=q.groupby('tick').agg(speed=('speed','mean'),stopped=('operational_stopped','mean'),active=('id','size'))
            frame=frame.reindex(range(round(horizon/.1)+1));frame['active']=frame.active.fillna(0.)
            # Speed/stopped fraction are undefined when there are no agents.
            # Zero is valid for occupancy/throughput, not for an empty speed sample.
            frame['bin']=np.minimum(frame.index.to_numpy()//round(width/.1),n-1)
            frame=frame.groupby('bin')[['speed','stopped','active']].mean().reindex(range(n))
            frame['throughput']=np.histogram(exits,edges)[0];data.append(frame)
        for metric in ['speed','stopped','active','throughput']:
            a=data[0][metric].to_numpy();b=data[1][metric].to_numpy();valid=np.isfinite(a)&np.isfinite(b);a=a[valid];b=b[valid];res=b-a
            rows.append({'series':label,'bin_s':width,'metric':metric,'RMSE':np.sqrt(np.mean(res**2)) if len(res) else np.nan,'bias':res.mean() if len(res) else np.nan,'correlation':np.corrcoef(a,b)[0,1] if len(a)>1 and a.std()>0 and b.std()>0 else np.nan,'MAE':np.abs(res).mean() if len(res) else np.nan,'bins_compared':len(a)})
        a=data[0].throughput.to_numpy();b=data[1].throughput.to_numpy()
        common=min(len(real_exits),len(sim_exits));bias=np.mean(np.sort(sim_exits)[:common]-np.sort(real_exits)[:common]) if common else np.nan
        through.append({'series':label,'bin_s':width,'maximum_cumulative_departure_deviation':np.max(np.abs(np.cumsum(b)-np.cumsum(a))),
            'maximum_cumulative_departure_deviation_event_times':event_max,
            'MAE_per_bin':np.mean(abs(b-a)),'timing_bias_s':bias,'real_total':len(real_exits),'simulated_total':len(sim_exits),'timing_bias_definition':'sorted departures, not paired vehicle trajectories'})
    return pd.DataFrame(rows),pd.DataFrame(through)

def conditional_headway(d,label):
    q=d[d.headway.gt(0)&d.intersection.isin([2,3])&d.lane.isin([1,2])].copy()
    if 'gap' in q:q=q[q.gap.gt(0)]
    q['state']=np.where(stopped(q.speed),'STOPPED_QUEUE',np.where(q.leader.ne(''),'FOLLOWING','FREE_FLOW'))
    q['distance_band']=pd.cut(q.distance,DISTANCE_EDGES,right=False).astype(str)
    rows=[]
    for (state,phase,band),z in q.groupby(['state','phase','distance_band']):
        rows.append({'series':label,'state':state,'phase':phase,'distance_band':band,'n':len(z),'mean_ft':z.headway.mean(),'median_ft':z.headway.median(),'P25_ft':z.headway.quantile(.25),'P75_ft':z.headway.quantile(.75)})
    rows.append({'series':label,'state':'FREE_FLOW','phase':'ALL','distance_band':'ALL','n':0,'note':'Headway undefined when there is no leader; not assigned zero'})
    return pd.DataFrame(rows)

def discharge(cross,inputs,bank,label):
    rows=[]
    for (intersection,direction),controller in bank.items():
        q=cross[(cross.intersection==intersection)&(cross.direction==direction)]
        for interval in controller.intervals:
            if interval.state!='GREEN' or interval.start<0:continue
            for lane in [1,2]:
                z=q[(q.lane==lane)&q.time.between(interval.start,interval.end,inclusive='left')].sort_values('time')
                times=z.time.to_numpy()
                for rank,(before,after) in enumerate(zip(times,times[1:]),start=2):rows.append({'series':label,'intersection':intersection,'direction':direction,'lane':lane,'green_start':interval.start,'rank':rank,'headway_s':after-before,'classification':'green crossing headway; demand gaps included, not guaranteed saturation'})
    return pd.DataFrame(rows)

def release_delays(d,bank,label):
    rows=[]
    for (intersection,direction),controller in bank.items():
        approach=d[(d.intersection==intersection)&(d.direction==direction)&d.lane.isin([1,2])]
        for interval in controller.intervals:
            if interval.state!='GREEN' or interval.start<0:continue
            # Exact observed tick immediately before green, rank all approach vehicles.
            at=approach[np.isclose(approach.time,interval.start-.1,atol=1e-6)&approach.distance.between(0,100)].copy()
            for lane,z in at.groupby('lane'):
                z=z.sort_values('distance')
                for rank,a in enumerate(z.itertuples(),start=1):
                    if a.speed>STOP_FT_S:continue
                    future=d[d.id.eq(a.id)&d.time.ge(interval.start)&d.time.lt(interval.end)]
                    moving=future[future.speed.gt(STOP_FT_S)]
                    rows.append({'series':label,'intersection':intersection,'direction':direction,'lane':lane,'id':a.id,'queue_rank':rank,
                        'green_start':interval.start,'distance_ft':a.distance,'release_delay_s':float(moving.time.iloc[0]-interval.start) if len(moving) else np.nan,
                        'censored':not len(moving),'definition':'observable SIGNAL_RELEASE_DELAY, not cognitive reaction time'})
    return pd.DataFrame(rows)
