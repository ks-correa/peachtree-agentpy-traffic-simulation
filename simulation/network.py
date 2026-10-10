"""Approved logical geometry; progress is front-center distance in SI."""
from dataclasses import dataclass
from .parameters import FOOT_M

@dataclass(frozen=True)
class StopLine:
    intersection:int
    direction:int
    progress_m:float
    local_y_ft:float

class PeachtreeEnvironment:
    def __init__(self,spec):
        self.y_min_ft=float(spec['y_min_ft']);self.y_max_ft=float(spec['y_max_ft'])
        self.length=(self.y_max_ft-self.y_min_ft)*FOOT_M
        self.main_lanes=tuple(spec.get('main_lanes',[1,2]))
        self.stop_lines=tuple(StopLine(int(r['intersection']),int(r['direction']),
            self.progress(float(r['local_y_ft']),int(r['direction'])),float(r['local_y_ft'])) for r in spec['stop_lines'])
        # Previously reconstructed observed extents; not surveyed stop bars.
        self.intersection_extents={2:(630.810,777.753),3:(1155.863,1246.452)}
        self.bay_connectors=spec.get('bay_connectors',[])

    def progress(self,y_ft,direction):
        return (y_ft-self.y_min_ft if direction==2 else self.y_max_ft-y_ft)*FOOT_M

    def local_y(self,progress,direction):
        return self.y_min_ft+progress/FOOT_M if direction==2 else self.y_max_ft-progress/FOOT_M

    def next_line(self,direction,progress):
        return next((s for s in sorted(self.stop_lines,key=lambda s:s.progress_m)
            if s.direction==direction and s.progress_m>progress+1e-8),None)

    def section(self,direction,progress):
        y=self.local_y(progress,direction)
        for lower,upper in self.intersection_extents.values():
            if lower<=y<=upper:return 0
        return 2 if y<630.810 else 3 if y<1155.863 else 4

    def boundary(self,direction,entry=False):
        return ('SOUTH_CUT' if direction==2 else 'NORTH_CUT') if entry else ('NORTH_CUT' if direction==2 else 'SOUTH_CUT')
