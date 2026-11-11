"""Question skills for the intake conversation (station 1, CEO 2026-11-08).

What an expert must know before a product of this family can be summarized for the architect. Venice gets the
playbook of the request's family as `context.expert_checklist` and asks about the most important topic that the
conversation has not covered yet, in the customer's words (never as a form, never several at once). The deterministic
gap detector still decides completeness; this is the consultant's knowledge, not a questionnaire shown to the
customer. Versioned: change the text -> bump SKILL_VERSION.
"""
from __future__ import annotations

SKILL_VERSION = 'question-skills/3'

_COMMON = (
    'who uses it (customer, staff, the owner) and what each one does',
    'the one thing it must do on day one (the core flow, step by step)',
)

PLAYBOOKS: dict[str, tuple[str, ...]] = {
    'web_app': _COMMON + (
        'the business rules (limits, capacities, deadlines, what happens at the edge: full, late, cancelled)',
        'what data is kept about people and who may see it',
        'who manages it and what the manager must see or change',
        'notifications the users expect (none, email, SMS/WhatsApp)',
        'money: is anything paid (online payment, deposit, subscription, invoice) or only recorded',
        'what exists today (paper, Excel, another system) and whether its data must be brought in',
        'how the owner will know it works (the number or moment that means success)',
        'look and language (colours, tone, mobile first)',
    ),
    'website': _COMMON + (
        'the goal of the site (leads, sales, information, booking) and the main call to action',
        'the pages and what each must say',
        'existing content: logo, photos, texts, prices, address, hours',
        'how visitors contact the business (form, phone, WhatsApp, map) and the REAL phone/WhatsApp number and '
        'address to show -- the builder never invents them (CEO 2026-11-09)',
        'customer reviews: only real ones the owner provides, or none',
        'look and language (colours, tone, mobile first)',
    ),
    'mobile_app': _COMMON + (
        'what must work offline or on the go',
        'what data is kept about people and who may see it',
        'notifications the users expect',
        'look and language',
    ),
    'game': (
        'the genre and the one-sentence idea (what the player does, how they win or lose)',
        'controls (keyboard, touch, mouse) and target device',
        'levels, difficulty curve and score',
        'characters and art style (pixel, cartoon, minimal) and sound/music',
        'length of one play session and what makes the player play again',
    ),
    'ai_agent': _COMMON + (
        'what the agent may decide alone and what needs a human',
        'which sources of knowledge it uses and what it must never say',
        'where it talks to people (site chat, WhatsApp, email)',
    ),
    'automation': (
        'what triggers it (time, new row, form, message)',
        'the steps in order and the systems involved',
        'what happens when a step fails and who is told',
        'how often it runs and how much data',
    ),
    'api_integration': (
        'which external system and what data moves in which direction',
        'how often and how fast it must sync',
        'what happens on conflicts or errors',
        'who owns the credentials (never asked for in chat)',
    ),
    'media': (
        'what is made: image, video, song, voice-over, and for which use',
        'length or size, format and where it will be published',
        'style references and mood, language of any text or lyrics',
        'brand elements that must appear (name, logo, colours)',
        'draft first, then the final version after approval',
    ),
    '3d_experience': (
        'what the visitor sees and does in the scene',
        'target device and performance limits',
        'models and art style, sound',
        'how it connects to a site or product',
    ),
}


def checklist(family: str | None) -> list[str]:
    """The playbook for a family; an unknown or missing family gets the web-app playbook."""
    return list(PLAYBOOKS.get(family or '', PLAYBOOKS['web_app']))
