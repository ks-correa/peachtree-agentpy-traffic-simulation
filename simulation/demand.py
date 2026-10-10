from collections import deque

class DemandStream:
    def __init__(self,inputs):
        if inputs.get('acquisition_id')!='B2':raise PermissionError('Development demand must be B2; B1 LOCKED')
        self.events=deque(sorted(inputs['entries'],key=lambda r:r['requested_time_s']))
        self.pending=[];self.speed_samples=inputs['entry_speed_samples_m_s']
        self.requested=0;self.delays=[]

    def due(self,time):
        while self.events and self.events[0]['requested_time_s']<=time+1e-9:
            event=dict(self.events.popleft());self.pending.append(event);self.requested+=1
        return self.pending

    def sample_speed(self,direction,rng):
        return float(rng.choice(self.speed_samples[str(direction)]))
