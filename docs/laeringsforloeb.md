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

---

## Modul 6: Finanstilsynets dødelighedsmodel

### Konceptet

Gompertz-Makeham er en parametrisk model — praktisk, men ikke nødvendigvis kalibreret
til den danske befolkning. Finanstilsynet (FT) publicerer den officielle danske
dødelighedsmodel som forsikringsselskaber **skal** anvende til hensættelsesberegning
(Solvens II Best Estimate). Modellen er baseret på observerede dødsfald i Danmark og
opdateres løbende.

I stedet for en formel er FT-modellen en **opslagstabel**: for hvert heltal af alderen
`x` er intensiteten `µ(x)` opgivet. For ikke-heltallige aldre bruges lineær interpolation.

```
µ_FT(65.3) = µ_FT(65) + 0.3 · (µ_FT(66) − µ_FT(65))
```

FT-modellen er typisk opdelt på **køn** (mænd/kvinder) og indeholder et **margentillæg**
der øger intensiteterne konservativt (forsiktighedsprincippet).

### Sammenligning med Gompertz-Makeham

| Egenskab | Gompertz-Makeham | FT-model |
|---|---|---|
| Form | Parametrisk formel | Diskret tabel |
| Kalibrering | Generisk | Dansk befolkning |
| Kønsopdelt | Nej (vælg parametre) | Ja (separate tabeller) |
| Anvendelse | Forskning, illustration | Hensættelse (lovkrav) |

```python
from verd import FinanstilsynetModel, GompertzMakeham

ft_m = FinanstilsynetModel(koen="M", med_margen=True)
gm   = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)

for alder in [40, 60, 80]:
    print(f"Alder {alder}: FT={ft_m.mortality_intensity(alder):.5f}, "
          f"GM={gm.mortality_intensity(alder):.5f}")
```

### Opgave 6

Beregn den 27-årige overlevelsessandsynlighed fra alder 40 til 67 med FT-modellen
(mænd, med margen) og sammenlign med Gompertz-Makeham fra Opgave 2.
Hvilken model giver lavere overlevelsessandsynlighed, og hvad er den praktiske
konsekvens for hensættelsesberegningen?

> **Hint:** Brug samme løkke som Opgave 2, men udskift `biometri`-objektet.

---

## Modul 7: Ophørende livrente og dødelighedsgevinster

### Konceptet

En **ophørende livrente** (ren livslivrente) udbetaler kun så længe pensionstageren
er i live. Dør pensionstageren, ophører ydelsen — der er ingen efterladtedækning.
Til gengæld er den månedlige ydelse *højere*, fordi depotet ikke er reserveret til
efterladte: det frigøres og fordeles som **dødelighedsgevinst** til de overlevende i
kollektivet.

Modelmæssigt implementeres dette via **risikosummen** i Thiele-ligningen.
Risikosummen `R_d` angiver, hvad der sker med depot `d` ved overgang I_LIVE → DOED:

```
dV_d/dt = r·V_d + π_d − b_d − c_d − µ(x) · R_d

R_d = V_d   →  depotet overføres til kollektivet ved død (ophørende livrente)
R_d = 0     →  depotet udbetales til efterladte ved død (garanteret livrente)
```

Den højere ydelse ved ophørende livrente opstår fordi annuitetsfaktoren `ä_x` er
*kortere* end den garanterede annuitetsfaktor `ä_n` — der diskonteres for
dødelighedsrisiko:

```
Ophørende: b = V / ä_x(alder)   →  ä_x < n  →  b er større
Garanteret: b = V / ä_n          →  fast periode, ingen dødelighedsfradag
```

### Eksempel

```python
from verd import Policy

# Ophørende livrente (standard)
police_liv = Policy(..., livrente_type="ophørende", ...)

# Garanteret livrente (ingen dødelighedsgevinst, efterladte modtager restydelse)
police_garanti = Policy(..., livrente_type="garanteret", ...)
```

### Opgave 7

Kør to fremregninger i udbetalingsfasen — én med ophørende og én med garanteret
livrente — med identisk starttilstand (`V_livrentedepot = 500.000 DKK`, alder 67).
Sammenlign:
1. Den månedlige livrente-ydelse (første trin)
2. Det forventede totale udbetalte beløb over 20 år

Hvad er dødelighedsgevinsten i DKK pr. måned?

---

## Modul 8: Ratepension til efterladte ved død

### Konceptet

Ratepensionen udbetales normalt til pensionstageren over en fast periode (f.eks. 10 år).
Dør pensionstageren i løbet af perioden, fortsætter ydelserne til **efterladte** —
det er en garanteret ydelse uanset overlevelse.

Modelmæssigt kræver dette en positiv risikosum for ratepensionsdepotet ved
I_LIVE → DOED:

```
R_ratepension = V_ratepension + PV(resterende garanterede rater)
```

Nutidsværdien af de resterende rater beregnes som en **sikker annuitet**
(ingen dødelighedsfradag, da ydelserne er garanterede):

```
PV = ä_n(resterende_år) × månedlig_rate
   = Σ_{k=1}^{N} dt · v^k · månedlig_rate
```

**Bemærk**: For policer *i opsparingsfasen* er `R_ratepension = 0` — der er endnu
ingen løbende rateydelse at garantere til efterladte.

### Eksempel

```python
police = Policy(
    ...,
    ratepension_til_efterladte=True,  # standard for danske ratepensioner
    ratepensionsvarighed=10,
    er_under_udbetaling=True,
)
```

### Opgave 8

Antag en pensionsopsparer der dør præcis ved pensionsalderen (67 år) med
`V_ratepension = 800.000 DKK` og 10 år tilbage af rateperioden.

Beregn nutidsværdien af de garanterede efterladteydelser ved `r = 0.05` og
`dt = 1/12`. Hvad er `R_ratepension` på dødstidspunktet?

Sammenlign med en police *uden* efterladtedækning (`ratepension_til_efterladte=False`):
hvad er risikosummen i det tilfælde?

> **Hint:** Brug `sikker_annuitet(10, marked, t_pension, 1/12)` til at beregne
> annuitetsfaktoren, og gang med den månedlige rate: `V_ratepension / (10 * 12)`.

---

## Modul 9: Stokastiske afkast under Q-mål

### Konceptet

Det deterministiske marked (`DeterministicMarket`) bruger en fast afkastrate `r` —
der er ingen usikkerhed. I virkeligheden svinger enhedsprisen.

**Q-målet** (det risikoneutrale sandsynlighedsmål) bruges til
*markedsværdi-hensættelser* (IFRS 17, Solvens II). Under Q er det forventede afkast
lig den risikofri rente `r_f` — men volatiliteten `σ` modelleres eksplicit:

```
Under P (fysisk):   dP = µ·P·dt + σ·P·dW        (µ = forventet afkast)
Under Q (risikoneut.): dP = r_f·P·dt + σ·P·dW_Q  (µ → r_f ved ændring af mål)
```

Med **Black-Scholes**-diskretisering simuleres enhedsprisen som:

```
P(t+dt) = P(t) · exp((r_f − σ²/2)·dt + σ·√dt·Z),    Z ~ N(0,1)
```

Det forventede afkast under Q er netop `r_f` (martingale-betingelse):
```
E_Q[P(T)] = P(0) · exp(r_f · T)
```

### Tolkning

Monte Carlo over Q-stier giver **fordelingen** af fremtidige cashflows og reserver —
ikke blot ét deterministisk tal. Best Estimate (BE) under IFRS 17 er middelværdien
over Q-stier.

```python
from verd import BlackScholesMarked, monte_carlo_fremregn

marked_q = BlackScholesMarked(r_f=0.03, sigma=0.15, enhedspris_0=100.0)

resultat = monte_carlo_fremregn(
    distribution=initial_distribution(police),
    n_stier=1000,
    market=marked_q,
    ...
)

# Forventet depot + 90%-konfidensinterval per tidsstep
print(resultat.forventet_depot_dkk)
print(resultat.percentil(0.05), resultat.percentil(0.95))
```

### Opgave 9

Simulér 500 Q-stier for `BlackScholesMarked(r_f=0.03, sigma=0.20, P₀=100)`
over 10 år med månedlige skridt.

1. Verificer martingale-betingelsen: er `mean(P(10)) ≈ 100·exp(0.03·10)`?
2. Hvad er 5%- og 95%-percentilerne for `P(10)`?
3. Sammenlign den gennemsnitlige forventede depotudvikling med `DeterministicMarket(r=0.03)`.

> **Hint:** Brug `np.mean(stier[:, -1])` for middelværdien ved T=10,
> og `np.percentile(stier[:, -1], [5, 95])` for percentilerne.

---

## Modul 10: Portefølje — til- og afgang af policer

### Konceptet

Enkeltpolicefremregning er fundamentet. En **portefølje** er en samling af policer,
og porteføljens samlede cashflows er summen af de individuelle.

Det interessante opstår ved **hændelser**:
- **Tilgang** (nytegning): ny police tilkommer med tegningsomkostning
- **Afgang**: policen forlader porteføljen af en af disse årsager:
  - `DOED` — policen er allerede modelleret biometrisk
  - `GENKOBT` — forsikringstager vælger at hæve depotet tidligt (genkøbsomkostning)
  - `FRIPOLICE` — indbetalinger stopper, depot fastholdes (fripoliceomkostning)
  - `PENSIONERET` — skift til udbetalingsfase (håndteres normalt internt)

Hændelsesomkostninger indgår i porteføljens `omkostning_dkk` det relevante tidsstep.

### Aggregering

```
Portefolje-cashflow(t) = Σ_i fremregn(police_i)[t]  +  hændelsesomkostninger(t)
```

Lineariteten gælder: aggregeret reserve = sum af individuelle reserver.
Det gør det muligt at analysere en hel bestand som summen af enkeltpolicer.

### Driftsplan-linjer

| Linje | Kilde |
|---|---|
| Præmieindtægt | Σ `indbetaling_dkk` over aktive policer |
| Pensionsudbetalinger | Σ `udbetaling_dkk` over aktive policer |
| Driftsomkostninger | Σ `omkostning_dkk` + hændelsesomkostninger |
| Netto | Præmie − Udbetalinger − Omkostninger |

### Eksempel

```python
from verd import Portefolje, tilfoej_police, afmeld_police, fremregn_portefolje, AfgangAarsag

portefolje = Portefolje(policer={}, haendelser=[])
portefolje = tilfoej_police(portefolje, "P001", police_a, t=0.0, tegningsomkostning_dkk=500.0)
portefolje = tilfoej_police(portefolje, "P002", police_b, t=0.0, tegningsomkostning_dkk=500.0)

# P002 genkøbes efter 2 år
portefolje = afmeld_police(portefolje, "P002", t=2.0,
                            aarsag=AfgangAarsag.GENKOBT,
                            omkostning_dkk=1_000.0)

resultat = fremregn_portefolje(portefolje, t_start=0.0, t_slut=5.0, dt=1/12, market=marked, ...)
print(resultat.to_dataframe())
```

### Opgave 10

Opret en portefølje med tre policer (alder 30, 45, 55 — alle med
`standard_omkostning`). Den 55-årige går på pension efter 12 år.
Kør `fremregn_portefolje` over 15 år og print en aggregeret tabel med:
- Præmieindtægt, udbetalinger, omkostninger og netto per år

I hvilket år skifter netto-linjen fra positiv til negativ, og hvad skyldes det?
