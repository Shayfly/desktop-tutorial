from __future__ import annotations
from dataclasses import dataclass, asdict
import shutil

@dataclass(frozen=True)
class GameEnginePlan:
    engine: str
    project_markers: tuple[str,...]
    headless_check: tuple[str,...]
    executable_available: bool
    supports_3d: bool=True
    supports_console_source: bool=True

    def to_dict(self): return asdict(self)

def engine_plan(engine: str) -> GameEnginePlan:
    e=engine.lower()
    if e=='godot':
        exe=shutil.which('godot4') or shutil.which('godot')
        return GameEnginePlan('godot',('project.godot',),('godot','--headless','--path','.','--quit'), bool(exe))
    if e=='unity':
        exe=shutil.which('unity-editor') or shutil.which('Unity')
        return GameEnginePlan('unity',('ProjectSettings/ProjectVersion.txt','Assets/'),('unity-editor','-batchmode','-quit','-projectPath','.'), bool(exe))
    if e=='unreal':
        exe=shutil.which('UnrealEditor') or shutil.which('UnrealEditor-Cmd')
        return GameEnginePlan('unreal',('.uproject','Config/DefaultEngine.ini'),('UnrealEditor-Cmd','PROJECT.uproject','-unattended','-nullrhi','-run=CompileAllBlueprints'), bool(exe))
    raise ValueError('engine must be godot, unity or unreal')
