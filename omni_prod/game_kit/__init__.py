"""148AI 2D browser games (warehouse item 134): a tested runtime, a definition schema the model writes into, an
assembler that makes one self-contained page, and game_probe, which plays the page in a real browser."""
from .assemble import build_html
from .schema import InvalidGame, KINDS, SCHEMA, validate

__all__ = ['build_html', 'InvalidGame', 'KINDS', 'SCHEMA', 'validate']
