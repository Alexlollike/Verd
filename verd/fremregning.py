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
from verd.policy import DoedsydelsesType, Policy
from verd.policy_distribution import PolicyDistribution
from verd.policy_state import PolicyState
from verd.praemieflow import PraemieFlow
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
        Trækkes fra depotet via Thiele-ligningen.
    faktisk_udgift_dkk:
        Faktisk policeudgift for selskabet i dette tidsstep (DKK).
        Spores separat — trækkes **ikke** fra depotet.
        Bruges til P&L-analyse: ``omkostningsresultat = omkostning_dkk - faktisk_udgift_dkk``.
        Er nul hvis ingen ``faktisk_udgift_funktion`` er angivet til ``fremregn()``.
    enhedspris:
        Enhedspris P(t) på tidspunkt t (DKK/enhed).
    """

    t: float
    alder: float
    tilstande: list[TilstandsSkridt]
    indbetaling_dkk: float
    udbetaling_dkk: float
    omkostning_dkk: float
    faktisk_udgift_dkk: float
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
        b_aldersopsparing=-indbetaling_aar * f_ald,
        b_ratepension=-indbetaling_aar * f_rate,
        b_livrente=-indbetaling_aar * f_liv,
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


def beregn_risikosum_funktion(market: FinancialMarket) -> RisikosumFunktion:
    """
    Fabriksfunktion: returnerer risikosum-funktion baseret på ``policy.doedsydelses_type``.

    Dispatches ved runtime på ``policy.doedsydelses_type``:

    **DEPOT** (depotsikring):
        b^{01}(t) = depot(t), V^{DOED}(t) = 0
        → R = b^{01} + V^{DOED} − V^{I_LIVE} = depot − depot = 0
        Ingen dødelighedsgevinster — risikopræmien og dødelsydelsen udligner hinanden.
        Kaster ``ValueError`` hvis ``er_under_udbetaling=True``.

    **INGEN** (ingen dødelsydelse):
        b^{01}(t) = 0, V^{DOED}(t) = 0
        → R_d = 0 + 0 − V^{I_LIVE}_d(t) = −depot_d(t) for hvert depot d
        Dødelighedsgevinster tilfalder overlevende og øger forventet fremtidig ydelse.

    Parameters
    ----------
    market:
        Finansielt marked — leverer enhedspris P(t) til DKK-omregning af risikosummen.

    Returns
    -------
    RisikosumFunktion
        En funktion ``(Policy, t) → RisikoSummer`` klar til brug i ``Overgang.risikosum_func``.

    Raises
    ------
    ValueError
        Hvis ``policy.doedsydelses_type == DoedsydelsesType.DEPOT``
        og ``policy.er_under_udbetaling == True``.
    """

    def _f(policy: Policy, t: float) -> RisikoSummer:
        if policy.doedsydelses_type == DoedsydelsesType.DEPOT:
            if policy.er_under_udbetaling:
                raise ValueError(
                    "DoedsydelsesType.DEPOT er kun gyldigt i opsparingsfasen "
                    "(er_under_udbetaling=True er ikke tilladt med DEPOT)"
                )
            return RisikoSummer()

        # INGEN: R_d = −V^{I_LIVE}_d = −depot_enheder_d × P(t)
        P_t = market.enhedspris(t)
        return RisikoSummer(
            aldersopsparing=-policy.aldersopsparing * P_t,
            ratepension=-policy.ratepensionsopsparing * P_t,
            livrente=-policy.livrentedepot * P_t,
        )

    return _f


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
    faktisk_udgift_funktion: OmkostningsFunktion = nul_omkostning,
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
        Trækkes fra depotet via Thiele-ligningen (omkostningsindtægt for selskabet).
        Standard: ``nul_omkostning`` (ingen ekstra omkostninger).
    faktisk_udgift_funktion:
        ``(Policy, t) → float`` — faktisk policeudgift i DKK/år for selskabet.
        Trækkes **ikke** fra depotet — kun sporet i ``FremregningsSkridt.faktisk_udgift_dkk``
        til P&L-analyse (omkostningsresultat = ``omkostning_dkk - faktisk_udgift_dkk``).
        Standard: ``nul_omkostning`` (nul faktisk udgift).
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
            faktisk_udgift_dkk=0.0,
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

        # ---- Beregn faktisk udgift for I_LIVE (spores, påvirker ikke depot) --
        il_pol_tuple = tilstands_dict.get(PolicyState.I_LIVE)
        if il_pol_tuple is not None:
            total_faktisk_udgift = faktisk_udgift_funktion(il_pol_tuple[0], t) * dt
        else:
            total_faktisk_udgift = 0.0

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
                faktisk_udgift_dkk=total_faktisk_udgift,
                enhedspris=market.enhedspris(t),
                cashflows_i_live=cashflows_il,
            )
        )

    return skridt


def simpel_cashflow_funktion(
    biometric: "BiometricModel",  # noqa: F821
    market: FinancialMarket,
    dt: float = 1.0 / 12.0,
    opsparing_func: CashflowFunktion | None = None,
) -> CashflowFunktion:
    """
    Fabriksfunktion: returnerer cashflow-funktion der automatisk skifter
    mellem opsparings- og udbetalingsfase ved pensioneringstidspunktet.

    Skiftet sker når ``t >= t_pension``, hvor::

        t_pension = policy.pensionsalder − policy.alder_ved_tegning()

    I opsparingsfasen delegeres til ``opsparing_func`` (standard:
    ``simpel_opsparings_cashflow``). I udbetalingsfasen delegeres til
    ``udbetaling_cashflow_funktion``.

    ``policy.er_under_udbetaling`` sættes korrekt via ``dataclasses.replace``
    inden delegation — cashflow-funktionerne behøver ikke kende til fasen selv.

    Parameters
    ----------
    biometric:
        Biometrisk model til livrenteannuitet-beregning i udbetalingsfasen.
    market:
        Finansielt marked til diskontfaktorer i udbetalingsfasen.
    dt:
        Tidsstep i år. Standard: 1/12 (månedligt).
    opsparing_func:
        Cashflow-funktion for opsparingsfasen. Standard:
        ``simpel_opsparings_cashflow``.

    Returns
    -------
    CashflowFunktion
        En funktion ``(Policy, t) -> CashflowSats`` klar til brug i ``fremregn()``.
    """
    import dataclasses as _dc
    from verd.udbetaling import udbetaling_cashflow_funktion

    _opsparing = opsparing_func or simpel_opsparings_cashflow
    _udbetaling_cache: dict[float, CashflowFunktion] = {}

    def _cashflow(policy: Policy, t: float) -> CashflowSats:
        t_pension = policy.pensionsalder - policy.alder_ved_tegning()

        if t < t_pension:
            pol = _dc.replace(policy, er_under_udbetaling=False) if policy.er_under_udbetaling else policy
            return _opsparing(pol, t)
        else:
            pol = _dc.replace(policy, er_under_udbetaling=True) if not policy.er_under_udbetaling else policy
            if t_pension not in _udbetaling_cache:
                _udbetaling_cache[t_pension] = udbetaling_cashflow_funktion(
                    biometric, market, t_pension, dt
                )
            return _udbetaling_cache[t_pension](pol, t)

    return _cashflow


def praemieflow_cashflow_funktion(praemieflow: PraemieFlow) -> CashflowFunktion:
    """
    Fabriksfunktion: returnerer cashflow-funktion for opsparingsfasen med præmieflow.

    Den returnerede funktion allokerer bruttopræmien (``loen × indbetalingsprocent``)
    via ``praemieflow.beregn()`` — dvs. risikopræmie fratrækkes først, og nettopræmien
    fordeles efter kundens ønsker med beløbsgrænser overholdt.

    Fortegnkonvention (standard aktuarnotation):
        b_d < 0 → indbetaling (depot vokser)
        b_d > 0 → udbetaling (depot falder)

    Betalingsstrukturen:
        π_brutto = loen × indbetalingsprocent
        π_netto  = π_brutto − risikopraemie
        b_rate   = −allokering_rate   (negativ → indbetaling)
        b_ald    = −allokering_ald
        b_liv    = −allokering_liv

    Risikopræmien registreres ikke som en depot-cashflow — den er en udgift der
    forsvinder ud af systemet (finansierer risikodækningerne). Det afspejles i at
    summen af b_rate + b_ald + b_liv = −π_netto ≠ −π_brutto.

    Parameters
    ----------
    praemieflow:
        Konfigureret ``PraemieFlow`` med risikobundle, beløbsgrænser og andele.

    Returns
    -------
    CashflowFunktion
        En funktion ``(Policy, t) -> CashflowSats`` klar til brug i ``fremregn()``.
    """

    def _cashflow(policy: Policy, t: float) -> CashflowSats:
        if policy.er_under_udbetaling or policy.tilstand != PolicyState.I_LIVE:
            return CashflowSats()

        bruttoindbetalng_aar = policy.loen * policy.indbetalingsprocent
        resultat = praemieflow.beregn(
            bruttoindbetalng_aar,
            ratepension_andel=policy.ratepension_andel,
            aldersopsparing_andel=policy.aldersopsparing_andel,
            risiko_bundle=policy.risiko_bundle,
        )

        return CashflowSats(
            b_aldersopsparing=-resultat.aldersopsparing_dkk,
            b_ratepension=-resultat.ratepension_dkk,
            b_livrente=-resultat.livrente_dkk,
        )

    return _cashflow
