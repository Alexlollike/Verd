"""
Tests for GompertzMakeham og BiometricModel.

Håndberegnede referenceværdier:
  Parametre: alpha=0.0005, beta=0.00004, sigma=0.09
  µ(40) = 0.0005 + 0.00004 * exp(0.09 * 40)
        = 0.0005 + 0.00004 * exp(3.6)
        = 0.0005 + 0.00004 * 36.59823...
        = 0.0005 + 0.001463929...
        = 0.001963929...

  µ(0) = 0.0005 + 0.00004 * exp(0) = 0.0005 + 0.00004 = 0.00054

  Overlevelsessandsynlighed ved alder 40, dt=1/12:
    p = exp(-µ(40) * 1/12) = exp(-0.001963929 / 12) = exp(-0.000163661...)
      ≈ 0.999836352...
"""

import math
import pytest

from verd.gompertz_makeham import GompertzMakeham
from verd.biometric_model import BiometricModel


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def gm() -> GompertzMakeham:
    """Typiske danske parametre (mand, G82-lignende)."""
    return GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)


# ---------------------------------------------------------------------------
# Arv og abstrakt interface
# ---------------------------------------------------------------------------

def test_er_subklasse_af_biometric_model(gm):
    assert isinstance(gm, BiometricModel)


# ---------------------------------------------------------------------------
# mortality_intensity() — µ(x) = alpha + beta * exp(sigma * x)
# ---------------------------------------------------------------------------

def test_mortality_intensity_ved_alder_0(gm):
    """
    Haandberegning: µ(0) = 0.0005 + 0.00004 * exp(0) = 0.00054.
    """
    forventet = 0.0005 + 0.00004 * math.exp(0.0)
    assert gm.mortality_intensity(0.0) == pytest.approx(forventet)


def test_mortality_intensity_ved_alder_40(gm):
    """
    Haandberegning: µ(40) = 0.0005 + 0.00004 * exp(0.09 * 40)
                           = 0.0005 + 0.00004 * 36.5982...
                           ≈ 0.001964
    """
    forventet = 0.0005 + 0.00004 * math.exp(0.09 * 40)
    assert gm.mortality_intensity(40.0) == pytest.approx(forventet)


def test_mortality_intensity_ved_alder_70(gm):
    """
    Haandberegning: µ(70) = 0.0005 + 0.00004 * exp(0.09 * 70)
                           = 0.0005 + 0.00004 * exp(6.3)
                           = 0.0005 + 0.00004 * 544.572...
                           ≈ 0.02228
    """
    forventet = 0.0005 + 0.00004 * math.exp(0.09 * 70)
    assert gm.mortality_intensity(70.0) == pytest.approx(forventet)


def test_mortality_intensity_er_positiv_for_alle_aldre(gm):
    for alder in [0, 10, 30, 50, 70, 90, 110]:
        assert gm.mortality_intensity(float(alder)) > 0.0


def test_mortality_intensity_vokser_med_alder(gm):
    """Intensiteten skal stige monotont med alderen (Gompertz-led dominerer)."""
    aldre = [20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    intensiteter = [gm.mortality_intensity(x) for x in aldre]
    for i in range(len(intensiteter) - 1):
        assert intensiteter[i] < intensiteter[i + 1]


def test_mortality_intensity_kun_makeham_led_naar_beta_er_nul():
    """
    Når beta=0 reducerer modellen til konstant intensitet = alpha (Makeham-model).
    µ(x) = alpha + 0 * exp(sigma * x) = alpha for alle x.
    """
    gm_makeham = GompertzMakeham(alpha=0.001, beta=0.0, sigma=0.09)
    for alder in [0.0, 30.0, 60.0, 90.0]:
        assert gm_makeham.mortality_intensity(alder) == pytest.approx(0.001)


def test_mortality_intensity_parametre_gemt_korrekt(gm):
    assert gm.alpha == pytest.approx(0.0005)
    assert gm.beta == pytest.approx(0.00004)
    assert gm.sigma == pytest.approx(0.09)


# ---------------------------------------------------------------------------
# survival_probability() — arvet fra BiometricModel
# p(x, dt) = exp(-µ(x) * dt)
# ---------------------------------------------------------------------------

def test_survival_probability_ved_alder_40_dt_maaned(gm):
    """
    Haandberegning:
      µ(40) ≈ 0.001963929
      p = exp(-0.001963929 / 12) = exp(-0.000163661) ≈ 0.999836352
    """
    mu = gm.mortality_intensity(40.0)
    forventet = math.exp(-mu * (1 / 12))
    assert gm.survival_probability(40.0, 1 / 12) == pytest.approx(forventet)


def test_survival_probability_er_mellem_0_og_1(gm):
    for alder in [20.0, 40.0, 60.0, 80.0, 100.0]:
        p = gm.survival_probability(alder, 1 / 12)
        assert 0.0 < p <= 1.0


def test_survival_probability_nul_intensitet_giver_1():
    """Med alpha=beta=0 er µ(x)=0 → overlevelsessandsynlighed = 1."""
    gm_nul = GompertzMakeham(alpha=0.0, beta=0.0, sigma=0.09)
    assert gm_nul.survival_probability(50.0, 1 / 12) == pytest.approx(1.0)


def test_survival_probability_falder_med_alder(gm):
    """Højere alder → lavere overlevelsessandsynlighed over samme dt."""
    p_ung = gm.survival_probability(30.0, 1 / 12)
    p_gammel = gm.survival_probability(80.0, 1 / 12)
    assert p_ung > p_gammel


def test_survival_probability_falder_med_storre_dt(gm):
    """Længere tidsinterval → lavere overlevelsessandsynlighed."""
    p_kort = gm.survival_probability(50.0, 1 / 12)
    p_lang = gm.survival_probability(50.0, 1.0)
    assert p_kort > p_lang


# ---------------------------------------------------------------------------
# death_probability() — arvet fra BiometricModel
# q(x, dt) = 1 - p(x, dt)
# ---------------------------------------------------------------------------

def test_death_probability_komplement_til_survival(gm):
    """p + q = 1 for alle aldre og dt."""
    for alder in [30.0, 50.0, 70.0]:
        p = gm.survival_probability(alder, 1 / 12)
        q = gm.death_probability(alder, 1 / 12)
        assert p + q == pytest.approx(1.0)


def test_death_probability_er_mellem_0_og_1(gm):
    for alder in [20.0, 50.0, 90.0]:
        q = gm.death_probability(alder, 1 / 12)
        assert 0.0 <= q < 1.0


def test_death_probability_nul_intensitet_giver_0():
    """Med µ=0 er dødssandsynligheden 0."""
    gm_nul = GompertzMakeham(alpha=0.0, beta=0.0, sigma=0.09)
    assert gm_nul.death_probability(50.0, 1 / 12) == pytest.approx(0.0)
