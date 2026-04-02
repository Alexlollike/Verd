"""
Tests for fremregning — fremregn(), simpel_opsparings_cashflow, nul_risikosum,
standard_toetilstands_model, simpel_cashflow_funktion.

Golden value-opsætning (µ=0, r=0):
    Police: 40 år ved tegning, aldersopsparing=100 enheder, P₀=100, r=0
    Bidrag: loen=120 000 DKK/år, indbetalingsprocent=10 % → 12 000 DKK/år
    µ=0 (GompertzMakeham(α=0, β=0)) → p_alive=1.0 altid
    dt=1/12

    Enkelt skridt:
        f_ald = 100/100 = 1.0 (kun aldersopsparing)
        b_ald = −12 000 × 1.0 = −12 000 DKK/år
        Δn_ald = (1/12) × 12 000 / 100 = 1.0 enhed pr. månedligt skridt

    Efter 12 skridt (1 år):
        aldersopsparing = 100 + 12 × 1 = 112 enheder
        depot_dkk = 112 × 100 = 11 200 DKK

    Efter 24 skridt (2 år):
        aldersopsparing = 100 + 24 × 1 = 124 enheder → depot = 12 400 DKK

    Uændret depot (ingen bidrag, µ=0, r=0):
        Police med loen=0 → depot konstant = start
"""

import math
from datetime import date

import pytest

from verd import (
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    fremregn,
    initial_distribution,
    nul_risikosum,
    simpel_cashflow_funktion,
    simpel_opsparings_cashflow,
    standard_toetilstands_model,
)
from verd.thiele import CashflowSats


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def marked_nul() -> DeterministicMarket:
    """P₀=100, r=0 — ingen afkast, ingen diskontering."""
    return DeterministicMarket(r=0.0, enhedspris_0=100.0)


@pytest.fixture
def marked_rente() -> DeterministicMarket:
    """P₀=100, r=ln(1.05) — 5% p.a. afkast."""
    return DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)


@pytest.fixture
def gm_nul() -> GompertzMakeham:
    """µ(x) = 0 for alle x — udødelige forsikringstagere."""
    return GompertzMakeham(alpha=0.0, beta=0.0, sigma=0.09)


@pytest.fixture
def gm_standard() -> GompertzMakeham:
    return GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)


DT = 1.0 / 12.0


def _lav_police(
    marked: DeterministicMarket,
    loen: float = 120_000.0,
    indbetalingsprocent: float = 0.10,
    ald_dkk: float = 10_000.0,
    rate_dkk: float = 0.0,
    liv_dkk: float = 0.0,
    pensionsalder: int = 100,
) -> Policy:
    return Policy.fra_dkk(
        foedselsdato=date(1984, 1, 1),
        tegningsdato=date(2024, 1, 1),
        pensionsalder=pensionsalder,
        er_under_udbetaling=False,
        gruppe_id="TEST",
        omkostningssats_id="STANDARD",
        loen=loen,
        indbetalingsprocent=indbetalingsprocent,
        aldersopsparing=ald_dkk,
        ratepensionsopsparing=rate_dkk,
        ratepensionsvarighed=10,
        livrentedepot=liv_dkk,
        enhedspris=marked.enhedspris(0.0),
    )


# ---------------------------------------------------------------------------
# Tests for nul_risikosum
# ---------------------------------------------------------------------------

class TestNulRisikosum:
    def test_alle_summer_er_nul(self, marked_nul: DeterministicMarket):
        police = _lav_police(marked_nul)
        r = nul_risikosum(police, t=0.0)
        assert r.aldersopsparing == pytest.approx(0.0)
        assert r.ratepension == pytest.approx(0.0)
        assert r.livrente == pytest.approx(0.0)

    def test_uaendret_for_vilkaarlig_t(self, marked_nul: DeterministicMarket):
        police = _lav_police(marked_nul)
        for t in [0.0, 5.0, 30.0]:
            r = nul_risikosum(police, t=t)
            assert r.aldersopsparing == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests for standard_toetilstands_model
# ---------------------------------------------------------------------------

class TestStandardToetilstandsmodel:
    def test_returnerer_tilstandsmodel(self, gm_standard: GompertzMakeham):
        from verd import Tilstandsmodel
        model = standard_toetilstands_model(gm_standard)
        assert isinstance(model, Tilstandsmodel)

    def test_model_har_to_tilstande(self, gm_standard: GompertzMakeham):
        model = standard_toetilstands_model(gm_standard)
        assert len(model.alle_tilstande()) == 2

    def test_i_live_er_ikke_absorberende(self, gm_standard: GompertzMakeham):
        model = standard_toetilstands_model(gm_standard)
        assert PolicyState.I_LIVE in model.ikke_absorberende()

    def test_doed_er_absorberende(self, gm_standard: GompertzMakeham):
        model = standard_toetilstands_model(gm_standard)
        assert PolicyState.DOED not in model.ikke_absorberende()


# ---------------------------------------------------------------------------
# Tests for simpel_opsparings_cashflow
# ---------------------------------------------------------------------------

class TestSimpelOpsparingsCashflow:
    def test_indbetaling_er_loen_gange_procent(self, marked_nul: DeterministicMarket):
        """
        Håndberegning: loen=120 000, pct=10% → 12 000 DKK/år til aldersopsparing.
        Kun aldersopsparing → f_ald=1.0 → b_ald = −12 000.
        """
        police = _lav_police(marked_nul, loen=120_000.0, indbetalingsprocent=0.10,
                             ald_dkk=10_000.0, rate_dkk=0.0, liv_dkk=0.0)
        cs = simpel_opsparings_cashflow(police, t=0.0)
        assert cs.b_aldersopsparing == pytest.approx(-12_000.0)
        assert cs.b_ratepension == pytest.approx(0.0)
        assert cs.b_livrente == pytest.approx(0.0)

    def test_fordeling_proportional_med_depoter(self, marked_nul: DeterministicMarket):
        """
        3 ligestore depoter → indbetaling fordeles 1/3 til hvert.
        loen=12 000, pct=100% → 12 000 DKK/år → 4 000 til hvert depot.
        """
        police = _lav_police(marked_nul, loen=12_000.0, indbetalingsprocent=1.0,
                             ald_dkk=1_000.0, rate_dkk=1_000.0, liv_dkk=1_000.0)
        cs = simpel_opsparings_cashflow(police, t=0.0)
        assert cs.b_aldersopsparing == pytest.approx(-4_000.0)
        assert cs.b_ratepension == pytest.approx(-4_000.0)
        assert cs.b_livrente == pytest.approx(-4_000.0)

    def test_nul_indbetaling_naar_under_udbetaling(self, marked_nul: DeterministicMarket):
        """er_under_udbetaling=True → returnerer nul-CashflowSats."""
        import dataclasses
        police = _lav_police(marked_nul)
        police = dataclasses.replace(police, er_under_udbetaling=True)
        cs = simpel_opsparings_cashflow(police, t=0.0)
        assert cs.b_aldersopsparing == pytest.approx(0.0)

    def test_nul_indbetaling_for_doed_tilstand(self, marked_nul: DeterministicMarket):
        """DOED tilstand → nul cashflow."""
        import dataclasses
        police = _lav_police(marked_nul)
        police = dataclasses.replace(police, tilstand=PolicyState.DOED)
        cs = simpel_opsparings_cashflow(police, t=0.0)
        assert cs.b_aldersopsparing == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests for fremregn — basis
# ---------------------------------------------------------------------------

class TestFremregningBasisEgenskaber:
    def test_returnerer_antal_skridt_plus_en(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """fremregn() med antal_skridt=N returnerer N+1 elementer (inkl. t_0)."""
        police = _lav_police(marked_nul, loen=0.0)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        skridt = fremregn(
            distribution=dist, antal_skridt=12,
            market=marked_nul, tilstandsmodel=model, dt=DT,
        )
        assert len(skridt) == 13  # 12 skridt + initial

    def test_foerste_skridt_er_initialstilstand(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """Første element svarer til t=0 og p_alive=1.0."""
        police = _lav_police(marked_nul, loen=0.0)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        skridt = fremregn(
            distribution=dist, antal_skridt=6,
            market=marked_nul, tilstandsmodel=model, dt=DT,
        )
        assert skridt[0].t == pytest.approx(0.0)
        assert skridt[0].prob_i_live == pytest.approx(1.0)

    def test_prob_summerer_til_en_i_hvert_skridt(
        self, gm_standard: GompertzMakeham, marked_rente: DeterministicMarket
    ):
        """Σ p_i(t) = 1 i hvert tidsstep."""
        police = _lav_police(marked_rente)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_standard)
        skridt = fremregn(
            distribution=dist, antal_skridt=24,
            market=marked_rente, tilstandsmodel=model, dt=DT,
        )
        for s in skridt:
            total_prob = sum(ts.prob for ts in s.tilstande)
            assert total_prob == pytest.approx(1.0, abs=1e-6)

    def test_tom_distribution_kaster_fejl(
        self, marked_nul: DeterministicMarket, gm_nul: GompertzMakeham
    ):
        model = standard_toetilstands_model(gm_nul)
        with pytest.raises(ValueError):
            fremregn(
                distribution=[], antal_skridt=12,
                market=marked_nul, tilstandsmodel=model, dt=DT,
            )


# ---------------------------------------------------------------------------
# Tests for fremregn — nul mortalitet (golden values)
# ---------------------------------------------------------------------------

class TestFremregningNulMortalitet:
    def test_prob_i_live_forbliver_en(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """µ=0 → ingen dødsfald → p_alive = 1.0 i alle skridt."""
        police = _lav_police(marked_nul, loen=0.0)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        skridt = fremregn(
            distribution=dist, antal_skridt=24,
            market=marked_nul, tilstandsmodel=model, dt=DT,
        )
        for s in skridt:
            assert s.prob_i_live == pytest.approx(1.0, abs=1e-9)

    def test_depot_vokser_korrekt_med_bidrag(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """
        Golden value:
            Start: 100 enheder × P₀=100 = 10 000 DKK
            Bidrag: 120 000 × 10% = 12 000 DKK/år → b_ald = −12 000
            Per skridt: Δn = (1/12) × 12 000 / 100 = 10.0 enheder
            Efter 12 skridt: (100 + 12×10) × 100 = 220 × 100 = 22 000 DKK
        """
        police = _lav_police(
            marked_nul, loen=120_000.0, indbetalingsprocent=0.10,
            ald_dkk=10_000.0,
        )
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        skridt = fremregn(
            distribution=dist, antal_skridt=12,
            market=marked_nul, tilstandsmodel=model, dt=DT,
        )
        # Forventet depot efter 12 skridt = 22 000 DKK
        assert skridt[-1].forventet_depot_dkk == pytest.approx(22_000.0, rel=1e-9)

    def test_depot_vokser_med_afkast_og_ingen_bidrag(
        self, gm_nul: GompertzMakeham, marked_rente: DeterministicMarket
    ):
        """
        r=ln(1.05), loen=0, start: 10 000 DKK.
        Enheder uændret; DKK-depot = 100 enh × P(1) = 100 × 105 = 10 500 DKK.
        """
        police = _lav_police(marked_rente, loen=0.0, ald_dkk=10_000.0)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        skridt = fremregn(
            distribution=dist, antal_skridt=12,
            market=marked_rente, tilstandsmodel=model, dt=DT,
        )
        forventet = 100.0 * marked_rente.enhedspris(1.0)
        assert skridt[-1].forventet_depot_dkk == pytest.approx(forventet, rel=1e-6)

    def test_ingen_bidrag_ingen_afkast_giver_konstant_depot(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """loen=0, r=0, µ=0 → depot uændret over hele fremregningen."""
        police = _lav_police(marked_nul, loen=0.0, ald_dkk=10_000.0)
        start_depot = police.depotvaerdi_dkk(marked_nul.enhedspris(0.0))
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        skridt = fremregn(
            distribution=dist, antal_skridt=24,
            market=marked_nul, tilstandsmodel=model, dt=DT,
        )
        for s in skridt:
            assert s.forventet_depot_dkk == pytest.approx(start_depot, rel=1e-9)


# ---------------------------------------------------------------------------
# Tests for fremregn — med mortalitet
# ---------------------------------------------------------------------------

class TestFremregningMedMortalitet:
    def test_prob_i_live_falder_over_tid(
        self, gm_standard: GompertzMakeham, marked_rente: DeterministicMarket
    ):
        """µ>0 → p_alive er strengt faldende over tid."""
        police = _lav_police(marked_rente, loen=0.0)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_standard)
        skridt = fremregn(
            distribution=dist, antal_skridt=24,
            market=marked_rente, tilstandsmodel=model, dt=DT,
        )
        p_prev = skridt[0].prob_i_live
        for s in skridt[1:]:
            assert s.prob_i_live <= p_prev + 1e-12
            p_prev = s.prob_i_live

    def test_forventet_depot_lavere_end_betinget(
        self, gm_standard: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """
        Sandsynlighedsvægtet depot = p × betinget depot.
        p < 1 → forventet < betinget for hvert skridt efter start.
        """
        police = _lav_police(marked_nul, loen=0.0)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_standard)
        skridt = fremregn(
            distribution=dist, antal_skridt=24,
            market=marked_nul, tilstandsmodel=model, dt=DT,
        )
        for s in skridt[1:]:
            il = s.i_live
            if il is not None and il.prob < 1.0:
                assert il.forventet_depot_dkk <= il.total_depot_dkk + 1e-9

    def test_indbetaling_registreres_korrekt(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """
        simpel_opsparings_cashflow: loen=120 000, pct=10% → 12 000 DKK/år.
        Per skridt: indbetaling_dkk = 12 000 × dt = 1 000 DKK.
        """
        police = _lav_police(marked_nul, loen=120_000.0, indbetalingsprocent=0.10)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        skridt = fremregn(
            distribution=dist, antal_skridt=12,
            market=marked_nul, tilstandsmodel=model, dt=DT,
        )
        # Alle skridt bortset fra t=0 (initial) har indbetalinger
        for s in skridt[1:]:
            assert s.indbetaling_dkk == pytest.approx(1_000.0)


# ---------------------------------------------------------------------------
# Tests for fremregn — simpel_cashflow_funktion (faseskift)
# ---------------------------------------------------------------------------

class TestSimpelCashflowFunktion:
    def test_indbetaling_i_opsparingsfasen(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """
        Pensionsalder=41 (1 år fremme), pt. 40 år → er i opsparingsfase.
        Indbetaling skal ske i de første 12 skridt.
        """
        police = _lav_police(
            marked_nul, loen=120_000.0, indbetalingsprocent=0.10,
            pensionsalder=41,
        )
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        cashflow_func = simpel_cashflow_funktion(gm_nul, marked_nul, DT)

        skridt = fremregn(
            distribution=dist, antal_skridt=6,
            market=marked_nul, tilstandsmodel=model,
            cashflow_funktion=cashflow_func, dt=DT,
        )
        # I opsparingsfasen forventes indbetalinger
        total_indbetaling = sum(s.indbetaling_dkk for s in skridt[1:])
        assert total_indbetaling > 0.0

    def test_udbetaling_efter_pensionering(
        self, gm_nul: GompertzMakeham, marked_nul: DeterministicMarket
    ):
        """
        Pensionsalder=40 → allerede pensioneret → udbetalingsfase fra start.
        Udbetalinger (b > 0) skal forekomme.
        """
        police = _lav_police(
            marked_nul, loen=0.0, ald_dkk=0.0,
            rate_dkk=0.0, liv_dkk=10_000.0, pensionsalder=40,
        )
        import dataclasses
        police = dataclasses.replace(police, er_under_udbetaling=True)
        dist = initial_distribution(police)
        model = standard_toetilstands_model(gm_nul)
        cashflow_func = simpel_cashflow_funktion(gm_nul, marked_nul, DT)

        skridt = fremregn(
            distribution=dist, antal_skridt=6,
            market=marked_nul, tilstandsmodel=model,
            cashflow_funktion=cashflow_func, dt=DT,
        )
        total_udbetaling = sum(s.udbetaling_dkk for s in skridt[1:])
        assert total_udbetaling > 0.0
