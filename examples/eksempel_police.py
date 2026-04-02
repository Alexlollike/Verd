"""
Eksempel: End-to-end fremregning af en unit-link police.

Demonstrerer:
  - Oprettelse af Policy med depotværdier i DKK
  - GompertzMakeham dødelighedsmodel
  - DeterministicMarket
  - Sandsynlighedsvægtet fremregning via Thieles differentialligning
  - Validering (kør_alle_checks)
  - Formateret output: print_policeoversigt + eksport til CSV

Kør med:
    python examples/eksempel_police.py
"""

import math
from datetime import date

import matplotlib
matplotlib.use("Agg")  # Ikke-interaktiv backend (egnet til CI/scripts)
import matplotlib.pyplot as plt
import pandas as pd

from verd import (
    BeloebsgraenserOpslag,
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    PraemieFlow,
    STANDARD_SATSER_FILSTI,
    fremregn,
    indlæs_offentlige_satser,
    initial_distribution,
    plot_fra_dataframe,
    kør_alle_checks,
    praemieflow_cashflow_funktion,
    print_policeoversigt,
    eksporter_cashflows_csv,
    simpel_cashflow_funktion,
    standard_toetilstands_model,
    standard_omkostning,
)

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)

# ---------------------------------------------------------------------------
# Police — 40-årig mand, 250.000 DKK i depot, pensionering ved 67
# ---------------------------------------------------------------------------
police = Policy.fra_dkk(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,
    indbetalingsprocent=0.15,
    aldersopsparing=120_000.0,
    ratepensionsopsparing=80_000.0,
    ratepensionsvarighed=10,
    livrentedepot=50_000.0,
    enhedspris=marked.enhedspris(0.0),
    tilstand=PolicyState.I_LIVE,
)

fordeling = initial_distribution(police)
tilstandsmodel = standard_toetilstands_model(biometri)

# ---------------------------------------------------------------------------
# Beløbsgrænser — slå 2026-satser op for en 46-årig (21 år til folkepension)
# Betingelse: "normal" (>7 år til pension) → aldersopsparing_max = 9.900 DKK/år
# ---------------------------------------------------------------------------
satser = indlæs_offentlige_satser(STANDARD_SATSER_FILSTI)
beloebsgraenser = BeloebsgraenserOpslag.fra_satser(
    satser=satser,
    aar=2026,
    aar_til_folkepension=67 - 46,  # 46-årig i 2026 → 21 år til folkepension
)

# ---------------------------------------------------------------------------
# Præmieallokering — fordeling af indbetalingen på de tre depoter
# Andele sat proportionalt med de initielle depotværdier:
#   aldersopsparing  : 120.000 / 250.000 = 0,48
#   ratepension      :  80.000 / 250.000 = 0,32
#   livrente (rest)  :  50.000 / 250.000 = 0,20
# Beløbsgrænser håndhæves: overskydende beløb sendes til livrente.
# ---------------------------------------------------------------------------
praemieallokering = PraemieFlow(
    risiko_bundle=None,
    beloebsgraenser=beloebsgraenser,
    ratepension_andel=80_000 / 250_000,
    aldersopsparing_andel=120_000 / 250_000,
)

# ---------------------------------------------------------------------------
# Fremregning — 60 år (opsparing + udbetaling til alder 100)
# ---------------------------------------------------------------------------
ANTAL_AAR = 60
cashflow_funktion = simpel_cashflow_funktion(
    biometric=biometri,
    market=marked,
    opsparing_func=praemieflow_cashflow_funktion(praemieallokering),
)
# Selskabet opkræver 0,5 % AUM + 200 DKK/år (omkostningsindtægt fra kunden).
# Faktisk driftsomkostning er lavere: 0,3 % AUM + 500 DKK/år.
# Differensen er selskabets omkostningsresultat pr. tidsstep.
omk_funktion = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)
faktisk_udgift = standard_omkostning(marked, aum_rate=0.003, styk_aar=500.0)

skridt = fremregn(
    distribution=fordeling,
    antal_skridt=ANTAL_AAR * 12,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=cashflow_funktion,
    omkostnings_funktion=omk_funktion,
    faktisk_udgift_funktion=faktisk_udgift,
    dt=1 / 12,
    t_0=0.0,
)

# ---------------------------------------------------------------------------
# Validering
# ---------------------------------------------------------------------------
kør_alle_checks(police, skridt, marked)
print("Validering: OK")
print()

# ---------------------------------------------------------------------------
# Samlet politikoversigt
# ---------------------------------------------------------------------------
print_policeoversigt(police, skridt, marked)

# ---------------------------------------------------------------------------
# CSV-eksport
# ---------------------------------------------------------------------------
csv_sti = "fremregning_eksempel.csv"
eksporter_cashflows_csv(skridt, csv_sti)
print()
print(f"Fremregning eksporteret til: {csv_sti}")

df = pd.read_csv(csv_sti)

# ---------------------------------------------------------------------------
# Omkostningsresultat — total over hele fremregningen
# ---------------------------------------------------------------------------
total_omk = df["omkostning_dkk"].sum()
total_faktisk = df["faktisk_udgift_dkk"].sum()
total_resultat = df["omkostningsresultat_dkk"].sum()
print(f"  Omk.indkægt (total)     : {total_omk:>12,.0f} DKK")
print(f"  Faktisk udgift (total)  : {total_faktisk:>12,.0f} DKK")
print(f"  Omkostningsresultat     : {total_resultat:>12,.0f} DKK")
print()

fig = plot_fra_dataframe(
    df=df,
    titel="Depotudvikling og ydelser — aldersopsparing + ratepension + livrente",
    pensionsalder_t=police.pensionsalder - (police.tegningsdato - police.foedselsdato).days / 365.25,
    gem_fil="depot_udvikling.png",
)

print("Plot gemt: depot_udvikling.png")
plt.close(fig)
