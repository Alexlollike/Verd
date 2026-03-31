"""
Tests for depotsikring — DoedsydelsesType og beregn_risikosum_funktion.
"""

import math
from datetime import date

import pytest

from verd import (
    DeterministicMarket,
    DoedsydelsesType,
    GompertzMakeham,
    Policy,
    PolicyState,
    beregn_risikosum_funktion,
    fremregn,
    initial_distribution,
    simpel_opsparings_cashflow,
)
from verd.overgang import BiometriOvergangsIntensitet, Overgang, Tilstandsmodel
from verd.thiele import RisikoSummer


# ---------------------------------------------------------------------------
# Fælles fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def marked():
    return DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)


@pytest.fixture
def biometri():
    return GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)


def _lav_police(marked: DeterministicMarket, doedsydelses_type: DoedsydelsesType) -> Policy:
    return Policy.fra_dkk(
        foedselsdato=date(1980, 1, 15),
        tegningsdato=date(2020, 6, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="TEST",
        omkostningssats_id="STANDARD",
        loen=600_000.0,
        indbetalingsprocent=0.15,
        aldersopsparing=120_000.0,
        ratepensionsopsparing=80_000.0,
        ratepensionsvarighed=10,
        livrentedepot=50_000.0,
        enhedspris=marked.enhedspris(0.0),
        doedsydelses_type=doedsydelses_type,
    )


def _lav_tilstandsmodel(biometri, marked):
    return Tilstandsmodel(
        overgange=[
            Overgang(
                fra=PolicyState.I_LIVE,
                til=PolicyState.DOED,
                intensitet=BiometriOvergangsIntensitet(biometri),
                risikosum_func=beregn_risikosum_funktion(marked),
            )
        ]
    )


# ---------------------------------------------------------------------------
# Tests for DoedsydelsesType enum
# ---------------------------------------------------------------------------

class TestDoedsydelsesTypeEnum:
    def test_depot_vaerdi(self):
        assert DoedsydelsesType.DEPOT.value == "depot"

    def test_ingen_vaerdi(self):
        assert DoedsydelsesType.INGEN.value == "ingen"

    def test_default_paa_policy_er_ingen(self, marked):
        police = _lav_police(marked, DoedsydelsesType.INGEN)
        assert police.doedsydelses_type == DoedsydelsesType.INGEN

    def test_depot_sættes_korrekt(self, marked):
        police = _lav_police(marked, DoedsydelsesType.DEPOT)
        assert police.doedsydelses_type == DoedsydelsesType.DEPOT


# ---------------------------------------------------------------------------
# Tests for beregn_risikosum_funktion — DEPOT
# ---------------------------------------------------------------------------

class TestRisikosumDepot:
    def test_risikosum_er_nul_i_opsparingsfasen(self, marked):
        func = beregn_risikosum_funktion(marked)
        police = _lav_police(marked, DoedsydelsesType.DEPOT)
        # DEPOT i opsparingsfasen → risikosum = 0 for alle depoter
        r = func(police, t=0.0)
        assert r.aldersopsparing == 0.0
        assert r.ratepension == 0.0
        assert r.livrente == 0.0

    def test_risikosum_er_nul_ved_flere_tidspunkter(self, marked):
        func = beregn_risikosum_funktion(marked)
        police = _lav_police(marked, DoedsydelsesType.DEPOT)
        for t in [0.0, 1.0, 5.0, 10.0]:
            r = func(police, t=t)
            assert r.aldersopsparing == 0.0
            assert r.ratepension == 0.0
            assert r.livrente == 0.0

    def test_depot_med_udbetaling_kaster_value_error(self, marked):
        import dataclasses
        func = beregn_risikosum_funktion(marked)
        police = _lav_police(marked, DoedsydelsesType.DEPOT)
        police_udbetaling = dataclasses.replace(police, er_under_udbetaling=True)
        with pytest.raises(ValueError, match="opsparingsfasen"):
            func(police_udbetaling, t=0.0)


# ---------------------------------------------------------------------------
# Tests for beregn_risikosum_funktion — INGEN
# ---------------------------------------------------------------------------

class TestRisikosumIngen:
    def test_risikosum_er_negativ_depot(self, marked):
        func = beregn_risikosum_funktion(marked)
        police = _lav_police(marked, DoedsydelsesType.INGEN)
        t = 0.0
        P_t = marked.enhedspris(t)
        r = func(police, t=t)
        assert r.aldersopsparing == pytest.approx(-police.aldersopsparing * P_t)
        assert r.ratepension == pytest.approx(-police.ratepensionsopsparing * P_t)
        assert r.livrente == pytest.approx(-police.livrentedepot * P_t)

    def test_risikosum_er_negativ_ved_t_5(self, marked):
        func = beregn_risikosum_funktion(marked)
        police = _lav_police(marked, DoedsydelsesType.INGEN)
        t = 5.0
        P_t = marked.enhedspris(t)
        r = func(police, t=t)
        # Enhedsprisen vokser — risikosummen (i DKK) er mere negativ end ved t=0
        assert r.aldersopsparing == pytest.approx(-police.aldersopsparing * P_t)

    def test_ingen_tilladt_i_udbetalingsfasen(self, marked):
        import dataclasses
        func = beregn_risikosum_funktion(marked)
        police = _lav_police(marked, DoedsydelsesType.INGEN)
        police_udbetaling = dataclasses.replace(police, er_under_udbetaling=True)
        # INGEN kaster ikke ValueError — skal returnere RisikoSummer
        r = func(police_udbetaling, t=0.0)
        assert isinstance(r, RisikoSummer)


# ---------------------------------------------------------------------------
# Integrationstest — fremregning med og uden depotsikring
# ---------------------------------------------------------------------------

class TestFremregningMedDepotsikring:
    def test_depot_giver_lavere_forventet_depot_end_ingen(self, marked, biometri):
        tilstandsmodel = _lav_tilstandsmodel(biometri, marked)
        police_ingen = _lav_police(marked, DoedsydelsesType.INGEN)
        police_depot = _lav_police(marked, DoedsydelsesType.DEPOT)

        kwargs = dict(
            antal_skridt=27 * 12,
            market=marked,
            tilstandsmodel=tilstandsmodel,
            cashflow_funktion=simpel_opsparings_cashflow,
            dt=1 / 12,
        )

        skridt_ingen = fremregn(distribution=initial_distribution(police_ingen), **kwargs)
        skridt_depot = fremregn(distribution=initial_distribution(police_depot), **kwargs)

        depot_ingen = skridt_ingen[-1].forventet_depot_dkk
        depot_depot = skridt_depot[-1].forventet_depot_dkk

        # INGEN > DEPOT: dødelighedsgevinster øger forventet depot
        assert depot_ingen > depot_depot + 1e-2
