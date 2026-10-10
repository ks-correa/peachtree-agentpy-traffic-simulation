"""B2 control association and queue measurement; never supplies vehicle dynamics."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from itertools import groupby
from simulation.parameters import FOOT_M
from simulation.training_data import require_train, load_inputs
from simulation.signals import controllers_from_inputs

STOP = .1 / FOOT_M
KEY = ['intersection', 'direction', 'lane']

def bumpers(y, length, direction):
    sign = np.where(np.asarray(direction) == 2, 1., -1.)
    return y, y-sign*length/2, y-sign*length

@dataclass(frozen=True)
class SignalControlEnvelope:
    intersection: int
    direction: int
    lane: int
    approach_start: float
    entry: float
    exit: float
    discharge_end: float
    stop_low: float = np.nan
    stop_high: float = np.nan

    def contains(self, y):
        return min(self.approach_start,self.exit) <= y <= max(self.approach_start,self.exit)

    def zone(self, y):
        if min(self.entry,self.exit) <= y <= max(self.entry,self.exit):return 'INTERSECTION_INTERIOR'
        if self.stop_low <= y <= self.stop_high:return 'STOP_ZONE'
        if self.contains(y):return 'APPROACH_ZONE'
        if min(self.exit,self.discharge_end)<=y<=max(self.exit,self.discharge_end):return 'DISCHARGE_ZONE'
        return 'OUTSIDE'

def associate(d, envelopes, acquisition='B2'):
    require_train(acquisition)
    d=d.copy();d['intersection']=0;d['zone']='OUTSIDE';d['phase']='UNCONTROLLED';d['control_entry']=np.nan;d['control_exit']=np.nan;d['discharge_intersection']=0
    bank=controllers_from_inputs(load_inputs())
    for e in envelopes:
        discharge=d.direction.eq(e.direction)&d.lane.eq(e.lane)&d.y.between(min(e.exit,e.discharge_end),max(e.exit,e.discharge_end))
        d.loc[discharge,'discharge_intersection']=e.intersection
        mask=d.direction.eq(e.direction)&d.lane.eq(e.lane)&d.y.between(min(e.approach_start,e.exit),max(e.approach_start,e.exit))
        d.loc[mask,'intersection']=e.intersection
        d.loc[mask,'control_entry']=e.entry;d.loc[mask,'control_exit']=e.exit
        d.loc[mask,'zone']=[e.zone(y) for y in d.loc[mask,'y']]
        d.loc[mask,'phase']=[bank[(e.intersection,e.direction)].at(t) for t in d.loc[mask,'time']]
    d['stopped']=d.speed.le(STOP)
    d['front'],d['center'],d['rear']=bumpers(d.y,d.length,d.direction)
    return d

def queue_snapshot(g, gap_ft):
    """Front-most same-lane stopped chain. A moving front blocks head attribution.

    Actual Following, when present, must agree with the adjacent spatial vehicle.
    No gap/threshold is estimated here; frozen B2 standstill threshold is passed in.
    """
    if g.empty:return []
    g=g.sort_values('y',ascending=int(g.direction.iloc[0])==4)
    return _chain(list(g.itertuples()),gap_ft)

def _chain(rows,gap_ft):
    head=rows[0]
    if head.speed>STOP:return []
    if hasattr(head,'movement') and head.movement!=1:return []
    # The inherited 100-ft head window is measured from OBSERVED ENTRY,
    # not from the earlier nominal proxy. It is not changed or fitted.
    if hasattr(head,'control_entry') and abs(head.y-head.control_entry)>100:return []
    chain=[head]
    for follower in rows[1:]:
        leader=chain[-1]
        gap=abs(leader.y-follower.y)-leader.length
        if follower.speed>STOP or gap<-.01 or gap>gap_ft:break
        if hasattr(leader,'following') and leader.following>0:
            if str(follower.id)!='B2:'+str(int(leader.following)):break
        chain.append(follower)
    return chain

def queue_series(d, gap_ft):
    records=[];members=[]
    eligible=d[d.intersection.isin([2,3])&d.lane.isin([1,2])].copy()
    eligible['order']=eligible.y*np.where(eligible.direction.eq(2),-1,1)
    eligible=eligible.sort_values(['frame']+KEY+['order'])
    key=lambda a:(a.frame,a.intersection,a.direction,a.lane)
    for keys,items in groupby(eligible.itertuples(index=False),key):
        rows=list(items);chain=_chain(rows,gap_ft);frame,i,di,lane=keys
        row={'frame':frame,'time':rows[0].time,'intersection':i,'direction':di,'lane':lane,'phase':rows[0].phase,
             'queue':len(chain),'spatial_ft':abs(chain[0].y-chain[-1].rear) if chain else 0.,
             'head_id':chain[0].id if chain else '', 'head_y':chain[0].y if chain else np.nan}
        records.append(row)
        for rank,a in enumerate(chain,1):
            members.append(dict(row,id=a.id,rank=rank,y=a.y,length=a.length,front=a.front,rear=a.rear))
    return pd.DataFrame(records),pd.DataFrame(members)

def onset(track, start, end):
    q=track[track.time.ge(start-1e-7)&track.time.lt(end)]
    # A release requires adjacent recorded samples, not a censored jump.
    if q.empty or abs(q.time.iloc[0]-start)>.11:return np.nan
    moving=q[q.speed.gt(STOP)]
    if moving.empty:return np.nan
    t=moving.time.iloc[0]
    seq=q[q.time.le(t)]
    if seq.time.diff().dropna().gt(.11).any():return np.nan
    return float(t-start)

def dynamics(d, q, members):
    bank=controllers_from_inputs(load_inputs());tracks={k:g.sort_values('time') for k,g in d.groupby('id')}
    snapshots={k:dict(zip(np.rint(g.time*10).astype(int),g.speed.to_numpy())) for k,g in tracks.items()}
    residual=[];propagation=[];heads=[]
    for (i,di),control in bank.items():
        intervals=control.intervals
        for cycle,red in enumerate(intervals):
            if red.state!='RED':continue
            green=next((a for a in intervals[cycle+1:] if a.state=='GREEN'),None)
            if green is None or green.start-red.end>5:continue
            for lane in [1,2]:
                group=q[q.intersection.eq(i)&q.direction.eq(di)&q.lane.eq(lane)]
                r=group[group.time.ge(red.start)&group.time.lt(red.end)&group.queue.gt(0)]
                if r.empty:continue
                # Cycle estimate is a median of the same first physical head's stopped samples.
                for hid,h in r.groupby('head_id'):
                    heads.append({'intersection':i,'direction':di,'lane':lane,'cycle':cycle,'id':hid,
                        'time':h.time.iloc[0],'position_y':h.head_y.median(),'front_bumper_position':h.head_y.median(),
                        'first_observed_position_y':h.head_y.iloc[0],
                        'left_censored':h.time.iloc[0]<=.05 or red.start<0,
                        'within_cycle_SD_ft':h.head_y.std(),'n_frames':len(h),'red_start':red.start,'red_end':red.end})
                prior=group[(group.time-green.start+.1).abs().lt(.051)]
                if prior.empty:continue
                base=prior.iloc[-1]
                chain=members[members.frame.eq(base.frame)&members.intersection.eq(i)&members.direction.eq(di)&members.lane.eq(lane)].sort_values('rank')
                if chain.empty:continue
                delays={a.id:onset(tracks[a.id],green.start,green.end) for a in chain.itertuples()}
                observed_end=min([tracks[a.id].time.max() for a in chain.itertuples()]+[green.end-.1])
                counts=[]
                for offset in [5.,10.]:
                    vals=[]
                    for a in chain.itertuples():
                        speed=snapshots[a.id].get(round((green.start+offset)*10))
                        vals.append(bool(speed<=STOP) if speed is not None else None)
                    counts.append(sum(vals) if all(x is not None for x in vals) else np.nan)
                # Clearance: first simultaneous snapshot where every onset-cohort member is observed moving.
                clearance=np.nan
                for t in np.round(np.arange(green.start,observed_end+.05,.1),1):
                    speeds=[snapshots[a.id].get(round(t*10),np.nan) for a in chain.itertuples()]
                    if all(x>STOP for x in speeds):clearance=float(t-green.start);break
                first=chain.iloc[0].id
                discharge=[]
                for a in chain.itertuples():
                    track=tracks[a.id];track=track[track.time.ge(green.start)&track.time.lt(green.end)]
                    sign=1 if di==2 else -1
                    references=tracks[a.id].loc[tracks[a.id].intersection.eq(i),'control_exit'].dropna()
                    exit_reference=references.iloc[0] if len(references) else np.nan
                    passed=track[(track.y-exit_reference)*sign>=0]
                    discharge.append(passed.time.iloc[0]-green.start if len(passed) else np.nan)
                discharge_clearance=max(discharge) if all(np.isfinite(x) for x in discharge) else np.nan
                residual.append({'intersection':i,'direction':di,'lane':lane,'cycle':cycle,'green_start':green.start,
                    'queue_at_green_onset':len(chain),'time_to_first_release_s':delays[first],
                    'time_to_stopped_queue_clearance_s':clearance,
                    'time_to_queue_clearance_s':discharge_clearance,'clearance_censored':not np.isfinite(discharge_clearance),
                    'remaining_stopped_after_5s':counts[0],'remaining_stopped_after_10s':counts[1]})
                last=None
                for a in chain.itertuples():
                    if last is not None:
                        propagation.append({'intersection':i,'direction':di,'lane':lane,'cycle':cycle,'leader':last.id,'follower':a.id,
                            'rank':a.rank,'queue_start_headway_s':delays[a.id]-delays[last.id],
                            'leader_release_s':delays[last.id],'follower_release_s':delays[a.id],
                            'censored':not np.isfinite(delays[a.id]-delays[last.id])})
                    last=a
    return pd.DataFrame(heads),pd.DataFrame(residual),pd.DataFrame(propagation)
