"""
Eksempel: Opret og print en unit-link police (Phase 1 done-kriterium).

Demonstrerer:
  - Oprettelse af en Policy med depotværdier i enheder
  - GompertzMakeham dødelighedsmodel
  - DeterministicMarket med voksende enhedspris
  - Konvertering DKK ↔ enheder
  - PolicyDistribution (initial)

Kør med:
    python examples/eksempel_police.py
"""

from datetime import date
import math

from verd import (
    DeterministicMarket,
    GompertzMakeham,
    Policy,
    PolicyState,
    initial_distribution,
)

# ---------------------------------------------------------------------------
# Biometrisk model — Gompertz-Makeham med typiske danske parametre (mand)
# µ(x) = 0.0005 + 0.00004 · exp(0.09 · x)
# ---------------------------------------------------------------------------
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)

# ---------------------------------------------------------------------------
# Finansielt marked — deterministisk med 5 % kontinuert afkast
# Startende enhedspris: 100 DKK/enhed
# ---------------------------------------------------------------------------
marked = DeterministicMarket(r=math.log(1.05), enhedspris_0=100.0)

# ---------------------------------------------------------------------------
# Police — unit-link aldersopsparing + ratepension + livrente
# Depotværdier er angivet i enheder (units), ikke DKK
# ---------------------------------------------------------------------------
police = Policy(
    foedselsdato=date(1980, 1, 15),
    tegningsdato=date(2020, 6, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=600_000.0,          # 600.000 DKK/år
    indbetalingsprocent=0.15,  # 15 % af løn
    aldersopsparing=1_200.0,   # 1.200 enheder × 100 DKK = 120.000 DKK
    ratepensionsopsparing=800.0,  # 800 enheder × 100 DKK = 80.000 DKK
    ratepensionsvarighed=10,
    livrentedepot=500.0,       # 500 enheder × 100 DKK = 50.000 DKK
    tilstand=PolicyState.I_LIVE,
)

# ---------------------------------------------------------------------------
# Print police
# ---------------------------------------------------------------------------
print("=" * 60)
print("EKSEMPEL POLICE (UNIT-LINK)")
print("=" * 60)
print(police)

# ---------------------------------------------------------------------------
# Enhedspris og depotværdi ved t=0 og t=1
# ---------------------------------------------------------------------------
t0, t1 = 0.0, 1.0
kurs_t0 = marked.enhedspris(t0)
kurs_t1 = marked.enhedspris(t1)

print()
print("ENHEDSPRIS OG DEPOTVÆRDI")
print("-" * 60)
print(f"  Enhedspris t=0          : {kurs_t0:>10.4f} DKK/enhed")
print(f"  Enhedspris t=1          : {kurs_t1:>10.4f} DKK/enhed")
print(f"  Vækst i enhedspris      : {(kurs_t1/kurs_t0 - 1):.2%}")
print()
print(f"  Depotværdi t=0          : {police.depotvaerdi_dkk(kurs_t0):>12,.2f} DKK")
print(f"  Depotværdi t=1          : {police.depotvaerdi_dkk(kurs_t1):>12,.2f} DKK")
print(f"  (Enhedsbeholdning uændret: {police.total_enheder():,.1f} enh.)")

# ---------------------------------------------------------------------------
# DKK → enheder konvertering (præmie indbetaling)
# ---------------------------------------------------------------------------
praemie_dkk = 10_000.0
enheder_kobt = marked.dkk_til_enheder(praemie_dkk, t0)
tilbageregnet_dkk = marked.enheder_til_dkk(enheder_kobt, t0)

print()
print("KONVERTERING DKK → ENHEDER (PRÆMIE)")
print("-" * 60)
print(f"  Præmie                  : {praemie_dkk:>10,.2f} DKK")
print(f"  Køber enheder (t=0)     : {enheder_kobt:>10.4f} enh.")
print(f"  Tilbageregnet (kontrol) : {tilbageregnet_dkk:>10,.2f} DKK  ✓")

# ---------------------------------------------------------------------------
# Biometri — dødelighedsintensitet og overlevelsessandsynlighed
# ---------------------------------------------------------------------------
# Beregn nuværende alder fra fødselsdato og tegningsdato (approksimeret)
import datetime
nu = police.tegningsdato
alder_aar = (nu - police.foedselsdato).days / 365.25

dt = 1 / 12  # månedligt tidsstep

mu = biometri.mortality_intensity(alder_aar)
p_overlev = biometri.survival_probability(alder_aar, dt)
q_doed = biometri.death_probability(alder_aar, dt)

print()
print("BIOMETRI (VED TEGNING)")
print("-" * 60)
print(f"  Alder ved tegning       : {alder_aar:.2f} år")
print(f"  µ(x) dødelighedsintens. : {mu:.6f} år⁻¹")
print(f"  p (overlev 1 måned)     : {p_overlev:.8f}")
print(f"  q (dø i 1 måned)        : {q_doed:.8f}")

# ---------------------------------------------------------------------------
# PolicyDistribution
# ---------------------------------------------------------------------------
fordeling = initial_distribution(police)
print()
print("POLICEDISTRIBUTION (INITIAL)")
print("-" * 60)
for pol, sandsynlighed in fordeling:
    print(f"  Tilstand: {pol.tilstand.value:<10}  Sandsynlighed: {sandsynlighed:.4f}")
print(f"  Sum af sandsynligheder  : {sum(s for _, s in fordeling):.4f}  ✓")

print()
print("=" * 60)
print("Phase 1 done-kriterium: Police beskrevet i kode og printet ✓")
print("=" * 60)
