# Verd — Teknisk Dokumentation

**Version:** Phase 2 (cashflow-fremregning)
**Formål:** Sandsynlighedsvægtet fremregning af enkeltpolice reserver og cashflows for rene unit-link pensionsprodukter.

---

## 1. Overblik

Biblioteket beregner, hvordan en pensionspolices depot og betalingsstrømme forventes at udvikle sig over tid, givet usikkerhed om forsikringstagerens overlevelse. Produkterne er rene **markedsrenteprodukter** (unit-link) uden garantier — forsikringstager bærer selv den finansielle risiko.

Tre produkttyper understøttes som separate depoter:

| Depot | Udbetaling |
|---|---|
| Aldersopsparing | Engangsudbetaling ved pensionering |
| Ratepension | Fast månedlig ydelse over *n* år |
| Livrente | Månedlig ydelse så længe forsikringstager lever |

---

## 2. Markov-modellen

Policens tilstand modelleres som en **to-tilstands Markov-kæde** i diskret tid:

```
I_LIVE  ──µ(x)──►  DOED
```

| Tilstand | Beskrivelse |
|---|---|
| `I_LIVE` | Forsikringstager er i live og policen er aktiv |
| `DOED` | Forsikringstager er død — absorberende tilstand |

**Tilstandsfordelingen** på tidspunkt $t$ angiver sandsynligheder:

$$p_0(t) = P(\text{I\_LIVE på tidspunkt } t), \quad p_1(t) = P(\text{DOED på tidspunkt } t)$$

med $p_0(t) + p_1(t) = 1$.

### Sandsynlighedsopdatering — Kolmogorov fremadligning

For hvert tidsstep $[t, t+\Delta t]$ opdateres sandsynlighederne via den diskretiserede Kolmogorov fremadligning:

$$p_0(t + \Delta t) = p_0(t) \cdot \bigl(1 - \mu(x+t) \cdot \Delta t\bigr)$$
$$p_1(t + \Delta t) = p_1(t) + p_0(t) \cdot \mu(x+t) \cdot \Delta t$$

hvor $\mu(x+t)$ er **dødelighedsintensiteten** (se afsnit 3) og $x$ er alder ved tegning.

Intuition: i hvert tidsstep "forlader" sandsynlighedsmassen $\mu \cdot p_0 \cdot \Delta t$ tilstanden I_LIVE og overføres til DOED.

---

## 3. Dødelighedsmodel — Gompertz-Makeham

Dødelighedsintensiteten (force of mortality) er:

$$\mu(x) = \alpha + \beta \cdot e^{\sigma x}$$

| Parameter | Fortolkning | Typisk dansk mand |
|---|---|---|
| $\alpha$ | Aldersuafhængig baggrundsdødelighed (ulykker, sygdom) | 0,0005 |
| $\beta$ | Gompertz præfaktor | 0,00004 |
| $\sigma$ | Aldringens vækstrate | 0,09 |

Enheden er år$^{-1}$: en 65-årig mand med disse parametre har $\mu(65) \approx 0{,}009$, svarende til ca. 0,9 % dødelighedsintensitet per år.

**Fra intensitet til sandsynlighed:** Overlevelsessandsynlighed over ét tidsstep:

$$P(\text{overlever } [t, t+\Delta t]) = e^{-\mu(x+t) \cdot \Delta t}$$

---

## 4. Finansielt marked — deterministisk unit-link

Policens depoter er investeret i en fond med **enhedspris** (NAV):

$$P(t) = P_0 \cdot e^{r \cdot t}$$

hvor $r$ er den kontinuerte årlige afkastrate og $P_0$ er startprisen. Depot­værdien i DKK er:

$$V(t) = n(t) \cdot P(t)$$

hvor $n(t)$ er antallet af enheder. Det finansielle afkast er *implicit* — det fremkommer automatisk af, at $P(t)$ stiger med $e^{r \cdot \Delta t}$ per tidsstep, uden at enhedsantallet ændres.

**Antagelse:** Markedet er deterministisk — ingen stokastisk afkastusikkerhed i v1.0.

---

## 5. Thieles differentialligning

Thieles ligning er den centrale ODE, der driver depotudviklingen. Den kan udledes som en **konsistenskrav** (no-arbitrage): depotets vækst pr. tidsenhed skal svare til afkast plus indbetalinger minus udbetalinger minus den forventede udgift til biometriske risici.

For depot $d$ i tilstand I_LIVE:

$$\frac{dV_d}{dt} = r \cdot V_d(t) + \pi_d(t) - b_d(t) - c_d(t) - \mu(x+t) \cdot R_d(t)$$

Hvert led har en klar fortolkning:

| Led | Symbol | Fortolkning |
|---|---|---|
| Afkast | $r \cdot V_d$ | Depot vokser med afkastraten |
| Indbetaling | $\pi_d$ | Præmieindbetaling til depot $d$ (DKK/år) |
| Udbetaling | $b_d$ | Pensionsydelse fra depot $d$ (DKK/år) |
| Omkostning | $c_d$ | Forvaltningsomkostning (DKK/år) |
| Biometrisk led | $\mu \cdot R_d$ | Forventet udgift til forsikringsdækning |

### Risikosummen $R_d$

Risikosummen er det nettobeløb, der skal afregnes ved død:

$$R_d = S_d + V_d^{\text{DOED}} - V_d^{\text{I\_LIVE}}$$

- $S_d$: ekstern dødsfaldsdækning på depot $d$
- $V_d^{\text{DOED}}$: depotets hensættelse i DOED-tilstanden
- $V_d^{\text{I\_LIVE}}$: depotets nuværende værdi

I dette bibliotek er produktet rent unit-link **uden ekstern dødsfaldsdækning**: depot udbetales til bo ved død, og DOED-reserven er nul. Det giver:

$$R_d = V_d + 0 - V_d = 0$$

Det biometriske led er strukturelt til stede i ligningerne, men bidrager numerisk med nul for opsparingsfasen. Ved udbetalingsfasens livrente gælder $R_d \neq 0$, da en levende forsikringstager har krav på fremtidige ydelser, som bortfalder ved død.

### Diskretisering — Euler fremadskridende

Da depotet opbevares som *enheder* $n_d = V_d / P(t)$ (og afkastleddet dermed er implicit), reduceres Thiele til:

$$\Delta n_d = \Delta t \cdot \frac{\pi_d - b_d - c_d - \mu \cdot R_d}{P(t)}$$

**Rækkefølge inden for hvert tidsstep:**
1. Indbetalinger ($\pi_d \cdot \Delta t$) tilskrives som nye enheder ved $P(t)$
2. Finansielt afkast: implicit via $P(t) \to P(t + \Delta t) = P(t) \cdot e^{r \Delta t}$
3. Biometrisk koblingsled ($-\mu \cdot R_d \cdot \Delta t$) fratrækkes ved $P(t)$
4. Udbetalinger og omkostninger ($-(b_d + c_d) \cdot \Delta t$) fratrækkes ved $P(t)$

---

## 6. Fremregningsalgoritmen

Systemet fremregnes med månedlige tidsstep $\Delta t = 1/12$:

```
For hvert tidsstep [t, t + Δt]:

  1. Beregn µ(x+t) fra Gompertz-Makeham

  2. Thiele-skridt (betinget depotfremregning):
     Δn_d = Δt · [π_d − b_d − c_d − µ·R_d] / P(t)
     → opdaterede betingede depoter givet I_LIVE

  3. Kolmogorov-skridt (sandsynlighedsopdatering):
     p₀(t+Δt) = p₀(t) · (1 − µ·Δt)
     p₁(t+Δt) = 1 − p₀(t+Δt)

  4. Output for dette tidsstep:
     - Betinget depot givet I_LIVE:   V_d(t+Δt | I_LIVE)
     - Sandsynlighedsvægtet depot:    p₀(t+Δt) · V_d(t+Δt | I_LIVE)
     - Overlevelsessandsynlighed:     p₀(t+Δt)
```

**Output** er en tidsserie med én række per måned, indeholdende alle depotværdier, sandsynligheder og cashflows.

---

## 7. Udbetalingsfasen

Når `er_under_udbetaling = True` stopper indbetalingerne og ydelserne beregnes:

**Ratepension** (fast ydelse over $n$ år):

$$b_{\text{rate}}(t) = \frac{V_{\text{rate}}(t)}{\ddot{a}_n^{(12)}}$$

hvor $\ddot{a}_n^{(12)} = \sum_{k=0}^{12n-1} \frac{1}{12} \cdot e^{-r \cdot k/12}$ er den diskonterede annuitetsfaktor.

**Livrente** (livsvarig ydelse):

$$b_{\text{liv}}(t) = \frac{V_{\text{liv}}(t)}{\ddot{a}_x^{(12)}}$$

hvor $\ddot{a}_x^{(12)} = \sum_{k=0}^{\infty} \frac{1}{12} \cdot e^{-r \cdot k/12} \cdot {}_k p_x$ er den livsvarige annuitetsfaktor (beregnet numerisk med max-alder 120 år).

---

## 8. Centrale antagelser

| # | Antagelse | Implikation |
|---|---|---|
| A1 | **To tilstande** — kun I_LIVE og DOED | Invalid, fripolice og genkøb er ikke modelleret |
| A2 | **Deterministisk finansielt marked** | Ingen afkastusikkerhed; $r$ er konstant over hele perioden |
| A3 | **Gompertz-Makeham dødelighed** — tidshomogen | Samme dødelighedsintensitet i hele fremregningsperioden; ingen fremtidig dødelighedsforbedring |
| A4 | **Rent unit-link** — $R_d = 0$ i opsparingen | Ingen ekstra dødsfaldsdækning ud over depotets aktuelle værdi |
| A5 | **Diskret tid** — $\Delta t = 1/12$ | Euler-diskretisering; numerisk fejl er $O(\Delta t^2) \approx 0,007$ pr. skridt |
| A6 | **Indbetaling proportional til depotandele** | Indbetalingen fordeles til de tre depoter i samme forhold som deres aktuelle størrelse |
| A7 | **`er_under_udbetaling` er eksplicit** | Systemet skifter *ikke* automatisk til udbetaling ved pensionsalderen — dette styres af kalderen |
| A8 | **Annuitetsfaktorer genberegnes ved hvert step** | Ydelsen ændrer sig månedligt med den resterende depotværdi og resterende løbetid |

---

## 9. Eksempel — Konkrete inputparametre

```python
# Dødelighedsmodel (dansk mand, G82-lignende)
biometri = GompertzMakeham(alpha=0.0005, beta=0.00004, sigma=0.09)

# Finansielt marked (5 % p.a. kontinuert afkast)
marked = DeterministicMarket(r=0.05, enhedspris_0=100.0)

# Police
police = Policy(
    foedselsdato    = date(1980, 1, 15),
    tegningsdato    = date(2020, 6, 1),   # alder ≈ 40,4 år
    pensionsalder   = 67,
    loen            = 600_000,            # DKK/år
    indbetalingsprocent = 0.15,           # 90.000 DKK/år
    ratepensionsopsparing = 800.0,        # enheder = 80.000 DKK
    ratepensionsvarighed  = 10,           # år
    livrentedepot   = 500.0,              # enheder = 50.000 DKK
)

# Omkostningsmodel: 0,5 % AUM p.a. + 200 DKK/år fast
omk = standard_omkostning(marked, aum_rate=0.005, styk_aar=200.0)
```

**Typisk output ved pensionsalder (t ≈ 26,6 år):**

| Størrelse | Værdi |
|---|---|
| Overlevelsessandsynlighed $p_0$ | ≈ 0,963 |
| Ratepension (betinget) | ≈ 750.000 DKK |
| Livrente (betinget) | ≈ 475.000 DKK |
| Total depot (betinget) | ≈ 1.225.000 DKK |

---

## 10. Hvad er ikke med i v1.0

- Stokastisk finansielt marked (rentekurve, scenariebaseret)
- Invalid-tilstand
- Fripolice og genkøb
- Ekstern dødsfaldsdækning ($S_d \neq 0$)
- Porteføljeaggregering
- Reserveberegning (Thiele baglæns — Phase 3)
