"""
Tests for DeterministicMarket og FinancialMarket.

Håndberegnede referenceværdier:
  r=0.05, enhedspris_0=100.0
  enhedspris(0)  = 100 * exp(0)       = 100.0
  enhedspris(1)  = 100 * exp(0.05)    = 100 * 1.05127... = 105.127...
  enhedspris(10) = 100 * exp(0.5)     = 100 * 1.64872... = 164.872...
"""

import math
import pytest

from verd.deterministic_market import DeterministicMarket
from verd.financial_market import FinancialMarket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def marked() -> DeterministicMarket:
    """5 % kontinuert rente, enhedspris 100 DKK ved t=0."""
    return DeterministicMarket(r=0.05, enhedspris_0=100.0)


@pytest.fixture
def marked_standard() -> DeterministicMarket:
    """Standard enhedspris_0=1.0 (default)."""
    return DeterministicMarket(r=0.05)


# ---------------------------------------------------------------------------
# Arv og abstrakt interface
# ---------------------------------------------------------------------------

def test_er_subklasse_af_financial_market(marked):
    assert isinstance(marked, FinancialMarket)


# ---------------------------------------------------------------------------
# enhedspris() — P(t) = P0 * exp(r * t)
# ---------------------------------------------------------------------------

def test_enhedspris_ved_t_0_er_enhedspris_0(marked):
    """Haandberegning: P(0) = 100 * exp(0) = 100."""
    assert marked.enhedspris(0.0) == pytest.approx(100.0)


def test_enhedspris_ved_t_1(marked):
    """
    Haandberegning: P(1) = 100 * exp(0.05) = 100 * 1.05127110... = 105.127...
    """
    forventet = 100.0 * math.exp(0.05 * 1.0)
    assert marked.enhedspris(1.0) == pytest.approx(forventet)


def test_enhedspris_ved_t_10(marked):
    """
    Haandberegning: P(10) = 100 * exp(0.5) = 164.872...
    """
    forventet = 100.0 * math.exp(0.05 * 10.0)
    assert marked.enhedspris(10.0) == pytest.approx(forventet)


def test_enhedspris_vokser_med_t(marked):
    """Enhedsprisen skal stige monotont ved positiv rente."""
    tidspunkter = [0.0, 1.0, 5.0, 10.0, 20.0, 30.0]
    priser = [marked.enhedspris(t) for t in tidspunkter]
    for i in range(len(priser) - 1):
        assert priser[i] < priser[i + 1]


def test_enhedspris_er_altid_positiv(marked):
    for t in [0.0, 1.0, 10.0, 40.0]:
        assert marked.enhedspris(t) > 0.0


def test_enhedspris_default_enhedspris_0_er_1(marked_standard):
    """Default enhedspris_0 = 1.0."""
    assert marked_standard.enhedspris(0.0) == pytest.approx(1.0)


def test_enhedspris_nul_rente_er_konstant():
    """Med r=0 er enhedsprisen konstant = enhedspris_0 for alle t."""
    marked_nul = DeterministicMarket(r=0.0, enhedspris_0=50.0)
    for t in [0.0, 1.0, 10.0, 30.0]:
        assert marked_nul.enhedspris(t) == pytest.approx(50.0)


def test_enhedspris_parametre_gemt_korrekt(marked):
    assert marked.r == pytest.approx(0.05)
    assert marked.enhedspris_0 == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# dkk_til_enheder() — arvet fra FinancialMarket
# enheder = DKK / enhedspris(t)
# ---------------------------------------------------------------------------

def test_dkk_til_enheder_ved_t_0(marked):
    """
    Haandberegning: 1000 DKK / 100 DKK/enhed = 10 enheder.
    """
    assert marked.dkk_til_enheder(1000.0, 0.0) == pytest.approx(10.0)


def test_dkk_til_enheder_ved_t_1(marked):
    """
    Haandberegning: 1000 / (100 * exp(0.05)) = 1000 / 105.127... ≈ 9.512...
    """
    forventet = 1000.0 / marked.enhedspris(1.0)
    assert marked.dkk_til_enheder(1000.0, 1.0) == pytest.approx(forventet)


def test_dkk_til_enheder_nul_dkk(marked):
    assert marked.dkk_til_enheder(0.0, 0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# enheder_til_dkk() — arvet fra FinancialMarket
# DKK = enheder * enhedspris(t)
# ---------------------------------------------------------------------------

def test_enheder_til_dkk_ved_t_0(marked):
    """
    Haandberegning: 10 enheder * 100 DKK/enhed = 1000 DKK.
    """
    assert marked.enheder_til_dkk(10.0, 0.0) == pytest.approx(1000.0)


def test_enheder_til_dkk_ved_t_1(marked):
    """
    Haandberegning: 10 * (100 * exp(0.05)) = 10 * 105.127... = 1051.27...
    """
    forventet = 10.0 * marked.enhedspris(1.0)
    assert marked.enheder_til_dkk(10.0, 1.0) == pytest.approx(forventet)


def test_enheder_til_dkk_nul_enheder(marked):
    assert marked.enheder_til_dkk(0.0, 5.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Round-trip: DKK → enheder → DKK
# ---------------------------------------------------------------------------

def test_roundtrip_dkk_til_enheder_til_dkk(marked):
    """
    Konvertering frem og tilbage skal give det originale beløb:
      DKK → enheder → DKK = DKK
    """
    original_dkk = 12345.67
    for t in [0.0, 1.0, 5.0, 10.0]:
        enheder = marked.dkk_til_enheder(original_dkk, t)
        gendannet = marked.enheder_til_dkk(enheder, t)
        assert gendannet == pytest.approx(original_dkk)


def test_roundtrip_enheder_til_dkk_til_enheder(marked):
    """
    Konvertering frem og tilbage skal give det originale antal enheder.
    """
    original_enheder = 987.654
    for t in [0.0, 2.0, 7.0]:
        dkk = marked.enheder_til_dkk(original_enheder, t)
        gendannet = marked.dkk_til_enheder(dkk, t)
        assert gendannet == pytest.approx(original_enheder)
