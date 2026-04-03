"""
Batch-fremregning: 18 repræsentative policer til driftsplan 2027-2031.

Genererer én CSV per police i mappen ``driftsplan/``:
    driftsplan/fremregning_{alder}_{profil}.csv

Brug:
    python examples/fremregning_driftsplan.py

Designbeslutninger
------------------
- Netto månedlig indbetaling = brutto × 0,80 (20 % til forsikringsdækning
  allokeres ikke til depot). Fremregningen modellerer kun depot-delen; de 20 %
  er allerede fratrukket i tabellen nedenfor (risiko_bundle=None).
- loen og indbetalingsprocent beregnes så ``loen × indbetalingsprocent / 12``
  svarer til netto månedlig indbetaling (indbetalingsprocent=0,15 fast).
- Alle policer bruger gruppe_id="DK_MAND_2023" — kønsneutral base case til
  forretningsplan.
- ratepensionsvarighed=10 (markedsstandard).
- doedsydelses_type=DoedsydelsesType.INGEN (ingen depotsikring i base case).
- Projektionshorisont: max(60 år, 100 − alder) for at dække hele udbetalingsfasen.
- Folkepensionsalder = 67 ved beregning af beloebsgraenser.
- Beloebsgraenser håndhæves: overskydende allokering sendes til livrente.
"""

import math
import sys
from datetime import date
from pathlib import Path

# Gør det muligt at køre direkte fra projektets rod
sys.path.insert(0, str(Path(__file__).parent.parent))

from verd import (
    BeloebsgraenserOpslag,
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    PraemieFlow,
    STANDARD_SATSER_FILSTI,
    eksporter_cashflows_csv,
    fremregn,
    indlæs_offentlige_satser,
    initial_distribution,
    kør_alle_checks,
    praemieflow_cashflow_funktion,
    simpel_cashflow_funktion,
    standard_omkostning,
    standard_toetilstands_model,
)

# ---------------------------------------------------------------------------
# Faste model-parametre
# ---------------------------------------------------------------------------
TEGNINGSDATO = date(2027, 1, 1)
BIOMETRI = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
MARKED = DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)
SATSER = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
OUTPUT_DIR = Path("driftsplan")

# Koststruktur (alle policer):
#   Opkrævet:  0,5 % AUM + 200 DKK/år  (omkostningsindtægt fra kunden)
#   Faktisk:   0,3 % AUM + 500 DKK/år  (selskabets driftsomkostning)
OMK_FUNKTION = standard_omkostning(MARKED, aum_rate=0.005, styk_aar=200.0)
FAKTISK_UDGIFT = standard_omkostning(MARKED, aum_rate=0.003, styk_aar=500.0)

TILSTANDSMODEL = standard_toetilstands_model(BIOMETRI)

# ---------------------------------------------------------------------------
# Police-konfigurationer
# (alder, profil, netto_maaned_dkk, transfer_depot_dkk, (rate%, liv%, ald%), pensionsalder)
#
# split_pct = (ratepension%, livrente%, aldersopsparing%)  — svarer til
# kolonnen "Split: Rate/Liv/Alder" i specifikationen.
# ---------------------------------------------------------------------------
POLICER: list[tuple[int, str, int, int, tuple[int, int, int], int]] = [
    (30, "A",  3_600,    80_000, (55, 25, 20), 67),
    (30, "B",  5_600,   150_000, (50, 30, 20), 67),
    (35, "A",  4_000,   200_000, (50, 30, 20), 67),
    (35, "B",  6_400,   350_000, (45, 35, 20), 67),
    (40, "A",  4_400,   350_000, (48, 32, 20), 67),
    (40, "B",  7_200,   600_000, (45, 35, 20), 67),
    (40, "C", 12_000,   400_000, (30, 55, 15), 67),
    (45, "A",  4_800,   500_000, (45, 35, 20), 67),
    (45, "B",  8_000,   900_000, (40, 40, 20), 67),
    (45, "C", 14_400,   700_000, (25, 60, 15), 67),
    (50, "A",  5_200,   700_000, (40, 40, 20), 68),
    (50, "B",  8_800, 1_300_000, (35, 45, 20), 68),
    (50, "C", 17_600, 1_000_000, (20, 65, 15), 68),
    (55, "A",  5_600,   900_000, (35, 45, 20), 68),
    (55, "B",  9_600, 1_700_000, (30, 50, 20), 68),
    (55, "C", 20_000, 1_400_000, (15, 70, 15), 68),
    (60, "A",  4_000, 1_100_000, (30, 50, 20), 68),
    (60, "B",  6_400, 2_000_000, (25, 55, 20), 68),
]

# Folkepensionsalder til beregning af beloebsgraenser
FOLKEPENSIONSALDER = 67

# Fast indbetalingsprocent — loen beregnes baglæns fra netto månedlig indbetaling
INDBETALINGSPROCENT = 0.15


def fremregn_police(
    alder: int,
    profil: str,
    netto_maaned_dkk: int,
    transfer_depot_dkk: int,
    split_pct: tuple[int, int, int],
    pensionsalder: int,
) -> None:
    """
    Fremregn én police og eksporter til CSV.

    Parameters
    ----------
    alder:
        Forsikringstagers alder ved tegningsdato (hele år).
    profil:
        Profilbetegnelse ("A", "B" eller "C").
    netto_maaned_dkk:
        Netto månedlig indbetaling til depot (DKK/måned).
        Bruttoindbetaling er netto / 0,80 — de 20 % til forsikring er
        allerede fratrukket her.
    transfer_depot_dkk:
        Samlet transfereret depot ved tegning (DKK).
    split_pct:
        (rate_pct, liv_pct, ald_pct) — fordeling af transfer-depot og
        ønsket indbetalingsallokering i procent.
    pensionsalder:
        Planlagt pensioneringsalder (hele år).
    """
    rate_pct, liv_pct, ald_pct = split_pct

    # --- Depot-split ved tegning -------------------------------------------
    ald_dkk  = transfer_depot_dkk * ald_pct  / 100
    rate_dkk = transfer_depot_dkk * rate_pct / 100
    liv_dkk  = transfer_depot_dkk * liv_pct  / 100

    # --- Fødselsdato: præcis alder ved TEGNINGSDATO ------------------------
    foedselsdato = date(TEGNINGSDATO.year - alder, TEGNINGSDATO.month, TEGNINGSDATO.day)

    # --- Løn: beregn baglæns fra netto månedlig indbetaling ----------------
    # loen × indbetalingsprocent / 12 = netto_maaned_dkk
    loen = (netto_maaned_dkk * 12) / INDBETALINGSPROCENT

    # --- Police-objekt -------------------------------------------------------
    police = Policy.fra_dkk(
        foedselsdato=foedselsdato,
        tegningsdato=TEGNINGSDATO,
        pensionsalder=pensionsalder,
        er_under_udbetaling=False,
        gruppe_id="DK_MAND_2023",
        omkostningssats_id="STANDARD",
        loen=loen,
        indbetalingsprocent=INDBETALINGSPROCENT,
        aldersopsparing=ald_dkk,
        ratepensionsopsparing=rate_dkk,
        ratepensionsvarighed=10,
        livrentedepot=liv_dkk,
        enhedspris=MARKED.enhedspris(0.0),
        tilstand=PolicyState.I_LIVE,
    )

    # --- Beloebsgraenser (brug 2026-satser, folkepensionsalder=67) ----------
    aar_til_folkepension = max(0.0, float(FOLKEPENSIONSALDER - alder))
    beloebsgraenser = BeloebsgraenserOpslag.fra_satser(
        satser=SATSER,
        aar=2026,
        aar_til_folkepension=aar_til_folkepension,
    )

    # --- Præmieallokering: ønsket split, beloebsgraenser håndhæves ----------
    # Overflow fra rate/aldersopsparing sendes automatisk til livrente.
    praemieallokering = PraemieFlow(
        risiko_bundle=None,
        beloebsgraenser=beloebsgraenser,
        ratepension_andel=rate_pct / 100,
        aldersopsparing_andel=ald_pct / 100,
    )

    # --- Cashflow-funktion ---------------------------------------------------
    cashflow_funktion = simpel_cashflow_funktion(
        biometric=BIOMETRI,
        market=MARKED,
        opsparing_func=praemieflow_cashflow_funktion(praemieallokering),
    )

    fordeling = initial_distribution(police)

    # --- Fremregning: til alder 100, minimum 60 år --------------------------
    antal_aar = max(60, 100 - alder)
    skridt = fremregn(
        distribution=fordeling,
        antal_skridt=antal_aar * 12,
        market=MARKED,
        tilstandsmodel=TILSTANDSMODEL,
        cashflow_funktion=cashflow_funktion,
        omkostnings_funktion=OMK_FUNKTION,
        faktisk_udgift_funktion=FAKTISK_UDGIFT,
        dt=1 / 12,
        t_0=0.0,
    )

    # --- Validering ----------------------------------------------------------
    kør_alle_checks(police, skridt, MARKED)

    # --- CSV-eksport ---------------------------------------------------------
    OUTPUT_DIR.mkdir(exist_ok=True)
    filsti = OUTPUT_DIR / f"fremregning_{alder}_{profil}.csv"
    eksporter_cashflows_csv(skridt, filsti)

    # --- Summary-linje -------------------------------------------------------
    initial_depot = skridt[0].forventet_depot_dkk
    total_indb = sum(s.indbetaling_dkk for s in skridt)
    max_depot  = max(s.forventet_depot_dkk for s in skridt)
    print(
        f"  {alder}{profil:<2}  depot(0)={initial_depot:>12,.0f}  "
        f"Σindb={total_indb:>12,.0f}  "
        f"max(E[depot])={max_depot:>12,.0f}  → {filsti}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 80)
    print("Driftsplan-fremregninger — 18 repræsentative policer")
    print(f"Tegningsdato : {TEGNINGSDATO}")
    print(f"Output-mappe : {OUTPUT_DIR}/")
    print("=" * 80)
    print()

    fejl: list[str] = []

    for cfg in POLICER:
        alder, profil, netto_maaned, transfer_depot, split_pct, pensionsalder = cfg
        navn = f"{alder}{profil}"
        try:
            fremregn_police(alder, profil, netto_maaned, transfer_depot, split_pct, pensionsalder)
        except Exception as exc:
            fejl.append(f"  {navn}: {exc}")
            print(f"  {navn}  FEJL: {exc}")

    print()
    print("=" * 80)
    if fejl:
        print(f"FEJL i {len(fejl)} police(r):")
        for f in fejl:
            print(f)
        sys.exit(1)
    else:
        print(f"Alle {len(POLICER)} fremregninger gennemført uden fejl.")
        print(f"CSV-filer gemt i: {OUTPUT_DIR}/")
