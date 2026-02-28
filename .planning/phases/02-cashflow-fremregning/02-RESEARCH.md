# Phase 2: Cashflow-fremregning - Research

**Researched:** 2026-02-28
**Domain:** Aktuariel cashflow-fremregning — betalingsprocesser, Markov-modeller, diskret approximation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Matematisk fundament — betalingsprocesser**

Produkter defineres via betalingsprocessen `B(t)` (jf. LivStok kap. 14–16):

```
dB(t) = b^{Z(t)}(t) dt  +  Σ_k b^{Z(t-)k}(t) dN^k(t)
```

- `b^j(t)` — kontinuert betalingsrate i tilstand j (positiv = ydelse til forsikringstager, negativ = præmie fra forsikringstager)
- `b^{jk}(t)` — engangsbetaling ved overgang fra tilstand j til k

For vores to-tilstandsmodel (J = {0=I_LIVE, 1=DOED}) er betalingsprocessen:

```
b^0(t) = -π(t) × 1_{NOT er_under_udbetaling}        # præmierate (negativ = indbetaling)
b^{01}(t) = sum_at_risk(t)                            # dødsfaldsdækning ved overgang I_LIVE→DOED
b^1(t) = 0                                            # ingen betalinger i DOED (absorberende tilstand)
```

**Overgangsintensitet og Kolmogorov**

Overgangssandsynligheder styres af Kolmogorovs fremadrettede ligning.

Diskret approksimation (dt = 1/12 år):
```
p_{00}(0, t+dt) = p_{00}(0, t) × exp(-μ(alder(t)) × dt)
```

**Præmie (b^0):**
```
π(t) = loen × indbetalingsprocent / 12   # DKK per måned
```

**Dødsfaldsdækning (b^{01}) — sum at risk:**
For unit-link uden ekstern dødsfaldsdækning: `b^{01}(t) = 0` og `risikopraemie = 0`.
`sum_at_risk = 0` i baseline. Risikopræmie-kolonnen indgår i DataFramen men er 0.

**Indbetalingsfordeling på depoter:**
Fordeles proportionalt baseret på aktuelle enheder-andele:
```
andel_j = depot_j_enheder / total_enheder
enheder_til_depot_j = (π(t) / enhedspris(t)) × andel_j
```
Hvis `total_enheder = 0`: fordeles ligeligt (1/3 til hvert depot).

**Returtype:** pandas DataFrame — én række per tidsstep. Alle beløb i DKK.

**Cashflow-kolonner (minimum):**
| Kolonne | Type | Forklaring |
|---|---|---|
| `t` | float | Tid i år fra tegningsdato (0.0, 1/12, 2/12, ...) |
| `alder` | float | Forsikringstagers alder i år |
| `sandsynlighed_i_live` | float | p_{00}(0,t) — Kolmogorov-sandsynlighed |
| `enhedspris` | float | DeterministicMarket.enhedspris(t) |
| `depot_enheder` | float | Samlet enheder (total_enheder) |
| `depot_dkk` | float | depot_enheder × enhedspris |
| `indbetaling_dkk` | float | π(t) × dt (råværdi, ikke p-vægtet) |
| `risikopraemie_dkk` | float | μ(alder) × sum_at_risk × dt (0 i baseline) |

`indbetaling_dkk` og `risikopraemie_dkk` er IKKE sandsynlighedsvægtede — `sandsynlighed_i_live` bruges til vægtning i Fase 3.

**Rækkefølge af operationer inden for tidsstep:**
1. Indbetaling — præmie konverteres til enheder og lægges til depoterne
2. Afkast — ingen enheds-ændring; enhedspris vokser automatisk via DeterministicMarket
3. Biometri — `p_live *= exp(-μ(alder) × dt)` via BiometricModel.survival_probability
4. Omkostninger — udskudt til Phase 2+

**Tidsskala:**
- `t` i år som float fra tegningsdato
- Alder: `alder(t) = alder_ved_tegning + t`
- Fremregning kører fra `t=0` til `sandsynlighed_i_live < 1e-6` eller max-alder = 110 år

**Modulstruktur:** Ny fil `verd/projection.py` — indeholder `fremregn()` og evt. hjælpefunktioner

### Claude's Discretion

Dødsfaldsdækning (b^{01}): sum_at_risk = 0 i baseline (Claude's decision). Kan raffineres i Fase 3 hvis konkret doedssum tilføjes til Policy.

### Deferred Ideas (OUT OF SCOPE)

- Udbetalingslogik — `b^0(t) > 0` som pensionsannuitet i udbetalingsfasen
- Ekstern dødsfaldsdækning — sum_at_risk > 0 kræver `doedssum` felt på Policy
- Omkostninger — OmkostningssatsID-opslag defineres i Phase 2+
- Sandsynlighedsvægtede cashflows som separate kolonner — Fase 3 håndterer dette
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CASH-01 | En funktion accepterer PolicyDistribution + BiometricModel + FinancialMarket og returnerer en tidsserie af cashflows | `fremregn()` i `verd/projection.py` — signaturen er fastlagt i CONTEXT.md, DataFrame-returtype er besluttet |
| CASH-02 | Cashflows beregnes med korrekt rækkefølge inden for hvert tidsstep: indbetalinger → afkast → biometri → omkostninger | Rækkefølgen er låst i CONTEXT.md; afkast er implicit (enhedspris stiger, enheder uændret), omkostninger er no-op i v1.0 |
| CASH-03 | Overlevelsessandsynlighed beregnes korrekt via p = exp(-µ * dt) med dt = 1/12 | BiometricModel.survival_probability(alder, dt) er allerede implementeret korrekt i Fase 1 |
| CASH-04 | Sandsynlighedsvægtet fremregning opdaterer PolicyDistribution korrekt over tid | I to-tilstandsmodellen: sandsynlighed_i_live opdateres, DOED-sandsynlighed = 1 - sandsynlighed_i_live; sum = 1 invariant skal bevares |
| CASH-05 | Cashflow-tabellen kan printes for en eksempelpolicy | Eksempelpolicen i `examples/eksempel_police.py` bruges som basis; ny `examples/eksempel_cashflow.py` udvidelse |
</phase_requirements>

---

## Summary

Fase 2 implementerer `fremregn()` — hjørnestensfunktionen der fremregner en `PolicyDistribution` måned for måned og returnerer en `pandas.DataFrame` med én række per månedligt tidsstep. Alle matematiske og arkitekturmæssige beslutninger er allerede låst i CONTEXT.md. Fase 1 har leveret alle nødvendige byggeklodser: `BiometricModel.survival_probability()`, `DeterministicMarket.enhedspris()`, `Policy.total_enheder()`, `FinancialMarket.dkk_til_enheder()` og `initial_distribution()`. Fase 2 er primært om at samle disse korrekt i et fremregningsloop.

Den matematiske kerne er en diskret approksimation af Kolmogorovs fremadrettede ligning: `p_live(t+dt) = p_live(t) × exp(-μ(alder(t)) × dt)`. Depot-opdateringen sker i enheder (ikke DKK) for at bevare afkastets transparens: enhedspris stiger, men enheder ændres kun ved indbetaling. Rækkefølgen inden for hvert step (indbetaling → afkast implicit → biometri) er fastlagt og skal dokumenteres eksplicit i koden.

`pandas` er allerede nævnt som del af stack i CLAUDE.md (evt.) og er den naturlige returtype da Fase 3 og 4 vil konsumere DataFrame til diskontering og output. `numpy` er allerede en projektafhængighed.

**Primary recommendation:** Implementér `fremregn()` i `verd/projection.py` som et rent while-loop med eksplicit `dt = 1/12` konstant, accumulation af rækker i en liste, og afsluttende `pd.DataFrame(rows)` konvertering. Ingen numpy-vektorisering nødvendig i v1.0.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11+ | Runtime | Fastlagt i pyproject.toml |
| pandas | 2.x | DataFrame returtype for cashflow-tabel | CLAUDE.md nævner det; naturlig valg for tidsserie-tabel |
| numpy | >=1.24 | Numerik (allerede i pyproject.toml) | Fastlagt afhængighed; exp() via math.exp tilstrækkeligt her |
| math (stdlib) | 3.11 | exp(), log() beregninger | Allerede brugt i BiometricModel og DeterministicMarket |
| dataclasses (stdlib) | 3.11 | Policy er allerede dataclass | Fastlagt fra Fase 1 |

### Bemærkning om pandas
pandas er ikke i `pyproject.toml` endnu — kun numpy er. `pandas` skal tilføjes som afhængighed. Alternativt kunne man bruge en liste af dicts og lade kalderen konvertere, men CONTEXT.md specificerer eksplicit `pandas DataFrame` som returtype.

**Installation:**
```bash
# Tilføj til pyproject.toml dependencies:
# "pandas>=2.0"
pip install pandas
```

---

## Architecture Patterns

### Recommended Project Structure
```
verd/
├── policy.py              # Fase 1 — DONE
├── policy_state.py        # Fase 1 — DONE
├── policy_distribution.py # Fase 1 — DONE
├── biometric_model.py     # Fase 1 — DONE
├── gompertz_makeham.py    # Fase 1 — DONE
├── financial_market.py    # Fase 1 — DONE
├── deterministic_market.py # Fase 1 — DONE
├── __init__.py            # Fase 1 — skal udvides med fremregn
└── projection.py          # Fase 2 — NY FIL
examples/
├── eksempel_police.py     # Fase 1 — DONE
└── eksempel_cashflow.py   # Fase 2 — NY FIL (CASH-05)
```

### Pattern 1: Fremregningsloop med akkumulering
**What:** While-loop der akkumulerer dict-rækker og konverterer til DataFrame til sidst
**When to use:** Altid i v1.0 — enkel og debugging-venlig

```python
# verd/projection.py

DT: float = 1 / 12  # Fastlagt månedligt tidsstep — ændres IKKE

def fremregn(
    fordeling: PolicyDistribution,
    biometri: BiometricModel,
    marked: FinancialMarket,
) -> pd.DataFrame:
    """
    Sandsynlighedsvægtet fremregning af en PolicyDistribution.

    Returnerer en pandas DataFrame med én række per månedligt tidsstep (dt = 1/12 år).
    Fremregningen kører fra t=0 til sandsynlighed_i_live < 1e-6 eller alder > 110 år.

    Betalingsprocessen (jf. LivStok kap. 14-16):
        b^0(t) = -π(t) × 1_{NOT er_under_udbetaling}   (præmierate)
        b^{01}(t) = sum_at_risk(t) = 0  (ingen ekstern dødsfaldsdækning i baseline)
        b^1(t) = 0                       (DOED er absorberende)

    Rækkefølge inden for hvert tidsstep:
        1. Indbetaling:  π(t) konverteres til enheder og tilskrives depoterne
        2. Afkast:       implicit — enhedspris vokser via marked.enhedspris(t); enheder uændret
        3. Biometri:     p_live *= survival_probability(alder, DT)
        4. Omkostninger: udskudt til Phase 2+
    """
    ...
```

### Pattern 2: Aldersberegning
**What:** Beregn alder ved `t` ud fra fødselsdato og tegningsdato
**When to use:** Ved hvert tidsstep for at slå dødelighedsintensitet op

```python
from datetime import date

def _beregn_alder_ved_tegning(policy: Policy) -> float:
    """Beregn forsikringstagers alder i år ved tegningsdato."""
    delta = policy.tegningsdato - policy.foedselsdato
    return delta.days / 365.25

# I fremregningsloopet:
# alder(t) = alder_ved_tegning + t
```

Bemærk: `eksempel_police.py` bruger allerede `(nu - police.foedselsdato).days / 365.25` — konsistens er vigtig.

### Pattern 3: Proportional indbetalingsfordeling
**What:** Fordel præmien i enheder proportionalt på de tre depoter
**When to use:** Hvert tidsstep i opsparingsfasen (`er_under_udbetaling = False`)

```python
def _fordel_indbetaling(policy: Policy, praemie_enheder: float) -> Policy:
    """
    Fordel præmie proportionalt på de tre depoter.

    Andel bestemt af aktuelle enheder. Fallback: ligeligt hvis total_enheder = 0.
    """
    total = policy.total_enheder()
    if total == 0.0:
        andel_alder = andel_rate = andel_livrente = 1.0 / 3.0
    else:
        andel_alder = policy.aldersopsparing / total
        andel_rate = policy.ratepensionsopsparing / total
        andel_livrente = policy.livrentedepot / total

    # Returnér ny Policy (immutable dataclass-kopi med opdaterede depoter)
    from dataclasses import replace
    return replace(
        policy,
        aldersopsparing=policy.aldersopsparing + praemie_enheder * andel_alder,
        ratepensionsopsparing=policy.ratepensionsopsparing + praemie_enheder * andel_rate,
        livrentedepot=policy.livrentedepot + praemie_enheder * andel_livrente,
    )
```

### Pattern 4: Stoptilstand for fremregning
**What:** Terminationsbetingelse for fremregningsloopet
**When to use:** Evalueres efter biometrisk opdatering

```python
MAX_ALDER: float = 110.0
P_LIVE_TÆRSKEL: float = 1e-6

# I loopet:
if p_live < P_LIVE_TÆRSKEL or alder > MAX_ALDER:
    break
```

### Anti-Patterns to Avoid

- **DKK i depoterne:** Depoter gemmes som ENHEDER, aldrig DKK. DKK beregnes kun til output-kolonner ved hjælp af `marked.enhedspris(t)`. Fase 1 har allerede etableret dette mønster.
- **Direkte mutation af Policy-dataclassen:** `Policy` er en `@dataclass` — brug `dataclasses.replace()` for at skabe opdaterede kopier. Undgå at mutere felter in-place.
- **Afkast som eksplicit enhedsændring:** Afkastet afspejles KUN som stigende `enhedspris(t)` — antallet af enheder ændres IKKE af afkastet. Forkert: `enheder *= (1 + r * dt)`.
- **Sandsynlighedsvægtede cashflows i DataFrame:** `indbetaling_dkk` og `risikopraemie_dkk` skal være råværdier (ikke ganget med `sandsynlighed_i_live`). Fase 3 ganger med sandsynlighed. Blandes dette, mister man sporbarhed.
- **pandas som loop-struktur:** Byg rækker som en liste af dicts; kald `pd.DataFrame(rows)` én gang til sidst. Undgå at appende til DataFrame inde i loopet (kvadratisk kompleksitet).
- **Magic number 1/12:** `dt = 1/12` skal være en navngiven modul-konstant `DT`, ikke et inlined tal.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Overlevelsessandsynlighed | Eget exp-udtryk | `biometri.survival_probability(alder, DT)` | Allerede implementeret og testet i Fase 1 |
| Enhedspris ved t | Eget exp-udtryk | `marked.enhedspris(t)` | Allerede implementeret i DeterministicMarket |
| DKK → enheder konvertering | Division med enhedspris | `marked.dkk_til_enheder(dkk, t)` | Allerede implementeret i FinancialMarket |
| Initial distribution | Manuel liste | `initial_distribution(policy)` | Allerede implementeret i policy_distribution.py |
| DataFrame-konstruktion | Custom tabeller | `pd.DataFrame(rows)` fra liste af dicts | pandas er projektets officielle returtype |
| Dataclass-kopier med ændrede felter | Manuel `__init__` eller dict-kopi | `dataclasses.replace(policy, felt=nyt_val)` | Stdlib, sikker, bevarer type |

**Key insight:** Fase 1 har leveret alle primitive operationer. Fase 2 er en orkestreringsopgave — sammensæt de eksisterende byggeklodser i den rigtige rækkefølge.

---

## Common Pitfalls

### Pitfall 1: Afkast modelleres som enheds-ændring
**What goes wrong:** Kode laver `enheder *= exp(r * dt)` for at afspejle afkast
**Why it happens:** Intuitivt virker det rigtigt — depotet vokser med afkastet
**How to avoid:** I et unit-link produkt afspejles afkastet UDELUKKENDE i enhedsprisens stigning (`enhedspris(t) = enhedspris_0 × exp(r × t)`). Antallet af enheder ændres kun ved køb/salg (indbetaling/udbetaling). `DKK(t) = enheder × enhedspris(t)` vokser automatisk korrekt.
**Warning signs:** `depot_enheder`-kolonnen stiger uden indbetalinger i opsparingsfasen

### Pitfall 2: Mutation af Policy-objektet i loopet
**What goes wrong:** `policy.aldersopsparing += nye_enheder` direkte på det originale objekt
**Why it happens:** Dataclasses minder om mutable objekter
**How to avoid:** Brug `dataclasses.replace()` for at skabe en ny Policy-instans. Policyen i PolicyDistribution skal kun opdateres med nye indbetalinger — ikke med "sandsynlighed-vægtet state".
**Warning signs:** Bivirkninger der påvirker den originale policy-instans

### Pitfall 3: Sandsynlighederne summer ikke til 1
**What goes wrong:** Efter biometrisk opdatering summer sandsynligheder i PolicyDistribution til < 1
**Why it happens:** I to-tilstandsmodellen: sandsynlighed for DOED er `1 - p_live`. Hvis DOED-tilstand ikke opdateres korrekt, går summen tabt.
**How to avoid:** I to-tilstandsmodellen med absorberende DOED er det tilstrækkeligt at tracke `p_live` alene. `p_doed = 1 - p_live`. Tilføj `assert abs(sum(s for _, s in fordeling) - 1.0) < 1e-10` som sanity check.
**Warning signs:** `sum(sandsynligheder) < 1` efter et par steps

### Pitfall 4: Alder beregnet inkonsistent
**What goes wrong:** Alder runder til nærmeste heltal, eller bruger forkert kalenderaritmetik
**Why it happens:** `date.year - foedselsdato.year` ignorerer måneder/dage
**How to avoid:** Brug `(tegningsdato - foedselsdato).days / 365.25` — præcis som `eksempel_police.py` allerede gør. Alder ved tid `t` er `alder_ved_tegning + t`.
**Warning signs:** Dødelighedsintensiteten hopper diskontinuerligt ved heltalskift

### Pitfall 5: pandas tilføjet til __init__.py import men ikke til pyproject.toml
**What goes wrong:** `import pandas` fejler ved installation i et nyt miljø
**Why it happens:** pandas ikke i `pyproject.toml` dependencies
**How to avoid:** Tilføj `"pandas>=2.0"` til `dependencies` i `pyproject.toml` inden implementering
**Warning signs:** `ModuleNotFoundError: No module named 'pandas'`

### Pitfall 6: Fremregningsperiode ikke terminerer
**What goes wrong:** Loop kører til alder 110 år for unge policyer — meget lange tabeller
**Why it happens:** Manglende eller forkert terminationsbetingelse
**How to avoid:** Tjek BÅDE `p_live < 1e-6` OG `alder > MAX_ALDER (110)` efter biometrisk step. For en 40-årig er dette ca. 840 rækker (70 år × 12) — acceptabelt.
**Warning signs:** DataFrame med tusindvis af rækker, alle med `sandsynlighed_i_live ≈ 0`

---

## Code Examples

Verified patterns from project codebase (Fase 1):

### Overlevelsessandsynlighed (eksisterende API)
```python
# Source: verd/biometric_model.py — BiometricModel.survival_probability
# p(x, dt) = exp(-µ(x) · dt)
p_overlev = biometri.survival_probability(alder, dt)
```

### Enhedspris og DKK-konvertering (eksisterende API)
```python
# Source: verd/deterministic_market.py og verd/financial_market.py
kurs = marked.enhedspris(t)            # DKK/enhed ved tidspunkt t
enheder = marked.dkk_til_enheder(dkk, t)  # DKK → enheder
dkk = marked.enheder_til_dkk(enheder, t)  # enheder → DKK
```

### Dataclass replace-mønster
```python
# Source: Python stdlib dataclasses.replace — anbefalet måde at "opdatere" dataclasses
from dataclasses import replace
ny_policy = replace(
    gammel_policy,
    aldersopsparing=gammel_policy.aldersopsparing + nye_enheder,
)
```

### Komplet fremregningsloop (blueprint)
```python
import pandas as pd
from dataclasses import replace
from verd.policy import Policy
from verd.policy_distribution import PolicyDistribution
from verd.biometric_model import BiometricModel
from verd.financial_market import FinancialMarket

DT: float = 1 / 12           # Månedligt tidsstep — fastlåst
MAX_ALDER: float = 110.0     # Fremregning stopper ved denne alder
P_LIVE_TÆRSKEL: float = 1e-6 # Fremregning stopper under denne sandsynlighed


def fremregn(
    fordeling: PolicyDistribution,
    biometri: BiometricModel,
    marked: FinancialMarket,
) -> pd.DataFrame:
    # Udtræk startpolicen (I_LIVE) og startssandsynlighed
    policy, p_live = fordeling[0]  # Start: [(policy, 1.0)]

    # Beregn alder ved tegningsdato
    alder_ved_tegning = (policy.tegningsdato - policy.foedselsdato).days / 365.25

    rows = []
    t = 0.0

    while True:
        alder = alder_ved_tegning + t
        kurs = marked.enhedspris(t)

        # --- 1. Indbetaling (kun i opsparingsfasen) ---
        if not policy.er_under_udbetaling:
            praemie_dkk = policy.loen * policy.indbetalingsprocent / 12
            praemie_enheder = marked.dkk_til_enheder(praemie_dkk, t)
            policy = _fordel_indbetaling(policy, praemie_enheder)
        else:
            praemie_dkk = 0.0

        # --- 2. Afkast (implicit — enhedspris stiger, enheder uændret) ---

        # --- 3. Biometri ---
        mu = biometri.mortality_intensity(alder)
        sum_at_risk = 0.0  # Ingen ekstern dødsfaldsdækning i baseline
        risikopraemie_dkk = mu * sum_at_risk * DT  # = 0 i baseline

        # Registrér tidsstep
        rows.append({
            "t": t,
            "alder": alder,
            "sandsynlighed_i_live": p_live,
            "enhedspris": kurs,
            "depot_enheder": policy.total_enheder(),
            "depot_dkk": policy.depotvaerdi_dkk(kurs),
            "indbetaling_dkk": praemie_dkk,
            "risikopraemie_dkk": risikopraemie_dkk,
        })

        # Opdatér sandsynlighed (Kolmogorov fremadrettet ligning, diskret approx.)
        p_live *= biometri.survival_probability(alder, DT)

        # Terminationsbetingelse
        t += DT
        if p_live < P_LIVE_TÆRSKEL or alder_ved_tegning + t > MAX_ALDER:
            break

    return pd.DataFrame(rows)
```

### Eksempel cashflow print (CASH-05 blueprint)
```python
# examples/eksempel_cashflow.py

from verd import DeterministicMarket, GompertzMakeham, Policy, PolicyState, initial_distribution
from verd.projection import fremregn

biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)
marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)
# ... opret police som i eksempel_police.py ...
fordeling = initial_distribution(police)
df = fremregn(fordeling, biometri, marked)

print(df[["t", "alder", "sandsynlighed_i_live", "depot_dkk", "indbetaling_dkk"]].head(24).to_string(index=False))
print(f"\nTotal rækker: {len(df)}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cashflows som liste af floats | pandas DataFrame med navngivne kolonner | Besluttet CONTEXT.md | Fuld sporbarhed, nem debugging, direkte Fase 3-integration |
| DKK i depoterne | Enheder i depoterne | Besluttet Fase 1 | Korrekt unit-link semantik; afkast via enhedspris, ikke enhedsantal |
| Implicitte biometriske overgange | Eksplicit Kolmogorov-approksimation med `exp(-µ × dt)` | Besluttet CONTEXT.md | Matematisk transparent, konsistent med LivStok teori |

**Deprecated/outdated for dette projekt:**
- NumPy-baseret vektorisering: Ikke nødvendig i v1.0 (enkeltpolicy); reducerer læsbarhed. Gem til v2.
- Sandsynlighedsvægtede DKK-kolonner i DataFramen: Adskillelse af råværdi og sandsynlighed er eksplicit besluttet for sporbarhed.

---

## Open Questions

1. **pandas i pyproject.toml**
   - What we know: `numpy>=1.24` er allerede der; pandas nævnes i CLAUDE.md som "evt."
   - What's unclear: Ingen eksplicit version specificeret
   - Recommendation: Tilføj `"pandas>=2.0"` til pyproject.toml som første opgave i Fase 2

2. **__init__.py eksport af fremregn()**
   - What we know: `__init__.py` eksporterer alle Fase 1-klasser via `__all__`
   - What's unclear: Skal `fremregn` eksporteres direkte fra `verd`-pakken?
   - Recommendation: Ja — tilføj `from verd.projection import fremregn` og `"fremregn"` til `__all__`

3. **Policy-mutation vs. immutabilitet**
   - What we know: `Policy` er `@dataclass` uden `frozen=True`; kan muteres
   - What's unclear: Om `dataclasses.replace()` er det rigtige mønster, eller om loopet skal arbejde direkte med enheds-akkumulering uden at kopiere Policy
   - Recommendation: Brug `replace()` for immutabilitet og klarhed. Alternativt kan man holde enheder i lokale variabler og kun bruge Policy som read-only konfigurationsobjekt. Det andet alternativ er enklere og undgår `replace()` kompleksitet.

4. **Tidspunkt for indbetalingsregistrering**
   - What we know: Rækkefølgen er "indbetaling → biometri" inden for step
   - What's unclear: Skal `indbetaling_dkk` i DataFramen repræsentere præmien ved STARTEN af steget (før biometri), eller er det en teknisk detalje?
   - Recommendation: Registrér `indbetaling_dkk` som præmien der er gyldig for tidssteget `t` (starten af steget). `sandsynlighed_i_live` er p_{00}(0,t) ved starten af steget. Fase 3 ganger disse.

---

## Sources

### Primary (HIGH confidence)
- Direkte inspektion af `verd/` kildekode — alle Fase 1 APIs verificeret
- `verd/biometric_model.py` — `survival_probability()` API og matematik
- `verd/financial_market.py` — `dkk_til_enheder()`, `enheder_til_dkk()` API
- `verd/deterministic_market.py` — `enhedspris(t)` API og matematik
- `verd/policy.py` — `total_enheder()`, `depotvaerdi_dkk()` API
- `verd/policy_distribution.py` — `initial_distribution()` API
- `.planning/phases/02-cashflow-fremregning/02-CONTEXT.md` — låste beslutninger

### Secondary (MEDIUM confidence)
- CLAUDE.md — teknisk stack og designprincipper
- `examples/eksempel_police.py` — etablerede kode-mønstre (aldersberegning, biometri-kald)
- `pyproject.toml` — aktuelle afhængigheder

### Tertiary (LOW confidence)
- Ingen LOW confidence sources i denne research — alt er direkte verificeret mod projektets kildekode og låste CONTEXT.md beslutninger

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verificeret mod pyproject.toml og CLAUDE.md
- Architecture: HIGH — alle APIs verificeret direkte i kildekoden; mønstrene er veldefinerede
- Pitfalls: HIGH — baseret på den eksisterende kodebase og låste beslutninger i CONTEXT.md

**Research date:** 2026-02-28
**Valid until:** 2026-04-28 (stabil domæne — ingen eksterne afhængigheder der ændrer sig hurtigt)
