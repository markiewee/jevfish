# Calibration experiment on the real Pureloft backtest, 18 Sep 2026

Re-analysis of the 4,005 stored poll records from run `r_2f97f45e18` (project
`p_71f65447c6`), 801 people polled at each of five nightly rates on the lite platform.
The only real outcome available is the level at MYR 300: **89.2 percent occupancy over 610
resolved nights**, from Pureloft's own `pricing_calendar`.

Scripts are analysis-only and live in the session scratchpad. Nothing in `src/` was changed.

> ## CORRECTION, added 18 Sep 2026 after the literature review came back
>
> **Every "credible elasticity" comparison in this document is withdrawn.** The two
> benchmarks used below are unsourced:
>
> - **"Cornell benchmark -0.36"** appears in neither Corgel, Lane and Woodworth (2012) nor
>   Enz, Canina and van der Rest (2015). I checked the second paper directly: it is a
>   relative-price-positioning study of 4,000+ European hotels over 2004 to 2013 and it
>   **does not measure price elasticity at all**.
> - **"published property-level range -0.13 to -0.95"** is a garbled restatement of the
>   properly sourced market-level -0.1 to -0.9.
>
> What is actually supported: Singh and Corsun (2023), 2,503 US hotels, 2SLS, **-0.165
> short run** and **-0.79 long run**, at *market* level. And Corgel et al. state plainly
> that "elasticity tends to increase with data disaggregation", that individual-hotel
> elasticity "will be higher than their market level elasticity suggests", and that their
> figures "cannot be directly applied to an individual hotel".
>
> **The bias runs the opposite way from what I assumed.** A single differentiated KL
> serviced apartment can legitimately be *more* elastic than -0.9. So the -0.893 below is
> not obviously credible and the -1.93 is not obviously absurd. **There is no trustworthy
> property-level benchmark, so elasticity cannot be used to judge whether a run is
> plausible.**
>
> **What survives, and it is the important part.** Finding 7 does not depend on any
> benchmark. Its claim is that the *same inputs* give -1.432 or -0.090 depending on one
> adjective per option, so neither number is a measurement. That is untouched, and it is
> now the load-bearing result. Also untouched: the 11.5x interval understatement
> (Finding 1), the degenerate crowd spread (Findings 2 and 5), and the estimand mismatch
> (Finding 6), none of which reference an elasticity benchmark.
>
> Corrected in memory at `project-jevfish-pricing-calibration` and
> `reference-hotel-price-elasticity-evidence`.

## Finding 1: the reported interval is wrong by 11.5x, and grows more wrong with crowd size

| Quantity | Value |
|---|---|
| Reported `mean_outcome` | 0.568 |
| Reported 90 percent interval | 0.540 to 0.596 (half-width 2.82pp) |
| Actual outcome | 0.892 |
| Actual error | 32.4pp |
| **Error divided by stated half-width** | **11.5x** |
| Half-width that would have contained the truth | 32.4pp, about 11x the stated one |

The interval is `Z90 * sqrt(sum p(1-p))`, which is sampling noise inside a synthetic crowd.
It shrinks as `1/sqrt(n)` while the real error does not move at all. Adding people therefore
makes JevFish more confidently wrong. This is the most dangerous single property in the tool
as it stands, because the number looks precise.

## Finding 2: the crowd barely disagrees, and that caps what any aggregation rule can do

Per-person probabilities at MYR 300, across 801 people:

| Quantile | p |
|---|---|
| 5th | 0.390 |
| 25th | 0.520 |
| 50th | 0.540 |
| 75th | 0.640 |
| 95th | 0.710 |
| standard deviation | 0.096 |

The whole 5th-to-95th range is 0.39 to 0.71. A real population deciding whether to book
would have heavy mass near 0 and near 1. Instead every simulated person answers roughly
"maybe", and 801 near-identical middling probabilities are averaged into 0.568.

A mean of values that all sit near 0.54 structurally cannot produce 0.89. The level error is
not mainly a mapping problem, it is a **variance problem in the crowd**. This matches the
mode-collapse result in the silicon-sampling literature: LLM personas are far less
heterogeneous than the population they are meant to stand for.

## Finding 3: no aggregation rule fixes both level and shape

Applied to the same stored probabilities, changing only how they are pooled:

| Rule | 200 | 250 | 300 | 400 | 500 | elasticity | error at 300 | picks |
|---|---|---|---|---|---|---|---|---|
| mean of probabilities (current) | 0.690 | 0.670 | 0.568 | 0.395 | 0.325 | -0.893 | -32.4pp | MYR 300 |
| hard vote at 0.5 | 1.000 | 1.000 | 0.889 | 0.235 | 0.142 | -2.375 | **-0.3pp** | MYR 300 |
| log-odds pool | 0.692 | 0.673 | 0.570 | 0.390 | 0.314 | -0.933 | -32.2pp | MYR 300 |
| extremized, a=2.0 | 0.835 | 0.808 | 0.638 | 0.289 | 0.174 | -1.836 | -25.4pp | MYR 250 |
| extremized, a=3.0 | 0.919 | 0.897 | 0.701 | 0.206 | 0.088 | -2.724 | -19.1pp | MYR 250 |

Reference points: the actual outcome at MYR 300 is 0.892, the Cornell property-level
elasticity benchmark is -0.36, and the published property-level range is -0.13 to -0.95.

Hard voting lands the level at MYR 300 almost exactly (0.889 against 0.892) with nothing
fitted, but it saturates at 1.000 for the two cheap rungs and returns an elasticity of
-2.375, which is far outside anything ever measured. It gets one number right and the curve
wrong. Log-odds pooling is indistinguishable from the current mean. Extremizing moves the
level in the right direction but overshoots the curve.

**No rule is good on both axes.** Picking an aggregation rule to make one known number come
out right is curve-fitting, and it would not survive a second anchor.

## Finding 4: a one-parameter logit shift fixes the level, preserves the order, and flips the decision

Shift every person's log-odds by a single constant `b`, then re-average. Solve `b` so that
the MYR 300 rung matches the one known outcome. Fitted `b = +1.8906`.

| rate | raw share | calibrated share | raw revenue index | calibrated revenue index |
|---|---|---|---|---|
| MYR 200 | 0.690 | 0.935 | 138 | 187 |
| MYR 250 | 0.670 | 0.930 | 168 | 232 |
| MYR 300 | 0.568 | 0.892 | 170 | 268 |
| MYR 400 | 0.395 | 0.795 | 158 | 318 |
| MYR 500 | 0.325 | 0.738 | 162 | 369 |

| | raw | calibrated |
|---|---|---|
| fitted elasticity | -0.893 | **-0.277** |
| error at MYR 300 | -32.4pp | 0.0pp (by construction) |
| revenue-maximising rate | MYR 300 | MYR 500 |
| order of the five rungs | 200>250>300>400>500 | identical |

Three things to take from this:

1. **The order cannot change.** A logit shift is strictly monotone, so the ranking of the
   five rungs on raw share is preserved exactly. The "shape is credible, level is not"
   result survives calibration for free.
2. **The elasticity moves from -0.893 to -0.277**, which sits closer to the Cornell -0.36
   benchmark than the raw number did. That is a real improvement in the one property we have
   an external benchmark for.
3. **The decision flips.** Raw says hold at MYR 300. Calibrated says raise. The evidence
   says raise (occupancy is flat from MYR 140 to 300 and sustained near 90 percent is the
   signature of underpricing). So calibration moved the recommendation from the wrong
   direction to the right one. It may overshoot on how far to raise, but the sign is now
   right, and the sign is the part that costs money.

### The important consequence

Monotone calibration cannot change which option has the highest share. It **can** change
which option is best once share is weighted by anything (price, margin, volume). That is
exactly what happened here: the order stayed identical while the revenue-maximising rung
moved from MYR 300 to MYR 500.

So the standing advice, "only use JevFish for relative comparisons, never quote its absolute
number", is not actually safe. As soon as the decision multiplies the share by a price or a
cost, the absolute level determines the answer. Calibration is required, not optional.

## What this does not show

Being honest about the limits of this experiment:

- `b` was fitted to make MYR 300 exactly right, so the zero level error is by construction
  and is **not** a validated gain. It is in-sample with one data point and one parameter.
- With a single anchor there is no way to hold anything out. A leave-one-out test needs at
  least three anchors, and a real validation needs a benchmark set with many resolved
  outcomes. That is the argument for a public benchmark suite rather than calibrating on
  Pureloft.
- Pureloft's own data cannot supply more anchors for this question. Measured elasticity on
  it comes out positive (+0.17 to -0.02) because rates were raised on nights already
  expected to fill, and only 169 of 1,520 resolved nights went unsold. It gives one credible
  level and no credible curve.
- The Cornell -0.36 is a different estimand (hotels, 4,120 properties) from a KL serviced
  apartment, so "closer to -0.36" is weak evidence, not proof.

## What it implies for the build

1. Calibration is not a nice-to-have. Without it the tool points the wrong way on a
   revenue decision.
2. The interval must be rebuilt from held-out error, not from Poisson-binomial noise. A
   number that is 11.5 times its own stated uncertainty is worse than no number.
3. Crowd variance has to be fixed upstream. With a per-person standard deviation of 0.096,
   all the aggregation rules are just different ways of squeezing one answer out of a
   degenerate distribution.
4. Anchors need somewhere to come from. One anchor buys one parameter. This drives the
   benchmark-suite work.

## Finding 5: the root cause, located precisely

Variance decomposition of the 801 people at MYR 300, using the stored `crowd.json` segments:

| Source | Variance | Share |
|---|---|---|
| total | 0.00915 | 100% |
| between segments | 0.00476 | 52.0% |
| within segments | 0.00439 | 48.0% |

| Segment | n | mean | sd | min | max |
|---|---|---|---|---|---|
| Gulf summer vacationers | 150 | 0.680 | 0.033 | 0.60 | 0.72 |
| Extended family holiday planners | 280 | 0.593 | 0.092 | 0.36 | 0.72 |
| Budget-conscious friend groups | 202 | 0.527 | **0.015** | 0.50 | 0.57 |
| AccommodationProvider | 1 | 0.510 | 0.000 | 0.51 | 0.51 |
| Indonesian shopping travelers | 168 | 0.476 | 0.074 | 0.35 | 0.56 |

Three hard facts fall out of this:

1. **Across all 801 people the minimum is 0.35 and the maximum is 0.72.** Not one simulated
   person would definitely book, and not one would definitely refuse. This is not a
   population, it is 801 shades of "maybe". No aggregation of numbers bounded in
   [0.35, 0.72] can produce 0.892.
2. **Only 30 distinct probability values are returned across 801 people**, and the four
   commonest are 0.52, 0.53, 0.54 and 0.71, covering 341 of the 801. Jev is emitting a
   coarse, narrow band, not a continuous individual judgment.
3. **The per-person attributes are nearly inert.** "Budget-conscious friend groups" has 202
   members carrying different income and priority attributes and a standard deviation of
   0.015. The segment label moves the answer (segment means spread across 0.204), the
   individual detail inside a segment does not.

### Why this happens, and what it implies

`poll_questions` asks a `NoulQ`: the probability that the person described in `agent` does
the thing. Jev is being asked to estimate a rate for a person **type**, and it answers like
an actuary, near the middle, because that is the well-hedged answer to a question about a
thinly described type. It is not being asked to make that person's decision.

Three candidate fixes, in the order I would try them:

1. **Ask for a discrete choice, not a probability.** Replace the per-person `NoulQ` with a
   `ChoiceQ` over the actual alternatives, including "books none of them". Jev must then
   commit per person, the share comes from counting, and the answer can reach 0 or 1.
   This is a frame and policy change, not new machinery.
2. **Give each person enough detail for the answer to be determined.** Real budget figures,
   party size, travel dates, the two alternatives they already shortlisted. The inertness of
   income and priority suggests the current attributes are too abstract to bite.
3. **Recalibrate what comes out**, using anchors, as Finding 4 does. This is the backstop
   that is needed regardless, because it is the only part that can be validated against
   held-out outcomes.

Fixes 1 and 2 attack the cause. Fix 3 bounds the damage. The plan should do all three, and
should measure each one separately on the same benchmark so we know which actually paid.

## Finding 6: live probe of four framings, 40 real personas each

Ran the same booking question four ways against live Jev, using 40 personas drawn from the
stored `crowd.json`, subject fixed at MYR 300. 160 requests, about US$0.007. Truth is 0.892.

| Condition | mean | sd | min | max | distinct values | range |
|---|---|---|---|---|---|---|
| A: current `NoulQ` | 0.515 | 0.080 | 0.42 | 0.67 | 19 | 0.25 |
| D: status-quo anchor removed | 0.527 | 0.083 | 0.40 | 0.69 | 21 | 0.29 |
| C: enriched persona | 0.433 | **0.192** | **0.09** | 0.68 | 29 | **0.59** |
| B: discrete `ChoiceQ` | 0.225 (share) | n/a | 0 | 1 | 2 | 1.00 |

### C: enriching the persona is the real variance fix, and it does not fix the level

Giving each person a party size, a number of nights, a total accommodation budget, a
per-night budget, one already-shortlisted alternative, date flexibility and whether they
have stayed in the building before:

- standard deviation goes from 0.080 to 0.192, **2.4x**
- the range goes from 0.25 to 0.59, and the minimum falls from 0.42 to 0.09, so some people
  now genuinely rule the apartment out
- distinct values rise from 19 to 29

This confirms the diagnosis in Finding 5: the attributes we were attaching (income band,
priority word) were too abstract to bite, and concrete numbers do bite. **But the mean moved
from 0.515 to 0.433, away from the truth.** Enrichment buys discrimination between people.
It does not buy level accuracy. Both have to be worked separately.

### D: the status-quo anchor is not the problem. Hypothesis killed

The frame labels the incumbent rate as "the rate Pureloft actually charges" and the others as
"a third below the current rate" and so on, which telegraphs the incumbent to the judge.
Removing it moved the mean by 1.2 points and left the standard deviation unchanged. Real but
negligible. Not worth a task. Worth having tested, because it cost almost nothing to rule out.

### B: the discrete choice made the level worse, and that is the most useful result

Replacing the probability question with a forced choice between "books this", "books a rival"
and "books nothing" produced a hard commitment per person and good underlying variance (its
`books_this` probabilities have sd 0.204 across 0.03 to 0.73). But the share came out at
0.225, far worse than 0.515, and the picks were:

| pick | n |
|---|---|
| books_this | 9 |
| books_rival | 31 |
| books_nothing | 0 |

My hypothesis in Finding 5 was that a forced choice would improve accuracy. **It did the
opposite.** That negative result is what makes the actual problem visible.

### The estimand is wrong, and that is the real finding

The frame tells the judge there are "several near-identical apartments in the SAME building,
listed by other owners who each set their own price". Faced with that, a sensible shopper
picks a rival most of the time, which is exactly what 31 out of 40 did. The model is
correctly answering a **market-share** question: out of the described option set, does this
shopper pick our listing?

Occupancy is not that quantity. 89.2 percent occupancy is the fraction of nights one unit is
full, which is total demand volume divided by supply. It is not the fraction of shoppers who
prefer our listing over its rivals. The two numbers can differ by any amount, because a unit
with a 22 percent choice share can still run at 89 percent occupancy if enough shoppers
arrive per night.

So the 32.4 point gap is not primarily a calibration error. It is an **estimand mismatch**.
`mean_outcome` is a choice share within a synthetic shopper pool whose size is not tied to
any real demand volume, and it was being read as an occupancy rate.

This changes the plan in three ways:

1. JevFish must **name its estimand** in the output. It predicts share of a described option
   set, and the UI should say so next to the number instead of showing a bare percentage
   that invites being read as a rate.
2. The calibration layer is still needed, but its job is narrower and better defined: map
   choice share to the real-world rate the user actually cares about. That map depends on
   the question type, so it has to be **per-question-family and fitted from anchors**, never
   one global constant.
3. The fitted logit shift in Finding 4 works because the map from share to occupancy happens
   to be monotone. It is a usable backstop, not an explanation. It should be presented as a
   fitted correction with the anchors it was fitted on, shown to the user.

### Costs, for the record

160 Jev requests, about US$0.007 total. Ruling out the status-quo-anchor hypothesis and
overturning the discrete-choice hypothesis cost under a cent. Every design change in the
plan should be probed this way before it is built.

### Sanity check that supports the estimand reading

The frame describes "several near-identical apartments in the SAME building, listed by other
owners who each set their own price". Under symmetric competition against k near-identical
rivals, a choice share of `1/(k+1)` is the expected answer. The measured discrete share was
0.225, and `1/(4+1) = 0.20`. The match is close enough that the simplest explanation is the
right one: Jev is computing a choice share correctly, and we were scoring it against
occupancy. Any model that answered 0.892 to the question as posed would have been wrong.

---

## Finding 7: the demand curve was written by the frame, not measured by the model

This overturns both the "the shape is credible" conclusion and my own Finding 6, part D.
Same 40 personas, same five rates, no social simulation. The **only** thing that changes
between arms is the `rate_note` string attached to each rate.

The stored frame's `rate_note` values, written by the LLM, are comparative:

| rate | `rate_note` as shipped |
|---|---|
| MYR 200 | "a third below the current rate" |
| MYR 250 | "below the current rate" |
| MYR 300 | "the rate Pureloft actually charges" |
| MYR 400 | "a third above the current rate" |
| MYR 500 | "two thirds above the current rate" |

Results:

| Arm | 200 | 250 | 300 | 400 | 500 | elasticity | mean sd | revenue-max |
|---|---|---|---|---|---|---|---|---|
| A: `rate_note` as shipped | 0.686 | 0.656 | 0.517 | 0.267 | 0.211 | **-1.432** | 0.063 | **MYR 250** |
| B: `rate_note` neutral, same length | 0.548 | 0.533 | 0.528 | 0.514 | 0.503 | **-0.090** | 0.081 | **MYR 500** |
| C: `rate_note` removed | 0.554 | 0.534 | 0.527 | 0.510 | 0.498 | **-0.113** | 0.081 | **MYR 500** |

Arms B and C agree to within 0.023. So it is not the presence of the field or its length, it
is the **comparative content**. Replacing "two thirds above the current rate" with a neutral
phrase of the same length removes essentially the entire price response.

### What this means

1. **The demand curve was an artifact of an LLM-authored adjective.** The -0.893 elasticity
   from the full run, the one we recorded as "inside the published range of -0.13 to -0.95
   and near Singh and Corsun's -0.79 long run", was largely produced by the frame telling
   Jev which rates were cheap and which were dear. It was not the model reasoning about
   price. Arm A reproduces the effect at -1.432 with only 40 people and no simulation.
2. **The decision flips on the wording alone.** Arm A says cut to MYR 250. Arms B and C say
   raise to MYR 500. Nothing about the property, the dates or the crowd changed. One
   editorial phrase per option decided a revenue recommendation.
3. **The un-cued price response is about -0.10.** That is close to what Pureloft's own
   resolved-nights data says (measured elasticity +0.17 to -0.02, occupancy flat from MYR 140
   to 300). When the frame stops telling Jev the answer, Jev and the real data agree that
   demand here is close to inelastic, which is the finding that says the rate is too low.
4. **My Finding 6 part D conclusion was wrong, and the reason is instructive.** I tested
   removing `rate_note` at MYR 300 only, saw a 1.2 point move, and wrote "hypothesis killed,
   not worth a task". But at MYR 300 the note reads "the rate Pureloft actually charges",
   which is roughly neutral. The bias lives at the ends of the ladder, which is exactly where
   the slope is determined. **Testing a frame change at a single option measures the level
   and tells you nothing about the shape.** Any frame-sensitivity test has to sweep the whole
   option set.

### The engineering consequence

The frame is an uncontrolled confound, and JevFish currently lets an LLM write it
unsupervised. This outranks calibration, post-stratification and aggregation in priority,
because no amount of downstream correction recovers a slope that was dictated by the prompt.

Two changes follow:

- **Per-option text must be neutral and symmetric by construction.** The frame generator
  must be forbidden from writing comparative or evaluative language into any per-variant
  field. Options should differ only in the quantity under test. This is a prompt constraint
  plus a validator in `normalize_frame`, and the validator is the part that makes it stick.
- **Frame sensitivity has to be reported on every run.** Re-run the ladder with per-option
  text neutralised and show both curves. If the two disagree, the run is telling you about
  its own wording, not about the world, and the report must say so instead of printing a
  number.

## Finding 8: the published exogeneity fix does not replicate on Jev

Gui and Toubia's result is that telling the model the treatment was randomly assigned moves
measured elasticity from 0.14 to 1.38 across 40 product categories, because a generative LLM
otherwise infers confounders (season, competitor prices, quality) from the price itself.

Tested on our data, 40 personas across all five rates, with `rate_note` neutralised so the
Finding 7 artifact could not mask the effect. Added sentence: the rate "was set RANDOMLY by
the operator as part of a pricing experiment. It carries no information about demand, season,
the quality of the apartment, or what competitors charge."

| Arm | elasticity | mean sd |
|---|---|---|
| baseline, no sentence | -0.106 | 0.080 |
| with exogeneity sentence | -0.107 | 0.067 |

**No effect: -0.001.** The sentence also narrowed the crowd slightly, from sd 0.080 to 0.067,
which is mildly unhelpful.

Likely reason, and it is a hypothesis rather than a finding: Gui and Toubia's mechanism
requires a generative model that imagines unstated confounders while composing an answer.
Jev returns a typed judgment and writes no text, so it may not be running that inference at
all. Finding 7 proves Jev is extremely sensitive to framing, so this is not indifference to
the prompt. It responds strongly to **comparative cues about the options** and not at all to
a **causal disclaimer about the design**.

Practical read: do not import prompt fixes from the generative-LLM simulation literature on
faith. They were measured on a different kind of model. Each one has to be re-tested here,
across the whole option set, and this one costs about two cents to test.
