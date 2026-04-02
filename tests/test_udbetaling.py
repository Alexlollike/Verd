"""
Tests for udbetaling — livrente_annuitet, sikker_annuitet, udbetaling_cashflow_funktion.

Håndberegnede referencetilfælde:

SIKKER ANNUITET (ä_n = Σ_{k=0}^{N-1} dt · exp(−r·k·dt)):
    r=0, remaining=1 år, dt=1/12:
        N = round(1/(1/12)) = 12
        ä_n = Σ_{k=0}^{11} (1/12)·1 = 12 × (1/12) = 1.0 år

    r=0, remaining=2 år:
        N = 24 → ä_n = 2.0 år

    r=0, remaining=10 år:
        ä_n = 10.0 år

LIVRENTE ANNUITET (ä_x = Σ_{k=0}^{K-1} dt · v^k · k_p_x):
    µ=0 (α=β=0), r=0, alder=30, max_alder=120:
        K = round((120-30)/(1/12)) = 1080
        k_p_x = 1 for alle k (ingen dødsfald)
        ä_x = 1080 × (1/12) = 90.0 år

    µ=0, r=0, alder=50, max_alder=120:
        ä_x = (120-50)/(1/12) × (1/12) = 70.0 år

    µ>0: ä_x < ä_x(µ=0) fordi k_p_x < 1 for k>0
"""

import dataclasses
import math
from datetime import date

import pytest

from verd import (
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    livrente_annuitet,
    sikker_annuitet,
    udbetaling_cashflow_funktion,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def marked_nul() -> DeterministicMarket:
    """P₀=100 DKK/enhed, r=0 → ingen diskontering."""
    return DeterministicMarket(r=0.0, enhedspris_0=100.0)


@pytest.fixture
def marked_rente() -> DeterministicMarket:
    """P₀=100, r=ln(1.05) → 5 % p.a. afkast."""
    return DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)


@pytest.fixture
def gm_nul_mortalitet() -> GompertzMakeham:
    """µ(x) = 0 for alle x — udødelige forsikringstagere."""
    return GompertzMakeham(alpha=0.0, beta=0.0, sigma=0.09)


@pytest.fixture
def gm_standard() -> GompertzMakeham:
    return GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)


DT = 1.0 / 12.0


def _lav_police_udbetaling(
    ald_enh: float = 100.0,
    rate_enh: float = 100.0,
    liv_enh: float = 100.0,
    ratepensionsvarighed: int = 10,
) -> Policy:
    return Policy(
        foedselsdato=date(1957, 1, 1),  # 67 år i 2024
        tegningsdato=date(2024, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=True,
        gruppe_id="TEST",
        omkostningssats_id="STANDARD",
        loen=0.0,
        indbetalingsprocent=0.0,
        aldersopsparing=ald_enh,
        ratepensionsopsparing=rate_enh,
        ratepensionsvarighed=ratepensionsvarighed,
        livrentedepot=liv_enh,
    )


# ---------------------------------------------------------------------------
# Tests for sikker_annuitet
# ---------------------------------------------------------------------------

class TestSikkerAnnuitet:
    def test_nul_rente_eet_aar_giver_eet_aar(self, marked_nul: DeterministicMarket):
        """
        Håndberegning: r=0, remaining=1 → N=12, ä_n = 12 × (1/12) = 1.0 år.
        """
        result = sikker_annuitet(remaining_years=1.0, market=marked_nul, t0=0.0, dt=DT)
        assert result == pytest.approx(1.0)

    def test_nul_rente_to_aar_giver_to_aar(self, marked_nul: DeterministicMarket):
        """r=0, remaining=2 → ä_n = 2.0 år."""
        result = sikker_annuitet(remaining_years=2.0, market=marked_nul, t0=0.0, dt=DT)
        assert result == pytest.approx(2.0)

    def test_nul_rente_ti_aar_giver_ti_aar(self, marked_nul: DeterministicMarket):
        """r=0, remaining=10 → ä_n = 10.0 år."""
        result = sikker_annuitet(remaining_years=10.0, market=marked_nul, t0=0.0, dt=DT)
        assert result == pytest.approx(10.0)

    def test_hoj_rente_giver_lavere_annuitet(
        self,
        marked_nul: DeterministicMarket,
        marked_rente: DeterministicMarket,
    ):
        """r>0 → betalinger diskonteres → ä_n < remaining_years."""
        ann_nul = sikker_annuitet(remaining_years=10.0, market=marked_nul, t0=0.0, dt=DT)
        ann_rente = sikker_annuitet(remaining_years=10.0, market=marked_rente, t0=0.0, dt=DT)
        assert ann_rente < ann_nul

    def test_er_positiv(self, marked_nul: DeterministicMarket):
        result = sikker_annuitet(remaining_years=5.0, market=marked_nul, t0=0.0, dt=DT)
        assert result > 0.0

    def test_stiger_med_resterende_aar(self, marked_rente: DeterministicMarket):
        """Længere udbetalingsperiode → højere annuitet."""
        ann_5 = sikker_annuitet(remaining_years=5.0, market=marked_rente, t0=0.0, dt=DT)
        ann_10 = sikker_annuitet(remaining_years=10.0, market=marked_rente, t0=0.0, dt=DT)
        assert ann_10 > ann_5


# ---------------------------------------------------------------------------
# Tests for livrente_annuitet
# ---------------------------------------------------------------------------

class TestLivrenteAnnuitet:
    def test_nul_mortalitet_nul_rente_giver_resterende_levetid(
        self,
        gm_nul_mortalitet: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """
        Håndberegning: µ=0, r=0, alder=30, max_alder=120
            ä_x = (120-30) × dt × (1/dt) = 90.0 år
        """
        result = livrente_annuitet(
            alder=30.0,
            biometric=gm_nul_mortalitet,
            market=marked_nul,
            t0=0.0,
            dt=DT,
            max_alder=120.0,
        )
        assert result == pytest.approx(90.0, rel=1e-9)

    def test_nul_mortalitet_nul_rente_alder_50(
        self,
        gm_nul_mortalitet: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """
        Håndberegning: µ=0, r=0, alder=50, max_alder=120 → ä_x = 70.0 år.
        """
        result = livrente_annuitet(
            alder=50.0,
            biometric=gm_nul_mortalitet,
            market=marked_nul,
            t0=0.0,
            dt=DT,
            max_alder=120.0,
        )
        assert result == pytest.approx(70.0, rel=1e-9)

    def test_mortalitet_reducerer_annuitet(
        self,
        gm_nul_mortalitet: GompertzMakeham,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """µ>0 → k_p_x < 1 → ä_x < ä_x(µ=0)."""
        ann_udoedelig = livrente_annuitet(
            alder=65.0, biometric=gm_nul_mortalitet,
            market=marked_nul, t0=0.0, dt=DT,
        )
        ann_mortalitet = livrente_annuitet(
            alder=65.0, biometric=gm_standard,
            market=marked_nul, t0=0.0, dt=DT,
        )
        assert ann_mortalitet < ann_udoedelig

    def test_livrente_lavere_end_sikker_ved_positiv_mortalitet(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """
        Livrenteannuitet < sikker annuitet over samme periode pga. mortalitet.
        """
        alder = 67.0
        max_alder = 120.0
        remaining = max_alder - alder

        ann_liv = livrente_annuitet(
            alder=alder, biometric=gm_standard,
            market=marked_nul, t0=0.0, dt=DT, max_alder=max_alder,
        )
        ann_sikker = sikker_annuitet(
            remaining_years=remaining, market=marked_nul, t0=0.0, dt=DT,
        )
        assert ann_liv < ann_sikker

    def test_er_positiv(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        result = livrente_annuitet(
            alder=40.0, biometric=gm_standard,
            market=marked_nul, t0=0.0, dt=DT,
        )
        assert result > 0.0

    def test_falder_med_stigende_alder_nul_rente(
        self,
        gm_nul_mortalitet: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """Ældre alder → kortere resterende levetid → lavere annuitet (µ=0, r=0)."""
        ann_30 = livrente_annuitet(
            alder=30.0, biometric=gm_nul_mortalitet,
            market=marked_nul, t0=0.0, dt=DT, max_alder=120.0,
        )
        ann_70 = livrente_annuitet(
            alder=70.0, biometric=gm_nul_mortalitet,
            market=marked_nul, t0=0.0, dt=DT, max_alder=120.0,
        )
        assert ann_30 > ann_70


# ---------------------------------------------------------------------------
# Tests for udbetaling_cashflow_funktion
# ---------------------------------------------------------------------------

class TestUdbetalingCashflowFunktion:
    def test_returnerer_nul_for_opsparingsfase(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """Police i opsparingsfasen → CashflowSats med alle nul."""
        t_pension = 0.0
        func = udbetaling_cashflow_funktion(gm_standard, marked_nul, t_pension, DT)
        police_opsparing = _lav_police_udbetaling()
        police_opsparing = dataclasses.replace(police_opsparing, er_under_udbetaling=False)
        cs = func(police_opsparing, t=0.0)
        assert cs.b_aldersopsparing == pytest.approx(0.0)
        assert cs.b_ratepension == pytest.approx(0.0)
        assert cs.b_livrente == pytest.approx(0.0)

    def test_returnerer_nul_for_doed_tilstand(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """DOED-tilstand → ingen udbetaling."""
        t_pension = 0.0
        func = udbetaling_cashflow_funktion(gm_standard, marked_nul, t_pension, DT)
        police = _lav_police_udbetaling()
        police = dataclasses.replace(police, tilstand=PolicyState.DOED)
        cs = func(police, t=0.0)
        assert cs.b_aldersopsparing == pytest.approx(0.0)
        assert cs.b_ratepension == pytest.approx(0.0)
        assert cs.b_livrente == pytest.approx(0.0)

    def test_aldersopsparing_toemmes_i_foerste_skridt(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """
        Aldersopsparing udbetales som engangsudbetaling:
            b_ald = V_ald × P(t) / dt
        Det er en positiv sats (udbetaling), der tømmer depotet i ét skridt.
        """
        t_pension = 0.0
        func = udbetaling_cashflow_funktion(gm_standard, marked_nul, t_pension, DT)
        police = _lav_police_udbetaling(ald_enh=100.0, rate_enh=0.0, liv_enh=0.0)
        cs = func(police, t=0.0)

        # b_ald = 100 enheder × 100 DKK/enh / (1/12) = 120,000 DKK/år
        forventet_b_ald = 100.0 * 100.0 / DT
        assert cs.b_aldersopsparing == pytest.approx(forventet_b_ald)

    def test_ratepension_giver_positiv_udbetaling(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """Ratepension i udbetalingsfasen → b_rate > 0 (udbetaling til policyholder)."""
        t_pension = 0.0
        func = udbetaling_cashflow_funktion(gm_standard, marked_nul, t_pension, DT)
        police = _lav_police_udbetaling(ald_enh=0.0, rate_enh=100.0, liv_enh=0.0)
        cs = func(police, t=0.0)
        assert cs.b_ratepension > 0.0

    def test_livrente_giver_positiv_udbetaling(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """Livrentedepot i udbetalingsfasen → b_livrente > 0."""
        t_pension = 0.0
        func = udbetaling_cashflow_funktion(gm_standard, marked_nul, t_pension, DT)
        police = _lav_police_udbetaling(ald_enh=0.0, rate_enh=0.0, liv_enh=100.0)
        cs = func(police, t=0.0)
        assert cs.b_livrente > 0.0

    def test_nul_depot_giver_nul_udbetaling(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """Tomt depot → ingen udbetaling."""
        t_pension = 0.0
        func = udbetaling_cashflow_funktion(gm_standard, marked_nul, t_pension, DT)
        police = _lav_police_udbetaling(ald_enh=0.0, rate_enh=0.0, liv_enh=0.0)
        cs = func(police, t=0.0)
        assert cs.b_aldersopsparing == pytest.approx(0.0)
        assert cs.b_ratepension == pytest.approx(0.0)
        assert cs.b_livrente == pytest.approx(0.0)

    def test_ratepension_nul_naar_periode_udlobet(
        self,
        gm_standard: GompertzMakeham,
        marked_nul: DeterministicMarket,
    ):
        """Ratepensionsvarighed = 1 år; ved t = t_pension + 1 er perioden udløbet."""
        t_pension = 0.0
        func = udbetaling_cashflow_funktion(gm_standard, marked_nul, t_pension, DT)
        police = _lav_police_udbetaling(ald_enh=0.0, rate_enh=100.0, liv_enh=0.0, ratepensionsvarighed=1)
        # t = t_pension + 1 = 1.0 → remaining = 1 - (1 - 0) = 0 ≤ dt → b_rate = 0
        cs = func(police, t=1.0)
        assert cs.b_ratepension == pytest.approx(0.0)
