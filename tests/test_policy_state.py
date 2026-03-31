"""
Tests for PolicyState enum.
"""

import pytest
from verd.policy_state import PolicyState


def test_har_tilstanden_i_live():
    """PolicyState skal have tilstanden I_LIVE."""
    assert PolicyState.I_LIVE is not None


def test_har_tilstanden_doed():
    """PolicyState skal have tilstanden DOED."""
    assert PolicyState.DOED is not None


def test_i_live_og_doed_er_forskellige():
    assert PolicyState.I_LIVE != PolicyState.DOED


def test_vaerdier_er_strenge():
    """Enum-værdier bruges som strenge i output og serialisering."""
    assert PolicyState.I_LIVE.value == "I_LIVE"
    assert PolicyState.DOED.value == "DOED"


def test_kun_to_tilstande_i_v1():
    """v1.0 definerer præcis to Markov-tilstande."""
    tilstande = list(PolicyState)
    assert len(tilstande) == 2


def test_opslag_fra_streng():
    """Tilstand skal kunne slås op fra strengværdi (nyttigt ved deserialisering)."""
    assert PolicyState("I_LIVE") is PolicyState.I_LIVE
    assert PolicyState("DOED") is PolicyState.DOED
