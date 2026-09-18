# Making JevFish-class predictions actually accurate

Literature review, 18 September 2026. Scope: silicon sampling / synthetic survey accuracy, the level-versus-shape failure, implementable calibration methods, scoring, benchmarks, and what the strongest LLM forecasting systems do.

Every claim below carries a URL. Where a number could not be verified from a primary source it is marked NOT VERIFIED.

---

## Executive summary: highest-leverage changes, ranked

1. Name the estimand, because the 32.4pp gap is mostly a mismatch, not a calibration failure. What the crowd produces is a share of a described option set under equal awareness and equal distribution, which the conjoint industry has called "share of preference" for forty years and never reads as a market rate; getting from there to a rate requires availability, awareness, a scale exponent and a share adjustment, in that order ([sawtoothsoftware.com/help/lighthouse-studio/manual/external-effects.html](https://sawtoothsoftware.com/help/lighthouse-studio/manual/external-effects.html)).
2. Collect anchor outcomes, and spend them on the correction layer rather than on improving the simulator. Synthesis alone carries 24% to 86% bias; synthesis plus rectification drops it below 5%, and under a fixed budget most human responses should go to rectification, not fine-tuning ([arxiv.org/abs/2510.11408](https://arxiv.org/abs/2510.11408)). Doubly-robust correction took naive synthetic bias from 33.1pp to 0.2pp on ANES and 1.9pp to 0.32pp on purchase intent ([arxiv.org/html/2609.13148](https://arxiv.org/html/2609.13148)).
3. Then fit a two-parameter monotone recalibration in logit space, `p_cal = sigmoid(a + b * logit(p_raw))`, applied per persona before aggregation. `a` fixes the level and `b` fixes the slope, so it fixes the elasticity too. This is what the only published LLM-persona pricing system that beats a real baseline does, and it reached 90% of optimal revenue from roughly 73 real observations, about 3 per product ([arxiv.org/html/2606.16183v1](https://arxiv.org/html/2606.16183v1)).
4. Fix the frame before trusting any curve. Gui and Toubia show naive price prompts produce inverted-U demand curves where humans slope down, and that stating the price variation is experimentally assigned cuts MAE by 1% to over 60% (elasticity 0.14 to 1.38 in the earlier version, against a literature benchmark of 1.8 to 3.0). The frame, not the crowd, sets the elasticity ([arxiv.org/html/2312.15524v3](https://arxiv.org/html/2312.15524v3)).
5. Put retrieved, relevance-filtered evidence in the frame. This is the largest lever in the forecasting literature by a wide margin: the current state of the art scores 0.1002 Brier with search and **0.3609 without**, worse than always guessing 0.5 ([arxiv.org/abs/2511.07678](https://arxiv.org/abs/2511.07678)), and no raw frontier model reaches the public crowd without tools ([forecastbench.org](https://www.forecastbench.org/)).
6. Build your own eval set before optimising the pipeline. In the only systematic survey of what separates winning forecasting bots from losing ones, "custom question testing" scored **+2,216 points [+912, +3,519]**, ahead of aggregation strategy and far ahead of dev time, which was not significant at all ([metaculus.com/notebooks/43363](https://www.metaculus.com/notebooks/43363/ai-forecasting-in-2026/)).
7. Replace the Poisson-binomial interval with split conformal on your own historical errors. Distribution-free finite-sample coverage, needing only `k >= 1/alpha - 1` anchors, so 9 for 90% ([arxiv.org/pdf/2303.02770](https://arxiv.org/pdf/2303.02770)). The current interval understated the measured error by 11.5x and gets worse as the crowd grows.
8. Stop growing the crowd and start diversifying the judge. A random-matrix analysis found that one model resampled 100 times has "**at most one dimension** [that] rises above noise", while 24 different models clear four ([arxiv.org/abs/2607.20464](https://arxiv.org/abs/2607.20464)). Winning bots use 5 to 10 samples across 3 to 7 models, with measured degradation past about 10 models. Persona richness buys nothing on top: 0.748 accuracy for a 500-question twin against 0.746 for 14 demographic variables ([arxiv.org/abs/2509.19088](https://arxiv.org/abs/2509.19088)).
9. Score with proper rules only, always against a named baseline including a one-call empty-persona ablation. RPS for ordered options, CRPS for a continuous share, Murphy's reliability-resolution-uncertainty split to separate level error from shape skill. ECE is not a proper scoring rule and a model with no discriminatory power can score zero on it ([arxiv.org/pdf/2408.02841](https://arxiv.org/pdf/2408.02841)).
10. For hotel rates specifically, the synthetic crowd is the wrong primary instrument. Your own booking pace with a fitted elasticity is the published state of the art and delivered 7.42% GMV lift in a live two-week test on 12,727 hotels ([arxiv.org/pdf/2208.03135](https://arxiv.org/pdf/2208.03135)). Use JevFish where you have no history, calibrate levels from the ledger where you do. Post-stratification is the cheap resolution win in between: a 93%-male, 65%-young Xbox sample that raw predicted a Romney landslide came within **0.6pp** of the national result after post-stratification ([5harad.com](https://5harad.com/papers/forecasting-with-nonrepresentative-polls.pdf)).

---

## 1. Silicon sampling and synthetic surveys: what the measured accuracy actually is

### 1.1 Argyle et al., "Out of One, Many" (Political Analysis 2023)

Source: [arxiv.org/abs/2209.06899](https://arxiv.org/abs/2209.06899), HTML at [ar5iv.labs.arxiv.org/html/2209.06899](https://ar5iv.labs.arxiv.org/html/2209.06899).

The paper that started the field. Conditions GPT-3 on ANES sociodemographic backstories (2012, 2016, 2020 waves) and proposes four criteria for "algorithmic fidelity":

- Social Science Turing Test: generated responses indistinguishable from parallel human text.
- Backward Continuity: responses consistent with the conditioning context.
- Forward Continuity: responses proceed naturally from the conditioning context in form, tone and content.
- Pattern Correspondence: responses reflect the underlying relational patterns between ideas, demographics and behaviour in comparable human data.

Measured numbers:

- Study 1 (partisan word lists): evaluators judged 61.7% of human lists to be human-written versus 61.2% of GPT-3 lists (p = 0.44). Partisanship of the list author was correctly identified 60.1% of the time for humans versus 52.8% for GPT-3.
- Study 2 (vote choice): tetrachoric correlation between silicon and human vote choice was 0.90 (2012), 0.92 (2016), 0.94 (2020). Proportion agreement 0.85, 0.87, 0.89.
- Study 3: mean difference in Cramer's V between human and GPT-3 contingency structure was -0.026.

The caveat that matters most for JevFish is stated by the authors themselves: there is "a mild amount of overall bias", with GPT-3 predisposed against Romney (2012), Trump (2016) and Biden (2020), yet subgroup correlations remain strong. Relative patterns match while absolute marginals diverge. That is the level-versus-shape problem, named in the founding paper.

### 1.2 Santurkar et al., "Whose Opinions Do Language Models Reflect?" (ICML 2023) and OpinionQA

Source: [arxiv.org/abs/2303.17548](https://arxiv.org/abs/2303.17548), HTML at [ar5iv.labs.arxiv.org/html/2303.17548](https://ar5iv.labs.arxiv.org/html/2303.17548), data at [github.com/tatsu-lab/opinions_qa](https://github.com/tatsu-lab/opinions_qa).

- Dataset: 1,498 questions, 60 US demographic groups, built from 15 Pew American Trends Panel waves (ATP_W26, W27, W29, W32, W34, W36, W41, W42, W43, W45, W49, W50, W54, W82, W92), 2017 to 2021.
- The alignment metric is 1 minus normalised 1-Wasserstein distance:
  `A(D1, D2; Q) = (1/|Q|) * sum_q [ 1 - WD(D1(q), D2(q)) / (N - 1) ]`
  where N is the number of ordered answer options excluding refusal. Representativeness of model m for group O is `R = A(D_m, D_O, Q)`.
- Headline findings: no model is representative of the general populace; the misalignment is comparable in size to the Democrat-Republican gap on climate change; every real demographic group was more representative of the overall populace than any LM was; misalignment persists after explicit demographic steering; 65+ and widowed respondents are among the worst represented.
- The paper reports representativeness as figures rather than a single headline table value, so a single "best model score" number is NOT VERIFIED here. Use the released code to recompute on your own option sets.

Why this matters for JevFish: the Wasserstein-based alignment score is directly reusable as your evaluation metric for an ordered option set (five price points is an ordered set).

### 1.3 Bisbee et al., "Synthetic Replacements for Human Survey Data? The Perils of LLMs" (Political Analysis 2024)

Source: [cambridge.org](https://www.cambridge.org/core/journals/political-analysis/article/synthetic-replacements-for-human-survey-data-the-perils-of-large-language-models/B92267DC26195C7F36E63EA04A47D2FE), doi 10.1017/pan.2024.5.

Prompts ChatGPT with ANES personas and asks for feeling-thermometer scores on 11 to 16 target groups. Numbers extracted from the published text:

- Means: every synthetic mean falls within one standard deviation of the ANES average, and the rank ordering of thermometers is largely intact. Shape right.
- Subgroups: once you split by race and partisanship, synthetic answers are more extreme, off by 0.5 to 1 ANES standard deviations, which is 10 to 20 points on a 100-point scale. Level wrong.
- Scale: **3,614,400 synthetic responses**, 30 per each of 7,530 real ANES respondents.
- Variance: synthetic standard deviations are far smaller than ANES, even at temperature 1.0. Quantified: the ANES pooled effect size was 7.8 with **SD 31.4**; the ChatGPT effect size was 12.5 with **SD 16.1**. So the effect is 1.6x too large while the spread is roughly half. The authors call this overconfidence and note it breaks any power calculation built on synthetic data.
- Not stable over time: a July re-collection showed "substantial mean reversion".
- Regression structure: 48% of coefficients estimated on ChatGPT data are statistically significantly different from their ANES counterparts, and among those cases the sign flips 32% of the time.
- Prompt sensitivity: a politics-only persona prompt has essentially identical MAE to the full prompt, while a demographics-only prompt dramatically inflates error for politically salient targets. Political attributes carry nearly all the signal.
- Framing: a second-person prompt ("You are a ...") produces exaggerated polarisation, consistent with Levendusky and Malhotra (2016) on humans estimating others' attitudes. A first-person prompt ("I am a ...") shows less exaggerated polarisation but worse overall MAE.
- Stability: response distributions shift with minor prompt wording changes, with ChatGPT version, and with the same prompt re-run three months later.

Actionable for JevFish: the persona axes that matter are the ones directly predictive of the outcome, not the demographic frame. And the second-person versus first-person choice is a measurable lever on extremity.

### 1.4 Dominguez-Olmedo, Hardt, Mendler-Dunner, "Questioning the Survey Responses of LLMs" (NeurIPS 2024)

Source: [arxiv.org/html/2306.07951v4](https://arxiv.org/html/2306.07951v4), proceedings [neurips.cc](https://proceedings.neurips.cc/paper_files/paper/2024/file/515c62809e0a29729d7eec26e2916fc0-Paper-Conference.pdf).

This is the most damaging result for a naive persona-polling pipeline.

- 43 models, 110M to 175B parameters, on 25 multiple-choice questions from the 2019 American Community Survey.
- All models show substantial "A-bias", a preference for the option labelled A, strongest in models of a few billion parameters or fewer. Labelling bias is more prevalent than positional bias across sizes.
- After adjusting via randomised choice ordering, base models reach normalised entropy of approximately 1.0, that is, essentially uniform random answering. Instruction-tuned models retain more variation but remain "significantly closer to the uniform baseline than to the US census".
- Model rankings reorder completely after adjustment: "differences across models that we see under naive prompting disappear after adjustment".
- Their conclusion about the alignment literature: models appear to represent best exactly those subgroups whose aggregate statistics happen to be closest to uniform.
- Recommended procedure: average model responses over all permutations of answer options while holding label order alphabetical.

For JevFish this means the per-option shares you observe may be dominated by label position rather than persona reasoning, unless you already permute. If you do not currently permute, this is the single cheapest experiment to run and it may explain a large fraction of the level error.

### 1.5 Tjuatja et al., "Do LLMs Exhibit Human-like Response Biases?" (TACL 2024)

Source: [aclanthology.org/2024.tacl-1.56](https://aclanthology.org/2024.tacl-1.56/), preprint [arxiv.org/abs/2311.04076](https://arxiv.org/abs/2311.04076).

- Nine models: base Llama2 at 7b, 13b and 70b; Solar (instruction fine-tuned Llama2 70b); Llama2 chat at 7b, 13b and 70b; plus OpenAI commercial models. Tested on five survey-design perturbations known to move human answers, acquiescence (176 questions), allow/forbid asymmetry (40), response order (271), opinion floating (126), odd/even scale (126), and on three non-bias perturbations (for example typos) known *not* to move humans.
- Result 1: **no model aligns with known human patterns across all five biases.**
- Result 2: **all models display statistically significant changes to the non-bias perturbations**, regardless of whether they responded to the bias modification itself. Humans do not.
- The most human-like model was base Llama2 70b, and it still showed a significant change from non-bias perturbations on **three of the five** bias types.
- No monotonic trend between model size and behaviour.
- RLHF makes it worse, in a specific measurable way: RLHF-ed chat models are more insensitive to bias-inducing changes than their base counterparts, yet show a **greater magnitude of effect size on non-bias perturbations in 21 of 27 settings**.

Implication: you cannot assume your crowd inherits human framing effects. Any framing effect JevFish reports is an artefact of the model unless independently validated.

A related 2026 study finds LLMs are biased toward answering "no" rather than exhibiting human acquiescence: across 152,040 responses from Llama, Mistral, Gemma and GPT-4 in German, English and Polish, positive ("option A equivalent") response rates were significantly *reduced* versus the neutral prompt, the opposite of the human acquiescence effect ([arxiv.org/pdf/2509.08480](https://arxiv.org/pdf/2509.08480), code at [github.com/Responsible-NLP/Acquiescence-Bias-in-Large-Language-Models](https://github.com/Responsible-NLP/Acquiescence-Bias-in-Large-Language-Models)). If your options include a "would not book" or "would decline" branch, expect a systematic refusal skew.

### 1.6 Park et al., "Generative Agent Simulations of 1,000 People" (2024/2025)

Source: [arxiv.org/abs/2411.10109](https://arxiv.org/abs/2411.10109), code [github.com/joonspk-research/genagents](https://github.com/joonspk-research/genagents), HAI writeup [hai.stanford.edu](https://hai.stanford.edu/news/ai-agents-simulate-1052-individuals-personalities-impressive-accuracy).

1,052 participants, each given a two-hour interview, then agents built from the transcripts. Accuracy is normalised against each person's own two-week test-retest reliability (1.0 means the agent predicts you as well as you predict yourself two weeks later):

- Interview-based agents: 83% of the test-retest benchmark on the GSS.
- Survey-response-based agents: 82%.
- Combined: 86%.
- Demographics-only agents: 74%.

The paper also reports reduced accuracy disparities across racial and ideological groups relative to demographics-only agents.

Read carefully: the demographics-only baseline is 74% and the best interview-based agent is 86%. Two hours of interview per person buys 12 points of normalised accuracy. JevFish generates personas from a population spec, so it sits at or below the 74% line by construction. The paper's underlying data is not public, which the Columbia mega-study below flags as a limitation.

### 1.7 Twin-2K-500 (Marketing Science 2025)

Source: [arxiv.org/html/2505.17479](https://arxiv.org/html/2505.17479), data [huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500](https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500), journal [pubsonline.informs.org/doi/10.1287/mksc.2025.0262](https://pubsonline.informs.org/doi/10.1287/mksc.2025.0262).

N = 2,058 US participants, average 2.42 hours each, four waves, 500 questions covering demographics, psychology, economics, personality, cognition, replications of behavioural economics experiments and a pricing survey. Reported out-of-sample accuracy reaching 87% of the test-retest benchmark; average absolute accuracy 72%; twins replicated about half the experimental effects found in humans.

This is public, includes a pricing survey, and is the best available paired human/LLM benchmark for a persona pipeline.

### 1.8 Peng, Gui, Brucks, ... Toubia, "Digital Twins are Funhouse Mirrors: Five Systematic Distortions" (2026)

Source: [arxiv.org/abs/2509.19088](https://arxiv.org/abs/2509.19088) (v5, 19 April 2026, 23 authors, Columbia). This is the largest and most adversarially designed test in the literature and the single most important paper on this list.

Design: 19 pre-registered sub-studies, 164 novel outcomes, N = 13,506 human observations across substudies, 1,784 unique participants drawn from the already-validated Twin-2K-500 sample, with new stimuli specifically chosen to avoid training-data leakage.

Measured results:

- Individual-level accuracy, full persona (the person's complete 500-question record in context): 0.748.
- Demographics-only persona (14 demographic variables): 0.746. Difference from full persona is not significant (p = 0.37).
- Empty persona (identical prompt for everyone, base model behaviour only): 0.734. Difference from full persona is 0.014, statistically significant but tiny.
- Uniform random baseline: 0.629.
- Average correlation between twin and human responses across outcomes: r = 0.197. Positive in 157 of 164 outcomes (95.7%), significantly positive in 97 (59.1%).
- Aggregate level: mean twin response differs from mean human response by 0.352 human standard deviations on average (absolute Glass's Delta), with a significant difference in 105 of 164 outcomes (64.0%).
- Twins are under-dispersed (standard deviation ratio below 1).
- Five named distortions: (i) insufficient individuation, (ii) stereotyping, (iii) representation bias (more accurate for higher education, higher income, moderate political views), (iv) ideological biases (simultaneously pro-human and pro-technology), (v) hyper-rationality (answers reflect higher rationality and knowledge than humans).
- Human experts could not predict twin behaviour: the average treatment effect among twins fell outside experts' 95% prediction interval in 3 of 5 cases, while the human ATE was inside in all 5.

Three conclusions JevFish should adopt directly:

1. Persona richness is nearly worthless for prediction. Spending compute on elaborate ontologies and backstories buys 0.002 accuracy over 14 demographic variables.
2. The expected aggregate level error is about 0.35 human SD. Use that as the benchmark for what good calibration looks like. The KL backtest error of 32.4pp against a roughly 89% actual is far larger than 0.35 SD would predict, which is consistent with the estimand-mismatch diagnosis in `calibration-experiment.md` rather than with ordinary synthetic-sample bias: a well-behaved synthetic crowd answering the right question should be off by roughly a third of a standard deviation, not by 32 points.
3. "Hyper-rationality" is the named distortion that most plausibly drives an over-steep demand curve: a hyper-rational agent shops on price far more than a real traveller does.

### 1.9 Horton, Filippas, Manning, "Homo Silicus" (NBER w31122)

Source: [nber.org/papers/w31122](https://www.nber.org/papers/w31122), [arxiv.org/abs/2301.07543](https://arxiv.org/abs/2301.07543).

Replications of Charness and Rabin (2002), Kahneman, Knetsch and Thaler (1986), Samuelson and Zeckhauser (1988) and others. The paper's own claim is "qualitatively similar results to the original". Qualitative, not quantitative. Useful as evidence that the ordering survives; provides no level calibration.

### 1.10 Aher, Arriaga, Kalai, "Turing Experiments" (ICML 2023)

Source: [arxiv.org/abs/2208.10264](https://arxiv.org/abs/2208.10264), proceedings [proceedings.mlr.press/v202/aher23a.html](https://proceedings.mlr.press/v202/aher23a.html), code [github.com/microsoft/turing-experiments](https://github.com/microsoft/turing-experiments) and [github.com/GatiAher/Using-Large-Language-Models-to-Replicate-Human-Subject-Studies](https://github.com/GatiAher/Using-Large-Language-Models-to-Replicate-Human-Subject-Studies).

Four TEs: Ultimatum Game, Garden Path Sentences, Milgram Shock, Wisdom of Crowds. The first three replicate. The Wisdom of Crowds TE reveals a named failure, "hyper-accuracy distortion": simulated crowds are too accurate, because the model knows the answer. This is a direct warning for a crowd-of-personas estimand: your crowd is not naive about the thing you are asking it to be naive about.

### 1.11 Large-scale replication (Nature Computational Science 2025)

Source: [nature.com/articles/s43588-025-00840-7](https://www.nature.com/articles/s43588-025-00840-7), preprint [arxiv.org/abs/2409.00128](https://arxiv.org/abs/2409.00128), PubMed 40634686.

156 psychological and management experiments, replicated with GPT-4, Claude 3.5 Sonnet and DeepSeek v3.

- Main effect replication rate: 73% to 81%.
- Interaction effect replication: 46% to 63%.
- Effect sizes: Fisher Z values approximately 2 to 3 times higher in LLM studies than in human studies.
- Where original studies reported null findings, LLMs produced significant results 68% to 83% of the time.
- Significantly lower replication for socially sensitive topics (race, gender, ethics).

"Direction right, magnitude 2 to 3 times too large" is the cleanest quantitative statement of the level problem available. It also explains a synthetic elasticity of -3.29 against a benchmark near -0.36: a factor of 9 is worse than 2 to 3 times, but combined with a hyper-rational frame and undifferentiated rivals it is the same mechanism.

### 1.12 Practitioner evidence: Verasight

Source: [verasight.io/reports/synthetic-sampling-2](https://www.verasight.io/reports/synthetic-sampling-2).

1,500 nationally representative US adults on a real panel, compared against GPT-4o and GPT-5 with chain-of-thought, vote history and attitudinal data.

- Generic congressional ballot: best model within 1 percentage point.
- Trump approval: best model within about 4 percentage points; the most heavily enhanced GPT-5 configuration was worse than the baseline.
- Immigration attitudes: 11.3 percentage points error in the best configuration.
- Subgroup MAE on Trump approval alone: more than 10 percentage points.
- Conclusion: loosely approximates frequently asked, polarised toplines; fails on subgroups and on less-canonical questions. More context sometimes made it worse.

The pattern across 1.1 to 1.12 is consistent and should set expectations. On questions the model has effectively memorised the distribution for, error is 1 to 4pp. On novel questions, aggregate level error is roughly 0.35 SD or 10pp and up, and individual-level correlation is about 0.2.

### 1.13 Scaling will not fix it

Source: [arxiv.org/html/2607.02464v1](https://arxiv.org/html/2607.02464v1), "Will Scaling Improve Social Simulation with LLMs?".

- Log-linear scaling laws explain as much as 97% of variance in loss across behavioural simulation, opinion modelling and longitudinal forecasting.
- Improving a behavioural task from 72% to 90% accuracy requires roughly 40 times more compute.
- Longitudinal forecasting hits a ceiling: best model 65%, extrapolated upper bound 77%. "Longitudinal forecasting will not be solved by scaling pre-training compute alone."
- About one third of behavioural tasks show no meaningful scaling, including correlated reward structures and risk-aversion measurement.
- Underrepresented populations scale weakly: r squared from 0.064 (Pakistan) to 0.60 (Canada).
- Fine-tuning Llama3 and Qwen2.5 from 0.5B to 8B produced no statistically significant parameter scaling on the weak-scaling tasks.

Relevant to a Kuala Lumpur crowd specifically: the weak-scaling-for-underrepresented-populations result means a Malaysian traveller population is in the worst regime. Do not expect a bigger or better model to fix the KL backtest.

### 1.14 On the OASIS social-interaction layer

Source: [arxiv.org/pdf/2411.11581](https://arxiv.org/pdf/2411.11581), [github.com/camel-ai/oasis](https://github.com/camel-ai/oasis).

OASIS validation is explicitly about replicating message propagation *trends*, compared on scale, depth and maximum reach, plus qualitative reproduction of information spread, group polarisation and herd effects. There is no published calibration of OASIS output against a measured population level. Adding interaction rounds to JevFish therefore has no evidentiary basis for improving level accuracy, and group polarisation is a documented emergent property of the simulator, which would push shares further from the mean. Treat the interaction layer as a source of additional variance until you have measured it against an anchor.

---

## 2. The level-versus-shape problem: is it named, and what corrects it

### 2.1 It is a known result, but it does not have one canonical name

There is no single accepted term. The literature uses these, and you should adopt the vocabulary rather than invent one:

- **"Pattern correspondence" holding while "overall bias" does not**, from Argyle et al. themselves ([ar5iv.labs.arxiv.org/html/2209.06899](https://ar5iv.labs.arxiv.org/html/2209.06899)).
- **Directional replication with effect-size overestimation**, from the Nature Computational Science replication, Fisher Z 2 to 3 times human ([nature.com/articles/s43588-025-00840-7](https://www.nature.com/articles/s43588-025-00840-7)).
- **Insufficient individuation / under-dispersion**, from the Columbia mega-study, plus aggregate mean offset of 0.352 SD ([arxiv.org/abs/2509.19088](https://arxiv.org/abs/2509.19088)).
- **Covariate shift plus concept shift**, which is the precise statistical decomposition: the LLM's implicit population differs from the target (covariate shift) and the conditional response function differs even at matched demographics (concept shift), plus finite-sample noise ([arxiv.org/html/2604.17267v2](https://arxiv.org/html/2604.17267v2), [arxiv.org/html/2609.13148](https://arxiv.org/html/2609.13148)).
- **Calibration slope versus intercept**, from the diagnostics literature: the slope `beta_g = Cov(Y_real, Y_syn | group) / Var(Y_syn | group)` measures whether shape is preserved, independently of level ([arxiv.org/html/2609.13148](https://arxiv.org/html/2609.13148)).

The covariate-shift/concept-shift decomposition is the one to build on, because it tells you which correction to use. Covariate shift is fixable with weighting alone (post-stratification, propensity weights). Concept shift is not: it needs real outcome labels.

### 2.2 The corrections that exist, with measured effect

**Rectification / prediction-powered inference.** Angelopoulos, Bates, Fannjiang, Jordan, Zrnic, "Prediction-Powered Inference", Science 2023 ([science.org/doi/10.1126/science.adi6000](https://www.science.org/doi/10.1126/science.adi6000), preprint [arxiv.org/abs/2301.09633](https://arxiv.org/abs/2301.09633), PPI++ [arxiv.org/pdf/2311.01453](https://arxiv.org/pdf/2311.01453)). Framework for valid inference when a small labelled dataset is supplemented by a large set of model predictions. The "rectifier" is the empirical bias between labels and predictions on the labelled set; correcting the prediction-based estimate by the rectifier yields provably valid confidence intervals with no assumptions on the predictor. More accurate predictions give narrower intervals. This is the right statistical frame for "JevFish is a prior to be corrected".

**Rectification difficulty and optimal allocation** ([arxiv.org/html/2604.17267v2](https://arxiv.org/html/2604.17267v2)). Defines rectification difficulty `A(lambda) = Var(Y - lambda * Y_LLM)` and gives the PPI++ variance decomposition
`Var(theta_hat(lambda)) = (1/n) Var(Y - lambda Y_LLM) + (lambda^2 / m) Var(Y_tilde_LLM)`
where n is labelled human sample and m the synthetic pool. As m goes to infinity the second term vanishes: a bigger crowd buys you nothing once the pool is large, which matches your own half-width analysis. Their Theorem 1 gives a Neyman-style allocation `n*_q = (B / sum_j sqrt(w_j A_j c_j)) * sqrt(w_q A_q / c_q)`: buy more real data where the LLM is harder to correct, where the question matters more, and where real data is cheaper. Measured MSE reductions: 11.4% on Twin-2K-500, 10.5% on CCES. A meta-learner predicts log difficulty with Spearman 0.73 and captures 61% to 79% of oracle improvements without a pilot.

**Doubly-robust AIPW correction with diagnostics** ([arxiv.org/html/2609.13148](https://arxiv.org/html/2609.13148), "When Can You Trust Your Synthetic Users? Diagnostics and Corrections for LLM Consumer Panels"). The most directly copyable recipe in the literature. Three diagnostics with explicit thresholds:

- Covariate overlap: train a binary classifier separating synthetic from real profiles on demographics, compute effective sample size from density ratio weights. ESS/N > 0.10 adequate, 0.01 to 0.10 marginal, < 0.01 walk away.
- Conditional calibration: `beta_g = Cov(Y_real, Y_syn | g) / Var(Y_syn | g)`. beta_g in [0.5, 1.5] with the same sign means proceed; outside that range or sign-flipped means walk away.
- Cross-LLM stability: rank correlation of subgroup estimates across models. min rho > 0.80 trust, 0.50 to 0.80 flag, < 0.50 walk away.

Correction (their equation 8), doubly robust AIPW with K-fold cross-fitting:
`tau_DR = (1/n) sum_j Y_T_j + (1/N) sum_i w_hat(X_S_i) [ Y_S_i + g_hat(X_S_i) - mu_hat_T(X_S_i) ]`
with `w_hat(x) = p_hat_T(x) / p_hat_S(x)` correcting covariate shift and `g_hat(x)` the concept-shift function estimated from the calibration sample. Consistent if either the outcome model or the propensity model is right.

Measured, on paired data of 172,884 individually matched human and GPT-4.1-mini observations:

| Target | Naive bias | After DR correction | Reduction |
|---|---|---|---|
| ANES, young Democrats | 33.1pp | 0.2pp | 99.5% |
| ANES, older Republicans | 28.8pp | 2.0pp | 92.9% |
| Twin-2K-500 pricing, full sample | 1.0pp | < 0.01pp | 99.2% |
| Twin-2K-500 pricing, high income | 1.9pp | 0.32pp | 83.3% |

Uncorrected calibration slopes on ANES were beta_g in [-0.004, 0.274], that is, shape was also broken, with sign flips (Democratic Party support underestimated by 18.7pp for Democrats but overestimated by +3.0pp for Republicans). On pricing, slopes were beta_g in [0.80, 0.93], the "trust" regime. Their finding that concept shift is task-specific rather than purely demographic is important: pricing behaviour was well calibrated in shape while cognitive-bias tasks were not (conjunction fallacy correlation fell to rho = 0.39, anchoring rho = 0.34 to 0.50).

**Fine-tuning on survey data (SubPOP)** ([arxiv.org/html/2502.16761v2](https://arxiv.org/html/2502.16761v2), code [github.com/JosephJeesungSuh/subpop](https://github.com/JosephJeesungSuh/subpop)). 3,362 questions, 70K subpopulation-response pairs, ATP waves 61 to 132 for training (SubPOP-Train, 3,229 questions) and GSS for evaluation (SubPOP-Eval, 133 questions). Metric is Wasserstein distance over ordinal options. Fine-tuning reduced the LLM-human gap by 32% to 46% on OpinionQA and 39% to 42% on SubPOP-Eval. Llama-3-70B reached WD 0.094 versus 0.138 zero-shot.

**Prompting, fine-tuning and rectification are complementary, and rectification should get most of your budget.** Krsteski, Russo, Chang, West and Gligoric, "Valid Survey Simulations with Limited Human Data: The Roles of Prompting, Fine-Tuning, and Rectification", ACL 2026 ([arxiv.org/abs/2510.11408](https://arxiv.org/abs/2510.11408), ACL [aclanthology.org/2026.acl-long.498](https://aclanthology.org/2026.acl-long.498/), code [github.com/skrsteski/survey-simulations](https://github.com/skrsteski/survey-simulations)). Three longitudinal surveys (NHANES, ATP Q1, ATP Q2), with `n_human = 100`:

| Method | NHANES bias | ATP Q1 | ATP Q2 | Average |
|---|---|---|---|---|
| Baseline, no synthesis | 7.61% | 2.30% | 62.41% | 24.11% |
| Domain fine-tuned, no rectification | 7.03% | 34.27% | 62.69% | **34.66%** |
| Persona-guided, no rectification | 82.08% | 50.22% | 19.99% | **50.76%** |
| SubPOP fine-tuned, no rectification | 180.78% | 44.82% | 33.08% | **86.23%** |
| **Domain fine-tuned + PPI rectification** | 3.33% | 1.73% | 3.40% | **2.82%** |
| **Demographics only + PPI rectification** | 1.75% | 6.75% | 4.52% | **4.34%** |

Read the middle rows: **persona-guided synthesis without rectification was the second-worst method tested, at 50.76% average bias, worse than doing no synthesis at all.** Fine-tuning without rectification was also worse than the baseline. Only rectification helps.

The estimator is PPI: `theta_hat(lambda) = y_bar_pilot + lambda * (y_hat_bar_held - y_hat_bar_pilot)`, with lambda power-tuned to minimise variance. **The selected lambda averaged 0.15 (NHANES), 0.30 (ATP Q1) and 0.05 (ATP Q2)**, meaning the synthetic estimate should carry only **5% to 30% of the weight**. With lambda forced to 1, bias stays in double digits (7.33% to 19.10%) and effective sample size goes **negative**. Allocation under a fixed 1,000-response budget: bias is minimised at **20% to fine-tuning and 80% to correction**.

That is the single cleanest budget instruction in this review. If you have N real outcomes, spend 80% of them on the correction layer, and let the synthetic estimate carry a weight nearer 0.1 than 1.0.

A companion warning: PPI is not free. "Beyond the Mean: Three-Axis Fidelity for Aligning LLM-Based Survey Simulators from Small Pilot Data" ([arxiv.org/html/2606.28963v1](https://arxiv.org/html/2606.28963v1), preprint) found PPI "helps the most biased simulator" but "**pulls already-calibrated simulators away from GT**" and "algebraically degenerates" when the simulator was fine-tuned on the same pilot. The same paper measures structural magnitude distortion from 50% (LoRA compression) to 128% (LoRA plus MLP inflation) while **sign agreement holds at 92%**, and individual fidelity never exceeds **r = 0.37 with MAE 0.61**. A related two-stage "Distribution Shift Alignment" scheme is reported to reduce required real-data volume by 53% to 69% ([arxiv.org/html/2604.17267v2](https://arxiv.org/html/2604.17267v2)).

**Learning the bias-correction map directly, with econometrics downstream.** Zhang, Li, Hortacsu, Ye, Chernozhukov, Ni, Huang, "Agentic Economic Modeling" ([arxiv.org/abs/2510.25743](https://arxiv.org/abs/2510.25743)). They learn a map from task features and raw LLM choices to human-aligned choices, then run standard econometrics on the corrected choices. Change in MAPE versus the primary-data estimate: **raw LLM choices +0.11 (worse), naive -8.42, tuned -16.52, pre-trained -16.63**, using only **10% of the original data** to fit the correction. Verbatim: "Directly using LLM generated choices even increases the bias, highlighting the necessity of bias correction." Their regional field-experiment validation: mixture model -65 (SE 10) bps against the full human experiment's -60 (SE 8) bps, with a black-box integrated model at only -39 (SE 9) bps.

### 2.2b The fitted slope, measured: synthetic spread is two to four times too wide

The only published numbers that pair a rank correlation with a level error and a fitted affine correction, which is exactly the statistic JevFish needs:

**The Korean media-panel validation** ([arxiv.org/html/2608.28615](https://arxiv.org/html/2608.28615), preprint) states the level-versus-shape result verbatim: "**the models ranked behaviors roughly correctly but misestimated their levels**". Against the nationally representative KISDI Media Panel Survey: mean absolute error **15 to 19 percentage points**, binary item correlations **0.69 to 0.90**, between-group error gap 52.4pp (Gemini) and 36.2pp (EXAONE). Gemini anchored low, EXAONE showed acquiescent upward bias. An **age-regression correction halved within-wave sex-by-age cell error, 18.9 to 8.6pp (Gemini) and 15.9 to 6.7pp (EXAONE)**, but "**correction did not transfer across waves**", and direct estimation from 30% real data beat everything at 3.6pp. Two lessons: a fitted correction halves the error, and it is not durable, so refit it every period.

**"Tastes without distinction"** ([arxiv.org/html/2606.30085](https://arxiv.org/html/2606.30085), preprint), 554,940 silicon responses against 9,249 real 2012 SPPA respondents across 17 music genres. Level errors are enormous and one-directional: folk **+63.61pp (OpenAI)**, gospel +62.16pp (DeepSeek), blues +61.49pp, with the largest underestimate only -9.15pp. The omnivorousness index is inflated by +21.71 / +21.96 / +15.59pp against a real 24.18%. Across 136 genre pairs, silicon and real Cramer's V were "essentially uncorrelated (Pearson's r = 0.06)". Derived from their Table 1 (this is a calculation from the published table, in-sample, n = 17, not a published result: FLAG): Spearman rho **0.755 / 0.779 / 0.831** with mean absolute level error **24.77 / 23.49 / 17.90pp**, and an OLS affine refit cuts that to **5.61 / 5.72 / 4.55pp** with fitted **slope 0.259 / 0.283 / 0.354**. So the silicon spread is roughly three to four times too wide and the correction is mostly a severe shrink plus a large negative shift. Worst residual after correction stays at 13 to 15pp.

Compare that with the doubly-robust consumer-panel paper's slopes: **beta_g in [0.80, 0.93]** on full-sample pricing, collapsing to **[0.21, 0.28]** for high-income targeting ([arxiv.org/html/2609.13148](https://arxiv.org/html/2609.13148)). The pattern across all of these is that the fitted slope is below 1 and how far below depends on the task and the subgroup, which is exactly why `b` must be fitted per question family rather than assumed.

That paper also reports doubly-robust correction achieving **more than 87% bias reduction at n of about 100**, specifically 99.2% full-sample, 83.3% high-income and 94.0% young consumers, with n in the 50 to 300 range, and it warns explicitly that "**global corrections ... worsen demographic bias**" with subgroup error ballooning by 10 to 30 percentage points. A single global constant is not an acceptable calibration layer.

### 2.2c Four deflationary results to read before trusting any persona crowd

- **Argyle et al. threw the level away.** The paper usually cited as proof that silicon samples work states: "We dichotomize the GPT-3 vote probability to match our human measure." Every number in its Table 1 is an association measure, and Independents score tetrachoric **0.31 / 0.41 / 0.02** across 2012, 2016 and 2020. Its correction is post-stratification by construction (sample backstories from a representative frame, compute `P(V|B)P(B)`), which fixes only demographic skew, and only "as long as GPT-3 models the conditional distribution P(V|B) well" ([arxiv.org/abs/2209.06899](https://arxiv.org/abs/2209.06899)).
- **A plain statistical baseline beats every LLM on distribution fidelity.** "Plausible but Not Valid" ([arxiv.org/html/2608.14606](https://arxiv.org/html/2608.14606), preprint), 37 models against n = 263 humans: a Gaussian copula baseline beat every LLM on both distribution fidelity (**d = 0.95** versus the best LLM's 0.589) and inter-item correlation (**0.95** versus 0.52). Their stated dominant failure mode is "**range restriction** (the LLM picks a narrower band of the scale than humans do)", which is JevFish's 0.35-to-0.72 range in one sentence.
- **A handful of real people beats the synthetic crowd.** "Synthetic social data: trials and tribulations" ([arxiv.org/abs/2510.19952](https://arxiv.org/abs/2510.19952)), 6 LLMs, 4 countries, 15 WVS questions: **94.4% of LLM-generated responses were statistically different (p <= 0.05) from the human benchmark**, and a random sample of real humans beat the synthetic mean at recovering the true population mean **47.5% of the time at N = 1, 60.8% at N = 2, 86% at N = 16, 97.6% at N = 128**. Sixteen real respondents beat 800 synthetic ones 86% of the time.
- **Internal consistency proves nothing about level accuracy.** "Calibrating the Instrument" ([arxiv.org/abs/2607.00910](https://arxiv.org/abs/2607.00910)) passes all seven preregistered ordering criteria at every temperature while explicitly asking "not whether a synthetic population tracks humans, but whether it tracks itself". A clean ordering result of that shape carries zero information about level accuracy. JevFish's "the shape was credible" finding is in this category until it is scored against more than one anchor.
- **Association structure is inflated, not just levels.** "Overstating Attitudes, Ignoring Networks" ([arxiv.org/abs/2602.04674](https://arxiv.org/abs/2602.04674), preprint): ground-truth Spearman rho between misinformation belief and sharing of **.606 / .418 / .342** across three surveys becomes **.925 / .956 / .749** when simulated; cross-validated out-of-sample R-squared goes from human .042 to .228 up to simulated .580 to .874, "often by an order of magnitude", producing "deterministic mappings uncharacteristic of human belief or behavior".
- **Mode collapse is the default, and the standard fix overshoots.** "Distribution-First Population Simulation" ([arxiv.org/html/2607.18310v1](https://arxiv.org/html/2607.18310v1), preprint), 2,414 real WVS-7 Turkey respondents: the independent-agent route versus a verbalized-sampling route gives **TVD = 0.437 [0.383, 0.498]**, modal concentration 0.358 versus 0.685, entropy 1.464 versus 0.770, with **collapse in 85% of units**. Verbalized sampling recovers +6.8 to +10.1 points but overshoots: the SD ratio moves from 0.40 to 0.56 up to 1.26 to 1.37.

A useful taxonomy for writing this up internally: "Total Simulated Survey Error" ([arxiv.org/html/2609.10280](https://arxiv.org/html/2609.10280), preprint) names seven error sources (specification, articulation, persona-construction, response-generation, persona-simulation, response-processing, adjustment) and three fallacies (ground truth, single best metric, context drift). Their 2024 ANES case study spans **weighted TVD 0.097 for the best configuration to 0.489 for the worst**, and F1 0.686 to 0.308. Design choices dominate the result, which is another way of saying the frame matters more than the crowd.

### 2.3 The cause of your elasticity error is probably the frame, not the crowd

Gui and Toubia, "The Challenge of Using LLMs to Simulate Human Behavior: A Causal Inference Perspective" ([arxiv.org/html/2312.15524v1](https://arxiv.org/html/2312.15524v1), SSRN 4650172) is the single most relevant paper to a price-elasticity backtest.

The mechanism: in a real experiment you assign a treatment to pre-existing units. In an LLM simulation the model generates the unit *from the prompt, including the treatment*. So varying the price in the prompt also varies the unspecified confounders the model imagines: competitor prices, historical prices, season, even weather. This is endogeneity by construction.

Measured:

- Naive prompting: Coca-Cola 12-pack elasticity 0.15; average across 40 product categories 0.14. Literature benchmark 1.8 to 3.0. Implausibly flat.
- When the focal price was varied from -60% to +60% without experimental framing, the LLM's stated Pepsi price moved systematically with it. The confounder is observable.
- After explicitly stating the variation is experimental ("the price of the product is set randomly by the store"): average elasticity 1.38 across 40 categories, approaching the literature range.
- Caveat the authors state: even with experimental framing you identify only a conditional average treatment effect specific to the experimental design you described, not a universal ATE, and results remain sensitive to the stated experimental range.

For JevFish this explains both halves of your synthetic result. Writing the rival options as interchangeable told the model it was in a commodity market, producing elasticity -3.29. Differentiating the rivals told it there was product differentiation, producing -1.93. Neither prompt told it the price variation was exogenous. The published fix is a sentence in the frame, and it moved a real measured elasticity by an order of magnitude.

Related: Goli and Singh, "Can LLMs Capture Human Preferences?" (Frontiers: Marketing Science 43, 709 to 722; [arxiv.org/abs/2305.02531](https://arxiv.org/abs/2305.02531)) find GPT-3.5 and GPT-4 both less patient than humans, with GPT-3.5 showing a lexicographic preference for earlier rewards that no human decision-maker has, and GPT-4's discount rates still considerably larger than human estimates. Their mitigation, "chain-of-thought conjoint" (prompting the model to explain its decisions), reduces but does not eliminate the gap. Same shape: monotone bias in a structural parameter, partially fixable by prompt.

### 2.4 Post-stratification of a wildly non-representative sample: the existence proof

Wang, Rothschild, Goel, Gelman, "Forecasting elections with non-representative polls", International Journal of Forecasting 2015 ([5harad.com/papers/forecasting-with-nonrepresentative-polls.pdf](https://5harad.com/papers/forecasting-with-nonrepresentative-polls.pdf), [sciencedirect.com](https://www.sciencedirect.com/science/article/abs/pii/S0169207014000879)).

- Sample: 750,148 interviews from 345,858 unique Xbox respondents over the 45 days before the 2012 US election. Over 30,000 respondents completed five or more polls.
- Skew: 93% male versus 47% of the electorate; 65% aged 18 to 29 versus 19%.
- Raw, unadjusted: the Xbox sample indicated a landslide for Romney. The authors compare it explicitly to the Literary Digest error.
- Model: multilevel logistic regression, partitioned into 176,256 post-stratification cells including political variables (party ID, 2008 vote), post-stratified onto 2008 exit poll summaries (101,638 respondents), deliberately using 2008 rather than 2012 so the method would have been available in real time.
- Result: the day-before-election national estimate was off the actual outcome by 0.6 percentage points. Across the 51 Electoral College races, mean and median absolute deviation from Pollster.com estimates were 2.5 and 1.8 percentage points. Demographic subgroup estimates versus exit polls differed by a median of 1.9 and mean of 2.2 percentage points.

This is the proof of concept for JevFish's entire premise: a sample that is catastrophically wrong in level can be recovered to sub-percentage-point accuracy by post-stratifying onto a correct population frame, provided the model includes the variables that actually predict the outcome. Note what made it work: political variables in the cells, and a real post-stratification frame. JevFish samples personas to match a population but does not, as far as the pipeline description goes, re-weight the *responses* onto a frame after the fact, and does not include outcome-predictive variables in the cells.

---

## 3. Concrete calibration techniques, with enough maths to code

### 3.1 Platt scaling

Canonical description in Niculescu-Mizil and Caruana, "Obtaining Calibrated Probabilities from Boosting" ([cs.cornell.edu/~caruana/niculescu.scldbst.crc.rev4.pdf](https://www.cs.cornell.edu/~caruana/niculescu.scldbst.crc.rev4.pdf), [arxiv.org/abs/1207.1403](https://arxiv.org/abs/1207.1403)) and Platt (1999).

Fit a two-parameter sigmoid on the raw score f:

```
p(f) = 1 / (1 + exp(A*f + B))
```

by minimising log loss on a held-out calibration set:

```
argmin_{A,B} -sum_i [ y_i log p_i + (1 - y_i) log(1 - p_i) ]
```

Two implementation details that matter and are usually omitted:

- Use an independent calibration set, or C-fold cross-validation with the union of the C validation sets used to fit A and B. Fitting on the training scores biases the sigmoid. The paper uses 3-fold.
- Use smoothed targets rather than 0 and 1 to avoid overfitting. With N+ positives and N- negatives in the calibration set:

```
y+ = (N+ + 1) / (N+ + 2)
y- = 1 / (N- + 2)
```

Inputs needed: a raw per-option score per persona (Jev already returns a calibrated-ish probability, use its logit) plus a set of realised binary outcomes.

Applicability to JevFish: Platt scaling is the right tool at the *persona-vote* level, mapping each Jev probability to a calibrated probability, if you have per-persona ground truth. You do not. What you have is aggregate ground truth, which takes you to 3.3.

### 3.2 Isotonic regression and beta calibration

Isotonic regression fits any monotone m minimising squared error:

```
m_hat = argmin_{m isotonic} sum_i (y_i - m(f_i))^2
```
solved by pool-adjacent-violators. Non-parametric, so more flexible than Platt but higher variance and, critically, it can only output values it has seen, so it cannot extrapolate beyond the range of your calibration set. With a handful of anchors it will produce a step function.

Beta calibration (Kull, Silva Filho, Flach, AISTATS 2017; [proceedings.mlr.press/v54/kull17a/kull17a.pdf](https://proceedings.mlr.press/v54/kull17a/kull17a.pdf)) is the better middle ground:

```
g(s; a, b, c) = 1 / (1 + exp( -(a * ln(s) - b * ln(1 - s) + c) ))
```

Three parameters. It assumes two Beta distributions rather than two equal-variance Gaussians, handles non-sigmoidal calibration maps, and crucially contains the identity map as a special case (a = b = 1, c = 0), so it does not force an S-curve onto an already-calibrated model. Platt always biases toward an S-curve. Fit by logistic regression on the two features `ln(s)` and `-ln(1-s)`.

On data requirements, from the learning curve analysis in Niculescu-Mizil and Caruana, "Predicting Good Probabilities With Supervised Learning" (ICML 2005), Section 5 ([cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf](https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf), [dl.acm.org/doi/10.1145/1102351.1102430](https://dl.acm.org/doi/10.1145/1102351.1102430)). They varied the calibration set from 32 to 8,192 cases by factors of two across nine learning methods and eight problems, and state directly: "When the calibration set is small (less than about 200-1000 cases), Platt Scaling outperforms Isotonic Regression with all nine learning methods." The reason given is that isotonic is less constrained and therefore easier to overfit, though Platt's method also overfits somewhat at small sizes. So the threshold is **200 to 1,000 calibration cases**, below which use Platt and above which isotonic can win.

Practical guidance for JevFish: with fewer than about 50 anchors use the two-parameter logit-affine map in 3.3. With a few hundred, beta calibration. Isotonic only once you have thousands.

Two independent confirmations that Platt beats the alternatives on this specific failure shape. Bridgewater's AIA Forecaster measured Platt at 0.1071 in-distribution and 0.1104 out, against isotonic at 0.1097 and 0.1134 and OLS at 0.1119 and 0.1125 ([arxiv.org/abs/2511.07678](https://arxiv.org/abs/2511.07678), Table 11). And "Wired for Overconfidence" ([arxiv.org/abs/2604.01457](https://arxiv.org/abs/2604.01457), COLM 2026, Appendix I Table 7) fitted four calibrators on a labelled half-split of verbalised confidence scores and evaluated on the disjoint half: Platt won 3 of 4 settings, cutting 10-bin ECE by **85% to 99%** (for example 0.568 to 0.008 on Llama-3.2-3B / PopQA), while **single-temperature scaling was the weakest parametric method on the three high-ECE rows** (only 47% to 52% reductions) and histogram binning actively hurt on MMLU. Their explanation applies directly: a score concentrated on two or three values has no single temperature that spreads it. JevFish returns about 30 distinct values across 801 personas, so it is squarely in that regime, and the two-parameter Platt map is the right choice over one-parameter temperature scaling.

On data efficiency, the largest study of verbalised-confidence recalibration (9 LLMs, 13 BLURB datasets, [JAMIA Open 8(4):ooaf058](https://academic.oup.com/jamiaopen/article/8/4/ooaf058/8196848)) found histogram binning and isotonic regression each cut average Flex-ECE by **23.5 and 23.6 percentage points** with 1,000 calibration examples, and "**as few as 100 examples proved sufficient** to provide a large and consistent reduction", over 75% on average.

### 3.3 Anchoring / affine recalibration in logit space: the one to build first

This is the technique with the strongest direct evidence for exactly your problem, from "LLM-Powered Virtual Population for Demand Simulation and Pricing" ([arxiv.org/html/2606.16183v1](https://arxiv.org/html/2606.16183v1)).

Their setup is a near-twin of JevFish: customers modelled as draws from a finite mixture of K = 50 personas plus one inactive persona; GPT-5-mini generates a purchase probability per persona-product-price triple from persona demographics plus product description, image and price; persona probabilities aggregate into a binomial demand distribution. Domain: H&M fashion dataset, September 2018 to 2020, 100 trouser products with observed price variation and transactions.

The calibration map is a monotone logit-scale transform:

```
T_{a,b}(q) = sigmoid( a + b * logit(q) ),    b > 0
```

where q is the raw LLM probability, `a` shifts the overall level and `b` scales the strength. The authors state plainly that it "corrects the scale of the probabilities without discarding their ordinal information". That is exactly the level-versus-shape separation you need: b preserves and rescales the shape, a fixes the level.

Fitting: maximum likelihood on truncated historical data (only positive demand is observed), jointly estimating the persona mixture weights alpha, the exposure parameter N, and (a, b) against a truncated likelihood objective.

Measured results:

| Metric | LLM calibrated | Embedding baseline |
|---|---|---|
| CRPS | 0.94 | 0.99 |
| KS-PIT | 0.30 | 0.32 |
| MAE | 1.38 units | 1.44 units |
| RMSE | 1.79 units | 1.86 units |

And the number that matters for a small operator: with only 2.5% of training data, about 73 samples, roughly 3 per product, the model achieved 90% of optimal expected revenue and 87% for the CVaR at 0.25 objective.

How few anchors can work. The honest answer from the literature:

- 3 observations per option, 73 total, was enough to get to 90% of optimal revenue in the paper above.
- Two parameters (a, b) are identified from 2 distinct anchor points in principle, and estimable with reasonable variance from perhaps 5 to 10. With k = 2 you get a point fit and no residual estimate. With k >= 5 you can hold one out.
- PPI-style rectification with a single-parameter shift (a only, b fixed at 1) is identified from 1 anchor and is the correct thing to do when you have one.
- Conformal intervals need 9 anchors for 90% coverage (see 3.5).

So the practical schedule is: 1 anchor buys you a level shift; about 5 buys you level plus scale; about 9 to 10 buys you honest intervals; about 70 buys you near-optimal decisions.

Four warnings.

1. A logit-affine map on the *aggregate share* is not the same as a map on each persona probability, and the two are not interchangeable because sigmoid is non-linear. The H&M paper calibrates persona-level probabilities before aggregation. Do the same: calibrate `q_persona`, then aggregate.
2. `b` fitted on a narrow price range does not extrapolate. The Gui and Toubia range-sensitivity caveat applies.
3. **The map only helps if the raw estimate is already on the correct side of the decision boundary.** Bridgewater's AIA Forecaster states this as a hard constraint: "post hoc calibration only helps when initial judgments are already on the correct side of 0.5" ([arxiv.org/abs/2511.07678](https://arxiv.org/abs/2511.07678), Appendix G.2). No monotone map crosses a boundary.
4. **The fit is not durable.** Refit it whenever the model, the prompt or the period changes. Three independent measurements of this: the Korean panel study's correction "did not transfer across waves" ([arxiv.org/html/2608.28615](https://arxiv.org/html/2608.28615)); a Metaculus bot-maker who implemented exactly this transform found the **binary slope drifting from 0.83 in spring 2026 to 1.66 in fall 2025**, "opposite calibration shapes between rounds", and shipped it as the identity rather than risk it ([github.com/No-Stream/metaculus-bot](https://github.com/No-Stream/metaculus-bot)); and Bisbee et al. found prompt distributions shifting across a three-month gap. Cap the permitted deviation (the same bot uses `MAX_ABS_DEVIATION = 0.10`) and re-fit on a rolling window.

A useful default when you have no anchors at all: AIA Forecaster's **fixed** coefficient version essentially matched their learned one (0.1076 versus 0.1071 Brier) using **alpha = sqrt(3), about 1.732**, from Neyman and Roughgarden, deliberately chosen "to avoid the risk of overfitting", and it transferred across benchmarks (0.1104 versus 0.1140 with no fitting at all). So `sigmoid(1.732 * logit(p))` is a defensible zero-anchor starting point for the slope, with `a = 0` until you have a level anchor. Note the direction: that fixed alpha above 1 *sharpens*, which is right for a hedging forecaster and wrong for an over-dispersed one. JevFish's measured `b` on share-type outcomes should be expected **below** 1 (the fitted slopes in section 2.2b are 0.26 to 0.93), so do not import 1.732 without checking the sign of your own error.

### 3.4 Post-stratification and MRP on synthetic respondents

**Plain post-stratification.** Partition the population into cells j = 1..J on the variables that predict the outcome. Let `N_j` be the population count in cell j from a real frame, and `theta_hat_j` your synthetic estimate in cell j. Then

```
theta_hat = sum_j (N_j / N) * theta_hat_j
```

Needs: a real population frame with cell counts, and enough personas per cell. Fixes covariate shift only. If your personas are already sampled to match the population, this is a no-op on the margins you matched and still corrects any margin you did not match.

**MRP.** Replace the raw cell estimate with a multilevel model estimate, so sparse cells borrow strength from similar cells:

```
Pr(y_i = 1) = logistic( alpha + a_{age[i]} + a_{race[i]} + a_{income[i]} + ... + a_{region[i]} + beta * X_state )
a_k ~ Normal(0, sigma_k^2)   for each grouping k
```
then post-stratify the fitted cell probabilities onto `N_j`.

Evidence on how much this buys, and at what sample size. Lax and Phillips, "How Should We Estimate Public Opinion in the States?", AJPS 2009 ([columbia.edu/~jhp2121/publications/HowShouldWeEstimateOpinion.pdf](http://www.columbia.edu/~jhp2121/publications/HowShouldWeEstimateOpinion.pdf)):

- Design: 26 national polls on gay rights, 1996 to 2005. Half the data defines the baseline "true" state opinion; 200 random draws at each of four sample sizes (approximately N = 1,400 at 5%, 2,800 at 10%, 7,000 at 25%, 14,000 at 50%), 800 simulation runs total.
- Mean absolute error: MRP ranges from 4 to 5 percentage points across all sample sizes. Disaggregation ranges from 4 to 11. MRP at the 5% sample was nearly as accurate as disaggregation at the 50% sample, which the authors describe as "like getting 12,000 or more observations free".
- Stability: MRP's mean standard deviation across simulations was approximately one quarter to one third that of disaggregation. Reliability and stability coefficients were 0.99 and 0.99 for MRP versus 0.91 and 0.90 for disaggregation.
- Out-of-sample validation against actual 2004 Bush vote shares: mean absolute errors (MRP, disaggregation) were (5.0, 12.8) at the 10% sample, (4.3, 8.6) at 25%, (3.9, 6.5) at 50%. Correlations (0.52, 0.37), (0.63, 0.50), (0.72, 0.64). Using the full survey set: MRP MAE 3.5 versus 5.2, a 32% reduction, correlations 0.78 versus 0.74, MRP better in 34 of 48 states.
- MRP had the lower MAE in 100% of simulated data sets.

Direct read-across to JevFish's resolution problem: your half-width formula `1.645 * sqrt(2 p (1-p) / n)` is the disaggregation variance. Model-based smoothing across cells is how the polling literature gets a 10x effective sample size increase without more respondents. A crowd of n = 48 post-stratified through a multilevel model over, say, 6 cells has materially better effective resolution than n = 48 disaggregated, and is far cheaper than running n = 800.

Caveat: MRP accuracy depends critically on including outcome-predictive covariates. Lauderdale et al. (2020) conclude careful model specification is essential ([bookdown.org/jl5522/MRP-case-studies/introduction-to-mrp.html](https://bookdown.org/jl5522/MRP-case-studies/introduction-to-mrp.html) for the survey of this literature; auxiliary-variable guidance at [arxiv.org/pdf/2011.00360](https://arxiv.org/pdf/2011.00360)). For a room-rate question the analogue of "party ID" is prior booking behaviour, lead time and channel, not age and gender.

### 3.5 Conformal prediction for a share estimand

The estimand is a proportion `p in [0,1]`, predicted as `p_hat`. The variant that fits is **split conformal on your own historical absolute errors**, which requires no distributional assumption about how JevFish fails.

Procedure:

1. Hold a calibration set of k past questions with known outcomes. Compute non-conformity scores `s_i = |p_actual_i - p_hat_i|`.
2. For a target miscoverage alpha, take `q_hat` = the `ceil((k+1)(1-alpha))`-th smallest score.
3. Report `[p_hat - q_hat, p_hat + q_hat]`, clipped to [0,1].

Coverage is at least `1 - alpha` in finite samples under exchangeability, with no assumption on the predictor. The feasibility condition is `ceil((1-alpha)(k+1)) <= k`, equivalently `k >= (1-alpha)/alpha = 1/alpha - 1` ([arxiv.org/pdf/2303.02770](https://arxiv.org/pdf/2303.02770) on the universal distribution of empirical coverage, and [stat.cmu.edu/~ryantibs/papers/conformal.pdf](https://www.stat.cmu.edu/~ryantibs/papers/conformal.pdf) for the split conformal construction). So:

- 80% coverage: k >= 4 anchors.
- 90% coverage: k >= 9 anchors.
- 95% coverage: k >= 19 anchors.

Refinements worth knowing:

- **Conformalized quantile regression** (Romano, Patterson, Candes) gives adaptive width when you have a covariate that predicts error size (for example, "is this question close to the model's training distribution"). Needs more calibration data.
- **Normalised scores**: `s_i = |p_actual - p_hat| / sigma_hat_i` where `sigma_hat_i` is your binomial half-width from crowd size. This makes the interval widen automatically for small crowds and is a one-line change.
- Coverage is marginal, not conditional. A conformal interval that covers 90% of all questions can systematically under-cover a subclass, and there is no distribution-free fix ([dl.acm.org/doi/10.1145/3736575](https://dl.acm.org/doi/10.1145/3736575)).

The honest position: with fewer than 9 anchors you cannot claim a calibrated 90% interval. You can still report the binomial half-width, but you must label it as "sampling noise only, excludes model bias", because your measured bias of 32.4pp is roughly twice the sampling half-width at n = 48.

### 3.6 Ensembling and extremising

**The formula.** Baron, Mellers, Tetlock, Stone, Ungar, "Two Reasons to Make Aggregated Probability Forecasts More Extreme", Decision Analysis 11(2), 133 to 145, 2014 ([faculty.wharton.upenn.edu PDF](https://faculty.wharton.upenn.edu/wp-content/uploads/2015/07/2015---two-reasons-to-make-aggregated-probability-forecasts_1.pdf), doi [10.1287/deca.2014.0293](https://pubsonline.informs.org/doi/10.1287/deca.2014.0293)):

```
t(p) = p^a / ( p^a + (1 - p)^a ),   a > 1
```

which is exactly multiplication of the log-odds by a:

```
logit(t(p)) = a * logit(p)
```

Figure 1 in the paper illustrates a = 2.5. The transformation traces to Karmarkar (1978) and has been used by Erev et al. (1994) and Shlomi and Wallsten (2010).

**The two reasons.** First, random error compresses the probability scale at both ends, pushing the mean toward 0.5. This affects the mean but not the median, nor (arguably) the mean of log odds. Second, forecasters each see only part of the available information, so the aggregate should be more confident than any individual. This affects mean, median and mean-of-log-odds alike.

**The measured parameter and gain**, from Good Judgment Project year-1 data, 86 questions, two-option questions only (Table 1):

| Expertise | Method | optimal a | Brier at optimal a | Brier at a = 1 |
|---|---|---|---|---|
| High | Mean | 2.43 (se 0.05) | 0.148 | 0.187 |
| High | Median | 1.78 (se 0.03) | 0.160 | 0.176 |
| Low | Mean | 3.08 (se 0.09) | 0.139 | 0.196 |
| Low | Median | 2.34 (se 0.06) | 0.153 | 0.184 |

Extremising the expert mean cut Brier from 0.187 to 0.148, a 21% reduction. For non-experts, 0.196 to 0.139, a 29% reduction. Note that the noisier the forecasters, the larger the optimal a, which is the opposite of the naive intuition and directly relevant to a crowd of weak persona votes.

**The caveat the paper states.** Extremising a forecast that is on the wrong side of 0.5 makes things worse; if the aggregate is on the wrong side, extremising is insufficient to fix it. The authors also note that with few forecasts the median can be noisier, and that the amount of extremising should depend on information overlap among forecasters.

**Information overlap.** Satopaa and Ungar and co-authors formalise this: the optimal amount of extremising varies with how much information forecasters share ([arxiv.org/abs/1501.06943](https://arxiv.org/abs/1501.06943), [arxiv.org/abs/1506.06405](https://arxiv.org/abs/1506.06405)). Their estimated Brier-minimising range for a was [1.161, 3.921]. This is a serious problem for a persona crowd: N personas generated by one LLM from one frame have near-total information overlap, so the second reason to extremise (information pooling) largely does not apply and the optimal a should be much closer to 1 than the 2.4 to 3.1 found for independent humans. Extremising a persona crowd as if it were 800 independent forecasters would be a mistake.

**Pooling rules.**

- Arithmetic mean (linear opinion pool): `p_bar = (1/N) sum p_i`. Matches the Brier quadratic scoring rule.
- Geometric mean of odds (logarithmic opinion pool): `odds_bar = prod_i (p_i / (1-p_i))^{1/N}`, then `p = odds_bar / (1 + odds_bar)`. Matches the log scoring rule.
- Extremised geometric mean of odds: raise the pooled odds to the power d.
- Vincentization (quantile averaging), from S. B. Vincent 1912: average the quantile functions rather than the densities, that is, average the CDFs horizontally rather than vertically. The Vincentized distribution has mean, variance and shape approximately equal to the average mean, variance and shape of the components, which is why it does not collapse dispersion the way linear pooling does. Reference: Busetti, "Quantile Aggregation of Density Forecasts", Oxford Bulletin of Economics and Statistics 2017 ([fabiobusetti.altervista.org PDF](http://fabiobusetti.altervista.org/Busetti_Quantile_aggregation_september_2015.pdf), [onlinelibrary.wiley.com](https://onlinelibrary.wiley.com/doi/abs/10.1111/obes.12163)).

Empirical comparison: Satopaa et al. report their extremised geometric-mean-of-odds estimator beating the mean, the median, the logarithmic opinion pool and a beta-transformed linear opinion pool on Brier, on 1,300 forecasters over 69 geopolitical questions ([forum.effectivealtruism.org/posts/sMjcjnnpoAQCcedL2](https://forum.effectivealtruism.org/posts/sMjcjnnpoAQCcedL2/when-pooling-forecasts-use-the-geometric-mean-of-odds) summarises; primary is [arxiv.org/abs/1501.06943](https://arxiv.org/abs/1501.06943)). The same summary notes that on Metaculus data the optimally extremised mean of probabilities and the optimally extremised mean of log odds gave identical Brier scores, with log odds winning only where extreme forecasts were involved. Conclusion: the extremising parameter matters more than the choice of pool.

For JevFish's estimand specifically: your output is a share over K options, not a probability of a binary event. The multi-option generalisation of extremising is to raise each option's aggregate share to the power a and renormalise:

```
s_k' = s_k^a / sum_j s_j^a
```

This is a temperature-scaled softmax over log-shares and is the standard multi-class analogue. It has, as far as I could find, no direct empirical validation in the forecasting literature: **NOT VERIFIED** for K > 2. Fit a on your own anchors rather than importing 2.5.

### 3.7 Debiasing known LLM response biases

**Option order / label position.** Established magnitudes:

- Moving the correct answer to position D degraded gpt-3.5-turbo accuracy by 6.3 percentage points (67.2 to 60.9) ([arxiv.org/abs/2309.03882](https://arxiv.org/abs/2309.03882), Zheng et al., "Large Language Models Are Not Robust Multiple Choice Selectors").
- Accuracy drops of 10.5% to 42.9% observed when shuffling option positions across models, and performance fluctuations of 13% to 85% across orderings have been reported ([researchgate.net summary of Pezeshkpour and Hruschka](https://www.researchgate.net/publication/382633315_Large_Language_Models_Sensitivity_to_The_Order_of_Options_in_Multiple-Choice_Questions), [arxiv.org/pdf/2406.19470](https://arxiv.org/pdf/2406.19470) on MMLU).
- Zheng et al. attribute the bias to token-level priors on option IDs and propose PriDe, which estimates the prior by permuting option contents on a small number of samples and then debiases the rest cheaply.
- Dominguez-Olmedo et al. show that after randomised choice ordering, 43 models across the size range trend toward uniform survey answering, meaning the pre-adjustment signal was largely position artefact ([arxiv.org/html/2306.07951v4](https://arxiv.org/html/2306.07951v4)).

Implementation for JevFish: for K options, either average over all K! permutations (feasible at K = 5: 120 permutations, or use a Latin square of K orderings for a K-fold cost), or implement PriDe by permuting on a subsample to estimate the position prior and then subtracting it. Expected effect: eliminates a bias that the literature measures at 6 to 40 accuracy points on MCQ, and which is large enough to have invalidated a whole sub-literature. This is the highest-confidence, lowest-cost fix available.

**Acquiescence and refusal.** Humans over-agree; LLMs do not, and in the one direct test they over-refuse ([arxiv.org/pdf/2509.08480](https://arxiv.org/pdf/2509.08480)). Tjuatja et al. find models generally fail to show human response biases, with RLHF models worst ([aclanthology.org/2024.tacl-1.56](https://aclanthology.org/2024.tacl-1.56/)). Implication: do not include a "neither / would not book" option unless you calibrate it separately; its share is a model artefact.

**Under-dispersion.** Documented repeatedly: Bisbee et al. (far smaller synthetic SDs than ANES, even at temperature 1.0), the Columbia mega-study (SD ratio below 1, named "insufficient individuation"). Temperature raises variance (Bisbee's SI Section 2 shows a strong positive association between temperature and empirical variance) but temperature-induced variance is not the same object as population heterogeneity. The correct fix is to fit the dispersion, that is, the `b` parameter in 3.3, against real outcomes, not to turn up the temperature.

**Hyper-rationality and hyper-accuracy.** Aher et al.'s "hyper-accuracy distortion" ([arxiv.org/abs/2208.10264](https://arxiv.org/abs/2208.10264)) and the Columbia study's "hyper-rationality" ([arxiv.org/abs/2509.19088](https://arxiv.org/abs/2509.19088)) are the same failure: simulated agents are better informed and more normatively rational than real people. For a price question this biases toward over-shopping and therefore over-steep elasticity. There is no published prompt fix with a measured effect size; the only measured correction is the frame fix in Gui and Toubia (2.3) and post-hoc recalibration.

**Prompt and version instability.** Bisbee et al. document that the same prompt gives significantly different distributions three months later, and across ChatGPT versions. Practical consequence: pin the model version and treat any recalibration `(a, b)` as version-specific. Re-fit when you change model.

---

## 4. Scoring and evaluation

### 4.1 Which rules are proper

A scoring rule is proper if the forecaster maximises expected score by reporting their true belief, strictly proper if that maximum is unique. Canonical reference: Gneiting and Raftery, "Strictly Proper Scoring Rules, Prediction, and Estimation", JASA 2007 ([sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)).

Proper and strictly proper:

- **Brier score** for a binary or categorical event. Multi-category form: `BS = (1/N) sum_n sum_k (p_nk - o_nk)^2`, where `o_nk` is 1 if k occurred. Strictly proper. Bounded.
- **Log score** `-log p_actual`. Strictly proper. Unbounded, so a single confident miss dominates. Matches logarithmic pooling.
- **CRPS** for a full predictive distribution over a real-valued or ordinal outcome: `CRPS(F, y) = integral (F(z) - 1{y <= z})^2 dz`. Strictly proper for distributions with finite first moment. Generalises absolute error to distributions, and is the integral of the Brier score over thresholds. Reference [cran.r-project.org/web/packages/scoringRules](https://cran.r-project.org/web/packages/scoringRules/vignettes/article.pdf).
- **Ranked probability score (RPS)**, the discrete CRPS, is the right rule for an *ordered* set of options, which five price points are.

Not proper:

- **ECE (expected calibration error)** and MCE. Not proper scoring rules: a classifier that ignores its input and outputs the marginal class rate for every case achieves ECE = 0 with zero discriminatory power ([arxiv.org/pdf/2408.02841](https://arxiv.org/pdf/2408.02841), "Evaluating Posterior Probabilities: Decision Theory, Proper Scoring Rules, and Calibration"). ECE is also a biased estimator of the true calibration error under any binning scheme, and the bias direction is to underestimate ([proceedings.mlr.press/v151/roelofs22a/roelofs22a.pdf](https://proceedings.mlr.press/v151/roelofs22a/roelofs22a.pdf), Roelofs et al., "Mitigating Bias in Calibration Error Estimation"). It is sensitive to bin choice and blind to group-specific miscalibration. It is better read as "Estimated" than "Expected" Calibration Error.
- **Accuracy, MAE, correlation** on their own. MAE is not proper for a probability, and correlation is invariant to exactly the affine level shift you are trying to detect. Use them as diagnostics alongside a proper rule, never as the headline.

Use ECE and reliability diagrams as *diagnostics*, which is what they are good for. A reliability diagram (predicted probability on x, observed frequency on y, binned, with bin counts shown) tells you the *shape* of your miscalibration, which tells you which map in section 3 to fit. A straight line off the diagonal with slope 1 means fit `a` only. A line through the middle with slope not equal to 1 means fit `a` and `b`. A curve means beta calibration or isotonic.

### 4.2 Decomposition: how to tell level error from shape error

Murphy's decomposition of the Brier score:

```
BS = REL - RES + UNC
```

- **UNC** (uncertainty) = `o_bar (1 - o_bar)` where `o_bar` is the base rate. Irreducible given the outcome distribution; independent of your forecasts.
- **REL** (reliability) = the binned mean squared difference between your forecast probability and the observed frequency conditional on that forecast. This is your *level* error. Zero when `p_n = P(y_n = 1 | p_n)`.
- **RES** (resolution) = how much your forecasts vary in a way that tracks varying event probabilities. This is your *shape* skill. Larger is better.

References: [rmets.onlinelibrary.wiley.com/doi/abs/10.1002/qj.2985](https://rmets.onlinelibrary.wiley.com/doi/abs/10.1002/qj.2985) (Siegert, simplifying and generalising Murphy's decomposition), [journals.ametsoc.org/view/journals/wefo/23/4/2007waf2006116_1.xml](https://journals.ametsoc.org/view/journals/wefo/23/4/2007waf2006116_1.xml) (two extra components), variance estimation at [arxiv.org/pdf/1303.6182](https://arxiv.org/pdf/1303.6182). CRPS has an analogous reliability / resolution decomposition ([arxiv.org/pdf/2311.14122](https://arxiv.org/pdf/2311.14122)).

This decomposition is the correct instrument for your specific complaint. Your backtest showed good shape and bad level. In Brier terms: high RES, high REL. Recalibration reduces REL without touching RES. Report both numbers every time, so you can prove the calibration step is doing its job and not destroying resolution.

### 4.3 Scoring "which option wins" versus "what share"

These are different estimands and need different scores. Do not conflate them.

**Which option wins (argmax).** The honest way is not accuracy, it is a proper score on the probability you assign to each option winning. Convert the crowd into a distribution over "option k has the highest share" by bootstrapping the crowd (resample personas with replacement, recompute the argmax, take the frequency), then score that categorical forecast with multi-category Brier or log score. Raw argmax accuracy is a 0/1 score on a single realisation, is not proper, and throws away all your uncertainty information. With five options and n = 48 it will also be extremely noisy.

**What share.** Two options:

- Treat the per-option share as a probability forecast for a randomly drawn individual, and score with multi-category Brier or log score against the realised choice distribution. This is the natural fit and is what Santurkar's Wasserstein alignment metric is a bounded variant of.
- Treat the share as a distributional forecast (you have a full posterior from the crowd) and score with CRPS, or RPS if the options are ordered. This is what the H&M pricing paper reports (CRPS 0.94 versus 0.99 baseline).

For five ordered price points, RPS is the right primary metric because it penalises being wrong by two price points more than being wrong by one. Brier treats all misses equally, which is wrong for an ordered set.

**For an occupancy level** (a continuous share, as in your KL backtest), the right primary metric is CRPS against the realised occupancy, plus absolute error in percentage points for interpretability, plus a PIT histogram or KS-PIT statistic to check whether your intervals have the right width. The H&M paper reports exactly this trio (CRPS, KS-PIT, MAE/RMSE), which is a good template.

### 4.4 Skill scores and the right naive baseline

A skill score is `SS = 1 - Score_model / Score_reference`. Positive means you beat the reference. This is the only number that means anything, because an absolute Brier of 0.148 is excellent on hard questions and terrible on easy ones.

The reference matters more than the model. For JevFish, ranked from weakest to strongest, the candidate baselines are:

1. **Uniform over K options** (share = 1/K each). Trivially weak. Only useful as a floor. Note the Columbia study's finding that uniform random already scores 0.629 individual accuracy, which is why absolute accuracy numbers are meaningless.
2. **Climatology / base rate**: the historical marginal distribution of the outcome. For occupancy, your own trailing occupancy over a comparable window. This is the standard meteorological reference and it is the *minimum* defensible baseline. In Murphy's decomposition, a climatology forecast has REL = 0, RES = 0, and Brier = UNC. So `SS` against climatology is exactly `(RES - REL) / UNC`.
3. **Persistence / no-change**: last period's realised value. For occupancy on a given weekday at a given lead time, last week's number. Hard to beat at short horizons.
4. **A fitted parametric demand curve on your own history**: constant-elasticity occupancy as a function of rate, fitted on your own booking ledger. This is the real bar for a pricing tool and is what the published state of the art is (section 5.3 below and [arxiv.org/pdf/2208.03135](https://arxiv.org/pdf/2208.03135)).
5. **An empty-persona LLM call**: ask the model directly for the occupancy share, no crowd. The Columbia study shows this is within 0.014 of a full-persona twin on individual accuracy, so it is the correct ablation to prove the crowd is doing anything at all. If JevFish does not beat one zero-shot LLM call, the ontology, persona generation and OASIS rounds are pure cost.

Report all five. The empty-persona ablation (5) is the one most likely to be uncomfortable and the one most worth knowing.

For the "which option wins" framing, the correct naive baseline is "pick the cheapest option" or "pick the status-quo option", whichever is the operational default. For Metaculus-style questions the standard is the status-quo / no-change prior, which is notoriously hard to beat.

---

## 5. Benchmarks you could actually run against

Access status checked 18 September 2026. Anything unverified is flagged.

### 5.1 Ranked shortlist

If you only build four harnesses, build these, in this order.

1. **SimBench.** Its estimand is a per-option share vector scored by total variation distance, which is identical in shape to JevFish's output. Data [huggingface.co/datasets/pitehu/SimBench](https://huggingface.co/datasets/pitehu/SimBench), code [github.com/pitehu/SimBench_release](https://github.com/pitehu/SimBench_release/), paper [arxiv.org/html/2510.17516](https://arxiv.org/html/2510.17516). 20 datasets spanning moral decision-making, economic choice and psychological assessment, 10,930,271 unique question-group simulation targets, test splits SimBenchPop (7,167 cases) and SimBenchGrouped (6,343). 45 LLMs evaluated from 0.5B to 405B. Score is 0 to 100 derived from TVD, where 0 is random guessing and 100 is perfect. Best model: **Claude-3.7-Sonnet at 40.80**. Two findings worth internalising: log-linear scaling in model size, no meaningful benefit from inference-time compute, and a near-perfect negative correlation (**r = -0.942**) between instruction-tuning gains and human response entropy, meaning aligned models get worse exactly where the human crowd is most split. Licence CC-BY-NC-SA 4.0 for the framework; 17 of 20 constituent datasets carry explicit permissive licences.
2. **Twin-2K-500.** The only benchmark on this list that hands you a **test-retest ceiling**, which is the maximum score any simulator can earn. Data [huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500](https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500), **CC-BY-4.0**, 733 MB, Parquet plus JSON/CSV, configs `full_persona` (2.06k rows) and `wave_split` (2.06k rows). Companion mega-study data at [huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500-Mega-Study](https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500-Mega-Study), code [github.com/tianyipeng-lab/Digital-Twin-Simulation](https://github.com/tianyipeng-lab/Digital-Twin-Simulation). 2,058 US participants, 2.42 hours each, 4 waves, 500+ questions, including a **pricing survey**. Wave 4 repeats the heuristics-and-biases items to establish the ceiling. Published twin accuracy **71.72%** across 17 tasks, which is **87.67%** of the human test-retest accuracy. Those are the two numbers to beat.
3. **OpinionQA.** Verified direct download, no login. 1,498 questions from 15 Pew ATP waves, 60 US demographic groups, with individual-level human responses and pre-computed OpenAI and AI21 model runs. CodaLab worksheet [worksheets.codalab.org/worksheets/0x6fb693719477478aac73fc07db333f69](https://worksheets.codalab.org/worksheets/0x6fb693719477478aac73fc07db333f69), code [github.com/tatsu-lab/opinions_qa](https://github.com/tatsu-lab/opinions_qa). Three bundles, all HTTP 200 unauthenticated: `model_input` 498 KB at [.../0xa6f81cc62d7d4ccb93031a72d2043669/contents/blob/](https://worksheets.codalab.org/rest/bundles/0xa6f81cc62d7d4ccb93031a72d2043669/contents/blob/), `human_resp` 200 MB at [.../0x050b7e72abb04d1f9b493c1743e580cf/contents/blob/](https://worksheets.codalab.org/rest/bundles/0x050b7e72abb04d1f9b493c1743e580cf/contents/blob/), `runs` 4.1 GB at [.../0xd70e124707194a77b73e5d20ae074ee9/contents/blob/](https://worksheets.codalab.org/rest/bundles/0xd70e124707194a77b73e5d20ae074ee9/contents/blob/). The representativeness formula is in section 1.2. No licence stated on either the repo or the worksheet, which is a flag. HuggingFace mirrors named `lighteval/opinions_qa` are empty.
4. **ForecastBench live CSVs.** The only source where a published human crowd baseline sits on the same questions as the model entries, which is exactly the comparison a crowd-simulation product needs to make. Paper [arxiv.org/html/2409.19839v5](https://arxiv.org/html/2409.19839v5), site [forecastbench.org](https://www.forecastbench.org/). See 5.3.

### 5.2 Survey and opinion benchmarks

**ANES.** [electionstudies.org/data-center](https://electionstudies.org/data-center/). Free registration, then SPSS `.sav`, Stata `.dta`, CSV or fixed-width ASCII with read-in syntax. 2020 Time Series: 8,280 pre-election interviews, 7,453 post-election reinterviews (the study page returned HTTP 403 to automated fetch, so these counts come from the codebook and announcement pages: FLAG). The cumulative file at [electionstudies.org/project/anes-time-series-cumulative-data-file](https://electionstudies.org/project/anes-time-series-cumulative-data-file/) harmonises cross-year variables and is what you want for multi-wave backtests. Argyle et al. used the **2012, 2016 and 2020** waves.

**GSS.** [gss.norc.org/us/en/gss/get-the-data.html](https://gss.norc.org/us/en/gss/get-the-data.html). Stata cumulative file `GSS_stata.zip`, 1972 to 2024, Release 3a (July 2026), no registration for the cumulative cross-section. SPSS and SAS equivalents alongside. GSS Data Explorer at [gssdataexplorer.norc.org](https://gssdataexplorer.norc.org/) (fetch failed with a TLS certificate error, so its account requirement is unconfirmed: FLAG). Mirrors: SDA Berkeley, Roper iPoll, ICPSR. GSS is the evaluation half of SubPOP and the task Park et al. score against, so using it keeps you numerically comparable to published work.

**World Values Survey wave 7.** 64 countries, 2017 to 2022, 50 technical variables plus 290 common questions. Respondent count reported inconsistently as 94,278 and 94,728 across sources (FLAG). The official documentation page [worldvaluessurvey.org/WVSDocumentationWV7.jsp](https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp) is JavaScript-gated with zero download links in the rendered HTML, so it cannot be automated. Use GESIS instead: WVS7 at [access.gesis.org/dbk/69555](https://access.gesis.org/dbk/69555) (registration plus stated purpose), joint EVS/WVS 2017-2022 at [search.gesis.org/research_data/ZA7505](https://search.gesis.org/research_data/ZA7505), version 5.0.0, DOI 10.4232/1.14320, 466 surveys across 118 countries.

**GlobalOpinionQA (Durmus et al., Anthropic).** Paper [arxiv.org/abs/2306.16388](https://arxiv.org/abs/2306.16388), data [huggingface.co/datasets/Anthropic/llm_global_opinions](https://huggingface.co/datasets/Anthropic/llm_global_opinions). 2,556 cross-national questions, single `train` split, 4.7 MB, licence **CC-BY-NC-SA-4.0** (the non-commercial clause matters if you publish a product benchmark). Fields: `question`, `selections` (country name to list of response percentages), `options`, `source` (Pew Global Attitudes or WVS). Finding: default model responses sit closest to the USA plus some European and South American populations; country-prompting shifts the distribution but can produce stereotyped output.

**Pew American Trends Panel.** Wave index at [pewresearch.org/american-trends-panel-datasets](https://www.pewresearch.org/american-trends-panel-datasets/), **169 waves** publicly listed (waves 2 and 136 have no data), most recent wave 169 fielded 28 April to 4 May 2025. Free account required at [pewresearch.org/profile/registration](https://www.pewresearch.org/profile/registration/). Codebook and working instructions at [pewresearch.org/wp-content/uploads/2018/05/Codebook-and-instructions-for-working-with-ATP-data.pdf](https://www.pewresearch.org/wp-content/uploads/2018/05/Codebook-and-instructions-for-working-with-ATP-data.pdf). Neither format nor licence is stated on the index page (FLAG).

**Park et al. agent bank.** Repo [github.com/joonspk-research/genagents](https://github.com/joonspk-research/genagents), **MIT licence**. What is public: a demographic agent bank of **over 3,000 agents built from GSS demographic information** (fictional names and addresses), plus **one** interview-based sample agent at `agent_bank/populations/single_agent/`. What is not public: the full 1,000+ interview-based agent bank. The stated plan is open access to aggregated responses on fixed tasks such as GSS, and restricted access to individualised responses via review. There is no application URL; you email joonspk@stanford.edu. I could not verify that the aggregated-response release has gone live (FLAG).

**SubPOP.** Paper [arxiv.org/abs/2502.16761](https://arxiv.org/abs/2502.16761), ACL version [aclanthology.org/2025.acl-long.1028](https://aclanthology.org/2025.acl-long.1028/), code [github.com/josephjeesungsuh/subpop](https://github.com/josephjeesungsuh/subpop) (**BSD-3-Clause**), data [huggingface.co/datasets/jjssuh/subpop](https://huggingface.co/datasets/jjssuh/subpop) (gated behind terms acceptance). Two `.jsonl` files. Metric is Wasserstein distance to the empirical human distribution, computed in `scripts/experiment/analyze_inference_result.ipynb`; training loss is forward KL. Fine-tuning reduces the LLM-human distributional gap by **up to 46%** versus prompting, consistent across 20+ subpopulations.

**WorldValuesBench.** [github.com/Demon702/WorldValuesBench](https://github.com/Demon702/WorldValuesBench), paper [arxiv.org/pdf/2404.16308](https://arxiv.org/pdf/2404.16308). Over **20 million** (demographic attributes, value question) to answer examples derived from WVS wave 7. Metric is Wasserstein-1 to the normalised human answer distribution. Share of questions within 0.2: **Alpaca-7B 11.1%, Vicuna-7B-v1.5 25.0%, Mixtral-8x7B-Instruct-v0.1 72.2%, GPT-3.5 Turbo 75.0%**.

**Newer (2025 to 2026) distribution-prediction work.**

- "When Synthetic Users Fail", [arxiv.org/html/2607.26348v1](https://arxiv.org/html/2607.26348v1). Ground truth GSS 2016-2024 (14,704 respondents, 10 attitude questions) and WVS wave 7 (63 countries, 91,774 respondents, 16 ordinal questions). Models: Claude Haiku 4.5, Claude Sonnet 4.6, Llama-3.1-8B, Llama-3.3-70B. Metric stack worth copying wholesale: exact-match, MAE, EMD, Jensen-Shannon divergence, log loss, Brier, a stereotyping index Delta eta squared, and Cramer's V. Benchmark itself is "available on request" with no public repo (FLAG).
- "When Can You Trust Your Synthetic Users", [arxiv.org/html/2609.13148](https://arxiv.org/html/2609.13148). ANES 2016 (2,286 respondents with complete feeling thermometers) and Twin-2K-500 (172,884 paired human and GPT-4.1-mini observations). Subgroup calibration slopes on ANES **beta_g in [-0.004, 0.274]** (near-total failure); Twin-2K-500 pricing **beta_g in [0.80, 0.93]** (trust regime). Person-level correlations: conjunction fallacy **rho = 0.387 to 0.392**, anchoring **rho = 0.337 to 0.500**. Reported 83% to 94% bias reduction on subgroup targeting. No public code URL located (FLAG).
- "Silicon Sampling via Cross-Survey Transfer", [arxiv.org/pdf/2607.03091](https://arxiv.org/pdf/2607.03091). Taiwanese TEDS data, individual level. Zero-shot LLMs hit **52% exact match** on genuinely unseen items (Qwen3.5 52.1%, gpt-oss 51.3%) against a supervised same-population ceiling of **58.3%**. Model size does not predict accuracy. The design caution matters: distributional match can be right while individual-level prediction is near chance.

### 5.3 Prediction market and forecasting benchmarks

**ForecastBench (Karger et al., ICLR 2025).** Paper [arxiv.org/html/2409.19839v5](https://arxiv.org/html/2409.19839v5).

- Question bank of **6,435** questions; each round samples 1,000 for LLMs and a 200-question subset for humans. Market questions 2,060 (**Polymarket 915, Metaculus 722, Manifold 405, RAND Forecasting Initiative 18**); dataset questions 4,375 (**ACLED 3,220, Yahoo Finance 509, Wikipedia 428, FRED 166, DBnomics 52**). Kalshi added as a source 19 August 2026. Only questions unresolved at submission time are scored, which is the leakage defence.
- Human baselines: **39 superforecasters** (3+ forecasts per question) and **500 general-public forecasters** via Prolific (40+ responses each).
- Brier scores in the paper, 200-question human set, 7/30/90/180-day horizons: **superforecasters 0.096, general public 0.121, best LLM (Claude-3.5-Sonnet) 0.122**. The EA Forum announcement of the same benchmark quotes **0.093 / 0.107 / 0.111** ([forum.effectivealtruism.org/posts/zwzgR8iuFEcJms3Hu](https://forum.effectivealtruism.org/posts/zwzgR8iuFEcJms3Hu/announcing-forecastbench-a-new-benchmark-for-ai-and-human)). Versions differ; say which you used.
- Live leaderboard CSVs download without auth. [leaderboard_tournament.csv](https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/main/leaderboards/csv/leaderboard_tournament.csv) (62,668 bytes as pulled), plus `leaderboard_baseline.csv`, `leaderboard_dataset.csv`, `leaderboard_preliminary.csv` in the same folder. Columns include `Brier Dataset`, `Brier Market`, `Brier Overall`, `N`, 95% CIs, `Peer`, `BSS`, and a difficulty-adjusted 0-to-100 index.
- Current state as pulled 18 September 2026. Tournament (tool use allowed): Google DeepMind "fire hedgehog" index 69.1, Brier Overall **0.095**, N = 843; "ceramic-kettle" 68.9, Brier **0.096**; the **superforecaster median forecast ranks 3rd** at 68.8, Brier **0.097**, N = 578; Cassi-AI and Torchcast AI at 68.5, Brier 0.099. The `Supers > Forecaster?` column reads **No** with p = 0.62 for the leader, so the top tool-using bots have drawn level with the superforecaster median without significantly beating it. Baseline (no tools): superforecaster median 67.8, Brier **0.104**; public median 62.7, Brier **0.139**; best LLM `claude-sonnet-4-6-adaptive-thinking-16000` 62.4, Brier **0.141**, with supers significantly better at p < 0.01 and the LLM not significantly better than the public at p = 0.55. Also `o3-2025-04-16-scratchpad` 0.146, `gpt-5.5-2026-04-23` 0.153, `claude-opus-4-1-20250805` 0.152.
- Data [github.com/forecastingresearch/forecastbench-datasets](https://github.com/forecastingresearch/forecastbench-datasets) (**CC BY-SA 4.0**, nightly updates), code [github.com/forecastingresearch/forecastbench](https://github.com/forecastingresearch/forecastbench) (**MIT**), submission instructions [wiki/How-to-submit-to-ForecastBench](https://github.com/forecastingresearch/forecastbench/wiki/How-to-submit-to-ForecastBench). Open to public submissions.

**Metaculus.** The API is now **closed by default**. `GET https://www.metaculus.com/api/posts/?limit=2` and `GET .../api2/questions/?limit=2` both returned **HTTP 403**: "The API is only available to authenticated users." Auth header is `Authorization: Token <token>`. Token comes from settings, "My Forecasting Bots", "Create a Bot". For non-bot use, email api-requests@metaculus.com.

Community Prediction is tiered as of 9 March 2026: standard accounts get CP on roughly **50 open questions**, a bot-benchmarking tier roughly **250 open plus 250 resolved** (form application), commercial and research tiers get full CP under written agreement. Documented at [metaculus.com/notebooks/42554/changes-to-the-metaculus-api](https://www.metaculus.com/notebooks/42554/changes-to-the-metaculus-api/), but that notebook returned 403 and the tiering detail was sourced from a third-party spec-drift report ([github.com/pmxt-dev/pmxt/issues/914](https://github.com/pmxt-dev/pmxt/issues/914)): FLAG. This is the biggest practical obstacle, because the crowd prediction is the thing you would score against.

Licence risk is real: [metaculus.com/terms-of-use](https://www.metaculus.com/terms-of-use/) prohibits automated copying outside the provided API and prohibits using Metaculus content to train or develop AI or ML models without prior written permission.

Tournament: FutureEval, bot branch. **$50k+ in prizes every 4 months**, roughly **300 to 500 questions** per season, new seasons each September, January and May; MiniBench runs back-to-back two-week **$1k** tournaments of about 60 questions. Scoring is spot peer score. Resources [metaculus.com/notebooks/38928/aib-resource-page](https://www.metaculus.com/notebooks/38928/aib-resource-page/), rules [metaculus.com/aib/contest-rules](https://www.metaculus.com/aib/contest-rules/), template [github.com/Metaculus/metac-bot-template](https://github.com/Metaculus/metac-bot-template).

**Manifold Markets.** Base `https://api.manifold.markets`, verified HTTP 200 unauthenticated on `GET /v0/markets?limit=1`. Docs [docs.manifold.markets/api](https://docs.manifold.markets/api). Reads need no auth, writes do. Rate limit **500 requests per minute per IP**, with an explicit instruction not to rotate IPs. Backtesting endpoints: `GET /v0/markets` (default limit 500, max 1,000, cursor via `before`, or `beforeTime` for deep pagination on `newest` sort) and `GET /v0/search-markets?filter=resolved`. Responses carry `isResolved`. Bulk dumps at [docs.manifold.markets/data](https://docs.manifold.markets/data): bets **967 MB** (2024-07-04), markets **87 MB** (2024-07-06), comments **127 MB** (2024-07-06), coverage from December 2021, URLs of the form `firebasestorage.googleapis.com/v0/b/mantic-markets.appspot.com/o/trade-dumps%2Fmanifold-dump-bets-04072024.json.zip`. **Dumps are personal and non-commercial only**; commercial licensing via data@manifold.markets. You get the full market probability path plus the outcome, so you can score both calibration against the outcome and agreement with the crowd price at any timestamp.

**Polymarket.** Open, no key, verified HTTP 200 on `GET https://gamma-api.polymarket.com/markets?limit=1&closed=true`. The OpenAPI spec lists `security: []`. Filters include `closed`, `uma_resolution_status`, liquidity, volume, date range and tags; pagination via `limit`/`offset` or keyset at `/markets/keyset`. Docs index [docs.polymarket.com/llms.txt](https://docs.polymarket.com/llms.txt). SDKs exist in TS and Python. No rate limits documented (FLAG); assume they exist.

**Halawi et al., "Approaching Human-Level Forecasting with Language Models" (NeurIPS 2024).** Paper [arxiv.org/pdf/2402.18563](https://arxiv.org/pdf/2402.18563).

- Raw dataset: 48,754 questions and 7,174,607 user forecasts, 2015 to 2024, from Metaculus, GJOpen, INFER, Polymarket and Manifold. Composition: 33,664 binary, 9,725 multiple-choice, 4,019 numerical, 1,346 other.
- Curated split: 5,516 binary questions, **3,762 train / 840 validation / 914 test**. Test per platform: Metaculus 275, Polymarket 300, Manifold 297, GJOpen 38, INFER 4. Test questions all opened on or after 1 June 2023; train and validation all resolved before it. The paper states the cut-off as 1 June 2023 in one place and 1 June 2024 in another, which is an internal inconsistency (FLAG). Five geometric retrieval dates per question, 86% retained on average, average question window about 70 days, average time to resolution 42 days.
- Metric: Brier averaged within question across retrieval dates, then across questions, plus RMS calibration error.
- No-retrieval baselines on the test set (1 SE): GPT-4-1106-Preview **0.208 (0.006)** zero-shot and 0.209 scratchpad, Claude-2.1 **0.220 (0.006)**, Llama-2-13B 0.226, Mistral-8x7B-Instruct 0.238, Gemini-Pro 0.243, trimmed mean 0.208. Random **0.250**, human crowd **0.149**.
- Full system (Table 3), all questions: system **0.179 (0.003)** versus crowd **0.149 (0.003)**; a 50/50 ensemble of system and crowd **0.146 (0.002)**. Accuracy 71.5% versus 77.0%. Selective settings: Crowd Uncertain (crowd between 0.3 and 0.7, 56% of questions) system **0.238** versus crowd **0.240**; Early Retrieval 0.186 versus 0.162; 5+ Articles 0.175 versus 0.142; All Criteria jointly (22% of forecasts, 43% of questions) **0.240** versus **0.247**. In every setting the system-plus-crowd ensemble is best.
- Release: code [github.com/dannyallover/llm_forecasting](https://github.com/dannyallover/llm_forecasting), data [huggingface.co/datasets/YuehHanChen/forecasting](https://huggingface.co/datasets/YuehHanChen/forecasting) and [.../forecasting_raw](https://huggingface.co/datasets/YuehHanChen/forecasting_raw). No licence stated on the code repo (FLAG).

**Consistency Checks for Language Model Forecasters (Paleka et al., ICLR 2025 Oral).** [arxiv.org/abs/2412.18544](https://arxiv.org/abs/2412.18544). **3,000 consistency checks** resolving in 2028, so no ground truth exists for over three years. Metric is an arbitrage-based consistency score over 10 logical rules (Negation, Paraphrase, Consequence, AndOr, And, Or, But, Cond, CondCond, ExpEvidence): if a forecaster gives both parties 60% to win the same race, an arbitrageur can profit against it, and the profit size is the score. The paper reports that instantaneous consistency correlates strongly with ground-truth Brier.

This is the most immediately useful item on the list for JevFish, because it lets you score the aggregator **today** with no outcome data. The share-of-crowd analogues are: shares sum to 1; merging two options should give the sum of their shares; renaming or reordering options should change nothing; adding a dominated option should not change the relative shares of the others. Each of those is a check you can run on every run for free, and each of them will catch a real bug. No code or data release URL verified (FLAG).

**Prophet Arena.** Paper [arxiv.org/html/2510.17638](https://arxiv.org/html/2510.17638). **1,367 resolved events covering 72,136 markets**, cutoff 11 October 2025, source **Kalshi**, twenty new events per day. Metrics: Brier, ECE, and Average Return. Paper numbers: GPT-5 (Reasoning) Brier **0.184** versus **Market Baseline 0.187**; all models land in [0.17, 0.24] against random 0.25; no model reaches break-even average return, so nobody profits against the market. Public 100-event subset at [huggingface.co/datasets/prophetarena/Prophet-Arena-Subset-100](https://huggingface.co/datasets/prophetarena/Prophet-Arena-Subset-100); full pool not released. Two fetches of the live leaderboard returned different column labels for the same rows (one reading "Brier Score" around 0.798, the other "Skill theta" around 0.00). Treat the live site numbers as unverified and cite the paper's 0.184 versus 0.187 (FLAG). Ranking methodology at [ai-prophet.github.io/pm_ranking/blogpost/ranking_llm_250727.html](https://ai-prophet.github.io/pm_ranking/blogpost/ranking_llm_250727.html).

**FutureSearch Deep Research Bench.** [arxiv.org/pdf/2506.06287](https://arxiv.org/pdf/2506.06287), leaderboard [drb.futuresearch.ai](https://drb.futuresearch.ai/). 169 real-world research tasks, each with 10k to 100k webpages stored offline, with curated answers. It scores research agents, not population shares, so it is only useful as a retrieval-quality harness.

### 5.4 Choice, product and behavioural benchmarks

**Hainmueller, Hopkins and Yamamoto immigrant conjoint.** The cleanest public conjoint ground truth that exists. Available as `immigrationconjoint` in the R package `cjoint`: **13,960 observations, 16 variables** (CaseID, contest_no, Education, Gender, Country of Origin, Reason for Application, Job, Job Experience, Job Plans, Prior Entry, Language Skills, Chosen_Immigrant, ethnocentrism, profile, LangPos, PriorPos), loaded with `data("immigrationconjoint")`, with the matching design object `immigrationdesign`. Docs [search.r-project.org/CRAN/refmans/cjoint/html/immigrationconjoint.html](https://search.r-project.org/CRAN/refmans/cjoint/html/immigrationconjoint.html). Same data in `cregg` as `immigration`: [thomasleeper.com/cregg/reference/immigration.html](https://thomasleeper.com/cregg/reference/immigration.html). Citation: Hainmueller, Hopkins and Yamamoto (2014), Political Analysis 22(1):1-30. Replication archives at AJPS Dataverse doi:10.7910/DVN/25505 and doi:10.7910/DVN/2OOLD7 (the Dataverse page returned empty content to automated fetch, so licence and file list are unconfirmed: FLAG). Ground-truth metric is the Average Marginal Component Effect per attribute level, so you score sign agreement, rank correlation of attribute importances, and absolute AMCE error in percentage points. I found no public Sawtooth sample conjoint dataset, only their data-export documentation (FLAG).

**Brand, Israeli and Ngwe, "Using GPT for Market Research".** MSI Working Paper 23-131 ([PDF](http://thearf-org-unified-admin.s3.amazonaws.com/MSI_Report_23-131.pdf)), SSRN abstract_id=4395751, ACM version [dl.acm.org/doi/pdf/10.1145/3670865.3673479](https://dl.acm.org/doi/pdf/10.1145/3670865.3673479). Ground truth is Fong, Guo and Rao, a real-consumer conjoint on toothpaste (Colgate versus Crest, fluoride) and deodorant (Dove versus Speed Stick, aluminium).

Exact numbers, and read them carefully because this is the single most-cited "LLMs work for market research" result:

| Quantity | GPT MNL | GPT random coefficient | Real human conjoint |
|---|---|---|---|
| WTP for fluoride | $3.40 | $3.30 | $3.27 |
| WTP for aluminium | -$0.99 | -$0.92 | -$1.97 and -$1.53 |

Regressions on 10,800 observations per category. Toothpaste price coefficient -0.484 (0.021), attribute coefficient 1.647 (0.037); deodorant price -0.692 (0.034), attribute -0.685 (0.054). So one attribute lands within 4% of the human estimate and the other is off by roughly a factor of two in the same direction. The paper itself notes estimates are "often inaccurate and in some cases wrong-signed" and that aggregate output hides a failure to capture individual heterogeneity. Whether the Fong, Guo and Rao ground-truth data is public is unverified (FLAG).

**Goli and Singh.** [arxiv.org/abs/2305.02531](https://arxiv.org/abs/2305.02531), Marketing Science 43(4):709-722, doi 10.1287/mksc.2023.0306. GPT-3.5 shows a lexicographic preference for earlier rewards that humans do not; GPT-4 avoids that but its discount rates remain considerably larger than human; both are more patient in weak-future-time-reference languages such as German and Mandarin; chain-of-thought conjoint mitigates but does not eliminate the gap. Exact discount rates and correlations not extracted (FLAG). The benchmark is the published discounting literature rather than a downloadable dataset, which makes it harder to score against.

**Gui and Toubia, the price-sweep gate.** Version 3 ([arxiv.org/html/2312.15524v3](https://arxiv.org/html/2312.15524v3)) reports a purpose-built benchmark: **1,000 respondents (991 after exclusions)**, representative US Prolific sample, purchase-intention questions on **40 CPG products** from the top categories in DellaVigna and Gentzkow (2019), at **11 price points from 0 to 200% of regular price in 20% increments**. Human demand curves slope downward; GPT-simulated curves follow an **inverted-U shape**. The fix is unblinding the randomisation in the system prompt ("the price of the product is randomly and uniformly drawn from {min_price} to {max_price}"), with MAE improvement from **1% to over 60%** across model versions, and for the fine-tuned model blinded MAE **0.134** versus unblinded **0.113**, a 15% reduction. Version 1 of the same paper reported elasticity figures instead (0.14 naive, 1.38 after unblinding, against a literature benchmark of 1.8 to 3.0); the versions present different analyses, so cite whichever you use. No explicit elasticity coefficients appear in v3 (FLAG).

Use this as a **gate, not a score**. Sweep price across a wide range and check the curve is monotone downward. If it is inverted-U or flat, nothing downstream is worth measuring.

**Other persona-replication results.**

- "AI personas replicating 133 published findings", [arxiv.org/abs/2408.16073](https://arxiv.org/abs/2408.16073). 133 experimental findings from 14 Journal of Marketing papers containing 45 studies, **19,447 AI personas**, each an individual Claude Sonnet instance prompted from the original measures, stimuli and sampling specs. Replicated **76% of main effects, 68% of all effects, and only 27% of interaction effects**. Sources disagree on the exact model version (FLAG). The interaction-effect collapse is the number that should worry a pricing tool, because segment-specific price response is an interaction effect.
- "Your Reviews Replicate You", [arxiv.org/pdf/2604.22756](https://arxiv.org/pdf/2604.22756). 200 active Reddit users, per-user vector databases from review histories, RAG plus prompt engineering, fractional factorial design with foldover over 16 orthogonal profiles, part-worths by logistic regression, case study on computer monitors. **87.73% accuracy** on 163 validation comparisons (149 correct, 14 incorrect) versus a 50% random baseline. Ground truth is self-constructed from Reddit, n is small, and it is the highest number in the area precisely because it is the narrowest task with the richest per-person input (FLAG). Not reusable as a benchmark.

**A/B test corpora.**

- **ASOS Digital Experiments Dataset** is the only genuinely good public A/B corpus. [arxiv.org/abs/2111.10198](https://arxiv.org/abs/2111.10198), NeurIPS 2021 Datasets and Benchmarks. **78 real A/B tests**, 2 to 5 variants each, 4 decision metrics (binary, count, real-valued), **24,153 snapshots** at daily or 12-hourly cumulative checkpoints during 2019 to 2020. Download: `wget -O ./data/asos_digital_experiments_dataset.parquet https://osf.io/62t7f/download`. Project [osf.io/64jsb](https://osf.io/64jsb/), datasheet [osf.io/vyuce](https://osf.io/vyuce), code [github.com/liuchbryan/oce-dataset](https://github.com/liuchbryan/oce-dataset). Group-level aggregates only, no per-respondent rows, and the metrics are anonymised, so you can score direction and calibrated lift but you cannot give a persona much context about what was tested (FLAG).
- **GoodUI** sells 26 case studies covering 1,533 testing days for $289 at [goodui.org/datastories](https://goodui.org/datastories/), reporting 92% success rate and 23% median impact. Public records carry uplift and page type but not sample size or significance, there is no bulk export or API, and a 92% win rate is agency selection bias, not what a real experimentation programme looks like. Unusable as a scoring set.
- **Microsoft and Booking.com**: I found no published A/B corpus from either. Kohavi's material ([exp-platform.com](https://exp-platform.com/) and the Trustworthy Online Controlled Experiments book) contains case studies in prose, not data. Do not plan around one existing (FLAG).

**Elections and box office.**

- FiveThirtyEight election results: [github.com/fivethirtyeight/election-results](https://github.com/fivethirtyeight/election-results), CSVs for President, Senate and Governor including primaries, national and by state, November 1998 onward.
- FiveThirtyEight polls and pollster ratings: [github.com/fivethirtyeight/data/tree/master/polls](https://github.com/fivethirtyeight/data/tree/master/polls) and `/pollster-ratings`. `raw-polls.csv` pairs each poll's estimate with the actual result, which is a ready-made poll-versus-outcome scoring set. The natural benchmark for a synthetic crowd is "beat the average pollster's error on the same races".
- FiveThirtyEight shut down in March 2025. Treat both repos as archives and check the last commit date (FLAG).
- Box office: no free official API. The Numbers and Box Office Mojo require scraping, with terms-of-service risk. Available ground truth is opening weekend gross, production budget, and domestic/international/worldwide gross. No canonical benchmark split exists, so you would be constructing your own and losing the comparability that is the point.

### 5.5 Price elasticity and willingness-to-pay ground truth, which is the weakest area

This matters most for JevFish's actual use case, and the honest conclusion is uncomfortable: **there is no public hotel dataset with exogenous price variation, therefore no public elasticity ground truth to score against.**

- **Expedia Personalized Sort (ICDM 2013)** is the best public hotel choice dataset with price variation. [kaggle.com/c/expedia-personalized-sort/data](https://www.kaggle.com/c/expedia-personalized-sort/data). Train **399,344 search lists and 9,917,530 rows**, test **266,230 lists and 6,622,629 rows**. Each search-hotel pair carries current price, average historical price, star rating, location scores, display position, competitor OTA information and user aggregate purchase history. Labels: **5 booked, 1 clicked, 0 neither**. Kaggle account plus competition-rules acceptance. You can compute observed booking share per option within a search set and score a predicted share vector directly against it, which is the closest public analogue to JevFish's estimand.
- **Antonio, Almeida and Nunes hotel booking demand.** Data in Brief 22 (Feb 2019), [sciencedirect.com/science/article/pii/S2352340918315191](https://www.sciencedirect.com/science/article/pii/S2352340918315191), Kaggle mirror [kaggle.com/datasets/jessemostipak/hotel-booking-demand](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand). **119,390 rows, 29 columns**, two Portuguese hotels (one city, one resort), with ADR, lead time, market segment and cancellation. Sources disagree on coverage (July 2015 to August 2017 versus October 2014 to September 2017): FLAG. Price is endogenous to demand throughout, so you get a realised-price-versus-demand relationship, not a clean elasticity.
- **Inside Airbnb.** [insideairbnb.com/get-the-data](https://insideairbnb.com/get-the-data/), licence stated as **CC BY 4.0**. Quarterly snapshots for the last year are free, 861 direct data links on the page. Per-city files `listings.csv.gz`, `calendar.csv.gz`, `reviews.csv.gz` plus a neighbourhoods GeoJSON, at URLs of the form `https://data.insideairbnb.com/united-states/ny/albany/2026-06-16/data/calendar.csv.gz`. Country-level archives now cover Australia, Canada, France, Germany, Greece, Italy, Netherlands, Portugal, Spain, Sweden, UK and US; older data via a request form. **`calendar.csv.gz` gives price and availability per listing per date, which is a revealed price-occupancy panel for short-term rentals.** Closest free thing to the actual Pureloft and Lazybee business.
- **STR / CoStar** is paid. [costar.com/products/str-benchmark](https://www.costar.com/products/str-benchmark), sample of 64,000 hotels and 8.7 million rooms in 180 countries. Academic access is negotiated.
- **Corgel, Lane and Woodworth, "Hotel Industry Demand Curves"**, Journal of Hospitality Financial Management 20(1):85-95 (2012), [ecommons.cornell.edu/handle/1813/72477](https://ecommons.cornell.edu/handle/1813/72477). Data from Smith Travel Research and Moody's Analytics. Published estimates:

| Level | Short-run price elasticity | Long-run price elasticity |
|---|---|---|
| All US hotels | -0.17 | -0.19 |
| Top 50 markets, all | -0.15 | -0.37 |
| Top 50 markets, upper priced | -0.22 | -0.84 |
| Top 50 markets, lower priced | -0.09 | -0.64 |

The paper's chain-scale column reads -0.17, -0.70, -0.32, -0.31, -0.42, -0.14, -0.08, -0.12 short-run and -0.19, -1.36, -0.34, -0.75, -1.11, -0.20, -0.29, -0.16 long-run; the row labels did not survive text extraction, so do not attribute a specific figure to a specific chain scale from this report alone (FLAG). The paper states luxury elasticity is roughly **four times** economy elasticity.

Two statements from the paper matter more than the table. First, "elasticity tends to increase with data disaggregation", demonstrated by the -0.84 / -0.37 / -0.19 sequence. Second, and explicitly: "we expect by extension that the elasticity for individual hotels will be higher than their market level elasticity suggests", and "the estimates presented here cannot be directly applied to an individual hotel or even a competitive set of hotels".

**On the -0.36 benchmark used in the JevFish synthetic test: I could not find -0.36 in Corgel et al.** The closest published figures are -0.37 (long run, top 50 markets, all hotels) and -0.17 (short run, all US hotels). Both are market-level aggregates that the authors explicitly say must not be applied to an individual property. Treat -0.36 as **NOT VERIFIED** as a property-level benchmark, and note that using an aggregate figure as a property-level target biases you toward concluding the tool is too elastic when property-level elasticity is genuinely higher.

Likewise, the property-level range of **-0.13 to -0.95** cited in the JevFish backtest could not be traced to a source in this review: **NOT VERIFIED**. Find and record the citation, because the entire "the shape was credible" conclusion rests on it.

- **Singh and Corsun (2023)**, Cornell Hospitality Quarterly, doi 10.1177/19389655231184475. Annual operating data on over 2,500 hotels, 2018 to 2021, concluding lodging demand is relatively inelastic. Publisher returned HTTP 403, so exact coefficients are unextracted (FLAG).
- Free Cornell Center for Hospitality Research reports: [ecommons.cornell.edu/collections/25c95350-d540-47fa-9a64-9487fd2e45e7](https://ecommons.cornell.edu/collections/25c95350-d540-47fa-9a64-9487fd2e45e7).

**The defensible benchmark for JevFish's pricing use case is therefore your own booking ledger, held out by date.** Not a public dataset. That is also the only way to get a level anchor, so it is required work regardless.

### 5.6 Two licence problems to resolve before any of this becomes commercial

Metaculus prohibits using its content to train or develop AI or ML models without written permission. Manifold's bulk dumps are personal and non-commercial only. Both are fine for internal evaluation; neither is fine for a published product benchmark. GlobalOpinionQA and SimBench are CC-BY-NC-SA, same constraint. Twin-2K-500 (CC-BY-4.0), ForecastBench data (CC BY-SA 4.0), ForecastBench code (MIT), SubPOP code (BSD-3) and Inside Airbnb (CC BY 4.0) are the commercially usable set.

---

## 6. What the best current systems do

The short version: none of them build a persona crowd. They retrieve evidence aggressively, sample the same or several models 5 to 10 times, aggregate arithmetically, clip, and apply a post-hoc affine correction in log-odds space. The current state of the art (Bridgewater's AIA Forecaster) ends its pipeline with Platt scaling, and that Platt step is worth more Brier than going from 1 sample to 10.

### 6.1 The current state of the art: AIA Forecaster (Bridgewater AIA Labs)

Paper [arxiv.org/abs/2511.07678](https://arxiv.org/abs/2511.07678). Authors Alur, Stadie, Kang, Chen, McManus, Rickert, Lee, Federici, Zhu, Fogerty, Williamson, Lozinski, Linsky, Sekhon. No code or data released (FLAG).

This is the first system to match or beat the superforecaster median on ForecastBench, and its architecture is the template to copy.

| Forecaster | FB-Market | FB-7-21 | FB-8-14 | MarketLiquid |
|---|---|---|---|---|
| Market price | 0.0965 | | | 0.1106 |
| Public survey median | 0.1035 | 0.1451 | 0.1510 | |
| Superforecaster median | 0.0740 | 0.1110 | 0.1152 | |
| ForecastBench prior SOTA | 0.107 | 0.133 | 0.145 | |
| OpenAI o3 | 0.1096 | 0.1221 | 0.1262 | 0.1324 |
| **AIA Forecaster** | **0.0753** | **0.1076** | **0.1099** | 0.1258 |

Architecture, in order: **M = 10 independent agents**, each doing fully agentic adaptive search; then an **agentic supervisor** that identifies disagreements between them, issues its own clarifying search queries (often to look up a base rate or fact-check an assertion), and updates with a stated confidence level, where only high-confidence updates replace the mean; then **Platt scaling** as the final step.

Three ablations that should reshape JevFish's priorities:

**Search is almost the whole system.** On live markets, with search 0.1002, without search **0.3609**, a 3.6x difference, and without search it is worse than always predicting 0.5. On ForecastBench: no search 0.1230, non-agentic Search-B 0.12168, agentic Search-B 0.11824, non-agentic Search-A 0.11738, agentic Search-A **0.1140**.

**Aggregation choice barely matters and sample count saturates fast.** FB-7-21, 1,610 questions, 10 forecasts (their Table 9): median **0.1138**, simple mean 0.1140, trimmed mean 0.1142, single forecast 0.1182. Going from 1 to 10 samples buys **0.0044 Brier**, about 3.7% relative. Choosing between mean, median and trimmed mean is worth **0.0004**. Their words: "averaging multiple independent forecasts is critical for forecasting performance and cannot be meaningfully improved by minor variations thereof." On scaling: sharply decreasing Brier from 1 to 5, modest further improvement to 15, standardise on 10.

**Post-processing is where the money is.** Their Table 11, FB-7-21:

| Correction | Fixed parameter | In-distribution fit | Out-of-distribution fit |
|---|---|---|---|
| **Platt scaling** | **0.1076** | **0.1071** | 0.1104 |
| Log-odds extremization | 0.1085 | n/a | n/a |
| Isotonic regression | n/a | 0.1097 | 0.1134 |
| OLS | n/a | 0.1119 | 0.1125 |
| **None** | **0.1140** | n/a | n/a |

Four things to take from that table:

1. The correction is worth **0.0064 to 0.0069 Brier, roughly 1.5x the entire gain from 1 sample to 10.** Calibration buys more than compute.
2. The **fixed-coefficient** version essentially matches the learned one (0.1076 versus 0.1071), so it needs no fitting data. They use **alpha = sqrt(3) approximately 1.732** from Neyman and Roughgarden, deliberately, "to avoid the risk of overfitting". The optimal learned value on their data was 2.27 and the value that optimises superforecaster performance was 1.72.
3. Parameters fitted on a **different benchmark** (Halawi's) still helped: 0.1104 versus 0.1140. The correction transfers out of distribution.
4. Isotonic regression is worse than Platt both in and out of distribution, which matches the 200-to-1,000-case rule in section 3.2.

Their transform, from Appendix G.2, is the same one in section 3.6:
`p_hat = p^alpha / (p^alpha + (1-p)^alpha) = sigmoid(alpha * logit(p))`
and they prove that log-odds extremization, `logit(p_hat) = (d/n) * sum_i logit(p_i)`, **is mathematically identical to Platt scaling applied to the geometric mean of the forecasts with coefficient d**. They chose Platt on the arithmetic mean because extremization needs the k raw forecasts and is therefore incompatible with their supervisor step.

Two constraints they state that JevFish must respect:

- "The largest Brier score decreases come from original forecasts p in [0.2, 0.4) union [0.6, 0.8)." Moving 0.497 to 0.381 changes Brier by -0.102; moving 0.995 to 0.999 changes it by 2.4e-5. All the value is in the middle of the range, which is exactly where JevFish's outputs live.
- **"Post hoc calibration only helps when initial judgments are already on the correct side of 0.5."** If the raw share is on the wrong side of the decision boundary, no monotone map saves it.

They also document the hedging that motivates the correction: "LLMs have an annoying bias, likely stemming from post-training via RLHF, which makes them hedge toward 0.5 ... Forecasts for events where the outcome is somewhat certain (e.g. a true probability of 0.85) are often attenuated to a more entropic forecast (e.g. 0.6) ... even for questions where the outcome is certain, LLMs will often predict 0.95 rather than 1.0." They print two o3 traces doing it: the model computes a 61% base rate then "trim the edge ... back to an even 0.60"; and computes "more than 99% chance the record survives" then writes "we shave the probability from 98% to 97%".

### 6.2 Halawi, Zhang, Yueh-Han, Steinhardt (NeurIPS 2024)

Paper [arxiv.org/abs/2402.18563](https://arxiv.org/abs/2402.18563), [proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/file/5a5acfd0876c940d81619c1dc60e7748-Paper-Conference.pdf), code [github.com/dannyallover/llm_forecasting](https://github.com/dannyallover/llm_forecasting) (62 stars, **no licence file**, last pushed 19 April 2026), data [huggingface.co/datasets/YuehHanChen/forecasting](https://huggingface.co/datasets/YuehHanChen/forecasting) and [forecasting_raw](https://huggingface.co/datasets/YuehHanChen/forecasting_raw).

The full retrieval pipeline, because the detail is the substance:

1. **Query generation.** GPT-4-1106-Preview at temperature 0 generates 6 search queries from each of two prompts (plain query expansion, and sub-question decomposition), union of both plus the raw question. Both prompts kept because their top-2 candidates scored 3.08 and 3.09 average article relevance versus below 3.04 for the other four, and they "generate queries with little overlap".
2. **News retrieval.** **NewsCatcher** and **Google News** (via `gnews`), selected from five APIs tested. Relevance sums over 24 test questions: Google News 39, NewsCatcher 35, Aylien 30.5, NewsAPI.org 23.5, Newsdata.io 16.5. Top 10 English articles per API per query within the retrieval date range.
3. **Relevance filter.** **GPT-3.5-Turbo** at temperature 0 rates each article **1 to 6**, and anything **scoring 3 or below is discarded**. They feed only the title plus first 250 words, not the full text: at threshold 4 this gives **recall 0.73, precision 0.65** against GPT-4-on-full-text gold labels, and saves about **70% of cost** (average article 1,087.6 tokens versus roughly 330). Alternatives tested: Mixtral-8x7B-DPO at threshold 3 gave recall 0.70 / precision 0.63; embedding cosine similarity at 0.48 gave recall 0.73 / precision 0.54.
4. **Summarisation.** GPT-3.5-Turbo at temperature 0.2, question-conditioned. Best of 5 candidate prompts scored Brier 0.193 versus 0.201 for second place.
5. **Presentation.** Top **k = 15** summaries **ordered by relevance, not recency**. Swept k in {5, 10, 15, 20, 30} and both orderings; k = 15 by relevance gave validation Brier **0.177**.
6. **Reasoning prompt.** Seven numbered steps: rephrase and expand the question, reasons for No with strength ratings, reasons for Yes with strength ratings, "Aggregate your considerations. Think like a superforecaster (e.g. Nate Silver)", output an initial probability, then step 6 verbatim: *"Evaluate whether your calculated probability is excessively confident or not confident enough. Also, consider anything else that might affect the forecast that you did not before consider (e.g. base rate of the event)"*, then output the final number. Best of **15 hand-crafted prompts**: validation Brier 0.167, next two at 0.170 and 0.174.
7. **Ensembling.** 6 forecasts per question: 3 from base GPT-4-1106-Preview on the top-3 scratchpad prompts, plus 3 from the fine-tuned GPT-4-0613 at temperature 0.5. Aggregated by a **non-standard trimmed mean** implemented in [ensemble.py](https://raw.githubusercontent.com/dannyallover/llm_forecasting/main/llm_forecasting/ensemble.py) as: find the median, find the single forecast furthest from it, halve its weight, redistribute that 0.5 uniformly over the other five, take the weighted average. Their own note: "this is not a standard implementation of trimmed mean, and it is set this way since we only aggregate a small number (i.e., 6) of forecasts."

Validation aggregator comparison (their Table 14): **trimmed mean 0.1649**, median 0.1651, geometric mean 0.1655, mean 0.1656, Universal Self-Consistency 0.1691, no-ensemble baseline 0.1676, human crowd 0.1600. The spread across aggregators is **0.0007**, and letting an LLM do the aggregating (USC) was **worse than not ensembling at all**.

**Fine-tuning procedure**, which is really a crowd-anchoring procedure and worth copying conceptually. Per training question: 2 retrieval configurations x 4 scratchpad prompts x 2 models (Claude-2.1, GPT-4-Preview) = 16 candidate forecasts. Selection: keep only outputs with a **lower Brier than the crowd**; then **discard any prediction deviating more than 0.15 from the crowd prediction**, explicitly to stop the model learning overconfidence; then set the **target to the average of the model's prediction and the crowd prediction**. 73,632 reasonings generated, 13,253 met the criteria, 6,000 most recent used, GPT-4-0613 fine-tuned for 2 epochs.

**Results.** Test set is 914 binary questions from Metaculus (275), Polymarket (300), Manifold (297), GJOpen (38), INFER (4), with 5 retrieval dates per question on a geometric schedule.

| System | Brier | Accuracy |
|---|---|---|
| Random (always 0.5) | 0.250 | |
| Best zero-shot baseline, GPT-4-1106-Preview | 0.208 (SE 0.006) | |
| Claude-2.1 scratchpad | 0.215 | |
| Llama-2-13B zero-shot | 0.226 | |
| Gemini-Pro scratchpad | 0.230 | |
| Their system, no retrieval and no fine-tuning | 0.206 | 66.6% |
| Their system, retrieval but no fine-tuning | 0.186 | 70.6% |
| Their system, fine-tuned GPT-3.5 swapped in | 0.182 | 70.7% |
| **Full system** | **0.179** (SE 0.003) | 71.5% |
| **Human crowd** | **0.149** (SE 0.003) | 77.0% |
| System + crowd, 4x weight on crowd | **0.146** (SE 0.002) | 77.8% |

**The retrieval ablation is the biggest single lever: 0.206 to 0.186.** The prompt search was worth almost nothing; the authors say so themselves ("fairly a minor improvement").

**Where it beats the crowd and where it does not** (their Table 3):

| Criterion | Theirs | Crowd | 50/50 aggregate | % questions |
|---|---|---|---|---|
| All questions | 0.179 | **0.149** | 0.146 | 100% |
| Crowd uncertain (crowd in [0.3, 0.7]) | **0.238** | 0.240 | 0.233 | 56% |
| Early retrieval | 0.186 | **0.162** | 0.159 | 100% |
| 5+ relevant articles | 0.175 | **0.142** | 0.140 | 94% |
| All three criteria jointly | **0.240** | 0.247 | 0.237 | 43% |

It beats the crowd only where the crowd is itself uncertain, and by 0.002. It loses badly where the crowd is confident: "our system achieves 7% higher accuracy on questions where the crowd's prediction is within .05 of 0 or 1, but the Brier score is worse by .04", because "it rarely outputs low probabilities ... this stems from our model's tendency to hedge predictions due to its safety training".

**The calibration finding, which cuts against my own section 3 and must be said plainly.** Their test-set RMS calibration error is **0.42 against the human crowd's 0.38** (the value is implausibly large for an RMS calibration error on [0,1] and the paper gives no formula, so treat the scale as unknown: FLAG). Their qualitative statements are the useful part: "most of the calibration error coming from the system's **underconfidence**: predictions near 0 are observed to occur less frequently than anticipated", and **"our system is naturally well calibrated ... standard calibration methods such as binning or isotonic regression do not improve performance."** Their fine-tuning-plus-ensembling improved calibration without any calibration-specific training. So a fitted calibration layer is not universally a win; it is a win when the raw system is miscalibrated, which JevFish demonstrably is and theirs was not.

**The main published critique.** FutureSearch's "Contra papers claiming superhuman AI forecasting" ([alignmentforum.org](https://www.alignmentforum.org/posts/uGkRcHqatmPkvpGLq/contra-papers-claiming-superhuman-ai-forecasting), 12 Sep 2024, with a disclosed conflict of interest) notes the headline gap of 0.179 versus 0.149 is a **0.03 shortfall against the authors' own 0.02 materiality threshold**, so the title overstates the result. Also note two internal inconsistencies in the paper: Early Retrieval appears as 0.186/0.162 in Table 3 and 0.185/0.161 in Section 6.3, and the test-set cutoff is given as 1 June 2023 in Table 2a and 1 June 2024 in Section 3.1.

### 6.3 Base-rate retrieval: small, real, and fragile

The honest summary: **base-rate prompting is a small, real, fragile effect, and no published system gets a large measured win from a dedicated base-rate retrieval module.** Nobody has a clean ablation on a "fetch the historical frequency then adjust" component.

**What the strongest systems actually do.**

- **Halawi**: one line inside step 6 of the scratchpad asking the model to reconsider in the light of "base rate of the event". No separate retrieval, no isolating ablation.
- **Metaculus's own template bot** uses a status-quo prior rather than a base rate, verbatim: *"(b) The status quo outcome if nothing changed ... You write your rationale remembering that good forecasters put extra weight on the status quo outcome since the world changes slowly most of the time."* For multiple choice it adds *"good forecasters leave some moderate probability on most options to account for unexpected outcomes"* ([main.py lines 213 to 221 and 276 to 287](https://raw.githubusercontent.com/Metaculus/metac-bot-template/main/main.py)).
- **AIA Forecaster** retrieves base rates **reactively**, only to settle disagreement between its 10 agents: "Useful queries at this stage often involve looking up a base rate, or fact-checking assertions made by individual forecasting agents" ([arxiv.org/abs/2511.07678](https://arxiv.org/abs/2511.07678), Section 3.2).
- **Panshul42** splits its five agents by reasoning style, "directing some toward outside view (historical/reference class) reasoning and others toward inside view (mechanistic/causal) reasoning" ([github.com/Panshul42/Forecasting_Bot_Q2](https://github.com/Panshul42/Forecasting_Bot_Q2)).
- **FutureSearch** turned base-rate work into benchmark categories rather than a prompt: Deep Research Bench has an explicit "Populate Reference Class" category (10 of 89 instances) and a "Derive Number" Fermi category (10 instances) ([arxiv.org/abs/2506.06287](https://arxiv.org/abs/2506.06287)). They also publish the failure mode: base rates get "extrapolated without checking whether the generating mechanism is still active" ([futuresearch.ai/blog/history-doesnt-repeat](https://futuresearch.ai/blog/history-doesnt-repeat)).

**The only large controlled test.** Schoenegger, Jones, Tetlock, Mellers, "Prompt Engineering Large Language Models' Forecasting Capabilities" ([arxiv.org/abs/2506.01578](https://arxiv.org/abs/2506.01578)). Study 1: 38 prompts, 100 ForecastBench questions, 4 models (GPT-4o, Claude 3.5 Sonnet, Claude 3.5 Haiku, Llama 3.1 405B), roughly 3,700 forecasts per model, preregistered mixed-effects model with Benjamini-Hochberg correction. Difference from control in Brier, negative is better:

| Prompt | Mean diff (SD) | t | adjusted p |
|---|---|---|---|
| Frequency-Based Reasoning | **-0.019** (0.114) | -3.267 | **0.022** |
| Base Rate First | **-0.016** (0.106) | -2.971 | **0.036** |
| Step-Back | -0.015 (0.107) | -2.835 | **0.036** |
| Multiple Reference Classes | -0.009 (0.113) | -1.588 | 0.233 |
| Anti-Biasing (Overconfidence) | -0.004 (0.070) | -1.241 | 0.362 |
| **Bayesian Reasoning** | **+0.025** (0.172) | +2.854 | **0.036 (worse)** |

Only three prompts survived correction, the two best are base-rate flavoured, and they are worth about 0.016 to 0.019 Brier. Explicitly telling the model to reason in a Bayesian way made it **significantly worse**. Study 2 killed even that: with 18 compound prompts across o1, o1-mini, GPT-4o, Claude 3.5 Sonnet and Llama 3.1 405B, "Base Rate First + Frequency-Based Reasoning" came in at **-0.004 (adjusted p = 0.985)** and after correction no prompt improved or reduced performance. The only significant Study 2 effect was a superforecaster-authored conditional odds-ratio prompt making things worse (+0.023, adjusted p = 0.01).

**The part relevant to a level error.** Mean forecast under the control prompt was 0.453 with mean absolute distance from 0.5 of only **0.134**. Base Rate First pulled the mean to **0.428** and Frequency-Based Reasoning to **0.427**, while the odds-ratio prompt sat at exactly 0.50. So base-rate framing shifts the whole distribution by roughly 2.5 percentage points. It moves the level a little; it does not fix it.

**Tournament survey evidence.** Metaculus's Fall 2025 survey, 39 respondents, 29 winners ([notebook 43337](https://www.metaculus.com/notebooks/43337/fall-2025-futureeval-survey/), summary in [43363](https://www.metaculus.com/notebooks/43363/ai-forecasting-in-2026/)): "explicitly calculating base rates in a rigorous way" correlates **r = +0.38, p = 0.032** within winners, used by **40% of top-15 winners versus 7% of the bottom half**. Looking up similar previously-resolved questions: 34% of top winners versus 0% of non-winners, Fisher p = 0.04. In Q1 2025, 5 of 10 prize winners explicitly calculated base rates. Metaculus's own verdict across 11 analyses: "Base-rate and frequency-based prompts may offer small, safe improvements, but the effect is **not robust enough to depend on**".

**The one large measured win from handing the model an anchor** is Schoenegger et al.'s Study 2, in 6.8 below: giving GPT-4 and Claude 2 the human crowd median improved accuracy by 17% to 28%. But read the caveat there, because a naive arithmetic average beat the model's own updating.

### 6.4 Metaculus AI Benchmark / FutureEval: results and architectures

Head-to-head score is bots minus the 10-person Metaculus Pro team on shared questions; negative means the humans won.

| Season | Bots | Questions (shared) | Head-to-head | p | Winner |
|---|---|---|---|---|---|
| Q3 2024 | 55 | 113 | -11.3 [-21.8, -0.7] | 0.036 | template bots placed high |
| Q4 2024 | 44 | 96 of 402 | -8.9 [-18.8, +1.0] | 0.079 | **pgodzinai**, peer score 13.2 [8.3, 18.1] |
| Q1 2025 | 45 | 96 | -17.7 [-28.3, -7.0] | 0.0007 | **manticAI** $7,685.18 |
| Q2 2025 | 54 (96 entries) | 93 of 348 | -20.03 [-28.63, -11.41] | 0.00001 | **Panshul42** $7,550 |
| **Spring 2026** | | **99** | **-1.25 [-4.87, +2.37]** | **0.247** | **GreeneiBot2** |

Sources: [Q4 2024](https://www.lesswrong.com/posts/P8YwCvHoF2FHQoHjF/metaculus-q4-ai-benchmarking-bots-are-closing-the-gap), [Q1 2025](https://www.lesswrong.com/posts/rDy5z8ZEtMrEGnfBd/q1-ai-benchmark-results-pro-forecasters-crush-bots), [Q2 2025](https://forum.effectivealtruism.org/posts/F2stjK9wHSy3HPEC9/q2-ai-benchmark-results-pros-maintain-clear-lead), [Q1 winners notebook](https://www.metaculus.com/notebooks/37692/winners-of-the-q1-2025-ai-forecasting-benchmark-tournament/), [Q2 winners notebook](https://www.metaculus.com/notebooks/39140/winners-of-q2-2025-ai-benchmark-tournament/), [Spring 2026](https://www.lesswrong.com/posts/wZBbDqzfBjYG58CxK/futureeval-spring-results-pros-beat-bots-but-the-gap-is).

The Spring 2026 collapse from -20.03 to -1.25 is the biggest trend in the series, though nine of the ten individual pros still finished ahead of every individual bot. By question type in Spring 2026: binary -2.51, numeric **+3.47** (bots won), multiple choice -5.02. Bots have always been worst on multiple choice (-32.9 in Q2 2025, -37.5 in Q1 2025), which is the type closest to JevFish's estimand.

Two qualifiers worth keeping in mind before assuming scaffolding is the win. In Q1 2025 the actual best score belonged to a **stock template bot**: "If you include the Metaculus-run template bots in the leaderboard, then our 1st place bot is actually the GPT-o1 template bot using AskNews" ([Q1 winners notebook](https://www.metaculus.com/notebooks/37692/winners-of-the-q1-2025-ai-forecasting-benchmark-tournament/)); manticAI won the prize money, not the score. In Spring 2026, "simple one-shot bots on frontier models placed in the top five of the leaderboard" ([metaculus.substack.com](https://metaculus.substack.com/p/metaculus-futureeval-ai-forecasting-benchmark)).

**The template bot, read from source** ([github.com/Metaculus/metac-bot-template](https://github.com/Metaculus/metac-bot-template) on [forecasting-tools](https://github.com/Metaculus/forecasting-tools)):

- `research_reports_per_question = 1`, `predictions_per_research_report = 5`, so **5 independent forecasts per question**.
- Aggregation: plain **median**, literally `return float(statistics.median(predictions))` ([binary_report.py line 79](https://raw.githubusercontent.com/Metaculus/forecasting-tools/main/forecasting_tools/data_models/binary_report.py)).
- Clipping: hard clamp, `decimal_pred = max(0.01, min(0.99, ...))`.
- Research: default `"asknews/news-summaries"`, alternative `SmartSearcher` at `num_searches_to_run=2, num_sites_per_search=10`.
- Output format: `"Probability: ZZ%", 0-100`.

**Winning architectures.**

- **pgodzinai (Q4 2024).** Grouped related questions to keep forecasts consistent, multi-paragraph prompts with forecasting principles, **filtered extreme values then averaged**, three runs of gpt-4o plus five runs of claude-3-5-sonnet-20241022, research via Perplexity and AskNews. Source not public.
- **Panshul42 (Q2 2025, $7,550).** 6 to 7 step agentic workflow, five agents: 2x Claude 3.7 Sonnet (later Sonnet 4), 2x o4-mini, 1x o3 with double weight "for ensemble diversity". Separate outside-view and inside-view research reports. Four research sources (Google Search API, Google News API, AskNews, Perplexity) with Serper and BrightData tooling. Aggregation described only as "weighted averaging based on model reliability"; the README mentions "statistical calibration using historical performance data" without specifying the function, bounds or extremising (FLAG).
- **nostreambot (Summer 2026, 15th of 277, about 3,240 spot peer points over 256 questions).** The most transparent open bot: [github.com/No-Stream/metaculus-bot](https://github.com/No-Stream/metaculus-bot). Three models, one each from OpenAI, Anthropic and Google, **median of three** on a shared research briefing. Research fans out over AskNews, OpenAI web search, Gemini grounded search, yfinance, FRED and a snapshot of Polymarket, Kalshi, Manifold and PredictIt prices, plus two gap-fill passes. Clipping at `BINARY_PROB_MIN = 0.02`, `BINARY_PROB_MAX = 0.98`. Four findings from their own postmortems that JevFish should read:
  - A "stacker" LLM that rewrites the forecast when the three models disagree "is in the code but off in production. In an 88-question test it scored no better than the median."
  - "The recurring finding is that **the worst misses come with all three models agreeing** on a shared briefing." That is correlated-error risk, which no amount of sampling fixes.
  - They implemented Platt scaling exactly as `logit(p_adj) = bias + slope * logit(p_raw)` and then **deliberately shipped it as the identity**, recording the reason verbatim: "Mean Brier improved by ~0.0015 binary / ~0.0001 MC on spring-aib-2026, and in-sample is optimistic", and "**Binary slope drifts from 0.83 (spring) to 1.66 (fall)** ... opposite calibration shapes between rounds".
  - They cap any non-identity fit at `PLATT_BINARY_MAX_ABS_DEVIATION = 0.10`.

**What the surveys say correlates with winning.** From Q4 2024 (13 respondents with positive peer scores), Q1 2025 (10 winners) and Fall 2025 (39 respondents):

| Technique | Evidence |
|---|---|
| Repeated LLM calls, median or mean | 76% of Q4 2024 winners; **10 of 10** Q1 2025 winners; 86% of Fall 2025 winners; optimal "3 to 7 diverse runs across model families" |
| **Custom question testing** (your own eval set) | coverage-adjusted **+2,216 points [+912, +3,519]** |
| **Aggregation strategy** | **+1,799 [+1,017, +2,582]** |
| Manual review of logs | 66% of Fall 2025 winners; +1,041 [-223, +2,305], not significant |
| Capping predictions at a max/min | 38% of Fall 2025 winners; **r = +0.48, p = 0.005**; 47% of top-15 versus 29% of bottom half; 5 of 10 Q1 winners |
| Base rates | 40% of top-15 versus 7% of bottom half; r = +0.38, p = 0.032 |
| Number of research sources | **r = 0.42, p = 0.006**; winners 1.75 sources versus non-winners 1.00; "no individual search provider gave a significant score advantage" |
| LLM calls per question | winners about **28**, non-winners **7**, p = 0.022; cost $1.40 versus $0.50 per question |
| Dev time | r = 0.08, not significant |
| Fine-tuning | 1 of 13 Q4 winners did any |
| Comparing to the community prediction | r = -0.32, p = 0.08 (weakly **negative**) |

The bot-makers' own free-text advice is blunt on the point that matters here: "**Clipping/extremization of final predictions is underused**" and "The community continues to **underrate the benefit of clipping** their predictions" ([notebook 43357](https://www.metaculus.com/notebooks/43357/bot-advice-fall-2025/)). One maker: "I cut number of forecasts to 1 which really hurt my average score ... due to the variance".

Metaculus's repeated conclusion is that the base model dominates: "the most important factor for good forecasting is the base model, and additional prompting and infrastructure on top of this provide marginal gains" ([Q1 analysis](https://www.metaculus.com/notebooks/38673/q1-ai-benchmarking-results/)). Fall 2025 quantified the other side: "top five scaffolded bots beat their non-scaffolded baseline by **5 to 11 peer-score points per question**", the bottom five lost 6 to 16, the spread within the GPT-5 family alone was about 27 points, and "good scaffolding is worth around **9 months of base model progress**".

**Calibration versus discrimination, the single most relevant finding to JevFish's diagnosis.** Q4 2024 measured both for pros and the best bot: "Both Pros and top bot appeared well-calibrated"; pros made more extreme forecasts (bottom quintile averaged **2% versus 7%** for the bot, top quintile **87% versus 76%**); pros' discrimination was **44 percentage points** between Yes and No resolutions versus pgodzinai's **26**. Stated plainly: **"The Pros' superior accuracy is not a result of better calibration; it is a result of better discrimination."**

**Metaculus's own calibration-adjustment replication** across 2025 Q1 and Q2 bot forecasts ([notebook 43356](https://www.metaculus.com/notebooks/43356/calibration-adjustment-analysis/)), out of sample (earliest 70% of each forecaster's questions for training, most recent 30% held out, forecasters with fewer than 500 forecasts excluded):

| Method | Binary Brier improvement | p | Multiple-choice improvement | p |
|---|---|---|---|---|
| **Logistic recalibration**, `adjusted = sigmoid((logit(p) - bias) / confidence)` | **0.016426** | 0.000523 | **0.005357** | 0.000053 |
| Uniform shift | 0.010440 | 0.001682 | -0.001838 | 0.999853 |
| Step shift | 0.010831 | 0.024139 | 0.004413 | 0.006016 |

External validation on the Centre for AI Safety "539" bot over 177 Metaculus questions: Brier **0.0999 to 0.0934**. Metaculus's own summary: significant on both question types, "absolute gains are small".

So the record on a fitted calibration layer is: clearly positive on pooled data (AIA +0.0064, Metaculus +0.0164 out of sample), clearly unstable per-bot across rounds (No-Stream's slope flipping 0.83 to 1.66), and unnecessary when the raw system is already calibrated (Halawi). JevFish's raw system is off by 32pp, so it is squarely in the case where the layer helps, but the instability warning means refit per configuration and cap the deviation.

**Automated prompt optimisation**, for completeness ([notebook 38421](https://www.metaculus.com/notebooks/38421/automated-prompt-engineering-for-forecasting/)): evolutionary search, 25 seed prompts, 112-question training set, 100 prompts total, tested on 230 questions, scored on expected baseline score. GPT-4.1-nano **11.72 (SD 4.89) optimised versus -6.35 (SD 7.96) control**; GPT-4.1 21.53 (4.02) versus 15.02 (6.28); DeepSeek-R1 16.28 to 18.11 optimised versus **20.30 (3.9) control**, that is, worse. Prompts transferred within a provider family and "performed poorly across providers".

### 6.5 FutureSearch

The most transparent of the three vendors: four arXiv papers with named authors, published confidence intervals, published leakage audits, and a published critique of its own competitors.

- Deep Research Bench, [arxiv.org/abs/2506.06287](https://arxiv.org/abs/2506.06287). 89 task instances, 8 categories, a RetroSearch frozen-corpus mode. Best model in the paper **o3 at 0.51 live, 0.46 on RetroSearch**; no formal human baseline (authors estimate a smart generalist reaches about 0.8). ChatGPT-o3 with web search beat OpenAI's dedicated Deep Research product. Live leaderboard now 169 tasks, last updated 10 June 2026: Opus 4.6 (high) **0.553** at $0.53 and 183s, Sonnet 4.6 (high) 0.549, Opus 4.5 (high) 0.548, GPT-5.5 (high) 0.540, down to GPT-5.4 (low) 0.351 ([drb.futuresearch.ai](https://drb.futuresearch.ai/)).
- Bench to the Future, a pastcasting benchmark, [arxiv.org/abs/2506.21558](https://arxiv.org/abs/2506.21558).
- Automating Forecasting Question Generation and Resolution, [arxiv.org/abs/2601.22444](https://arxiv.org/abs/2601.22444). 1,499 generated questions, about 96% verifiable, about 95% resolution accuracy. Brier 0.134 (Gemini 3 Pro), 0.149 (GPT-5), 0.179 (Gemini 2.5 Flash). **Question decomposition improved the score from 0.141 to 0.132.**
- Evaluating Strategic Reasoning in Forecasting Agents, [arxiv.org/abs/2604.26106](https://arxiv.org/abs/2604.26106). BTF-2, 1,417 questions, frozen 15M-document corpus. Their best forecaster is 0.011 Brier better than any single frontier agent. Human experts found frontier agents fail most on leaders' incentives, follow-through on stated intentions, and institutional process modelling.
- Towards a Realistic Long-Term Benchmark for Open-Web Research Agents, [arxiv.org/abs/2409.14913](https://arxiv.org/abs/2409.14913). A ReAct architecture with subagent delegation performed best.

**Architecture.** Research agents, then a **world-modelling pass** that "reconciles each answer against the shared drivers it has learned across thousands of forecasts", which they claim "improved all nine base forecasters we tested on BTF-3 (four of them significantly)" ([FORECAST API docs](https://futuresearch.ai/docs/reference/FORECAST/)). Two effort tiers: LOW at 3 to 5 minutes and $0.09 to $0.20 per row, HIGH at 5 to 10 minutes and about $1.20 per row.

**Their aggregation ablation, which is clean.** They take the **mean across four agent runs**. On 1,367 BTF-2 questions: a single Claude Opus 4.6 agent 0.130, a second independent Opus 4.6 run also 0.130, and the four-run mean (2x Opus 4.6 + Gemini 3.1 Pro + GPT-5.4) **0.125** ([futuresearch.ai/blog/run-agents-twice](https://futuresearch.ai/blog/run-agents-twice)). Ensembling four heterogeneous runs bought 0.005 Brier. Re-running the *same* model bought nothing.

**Self-published accuracy.** BTF-3, 2,386 resolved questions, June to August 2026: FutureSearch SOTA **0.116 [0.109, 0.123]**, Claude Opus 5 (xhigh) 0.120 [0.113, 0.128], Claude Opus 4.8 0.132, GPT-6 Astra (low) 0.135, GPT-5.6 Sol (medium) 0.137, Claude Sonnet 5 (xhigh) 0.142, GLM-5.3 0.149. Paired bootstrap margin over Opus 5: 0.0047 pooled, 95% CI [-0.0065, -0.0029], p < 0.001 ([evals.futuresearch.ai](https://evals.futuresearch.ai/)). BTF-2, last updated 2026-04-20: FutureSearch Agent **0.119 with a Murphy-decomposition calibration component of 0.002 and refinement 0.081**, Opus 4.6 Agent 0.130, Gemini 3.1 Pro 0.141, GPT-5.4 0.152, Grok 4.20 Beta 0.165.

**That calibration component of 0.002 out of 0.119 is the cleanest published statement that calibration is nearly free and discrimination is the whole game** for a system that is already well built. It is the counterweight to the AIA Platt result, and both are true: calibration is cheap to fix and therefore never the thing that separates the best systems, but it is exactly the thing separating JevFish from usable.

They disclose the comparison asymmetry themselves: "FutureSearch SOTA synthesizes forecasts from multiple FutureSearch agent runs" and "Claude Opus 5 is one of the agent runs it synthesizes from", so the 0.0047 margin is ensemble versus single run. They publish a five-part leakage audit and state what they cannot rule out.

**Independently checkable.** On ForecastBench, `fb_early_closer_v2` is **rank 18 of 334, Brier Index 67.5 [66.1, 69.0], N = 843**, against the superforecaster median at rank 3 with 68.8 [67.3, 70.5], and the significance column reads "No, p = 0.13". So they are statistically indistinguishable from superforecasters and **not above them** on the point estimate. Their own homepage claim of "#37 of 464" cites the **preliminary** board, which is explicitly non-final. Third-party summaries claiming FutureSearch sits above the superforecaster median are not supported by the live data (FLAG).

### 6.6 Mantic and Lightning Rod Labs

Both publish claims that were true at an earlier leaderboard snapshot and have since decayed. Both appear on ForecastBench, where they can be checked, and on the live board (file last modified 18 September 2026) **both are significantly worse than the superforecaster median.**

**Mantic.** The Q1 2025 Metaculus prize win is real: manticAI $7,685.18, first place ([winners notebook](https://www.metaculus.com/notebooks/37692/winners-of-the-q1-2025-ai-forecasting-benchmark-tournament/)), with Metaculus's own qualifier in the same notebook that the actual best score went to the GPT-o1 template bot with AskNews.

Their one real technical writeup is a guest post on Thinking Machines Lab, 19 March 2026 ([thinkingmachines.ai](https://thinkingmachines.ai/news/training-llms-to-predict-world-events/)): base model `gpt-oss-120b`; policy gradient with GRPO-style advantage normalisation plus importance-sampling corrections on the advantages; **Brier score as the reward**, chosen over log score for bounded variance and more stable training; Tinker with vLLM sampling and FSDP; about **10,000 binary questions, August 2024 to December 2025**; batch size 64, group size 8; held-out test is Metaculus Q2 2025. Result: **baseline 38.6 to 45.8, +7.2 points. Without research or tools the gain is only about +3.** Their best ensemble weighting is 40% fine-tuned gpt-oss-120b, 20% each Gemini 3 Pro, GPT-5, Grok 4, that is, a **4-model ensemble**. No calibration metrics reported (FLAG).

Their homepage claims "Ranked **4th out of 539** humans in the Metaculus Cup, the best AI result to date, as reported by Bloomberg, The Guardian, and Time Magazine" ([mantic.com](https://www.mantic.com/)). Metaculus's Summer 2025 Cup notebook says: "congratulations to manticAI who came in **8th**, the best rank a bot has ever achieved competing with human forecasters" ([notebook 39990](https://www.metaculus.com/notebooks/39990/winners-of-the-summer-2025-metaculus-cup/)). TIME reports "**eighth out of 549 contestants**" and adds Metaculus's caveats: a small 60-question sample, most of the 600 contestants are amateurs, the bot had a coverage advantage from constant updating, and it trailed the Community Prediction by five places ([time.com](https://time.com/7318577/ai-model-forecasting-predict-future-metaculus/)). **Their cited source says 8th of 549; they claim 4th of 539.** Their own homepage chart shows Metaculus Cup rank going 4th, 8th, 34th, 39th across four seasons.

ForecastBench, live: `mantic-2026-01-16` **rank 49 of 334, 66.0 [65.3, 66.6], N = 3,089**, supers significantly better at p < 0.001. `mantic-2026-03-01` rank 127 at 64.1. `mantic-light-2025-10-testing` rank 250 at 59.5, barely above the naive Imputed Forecaster baseline at 59.4. Their newest submission is dated 1 March 2026 and scored worse than their January one. They do not cite ForecastBench anywhere on their site.

**Lightning Rod Labs.** The genuinely distinctive and verifiable contribution is the training method, and it is directly relevant to calibration.

- "Future-as-Label: Scalable Supervision from Real-World Outcomes", Turtel, Wilczewski, Franklin, Skothiem, [arxiv.org/abs/2601.06336](https://arxiv.org/abs/2601.06336). Timestamped historical documents provide a cutoff, questions are generated from source material, ground truth comes from post-cutoff publications. Training is "Foresight Learning", an RLVR adaptation with multiple independent rollouts per question scored by proper scoring rules, reinforcing calibrated predictions and penalising overconfident ones. **27% Brier improvement for Qwen3-32B, calibration error reduced by 50%, and Qwen3-32B outperforming Qwen3-235B despite roughly 7x fewer parameters.**
- "LLMs Can Teach Themselves to Better Predict the Future", [arxiv.org/abs/2502.05253](https://arxiv.org/abs/2502.05253). Self-play generates diverse reasoning trajectories, ranks pairs by distance to the actual outcome, fine-tunes by DPO. **+7 to 10% accuracy** for Phi-4 14B and DeepSeek-R1 14B over base and over a randomised-label DPO control.
- "Outcome-based Reinforcement Learning to Predict the Future", [arxiv.org/html/2505.17989v3](https://arxiv.org/html/2505.17989v3). DeepSeek-R1-Distill-Qwen-14B, reward is the **negative Brier score**. Their **Modified GRPO removes standard-deviation normalisation** because per-question normalisation "can excessively dampen large errors and encourage overconfidence". Results: ReMax Ensemble-7 at 100k training data, soft-Brier **0.190 [0.178, 0.203], ECE 0.062**, versus OpenAI o1 at soft-Brier 0.202, ECE 0.093, from a model likely 1 to 2 orders of magnitude smaller. The extremity control is the number to note: **predictions landing in extreme buckets dropped from 39.3% under standard GRPO to 7.9%** under modified GRPO, with guardrails at 13.1%. Polymarket simulation: about 10% ROI overall, about 20% on low-market-confidence questions ($52 profit on $433 cost).

Self-run numbers with no independent verification (FLAG): Foresight V4, 1 July 2026, on "high-volume Polymarket questions resolved in Q1 2026" with **sample size not disclosed**, Brier Skill Score V4 Full +25.9%, V4 Low +21.2%, V3 +22.4%, GPT-5.4 +19.1%, GPT-5 +16.3%, Gemini 3.1 Pro +13.7%, Opus 4.6 +12.6%; raw Brier for V4 Full 0.1633, ECE 0.0645; $3.30 per 1,000 forecasts for V4 Low. Their [models page](https://www.lightningrod.ai/models) gives different figures (26% / 13% / 19%), so their two surfaces disagree. Domain claims (SEC risk, Fed Beige Book, supply chain, MIMIC-III) are all self-run without sample sizes.

Decayed claims (FLAG): they claim Foresight V3 "ranks first overall on ProphetArena" ([blog, 2 April 2026](https://blog.lightningrod.ai/p/how-we-built-the-number-1-ai-forecaster)). On the live board, last scored 16 September 2026, **Foresight V3 is rank 20 with 1-Brier 0.7923, marked retired**; the top five are Agent Gemini 3.1 Pro 0.7981, Agent GPT-5.6 Sol 0.7980, **Kalshi Markets 0.7979**, Agent Claude Fable 5 0.7967, Claude Fable 5.1 0.7961; Foresight V4 does not appear at all ([prophetarena.co/leaderboard](https://www.prophetarena.co/leaderboard/forecast)). Their post "AI Reaches Human SuperForecaster Range" (8 July 2026) claimed Foresight-v3 at 67.7, rank 4, against supers at 69.3; today `foresight-v3` is **rank 103 of 334 at 64.5 [63.6, 65.4]**, and their best entry `Foresight-32B` is rank 56 at 65.6 [63.9, 67.3] with supers significantly better at p < 0.01.

Funding is grant-based: $1.6M (September 2026) from Coefficient Giving and Longview Philanthropy, approved for DARPA ERIS and CDAO Tradewinds ([lightningrod.ai/about](https://www.lightningrod.ai/about)). Models are on [Hugging Face](https://huggingface.co/LightningRodLabs).

**The transferable point from both vendors**: the strongest specialist systems train on a **proper scoring rule as the objective**, Mantic states the practical reason to prefer Brier over log score (bounded variance, stable training), and Lightning Rod's modified GRPO shows that removing per-question variance normalisation is what stops the model becoming overconfident. JevFish cannot fine-tune Jev, but it should use Brier rather than log loss as the fitting objective for its calibration map, for exactly the stability reason Mantic gives.

### 6.7 Aggregation and post-processing: what actually works

Consolidating the numbers above plus the ForecastBench baseline:

- **The aggregator barely matters.** AIA: median 0.1138, mean 0.1140, trimmed mean 0.1142, spread 0.0004. Halawi: trimmed mean 0.1649, median 0.1651, geometric 0.1655, mean 0.1656, spread 0.0007. ForecastBench's own LLM crowd baseline (9 forecasts, 3 models x 3 superforecaster-written prompts, temperature 0): **median 0.155, geometric mean 0.157, geometric mean of log odds 0.157** on one question set and 0.161 / 0.162 / 0.162 on another ([ForecastBench paper Appendix J.3](https://faculty.wharton.upenn.edu/wp-content/uploads/2026/02/ForecastBench_A_Dynamic_.pdf)). **Log-odds pooling did not beat the median**, and the whole crowd at 0.155 was far worse than the best single model with the right context at 0.122.
- **Never let an LLM do the blending.** Halawi's Universal Self-Consistency 0.1691 versus trimmed mean 0.1649 and no ensemble 0.1676. AIA's best-of-k 0.1191 and non-agentic supervisor 0.1168 versus mean 0.1140. No-Stream's stacker scored no better than the median on 88 questions. The only LLM aggregator that beat the mean is AIA's **agentic** supervisor, which earns it by issuing fresh search queries to resolve disagreement: 0.1125 versus 0.1140.
- **Sample count saturates at 5 to 10.** AIA: sharp 1 to 5, modest to 15, standardise at 10, total gain 0.0044. Wang et al. on self-consistency: "performance saturates quickly", 5 or 10 paths. Xiong et al. swept M = 1 to 13 and found the improvement becomes marginal. Tian: n = 20 gave no meaningful improvement over n = 10.
- **Model count has an optimum and then degrades.** "Don't Always Pick the Highest-Performing Model" ([arxiv.org/abs/2602.08003](https://arxiv.org/abs/2602.08003), preprint), 12-model pool: best average error at **k = 4 to 6** (0.144 at k = 4, 0.141 at k = 6) versus top-k-by-accuracy at 0.150 and 0.149, degrading to **0.171 for all methods by k = 13**. They derive an information-theoretic error floor from a Gaussian copula of correlated errors and warn that "adding another high-accuracy model may contribute little new information or may even degrade performance if it reinforces the same mistakes". Metaculus Spring 2026 independently found optimal bot-team size 2 to 10, declining after 10. Mantic's optimum was 4.
- **Clipping is universal among winners.** Metaculus template [0.01, 0.99]; No-Stream [0.02, 0.98]; Lightning Rod's guardrails force near-zero forecasts above zero; 38% of Fall 2025 winners cap, correlating r = +0.48, p = 0.005.
- **Extremising coefficient theory.** Satopaa et al. recommended a scaling factor of 2 and found the optimal factor on geopolitical questions in d in [1.161, 3.921]. Neyman and Roughgarden give `d = n(sqrt(3n^2 - 3n + 1) - 2)/(n^2 - n - 1)`, which tends to **sqrt(3)** as n grows ([EA Forum summary](https://forum.effectivealtruism.org/posts/biL94PKfeHmgHY6qe/principled-extremizing-of-aggregated-forecasts)). The caveat that applies to a persona crowd: "the average forecast of a team of superforecasters often requires very little or no extremizing. Their forecasts are highly convergent." Extremising corrects for averaging failing to accumulate independent information. If your crowd shares essentially all its information, the correct coefficient is small, and your level error is a **bias term needing a shift**, not an underconfidence problem needing a slope.
- **Which direction to correct depends on the task, and getting it wrong makes things worse.** Toward the extremes (hedging) is the forecasting case: AIA's 0.5 attenuation quotes, Halawi's underconfidence, Schoenegger's mean absolute distance from 0.5 of only 0.134 across 14,781 forecasts, FutureSearch's case studies of a model computing 1.34M ballots against a 1.3M threshold and then assigning 25% ([futuresearch.ai/blog/ais-underconfident](https://futuresearch.ai/blog/ais-underconfident), anecdotal). Toward 0.5 (overconfidence) is the QA case: Xiong et al. measured verbalised confidence "primarily range between 80% and 100%, often in multiples of 5 ... indicating significant overconfidence" ([arxiv.org/abs/2306.13063](https://arxiv.org/abs/2306.13063)), and Chhikara measured ECE 0.750 for GPT-4o-mini and 0.810 for LLaMA-3-8B on SimpleQA ([arxiv.org/abs/2502.11028](https://arxiv.org/abs/2502.11028)). Both directions appear **in the same model**: Groot and Valdenegro-Toro's Net Calibration Error (positive is underconfident) gives GPT-4 **+13.5** on binary sentiment and **-6.8** on math word problems, GPT-3.5 +0.15 and **-74.8**, LLaMA2-70B +10.4 and -51.7, PaLM 2 +10.6 and -43.6 ([arxiv.org/abs/2405.02917](https://arxiv.org/abs/2405.02917)). Classical theory says averaging "tends toward underconfidence" ([Lichtendahl, Grushka-Cockayne, Jose, Winkler, arxiv.org/abs/1705.02391](https://arxiv.org/abs/1705.02391)) while also showing "optimal aggregators do not always extremize the average forecast". **Fit the direction, do not assume it, and refit when the model or prompt changes.**

### 6.8 Prompting for calibration: the picture is messier than the headline

The literature does **not** support a flat "verbalised beats logprobs". It supports: verbalised numeric confidence usually wins on **ECE** for large RLHF'd closed models on short-form factual QA; it loses on **AUROC and discrimination** almost everywhere; it loses on both for small open models; and it is so heavily discretised onto round numbers that a good ECE can be an artefact. Note also that ECE is defined differently in each paper (Tian uses squared per-bin error, Kadavath uses 10 equal-mass bins with mean absolute difference, Yang uses 20 bins, Chhikara uses bin width 0.1), so compare only within a paper.

**Tian et al. 2023, "Just Ask for Calibration"** ([arxiv.org/abs/2305.14975](https://arxiv.org/abs/2305.14975), EMNLP 2023). 1,000 TriviaQA, 1,000 SciQ, all 817 TruthfulQA. Important: their logprob baseline ("Label prob.") is **estimated from n = 10 samples**, not true token logprobs, because the closed models do not expose them; n = 20 "did not meaningfully improve" it. Headline: verbalised confidences are typically better calibrated than the model's conditional probabilities, "often reducing the expected calibration error by a relative 50%".

gpt-3.5-turbo, ECE then AUC:

| Method | TriviaQA | SciQ | TruthfulQA | TriviaQA AUC | SciQ AUC | TruthfulQA AUC |
|---|---|---|---|---|---|---|
| Label prob. (10-sample frequency) | 0.140 | 0.256 | 0.451 | 0.869 | 0.752 | 0.418 |
| 'Is True' prob. | 0.164 | 0.312 | 0.470 | 0.826 | 0.677 | 0.384 |
| Verb. 1S top-1 | 0.068 | 0.234 | 0.389 | 0.879 | 0.744 | 0.545 |
| Verb. 1S top-4 | 0.054 | **0.065** | 0.203 | **0.896** | 0.763 | 0.455 |
| Verb. 2S CoT | 0.110 | 0.323 | 0.419 | 0.830 | 0.683 | **0.551** |
| Ling. 1S-opt. | 0.058 | 0.064 | **0.125** | 0.878 | 0.674 | 0.492 |

GPT-4: Label prob. 0.078 / 0.219 / 0.445; Verb. 1S top-1 **0.024** / 0.201 / 0.350; Ling. 1S-opt 0.056 / **0.028** / **0.082**. **Claude-1 is the counterexample**: Label prob. 0.074 / 0.216 / 0.432 versus Verb. 1S top-1 0.049 / **0.265** / **0.440**, worse on two of three, and the paper says Claude-1 "is less able to verbalize well-calibrated confidences". Llama-2-70b-chat improves ECE (0.151 to 0.060 on TriviaQA) but **degrades AUC** (0.865 to 0.815).

Relative ECE reductions across their tables: gpt-3.5-turbo 66 / 75 / 55 percent, GPT-4 69 / 74 / 56, claude-1 38 / 30 / 14, claude-2 45 / 74 / 33, Llama-2-70B 60 / 61 / 43. So "50%" is conservative for GPT and optimistic for Claude-1.

Their conclusions: multi-hypothesis "top-k" formats beat single-hypothesis; **numbers do as well as or better than words**; **chain-of-thought does not improve verbalised calibration**; RLHF worsens logprob calibration on both ECE and AUC while verbalised confidence reverses some of that degradation.

Load-bearing caveat: `Ling. 1S-opt.`, which produces most of their best SciQ and TruthfulQA numbers, is **not zero-shot elicitation**. It "uses a held out set of calibration questions and answers to compute the average accuracy for each likelihood expression", which is post-hoc recalibration of a 10-level scale. The unfitted human-survey version is far weaker (TruthfulQA 0.306 versus 0.125). Their ECE-t columns are also temperature-scaled.

**Lin, Hilton, Evans 2022** ([arxiv.org/abs/2205.14334](https://arxiv.org/abs/2205.14334), TMLR), GPT-3 175B on CalibratedMath. Trained on Add-subtract (median accuracy 21%), evaluated on Multi-answer (65%) and Multiply-divide, so the shift requires *higher* confidence at test. MSE is the Brier score, MAD is mean absolute deviation calibration error, percentages:

| Setup | Multi-answer MSE | Multi-answer MAD | Multiply-divide MSE | Multiply-divide MAD |
|---|---|---|---|---|
| **Verbalized numbers (finetune)** | **22.0** | **16.4** | 15.5 | 19.0 |
| Answer logit (zero-shot) | 37.4 | 33.7 | **10.4** | 9.4 |
| Indirect logit (finetune) | 33.7 | 38.4 | 11.7 | **7.1** |
| Constant baseline | 34.1 | 31.1 | 15.3 | 8.5 |

Verbalised wins on the distribution-shifted set and **loses to the raw answer logit on the harder in-format set**. Their own summary: "Verbalized probability overfits to training. Calibration for verbalized probability is much better in-distribution." Few-shot reaches fine-tuned performance at **k = 50** examples. Their footnote 7 is the earliest statement of the granularity problem: "the finetuned GPT-3 will only output a verbal probability (e.g. 96%) **if that precise token ('96%') appeared during training**. This would explain the lack of smoothness in the calibration curves."

**Kadavath et al. 2022** ([arxiv.org/abs/2207.05221](https://arxiv.org/abs/2207.05221), Anthropic, models to 52B). Reports essentially no numeric ECE in text; calibration lives in figures (FLAG). P(IK) AUROC / Brier at 52B, training on all tasks except GSM8K: TriviaQA 0.873/0.145, Mixed-Arithmetic **0.987/0.042**, LAMBADA 0.853/0.108, Python synthesis 0.881/0.109, GSM8K 0.752/0.121.

Three findings that matter for JevFish's frame design, verbatim:

- **Format**: "It is crucial that the model gets to see the answer choices explicitly before choosing amongst them; without this, we would not expect a calibrated response, due to ambiguities and degeneracies among possible paraphrases ... task formatting is important for achieving excellent calibration, and calibration improves as we pass from 0-shot to 5-shot evaluation. We expect calibration is also easier to achieve with this format because **each answer option corresponds to a single token**." Replacing an option with "none of the above" "reduces accuracy and calibration significantly". That last point is a direct warning about a "books nothing" option.
- **Hedging at 0.5**: "Zero-shot, P(True) is poorly calibrated, and typically it lies **close to 50% for typical samples**." Fixing it required few-shot evaluation and showing multiple samples; 5 samples asking about one of them at 20-shot gave the best Brier in every case, and "larger k for k-shot self-evaluation seems to primarily help by improving calibration, rather than by improving the AUROC".
- **RLHF and temperature**: RLHF policies "naively appear very miscalibrated ... However, a **simple temperature adjustment (with the same temperature T = 2.5 for all evaluations) largely fixes calibration issues**." A one-parameter fix, and the direct precursor of Tian's result.

**Xiong et al. 2023, which contradicts Tian's headline** ([arxiv.org/abs/2306.13063](https://arxiv.org/abs/2306.13063), ICLR 2024), 8 datasets, 5 models. Vanilla verbalised ECE x100 averaged over 8 datasets: GPT-3 **52.0**, Vicuna 46.1, LLaMA 2 43.6, GPT-3.5 37.7, GPT-4 **18.0**; average AUROC 51.3, 52.5, 56.4, 55.1, **62.7**. Verbatim: "GPT-4 displays lower ECE, its AUROC and AUPRC-Negative scores remain suboptimal, with an average AUROC of merely 62.7%, **close to the 50% random guess threshold**." White-box comparison on GPT-3 with a Top-K prompt (5-dataset means): verbalised ECE 51.93 / AUROC 54.20, sequence probability 22.35 / 60.32, length-normalised 54.94 / 60.48, key-token probability 42.63 / 62.48. Their verdict: "white-box methods exhibit better performance", with the gap quantified as "0.522 to 0.605 in AUROC".

Their ECE-is-gameable warning is the one to remember: "with the CoT prompting on the GSM8K dataset, GPT-4 with 93.6% accuracy achieves a near-optimal **ECE 0.064 by assigning 100% confidence to all samples**. However, since all samples receive the same confidence, it is challenging to distinguish between correct and incorrect samples." Their recommendation is "Top-K prompt + Self-Random sampling + Avg-Conf or Pair-Rank aggregation"; GPT-4 with Top-K + Self-Random reached Pair-Rank mean ECE **6.90 (SD 0.2)** / AUROC 67.6.

**The arbitration, 2026.** Yang, Tsai, Yamada, "On Verbalized Confidence Scores for LLMs" ([arxiv.org/abs/2412.14737](https://arxiv.org/abs/2412.14737), v2 May 2026), 10 models, 17 prompt methods including 7 taken verbatim from Tian and Xiong: "we empirically verified the disagreement between Tian et al. and Xiong et al. ... the vanilla prompt method `tian2023_top1` returns better calibrated scores than `xiong2023_vanilla`, in particular for large LLMs. This suggests the calibration of verbalized confidence scores is **not inherently good or bad, but heavily depends on how we ask for it**." For models of 70B and above the ECE is around 0.1; their best prompt reached aggregated ECE 0.07 and reliability panels as low as 0.02; the smallest model (gemma1.1-2b) was 0.31 and "almost independent from its accuracy". Prompt design changed the number of distinct confidence values used by roughly **6x** (15 to 91).

**Round-number clustering, which is the finding that matches JevFish's own data exactly.**

Cause: Zhou, Jurafsky, Hashimoto ([arxiv.org/abs/2302.13439](https://arxiv.org/abs/2302.13439), EMNLP 2023) queried the Pile and found "drastic imbalances in the use of percentages in training datasets ... significant spikes in frequency at the upper extremes (50%, 95% and 100%) ... peaks at every 10 and 5 intervals".

Magnitude: Dai and Wang 2026 ([arxiv.org/abs/2603.09309](https://arxiv.org/abs/2603.09309), preprint), six frontier models, three datasets, standard [0, 100] scale: **the single most frequent value accounts for 35.6% to 68.4% of all responses, the top three values cover 78.2% to 92.1%, and models use only 15 to 28 distinct integers out of 101**, with entropy 0.95 to 1.88 bits against 6.66 for uniform. Conditional accuracy at the top-1 confidence value is off by 10 to 29 percentage points. **Their fix, replicated across all seven models tested: use a [0, 20] scale**, which raises metacognitive efficiency over [0, 100] for every model (p < 0.05, Bonferroni-corrected): GPT-5.2 0.95 versus 0.92, Qwen3-30B 0.68 versus 0.62, Llama-3-8B-Instruct 0.79 versus 0.71. Boundary compression hurts: restricting to [60, 100] drops GPT-5.2 from 0.92 to 0.69.

Sun, Sun, Geng 2026 ([arxiv.org/abs/2606.22179](https://arxiv.org/abs/2606.22179), preprint), 25 model-dataset pairs: verbalised confidence "ranks cases surprisingly well" (normalised PR-AUC 0.41 to 0.95, mean 0.80) "yet takes only a handful of distinct values ... a **median of 58% of test cases share Verb's single most common acceptance level**, and Verb offers only 1 to 13 distinct levels (median 6)". Two warnings: **"requesting three-decimal confidences degrades PR-AUC in all six tested pairs"** (PubMedQA with GPT-4o-mini fell 0.936 to 0.580), and logprobs have their own saturation problem, "65 to 94% of its mass saturates at q > 0.99".

Mechanical warning from Wang et al. ([arxiv.org/abs/2410.06707](https://arxiv.org/abs/2410.06707), Amazon): applying softmax temperature scaling to an already-normalised verbalised distribution **re-softmaxes it and is not a correct calibration procedure**; their invert-softmax-then-temperature fix cut ECE from 16.9% to 4.9% (Mixtral, Emotion) and 14.5% to 7.2% (Claude-v2, Massive), with fitted optimal temperature both above 1 (overconfident) and below 1 (Claude-v3 on IMDB, 0.64).

**Forecasting-specific: probes on internal activations beat verbalised confidence.** "What LLM Forecasters Know but Don't Say" ([arxiv.org/abs/2607.08046](https://arxiv.org/abs/2607.08046), preprint). Eternis-Forecaster 8B on OpenForesight, N = 3,020: probe and verbalised confidence are statistically indistinguishable as rankers (**AUROC 0.756 versus 0.758**) but differ sharply in calibration (**ECE 0.044 versus 0.093**). Out of distribution: skysports 0.064 versus 0.089, aljazeera 0.140 versus 0.178. Probe-only on frozen models: GLM-4.7-Flash probe AUROC 0.768 / ECE **0.054** versus verbalised 0.669 / **0.287**. The error shape: "**Verbalized confidence is nearly calibrated below 0.5 and systematically overconfident above it: rollouts stated at 0.93 resolve correct 70% of the time, and those stated at 0.75 only 44%.**" And the hedging, over 29,600 generations at 10 temperatures: "**confidence sits near 50% against about 37% accuracy and barely moves**, even as the rollouts disagree more".

**Post-hoc recalibration of verbalised scores, the clearest head-to-head.** "Wired for Overconfidence" ([arxiv.org/abs/2604.01457](https://arxiv.org/abs/2604.01457), COLM 2026), Appendix I Table 7, calibrators fitted on a labelled 50% split of the verbalised scores and evaluated on the disjoint half, 10-bin ECE:

| Model / dataset | Raw | Temp. scaling | **Platt** | Isotonic | Histogram |
|---|---|---|---|---|---|
| Llama-3.2-3B / PopQA | 0.568 | 0.302 | **0.008** | 0.075 | 0.147 |
| Qwen2.5-3B / NQOpen | 0.555 | 0.304 | **0.016** | 0.054 | 0.033 |
| Llama-3.2-3B / MMLU | 0.176 | **0.021** | 0.026 | 0.078 | 0.232 |
| Llama-3.2-3B / NQOpen | 0.507 | 0.245 | **0.036** | 0.057 | 0.191 |

**Platt wins 3 of 4, cutting ECE by 85 to 99 percent. Single-temperature scaling is the weakest parametric method on the three high-ECE rows (only 47 to 52 percent reductions), and histogram binning actively hurts on MMLU.** Single temperature underperforms precisely because a score concentrated on two or three values has no temperature that spreads it, which is exactly JevFish's situation with 30 distinct values across 801 personas. So the two-parameter Platt map is the right choice over one-parameter temperature scaling, on measured evidence, for this specific failure shape.

Data efficiency, from the largest study on verbalised confidence (9 LLMs, 13 BLURB datasets, [JAMIA Open 8(4):ooaf058](https://academic.oup.com/jamiaopen/article/8/4/ooaf058/8196848)): histogram binning and isotonic regression each cut average Flex-ECE by **23.5 and 23.6 percentage points** with 1,000 calibration examples, and "**as few as 100 examples proved sufficient** to provide a large and consistent reduction", over 75% on average. By elicitation strategy: self-consistency 27.3% mean error, verbal 42.0%, hybrid 44.2%.

Training the model to verbalise also works: ConfTuner ([arxiv.org/abs/2508.18847](https://arxiv.org/abs/2508.18847), NeurIPS 2025) uses a tokenised Brier loss proved to be a proper scoring rule and cut Llama-3.1-8B-Instruct average ECE from **0.2768 to 0.1082** across five datasets while raising average AUROC from 0.5923 to 0.6740. Their Table 16 is the fair comparison: against logprob-based P(True), AUROC is essentially tied (0.6690 versus 0.6740) while ECE is 0.3427 versus 0.1082.

### 6.9 Crowd of LLMs versus a single LLM

**Schoenegger, Tuminauskaite, Park, Bastos, Tetlock (2024), "Wisdom of the Silicon Crowd."** Science Advances 10(45), DOI [10.1126/sciadv.adp1528](https://www.science.org/doi/10.1126/sciadv.adp1528), preprint [arxiv.org/abs/2402.19379](https://arxiv.org/abs/2402.19379). 12 LLMs, **31 binary questions**, three-month tournament, 925 human forecasters, 1,007 individual forecasts collected. Aggregation is the median across models per question.

| Forecaster | Brier | SD | Calibration Index |
|---|---|---|---|
| GPT-4 | **0.15** | 0.11 | 0.075 |
| GPT-4 with Bing | 0.16 | 0.11 | 0.088 |
| Bard (PaLM 2) | 0.19 | 0.17 | 0.071 |
| **Human crowd (public median)** | **0.19** | 0.19 | |
| **LLM crowd (median of 12)** | **0.20** | 0.12 | **0.041** |
| Falcon-180B | 0.21 | 0.13 | **0.027** |
| Claude 2 | 0.21 | 0.16 | 0.082 |
| Solar-0-70B | 0.22 | 0.16 | 0.081 |
| PaLM 2 (Chat-Bison@002) | 0.23 | 0.15 | 0.068 |
| Mistral-7B-Instruct | 0.24 | 0.16 | 0.080 |
| Qwen-7B-Chat | 0.24 | 0.17 | 0.055 |
| GPT3.5-Turbo-Instruct | 0.25 | 0.20 | 0.106 |
| Llama-2-70B | 0.25 | 0.16 | 0.071 |
| Coral (Command) | 0.38 | 0.40 | 0.212 |
| No-information benchmark | 0.25 | | |

- LLM crowd versus benchmark: t(30) = -2.35, p = 0.026 (BH-adjusted 0.039).
- LLM crowd versus human crowd: t(60) = 0.19, p = 0.850, not significantly different, and equivalent within medium-effect-size bounds. The authors' own caveat: "bounds of 0.08 in Brier scores are wide".
- ANOVA across models F(12,354) = 2.64, p = 0.002; Tukey HSD found only Coral significantly worse.
- **The 12-model crowd (0.20) was beaten by GPT-4 alone (0.15).** The paper notes the aggregate "is numerically lower than 9 out of the 12 individual models. However, this difference is not statistically significant after adjustments." This is a **variance-reduction result, not an accuracy-gain result.** Aggregation improved the calibration index over 11 of 12 members but did not beat the single best member (0.041 versus Falcon's 0.027).

**The level bias, which is JevFish's symptom measured in a forecasting setting.** Raw forecasts spanned 0.1% to 99.5% with a median of 60%: "the mean forecast value of the crowd **M = 57.35 (SD = 20.93) being significantly above the 50% mark, t(1006) = 86.20, p < 0.001**", while **14 of 31 questions (45.2%) resolved positively**. That is roughly a **+12 percentage point systematic yes-bias**, with orderings intact. The authors' own verdict is "poor calibration of most models and overconfidence of the aggregate ... models overpredict outcomes compared to their actual rate of occurrence".

**Study 2, handing the model the human median.** 186 primary and 186 updated forecasts. GPT-4 **0.17 (SD 0.13) to 0.14 (SD 0.11), p = 0.003**. Claude 2 **0.22 (SD 0.19) to 0.15 (SD 0.14), p < 0.001**. That is the 17% to 28% improvement. Prediction intervals narrowed (GPT-4 17.75 to 14.22, Claude 2 11.67 to 8.28, both p < 0.001) and adjustment size tracked initial deviation (r = 0.88 and 0.87). **The part nobody quotes**: both models' updated forecasts were significantly **worse than a naive 50/50 arithmetic average** of the machine and human medians, "for both GPT-4 at a Brier score of 0.13, t(92) = 2.583, p = .011, and Claude 2 at a Brier score of 0.14, t(92) = 3.530, p = .001 ... the updating itself is directionally correct but **fails to improve upon a simple benchmark**."

So the correct way to use an anchor is to **blend it arithmetically, outside the model**, not to put it in the prompt and ask the model to update. That is a direct design instruction for JevFish.

**The replication that reverses the crowd result.** Douven, "Wisdom of LLM Crowds" ([arxiv.org/html/2607.18269v2](https://arxiv.org/html/2607.18269v2), 2026 preprint, **unrefereed**). 15 LLMs, 254 Manifold questions, plus a **94-item contamination-free subset (44 YES, 50 NO) resolving after 1 September 2025**, past every model's cutoff. Clean-subset Brier:

| Aggregator | Brier |
|---|---|
| **Logistic regression (learned)** | **0.241** |
| MLP (learned) | 0.264 |
| Arithmetic mean | 0.313 |
| **Median (the Schoenegger method)** | **0.343** |
| Geometric / log-odds mean | 0.360 |
| Harmonic mean | 0.378 |

Best single model on the full 208-item set: Claude Sonnet 4.6 at 0.273. **On uncontaminated questions the median crowd (0.343) was worse than always predicting 0.5 (0.25) and worse than the best single model.** Only a learned aggregator fitted on resolved historical questions reached 0.241, a 23% cut versus the arithmetic mean (sign test 62 of 94, p = .002; Wilcoxon z = -2.48, p = .013). Contamination effects: accuracy differential within versus outside cutoff up to **+0.256**; Spearman rho = 0.532 between full-set and clean-set model rankings. Human prediction markets beat the LLM arithmetic mean by **2.01x** on Brier even after cutoff-matching prices.

If that replication holds, the single most important consequence for JevFish is that **the aggregation must be learned from resolved outcomes**, not chosen a priori, which is the same conclusion as section 3.3 arrived at from a different direction.

**Does the crowd help only if members are already calibrated? Yes.** Hsieh, Fu, Chen, "Reasoning and Tools for Human-Level Forecasting" ([arxiv.org/abs/2408.12036](https://arxiv.org/abs/2408.12036), NeurIPS 2024), 201 Manifold questions: RTF median of 3 **0.169** and mean of 3 0.170 against the crowd's 0.172, versus a single sampled RTF agent at 0.180. But **ensembling base LMs made them worse**: Base LM Mean 0.218 and Base LM Median 0.228 against single GPT-4o at **0.210**. Their explanation, verbatim: **"Ensembles only contribute to the final performance if each ensemble member is already sufficiently calibrated."** Ensemble SD was 0.092 for the ReAct agents versus 0.150 for base LMs.

Wang et al.'s self-consistency paper makes the same point for multi-model voting on GSM8K: PaLM-540B self-consistency 74.4, PaLM-540B + LaMDA-137B majority vote **36.9**, LaMDA-137B + GPT-3 code-davinci-001 16.0, all three 33.3 ([arxiv.org/abs/2203.11171](https://arxiv.org/abs/2203.11171), Table 10). "Lower-capacity models drag down the performance of higher-capacity models."

**Vote share as probability is much worse than just asking for a number.** Prophet Arena ([arxiv.org/abs/2510.17638](https://arxiv.org/abs/2510.17638), Table 8) ran exactly JevFish's architecture against verbalised elicitation on 100 events, Brier then ECE:

| Method | Grok 4 | Gemini 2.5 Flash | Claude Sonnet 4 | GPT-5 | Llama 4 Scout |
|---|---|---|---|---|---|
| Verbalised, default | 0.186/0.117 | 0.166/0.036 | 0.173/0.046 | **0.165/0.020** | 0.196/0.153 |
| Verbalised, prompt ensemble | 0.177/0.117 | 0.165/0.032 | 0.170/0.043 | 0.160/0.024 | 0.192/0.142 |
| Verbalised, bi-directional | 0.180/0.101 | 0.164/0.031 | 0.165/0.028 | 0.158/0.023 | 0.203/0.140 |
| **Self-consistency, unweighted (10 Yes/No rollouts, fraction Yes)** | **0.238/0.115** | **0.231/0.110** | **0.241/0.071** | **0.239/0.071** | **0.267/0.129** |
| Self-consistency, confidence-weighted | 0.205/0.091 | 0.201/0.067 | 0.189/0.050 | 0.181/0.046 | 0.214/0.125 |

**Counting votes from 10 rollouts cost 0.05 to 0.07 Brier versus simply asking the model for a probability, on every one of five models.** Their explanation: "the unweighted variant produces coarse-grained probabilities at a resolution of 0.1, limiting accuracy despite incurring higher compute cost." Confidence weighting recovers roughly half the loss. Their bi-directional trick (eliciting P(Yes) and P(No) separately and taking the average of p and 1 minus p-complement) improved calibration on 4 of 5 models, "supporting the view that **LLMs tend to be overconfident toward Yes outcomes**". Prompt ensembling barely helped "since elicited probabilities are already similar across variations".

This directly validates JevFish's current `NoulQ` design over the `ChoiceQ` alternative your Finding 6 probe tested, and it explains why the forced choice made the level worse. The literature says: keep asking for the probability, weight by it, and do not count votes.

Two commonly cited papers do **not** support the calibration claim made for them: Wang et al.'s self-consistency paper claims "improved calibration" in its conclusion but reports **no ECE and no reliability diagram**, and its only in-body calibration statement is the opposite; Universal Self-Consistency ([arxiv.org/abs/2311.17311](https://arxiv.org/abs/2311.17311)) reports no calibration numbers at all.

**Temperature resampling cannot manufacture diversity, and this is the strongest single argument against a large persona crowd.** "Stochastic Sampling is Epistemically Shallow" ([arxiv.org/abs/2607.20464](https://arxiv.org/abs/2607.20464), preprint) compares one model run 100 times at temperature 1 against 24 LLMs run once each at temperature 0, applying a Marchenko-Pastur random-matrix test to both: "Within any single model, **at most one dimension** rises above noise across five families and three benchmarks. Across the ensemble, **four eigenvalues** clear the noise edge ... Self-consistency gives accurate per-question uncertainty but no detectable cross-question structure; only a diverse ensemble surfaces what a model does not know."

One model sampled N times yields roughly **one effective degree of freedom**. A persona crowd is one model sampled N times with different context strings. It cannot reproduce population heterogeneity, and your own data agrees: 801 personas produced about 30 distinct probability values with a standard deviation of 0.096.

For accuracy on reasoning tasks, path diversity within one model does beat prompt diversity: LaMDA-137B at budget 40, self-consistency over sampled paths gave GSM8K 27.7 (SD 0.2) versus prompt permutation 19.2 (0.1) and three prompt sets 18.6 (0.5). And interpretation diversity is competitive with model diversity: BoolQ 88.5% (GPT-3.5-turbo + Llama 2 70B + Claude 3) versus **89.1%** (three GPT-3.5-turbo runs with different question phrasings); PubmedQA 78.2% versus 79.8% ([arxiv.org/abs/2507.21168](https://arxiv.org/abs/2507.21168), 3 members only, gaps of 0.6 and 1.6 points, no CIs: FLAG).

**The exception, and its condition.** "More Agents Is All You Need" ([arxiv.org/abs/2402.05120](https://arxiv.org/abs/2402.05120)) scales sampling-and-voting to 40 agents and reports 12 to 24% on GSM8K, 6 to 10% on MATH, 4 to 9% on HumanEval, with Llama2-13B at 15 agents matching Llama2-70B. But the relative gain is **28 to 200% for Llama2-13B and only 8 to 16% for GPT-3.5-Turbo**. Returns from more agents are large when the base model is weak and small when it is strong.

### 6.10 ForecastBench as the reference scoreboard, for context

**ForecastBench** ([arxiv.org/abs/2409.19839](https://arxiv.org/abs/2409.19839), ICLR 2025). Original July 2024 human survey: superforecasters **0.096 [0.076, 0.116]**, public 0.121 [0.101, 0.141], best LLM (Claude-3-5-Sonnet with freeze values and scratchpad) 0.122 [0.099, 0.146], p < 0.001 for the human advantage. **Adding news made it worse**: the same model with "news with freeze values" scored 0.127. The live tournament board now has Google DeepMind "fire hedgehog" 69.1 [67.9, 70.4], "ceramic-kettle" 68.9, superforecaster median 68.8 [67.3, 70.5] at rank 3, Cassi-AI 68.5, Torchcast 68.5, public median rank 150 at 63.5, "always 0.5" at 50.0. The baseline board (no tools, no scaffolding) has superforecasters rank 1 at 67.8, public rank 2 at 62.7, and the best raw model at rank 3 with 62.4: **no raw frontier model reaches the public crowd without tools.**

FRI's own assessment as of 16 July 2026: Cassi AI, xAI and Google DeepMind cannot be statistically separated from superforecasters (bootstrap one-sided p = 0.41, 0.16, 0.15, 0.14) ([forecastingresearch.substack.com](https://forecastingresearch.substack.com/p/ai-models-have-likely-reached-parity)). Trend: **0.016 difficulty-adjusted Brier points of improvement per year**, Claude 3.5 Sonnet 0.117 in October 2024 to Grok 4.20 Preview 0.102 in October 2025. Two caveats FRI state themselves: the human baselines were last surveyed in **July 2024**, and every AI-versus-human comparison is a two-way fixed-effects adjustment rather than a head-to-head.
## 7. Recommended implementation for JevFish

This section assumes the findings already recorded in `docs/research/calibration-experiment.md`, in particular the estimand-mismatch diagnosis in Finding 6 and the fitted logit shift in Finding 4. It does not repeat them. Implementation cost is in engineer-days for one person who knows the codebase.

### 7.0 What the literature says about the current design, before the fixes

Four structural facts about the current pipeline, each with a literature match:

- `mean_outcome` in `src/jevfish/metrics.py` is the arithmetic mean of per-persona Jev probabilities, that is, a linear opinion pool. That is the pool matched to the Brier scoring rule, which is defensible. The problem is not the pool.
- Each variant runs as a separate simulation with its own platform, feed and subject facts (`src/jevfish/simulate.py`, `VariantRun`). Every price point is therefore a different imagined world. This is precisely the design Gui and Toubia identify as endogenous by construction ([arxiv.org/html/2312.15524v3](https://arxiv.org/html/2312.15524v3)): varying the treatment in the prompt also varies unstated confounders, which is why their naive curves come out flat or inverted-U and why yours comes out too steep.
- The outcome question is a `NoulQ` asked per persona per variant, so there is no K-way option list and therefore no A-bias in the Dominguez-Olmedo sense on that path. Good. The `ChoiceQ` paths (action, point, target) do carry option-order exposure and should be permuted.
- The 90% interval is `Z90 * sqrt(sum p(1-p))`, Poisson-binomial sampling noise. The docstring already says it "covers only that chance element, not model error", which is honest, but the number is still printed as if it bounded the answer. The measured aggregate level error across the literature is 0.352 human SD ([arxiv.org/abs/2509.19088](https://arxiv.org/abs/2509.19088)), which is a bias term the formula does not contain at all.

One more observation from the stored run that the literature explains: Jev returned only about 30 distinct probability values across 801 personas, with four values covering 341 of them. That is a resolution floor in the judge, not a property of the population. It caps how much any within-crowd variance fix can achieve and means the effective number of independent opinions is far below 801. It also means the Satopaa information-overlap argument applies at full strength: a persona crowd from one frame and one model shares almost all its information, so the second reason to extremise does not apply and an extremising exponent near human-crowd values (2.4 to 3.1) would badly overshoot. Your own test confirms this: a = 2.0 and a = 3.0 both overshot the curve.

### 7.1 Priority 1: name the estimand and store it

**What it is.** Add an explicit `estimand` field to the frame and to every run output, with a controlled vocabulary: `choice_share_of_described_set`, `acceptance_rate_independent`, `event_probability`. The current `mean_outcome` is `acceptance_rate_independent` under the `NoulQ` path and `choice_share_of_described_set` under the `ChoiceQ` path, and these are different quantities that cannot be compared or calibrated with the same map. Stop rendering a bare percentage; render "share of the described option set" or "acceptance rate among the described crowd" next to it.

**What it needs.** A frame schema change, a field in the report, and UI copy. No model work.

**Expected gain.** Zero measured accuracy gain and the single largest reduction in wrong decisions. The industry has a settled name for this distinction: conjoint simulators output "share of preference", explicitly defined as predicted shares "given equal awareness and equal distribution", and Sawtooth's documented pipeline to get from there to market share is a fixed sequence of Product Availability, then Product Awareness, then Exponent, then Share Adjustment ([sawtoothsoftware.com/help/lighthouse-studio/manual/external-effects.html](https://sawtoothsoftware.com/help/lighthouse-studio/manual/external-effects.html), [.../share-adjustment.html](https://sawtoothsoftware.com/help/lighthouse-studio/manual/share-adjustment.html)). The factors they list as missing from share of preference are advertising level and effectiveness, sales force, number of outlets, awareness and time on market. For a room night the analogues are channel mix, listing visibility, lead time and arrival volume. JevFish has none of them and cannot get to occupancy without them. Note also Sawtooth's own statement that the Aggregate Adjustment method "was shown to be inferior to other methods by Orme and Johnson", so use per-respondent adjustment, not a single global multiplier.

**Cost.** 0.5 day.

### 7.2 Priority 2: an anchor store, as a first-class object

**What it is.** A table, one row per resolved anchor: `question_family`, `option_id`, `predicted_share`, `realised_outcome`, `realised_estimand`, `n_crowd`, `model_version`, `frame_hash`, `resolved_at`. Every calibration, every interval and every skill score reads from this table. Nothing else in this list works without it.

**What it needs.** A schema addition in `src/jevfish/store.py` (JSON on disk is fine), plus a small CLI to record an outcome against a past run.

**Expected gain.** This is the prerequisite, so the gain is everything downstream. The evidence that anchors are the binding constraint is unambiguous: prediction-powered inference needs a labelled sample to compute the rectifier ([science.org/doi/10.1126/science.adi6000](https://www.science.org/doi/10.1126/science.adi6000)); doubly-robust correction took bias from 33.1pp to 0.2pp on ANES and 1.9pp to 0.32pp on purchase intent but only with a calibration sample, and reaches more than 87% bias reduction at n of about 100 ([arxiv.org/html/2609.13148](https://arxiv.org/html/2609.13148)); the H&M pricing system reached 90% of optimal revenue on about 73 real observations, roughly 3 per product ([arxiv.org/html/2606.16183v1](https://arxiv.org/html/2606.16183v1)); and the Krsteski allocation result says 100 real responses plus rectification takes bias from 24% to 86% down below 5% ([arxiv.org/abs/2510.11408](https://arxiv.org/abs/2510.11408)).

**Two design rules the literature is explicit about.**

- **Weight the synthetic estimate low.** The PPI power-tuned lambda in Krsteski et al. averaged **0.05 to 0.30** across three surveys, and forcing lambda to 1 left bias in double digits with negative effective sample size. So the corrected estimate should be mostly the real anchor with a small synthetic adjustment, not mostly synthetic with a nudge.
- **Blend the anchor arithmetically, outside the model, not by putting it in the prompt.** Schoenegger et al.'s Study 2 handed GPT-4 and Claude 2 the human crowd median and got a 17% to 28% accuracy gain, but the part nobody quotes is that both models' updated forecasts were **significantly worse than a naive 50/50 arithmetic average** of the machine and human medians (GPT-4 0.13, t(92) = 2.583, p = .011; Claude 2 0.14, t(92) = 3.530, p = .001): "the updating itself is directionally correct but fails to improve upon a simple benchmark" ([science.org/doi/10.1126/sciadv.adp1528](https://www.science.org/doi/10.1126/sciadv.adp1528)). Do the arithmetic in code.

Also record `model_version` and `frame_hash`: Bisbee et al. showed the same prompt gives significantly different distributions across ChatGPT versions and across a three-month gap, so a calibration fitted on one version does not transfer.

**Cost.** 1 day.

### 7.3 Priority 3: two-parameter logit recalibration per question family

**What it is.** Replace the single fitted shift with the monotone two-parameter map applied to each persona probability **before** aggregation:

```
q_cal = sigmoid( a + b * logit(q_raw) ),   b > 0
```

Fit `(a, b)` per question family by minimising a proper score (log loss or Brier) against the anchors, with `b` constrained positive so the map stays monotone. This is exactly the transform used in the H&M paper, whose authors state it "corrects the scale of the probabilities without discarding their ordinal information". `a` fixes the level, `b` fixes the slope, which means it fixes the elasticity as well as the occupancy number. Your existing one-parameter fit only had `a` because you only had one anchor.

Apply it to `q_raw` per persona, not to the aggregate share. The two are not interchangeable because sigmoid is non-linear, and the published system calibrates at the persona level.

**What it needs.** At least 2 anchors at different levels to identify `(a, b)`, ideally 5 or more so you can hold one out. For the Pureloft question you have exactly one credible level (MYR 300, 89.2% over 610 resolved nights) and no credible curve, because measured elasticity on your own data comes out positive. So the second anchor has to come from somewhere else: a different unit, a different season, a different property, or a public benchmark with the same estimand.

**Expected gain.** Direct evidence: CRPS 0.94 versus 0.99, MAE 1.38 versus 1.44 units, RMSE 1.79 versus 1.86 against an embedding baseline, and 90% of optimal expected revenue from about 73 observations ([arxiv.org/html/2606.16183v1](https://arxiv.org/html/2606.16183v1)). Supporting evidence that the fewest parameters is right: Guo et al. found single-parameter temperature scaling outperforms the strictly more general vector and matrix Platt variants, because most miscalibration is average over- or under-confidence, and it leaves the ordering untouched ([proceedings.mlr.press/v70/guo17a/guo17a.pdf](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf)). The industry analogue is Sawtooth's Exponent, which "tunes the degree of flatness or steepness in the share of preference probabilities", that is, the same `b`.

Honest caveat: your existing single-parameter fit produced zero error at MYR 300 by construction, which is not a validated gain. A two-parameter fit on two anchors has the same problem. The gain is only demonstrated once you have enough anchors to hold one out, which is the argument for 7.9.

**Cost.** 1 day for the map and the fit, plus whatever it costs to get anchors.

**Three implementation details that are cheap and measured.**

- Fit by minimising **Brier, not log loss**. Mantic's technical writeup gives the reason: "the Brier score leads to more stable training than the log score", which is why they use it as their RL reward ([thinkingmachines.ai](https://thinkingmachines.ai/news/training-llms-to-predict-world-events/)). It is bounded, so one outlier anchor cannot dominate the fit.
- **Clip the output** to [0.02, 0.98] or [0.01, 0.99]. Every winning Metaculus bot does: the official template hard-clamps to [0.01, 0.99], the best-documented open bot uses [0.02, 0.98], 38% of Fall 2025 winners cap and capping correlates **r = +0.48, p = 0.005** with winning. The bot-makers' own advice is that "the community continues to underrate the benefit of clipping" ([notebook 43357](https://www.metaculus.com/notebooks/43357/bot-advice-fall-2025/)).
- **Cap the permitted deviation** of the fitted map, so a bad fit degrades to the identity rather than to a new error. `MAX_ABS_DEVIATION = 0.10` is the published precedent.

### 7.4 Priority 4: replace the interval with split conformal on held-out error

**What it is.** Keep computing the Poisson-binomial half-width but relabel it "sampling noise inside the crowd, excludes model bias". Separately, once the anchor store has `k` rows for a question family, compute split conformal non-conformity scores `s_i = |actual_i - predicted_i|`, take `q_hat` as the `ceil((k+1)(1-alpha))`-th smallest, and report `[p_hat - q_hat, p_hat + q_hat]` clipped to [0,1]. Use normalised scores `s_i = |actual_i - predicted_i| / sigma_binomial_i` if you want the interval to widen automatically for small crowds.

**What it needs.** `k >= 1/alpha - 1` anchors: 4 for 80% coverage, 9 for 90%, 19 for 95% ([arxiv.org/pdf/2303.02770](https://arxiv.org/pdf/2303.02770), [stat.cmu.edu/~ryantibs/papers/conformal.pdf](https://www.stat.cmu.edu/~ryantibs/papers/conformal.pdf)). Below 4 anchors, do not print an interval at all; print the raw historical errors instead.

**Expected gain.** Distribution-free finite-sample coverage with no assumptions on the predictor. In your own measured case the stated half-width was 2.82pp against an actual error of 32.4pp, an 11.5x understatement that gets worse as the crowd grows. A conformal interval fitted on anchors like that one would have been roughly 32pp wide, which is honest and, importantly, would have flagged the estimand mismatch immediately rather than three runs later. Coverage is marginal not conditional, so it will not protect a question type unlike anything in the anchor set ([dl.acm.org/doi/10.1145/3736575](https://dl.acm.org/doi/10.1145/3736575)).

**Cost.** 0.5 day.

### 7.5 Priority 5: two frame gates, run before any number is trusted

**Gate A, unblind the randomisation.** Add to the frame a sentence stating that the varying attribute is experimentally assigned, for example "the nightly rate is set randomly and uniformly between MYR 200 and MYR 500 by the owner, independent of season, demand and competitor rates". This is Gui and Toubia's fix verbatim. Their measured effect: MAE improvement from 1% to over 60% across model versions, and for the fine-tuned model blinded MAE 0.134 versus unblinded 0.113, a 15% reduction ([arxiv.org/html/2312.15524v3](https://arxiv.org/html/2312.15524v3)). The v1 analysis of the same work reported elasticity moving from 0.14 to 1.38 against a literature benchmark of 1.8 to 3.0 ([arxiv.org/html/2312.15524v1](https://arxiv.org/html/2312.15524v1)). The versions present different analyses; cite whichever you use. Their caveat stands: you identify a conditional ATE specific to the range you state, and results are sensitive to that range, so record the stated range with the run.

**Gate B, the monotonicity sweep.** Before any run is reported, sweep the varying attribute over a wide range and assert the response curve is monotone in the expected direction. Gui and Toubia's human curves slope down while GPT's follow an inverted U. If your curve is non-monotone, flat, or steeper than the widest published estimate, block the run rather than report it.

**What it needs.** A frame template change, an assertion in the run pipeline, and a list of expected-direction priors per question family.

**Expected gain.** Gate A is the only published prompt-level intervention with a measured double-digit error reduction on a demand curve. Gate B costs one extra variant sweep and catches the failure class that produced your -3.29.

**Cost.** 1 day.

### 7.5b Priority 5b: put retrieved evidence in the frame, because it is the largest measured lever in the whole forecasting literature

**What it is.** Before generating personas, retrieve real evidence for the question and put the summaries into the `subject` block: comparable rates from your own ledger, current competitor prices, the relevant seasonality, any published elasticity for the segment, recent news that bears on demand. JevFish currently builds an ontology from supplied documents; this is the step that fills those documents automatically.

**Why it ranks this high.** The measured effects are larger than anything else in section 6, by an order of magnitude:

- Bridgewater's AIA Forecaster on live markets: **with search 0.1002 Brier, without search 0.3609**, a 3.6x difference, and without search it is worse than always predicting 0.5 ([arxiv.org/abs/2511.07678](https://arxiv.org/abs/2511.07678)).
- Halawi et al.: the retrieval ablation is their biggest single lever, **0.206 to 0.186**, while their search over 15 hand-crafted reasoning prompts was worth "fairly a minor improvement" by their own description ([arxiv.org/abs/2402.18563](https://arxiv.org/abs/2402.18563)).
- Metaculus tournament survey: number of research sources correlates **r = 0.42, p = 0.006**, with winners averaging 1.75 sources and non-winners 1.00, and "no individual search provider gave a significant score advantage" (so use whatever you already have).
- ForecastBench baseline board: **no raw frontier model reaches the public crowd without tools.** Superforecasters rank 1 at 67.8, public rank 2 at 62.7, best raw model rank 3 at 62.4.

**What it needs.** A retrieval step and a relevance filter. Halawi's exact recipe is cheap and copyable: generate about 6 queries from two prompts (plain expansion and sub-question decomposition), retrieve, then have a **small model rate each item 1 to 6 and discard anything scoring 3 or below**, feeding only the title plus first 250 words to the rater, which gives recall 0.73 and precision 0.65 against a full-text gold standard at **about 30% of the cost**. Then summarise, and present the **top 15 items ordered by relevance, not recency**.

**The counter-evidence to respect.** ForecastBench's original paper found that adding news made the best model **worse** (0.122 to 0.127), and FutureSearch documents the specific failure: base rates get "extrapolated without checking whether the generating mechanism is still active" ([futuresearch.ai/blog/history-doesnt-repeat](https://futuresearch.ai/blog/history-doesnt-repeat)). So retrieval helps when it is filtered and summarised, and hurts when it is dumped in raw. The relevance filter is not optional.

**Cost.** 2 days, most of it the filter and the summariser.

### 7.6 Priority 6: consistency checks, which cost nothing and need no ground truth

**What it is.** Paleka et al.'s arbitrage-based consistency framework, adapted to a share estimand ([arxiv.org/abs/2412.18544](https://arxiv.org/abs/2412.18544)). Run these on every run:

- Shares over a mutually exclusive, exhaustive option set sum to 1 (only applies on the `ChoiceQ` path; on the `NoulQ` path they must not be presented as if they did).
- Merge invariance: merging two options should give approximately the sum of their separate shares.
- Label invariance: renaming or reordering options should not move shares beyond sampling noise.
- Irrelevant-alternative invariance: adding a dominated option should not change the relative shares of the others.
- Paraphrase invariance: rewording the outcome question without changing its meaning should not move the share.
- Negation coherence: `P(books)` plus `P(does not book)` asked separately should sum to 1.

**Expected gain.** The paper reports that instantaneous consistency correlates strongly with ground-truth Brier, which means this is a proxy for accuracy you can compute today with zero anchors. Bisbee et al. give the independent reason to run paraphrase invariance in particular: response distributions are highly sensitive to minor prompt wording changes ([cambridge.org, doi 10.1017/pan.2024.5](https://www.cambridge.org/core/journals/political-analysis/article/synthetic-replacements-for-human-survey-data-the-perils-of-large-language-models/B92267DC26195C7F36E63EA04A47D2FE)). Expect several of these to fail on the current build.

**Cost.** 1.5 days, mostly in generating the perturbed frames.

### 7.7 Priority 7: post-stratify the segments instead of growing the crowd

**What it is.** Your own variance decomposition put 52.0% of total variance between segments and 48.0% within. That makes segment weights the dominant lever on the aggregate, and it means the aggregate is only as good as the segment mix. Replace the unweighted mean with a post-stratified estimate `theta = sum_j (N_j / N) * theta_j` over segments, where `N_j` comes from a real frame (booking history by market, channel mix, arrival origin), and use a multilevel model for `theta_j` so sparse segments borrow strength.

**What it needs.** A real population frame per question family. For Pureloft that is your own booking ledger by guest origin and channel, which you already have. Plus a weights field in `crowd.json` and a weighted path through `metrics.summarize_poll` and `metrics.segment_breakdown` (both currently unweighted).

**Expected gain.** The existence proof is the Xbox study: a sample that was 93% male and 65% aged 18 to 29 pointed to a Romney landslide raw, and post-stratification onto a real frame across 176,256 cells landed within **0.6 percentage points** of the national outcome, with 1.8 to 2.5pp mean and median absolute deviation across 51 state races ([5harad.com/papers/forecasting-with-nonrepresentative-polls.pdf](https://5harad.com/papers/forecasting-with-nonrepresentative-polls.pdf)). The resolution argument is Lax and Phillips: MRP held mean absolute error at 4 to 5pp from N about 1,400 up to N about 14,000 while raw disaggregation ranged 4 to 11pp, MRP at the 5% sample matched disaggregation at the 50% sample ("like getting 12,000 or more observations free"), MRP's cross-simulation standard deviation was one quarter to one third of disaggregation's, and MRP had the lower MAE in 100% of simulated data sets ([columbia.edu/~jhp2121/publications/HowShouldWeEstimateOpinion.pdf](http://www.columbia.edu/~jhp2121/publications/HowShouldWeEstimateOpinion.pdf)).

Read across to your resolution problem: `1.645 * sqrt(2p(1-p)/n)` giving plus or minus 17pp at n = 48 is the disaggregation variance. Model-based smoothing across segments is how the polling literature gets an order of magnitude in effective sample size without more respondents, and it is much cheaper than running n = 800. The binding condition from that literature is that the cells must contain outcome-predictive variables. For a room rate that means lead time, channel and party size, not income band and priority word. Your own data already shows why: "budget-conscious friend groups" had 202 members with different income and priority attributes and a within-segment SD of 0.015, so those attributes are inert.

**Cost.** 2 days for weighted aggregation and a simple hierarchical shrinkage estimator. More if you want full MRP with a fitted multilevel model.

### 7.8 Priority 8: concrete persona attributes, with the level expectation set correctly

**What it is.** Replace abstract persona attributes with concrete numbers, as your Finding 6 probe already did: party size, nights, total accommodation budget, per-night budget, one already-shortlisted alternative with its price, date flexibility, prior stay in the building.

**Expected gain, and the honest limit.** Your probe measured persona SD rising from 0.080 to 0.192, a 2.4x increase, range from 0.25 to 0.59, minimum falling from 0.42 to 0.09, distinct values from 19 to 29. That is a real dispersion fix, and dispersion is what makes the interval meaningful. But the mean moved from 0.515 to 0.433, away from the truth. The literature says to expect exactly this and no more. In the Columbia mega-study, full 500-question personas scored individual accuracy 0.748 against 0.746 for 14 demographic variables and 0.734 for an empty persona, with average correlation to real humans of r = 0.197 ([arxiv.org/abs/2509.19088](https://arxiv.org/abs/2509.19088)). Park et al.'s two-hour interviews bought 12 normalised points over demographics-only, 86% versus 74%, which is the upper bound on what persona richness can deliver and requires an interview per person ([arxiv.org/abs/2411.10109](https://arxiv.org/abs/2411.10109)). Verasight found richer context sometimes made accuracy *worse*, with the most enhanced GPT-5 configuration beaten by the baseline on Trump approval ([verasight.io/reports/synthetic-sampling-2](https://www.verasight.io/reports/synthetic-sampling-2)).

So: do it for dispersion, budget it as cheap, and do not expect a level improvement. Measure dispersion and level separately so you can see which moved.

Related: Bisbee et al. found a politics-only persona prompt had essentially identical MAE to a full prompt, while a demographics-only prompt inflated error badly on politically salient targets. The general rule is that the persona axes worth including are the ones directly predictive of the specific outcome, and nothing else. For a booking decision that is budget and alternatives, not demographics.

Also worth testing, at near-zero cost: Bisbee et al. found the second-person framing ("You are a ...") produces exaggerated polarisation consistent with Levendusky and Malhotra on humans estimating others' attitudes, while first-person ("I am a ...") shows less exaggeration but worse overall MAE. That is a one-line A/B with a documented effect on extremity.

**Cost.** 1 day for the enriched persona schema, given the probe already exists.

### 7.8b Priority 8b: keep asking Jev for a probability, and fix the elicitation scale

Your Finding 6 probe replaced the per-persona probability question with a forced `ChoiceQ` and the level got worse, 0.225 against 0.515. The literature says that was the predictable outcome and you should not revisit it.

Prophet Arena ran exactly that comparison on 100 events across five models ([arxiv.org/abs/2510.17638](https://arxiv.org/abs/2510.17638), Table 8). **Counting Yes votes from 10 rollouts cost 0.05 to 0.07 Brier versus simply asking the model for a probability, on every one of the five models.** Their explanation: "the unweighted variant produces coarse-grained probabilities at a resolution of 0.1, limiting accuracy despite incurring higher compute cost." Confidence-weighting the votes recovers roughly half the loss. Tian et al. found the same in the QA setting: their logprob baseline **is** 10-sample vote frequency, and verbalised confidence beat it on all three datasets for gpt-3.5-turbo and GPT-4 ([arxiv.org/abs/2305.14975](https://arxiv.org/abs/2305.14975)). And sample frequency is upward-biased by Jensen's inequality ([arxiv.org/html/2605.08432](https://arxiv.org/html/2605.08432), preprint).

So: keep the `NoulQ`, and weight by the probability rather than thresholding it. But two elicitation fixes are worth testing, both cheap:

1. **Try a coarser answer scale.** Dai and Wang, six frontier models, three datasets, found that on a [0, 100] confidence scale **the single most frequent value accounts for 35.6% to 68.4% of all responses, the top three cover 78.2% to 92.1%, and models use only 15 to 28 distinct integers out of 101** ([arxiv.org/abs/2603.09309](https://arxiv.org/abs/2603.09309), preprint). That is almost exactly JevFish's measured behaviour (about 30 distinct values across 801 personas, four values covering 341 of them). Their fix, replicated across all seven models they tested, is a **[0, 20] scale**, which raised metacognitive efficiency over [0, 100] for every model at p < 0.05 Bonferroni-corrected. Also relevant: requesting *more* precision makes things worse. Sun, Sun and Geng found "requesting three-decimal confidences degrades PR-AUC in all six tested pairs", in one case 0.936 to 0.580 ([arxiv.org/abs/2606.22179](https://arxiv.org/abs/2606.22179), preprint).
2. **Try bi-directional elicitation.** Ask for P(books) and P(does not book) separately and take `0.5 * (p_yes + (1 - p_no))`. Prophet Arena measured this improving calibration on 4 of 5 models, "supporting the view that LLMs tend to be overconfident toward Yes outcomes". This doubles the request count and doubles as one of the consistency checks in 7.6.

Also, from Kadavath et al., a direct warning about the frame: "It is crucial that the model gets to see the answer choices explicitly before choosing amongst them", calibration "improves as we pass from 0-shot to 5-shot", and replacing an option with "none of the above" "**reduces accuracy and calibration significantly**" ([arxiv.org/abs/2207.05221](https://arxiv.org/abs/2207.05221)). If your frame carries a "books nothing" branch, that is the option they measured as harmful.

**Cost.** 0.5 day for the scale change plus a 40-persona probe like the one you already ran; 1 day if you add bi-directional elicitation.

### 7.9 Priority 9: the benchmark suite, four harnesses

**What it is.** A `bench/` directory with four scorers, run on every material change. Details and access paths in section 5.

1. **SimBench.** Same estimand shape as JevFish (per-option share vector, TVD-derived 0 to 100 score). Bar to clear: Claude-3.7-Sonnet 40.80.
2. **Twin-2K-500.** Includes a pricing survey and a test-retest ceiling. Bar to clear: 71.72% accuracy, 87.67% of ceiling.
3. **OpinionQA.** Wasserstein representativeness over 1,498 questions and 60 groups, with pre-computed model runs so you can compare without re-running anything.
4. **Expedia Personalized Sort.** 9.9M rows of hotel search results with booking labels, so you can compute observed booking share per option within a search set and score a predicted share vector against it. This is the closest public analogue to the actual product.

**Expected gain.** This is the single largest measured effect in the only systematic survey of what separates winning forecasting bots from losing ones. Metaculus's Fall 2025 survey of 39 bot-makers put **"custom question testing" at +2,216 coverage-adjusted points, 95% CI [+912, +3,519]**, ahead of aggregation strategy at +1,799 [+1,017, +2,582] and well ahead of manual review of logs at +1,041 [-223, +2,305], which was not significant. Dev time correlated at r = 0.08, not significant. Building your own eval set beats spending time on the pipeline.

It is also the only way to know whether any of 7.3 to 7.8 worked. Your own doc already states the problem correctly: a single-anchor, single-parameter fit is in-sample with one data point and cannot be held out. A leave-one-out test needs at least 3 anchors and a real validation needs many resolved outcomes.

One design note from the benchmark literature: build the contamination check in from the start. Douven's replication of the silicon-crowd result found an accuracy differential of up to **+0.256** between questions inside and outside the model's training cutoff, and a Spearman correlation of only 0.532 between model rankings on the full set and on the contamination-free subset ([arxiv.org/html/2607.18269v2](https://arxiv.org/html/2607.18269v2), preprint). On the clean subset the median-of-crowd aggregator scored **0.343, worse than always predicting 0.5**, and only a learned aggregator fitted on resolved history reached 0.241. Any benchmark result on questions inside the cutoff is roughly meaningless, and this is the strongest independent argument that the aggregation must be **fitted**, not chosen.

**Cost.** 3 days for all four, 1 day for SimBench alone. Start with SimBench.

### 7.10 Priority 10: the scoring and ablation table, printed on every run

**What it is.** Every run reports: RPS (for ordered options) or multi-category Brier (unordered), log score, CRPS against the realised value where the estimand is continuous, the Murphy decomposition into reliability, resolution and uncertainty, a reliability diagram, and skill scores against five baselines.

The five baselines, in order:

1. Uniform over K options.
2. Climatology: your own trailing realised rate over a comparable window. In Murphy terms this has REL = 0 and RES = 0, so skill against it is exactly `(RES - REL) / UNC`.
3. Persistence: last comparable period's realised value.
4. A fitted constant-elasticity demand curve on your own booking ledger.
5. **Empty-persona ablation**: one zero-shot LLM call asking for the share directly, no ontology, no personas, no interaction rounds.

**Expected gain.** ECE must not be the headline: it is not a proper scoring rule and a model that ignores its input and outputs the marginal rate achieves ECE = 0 with zero discriminatory power ([arxiv.org/pdf/2408.02841](https://arxiv.org/pdf/2408.02841)), and it is a biased estimator under any binning ([proceedings.mlr.press/v151/roelofs22a/roelofs22a.pdf](https://proceedings.mlr.press/v151/roelofs22a/roelofs22a.pdf)). Use it and reliability diagrams as diagnostics that tell you which calibration map to fit.

Baseline 5 is the uncomfortable one and the most important. The Columbia study measured the full persona pipeline at 0.014 above an empty persona ([arxiv.org/abs/2509.19088](https://arxiv.org/abs/2509.19088)). If JevFish does not beat one zero-shot call on the benchmark suite, the ontology stage, the persona generation and the interaction rounds are pure cost and should be cut.

Baseline 4 is the one that matters commercially. The published state of the art for hotel occupancy prediction learns elasticity from the operator's own reservation logs: Fliggy's PEM model, trained on 712K to 834K reservations across 12,727 hotels, delivered a **7.42% improvement in daily GMV** over manual pricing in a two-week live test ([arxiv.org/pdf/2208.03135](https://arxiv.org/pdf/2208.03135)). That is the bar for a pricing recommendation, and a synthetic crowd is not going to clear it on level accuracy. It can clear it on questions where you have no history at all, which is the honest product claim.

**Cost.** 1.5 days.

### 7.11 Priority 11: measure the OASIS interaction rounds, then keep or cut

**What it is.** Run the benchmark suite with rounds = 0 and with rounds = n, and compare on a proper score. Keep the interaction layer only if it wins.

**Expected gain.** Possibly negative. OASIS's published validation is about replicating message propagation *trends* compared on scale, depth and maximum reach, plus qualitative reproduction of information spread, group polarisation and herd effects ([arxiv.org/pdf/2411.11581](https://arxiv.org/pdf/2411.11581)). There is no published calibration of OASIS output against a measured population level, and group polarisation is a documented emergent property of the simulator, which would push shares away from the mean rather than toward the truth. Meanwhile SimBench found no meaningful benefit from inference-time compute across 45 models ([arxiv.org/html/2510.17516](https://arxiv.org/html/2510.17516)), and the scaling study found about one third of behavioural tasks show no scaling at all ([arxiv.org/html/2607.02464v1](https://arxiv.org/html/2607.02464v1)). The interaction layer is the most expensive part of the pipeline and the least evidenced. Measure it before defending it.

**Cost.** 0.5 day, given 7.9 exists.

### 7.12 Priority 12: permute option order on every ChoiceQ path

**What it is.** For every `ChoiceQ` (action, point, target_post, target_comment, followee, and any future K-way outcome question), either average over all permutations of the option list, or implement PriDe: estimate the position prior by permuting on a subsample, then debias the rest cheaply.

**Expected gain.** Not on the critical path today because the outcome question is a `NoulQ`, but it becomes Priority 1 the moment you move the outcome to a `ChoiceQ`, which your Finding 6 probe already did. The magnitudes are large: moving the correct answer to position D cost gpt-3.5-turbo 6.3 percentage points ([arxiv.org/abs/2309.03882](https://arxiv.org/abs/2309.03882)), shuffle-induced accuracy drops of 10.5% to 42.9% are documented, and after randomised choice ordering 43 models across the size range trend toward uniform survey answering, meaning the pre-adjustment signal was largely position artefact ([arxiv.org/html/2306.07951v4](https://arxiv.org/html/2306.07951v4)). Cost of all permutations at K = 5 is 120x; a Latin square of 5 orderings is 5x and captures most of it.

**Cost.** 1 day.

### 7.13 What not to do

- **Do not grow the crowd.** The PPI++ variance decomposition shows the synthetic-pool term `lambda^2 Var(Y_LLM) / m` vanishes as the pool grows, so past a few hundred personas additional personas buy nothing ([arxiv.org/html/2604.17267v2](https://arxiv.org/html/2604.17267v2)). Your own measurement is sharper: the stated half-width shrinks as `1/sqrt(n)` while the real error does not move, so more personas make the tool more confidently wrong. The theoretical result is worse still: a random-matrix analysis comparing one model run 100 times at temperature 1 against 24 models run once each found that "**within any single model, at most one dimension rises above noise** across five families and three benchmarks", while across the model ensemble four eigenvalues cleared the noise edge ([arxiv.org/abs/2607.20464](https://arxiv.org/abs/2607.20464), preprint). One model sampled N times gives roughly **one effective degree of freedom**. A persona crowd is one model sampled N times with different context strings, and with roughly 30 distinct probability values across 801 personas that is what the data shows. If you want real diversity, use two or three different judge models, which is what every winning forecasting bot does: 5 to 10 samples, 3 to 7 diverse runs across model families, with measured degradation past about 10 models ([arxiv.org/abs/2602.08003](https://arxiv.org/abs/2602.08003)).
- **Do not replace the probability question with vote counting**, and do not add a "none of the above" branch without calibrating it separately. See 7.8b.
- **Do not let an LLM do the aggregation.** Four independent measurements: Halawi's Universal Self-Consistency scored 0.1691 against a trimmed mean at 0.1649 and no ensemble at all at 0.1676; AIA's best-of-k scored 0.1191 and its non-agentic supervisor 0.1168 against a plain mean at 0.1140; a Metaculus bot-maker's "stacker" LLM "scored no better than the median" on 88 questions and was shipped disabled. The one exception is AIA's **agentic** supervisor, which beats the mean (0.1125 versus 0.1140) only because it issues fresh search queries to resolve the disagreement rather than reasoning about the numbers.
- **Do not add interaction rounds or more reasoning on the assumption that more compute helps.** SimBench found "no meaningful benefit from inference-time compute" across 45 models ([arxiv.org/html/2510.17516](https://arxiv.org/html/2510.17516)), and going from 1 to 10 samples in the current state of the art is worth 0.0044 Brier while the calibration step is worth 0.0064 to 0.0069.
- **Do not assume the crowd helps at all until the members are calibrated.** Hsieh, Fu and Chen measured ensembling base LMs making them **worse** (Base LM mean 0.218 and median 0.228 against a single GPT-4o at 0.210) while ensembling calibrated ReAct agents helped (0.169 against a single agent's 0.180), and state the rule verbatim: "**Ensembles only contribute to the final performance if each ensemble member is already sufficiently calibrated**" ([arxiv.org/abs/2408.12036](https://arxiv.org/abs/2408.12036)). This is the ordering argument for doing 7.3 before 7.7.
- **Do not import an extremising exponent from the human forecasting literature.** The optimal a of 2.43 to 3.08 in Baron et al. was fitted to independent human forecasters. A persona crowd from one frame and one model has near-total information overlap, so the information-pooling justification does not apply. Your own test overshot at both a = 2.0 and a = 3.0. If you extremise at all, fit a on anchors and expect it near 1.
- **Do not pick an aggregation rule because it makes one known number come out right.** Your hard-vote rule landed 0.889 against a truth of 0.892 while producing an elasticity of -2.375 and saturating at 1.000 on two rungs. That is curve-fitting on one point.
- **Do not expect a bigger or better model to fix it.** The scaling study found that improving a behavioural task from 72% to 90% needs roughly 40x more compute, that longitudinal forecasting has an extrapolated ceiling of 77%, that a third of behavioural tasks do not scale, and that underrepresented populations scale weakest (r squared 0.064 for Pakistan versus 0.60 for Canada) ([arxiv.org/html/2607.02464v1](https://arxiv.org/html/2607.02464v1)). A Malaysian traveller population is in the worst regime of that result.
- **Do not calibrate on Pureloft alone.** Measured elasticity on your own data comes out positive (+0.17 to -0.02) because rates were raised on nights already expected to fill, and only 169 of 1,520 resolved nights went unsold. That gives one credible level and no credible curve. Use `pricing_calendar`, never `reservations`, and get the second anchor from a different unit or a public benchmark.
- **Do not cite -0.36 as a property-level benchmark without a source.** I could not find that figure in Corgel et al.; the closest published numbers are -0.17 (short run, all US hotels) and -0.37 (long run, top 50 markets, all hotels), both market-level aggregates that the authors explicitly say must not be applied to an individual property, and they state property-level elasticity should be *higher* than market-level. The -0.13 to -0.95 property-level range also could not be traced in this review. Both are NOT VERIFIED and the "shape was credible" conclusion rests on them.

### 7.14 The 10-day plan

| Day | Work | Deliverable |
|---|---|---|
| 1 | 7.1 estimand field, 7.4 interval relabel | No number is printed as a rate again |
| 2 | 7.2 anchor store plus record-outcome CLI, with lambda weighting and arithmetic blending | Anchors are storable and correctly weighted |
| 3 | 7.9 SimBench harness with a contamination-date filter | One external, comparable score, and the largest measured lever in the survey data |
| 4 | 7.3 two-parameter logit map, Brier objective, clipping, deviation cap, hold-out plumbing | Calibration is a real code path |
| 5 | 7.5 frame gates A and B | Non-monotone and blinded runs are blocked |
| 6 to 7 | 7.5b retrieved evidence into the frame, with the relevance filter | The 3.6x lever from the forecasting literature |
| 8 | 7.10 scoring and ablation table including empty-persona | Proof the pipeline beats one LLM call, or not |
| 9 | 7.6 consistency checks, 7.8b elicitation-scale probe | Free accuracy proxy on every run, plus a cheap elicitation test |
| 10 | 7.7 weighted and shrunk segment aggregation, 7.11 OASIS ablation | Post-stratified estimate, keep-or-cut on the expensive stage |

Priorities 7.1, 7.2, 7.4, 7.5b and 7.9 are unconditional. Everything after them is contingent on what the benchmark says. Note the ordering constraint from Hsieh, Fu and Chen in 7.13: ensembling and post-stratification only pay once the individual judgments are calibrated, so 7.3 comes before 7.7.
