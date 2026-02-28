"""
Policetilstand — Markov-tilstande for en enkeltpolice.

v1.0 understøtter kun I_LIVE og DOED.
Fremtidige tilstande (INVALID, FRIPOLICE, GENKOBT) gemmes til backlog.
"""

import enum


class PolicyState(enum.Enum):
    """
    Markov-tilstand for en forsikringspolicy.

    Policen befinder sig til enhver tid i præcis én tilstand.
    Fremregningen følger sandsynlighedsfordelingen over tilstandene.
    """

    I_LIVE = "I_LIVE"
    """Policen er aktiv og forsikringstager er i live."""

    DOED = "DOED"
    """Forsikringstager er afgået ved døden."""
