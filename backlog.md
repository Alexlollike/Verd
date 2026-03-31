# Backlog — Verd Aktuarbibliotek

Planlagte features til v1.1+. Rækkefølgen er prioriteret efter afhængigheder.
Afslut v1.0 (Fase 1–5 i `todo.md`) inden disse påbegyndes.

Brug `[x]` når en opgave er færdig.

---

## Afhængighedsgraf

```
Todo A: Finanstilsynets dødelighedsmodel  ─┐
Todo B: Ophørende livrente                ─┼─► Todo E: Portefølje (til- og afgang)
Todo C: Ratepension til efterladte        ─┘
             ↑
    bygger på B (risikosum-mønster)

Todo D: Stokastiske afkast (Q-mål)        ─► Todo F: Investeringsfonde & livscyklus
             (uafhængig af A–C, kan parallelliseres)

Todo G: Risikopræmie (dødsfald, TAE, SUL) — uafhængig, kan starte nu
```

Anbefalet rækkefølge: **A → B → C → D → E**, **D → F**, **G** (parallel)

---

## Todo A — Finanstilsynets dødelighedsmodel

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

## Todo B — Ophørende livrente

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

## Todo C — Ratepension til efterladte ved død efter pensionering

**Baggrund**: Ved pensionstagets død *efter* pensionsstart fortsætter ratepensionsudbetalingerne
til efterladte i den resterende rateperiode (garanteret ydelse). Det modelleres via
risikosummen i Thiele-leddet for I_LIVE → DOED: `R_ratepension = PV(resterende rater)`.
Modsætningsvis er den ophørende livrente (Todo B) *uden* efterladtedækning.

**Afhængigheder**: Bygger på risikosum-mønstret etableret i **Todo B**.

**Opgaver**:
- [ ] Tilføj `ratepension_til_efterladte: bool = True` på `Policy`
- [ ] Implementér `ratepension_efterladte_risikosum(policy, t, market) → RisikoSummer`
  i `verd/udbetaling.py`:
  - Aktiv kun når `er_under_udbetaling=True` og `t < t_pension + ratepensionsvarighed`
  - Beregn `PV = sikker_annuitet(resterende_aar, market, t, dt) × maanedlig_rate`
  - `R_ratepension = V_ratepension + PV` (depot + nutidsværdi af fremtidige garanterede rater)
  - `R_aldersopsparing = R_livrentedepot = 0`
  - Ellers (uden for rateperioden eller opsparingsfase): alle nul
- [ ] Kombinér med `ophørende_livrente_risikosum` (Todo B) til én samlet `risikosum_funktion`
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

## Todo D — Stokastiske afkast under Q-mål

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

## Todo E — Portefølje: til- og afgang af policer

**Baggrund**: I en portefølje tilkommer nye policer (nytegning) og eksisterende policer
afgår (død, genkøb, fripolice, pensionering). Hvert event medfører tilhørende omkostninger
(tegningsgebyr, genkøbsomkostning, fripoliceomkostning) og ændrer porteføljens samlede
cashflow. Dette er et spring fra enkeltpoliceniveau til portføljeniveau — kræver fuld
modellering af enkeltpolicen (Todo A+B+C) inden implementering.

**Afhængigheder**: Kræver **Todo A** (korrekt dødelighedsmodel) + **Todo B** (livrente-type)
+ **Todo C** (efterladtedækning) — dvs. fuld enkeltpolicemodel på plads.

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
  - Inkludér hændelsesomkostninger (`tegnings-` og `afgangsomkostning`) i `omkostning_dkk`
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

## Todo F — Investeringsfonde og Livscyklusprodukter

**Baggrund**: Et markedsrenteprodukt investeres typisk i en portefølje af fonde med
forskellige risikoprofiler. Kunden vælger et livscyklusprodukt — én af 4 profiler
(fx Høj, Mellem-høj, Mellem-lav, Lav) — der bestemmer, hvordan opsparingen fordeles
mellem fondene, og hvordan fordelingen nedtrappes automatisk jo tættere kunden er på
pension (svarende til PFAs "indbygget nedtrapning af risiko i alle profiler").

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

Da humankapitalen falder med alderen (den resterende lønhorisont skrumper), vil
`w_risiko(t)` falde over tid — selv om `γ` er konstant. Dette giver den teoretiske
motivation for at alle 4 livscyklusprofiler nedtrapper eksponeringen mod risikofyldte
aktiver. Profilerne adskiller sig ved valget af `γ` (dvs. graden af risikovillighed).

**Afhængigheder**: Bygger på **Todo D** (`BlackScholesMarked`) for stokastisk modellering
af hvert fonds afkast. Flerfonds-udvidelsen af `FinancialMarket` etableres her.

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
  - `fonde: list[InvesteringsFond]` — 3–5 fonde (fx aktier høj, aktier lav, obligationer, kreditobligationer, pengemarked)
  - `korrelationsmatrix: np.ndarray` — (n×n) korrelationsmatrix mellem fondene
  - Valideringsmetode: kontrollér at matrix er positiv semidefinit og symmetrisk
- [ ] Implementér `LivescyklusProfil(dataclass)` i `verd/livescyklus.py`:
  ```python
  @dataclass
  class LivescyklusProfil:
      navn: str                        # fx "Høj", "Mellem-høj", "Mellem-lav", "Lav"
      gamma: float                     # Merton-andel (CRRA risikoaversion)
      glide_path: Callable[[float, float], dict[str, float]]
      # glide_path(alder, aar_til_pension) → {fond_navn: vægt}
      # Vægte summerer til 1.0
  ```
- [ ] Implementér 4 standardprofiler i `verd/livescyklus.py` med parametriserede glide-paths:
  - Nedtrapning aktiveres typisk 15–20 år før pension
  - Alle profiler ender i samme lav-risiko allokering ved pensionering
  - Profilerne adskiller sig i startallokering (styret af `γ`)
- [ ] Implementér `humankapital(alder, pensionsalder, loen, diskonteringsrente) → float`
  i `verd/humankapital.py`:
  - `HK(t) = loen · ä_{pensionsalder - alder}` (sikker annuitet over resterende arbejdsliv)
- [ ] Implementér `MultiFondsMarked(FinancialMarket)` i `verd/multi_fonds_marked.py`:
  - Indeholder `FondsUnivers` + `LivescyklusProfil`
  - Beregner porteføljeafkast som vægtet gennemsnit af fondsafkast per tidsstep
  - Implementerer `simuler_sti` via Cholesky-dekomponeret korrelationsmatrix
- [ ] Tilføj `examples/eksempel_livescyklus.py`:
  - Plot fondsvægtning over tid for alle 4 profiler (alder 30 → 70)
  - Plot forventet depotudvikling med 10%/90%-konfidensinterval for hver profil
- [ ] Unit-tests i `tests/test_livescyklus.py`:
  - [ ] Fondsværgte summerer til 1.0 for alle aldre og alle 4 profiler
  - [ ] Nedtrapning er monoton: aktieandel faldende jo tættere på pension
  - [ ] `humankapital(pensionsalder, pensionsalder, ...) == 0.0` (ingen resterende arbejdsliv)
  - [ ] Porteføljeafkast ≈ vægtet gennemsnit af fondsafkast (ved 0-korrelation og deterministisk)
  - [ ] `MultiFondsMarked` med én fond og 0 volatilitet = `DeterministicMarket`

**Berørte filer**: ny `verd/investeringsfond.py`, ny `verd/livescyklus.py`,
ny `verd/humankapital.py`, ny `verd/multi_fonds_marked.py`, `verd/__init__.py`

---

## Todo G — Risikopræmie for rene risikoprodukter (dødsfald, TAE, SUL)

**Baggrund**: Ud over opsparingen dækker en pensionspolice typisk rene risikoprodukter:
- **Dødsfald**: udbetaling til efterladte ved død
- **TAE** (Tab af Erhvervsevne): løbende udbetaling ved varig invaliditet
- **SUL** (Sum ved Ulykkestilfælde/Livstruende sygdom): engangsudbetaling ved kritisk sygdom

Disse dækninger finansieres via en **risikopræmie** der fratrækkes præmien, *inden*
den resterende nettopræmie fordeles på de tre opsparingsprodukter (aldersopsparing,
ratepensionsopsparing, livrentedepot). I første omgang modelleres risikopræmien som
et fast beløb uafhængigt af alder, køn og helbredstilstand.

**Afhængigheder**: Ingen — kan starte parallelt med alle andre todos.

**Modellering**:
Bruttoindbetalingen `π_brutto` splittes ved hvert tidsstep:

```
π_netto(t) = π_brutto(t) − risikopraemie_pr_maaned

risikopraemie_pr_maaned = risikopraemie_aarlig / 12
```

`π_netto` fordeles herefter på de tre depoter efter de sædvanlige allokeringsregler.
Hvis `π_netto < 0` (risikopræmie overstiger indbetalingen) trækkes differencen fra depottet.

**Opgaver**:
- [ ] Tilføj `RisikoDaekning(dataclass)` i `verd/risiko.py`:
  ```python
  @dataclass
  class RisikoDaekning:
      navn: str                        # fx "Dødsfald", "TAE", "SUL"
      aarlig_praemie_dkk: float        # fast beløb, default per dækning
  ```
- [ ] Tilføj `RisikoBundle(dataclass)` i `verd/risiko.py`:
  - `daekninger: list[RisikoDaekning]`
  - Property `aarlig_praemie_dkk → float`: sum af alle dækningers præmier
  - Property `maanedlig_praemie_dkk → float`: `aarlig_praemie_dkk / 12`
- [ ] Definer standardbundles som konstanter i `verd/risiko.py`:
  ```python
  STANDARD_RISIKO_BUNDLE = RisikoBundle(daekninger=[
      RisikoDaekning(navn="Dødsfald", aarlig_praemie_dkk=500.0),
      RisikoDaekning(navn="TAE",      aarlig_praemie_dkk=700.0),
      RisikoDaekning(navn="SUL",      aarlig_praemie_dkk=300.0),
  ])
  # Samlet: 1.500 kr/år = 125 kr/md
  ```
- [ ] Tilføj `risiko_bundle: RisikoBundle | None = None` på `Policy`
- [ ] Opdatér indbetalingslogikken i `verd/indbetaling.py`:
  - Træk `risiko_bundle.maanedlig_praemie_dkk` fra bruttoindbetalingen før allokering
  - Håndtér tilfældet `π_netto < 0`: træk fra depottet (aldersopsparing først)
- [ ] Tilføj `examples/eksempel_risiko.py`:
  - Vis effekten på depotudviklingen: med vs. uden risikodækninger (1.500 kr/år)
- [ ] Unit-tests i `tests/test_risiko.py`:
  - [ ] `STANDARD_RISIKO_BUNDLE.aarlig_praemie_dkk == 1500.0`
  - [ ] `STANDARD_RISIKO_BUNDLE.maanedlig_praemie_dkk == 125.0`
  - [ ] Depotværdi efter 1 år med risikopræmie = depotværdi uden − 1.500 kr (approx, før afkast)
  - [ ] `π_netto < 0`: differencen trækkes korrekt fra aldersopsparingen

**Berørte filer**: ny `verd/risiko.py`, `verd/policy.py`, `verd/indbetaling.py`, `verd/__init__.py`

---

## Todo H — Stresstesting af antagelser

**Baggrund**: I praksis ønsker aktuar at vurdere følsomheden af cashflows og reserver
over for ændringer i centrale antagelser — typisk dødelighedsintensiteten (`µ(x)`),
afkastraten (`r`), indbetalingsprocenten eller omkostningssatser. Et stresstest-framework
skal gøre det nemt at køre den samme fremregning under to eller flere antagelsessæt og
sammenligne resultaterne — fx det aggregerede cashflow for en bestand af policer under
henholdsvis "base"-dødelighedsintensitet og en "stresset" version (fx `µ_stress(x) = 1.2 · µ(x)`),
eller med forhøjede administrationsomkostninger.

**Afhængigheder**: Bygger på `fremregn()` (Fase 2) og evt. `fremregn_portefolje()` (Todo E).
Kan implementeres gradvist: simpel enkeltpolicestress før porteføljestress.

**Modellering**:
En "stresset" `BiometricModel` er blot en wrapper der skalerer intensiteten:

```python
@dataclass
class SkaleretBiometricModel(BiometricModel):
    base_model: BiometricModel
    skaleringsfaktor: float   # fx 1.20 = +20% dødelighedsintensitet

    def mortality_intensity(self, alder: float) -> float:
        return self.skaleringsfaktor * self.base_model.mortality_intensity(alder)
```

Et `Scenarie` samler alle de antagelser der varieres på tværs af kørsler:

```python
@dataclass
class Scenarie:
    navn: str
    biometric_model: BiometricModel
    financial_market: FinancialMarket
    omkostningssats_overrides: dict[str, float] | None = None
    # Nøgle: OmkostningssatsID, værdi: ny sats — øvrige satser er uændrede
```

**Opgaver**:
- [ ] Implementér `SkaleretBiometricModel` i `verd/stresstest.py`
- [ ] Implementér `Scenarie(dataclass)` i `verd/stresstest.py`
  - `navn: str`, `biometric_model: BiometricModel`, `financial_market: FinancialMarket`,
    `omkostningssats_overrides: dict[str, float] | None = None`
- [ ] Implementér `sammenlign_scenarier(policer, scenarier, t_start, t_slut, dt) → dict[str, pd.DataFrame]`
  - Kør `fremregn()` (eller `fremregn_portefolje()`) per scenarie
  - Returnér dict `{scenarie_navn: cashflow_dataframe}` — nemt at sende til plot
- [ ] Tilføj `examples/eksempel_stresstest.py`:
  - Definér en bestand af 3–5 policer med varierende alder og depot
  - Kør tre scenarier: `Base`, `DødelighedStress` (`1.2 · µ(x)`), `OmkostningsStress` (forhøjede adm.-satser)
  - Print aggregeret cashflow-tabel side om side
  - Plot forskel i forventet udbetaling og omkostninger over tid
- [ ] Unit-tests i `tests/test_stresstest.py`:
  - [ ] `SkaleretBiometricModel(model, 1.0)` giver identiske cashflows som `model`
  - [ ] `SkaleretBiometricModel(model, 1.2)` giver højere forventet dødsudbetaling end `model`
  - [ ] Omkostningsstress: forhøjet sats øger samlede omkostninger monotont
  - [ ] `sammenlign_scenarier` returnerer én nøgle per scenarie
  - [ ] Alle DataFrames har identiske tidskolonner (samme tidsakse)

**Berørte filer**: ny `verd/stresstest.py`, `verd/__init__.py`
