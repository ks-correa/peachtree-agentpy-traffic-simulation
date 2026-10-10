"""AgentPy owns the lifecycle. All decisions use one immutable tick snapshot."""
import math,time
import agentpy as ap
from .agents import VehicleAgent,ballistic,acceleration_for_max_distance
from .parameters import IDMParameters,DT,FOOT_M
from .network import PeachtreeEnvironment
from .signals import controllers_from_inputs
from .demand import DemandStream
from .metrics import MetricRecorder

STEP_ORDER=('signals','arrivals','leaders_followers','lane_changes','accelerations','velocities','positions','boundary_crossings','EXITED','metrics')

class PhysicsInvariantError(RuntimeError):pass

class PeachtreeModel(ap.Model):
    def setup(self,inputs,idm,trace=False,queue_gap=3.):
        if float(inputs['dt'])!=DT:raise ValueError('One AgentPy step must be exactly0.1s')
        self.inputs=inputs;self.idm=idm;self.dt=DT;self.simulation_time=0.
        self.network=PeachtreeEnvironment(inputs['network']);self.controllers=controllers_from_inputs(inputs)
        self.demand=DemandStream(inputs);self.agents=ap.AgentList(self);self.all_agents=[]
        self.entered=0;self.exited=0;self.initial_count=len(inputs['initial']);self.counter=0
        self.lane_changes=0;self.safety_interventions=0;self.hard_brakes_this_tick=0
        self.recorder=MetricRecorder(trace,queue_gap)
        self.revision=inputs.get('revision',{});self.release_events=[]
        for data in inputs['initial']:self.create_agent(data,0.,True)
        for controller in self.controllers.values():controller.update(0.)
        self.refresh_relations();self.assert_invariants()

    def create_agent(self,data,entry_time,initial=False):
        self.counter+=1
        agent=VehicleAgent(self,data=dict(data),synthetic_id=f'SIM-{self.counter:05d}',entry_time=entry_time,initial=initial)
        self.agents.append(agent);self.all_agents.append(agent)
        return agent

    def lane_groups(self):
        groups={}
        for agent in self.agents:groups.setdefault((agent.direction,agent.lane),[]).append(agent)
        for group in groups.values():group.sort(key=lambda a:(-a.position,a.agent_id))
        return groups

    def refresh_relations(self):
        self.leaders={}
        for group in self.lane_groups().values():
            for index,agent in enumerate(group):
                leader=group[index-1] if index else None;follower=group[index+1] if index+1<len(group) else None
                agent.leader_id=leader.agent_id if leader else None;agent.follower_id=follower.agent_id if follower else None
                self.leaders[agent.agent_id]=leader

    def insert_arrivals(self,time0):
        remaining=[];blocked=set()
        for event in self.demand.due(time0):
            if '_sampled_speed' not in event:event['_sampled_speed']=self.demand.sample_speed(event['direction'],self.random)
            key=(event['direction'],event['lane'])
            if self.revision.get('safe_insertion_fifo',False) and key in blocked:
                remaining.append(event);continue
            group=self.lane_groups().get((event['direction'],event['lane']),[])
            near=group[-1] if group else None;speed=event['_sampled_speed']
            # Safe boundary insertion is an observable delay, not a forced position.
            required=self.idm.s0+max(0.,speed*speed-(near.speed*near.speed if near else 0.))/(2*self.idm.b)
            if near and near.position-near.length<required:
                remaining.append(event);blocked.add(key);continue
            data={**event,'speed_m_s':speed,'position_m':0.}
            self.create_agent(data,time0,False);self.entered+=1
            self.demand.delays.append(time0-event['requested_time_s'])
        self.demand.pending=remaining

    def plan_lane_changes(self,time0):
        # Sparse TRAIN sample does not support a stable discretionary model.
        # Only the logical through connector11 must merge into regular lane1.
        snapshot=list(self.agents);proposals=[]
        for agent in snapshot:
            if agent.lane!=11:continue
            target=[x for x in snapshot if x.direction==agent.direction and x.lane==1]
            ahead=sorted([x for x in target if x.position>agent.position],key=lambda x:x.position)
            behind=sorted([x for x in target if x.position<=agent.position],key=lambda x:-x.position)
            front_gap=ahead[0].position-ahead[0].length-agent.position if ahead else math.inf
            back_gap=agent.position-agent.length-behind[0].position if behind else math.inf
            if front_gap>=self.idm.s0+agent.speed*self.idm.T and back_gap>=self.idm.s0+(behind[0].speed*self.idm.T if behind else 0.):
                proposals.append(agent)
        for agent in sorted(proposals,key=lambda a:(-a.position,a.agent_id)):
            if all(x.direction!=agent.direction or x.lane!=1 or abs(x.position-agent.position)>max(x.length,agent.length)+self.idm.s0 for x in self.agents):
                agent.lane=1;agent.last_lane_change=time0;self.lane_changes+=1

    def step(self):
        time0=(self.t-1)*self.dt
        prior_signal={key:c.state for key,c in self.controllers.items()}
        for controller in self.controllers.values():controller.update(time0)
        self.insert_arrivals(time0);self.refresh_relations();self.plan_lane_changes(time0);self.refresh_relations()
        if self.revision.get('signal_release_delay_s',0)>0:
            self.assign_release_holds(time0,prior_signal)
        snapshot={a.agent_id:{'position':a.position,'speed':a.speed} for a in self.agents}
        candidate={};restriction={};lines={}
        for agent in self.agents:
            line=self.network.next_line(agent.direction,agent.position)
            state=self.controllers[(line.intersection,agent.direction)].state if line else 'GREEN'
            candidate[agent.agent_id],restriction[agent.agent_id]=agent.decision(snapshot,self.leaders[agent.agent_id],line,state,time0,self.idm)
            if time0<agent.release_until-1e-9:
                # A measured observable release hold; brake through acceleration,
                # never set a historical position or a historical speed.
                candidate[agent.agent_id]=min(candidate[agent.agent_id],-agent.speed/self.dt)
                restriction[agent.agent_id]=True
            lines[agent.agent_id]=line
        advances={};new_speeds={};final_acc={};self.hard_brakes_this_tick=0
        # A simultaneous feasibility constraint propagates along spatial chains.
        # It limits acceleration, never overwrites or teleports a position.
        for group in self.lane_groups().values():
            for index,agent in enumerate(group):
                a=candidate[agent.agent_id];allow=math.inf
                if index:
                    leader=group[index-1];gap=snapshot[leader.agent_id]['position']-leader.length-snapshot[agent.agent_id]['position']
                    allow=max(0.,gap+advances[leader.agent_id]-1e-7)
                if restriction[agent.agent_id]:allow=min(allow,max(0.,lines[agent.agent_id].progress_m-agent.position-1e-7))
                adjusted=acceleration_for_max_distance(agent.speed,a,allow,self.dt)
                if adjusted<a-1e-7:self.safety_interventions+=1
                if adjusted<-9.:self.hard_brakes_this_tick+=1 # Literature-scale emergency diagnostic, not fitted parameter.
                dx,v=ballistic(agent.speed,adjusted,self.dt)
                advances[agent.agent_id]=dx;new_speeds[agent.agent_id]=v;final_acc[agent.agent_id]=adjusted
        exited=[]
        for agent in list(self.agents):
            old=agent.position;v=snapshot[agent.agent_id]['speed'];a=final_acc[agent.agent_id]
            agent.acceleration=a;agent.speed=new_speeds[agent.agent_id];agent.position=old+advances[agent.agent_id]
            if agent.position>=self.network.length:
                d=max(0.,self.network.length-old);disc=max(0.,v*v+2*a*d)
                travel_in_tick=2*d/(v+math.sqrt(disc)) if v+math.sqrt(disc)>0 else 0.
                agent.exit_time=time0+min(self.dt,max(0.,travel_in_tick));agent.state='EXITED'
                self.exited+=1;exited.append(agent)
                boundary=self.network.boundary(agent.direction)
                self.recorder.exits.append({'agent_id':agent.agent_id,'boundary':boundary,'direction':agent.direction,'exit_time_s':agent.exit_time})
                if not agent.initial and agent.agent_role=='TARGET':
                    self.recorder.travels.append({'agent_id':agent.agent_id,'direction':agent.direction,'travel_time_s':agent.exit_time-agent.entry_time,'entry_time_s':agent.entry_time,'exit_time_s':agent.exit_time})
            elif agent.last_lane_change>=time0-1e-9:agent.state='LANE_CHANGING'
            elif agent.speed<=self.revision.get('operational_stop_m_s',1e-6) and restriction[agent.agent_id]:agent.state='STOPPED_SIGNAL'
            elif self.leaders[agent.agent_id] is not None:agent.state='FOLLOWING'
            else:agent.state='FREE_FLOW'
            for line in self.network.stop_lines:
                if line.direction==agent.direction and old<line.progress_m<=agent.position:
                    key=line.intersection
                    if key not in agent.crossed_lines:
                        agent.crossed_lines.add(key)
                        self.recorder.crossings.append({'agent_id':agent.agent_id,'intersection':key,'direction':agent.direction,'time_s':time0+self.dt})
                        if len(agent.crossed_lines)==2:
                            prior=next(r for r in reversed(self.recorder.crossings[:-1]) if r['agent_id']==agent.agent_id)
                            self.recorder.section_times.append({'agent_id':agent.agent_id,'direction':agent.direction,'travel_time_s':time0+self.dt-prior['time_s'],'definition':'between approved signal reference cuts'})
        for agent in exited:self.agents.remove(agent)
        self.simulation_time=self.t*self.dt;self.refresh_relations();self.assert_invariants()

    def assign_release_holds(self,time0,previous):
        heads={}
        for a in self.agents:
            line=self.network.next_line(a.direction,a.position)
            if line is None:continue
            key=(line.intersection,a.direction)
            if self.controllers[key].state!='GREEN' or previous[key] not in ['RED','YELLOW']:continue
            group=(line.intersection,a.direction,a.lane)
            if group not in heads or a.position>heads[group][0].position:heads[group]=(a,line)
        for a,line in heads.values():
            if a.speed>self.revision['operational_stop_m_s']:continue
            if (line.progress_m-a.position)/FOOT_M>self.revision['queue_head_window_ft']:continue
            hold=max(0.,self.revision['signal_release_delay_s']-self.dt)
            a.release_until=time0+hold
            self.release_events.append({'agent_id':a.agent_id,'intersection':line.intersection,'direction':a.direction,'green_onset':time0,'hold_s':hold,'source':'B2_POOLED_FIRST_HEAD_MEDIAN'})

    def update(self):self.recorder.record(self)

    def assert_invariants(self):
        for group in self.lane_groups().values():
            for index,agent in enumerate(group):
                if agent.speed<-1e-9:raise PhysicsInvariantError('Negative speed')
                if index and group[index-1].position-group[index-1].length-agent.position<-1e-8:
                    raise PhysicsInvariantError('Invalid longitudinal overlap')
        if self.initial_count+self.entered!=len(self.agents)+self.exited:raise PhysicsInvariantError('Conservation violation')

    def end(self):
        self.summary=self.recorder.summary(self)
        for name,value in self.summary.items():self.report(name,value)

def run_baseline(inputs,parameters,seed=10,trace=False,queue_gap=3.,steps=None):
    model=PeachtreeModel({'steps':int(round(inputs['horizon_s']/DT)) if steps is None else steps,'seed':int(seed)},
        inputs=inputs,idm=parameters,trace=trace,queue_gap=queue_gap)
    model.run(display=False)
    return model
