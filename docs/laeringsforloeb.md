# Læringsforløb: Fra police til driftsplan

Dette forløb fører dig igennem `verd`-biblioteket med fokus på, hvordan du bruger
enkeltpolice-fremregning til at opbygge cashflows til en selskabets driftsplan:
indbetalinger, udbetalinger, udgifter og omkostninger.

Hvert modul slutter med en lille opgave du løser i en Python-fil.

---

## Modul 1: Hvad er en `Policy`?

### Konceptet

En `Policy` er et **snapshot** af en forsikringspolice på ét bestemt tidspunkt.
Den indeholder to slags oplysninger:

1. **Stamdata** — hvem er forsikringstageren, og hvad er aftalen?
2. **Depottilstand** — hvor mange *enheder* ligger der i hvert depot?

Det vigtige at forstå: depoterne gemmes **ikke** i DKK, men i **enheder (units)**.
DKK-værdien beregnes altid som:

```
DKK = enheder × enhedspris(t)
```

Det svarer til, hvordan et investeringsbevis fungerer: du ejer et antal andele,
og kursen afgør hvad de er værd.

### De tre depoter

| Depot | Dansk navn | Python-felt |
|---|---|---|
| Engangsudbetaling ved pension | Aldersopsparing | `aldersopsparing` |
| Udbetaling over N år | Ratepensionsopsparing | `ratepensionsopsparing` |
| Livsvarig månedlig ydelse | Livrentedepot | `livrentedepot` |

### Eksempel

```python
from datetime import date
from verd import Policy, PolicyState

police = Policy(
    foedselsdato=date(1985, 3, 10),
    tegningsdato=date(2025, 1, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="DK_MAND_2023",
    omkostningssats_id="STANDARD",
    loen=500_000.0,           # 500.000 DKK/år
    indbetalingsprocent=0.12, # 12 % af løn
    aldersopsparing=0.0,
    ratepensionsopsparing=0.0,
    ratepensionsvarighed=10,
    livrentedepot=0.0,
    tilstand=PolicyState.I_LIVE,
)

print(f"Alder ved tegning: {police.alder_ved_tegning():.1f} år")
print(f"Samlet indbetaling/år: {police.loen * police.indbetalingsprocent:,.0f} DKK")
```

### Opgave 1

Opret en `Policy` for en 45-årig kvinde med løn 700.000 DKK og
indbetalingsprocent 15 %. Hun har 500.000 DKK i ratepensionsopsparing allerede.
Enhedsprisen er 120 DKK/enhed — hvor mange enheder svarer det til?
Print depotværdien i DKK.

> **Hint:** `enheder = DKK / enhedspris`, brug `police.depotvaerdi_dkk(enhedspris)`

---

## Modul 2: Det finansielle marked og dødelighedsmodellen

### `DeterministicMarket` — kursen over tid

Markedet leverer kun ét tal: **enhedsprisen** på et givet tidspunkt.
Med fast kontinuert rente `r` vokser kursen eksponentielt:

```
P(t) = P₀ · exp(r · t)
```

```python
from verd import DeterministicMarket

marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)

print(f"Kurs t=0:   {marked.enhedspris(0):.2f} DKK")    # 100.00
print(f"Kurs t=1:   {marked.enhedspris(1):.2f} DKK")    # 105.13
print(f"Kurs t=10:  {marked.enhedspris(10):.2f} DKK")   # 164.87
```

### `GompertzMakeham` — sandsynlighed for at overleve

Dødelighedsintensiteten `µ(x)` angiver den øjeblikkelige "dødshastighed"
ved alder `x`. Med Gompertz-Makeham:

```
µ(x) = alpha + beta · exp(sigma · x)
```

Fra intensitet til overlevelsessandsynlighed over et lille skridt `dt`:

```
p(overleve ét skridt) = exp(-µ(x) · dt)
```

```python
import math
from verd import GompertzMakeham

biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)

for alder in [30, 50, 70, 90]:
    mu = biometri.mortality_intensity(alder)
    p_overleve_aar = math.exp(-mu)
    print(f"Alder {alder}: µ={mu:.5f}/år, p(overleve 1 år)={p_overleve_aar:.4f}")
```

### Opgave 2

Brug `GompertzMakeham` til at beregne sandsynligheden for at en 40-årig
overlever til 67 (pensionsalderen) — dvs. over 27 år med månedlige skridt
`dt = 1/12`. Hvad er den samlede overlevelsessandsynlighed?

> **Hint:** Start med `p_total = 1.0`. Kør en løkke over alle måneder (27 × 12)
> og gang på: `p_total *= math.exp(-biometri.mortality_intensity(alder + k * dt) * dt)`

---

## Modul 3: Fremregning — maskinrummet

### Hvad sker der i `fremregn()`?

For hvert månedligt tidsstep gør funktionen to ting:

**1. Thiele-skridt** — opdater depoterne

```
Δn_d = dt × [π_d − b_d − c_d] / P(t)
```

| Symbol | Betydning |
|---|---|
| `π_d` | Indbetaling til depot d (DKK/år) |
| `b_d` | Udbetaling fra depot d (DKK/år) |
| `c_d` | Omkostning på depot d (DKK/år) |
| `P(t)` | Enhedspris — omregner DKK-strømme til enheder |

**2. Sandsynlighedsopdatering** (Kolmogorov fremadligning)

```
p(I_LIVE, t+dt) = p(I_LIVE, t) × exp(-µ(x+t) · dt)
```

### Hvad returnerer den?

En liste af `FremregningsSkridt` — ét per tidsstep. De vigtigste felter:

| Felt | Indhold |
|---|---|
| `s.t`, `s.alder` | Tidspunkt og alder |
| `s.indbetaling_dkk` | Præmieindtægt dette skridt (DKK) |
| `s.udbetaling_dkk` | Pensionsudbetaling dette skridt (DKK) |
| `s.omkostning_dkk` | Omkostning dette skridt (DKK) |
| `s.i_live.prob` | Sandsynlighed for at policen er aktiv |
| `s.i_live.total_depot_dkk` | Depot i DKK *givet* at policen er i live |
| `s.forventet_depot_dkk` | Sandsynlighedsvægtet depot = `prob × depot_dkk` |

### Eksempel — kør en fremregning

```python
from datetime import date
from verd import (
    Policy, PolicyState, DeterministicMarket, GompertzMakeham,
    fremregn, initial_distribution, standard_toetilstands_model,
    simpel_opsparings_cashflow,
)

marked   = DeterministicMarket(r=0.05, enhedspris_0=100.0)
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)

police = Policy(
    foedselsdato=date(1985, 3, 10),
    tegningsdato=date(2025, 1, 1),
    pensionsalder=67,
    er_under_udbetaling=False,
    gruppe_id="A",
    omkostningssats_id="A",
    loen=500_000.0,
    indbetalingsprocent=0.12,
    aldersopsparing=0.0,
    ratepensionsopsparing=5_000.0,
    ratepensionsvarighed=10,
    livrentedepot=0.0,
)

skridt = fremregn(
    distribution=initial_distribution(police),
    antal_skridt=12,  # 1 år
    market=marked,
    tilstandsmodel=standard_toetilstands_model(biometri),
    cashflow_funktion=simpel_opsparings_cashflow,
    dt=1/12,
)

for s in skridt:
    il = s.i_live
    print(
        f"t={s.t:.2f}  "
        f"depot={il.total_depot_dkk:>12,.0f} DKK  "
        f"indbetalt={s.indbetaling_dkk:>8,.0f} DKK  "
        f"p={il.prob:.6f}"
    )
```

### Opgave 3

Kør en fremregning over **40 år** (480 månedlige skridt) fra tegning til
pensionsalder. Udskriv hvert år: alder, sandsynlighedsvægtet depot
(`s.forventet_depot_dkk`) og akkumuleret indbetaling.
Hvad er det forventede depot ved pensionsalderen?

> **Hint:** Brug `step_nr = round(s.t * 12)` og print kun når
> `step_nr % 12 == 0`. Hold en løbende sum af `s.indbetaling_dkk`.

---

## Modul 4: Omkostninger — hvad koster det at drive en police?

### To slags omkostninger

`standard_omkostning(market, aum_rate, styk_aar)` returnerer en funktion
der hvert skridt beregner:

```
c(t) = aum_rate × depotværdi(t)  +  styk_aar
```

| Type | Hvad er det? | Relevans for driftsplan |
|---|---|---|
| AUM-omkostning | Procent af depot/år (ÅOP) | Skalerer med porteføljens størrelse |
| Stykomkostning | Fast beløb/police/år | Afspejler administrationsomkostning |

```python
from verd import standard_omkostning, DeterministicMarket

marked   = DeterministicMarket(r=0.05, enhedspris_0=100.0)
omk_funk = standard_omkostning(marked, aum_rate=0.005, styk_aar=300.0)
```

Funktionen sendes som `omkostnings_funktion`-argument til `fremregn()`:

```python
skridt = fremregn(
    ...,
    omkostnings_funktion=omk_funk,
)
```

### Hvad `FremregningsSkridt` leverer til driftsplanen

| Felt | Forklaring | Fortegn i P&L |
|---|---|---|
| `s.indbetaling_dkk` | Præmieindtægt | + |
| `s.udbetaling_dkk` | Pensionsudbetalinger | − |
| `s.omkostning_dkk` | Driftsomkostninger | − |

Afkastet på depotet tilhører kunden og afspejles implicit i stigende
enhedspris — det er neutralt for selskabets P&L i et rent unit-link produkt.

### Opgave 4

Kør fremregning for policen fra Opgave 3 **med**
`standard_omkostning(aum_rate=0.005, styk_aar=300)`.
Sammenlign det forventede depot ved pensionsalder med og uden omkostninger.
Hvad er forskellen i DKK?

> **Hint:** Kør `fremregn()` to gange — én gang med `nul_omkostning` og én
> gang med `standard_omkostning` — og print det sidste element i listen.

---

## Modul 5: Fra enkeltpolice til driftsplan

### Ideen

En driftsplan for selskabet er summen af enkeltpolice-fremregninger over
en hel bestand. For hver police køres `fremregn()`, og cashflows aggregeres
per kalenderår:

```python
driftsplan: dict[int, dict] = {}

for police in alle_policer:
    skridt = fremregn(distribution=initial_distribution(police), ...)
    for s in skridt:
        aar = int(s.t)
        driftsplan.setdefault(aar, {"ind": 0.0, "ud": 0.0, "omk": 0.0})
        driftsplan[aar]["ind"]  += s.indbetaling_dkk
        driftsplan[aar]["ud"]   += s.udbetaling_dkk
        driftsplan[aar]["omk"]  += s.omkostning_dkk
```

### De fire pengestrømstyper

| Strøm | Kilde i koden | Fortegn |
|---|---|---|
| Præmieindtægt | `s.indbetaling_dkk` | + |
| Pensionsudbetalinger | `s.udbetaling_dkk` | − |
| Driftsomkostninger | `s.omkostning_dkk` | − |
| Afkast på depot | Implicit via enhedspris | Neutral (tilhører kunden) |

### Udbetalingsfasen

For policer der når pensionsalderen skiftes til udbetalingsfasen ved at
sætte `er_under_udbetaling=True` og bruge `udbetaling_cashflow_funktion()`:

```python
from verd import udbetaling_cashflow_funktion

t_pension = pensionsalder - alder_ved_tegning

udbetaling_funk = udbetaling_cashflow_funktion(
    biometric=biometri,
    market=marked,
    t_pension=t_pension,
)

# Kør udbetalingsfasen fra t_pension og frem
skridt_udbetaling = fremregn(
    distribution=initial_distribution(pension_police),
    antal_skridt=20 * 12,   # 20 år i udbetaling
    market=marked,
    tilstandsmodel=standard_toetilstands_model(biometri),
    cashflow_funktion=udbetaling_funk,
)
```

### Opgave 5 — Samlet driftsplan

Opret **tre policer** med forskellig alder og lønprofil (f.eks. 30-årig,
45-årig og 55-årig). Kør fremregning for alle tre over 10 år med
`standard_omkostning`. Aggreger og print en tabel:

```
 År | Præmieindtægt | Udbetalinger | Omkostninger |      Netto
----|---------------|--------------|--------------|----------
  1 |   xxx.xxx DKK |        0 DKK |    x.xxx DKK |  xxx.xxx DKK
  2 |   ...
```

> **Hint:** Netto = præmieindtægt − udbetalinger − omkostninger.
> Den 55-årige vil nå pensionsalder inden for 10 år — hvad sker der med
> nettolinjen det år?

---

## Næste skridt efter læringsforløbet

Når du kan besvare Opgave 5, er fundamentet på plads til en reel driftsplan.
De naturlige udvidelser er:

1. **Kobling af opsparing og udbetaling** — automatisk skift til
   `udbetaling_cashflow_funktion()` når policen når `pensionsalder`
2. **Porteføljeindlæsning** — indlæs policer fra CSV eller database
3. **Scenarieanalyse** — varier `r` og dødelighedsparametre og se
   sensitiviteten på nettocashflows
4. **Risikopræmie** — tilføj en risikosum (`RisikoSummer`) for at
   modellere dødsfaldsdækning med ekstra udbetaling ved død
