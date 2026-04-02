"""
Tests for thiele — thiele_step(), RisikoSummer, CashflowSats.

Euler-diskretiseringen for depot d er:
    Δn_d = dt · [−b_d − c_d − Σ_j µ_ij·R_ij_d] / P(t)

Håndberegnede referencetilfælde (alle: P₀=100 DKK/enhed, r=0, dt=1/12):

1. NUL FLOWS (ingen cashflows, ingen omkostning, ingen mortalitet):
       Δn_ald = (1/12) × (0 − 0 − 0) / 100 = 0  → uændret

2. INDBETALING (b_ald = −12 000 DKK/år):
       Δn_ald = (1/12) × (−(−12 000) − 0) / 100
             = (1/12) × 12 000 / 100 = 10.0 enheder
       Start: 100 enh → Slut: 110 enheder

3. AUM-OMKOSTNING (c = 1 200 DKK/år, kun aldersopsparing):
       w_ald = 100/100 = 1.0  →  omk_ald = 1 200 × 1.0 = 1 200 DKK/år
       Δn_ald = (1/12) × (0 − 1 200) / 100 = −1.0 enhed
       Start: 100 enh → Slut: 99 enheder

4. DEPOT-CLAMP (stor udbetaling → depotet ramt nul):
       b_ald = +120 000 DKK/år (udbetaling), start: 1 enhed
       Δn_ald = (1/12) × (−120 000) / 100 = −100 → 1 − 100 = −99 → clamp til 0

5. BIOMETRISK LED MED R=0 (DEPOT-type):
       µ = 0.12 år⁻¹, R_ald = 0  →  Σ µ·R = 0  →  ingen effekt

6. BIOMETRISK LED MED R=−V (INGEN-type):
       µ = 0.12 år⁻¹, R_ald = −100 × 100 = −10 000 DKK
       Σ µ·R = 0.12 × (−10 000) = −1 200 DKK/år
       Δn_ald = (1/12) × (−(−1 200)) / 100 = +1.0 enhed
       Start: 100 enh → Slut: 101 enheder

7. PROPOROTIONAL OMKOSTNINGSFORDELING (tre depoter):
       100 ald + 200 rate + 200 liv = 500 enheder total
       w_ald = 100/500 = 0.2, w_rate = w_liv = 200/500 = 0.4
       c = 600 DKK/år  →  omk_ald = 120, omk_rate = omk_liv = 240 DKK/år
       Δn_ald = (1/12) × (−120) / 100 = −0.1 enhed
"""

import math
from datetime import date

import pytest

from verd import (
    CashflowSats,
    DeterministicMarket,
    Policy,
    PolicyState,
    RisikoSummer,
    thiele_step,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def marked() -> DeterministicMarket:
    """P₀=100 DKK/enhed, r=0 → P(t)=100 for alle t."""
    return DeterministicMarket(r=0.0, enhedspris_0=100.0)


def _lav_police(
    ald: float = 100.0,
    rate: float = 0.0,
    liv: float = 0.0,
    tilstand: PolicyState = PolicyState.I_LIVE,
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
        tilstand=tilstand,
    )


DT = 1.0 / 12.0


# ---------------------------------------------------------------------------
# Tests for RisikoSummer
# ---------------------------------------------------------------------------

class TestRisikoSummer:
    def test_standardvaerdier_er_nul(self):
        r = RisikoSummer()
        assert r.aldersopsparing == 0.0
        assert r.ratepension == 0.0
        assert r.livrente == 0.0

    def test_kan_sætte_vaerdier(self):
        r = RisikoSummer(aldersopsparing=100.0, ratepension=-50.0, livrente=0.0)
        assert r.aldersopsparing == pytest.approx(100.0)
        assert r.ratepension == pytest.approx(-50.0)


# ---------------------------------------------------------------------------
# Tests for CashflowSats
# ---------------------------------------------------------------------------

class TestCashflowSats:
    def test_standardvaerdier_er_nul(self):
        c = CashflowSats()
        assert c.b_aldersopsparing == 0.0
        assert c.b_ratepension == 0.0
        assert c.b_livrente == 0.0
        assert c.omkostning == 0.0

    def test_total_indbetaling_er_sum_af_negative_b(self):
        """b_d < 0 → indbetaling: total_indbetaling = sum af abs(negative b'er)."""
        c = CashflowSats(b_aldersopsparing=-1200.0, b_ratepension=-800.0, b_livrente=0.0)
        # total_indbetaling = -(-1200) + -(-800) + -min(0,0) = 2000
        assert c.total_indbetaling == pytest.approx(2000.0)

    def test_total_udbetaling_er_sum_af_positive_b(self):
        """b_d > 0 → udbetaling."""
        c = CashflowSats(b_aldersopsparing=500.0, b_ratepension=300.0)
        assert c.total_udbetaling == pytest.approx(800.0)

    def test_bland_indbetaling_og_udbetaling(self):
        c = CashflowSats(b_aldersopsparing=-1000.0, b_ratepension=500.0)
        assert c.total_indbetaling == pytest.approx(1000.0)
        assert c.total_udbetaling == pytest.approx(500.0)


# ---------------------------------------------------------------------------
# Tests for thiele_step — basis
# ---------------------------------------------------------------------------

class TestThieleStepIngenFlows:
    def test_nul_cashflow_giver_uaendret_depot(self, marked: DeterministicMarket):
        """
        Håndberegning (tilfælde 1):
            Ingen b, c=0, ingen mortalitet → Δn = 0 → depotet uændret.
        """
        police = _lav_police(ald=100.0)
        resultat = thiele_step(
            policy=police,
            t=0.0,
            dt=DT,
            market=marked,
            cashflows=CashflowSats(),
            overgangs_led=[],
        )
        assert resultat.aldersopsparing == pytest.approx(100.0)
        assert resultat.ratepensionsopsparing == pytest.approx(0.0)
        assert resultat.livrentedepot == pytest.approx(0.0)


class TestThieleStepIndbetaling:
    def test_indbetaling_oeger_depot(self, marked: DeterministicMarket):
        """
        Håndberegning (tilfælde 2):
            b_ald = −12 000 DKK/år, dt=1/12, P=100
            Δn_ald = (1/12) × 12 000 / 100 = 10.0 enheder
            Start: 100 → Slut: 110.0 enheder
        """
        police = _lav_police(ald=100.0)
        cashflows = CashflowSats(b_aldersopsparing=-12_000.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows, overgangs_led=[],
        )
        assert resultat.aldersopsparing == pytest.approx(110.0)

    def test_indbetaling_paavirker_ikke_andre_depoter(self, marked: DeterministicMarket):
        """Indbetaling til aldersopsparing påvirker ikke rate- eller livrentedepot."""
        police = _lav_police(ald=100.0, rate=50.0, liv=50.0)
        cashflows = CashflowSats(b_aldersopsparing=-1200.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows, overgangs_led=[],
        )
        assert resultat.ratepensionsopsparing == pytest.approx(50.0)
        assert resultat.livrentedepot == pytest.approx(50.0)


class TestThieleStepOmkostning:
    def test_aum_omkostning_reducerer_depot(self, marked: DeterministicMarket):
        """
        Håndberegning (tilfælde 3):
            c = 1 200 DKK/år, kun ald (w_ald=1.0)
            Δn_ald = (1/12) × (−1 200) / 100 = −1.0 enhed
            Start: 100 → Slut: 99.0 enheder
        """
        police = _lav_police(ald=100.0)
        cashflows = CashflowSats(omkostning=1_200.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows, overgangs_led=[],
        )
        assert resultat.aldersopsparing == pytest.approx(99.0)

    def test_omkostning_fordeles_proportionalt(self, marked: DeterministicMarket):
        """
        Håndberegning (tilfælde 7):
            100 ald + 200 rate + 200 liv = 500 total
            w_ald = 0.2, w_rate = w_liv = 0.4
            c = 600 DKK/år
            Δn_ald = (1/12) × (−600×0.2) / 100 = (1/12)×(−120)/100 = −0.1
            Δn_rate = (1/12) × (−600×0.4) / 100 = (1/12)×(−240)/100 = −0.2
        """
        police = _lav_police(ald=100.0, rate=200.0, liv=200.0)
        cashflows = CashflowSats(omkostning=600.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows, overgangs_led=[],
        )
        assert resultat.aldersopsparing == pytest.approx(100.0 - 0.1, abs=1e-9)
        assert resultat.ratepensionsopsparing == pytest.approx(200.0 - 0.2, abs=1e-9)
        assert resultat.livrentedepot == pytest.approx(200.0 - 0.2, abs=1e-9)

    def test_nul_depot_fordeler_ligeligt(self, marked: DeterministicMarket):
        """
        Alle depoter tomme → omkostning fordeles 1/3 til hvert depot.
        c = 600 DKK/år → Δn_ald = (1/12) × (−200) / 100 = −1/6 enh → clamp til 0.
        """
        police = _lav_police(ald=0.0, rate=0.0, liv=0.0)
        cashflows = CashflowSats(omkostning=600.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows, overgangs_led=[],
        )
        # Depot kan ikke gå under nul
        assert resultat.aldersopsparing == pytest.approx(0.0)
        assert resultat.ratepensionsopsparing == pytest.approx(0.0)
        assert resultat.livrentedepot == pytest.approx(0.0)


class TestThieleStepDepotkClamp:
    def test_depot_clampet_til_nul(self, marked: DeterministicMarket):
        """
        Håndberegning (tilfælde 4):
            b_ald = +120 000 DKK/år (stor udbetaling), start: 1 enhed
            Δn_ald = (1/12) × (−120 000) / 100 = −100 enh
            1 − 100 = −99 → clamp til 0.0
        """
        police = _lav_police(ald=1.0)
        cashflows = CashflowSats(b_aldersopsparing=120_000.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows, overgangs_led=[],
        )
        assert resultat.aldersopsparing == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests for thiele_step — biometrisk led
# ---------------------------------------------------------------------------

class TestThieleStepBiometriskLed:
    def test_nul_risikosum_paavirker_ikke_depot(self, marked: DeterministicMarket):
        """
        Håndberegning (tilfælde 5):
            µ = 0.12 år⁻¹, R_ald = 0 → Σ µ·R = 0 → ingen effekt
            Depot uændret selv med høj mortalitet.
        """
        police = _lav_police(ald=100.0)
        mu = 0.12
        r = RisikoSummer(aldersopsparing=0.0, ratepension=0.0, livrente=0.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=CashflowSats(),
            overgangs_led=[(mu, r)],
        )
        assert resultat.aldersopsparing == pytest.approx(100.0)

    def test_negativ_risikosum_oeger_depot(self, marked: DeterministicMarket):
        """
        Håndberegning (tilfælde 6, INGEN-type):
            µ = 0.12 år⁻¹, R_ald = −100×100 = −10 000 DKK
            Σ µ·R = 0.12 × (−10 000) = −1 200 DKK/år
            Δn_ald = (1/12) × (−(−1 200)) / 100 = +1.0 enhed
            Start: 100 enh → Slut: 101.0 enheder
        """
        police = _lav_police(ald=100.0)
        mu = 0.12
        P_t = marked.enhedspris(0.0)  # 100
        r = RisikoSummer(aldersopsparing=-police.aldersopsparing * P_t)  # −10 000
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=CashflowSats(),
            overgangs_led=[(mu, r)],
        )
        assert resultat.aldersopsparing == pytest.approx(101.0)

    def test_positiv_risikosum_reducerer_depot(self, marked: DeterministicMarket):
        """
        Positiv R (risikoudgift for forsikringsselskabet) reducerer depotet.
            µ = 0.12, R_ald = +10 000 DKK
            Δn_ald = (1/12) × (−0.12 × 10 000) / 100 = −1.0
        """
        police = _lav_police(ald=100.0)
        mu = 0.12
        r = RisikoSummer(aldersopsparing=100.0 * 100.0)  # +10 000
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=CashflowSats(),
            overgangs_led=[(mu, r)],
        )
        assert resultat.aldersopsparing == pytest.approx(99.0)

    def test_kombineret_indbetaling_og_biometrisk_led(self, marked: DeterministicMarket):
        """
        Kombineret: indbetaling +10 enheder, biometrisk led +1 enhed (INGEN-type).
        Start: 100 enh → Slut: 111.0 enheder.
        """
        police = _lav_police(ald=100.0)
        cashflows = CashflowSats(b_aldersopsparing=-12_000.0)
        mu = 0.12
        P_t = marked.enhedspris(0.0)
        r = RisikoSummer(aldersopsparing=-police.aldersopsparing * P_t)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows,
            overgangs_led=[(mu, r)],
        )
        assert resultat.aldersopsparing == pytest.approx(111.0)

    def test_returnerer_ny_policy_objekt(self, marked: DeterministicMarket):
        """thiele_step returnerer en ny Policy — originalen er uændret."""
        police = _lav_police(ald=100.0)
        cashflows = CashflowSats(b_aldersopsparing=-1200.0)
        resultat = thiele_step(
            policy=police, t=0.0, dt=DT, market=marked,
            cashflows=cashflows, overgangs_led=[],
        )
        assert resultat is not police
        assert police.aldersopsparing == pytest.approx(100.0)  # original uændret
