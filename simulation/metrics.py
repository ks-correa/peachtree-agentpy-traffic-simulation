"""Numerical evidence, separate from Canvas and Streamlit."""
import math
import numpy as np
import pandas as pd
from .parameters import FOOT_M

class MetricRecorder:
    def __init__(self,trace=False,queue_gap=3.):
        self.times=[];self.traces=[];self.trace=trace;self.queue_gap=queue_gap
        self.speeds=[];self.headways=[];self.accelerations=[]
        self.travels=[];self.exits=[];self.section_times=[]
        self.crossings=[]

    def record(self,model):
        physical=list(model.agents);agents=[a for a in physical if getattr(a,'agent_role','TARGET')=='TARGET'];v=[a.speed for a in agents]
        threshold=getattr(model,'revision',{}).get('operational_stop_m_s',1e-6)
        stopped=sum(x<=threshold for x in v)
        speeds_ft=[x/FOOT_M for x in v]
        headway=[];queue_max=0
        for group in model.lane_groups().values():
            cluster=0
            for index,agent in enumerate(group):
                if agent.speed<=threshold:
                    if index==0 or group[index-1].speed<=threshold and group[index-1].position-group[index-1].length-agent.position<=self.queue_gap:
                        cluster+=1
                    else:cluster=1
                    queue_max=max(queue_max,cluster)
                else:cluster=0
                if index:
                    leader=group[index-1];h=leader.position-agent.position
                    if agent.agent_role=='TARGET' and model.network.next_line(agent.direction,agent.position) is not None and model.network.section(agent.direction,agent.position)>0 and model.network.section(agent.direction,agent.position)==model.network.section(leader.direction,leader.position) and agent.lane in [1,2]:
                        headway.append(h/FOOT_M)
                        self.headways.append(h/FOOT_M)
        self.speeds.extend(speeds_ft);self.accelerations.extend(a.acceleration/FOOT_M for a in agents)
        row={'simulation_time':model.simulation_time,'vehicles_entered':model.entered,
            'initial_vehicles':model.initial_count,'vehicles_active':len(physical),'vehicles_exited':model.exited,
            'requested_arrivals':model.demand.requested,'pending_arrivals':len(model.demand.pending),
            'mean_speed_ft_s':float(np.mean(speeds_ft)) if v else 0.,'median_speed_ft_s':float(np.median(speeds_ft)) if v else 0.,
            'stopped_vehicles':stopped,'stopped_fraction':stopped/len(v) if v else 0.,
            'exact_zero_stopped_vehicles':sum(x==0 for x in v),
            'exact_zero_stopped_fraction':sum(x==0 for x in v)/len(v) if v else 0.,
            'target_active':len(agents),'background_active':len(physical)-len(agents),'physical_active':len(physical),
            'mean_headway_ft':float(np.mean(headway)) if headway else np.nan,
            'travel_time_mean_s':float(np.mean([r['travel_time_s'] for r in self.travels])) if self.travels else np.nan,
            'throughput_cumulative':model.exited,'queue_proxy_vehicles':queue_max,'lane_changes':model.lane_changes,
            'north_exit_cumulative':sum(r['direction']==2 for r in self.exits),
            'south_exit_cumulative':sum(r['direction']==4 for r in self.exits),
            'braking_vehicles':sum(a.acceleration<0 for a in agents),
            'stopped_at_signal':sum(a.state=='STOPPED_SIGNAL' for a in agents),
            'hard_brakes_this_tick':model.hard_brakes_this_tick,'safety_interventions_cumulative':model.safety_interventions}
        self.times.append(row)
        if self.trace and (model.t%5==0 or model.t==0):
            self.traces.append({'time':model.simulation_time,'metrics':row,
                'agents':[{'agent_id':a.agent_id,'position':model.network.local_y(a.position,a.direction),
                    'lane':a.lane,'speed':a.speed/FOOT_M,'class':a.vehicle_class,'length_ft':a.length/FOOT_M,
                    'direction':a.direction,'state':a.state,'role':getattr(a,'agent_role','TARGET')} for a in physical],
                'signals':{f'{i}-{di}':c.at(model.simulation_time) for (i,di),c in model.controllers.items()}})

    def summary(self,model):
        speeds=np.asarray(self.speeds);headway=np.asarray(self.headways)
        return {'mean_speed_ft_s':float(speeds.mean()) if len(speeds) else 0.,
            'median_speed_ft_s':float(np.median(speeds)) if len(speeds) else 0.,
            'mean_headway_ft':float(headway.mean()) if len(headway) else np.nan,
            'mean_travel_time_s':float(np.mean([r['travel_time_s'] for r in self.travels])) if self.travels else np.nan,
            'median_travel_time_s':float(np.median([r['travel_time_s'] for r in self.travels])) if self.travels else np.nan,
            'stopped_fraction':sum(r['stopped_vehicles'] for r in self.times)/max(1,sum(r['target_active'] for r in self.times)),
            'exact_zero_stopped_fraction':sum(r['exact_zero_stopped_vehicles'] for r in self.times)/max(1,sum(r['target_active'] for r in self.times)),
            'vehicles_entered':model.entered,'initial_vehicles':model.initial_count,'vehicles_exited':model.exited,
            'vehicles_remaining':len(model.agents),'pending_arrivals':len(model.demand.pending),
            'lane_changes':model.lane_changes,'safety_interventions':model.safety_interventions,
            'mean_entry_delay_s':float(np.mean(model.demand.delays)) if model.demand.delays else 0.,
            'max_entry_delay_s':float(max(model.demand.delays)) if model.demand.delays else 0.,
            'conservation_verified':model.initial_count+model.entered==model.exited+len(model.agents)}
