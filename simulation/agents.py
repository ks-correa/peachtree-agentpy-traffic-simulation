"""VehicleAgent is a real AgentPy agent, with no historical trajectory handle."""
import math
import agentpy as ap

def idm_acceleration(speed,gap,leader_speed,p):
    free=p.a*(1-(max(speed,0)/p.v0)**p.delta)
    if gap is None:return free
    closing=speed-leader_speed
    desired=p.s0+max(0.,speed*p.T+speed*closing/(2*math.sqrt(p.a*p.b)))
    return free-p.a*(desired/max(gap,1e-6))**2

def ballistic(speed,acceleration,dt):
    """Stop inside the tick rather than integrating to a negative speed."""
    if acceleration<0 and speed+acceleration*dt<0:
        return -speed*speed/(2*acceleration),0.
    return speed*dt+.5*acceleration*dt*dt,max(0.,speed+acceleration*dt)

def acceleration_for_max_distance(speed,acceleration,distance,dt):
    displacement,_=ballistic(speed,acceleration,dt)
    if displacement<=distance+1e-12:return acceleration
    if distance<0:raise RuntimeError('Negative admissible movement: invalid initial overlap')
    if speed==0:return min(acceleration,2*distance/(dt*dt))
    if distance>=speed*dt/2:return 2*(distance-speed*dt)/(dt*dt)
    if distance<=1e-12:return -speed*speed/(2e-12)
    return -speed*speed/(2*distance)

class VehicleAgent(ap.Agent):
    def setup(self,data,synthetic_id,entry_time=0.,initial=False):
        self.agent_id=synthetic_id
        self.vehicle_class=int(data['vehicle_class']);self.length=float(data['length_m']);self.width=float(data['width_m'])
        self.position=float(data.get('position_m',0.));self.lane=int(data['lane'])
        self.speed=float(data['speed_m_s']);self.acceleration=0.
        self.movement=int(data.get('movement',1));self.direction=int(data['direction'])
        self.leader_id=None;self.follower_id=None
        self.entry_time=None if initial else float(entry_time);self.exit_time=None
        self.state='ENTERING';self.initial=initial;self.yellow_decisions={};self.last_lane_change=-1e9
        self.initial_age_s=float(data.get('initial_age_s',0.))
        self.section_entry_times={};self.crossed_lines=set()
        self.agent_role=data.get('agent_role','TARGET');self.release_until=-1e9

    def decision(self,snapshot,leader,line,state,time,p):
        mine=snapshot[self.agent_id];v=mine['speed'];x=mine['position']
        acceleration=idm_acceleration(v,None,0.,p)
        restriction=False
        if leader is not None:
            front=snapshot[leader.agent_id]
            acceleration=min(acceleration,idm_acceleration(v,front['position']-leader.length-x,front['speed'],p))
        if line is not None:
            distance=line.progress_m-x
            stop=state=='RED'
            if state=='YELLOW':
                key=(line.intersection,self.direction)
                if key not in self.yellow_decisions:
                    self.yellow_decisions[key]=distance>=p.s0+v*v/(2*p.b)
                stop=self.yellow_decisions[key]
            else:self.yellow_decisions.pop((line.intersection,self.direction),None)
            if state=='UNKNOWN':raise RuntimeError('Unknown signal in authorized simulation window')
            if stop:
                acceleration=min(acceleration,idm_acceleration(v,distance,0.,p));restriction=True
        return acceleration,restriction
