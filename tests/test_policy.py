"""
Tests for Policy dataclass.

Håndberegnede referenceværdier er noteret inline ved hvert testtilfælde.
"""

import math
import pytest
from datetime import date

from verd.policy import Policy
from verd.policy_state import PolicyState


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def standard_police() -> Policy:
    """
    Standardpolice brugt i de fleste tests.

    Foedselsdato: 1985-01-01
    Tegningsdato: 2025-01-01
    Depoter: aldersopsparing=500, ratepension=300, livrente=200 enheder
    """
    return Policy(
        foedselsdato=date(1985, 1, 1),
        tegningsdato=date(2025, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="G1",
        omkostningssats_id="O1",
        loen=600_000.0,
        indbetalingsprocent=0.15,
        aldersopsparing=500.0,
        ratepensionsopsparing=300.0,
        ratepensionsvarighed=10,
        livrentedepot=200.0,
    )


# ---------------------------------------------------------------------------
# Oprettelse og standardværdier
# ---------------------------------------------------------------------------

def test_standard_tilstand_er_i_live(standard_police):
    """Nyoprettet police skal have tilstand I_LIVE som default."""
    assert standard_police.tilstand is PolicyState.I_LIVE


def test_kan_oprette_med_doed_tilstand():
    police = Policy(
        foedselsdato=date(1980, 6, 15),
        tegningsdato=date(2020, 6, 15),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="G1",
        omkostningssats_id="O1",
        loen=500_000.0,
        indbetalingsprocent=0.10,
        aldersopsparing=100.0,
        ratepensionsopsparing=50.0,
        ratepensionsvarighed=10,
        livrentedepot=50.0,
        tilstand=PolicyState.DOED,
    )
    assert police.tilstand is PolicyState.DOED


# ---------------------------------------------------------------------------
# alder_ved_tegning()
# ---------------------------------------------------------------------------

def test_alder_ved_tegning_heltal_noejagtigt(standard_police):
    """
    Haandberegning:
      (date(2025,1,1) - date(1985,1,1)).days = 14610
      14610 / 365.25 ≈ 39.9863
    Forventet: ~40 år (indenfor ±0.1 år).
    """
    alder = standard_police.alder_ved_tegning()
    assert alder == pytest.approx(14610 / 365.25, abs=1e-9)


def test_alder_ved_tegning_formula(standard_police):
    """alder_ved_tegning bruger (tegningsdato - foedselsdato).days / 365.25."""
    forventet = (date(2025, 1, 1) - date(1985, 1, 1)).days / 365.25
    assert standard_police.alder_ved_tegning() == pytest.approx(forventet)


def test_alder_ved_tegning_er_positiv(standard_police):
    assert standard_police.alder_ved_tegning() > 0


def test_alder_ved_tegning_samme_dato_er_nul():
    """Hvis tegningsdato == foedselsdato er alderen 0."""
    police = Policy(
        foedselsdato=date(2000, 1, 1),
        tegningsdato=date(2000, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="G1",
        omkostningssats_id="O1",
        loen=0.0,
        indbetalingsprocent=0.0,
        aldersopsparing=0.0,
        ratepensionsopsparing=0.0,
        ratepensionsvarighed=10,
        livrentedepot=0.0,
    )
    assert police.alder_ved_tegning() == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# total_enheder()
# ---------------------------------------------------------------------------

def test_total_enheder_summer_tre_depoter(standard_police):
    """
    Haandberegning: 500 + 300 + 200 = 1000 enheder.
    """
    assert standard_police.total_enheder() == pytest.approx(1000.0)


def test_total_enheder_alle_nul():
    police = Policy(
        foedselsdato=date(1990, 1, 1),
        tegningsdato=date(2030, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="G1",
        omkostningssats_id="O1",
        loen=0.0,
        indbetalingsprocent=0.0,
        aldersopsparing=0.0,
        ratepensionsopsparing=0.0,
        ratepensionsvarighed=10,
        livrentedepot=0.0,
    )
    assert police.total_enheder() == pytest.approx(0.0)


def test_total_enheder_kun_aldersopsparing():
    """Kun aldersopsparingsdepot udfyldt — de andre to er nul."""
    police = Policy(
        foedselsdato=date(1985, 1, 1),
        tegningsdato=date(2025, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="G1",
        omkostningssats_id="O1",
        loen=600_000.0,
        indbetalingsprocent=0.15,
        aldersopsparing=750.0,
        ratepensionsopsparing=0.0,
        ratepensionsvarighed=10,
        livrentedepot=0.0,
    )
    assert police.total_enheder() == pytest.approx(750.0)


# ---------------------------------------------------------------------------
# depotvaerdi_dkk()
# ---------------------------------------------------------------------------

def test_depotvaerdi_dkk_ved_enhedspris_1(standard_police):
    """
    Haandberegning: total_enheder=1000, enhedspris=1.0 → 1000 DKK.
    """
    assert standard_police.depotvaerdi_dkk(1.0) == pytest.approx(1000.0)


def test_depotvaerdi_dkk_skalerer_med_enhedspris(standard_police):
    """
    Haandberegning: total_enheder=1000, enhedspris=2.5 → 2500 DKK.
    """
    assert standard_police.depotvaerdi_dkk(2.5) == pytest.approx(2500.0)


def test_depotvaerdi_dkk_er_total_gange_pris(standard_police):
    """depotvaerdi_dkk == total_enheder * enhedspris for vilkårlig pris."""
    for pris in [0.5, 1.0, 1.23, 100.0, 1234.56]:
        forventet = standard_police.total_enheder() * pris
        assert standard_police.depotvaerdi_dkk(pris) == pytest.approx(forventet)


def test_depotvaerdi_dkk_nul_enheder():
    police = Policy(
        foedselsdato=date(1985, 1, 1),
        tegningsdato=date(2025, 1, 1),
        pensionsalder=67,
        er_under_udbetaling=False,
        gruppe_id="G1",
        omkostningssats_id="O1",
        loen=0.0,
        indbetalingsprocent=0.0,
        aldersopsparing=0.0,
        ratepensionsopsparing=0.0,
        ratepensionsvarighed=10,
        livrentedepot=0.0,
    )
    assert police.depotvaerdi_dkk(150.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Felter gemt korrekt
# ---------------------------------------------------------------------------

def test_felter_gemt_korrekt(standard_police):
    assert standard_police.pensionsalder == 67
    assert standard_police.er_under_udbetaling is False
    assert standard_police.gruppe_id == "G1"
    assert standard_police.omkostningssats_id == "O1"
    assert standard_police.loen == pytest.approx(600_000.0)
    assert standard_police.indbetalingsprocent == pytest.approx(0.15)
    assert standard_police.aldersopsparing == pytest.approx(500.0)
    assert standard_police.ratepensionsopsparing == pytest.approx(300.0)
    assert standard_police.ratepensionsvarighed == 10
    assert standard_police.livrentedepot == pytest.approx(200.0)
