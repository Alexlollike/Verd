"""
Tests for validering — check_sandsynligheder, check_p_alive_monoton, kør_alle_checks.

Dækker:
    - check_sandsynligheder: valid fordeling passerer; ugyldig kaster ValueError
    - check_p_alive_monoton: monotont faldende passerer; stigende kaster ValueError
    - kør_alle_checks: kører igennem på et gyldigt fremregningsresultat
"""

import math
from datetime import date

import pytest

from verd import (
    DeterministicMarket,
    FremregningsSkridt,
    GompertzMakeham,
    Policy,
    PolicyState,
    TilstandsSkridt,
    check_p_alive_monoton,
    check_sandsynligheder,
    fremregn,
    initial_distribution,
    kør_alle_checks,
    simpel_opsparings_cashflow,
    standard_toetilstands_model,
)


# ---------------------------------------------------------------------------
# Hjælpefunktioner
# ---------------------------------------------------------------------------

def _lav_skridt(prob_i_live: float, t: float = 0.0) -> FremregningsSkridt:
    """Opret et minimalt FremregningsSkridt med én I_LIVE-tilstand."""
    ts_live = TilstandsSkridt(
        tilstand=PolicyState.I_LIVE,
        prob=prob_i_live,
        aldersopsparing_dkk=1000.0,
        ratepension_dkk=0.0,
        livrente_dkk=0.0,
    )
    ts_doed = TilstandsSkridt(
        tilstand=PolicyState.DOED,
        prob=1.0 - prob_i_live,
        aldersopsparing_dkk=0.0,
        ratepension_dkk=0.0,
        livrente_dkk=0.0,
    )
    return FremregningsSkridt(
        t=t,
        alder=40.0 + t,
        tilstande=[ts_live, ts_doed],
        indbetaling_dkk=0.0,
        udbetaling_dkk=0.0,
        omkostning_dkk=0.0,
        faktisk_udgift_dkk=0.0,
        enhedspris=100.0,
    )


def _lav_police() -> Policy:
    return Policy.fra_dkk(
        foedselsdato=date(1984, 1, 1),
        tegningsdato=date(2024, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="TEST",
        omkostningssats_id="STANDARD",
        loen=600_000.0,
        indbetalingsprocent=0.15,
        aldersopsparing=100_000.0,
        ratepensionsopsparing=0.0,
        ratepensionsvarighed=10,
        livrentedepot=0.0,
        enhedspris=100.0,
    )


# ---------------------------------------------------------------------------
# Tests for check_sandsynligheder
# ---------------------------------------------------------------------------

class TestCheckSandsynligheder:
    def test_valid_fordeling_passerer(self):
        """Sum = 1.0 → ingen fejl."""
        police = _lav_police()
        fordeling = [(police, 1.0)]
        check_sandsynligheder(fordeling)  # må ikke kaste

    def test_to_tilstande_summerer_til_en(self):
        """0.7 + 0.3 = 1.0 → passerer."""
        police = _lav_police()
        import dataclasses
        police_doed = dataclasses.replace(police, tilstand=PolicyState.DOED)
        fordeling = [(police, 0.7), (police_doed, 0.3)]
        check_sandsynligheder(fordeling)  # må ikke kaste

    def test_for_lav_sum_kaster_fejl(self):
        """Sum = 0.9 → ValueError."""
        police = _lav_police()
        import dataclasses
        police_doed = dataclasses.replace(police, tilstand=PolicyState.DOED)
        fordeling = [(police, 0.5), (police_doed, 0.4)]
        with pytest.raises(ValueError):
            check_sandsynligheder(fordeling)

    def test_for_hoj_sum_kaster_fejl(self):
        """Sum = 1.1 → ValueError."""
        police = _lav_police()
        import dataclasses
        police_doed = dataclasses.replace(police, tilstand=PolicyState.DOED)
        fordeling = [(police, 0.6), (police_doed, 0.5)]
        with pytest.raises(ValueError):
            check_sandsynligheder(fordeling)

    def test_nul_sum_kaster_fejl(self):
        police = _lav_police()
        fordeling = [(police, 0.0)]
        with pytest.raises(ValueError):
            check_sandsynligheder(fordeling)

    def test_tolerance_overholdes(self):
        """Meget lille afvigelse (< default tolerance 1e-9) passerer."""
        police = _lav_police()
        fordeling = [(police, 1.0 + 1e-12)]
        check_sandsynligheder(fordeling)  # inden for tolerance


# ---------------------------------------------------------------------------
# Tests for check_p_alive_monoton
# ---------------------------------------------------------------------------

class TestCheckPAliveMonoton:
    def test_faldende_sandsynlighed_passerer(self):
        """p_alive faldende: 1.0 → 0.99 → 0.97 → passerer."""
        skridt = [
            _lav_skridt(prob_i_live=1.00, t=0.0),
            _lav_skridt(prob_i_live=0.99, t=1 / 12),
            _lav_skridt(prob_i_live=0.97, t=2 / 12),
        ]
        check_p_alive_monoton(skridt)  # må ikke kaste

    def test_konstant_sandsynlighed_passerer(self):
        """p_alive konstant = 1.0 (µ=0) → passerer."""
        skridt = [_lav_skridt(prob_i_live=1.0, t=k / 12) for k in range(5)]
        check_p_alive_monoton(skridt)

    def test_stigende_sandsynlighed_kaster_fejl(self):
        """p_alive stiger over tolerance → ValueError."""
        skridt = [
            _lav_skridt(prob_i_live=0.90, t=0.0),
            _lav_skridt(prob_i_live=0.95, t=1 / 12),  # stigende!
        ]
        with pytest.raises(ValueError):
            check_p_alive_monoton(skridt)

    def test_tom_liste_passerer(self):
        check_p_alive_monoton([])  # ingen skridt → ingen fejl

    def test_enkelt_skridt_passerer(self):
        check_p_alive_monoton([_lav_skridt(prob_i_live=0.95)])


# ---------------------------------------------------------------------------
# Tests for kør_alle_checks
# ---------------------------------------------------------------------------

class TestKørAlleChecks:
    def test_valid_fremregning_passerer(self):
        """En korrekt fremregning med standard inputs passerer alle checks."""
        marked = DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)
        biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
        police = _lav_police()
        tilstandsmodel = standard_toetilstands_model(biometri)
        dist = initial_distribution(police)

        skridt = fremregn(
            distribution=dist,
            antal_skridt=24,
            market=marked,
            tilstandsmodel=tilstandsmodel,
            cashflow_funktion=simpel_opsparings_cashflow,
            dt=1 / 12,
        )

        kør_alle_checks(police, skridt, marked)  # må ikke kaste
