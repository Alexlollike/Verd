"""
Tests for omkostning — nul_omkostning og standard_omkostning.

Håndberegnede referenceværdier:

    standard_omkostning med aum_rate=0.005, styk_aar=200:
        V_total = total_enheder × P(t)
        c(t) = 0.005 × V_total + 200  [DKK/år]

    Eksempel (P₀=100, r=0):
        100 enheder ald + 0 rate + 0 liv → V_total = 100×100 = 10,000 DKK
        c = 0.005 × 10,000 + 200 = 50 + 200 = 250 DKK/år

        1000 enheder total → V_total = 100,000 DKK
        c = 0.005 × 100,000 + 200 = 500 + 200 = 700 DKK/år

    Nul depot:
        V_total = 0 → c = 0.005 × 0 + 200 = 200 DKK/år (kun styk)
"""

import math
from datetime import date

import pytest

from verd import DeterministicMarket, Policy, nul_omkostning, standard_omkostning
from verd.policy_state import PolicyState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def marked() -> DeterministicMarket:
    """Deterministisk marked med P₀=100 DKK/enhed og nul afkast (r=0)."""
    return DeterministicMarket(r=0.0, enhedspris_0=100.0)


def _lav_police(
    ald: float = 100.0,
    rate: float = 0.0,
    liv: float = 0.0,
) -> Policy:
    return Policy(
        foedselsdato=date(1984, 1, 1),
        tegningsdato=date(2024, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="TEST",
        omkostningssats_id="STANDARD",
        loen=600_000.0,
        indbetalingsprocent=0.15,
        aldersopsparing=ald,
        ratepensionsopsparing=rate,
        ratepensionsvarighed=10,
        livrentedepot=liv,
    )


# ---------------------------------------------------------------------------
# Tests for nul_omkostning
# ---------------------------------------------------------------------------

class TestNulOmkostning:
    def test_returnerer_nul(self):
        police = _lav_police(ald=100.0)
        assert nul_omkostning(police, t=0.0) == 0.0

    def test_returnerer_nul_uanset_depot(self):
        for ald in [0.0, 1.0, 1000.0, 1_000_000.0]:
            police = _lav_police(ald=ald)
            assert nul_omkostning(police, t=5.0) == 0.0

    def test_returnerer_nul_uanset_t(self):
        police = _lav_police(ald=500.0)
        for t in [0.0, 1.0, 10.0, 30.0]:
            assert nul_omkostning(police, t=t) == 0.0


# ---------------------------------------------------------------------------
# Tests for standard_omkostning
# ---------------------------------------------------------------------------

class TestStandardOmkostning:
    def test_total_er_aum_plus_styk(self, marked: DeterministicMarket):
        """
        Håndberegning:
            100 enheder ald, P₀=100 → V_total = 10,000 DKK
            c = 0.005 × 10,000 + 200 = 50 + 200 = 250 DKK/år
        """
        police = _lav_police(ald=100.0)
        omk_func = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)
        forventet = 0.005 * 100.0 * 100.0 + 200.0  # 250.0 DKK/år
        assert omk_func(police, t=0.0) == pytest.approx(forventet)

    def test_aum_skalerer_med_depotvaerdi(self, marked: DeterministicMarket):
        """
        Håndberegning:
            1000 enheder total, P₀=100 → V_total = 100,000 DKK
            c = 0.005 × 100,000 + 200 = 500 + 200 = 700 DKK/år
        """
        police = _lav_police(ald=400.0, rate=300.0, liv=300.0)  # 1000 enheder
        omk_func = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)
        forventet = 0.005 * 1000.0 * 100.0 + 200.0  # 700.0 DKK/år
        assert omk_func(police, t=0.0) == pytest.approx(forventet)

    def test_nul_depot_giver_kun_styk(self, marked: DeterministicMarket):
        """
        Håndberegning:
            V_total = 0 → AUM = 0 → c = 0 + 200 = 200 DKK/år
        """
        police = _lav_police(ald=0.0, rate=0.0, liv=0.0)
        omk_func = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)
        assert omk_func(police, t=0.0) == pytest.approx(200.0)

    def test_nul_styk_giver_kun_aum(self, marked: DeterministicMarket):
        """
        Håndberegning:
            100 enheder, P₀=100 → V_total = 10,000 DKK
            c = 0.005 × 10,000 + 0 = 50 DKK/år
        """
        police = _lav_police(ald=100.0)
        omk_func = standard_omkostning(marked, aum_rate=0.005, styk_aar=0.0)
        assert omk_func(police, t=0.0) == pytest.approx(50.0)

    def test_stiger_med_depotvaerdi(self, marked: DeterministicMarket):
        """Større depot → højere omkostning."""
        omk_func = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)
        lille = omk_func(_lav_police(ald=100.0), t=0.0)
        stor = omk_func(_lav_police(ald=1000.0), t=0.0)
        assert stor > lille

    def test_aum_rate_nul_giver_kun_styk(self, marked: DeterministicMarket):
        police = _lav_police(ald=999.0)
        omk_func = standard_omkostning(marked, aum_rate=0.0, styk_aar=300.0)
        assert omk_func(police, t=0.0) == pytest.approx(300.0)

    def test_returnerer_positivt_beloeb(self, marked: DeterministicMarket):
        police = _lav_police(ald=500.0, rate=200.0, liv=100.0)
        omk_func = standard_omkostning(marked)
        assert omk_func(police, t=0.0) > 0.0

    def test_stiger_med_afkast(self):
        """
        Med positiv rente P(t) > P(0) → V_total vokser → AUM-omkostning stiger over tid.
        r = ln(1.05) → P(1) = 100 × 1.05 = 105 DKK/enhed
        c(1) = 0.005 × 100 × 105 + 200 = 52.5 + 200 = 252.5 DKK/år
        """
        marked_med_afkast = DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)
        police = _lav_police(ald=100.0)
        omk_func = standard_omkostning(marked_med_afkast, aum_rate=0.005, styk_aar=200.0)
        forventet_t1 = 0.005 * 100.0 * 105.0 + 200.0  # 252.5 DKK/år
        assert omk_func(police, t=1.0) == pytest.approx(forventet_t1, rel=1e-6)
