"""
Eksempel: Thiele-baseret sandsynlighedsvægtet fremregning (Phase 2 done-kriterium).

Demonstrerer:
  - Fremregning af betingede forventede depoter via Thieles differentialligning
  - Sandsynlighedsvægtet depot (prob_I_LIVE × betinget depot)
  - Cashflow-tabel for en eksempelpolicy over 5 år (60 månedlige skridt)

Kør med:
    python examples/eksempel_fremregning.py
"""

from datetime import date

from verd import (
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    fremregn,
    initial_distribution,
    simpel_opsparings_cashflow,
)

# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)

# ---------------------------------------------------------------------------
# Police
# ---------------------------------------------------------------------------
police = Policy(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,             # 600.000 DKK/år
    indbetalingsprocent=0.15,   # 15 % af løn → 90.000 DKK/år
    aldersopsparing=1_200.0,    # 1.200 enh. × 100 DKK = 120.000 DKK
    ratepensionsopsparing=800.0,  # 800 enh. × 100 DKK = 80.000 DKK
    ratepensionsvarighed=10,
    livrentedepot=500.0,        # 500 enh. × 100 DKK = 50.000 DKK
    tilstand=PolicyState.I_LIVE,
)

fordeling = initial_distribution(police)

# ---------------------------------------------------------------------------
# Fremregning — 5 år (60 månedlige skridt) via Thieles ODE
# ---------------------------------------------------------------------------
ANTAL_AAR = 5
skridt = fremregn(
    distribution=fordeling,
    antal_skridt=ANTAL_AAR * 12,
    biometric=biometri,
    market=marked,
    cashflow_funktion=simpel_opsparings_cashflow,
    dt=1 / 12,
    t_0=0.0,
)

# ---------------------------------------------------------------------------
# Udskriv tabel — én linje per år (hvert 12. skridt)
# ---------------------------------------------------------------------------
print("=" * 100)
print("THIELE-BASERET FREMREGNING — BETINGEDE FORVENTEDE DEPOTER")
print("=" * 100)
print(
    f"{'t (år)':>7}  {'Alder':>6}  {'p(I_LIVE)':>10}  "
    f"{'Ald.opsp.':>12}  {'Ratepens.':>12}  {'Livrente':>12}  "
    f"{'Total depot':>13}  {'E[Depot]':>13}  {'Indbetal.':>11}  {'Kurs':>8}"
)
print("-" * 100)

for s in skridt:
    # Vis hvert 12. skridt (månedligt → årligt) plus det initiale
    step_nr = round(s.t * 12)
    if step_nr % 12 == 0:
        print(
            f"{s.t:>7.2f}  {s.alder:>6.2f}  {s.prob_i_live:>10.6f}  "
            f"{s.aldersopsparing_dkk:>12,.0f}  {s.ratepension_dkk:>12,.0f}  "
            f"{s.livrente_dkk:>12,.0f}  "
            f"{s.total_depot_dkk:>13,.0f}  {s.forventet_depot_dkk:>13,.0f}  "
            f"{s.indbetaling_dkk:>11,.0f}  {s.enhedspris:>8.4f}"
        )

print("-" * 100)

# ---------------------------------------------------------------------------
# Detaljeret månedlig tabel (første 6 måneder)
# ---------------------------------------------------------------------------
print()
print("MÅNEDLIG DETALJE — FØRSTE 6 MÅNEDER")
print("-" * 100)
print(
    f"{'t (år)':>7}  {'Alder':>6}  {'p(I_LIVE)':>10}  "
    f"{'Total depot':>13}  {'E[Depot]':>13}  "
    f"{'Indbetal./md':>13}  {'Kurs':>8}"
)
print("-" * 100)
for s in skridt[:7]:
    print(
        f"{s.t:>7.4f}  {s.alder:>6.2f}  {s.prob_i_live:>10.8f}  "
        f"{s.total_depot_dkk:>13,.2f}  {s.forventet_depot_dkk:>13,.2f}  "
        f"{s.indbetaling_dkk:>13,.2f}  {s.enhedspris:>8.4f}"
    )

print()
print("=" * 100)
print("Phase 2 done-kriterium: Cashflow-tabel printet via Thieles differentialligning ✓")
print("=" * 100)
