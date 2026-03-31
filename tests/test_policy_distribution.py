"""
Tests for PolicyDistribution type og initial_distribution().
"""

import pytest
from datetime import date

from verd.policy import Policy
from verd.policy_state import PolicyState
from verd.policy_distribution import PolicyDistribution, initial_distribution


@pytest.fixture
def police() -> Policy:
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
# initial_distribution()
# ---------------------------------------------------------------------------

def test_initial_distribution_returnerer_liste(police):
    dist = initial_distribution(police)
    assert isinstance(dist, list)


def test_initial_distribution_har_eet_element(police):
    """Ved start er policen i sin starttilstand med sandsynlighed 1."""
    dist = initial_distribution(police)
    assert len(dist) == 1


def test_initial_distribution_sandsynlighed_er_1(police):
    dist = initial_distribution(police)
    _, prob = dist[0]
    assert prob == pytest.approx(1.0)


def test_initial_distribution_indeholder_samme_police(police):
    dist = initial_distribution(police)
    gemt_police, _ = dist[0]
    assert gemt_police is police


def test_initial_distribution_er_liste_af_tupler(police):
    dist = initial_distribution(police)
    element = dist[0]
    assert isinstance(element, tuple)
    assert len(element) == 2


# ---------------------------------------------------------------------------
# PolicyDistribution som type (strukturelle tests)
# ---------------------------------------------------------------------------

def test_policy_distribution_kan_have_to_tilstande(police):
    """
    En distribution med to tilstande (I_LIVE + DOED) skal fungere —
    dette er det typiske udseende efter ét fremregningsstep.
    """
    doed_police = Policy(
        foedselsdato=police.foedselsdato,
        tegningsdato=police.tegningsdato,
        pensionsalder=police.pensionsalder,
        er_under_udbetaling=police.er_under_udbetaling,
        gruppe_id=police.gruppe_id,
        omkostningssats_id=police.omkostningssats_id,
        loen=police.loen,
        indbetalingsprocent=police.indbetalingsprocent,
        aldersopsparing=0.0,
        ratepensionsopsparing=0.0,
        ratepensionsvarighed=police.ratepensionsvarighed,
        livrentedepot=0.0,
        tilstand=PolicyState.DOED,
    )
    p_liv = 0.999
    p_doed = 0.001
    dist: PolicyDistribution = [(police, p_liv), (doed_police, p_doed)]

    assert len(dist) == 2
    sandsynligheder = [p for _, p in dist]
    assert sum(sandsynligheder) == pytest.approx(1.0)
