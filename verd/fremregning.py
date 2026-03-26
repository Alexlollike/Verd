"""
Fremregning — sandsynlighedsvægtet fremregning via koblede Thiele-ligninger.

Fremregningen kombinerer to lag for hvert tidsstep:

    1. Betinget depotfremregning (koblede Thiele-ligninger):
       For hver aktiv tilstand i fremregnes hvert depot via:
           Δn_d = dt · [π_d − b_d − c_d − Σ_j µ_ij·R_ij_d] / P(t)
       Det biometriske led er altid eksplicit, selv når R_ij_d = 0.

    2. Sandsynlighedsopdatering (Kolmogorov fremadligning, Euler):
       For hver tilstand i opdateres sandsynligheden:
           Δp_i = dt · [Σ_{j→i} µ_ji·p_j  −  Σ_{i→j} µ_ij·p_i]
       Dette reducerer til p(t+dt) = p(t)·exp(−µ·dt) for to-tilstands-modellen.

Det forventede depot (sandsynlighedsvægtet) for tilstand i på tidspunkt t:
    E[V_d^i(t)] = p_i(t) · V_d^i(t | tilstand i)

Standardfunktioner:
    ``simpel_opsparings_cashflow`` — indbetaling = loen × indbetalingsprocent
    ``nul_risikosum``              — R_ij_d = 0 for alle d (rent unit-link)
    ``standard_toetilstands_model``— fabriksfunktion for I_LIVE → DOED
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

from verd.financial_market import FinancialMarket
from verd.omkostning import OmkostningsFunktion, nul_omkostning
from verd.overgang import Tilstandsmodel
from verd.policy import Policy
from verd.policy_distribution import PolicyDistribution
from verd.policy_state import PolicyState
from verd.thiele import CashflowSats, RisikoSummer, thiele_step

# Signaturer for brugerdefinerbare funktioner
CashflowFunktion = Callable[[Policy, float], CashflowSats]
RisikosumFunktion = Callable[[Policy, float], RisikoSummer]


@dataclass
class TilstandsSkridt:
    """
    Depotværdier og sandsynlighed for én tilstand på ét tidspunkt.

    Attributes
    ----------
    tilstand:
        Markov-tilstanden dette resultat tilhører.
    prob:
        Sandsynlighed for at policen er i denne tilstand, p_i(t).
    aldersopsparing_dkk:
        Betinget forventet aldersopsparing i DKK (givet tilstand i).
    ratepension_dkk:
        Betinget forventet ratepensionsopsparing i DKK (givet tilstand i).
    livrente_dkk:
        Betinget forventet livrentedepot i DKK (givet tilstand i).
    """

    tilstand: PolicyState
    prob: float
    aldersopsparing_dkk: float
    ratepension_dkk: float
    livrente_dkk: float

    @property
    def total_depot_dkk(self) -> float:
        """Samlet betinget forventet depot i DKK (givet tilstanden)."""
        return self.aldersopsparing_dkk + self.ratepension_dkk + self.livrente_dkk

    @property
    def forventet_depot_dkk(self) -> float:
        """Sandsynlighedsvægtet forventet depot: p_i(t) × total_depot_dkk."""
        return self.prob * self.total_depot_dkk


@dataclass
class FremregningsSkridt:
    """
    Resultat af ét tidsstep i den sandsynlighedsvægtede fremregning.

    Indeholder resultater for alle tilstande i modellen.

    Attributes
    ----------
    t:
        Tid fra tegningsdato i år.
    alder:
        Forsikringstagers alder på tidspunkt t.
    tilstande:
        Liste af ``TilstandsSkridt`` — ét element per tilstand i modellen.
    indbetaling_dkk:
        Samlet indbetalt beløb fra I_LIVE-tilstanden i dette tidsstep (DKK).
    udbetaling_dkk:
        Samlet udbetalt beløb fra I_LIVE-tilstanden i dette tidsstep (DKK).
    omkostning_dkk:
        Samlet omkostning fra I_LIVE-tilstanden i dette tidsstep (DKK).
    enhedspris:
        Enhedspris P(t) på tidspunkt t (DKK/enhed).
    """

    t: float
    alder: float
    tilstande: list[TilstandsSkridt]
    indbetaling_dkk: float
    udbetaling_dkk: float
    omkostning_dkk: float
    enhedspris: float
    cashflows_i_live: CashflowSats = field(default_factory=CashflowSats)

    def _find(self, tilstand: PolicyState) -> TilstandsSkridt | None:
        """Opslag på et ``TilstandsSkridt`` med givet tilstand."""
        return next((s for s in self.tilstande if s.tilstand == tilstand), None)

    @property
    def i_live(self) -> TilstandsSkridt | None:
        """``TilstandsSkridt`` for I_LIVE-tilstanden (None hvis ikke i modellen)."""
        return self._find(PolicyState.I_LIVE)

    @property
    def prob_i_live(self) -> float:
        """Sandsynlighed for I_LIVE på tidspunkt t (0.0 hvis ikke i modellen)."""
        s = self.i_live
        return s.prob if s is not None else 0.0

    @property
    def forventet_depot_dkk(self) -> float:
        """Sandsynlighedsvægtet forventet total depot i DKK for I_LIVE-tilstanden."""
        s = self.i_live
        return s.forventet_depot_dkk if s is not None else 0.0


def simpel_opsparings_cashflow(policy: Policy, t: float) -> CashflowSats:
    """
    Standard cashflow-funktion for opsparingsfasen.

    Indbetalingen er ``loen × indbetalingsprocent`` og fordeles proportionalt
    til de tre depoter baseret på deres aktuelle enhedsandele.
    Er alle depoter tomme, fordeles indbetalingen ligeligt (1/3 til hvert depot).

    Udbetalinger og omkostninger er nul i denne simple model.

    Håndterer automatisk andre tilstande (f.eks. INVALID) ved at returnere
    nul-cashflow hvis ``policy.er_under_udbetaling`` er sat eller for
    tilstande der ikke er I_LIVE.

    Parameters
    ----------
    policy:
        Policyen hvis cashflows skal beregnes.
    t:
        Tid fra tegningsdato (år).

    Returns
    -------
    CashflowSats
        Cashflow-satser i DKK/år.
    """
    if policy.er_under_udbetaling or policy.tilstand != PolicyState.I_LIVE:
        return CashflowSats()

    indbetaling_aar = policy.loen * policy.indbetalingsprocent

    total_enh = policy.total_enheder()
    if total_enh > 0.0:
        f_ald = policy.aldersopsparing / total_enh
        f_rate = policy.ratepensionsopsparing / total_enh
        f_liv = policy.livrentedepot / total_enh
    else:
        f_ald = f_rate = f_liv = 1.0 / 3.0

    return CashflowSats(
        indbetaling_aldersopsparing=indbetaling_aar * f_ald,
        indbetaling_ratepension=indbetaling_aar * f_rate,
        indbetaling_livrente=indbetaling_aar * f_liv,
    )


def nul_risikosum(policy: Policy, t: float) -> RisikoSummer:
    """
    Standard risikosum-funktion for rent unit-link uden ekstra dødsbenefit.

    Returnerer R_ij_d = 0 for alle depoter, svarende til at dødsbenefit =
    depotsværdi og DOED-reserven er nul:

        R_ij_d = S_ij_d + V_j_d − V_i_d = V_i_d + 0 − V_i_d = 0

    Det biometriske led −µ_ij·R_ij_d bidrager numerisk med nul, men er
    strukturelt til stede i ligningerne (se ``thiele_step``).

    Parameters
    ----------
    policy:
        Ikke brugt — returnerer altid ``RisikoSummer()`` med nulværdier.
    t:
        Ikke brugt.

    Returns
    -------
    RisikoSummer
        Risikosum med alle depot-værdier = 0.
    """
    return RisikoSummer()


def standard_toetilstands_model(biometric: "BiometricModel") -> Tilstandsmodel:  # noqa: F821
    """
    Fabriksfunktion: standard to-tilstands-model med I_LIVE → DOED.

    Opretter en ``Tilstandsmodel`` med én overgang: I_LIVE → DOED med
    Gompertz-Makeham (eller anden ``BiometricModel``) som intensitet.
    Risikosummen er nul (rent unit-link).

    Parameters
    ----------
    biometric:
        Biometrisk model der leverer dødelighedsintensiteten µ(x+t).

    Returns
    -------
    Tilstandsmodel
        Tilstandsmodel med overgang I_LIVE → DOED.
    """
    from verd.overgang import BiometriOvergangsIntensitet, Overgang

    return Tilstandsmodel(
        overgange=[
            Overgang(
                fra=PolicyState.I_LIVE,
                til=PolicyState.DOED,
                intensitet=BiometriOvergangsIntensitet(biometric),
                risikosum_func=nul_risikosum,
            )
        ]
    )


def fremregn(
    distribution: PolicyDistribution,
    antal_skridt: int,
    market: FinancialMarket,
    tilstandsmodel: Tilstandsmodel,
    cashflow_funktion: CashflowFunktion = simpel_opsparings_cashflow,
    omkostnings_funktion: OmkostningsFunktion = nul_omkostning,
    dt: float = 1.0 / 12.0,
    t_0: float = 0.0,
) -> list[FremregningsSkridt]:
    """
    Sandsynlighedsvægtet fremregning via koblede Thiele-ligninger.

    For hvert tidsstep:
      1. Thiele-skridt for hver aktiv (ikke-absorberende) tilstand:
         - Beregn cashflows via ``cashflow_funktion(policy_i, t)``
         - Tillæg omkostninger via ``omkostnings_funktion(policy_i, t)``
         - Beregn overgangsled: [(µ_ij, R_ij)] for hvert udgående overgang
         - Kald ``thiele_step`` → opdaterede betingede depoter
      2. Kolmogorov fremadligning (Euler) for alle tilstande:
         Δp_i = dt · [Σ_{j→i} µ_ji·p_j  −  Σ_{i→j} µ_ij·p_i]

    Parameters
    ----------
    distribution:
        Initial ``PolicyDistribution``. Typisk fra ``initial_distribution(policy)``.
        Hvert ``Policy``-objekt har et ``tilstand``-felt der identificerer tilstanden.
        Absorberende tilstande (ingen udgående overgange) fremregnes ikke via Thiele
        — kun sandsynligheder opdateres.
    antal_skridt:
        Antal tidsstep der fremregnes (f.eks. 12 × antal_år).
    market:
        Finansielt marked — leverer enhedspris P(t).
    tilstandsmodel:
        Definition af tilstandsrummet: alle overgange med intensiteter og risikosummer.
    cashflow_funktion:
        ``(Policy, t) → CashflowSats`` — indbetalinger og udbetalinger for hvert skridt.
        Standard: ``simpel_opsparings_cashflow``.
    omkostnings_funktion:
        ``(Policy, t) → float`` — samlet omkostningssats i DKK/år (AUM + styk + øvrige).
        Lægges oven på ``cashflow_funktion``s eventuelle ``omkostning``-felt.
        Standard: ``nul_omkostning`` (ingen ekstra omkostninger).
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).
    t_0:
        Starttidspunkt i år fra tegningsdato. Standard: 0.0.

    Returns
    -------
    list[FremregningsSkridt]
        Tidsserie af fremregningsresultater. Første element svarer til t_0;
        hvert efterfølgende element er ét skridt fremme.

    Raises
    ------
    ValueError
        Hvis ``distribution`` er tom.
    """
    if not distribution:
        raise ValueError("distribution er tom")

    # Byg den interne tilstandstabel: {PolicyState: (Policy, prob)}
    # Policy-objekterne bærer depotværdierne for den givne tilstand.
    tilstands_dict: dict[PolicyState, tuple[Policy, float]] = {}
    for pol, prob in distribution:
        tilstands_dict[pol.tilstand] = (pol, prob)

    # Sikr at alle tilstande der optræder i modellen er repræsenteret,
    # opret manglende med nul-depoter og nul-sandsynlighed.
    reference_policy = distribution[0][0]
    import dataclasses as _dc
    for tilstand in tilstandsmodel.alle_tilstande():
        if tilstand not in tilstands_dict:
            nul_policy = _dc.replace(
                reference_policy,
                aldersopsparing=0.0,
                ratepensionsopsparing=0.0,
                livrentedepot=0.0,
                tilstand=tilstand,
            )
            tilstands_dict[tilstand] = (nul_policy, 0.0)

    alder_ved_tegning = reference_policy.alder_ved_tegning()
    aktive = tilstandsmodel.ikke_absorberende()
    t = t_0

    # -----------------------------------------------------------------------
    # Hjælpefunktion: byg TilstandsSkridt-liste fra tilstands_dict
    # -----------------------------------------------------------------------
    def _byg_tilstande_skridt(t_: float) -> list[TilstandsSkridt]:
        P = market.enhedspris(t_)
        return [
            TilstandsSkridt(
                tilstand=tilstand,
                prob=prob,
                aldersopsparing_dkk=pol.aldersopsparing * P,
                ratepension_dkk=pol.ratepensionsopsparing * P,
                livrente_dkk=pol.livrentedepot * P,
            )
            for tilstand, (pol, prob) in tilstands_dict.items()
        ]

    # -----------------------------------------------------------------------
    # Initial tilstand (t = t_0)
    # -----------------------------------------------------------------------
    skridt: list[FremregningsSkridt] = [
        FremregningsSkridt(
            t=t,
            alder=alder_ved_tegning + t,
            tilstande=_byg_tilstande_skridt(t),
            indbetaling_dkk=0.0,
            udbetaling_dkk=0.0,
            omkostning_dkk=0.0,
            enhedspris=market.enhedspris(t),
        )
    ]

    # -----------------------------------------------------------------------
    # Fremregningsløkke
    # -----------------------------------------------------------------------
    for _ in range(antal_skridt):
        alder = alder_ved_tegning + t

        # Forudberegn intensiteter µ_ij for alle overgange ved denne alder
        mu_vaerdier: dict[tuple[PolicyState, PolicyState], float] = {
            (o.fra, o.til): o.intensitet.intensitet(alder)
            for o in tilstandsmodel.overgange
        }

        # ---- 1. Thiele-skridt for aktive tilstande -------------------------
        ny_policies: dict[PolicyState, Policy] = {}
        total_indbetaling = 0.0
        total_udbetaling = 0.0
        total_omkostning = 0.0
        cashflows_il = CashflowSats()

        for tilstand in aktive:
            pol, prob = tilstands_dict[tilstand]

            cashflows_raa = cashflow_funktion(pol, t)
            ekstra_omk = omkostnings_funktion(pol, t)
            cashflows = _dc.replace(
                cashflows_raa,
                omkostning=cashflows_raa.omkostning + ekstra_omk,
            )

            # Byg overgangs_led: [(µ_ij, R_ij)] for hvert udgående overgang
            overgangs_led: list[tuple[float, RisikoSummer]] = [
                (
                    mu_vaerdier[(o.fra, o.til)],
                    o.risikosum_func(pol, t),
                )
                for o in tilstandsmodel.ud_overgange(tilstand)
            ]

            ny_policies[tilstand] = thiele_step(pol, t, dt, market, cashflows, overgangs_led)

            if tilstand == PolicyState.I_LIVE:
                cashflows_il = cashflows
                total_indbetaling += cashflows.total_indbetaling * dt
                total_udbetaling += cashflows.total_udbetaling * dt
                total_omkostning += cashflows.omkostning * dt

        # ---- 2. Kolmogorov fremadligning (Euler) ---------------------------
        # Δp_i = dt · [Σ_{j→i} µ_ji·p_j  −  Σ_{i→j} µ_ij·p_i]
        nye_probs: dict[PolicyState, float] = {}
        for tilstand in tilstands_dict:
            _, p_i = tilstands_dict[tilstand]

            # Ind-strøm: sandsynlighed der ankommer fra andre tilstande
            ind = sum(
                mu_vaerdier[(o.fra, o.til)] * tilstands_dict[o.fra][1]
                for o in tilstandsmodel.overgange
                if o.til == tilstand and o.fra != tilstand
            )
            # Ud-strøm: sandsynlighed der forlader denne tilstand
            ud = sum(
                mu_vaerdier[(o.fra, o.til)] * p_i
                for o in tilstandsmodel.ud_overgange(tilstand)
            )
            nye_probs[tilstand] = p_i + dt * (ind - ud)

        # ---- Opdater tilstands_dict ----------------------------------------
        t += dt

        for tilstand in tilstands_dict:
            pol_gammel, _ = tilstands_dict[tilstand]
            pol_ny = ny_policies.get(tilstand, pol_gammel)  # absorberende: uændret
            tilstands_dict[tilstand] = (pol_ny, max(0.0, nye_probs[tilstand]))

        # ---- Optag skridt --------------------------------------------------
        skridt.append(
            FremregningsSkridt(
                t=t,
                alder=alder_ved_tegning + t,
                tilstande=_byg_tilstande_skridt(t),
                indbetaling_dkk=total_indbetaling,
                udbetaling_dkk=total_udbetaling,
                omkostning_dkk=total_omkostning,
                enhedspris=market.enhedspris(t),
                cashflows_i_live=cashflows_il,
            )
        )

    return skridt
