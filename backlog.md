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

Todo D: Stokastiske afkast (Q-mål)        — uafhængig, kan parallelliseres med A–C
```

Anbefalet rækkefølge: **A → B → C → D → E**

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
