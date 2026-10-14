from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from .secret_redaction import redact

@dataclass(frozen=True)
class TrainingExample:
    task: str
    input_text: str
    output_text: str
    outcome: str
    quality_score: int

    def sanitized(self) -> 'TrainingExample':
        return TrainingExample(self.task,redact(self.input_text),redact(self.output_text),self.outcome,self.quality_score)

def to_jsonl(examples:list[TrainingExample])->str:
    lines=[]
    for ex in examples:
        s=ex.sanitized()
        if s.outcome not in {'accepted','rejected','repaired'}: raise ValueError('invalid outcome')
        if not 0<=s.quality_score<=100: raise ValueError('invalid quality score')
        lines.append(json.dumps(asdict(s),ensure_ascii=False,separators=(',',':')))
    return '\n'.join(lines)+ ('\n' if lines else '')
