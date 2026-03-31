# Backlog — Verd Aktuarbibliotek

Brug `[x]` når en opgave er færdig.

---

## Feature

### v1.0 — Output og validering (Fase 2–3)

**Manglende output-funktioner (Fase 2)**
- [x] Implementer `til_dataframe(cashflows)` → `pandas.DataFrame` med formaterede kolonner
- [x] Implementer `print_cashflow_tabel(cashflows, marked)` — printer de første/sidste rækker med totaler

**Validering (Fase 3)**
- [x] Opret `verd/validering.py`
- [x] Implementer `check_sandsynligheder(fordeling)` — summer til 1.0 (tolerance 1e-9)
- [x] Implementer `check_p_alive_monoton(cashflows)` — `p_alive` er aftagende
- [x] Implementer `kør_alle_checks(police, cashflows, marked)` — kalder alle checks, kaster `ValueError` ved fejl

**CSV og formateret output (Fase 3)**
- [x] Implementer `eksporter_cashflows_csv(cashflows, marked, filsti)` — skriver cashflow DataFrame til CSV
- [x] Implementer `print_policeoversigt(police, cashflows, marked)` — samlet rapport til stdout:
  - Policestamdata
  - Nøgletal (depotværdi, V(0), sum af indbetalinger, sum af ydelser)
  - Første og sidste 5 rækker af cashflowtabel
- [x] Opdater `examples/eksempel_police.py` til komplet end-to-end eksempel

---

### A — Finanstilsynets dødelighedsmodel

**Baggrund**: Finanstilsynet publicerer Danmarks officielle dødelighedsmodel, som
forsikringsselskaber anvender til hensættelsesberegning (Solvens II, IFRS 17).
Modellen er mere detaljeret end Gompertz-Makeham: den er baseret på aldersspecifikke
intensitetstabeller med tilhørende margenbelastning og er kønsspecifik.

**Afhængigheder**: Ingen — kan starte nu.

**Opgaver**:
- [ ] Research: identificér den seneste officielle FT-dødelighedsmodel (Benchmark 2022 eller nyere)
  - Hent intensitetstabeller (µ(x) per aldersår) for mænd og kvinder
  - Afklar om margentillæg skal være valgfrit parameter
- [ ] Opret `verd/data/` mappe
- [ ] Gem FT-intensitetstabeller som CSV: `verd/data/ft_intensitet_m.csv`, `verd/data/ft_intensitet_k.csv`
  - Kolonner: `alder` (heltal), `mu` (intensitet år⁻¹)
- [ ] Implementér `verd/finanstilsynet_model.py` — ny `BiometricModel`-subklasse:
  ```python
  class FinanstilsynetModel(BiometricModel):
      def __init__(self, koen: Literal["M", "K"], med_margen: bool = True): ...
      def mortality_intensity(self, alder: float) -> float: ...
      # Lineær interpolation mellem tabelværdier for ikke-heltallige aldre
  ```
- [ ] Eksporter `FinanstilsynetModel` fra `verd/__init__.py`
- [ ] Tilføj `examples/eksempel_dødelighedsmodel.py`:
  - Plot µ(x) for FT-model (M og K) vs. Gompertz-Makeham over aldersintervallet [20, 100]
- [ ] Unit-tests i `tests/test_finanstilsynet_model.py`:
  - [ ] `µ(30)`, `µ(65)`, `µ(90)` matcher kendte FT-tabelværdier (tolerance 1e-8)
  - [ ] Lineær interpolation: µ(65.5) ligger mellem µ(65) og µ(66)
  - [ ] `survival_probability + death_probability = 1.0` præcist (nedarvet fra ABC)
  - [ ] `mortality_intensity(x) >= 0` for alle x i tabellen

**Berørte filer**: ny `verd/finanstilsynet_model.py`, ny `verd/data/*.csv`, `verd/__init__.py`

---

### B — Ophørende livrente

**Baggrund**: En ophørende livrente (ren livslivrente) ophører ved pensionstagets død —
der er ingen efterladtedækning. Til gengæld får pensionstageren *dødelighedsgevinster*:
de depoter der frigøres ved andres død fordeles til de overlevende (i kollektivet).
Modelmæssigt sættes risikosummen `R_livrentedepot = V_livrentedepot` ved I_LIVE → DOED,
så depotet overføres ved død og ikke betales ud til efterladte.

Adskilles fra den nuværende model, der implicit behandler livrenten som garanteret
(depotet udbetales gradvist uanset om pensionstageren er i live).

**Afhængigheder**: Ingen — kan starte parallelt med A.

**Opgaver**:
- [ ] Tilføj `livrente_type: Literal["ophørende", "garanteret"] = "ophørende"` på `Policy`
- [ ] Implementér `ophørende_livrente_risikosum(policy, t) → RisikoSummer` i `verd/udbetaling.py`:
  - `R_livrentedepot = V_livrentedepot` (depotet overføres til kollektivet ved død)
  - `R_aldersopsparing = R_ratepension = 0`
- [ ] Opdatér `udbetaling_cashflow_funktion` til at bruge korrekt annuitet per type:
  - `"ophørende"`: brug livrente-annuitet `ä_x(alder)` med dødelighedsfradag (nuværende adfærd)
  - `"garanteret"`: brug sikker annuitet `ä_n` (resterende antal år, ingen dødelighedsfradag)
- [ ] Gør `risikosum_funktion` til et valgfrit argument i `fremregn()` (standard: `nul_risikosum`)
- [ ] Tilføj `examples/eksempel_livrente.py`:
  - Sammenlign forventet total udbetaling: ophørende vs. garanteret livrente
  - Verificer at dødelighedsgevinsten øger den månedlige ydelse ved ophørende
- [ ] Unit-tests i `tests/test_livrente.py`:
  - [ ] Ophørende: `E[total_udbetalt] < V_livrentedepot(t_pension)` (dødelighedsfradag)
  - [ ] Garanteret: `E[total_udbetalt] ≈ V_livrentedepot(t_pension)` (ingen fradag, tolerance 1e-2)
  - [ ] Ophørende: månedlig ydelse > garanteret (kompensation for dødelighedsrisiko)

**Berørte filer**: `verd/policy.py`, `verd/udbetaling.py`, `verd/thiele.py`, `verd/fremregning.py`

---

### C — Depotsikring i opsparingsfasen

**Baggrund**: I opsparingsfasen kan forsikringstager vælge *depotsikring*: ved død udbetales
den fulde depotværdi til efterladte. Modelmæssigt sættes dødsfaldsdækningen lig depotværdien,
så risikosummen `S = b^{01}(t) + V^{DOED}(t) − V^{I_LIVE}(t) = 0`. Konsekvensen er at der
ingen dødelighedsgevinster opstår — de forventede livrente-ydelser bliver tilsvarende lavere,
fordi der betales en risikopræmie `µ(t)×S = 0`... nej: risikopræmien forsvinder *ikke*, men
dødelighedsgevinsten modsvares præcis af risikopræmien og nettobidraget til reserven er nul.

Uden depotsikring er `b^{01}(t) = 0` og `V^{DOED}(t) = 0`, så `S = −V^{I_LIVE}(t) < 0` —
dødelighedsgevinster tilfalde de overlevende og øger den forventede livrente-ydelse.

Implementeres som `doedsydelses_type: DoedsydelsesType` på `Policy` med enum-værdier
`DEPOT` (depotsikring, risikosum = 0) og `INGEN` (ingen dødelsydelse, risikosum = −V).

**Afhængigheder**: Ingen — kan starte parallelt med A.

**Matematisk detalje**:
- `DEPOT`: `b^{01}(t) = depot(t)`, `V^{DOED}(t) = 0` → `S = depot(t) − V^{I_LIVE}(t) ≈ 0`
  (depot ≈ reserve i et rent unit-link produkt uden garantier)
- `INGEN`: `b^{01}(t) = 0`, `V^{DOED}(t) = 0` → `S = −V^{I_LIVE}(t)`
- Kun gyldigt i opsparingsfasen (`er_under_udbetaling = False`)

**Opgaver**:
- [ ] Tilføj `DoedsydelsesType`-enum i `verd/policy.py`:
  ```python
  class DoedsydelsesType(enum.Enum):
      DEPOT = "depot"        # depotværdi udbetales ved død — risikosum ≈ 0
      INGEN = "ingen"        # ingen ydelse ved død — dødelighedsgevinster til overlevende
  ```
- [ ] Tilføj `doedsydelses_type: DoedsydelsesType = DoedsydelsesType.INGEN` på `Policy`
- [ ] Implementér `beregn_risikosum(policy, t) → float` i `verd/thiele.py` (eller `verd/udbetaling.py`):
  - `DEPOT`: returner `0.0` (risikosummen er nul — depot og hensættelse er ens)
  - `INGEN`: returner `−policy.depotvardi` (hensættelsen frigives ved død)
  - Kast `ValueError` hvis `doedsydelses_type=DEPOT` og `er_under_udbetaling=True`
    (depotsikring er kun defineret i opsparingsfasen)
- [ ] Brug `beregn_risikosum` i Thiele-trinnet i `verd/thiele.py`
- [ ] Eksporter `DoedsydelsesType` fra `verd/__init__.py`
- [ ] Tilføj `examples/eksempel_depotsikring.py`:
  - Sammenlign to policer: med og uden depotsikring
  - Vis at forventet total udbetaling er lavere med depotsikring (ingen dødelighedsgevinster)
  - Vis at reserve-forløbet er ens (unit-link, ingen garantier)
- [ ] Unit-tests i `tests/test_depotsikring.py`:
  - [ ] `DEPOT`: risikosummen = 0 for alle tidsstep i opsparingsfasen
  - [ ] `INGEN`: risikosummen = `−V(t)` for alle tidsstep i opsparingsfasen
  - [ ] `DEPOT` + `er_under_udbetaling=True`: `ValueError` kastes
  - [ ] Med depotsikring: forventet total udbetaling ≤ uden depotsikring (tolerance 1e-2)

**Berørte filer**: `verd/policy.py`, `verd/thiele.py`, `verd/__init__.py`

---

### D — Ratepension til efterladte ved død efter pensionering

**Baggrund**: Ved pensionstagets død *efter* pensionsstart fortsætter ratepensionsudbetalingerne
til efterladte i den resterende rateperiode (garanteret ydelse). Det modelleres via
risikosummen i Thiele-leddet for I_LIVE → DOED: `R_ratepension = PV(resterende rater)`.
Modsætningsvis er den ophørende livrente (B) *uden* efterladtedækning.

**Afhængigheder**: Bygger på risikosum-mønstret etableret i **B**.

**Opgaver**:
- [ ] Tilføj `ratepension_til_efterladte: bool = True` på `Policy`
- [ ] Implementér `ratepension_efterladte_risikosum(policy, t, market) → RisikoSummer`
  i `verd/udbetaling.py`:
  - Aktiv kun når `er_under_udbetaling=True` og `t < t_pension + ratepensionsvarighed`
  - Beregn `PV = sikker_annuitet(resterende_aar, market, t, dt) × maanedlig_rate`
  - `R_ratepension = V_ratepension + PV` (depot + nutidsværdi af fremtidige garanterede rater)
  - `R_aldersopsparing = R_livrentedepot = 0`
  - Ellers (uden for rateperioden eller opsparingsfase): alle nul
- [ ] Kombinér med `ophørende_livrente_risikosum` (B) til én samlet `risikosum_funktion`
  der håndterer begge produkter
- [ ] Tilføj `examples/eksempel_efterladte.py`:
  - Vis cashflows til pensionstageren (in-life) + forventede efterladteydelser
  - Verificer: sum af in-life ydelser + E[efterladteydelser] ≈ deterministisk annuitetsværdi
- [ ] Unit-tests i `tests/test_efterladte.py`:
  - [ ] `R_ratepension > 0` når policen er i udbetalingsfase og inden rateperiodens udløb
  - [ ] `R_ratepension = 0` i opsparingsfasen
  - [ ] `R_ratepension = 0` efter rateperiodens udløb
  - [ ] Forventet total udbetalt (in-life + efterladte) ≈ `V_ratepension(t_pension)` (tolerance 1e-2)

**Berørte filer**: `verd/policy.py`, `verd/udbetaling.py`, `verd/thiele.py`, `verd/fremregning.py`

---

### D — Stokastiske afkast under Q-mål

**Baggrund**: Q-målet (det risikoneutrale sandsynlighedsmål) bruges til
markedsværdi-hensættelser (IFRS 17, Solvens II Best Estimate). Under Q er det forventede
afkast lig den risikofri rente `r_f` uanset aktivklasse; volatilitet modelleres eksplicit.
Monte Carlo-simulering over Q-stier giver fordelingen af fremtidige cashflows.

**Afhængigheder**: Bygger på eksisterende `FinancialMarket` ABC — ellers uafhængig.

**Opgaver**:
- [ ] Udvid `verd/financial_market.py` med metode `simuler_sti(t0, T, dt, seed) → np.ndarray`
  på `FinancialMarket` ABC (optional: kast `NotImplementedError` i base)
- [ ] Implementér `verd/black_scholes_market.py` — `BlackScholesMarked(FinancialMarket)`:
  ```python
  class BlackScholesMarked(FinancialMarket):
      def __init__(self, r_f: float, sigma: float, enhedspris_0: float): ...
      # Lognormal diskretisering under Q:
      # P(t+dt) = P(t) · exp((r_f − σ²/2)·dt + σ·√dt·Z),  Z ~ N(0,1)
      def enhedspris(self, t: float) -> float: ...          # deterministisk E[P(t)] under Q
      def simuler_sti(self, t0, T, dt, seed) -> np.ndarray: ...
      def simuler_stier(self, t0, T, dt, n_stier, seed) -> np.ndarray: ...  # shape (n_stier, N)
  ```
- [ ] Implementér `verd/monte_carlo.py` — `monte_carlo_fremregn(distribution, n_stier, market, ...)`:
  - Simulér `n_stier` enhedsprissimulationer
  - Kør `fremregn()` per scenarie (eller brug vectoriseret tilgang)
  - Returnér `MonteCarloResultat` med forventet cashflow + 5%/95%-percentiler per tidsstep
- [ ] Tilføj `examples/eksempel_stokastisk.py`:
  - Plot fanout af 100 enhedsprissimulationer under Q
  - Vis forventet cashflow med konfidensinterval
- [ ] Unit-tests i `tests/test_black_scholes.py`:
  - [ ] `E[P(T)]` over 10.000 stier ≈ `P(0)·exp(r_f·T)` (martingale-check, tolerance 1e-2)
  - [ ] `Var[log P(T)]` ≈ `σ²·T` (tolerance 1e-2)
  - [ ] Seed giver reproducerbare stier
  - [ ] `n_stier=1` returnerer shape `(1, N_skridt)`

**Berørte filer**: `verd/financial_market.py`, ny `verd/black_scholes_market.py`,
ny `verd/monte_carlo.py`, `verd/__init__.py`

---

### E — Portefølje: til- og afgang af policer

**Baggrund**: I en portefølje tilkommer nye policer (nytegning) og eksisterende policer
afgår (død, genkøb, fripolice, pensionering). Hvert event medfører tilhørende omkostninger
(tegningsgebyr, genkøbsomkostning, fripoliceomkostning) og ændrer porteføljens samlede
cashflow.

**Afhængigheder**: Kræver at Fase 2–3 er afsluttede (`fremregn()` og reserveberegning klar).
Fungerer med enhver kombination af `BiometricModel` og produktkonfiguration — A, B og C er ikke nødvendige forudsætninger.

**Opgaver**:
- [ ] Definér `AfgangAarsag(enum)` i `verd/portefolje.py`:
  `DOED | GENKOBT | FRIPOLICE | PENSIONERET | UDLOEBET`
- [ ] Definér `PoliceHaendelse(dataclass)`:
  - `tidspunkt: float`, `police_id: str`
  - `type: Literal["tilgang", "afgang"]`
  - `aarsag: AfgangAarsag | None`
  - `omkostning_dkk: float`
- [ ] Definér `Portefolje(dataclass)`:
  - `policer: dict[str, PolicyDistribution]` — aktive policer
  - `haendelser: list[PoliceHaendelse]` — komplet hændelseshistorik
- [ ] Implementér `tilfoej_police(portefolje, police_id, police, t, tegningsomkostning_dkk) → Portefolje`
- [ ] Implementér `afmeld_police(portefolje, police_id, t, aarsag, omkostning_dkk) → Portefolje`
- [ ] Implementér `fremregn_portefolje(portefolje, t_start, t_slut, dt, market, ...) → PortefoeljeFremregning`:
  - Kør `fremregn()` per aktiv police i perioden
  - Aggregér `indbetaling_dkk`, `udbetaling_dkk`, `omkostning_dkk` på tværs af policer per tidsstep
  - Inkludér hændelsesomkostninger i `omkostning_dkk`
  - Returnér `PortefoeljeFremregning` med aggregerede tidsserier + hændelseslog
- [ ] Definér `PortefoeljeFremregning(dataclass)`:
  - `skridt: list[dict]` — aggregerede cashflows per tidsstep
  - `haendelser: list[PoliceHaendelse]` — alle hændelser i perioden
  - `to_dataframe() → pd.DataFrame`
- [ ] Tilføj `examples/eksempel_portefolje.py`:
  - 3 policer med forskellig alder og depot
  - Én afgår ved genkøb efter 2 år (med genkøbsomkostning)
  - En ny police tilkommer efter 1 år
  - Print aggregeret cashflow-tabel over 5 år
- [ ] Unit-tests i `tests/test_portefolje.py`:
  - [ ] Aggregeret reserve = sum af individuelle reserver (linearitet)
  - [ ] Hændelsesomkostninger dukker op korrekt i `omkostning_dkk` det rette tidsstep
  - [ ] Afgået police bidrager ikke til cashflows efter afgangstidspunktet
  - [ ] `Portefolje` med én police = enkelt `fremregn()` (konsistenscheck)

**Berørte filer**: ny `verd/portefolje.py`, `verd/omkostning.py`, `verd/__init__.py`

---

### F — Investeringsfonde og livscyklusprodukter

**Baggrund**: Et markedsrenteprodukt investeres typisk i en portefølje af fonde med
forskellige risikoprofiler. Kunden vælger et livscyklusprodukt — én af 4 profiler
(fx Høj, Mellem-høj, Mellem-lav, Lav) — der bestemmer, hvordan opsparingen fordeles
mellem fondene, og hvordan fordelingen nedtrappes automatisk jo tættere kunden er på
pension.

**Teoretisk begrundelse for risikonedskalering**:
Under CRRA-nytte (power utility) er den optimale andel investeret i risikofyldte aktiver
proportional med forholdet mellem total formue og finansiel formue:

```
w_risiko(t) = γ · (V_finansiel(t) + HK(t)) / V_finansiel(t)
```

hvor:
- `γ` = Merton-andelen (konstant under CRRA, afhænger af risikoaversion og Sharpe-ratio)
- `HK(t)` = humankapital = diskonteret nutidsværdi af fremtidig løn ved tidspunkt `t`
- `V_finansiel(t)` = depotværdi

Da humankapitalen falder med alderen, vil `w_risiko(t)` falde over tid — selv om `γ` er konstant.

**Afhængigheder**: Bygger på **D** (`BlackScholesMarked`) for stokastisk modellering
af hvert fonds afkast.

**Opgaver**:
- [ ] Definér `InvesteringsFond(dataclass)` i `verd/investeringsfond.py`:
  ```python
  @dataclass
  class InvesteringsFond:
      navn: str
      forventet_afkast: float   # årlig, P-mål
      volatilitet: float        # årlig standardafvigelse
  ```
- [ ] Definér `FondsUnivers(dataclass)` i `verd/investeringsfond.py`:
  - `fonde: list[InvesteringsFond]` — 3–5 fonde
  - `korrelationsmatrix: np.ndarray` — (n×n)
  - Valideringsmetode: kontrollér at matrix er positiv semidefinit og symmetrisk
- [ ] Implementér `LivescyklusProfil(dataclass)` i `verd/livescyklus.py`:
  ```python
  @dataclass
  class LivescyklusProfil:
      navn: str                        # fx "Høj", "Mellem-høj", "Mellem-lav", "Lav"
      gamma: float                     # Merton-andel (CRRA risikoaversion)
      glide_path: Callable[[float, float], dict[str, float]]
      # glide_path(alder, aar_til_pension) → {fond_navn: vægt}
  ```
- [ ] Implementér 4 standardprofiler med parametriserede glide-paths
- [ ] Implementér `humankapital(alder, pensionsalder, loen, diskonteringsrente) → float`
  i `verd/humankapital.py`:
  - `HK(t) = loen · ä_{pensionsalder - alder}` (sikker annuitet over resterende arbejdsliv)
- [ ] Implementér `MultiFondsMarked(FinancialMarket)` i `verd/multi_fonds_marked.py`:
  - Indeholder `FondsUnivers` + `LivescyklusProfil`
  - Beregner porteføljeafkast som vægtet gennemsnit per tidsstep
  - Implementerer `simuler_sti` via Cholesky-dekomponeret korrelationsmatrix
- [ ] Tilføj `examples/eksempel_livescyklus.py`:
  - Plot fondsvægtning over tid for alle 4 profiler (alder 30 → 70)
  - Plot forventet depotudvikling med 10%/90%-konfidensinterval for hver profil
- [ ] Unit-tests i `tests/test_livescyklus.py`:
  - [ ] Fondsværgte summerer til 1.0 for alle aldre og alle 4 profiler
  - [ ] Nedtrapning er monoton: aktieandel faldende jo tættere på pension
  - [ ] `humankapital(pensionsalder, pensionsalder, ...) == 0.0`
  - [ ] Porteføljeafkast ≈ vægtet gennemsnit af fondsafkast (ved 0-korrelation og deterministisk)
  - [ ] `MultiFondsMarked` med én fond og 0 volatilitet = `DeterministicMarket`

**Berørte filer**: ny `verd/investeringsfond.py`, ny `verd/livescyklus.py`,
ny `verd/humankapital.py`, ny `verd/multi_fonds_marked.py`, `verd/__init__.py`

---

### G — Præmieflow: risikodækninger og allokeringsalgoritme

**Baggrund**: Bruttoindbetalingen gennemløber to transformationer, inden den rammer
opsparingsdepotterne:

```
π_brutto(t)
  − risikopraemie(t)          ← finansierer dødsfald/TAE/SUL-dækninger
  = π_netto(t)
      → ratepension            ← op til skattemæssig beløbsgrænse
      → aldersopsparing        ← op til skattemæssig beløbsgrænse
      → livrente               ← resterende (ingen beløbsgrænse)
```

Disse to led hænger uløseligt sammen: risikodelen bestemmer størrelsen af `π_netto`,
og allokeringsdelen bestemmer hvordan `π_netto` fordeles. Begge implementeres i ét
præmielag (`verd/praemieflow.py` + `verd/indbetaling.py`).

**Risikodækninger** finansierer rene risikoprodukter:
- **Dødsfald**: engangsudbetaling til efterladte ved død
- **TAE** (Tab af Erhvervsevne): løbende udbetaling ved varig invaliditet
- **SUL** (Sum ved Ulykkestilfælde/Livstruende sygdom): engangsudbetaling ved kritisk sygdom

Hvis `π_netto < 0` (risikopræmie overstiger bruttopræmien) trækkes differencen fra
depottet (aldersopsparing først).

**Allokeringsalgoritme** — beløbsgrænser pr. 2026 (kilde: skat.dk):
- Ratepension: **68.700 kr./år**
- Aldersopsparing (>7 år til folkepensionsalder): **9.900 kr./år**
- Aldersopsparing (≤7 år til folkepensionsalder): **64.200 kr./år**
- Livrente: **ingen beløbsgrænse**

Satserne gemmes i `verd/data/offentlige_satser.csv` og kan opdateres hvert år
uden kodeændringer.

**Afhængigheder**: Ingen — kan starte parallelt med alle andre.

**Datasæt**: `verd/data/offentlige_satser.csv`

```
produkt,aar,beloebsgraense_dkk,betingelse
aldersopsparing,2025,9400,normal
aldersopsparing,2025,61200,nær_pension
ratepension,2025,65500,
aldersopsparing,2026,9900,normal
aldersopsparing,2026,64200,nær_pension
ratepension,2026,68700,
livrente,2026,,
```

Kolonner:
- `produkt`: `aldersopsparing` | `ratepension` | `livrente`
- `aar`: kalenderår satsen gælder
- `beloebsgraense_dkk`: max indbetaling pr. år (blank = ingen grænse)
- `betingelse`: `normal` (>7 år til folkepensionsalder), `nær_pension` (≤7 år), blank = gælder altid

**Opgaver**:

*Risikodækninger — `verd/risiko.py`*:
- [ ] Tilføj `RisikoDaekning(dataclass)`:
  ```python
  @dataclass
  class RisikoDaekning:
      navn: str                        # fx "Dødsfald", "TAE", "SUL"
      aarlig_praemie_dkk: float
  ```
- [ ] Tilføj `RisikoBundle(dataclass)`:
  - `daekninger: list[RisikoDaekning]`
  - Property `aarlig_praemie_dkk → float`: sum af alle dækningers præmier
  - Property `maanedlig_praemie_dkk → float`: `aarlig_praemie_dkk / 12`
- [ ] Definer standardbundle som konstant:
  ```python
  STANDARD_RISIKO_BUNDLE = RisikoBundle(daekninger=[
      RisikoDaekning(navn="Dødsfald", aarlig_praemie_dkk=500.0),
      RisikoDaekning(navn="TAE",      aarlig_praemie_dkk=700.0),
      RisikoDaekning(navn="SUL",      aarlig_praemie_dkk=300.0),
  ])
  # Samlet: 1500 kr/år = 125 kr/md
  ```
- [ ] Tilføj `risiko_bundle: RisikoBundle | None = None` på `Policy`

*Beløbsgrænser — `verd/offentlige_satser.py`*:
- [ ] Opret `verd/data/offentlige_satser.csv` med satserne for 2025 og 2026
- [ ] Implementér `indlæs_offentlige_satser(filsti: Path) → dict`
  - Returnér `{(produkt, aar, betingelse): beloebsgraense_dkk | None}`
  - Kast `ValueError` ved ukendt `produkt`-værdi eller manglende påkrævede kolonner
- [ ] Implementér `BeloebsgraenserOpslag(dataclass)`:
  - `aar: int`, `aar_til_folkepension: float`
  - `aldersopsparing_max: float` — `nær_pension`-grænse hvis ≤7 år til pension, ellers `normal`
  - `ratepension_max: float`
  - `livrente_max: float | None` — `None` = ingen grænse

*Præmieflow — `verd/praemieflow.py`*:
- [ ] Implementér `PraemieFlow(dataclass)`:
  ```python
  @dataclass
  class PraemieFlow:
      risiko_bundle: RisikoBundle | None
      beloebsgraenser: BeloebsgraenserOpslag | None
      ratepension_andel: float    # ønsket andel af π_netto til ratepension (0–1)
      aldersopsparing_andel: float  # ønsket andel til aldersopsparing (0–1)
      # livrente_andel = 1 - ratepension_andel - aldersopsparing_andel
  ```
- [ ] Implementér `beregn(bruttoindbetalng_aar: float) → PraemieFlowResultat`:
  1. Beregn `π_netto = π_brutto − risiko_bundle.aarlig_praemie_dkk` (0 hvis ingen bundle)
  2. Allokér `π_netto` proportionalt efter andele, beskær ved beløbsgrænser, rest → livrente
  3. Returnér `PraemieFlowResultat(risikopraemie_dkk, ratepension_dkk, aldersopsparing_dkk, livrente_dkk)`
- [ ] Håndtér `π_netto < 0`: returner negativt beløb i `aldersopsparing_dkk` (trækkes fra depot)
- [ ] Integrér med `simpel_opsparings_cashflow()` i `verd/fremregning.py`:
  - Acceptér valgfrit `praemieflow: PraemieFlow | None = None`
  - `None` → nuværende proportionsbaserede fordeling (bagudkompatibelt)

*Eksempel og tests*:
- [ ] Tilføj `examples/eksempel_praemieflow.py`:
  - 35-årig (>7 år til pension), 100.000 kr/år brutto — vis risikofradrag + allokering
  - 60-årig (≤7 år til pension) — vis større aldersopsparingsgrænse
  - Vis depotudvikling med vs. uden risikodækninger over 10 år
- [ ] Unit-tests i `tests/test_praemieflow.py`:
  - [ ] `STANDARD_RISIKO_BUNDLE.aarlig_praemie_dkk == 1500.0`
  - [ ] `STANDARD_RISIKO_BUNDLE.maanedlig_praemie_dkk == 125.0`
  - [ ] `risikopraemie + ratepension + aldersopsparing + livrente == π_brutto`
  - [ ] Overflow: `beregn(200.000)` → `ratepension_dkk == 68.700` + rest til livrente
  - [ ] `nær_pension` (≤7 år): `aldersopsparing_max == 64.200`
  - [ ] `normal` (>7 år): `aldersopsparing_max == 9.900`
  - [ ] `π_netto < 0`: negativt beløb returneres korrekt i `aldersopsparing_dkk`
  - [ ] `indlæs_offentlige_satser()` parser 2026-satserne korrekt fra CSV
  - [ ] Depotværdi efter 1 år med risikopræmie ≈ depotværdi uden − 1.500 kr (før afkast)

**Berørte filer**: ny `verd/risiko.py`, ny `verd/offentlige_satser.py`, ny `verd/praemieflow.py`,
ny `verd/data/offentlige_satser.csv`, `verd/policy.py`, `verd/fremregning.py`, `verd/__init__.py`

---

### H — Stresstesting af antagelser

**Baggrund**: Aktuar ønsker at vurdere følsomheden af cashflows og reserver
over for ændringer i centrale antagelser — typisk dødelighedsintensiteten (`µ(x)`),
afkastraten (`r`), indbetalingsprocenten eller omkostningssatser.

**Afhængigheder**: Bygger på `fremregn()` (Fase 2) og evt. `fremregn_portefolje()` (E).

**Modellering**:
```python
@dataclass
class SkaleretBiometricModel(BiometricModel):
    base_model: BiometricModel
    skaleringsfaktor: float   # fx 1.20 = +20% dødelighedsintensitet

    def mortality_intensity(self, alder: float) -> float:
        return self.skaleringsfaktor * self.base_model.mortality_intensity(alder)

@dataclass
class Scenarie:
    navn: str
    biometric_model: BiometricModel
    financial_market: FinancialMarket
    omkostningssats_overrides: dict[str, float] | None = None
```

**Opgaver**:
- [ ] Implementér `SkaleretBiometricModel` i `verd/stresstest.py`
- [ ] Implementér `Scenarie(dataclass)` i `verd/stresstest.py`
- [ ] Implementér `sammenlign_scenarier(policer, scenarier, t_start, t_slut, dt) → dict[str, pd.DataFrame]`
  - Kør `fremregn()` per scenarie
  - Returnér dict `{scenarie_navn: cashflow_dataframe}`
- [ ] Tilføj `examples/eksempel_stresstest.py`:
  - 3–5 policer med varierende alder og depot
  - Tre scenarier: `Base`, `DødelighedStress` (`1.2 · µ(x)`), `OmkostningsStress`
  - Print aggregeret cashflow-tabel side om side
- [ ] Unit-tests i `tests/test_stresstest.py`:
  - [ ] `SkaleretBiometricModel(model, 1.0)` giver identiske cashflows som `model`
  - [ ] `SkaleretBiometricModel(model, 1.2)` giver højere forventet dødsudbetaling
  - [ ] Omkostningsstress: forhøjet sats øger samlede omkostninger monotont
  - [ ] `sammenlign_scenarier` returnerer én nøgle per scenarie
  - [ ] Alle DataFrames har identiske tidskolonner (samme tidsakse)

**Berørte filer**: ny `verd/stresstest.py`, `verd/__init__.py`

---

## Bug

*(ingen kendte)*

---

## Refactor

*(ingen planlagte)*

---

## Test

### ~~v1.0 — Fase 1b: Unit tests for eksisterende klasser~~ ✓ FÆRDIG

Parametre for alle tests: `alpha=0.0005`, `beta=0.00004`, `sigma=0.09`, `r=0.05`, `P₀=100.0`

**Referenceberegninger (håndberegnede facit)**

| Beregning | Formel | Facit |
|---|---|---|
| µ(40) | 0.0005 + 0.00004·exp(0.09·40) | **0.00196393 år⁻¹** |
| µ(50) | 0.0005 + 0.00004·exp(0.09·50) | **0.00410068 år⁻¹** |
| µ(60) | 0.0005 + 0.00004·exp(0.09·60) | **0.00935625 år⁻¹** |
| p(40, 1/12) | exp(−0.00196393/12) | **0.99983637** |
| q(40, 1/12) | 1 − p | **0.00016363** |
| enhedspris(1) | 100·exp(0.05) | **105.12710964 DKK/enh.** |
| depotværdi | 2500 enh. × 100 DKK/enh. | **250.000,00 DKK** |
| DKK→enh. | 10.000 DKK / 100 DKK/enh. | **100,0000 enh.** |
| Månedlig præmie | 600.000 × 0,15 / 12 | **7.500,00 DKK/md.** |
| Præmie i enh. (t=0) | 7.500 / 100 | **75,0000 enh./md.** |

- [x] `tests/test_policy_state.py` — 6 tests, alle grønne
  - [x] `PolicyState` har præcis `I_LIVE` og `DOED`
  - [x] Enum-værdier er strings (`"I_LIVE"`, `"DOED"`)

- [x] `tests/test_policy.py` — 13 tests, alle grønne
  - [x] `total_enheder()` returnerer sum af de tre depoter
  - [x] `depotvaerdi_dkk(100.0)` = `total_enheder()` × 100
  - [x] `depotvaerdi_dkk` er ikke et gemt felt (verificer med `dataclasses.fields()`)
  - [x] `tilstand` defaulter til `PolicyState.I_LIVE`
  - [x] `depotvaerdi_dkk(0.0)` = 0.0 (zero-enhedspris edge case)

- [x] `tests/test_policy_distribution.py` — 6 tests, alle grønne
  - [x] `initial_distribution(police)` returnerer liste med præcis ét element
  - [x] Sandsynlighed i initial distribution = 1.0
  - [x] Sandsynligheder summer til 1.0

- [x] `tests/test_gompertz_makeham.py` — 16 tests, alle grønne
  - [x] `mortality_intensity(40)` matcher facit 0.00196393 (tolerance 1e-8)
  - [x] `mortality_intensity(50)` matcher facit 0.00410068 (tolerance 1e-8)
  - [x] `mortality_intensity(60)` matcher facit 0.00935625 (tolerance 1e-8)
  - [x] `mortality_intensity(x) >= 0` for x ∈ {0, 20, 40, 60, 80, 100}
  - [x] `mortality_intensity` er monotont stigende (intensitet ved 50 > intensitet ved 40)
  - [x] `survival_probability(40, 1/12)` matcher facit 0.99983637 (tolerance 1e-8)
  - [x] `death_probability(40, 1/12)` matcher facit 0.00016363 (tolerance 1e-8)
  - [x] `survival_probability + death_probability = 1.0` præcist

- [x] `tests/test_deterministic_market.py` — 18 tests, alle grønne
  - [x] `enhedspris(0)` = `enhedspris_0` (100.0)
  - [x] `enhedspris(1)` matcher facit 105.12710964 (tolerance 1e-6)
  - [x] `enhedspris(t) > enhedspris(0)` for t > 0 og r > 0
  - [x] Round-trip: `dkk_til_enheder(X, t) × enhedspris(t)` = X (tolerance 1e-10)
  - [x] Round-trip: `enheder_til_dkk(dkk_til_enheder(X, t), t)` = X (tolerance 1e-10)
  - [x] `dkk_til_enheder(10000, 0)` = 100.0 (matcher facit)

---

### v1.0 — Fase 2–3: Cashflow- og valideringstests

- [ ] `tests/test_cashflow.py`
  - [ ] Månedlig præmie = 600.000 × 0,15 / 12 = 7.500,00 DKK (matcher facit)
  - [ ] Præmie i enheder (t=0, P₀=100) = 75,0 enh. (matcher facit)
  - [ ] `p_alive` starter på 1.0 og er strengt aftagende
  - [ ] `p_alive` er altid ∈ [0, 1]
  - [ ] Sandsynlighedsvægtede cashflows ≤ uvægtede cashflows
  - [ ] Cashflow-liste er ikke tom
  - [ ] Første skridt: `t ≈ 0`, `p_alive = 1.0`
  - [ ] Verificer første 3 måneders `indbetaling_enheder` mod håndberegnet facit
  - [ ] Ved opsparingsfase: `udbetaling_dkk = 0` på alle rækker

- [ ] `tests/test_validering.py`
  - [ ] `check_sandsynligheder` kaster `ValueError` hvis sum ≠ 1.0
  - [ ] `check_p_alive_monoton` kaster `ValueError` ved stigende p_alive
  - [ ] CSV-eksport producerer velformet fil med korrekte kolonnenavne
  - [ ] End-to-end: `standard_police` → cashflows → alle checks → ingen undtagelser

---

### v1.0 — Fase 4: Facittests og edge cases

**Håndberegnet faciteksempel**:
3-årig ren aldersopsparing — starttilstand: 1.000 enh. × 100 DKK/enh. = 100.000 DKK —
parametre: r=0.05, alpha=0.0005, beta=0.00004, sigma=0.09, alder=40, dt=1/12

- [ ] `tests/test_facit.py`:
  - [ ] µ(40) = 0.00196393 (tolerance 1e-8)
  - [ ] µ(50) = 0.00410068 (tolerance 1e-8)
  - [ ] µ(60) = 0.00935625 (tolerance 1e-8)
  - [ ] p(40, 1/12) = 0.99983637 (tolerance 1e-8)
  - [ ] enhedspris(1) = 105.12710964 (tolerance 1e-6)
  - [ ] Månedlig præmie for standardpolicen = 7.500,00 DKK (eksakt)
  - [ ] `V(0)` for nulcashflow-policen = `depotvaerdi_dkk` (tolerance 1e-4)
  - [ ] Første måneds `indbetaling_enheder` = håndberegnet facit (tolerance 1e-8)
  - [ ] Første måneds `risikopraemie_enheder` = håndberegnet facit (tolerance 1e-8)

- [ ] Edge cases:
  - [ ] Police med alle depoter = 0.0 → `depotvaerdi_dkk` = 0.0
  - [ ] Police med `er_under_udbetaling = True` fra starten → ingen indbetalinger
  - [ ] `ratepensionsvarighed = 0` → ingen ratepensionsydelser
  - [ ] Meget høj dødelighedsintensitet (alpha=1.0) → `p_alive` falder hurtigt, fremregning stopper tidligt
  - [ ] `r = 0.0` → `enhedspris(t) = enhedspris_0` for alle t (flad kurve)

---

## Chore

### ~~v1.0 — Test-infrastruktur~~ ✓ FÆRDIG

- [x] Tilføj `pytest` til `pyproject.toml` under `[project.optional-dependencies] dev`
- [x] Opret `tests/` mappe med `tests/__init__.py`
- [ ] Opret `tests/conftest.py` med delte fixtures:
  - `standard_biometri` — `GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)`
  - `standard_marked` — `DeterministicMarket(r=0.05, enhedspris_0=100.0)`
  - `standard_police` — aldersopsparing med loen=600.000, indbetalingsprocent=0.15

### v1.0 — Dokumentation

- [ ] Opret `docs/referenceberegninger.md` med facittabel og mellemregninger
- [ ] Opret `docs/facit_eksempel.md` — komplet håndberegnet eksempel:
  - 3-årig ren aldersopsparing
  - Alle mellemresultater til 8 decimaler

### v1.0 — CI

- [ ] Opret `.github/workflows/test.yml` der kører `pytest` på push til `main`
