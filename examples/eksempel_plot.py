"""
Eksempel: To-faseprojektering — opsparingsfase + udbetalingsfase.

Police med to produkter:
  - Ratepension:  800 enh. × 100 DKK =  80.000 DKK ved tegning
  - Livrente:     500 enh. × 100 DKK =  50.000 DKK ved tegning
  - Aldersopsparing: 0 (ikke aktiv)

Opsparingsfase: alder 40 → 67 (≈ 27 år), bidrag 15 % af 600.000 DKK/år.
Udbetalingsfase: ratepension over 10 år, livrente livsvarigt (op til 107 år).

Kør med:
    python examples/eksempel_plot.py
"""

import dataclasses
import matplotlib
matplotlib.use("Agg")  # Ikke-interaktiv backend (egnet til CI/scripts)

import matplotlib.pyplot as plt
from datetime import date

from verd import (
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    fremregn,
    initial_distribution,
    simpel_opsparings_cashflow,
    standard_omkostning,
    standard_toetilstands_model,
)
from verd.plot import plot_fremregning
from verd.udbetaling import udbetaling_cashflow_funktion

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)

# ---------------------------------------------------------------------------
# Police — kun ratepension + livrente, ingen aldersopsparing
# ---------------------------------------------------------------------------
police = Policy(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,
    indbetalingsprocent=0.15,        # 90.000 DKK/år
    aldersopsparing=0.0,             # ikke aktiv
    ratepensionsopsparing=800.0,     # 80.000 DKK
    ratepensionsvarighed=10,
    livrentedepot=500.0,             # 50.000 DKK
    tilstand=PolicyState.I_LIVE,
)

alder_ved_tegning = police.alder_ved_tegning()        # ≈ 40,4 år
t_pension = police.pensionsalder - alder_ved_tegning  # ≈ 26,6 år
antal_skridt_op = round(t_pension * 12)

tilstandsmodel = standard_toetilstands_model(biometri)

# Omkostningsmodel: 0% indbetalingsomkostning, 0,5% AUM p.a., 200 DKK/år styk
omk = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)

# ---------------------------------------------------------------------------
# Fase 1 — Opsparingsfase (alder 40 → 67)
# ---------------------------------------------------------------------------
skridt_op = fremregn(
    distribution=initial_distribution(police),
    antal_skridt=antal_skridt_op,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=simpel_opsparings_cashflow,
    omkostnings_funktion=omk,
    dt=1 / 12,
    t_0=0.0,
)

# ---------------------------------------------------------------------------
# Overgang til udbetalingsfase
# Rekonstruér distribution fra sidste opsparing-skridt:
# depotenheder = DKK-depotværdi / enhedspris(t_pension)
# ---------------------------------------------------------------------------
slut_op = skridt_op[-1]
P_pension = slut_op.enhedspris
il_op = slut_op.i_live

police_udb = dataclasses.replace(
    police,
    aldersopsparing=il_op.aldersopsparing_dkk / P_pension,
    ratepensionsopsparing=il_op.ratepension_dkk / P_pension,
    livrentedepot=il_op.livrente_dkk / P_pension,
    er_under_udbetaling=True,
    tilstand=PolicyState.I_LIVE,
)
police_doed_udb = dataclasses.replace(
    police_udb,
    aldersopsparing=0.0,
    ratepensionsopsparing=0.0,
    livrentedepot=0.0,
    tilstand=PolicyState.DOED,
)
prob_il = il_op.prob
dist_udb = [(police_udb, prob_il), (police_doed_udb, 1.0 - prob_il)]

# ---------------------------------------------------------------------------
# Fase 2 — Udbetalingsfase (67 → 107, 40 år)
# ---------------------------------------------------------------------------
cashflow_udb = udbetaling_cashflow_funktion(
    biometric=biometri,
    market=marked,
    t_pension=t_pension,
    dt=1 / 12,
)

skridt_udb = fremregn(
    distribution=dist_udb,
    antal_skridt=40 * 12,
    market=marked,
    tilstandsmodel=tilstandsmodel,
    cashflow_funktion=cashflow_udb,
    omkostnings_funktion=omk,
    dt=1 / 12,
    t_0=t_pension,
)

# ---------------------------------------------------------------------------
# Sammensæt (spring duplikat ved t_pension over)
# ---------------------------------------------------------------------------
skridt_alle = skridt_op + skridt_udb[1:]

# ---------------------------------------------------------------------------
# Udskriv summary
# ---------------------------------------------------------------------------
slut_udb = skridt_udb[-1]
il_udb = slut_udb.i_live

print("=" * 65)
print("POLICE — RATEPENSION + LIVRENTE — TO-FASEPROJEKTERING")
print("=" * 65)
print(f"  Opsparingsfase   : {antal_skridt_op} skridt ({antal_skridt_op/12:.1f} år)")
print(f"  Udbetalingsfase  : {40*12} skridt (40,0 år)")
print(f"  Alder ved start  : {alder_ved_tegning:.1f} år")
print(f"  Pensionsalder    : {police.pensionsalder} år  (t ≈ {t_pension:.1f} år)")
print()
print(f"  VED PENSION (t = {t_pension:.1f} år):")
if il_op:
    print(f"    p(I_LIVE)        : {il_op.prob:.6f}")
    print(f"    Ratepension      : {il_op.ratepension_dkk:>12,.0f} DKK")
    print(f"    Livrente         : {il_op.livrente_dkk:>12,.0f} DKK")
    print(f"    Total depot      : {il_op.total_depot_dkk:>12,.0f} DKK")
    # Vis første ydelse
    cf_start = skridt_udb[1].cashflows_i_live if len(skridt_udb) > 1 else None
    if cf_start:
        print(f"    Ratepensionsydelse: {cf_start.b_ratepension:>10,.0f} DKK/år")
        print(f"    Livrenteydelse    : {cf_start.b_livrente:>10,.0f} DKK/år")
print("=" * 65)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig = plot_fremregning(
    skridt=skridt_alle,
    titel="Depotudvikling og ydelser — ratepension + livrente (to-faseprojektering)",
    pensionsalder_t=t_pension,
    gem_fil="depot_udvikling.png",
)

print()
print("Plot gemt: depot_udvikling.png")
plt.close(fig)
