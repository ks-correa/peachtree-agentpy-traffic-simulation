from bisect import bisect_right
from dataclasses import dataclass

@dataclass(frozen=True)
class SignalInterval:
    start:float
    end:float
    state:str

class SignalController:
    """Observed baseline schedule; no optimization or wall-clock input."""
    def __init__(self,intersection,direction,intervals):
        self.intersection=intersection;self.direction=direction
        self.intervals=tuple(sorted(intervals,key=lambda x:x.start))
        self.starts=tuple(x.start for x in self.intervals);self.state='UNKNOWN'

    def at(self,time):
        index=bisect_right(self.starts,time+1e-9)-1
        if index<0:return 'UNKNOWN'
        interval=self.intervals[index]
        return interval.state if time<interval.end-1e-9 else 'UNKNOWN'

    def update(self,time):self.state=self.at(time);return self.state

def controllers_from_inputs(inputs):
    group={};origin=inputs['source_window_start_relative_s']
    for r in inputs['signals']:
        key=(int(r['intersection_id']),int(r['direction']))
        group.setdefault(key,[]).append(SignalInterval(float(r['t_start_s'])-origin,float(r['t_end_s'])-origin,r['state']))
    return {key:SignalController(*key,intervals) for key,intervals in group.items()}
