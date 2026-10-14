from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class HumanEvaluation:
    project_id:str
    build_id:str
    satisfied:bool
    score:int
    comment:str=''
    def __post_init__(self):
        if not 1<=self.score<=5: raise ValueError('score must be 1..5')

def summarize_evaluations(items:list[HumanEvaluation])->dict:
    if not items:return {'responses':0,'satisfaction_rate':0,'avg_score':0}
    return {'responses':len(items),'satisfaction_rate':round(sum(x.satisfied for x in items)/len(items),4),'avg_score':round(sum(x.score for x in items)/len(items),2)}
