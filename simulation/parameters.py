"""SI parameters, pooled across classes 2/3; immutable to the development UI."""
from dataclasses import dataclass,asdict
import json
import math
from pathlib import Path

FOOT_M=1200/3937 # NGSIM US survey feet.
DT=.1

@dataclass(frozen=True)
class IDMParameters:
    v0:float
    T:float
    s0:float
    a:float
    b:float
    delta:float=4.

    def __post_init__(self):
        if not all(math.isfinite(v) and v>0 for v in (self.v0,self.T,self.s0,self.a,self.b,self.delta)):raise ValueError('IDM parameters must be finite and positive')

    def to_dict(self):return asdict(self)

    @classmethod
    def load(cls,path):
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        if data.get('training_acquisition')!='B2':raise ValueError('Parameters must originate exclusively in B2')
        return cls(**data['parameters'])
