"""Learn CAT curriculum (section 14).

An initial, self-contained subset of the 22-topic curriculum. Each lesson has
the required shape (one-sentence, plain-language, technical definition, formula
where relevant, example, common mistake, real use, platform link, knowledge
check). Content is educational and number-light; where a figure appears it is a
worked illustration, not a claim about the demo portfolio.
"""

from __future__ import annotations

from app.schemas.learn import GlossaryTerm, KnowledgeCheck, Lesson, LessonSummary


def _kc(q: str, options: list[str], answer: int, why: str) -> KnowledgeCheck:
    return KnowledgeCheck(question=q, options=options, answer_index=answer, explanation=why)


LESSONS: list[Lesson] = [
    Lesson(
        lesson_id="what-is-cat-modelling", order=1, title="What catastrophe modelling is",
        one_sentence="Catastrophe modelling estimates the damage and financial loss a hazard could cause.",
        plain_language="Instead of waiting for a disaster, a CAT model simulates many possible events to estimate how much damage and loss could occur, and how often.",
        technical_definition="A framework combining a hazard module, an exposure module, a vulnerability module and a financial module to estimate physical and monetary loss, deterministically or probabilistically.",
        formula=None,
        interactive_example="Pick a place, choose flood, run a 100-year scenario, and read the loss range and its uncertainty.",
        common_mistake="Treating a model output as a prediction of a specific future event rather than an estimate under stated assumptions.",
        real_world_use="Insurers use CAT models to price risk and hold capital; planners use them to prioritise mitigation.",
        platform_link="/model",
        knowledge_check=_kc("A CAT model primarily produces…", ["A weather forecast", "An estimate of potential loss under assumptions", "A guaranteed loss figure"], 1, "It estimates potential loss under stated assumptions, not a guarantee."),
    ),
    Lesson(
        lesson_id="ehevl-framework", order=2, title="The event–hazard–exposure–vulnerability–loss framework",
        one_sentence="Loss is built up from an event's hazard intensity, what is exposed, and how vulnerable it is.",
        plain_language="An event creates a hazard (like flood depth); exposure is what sits in harm's way; vulnerability says how badly that intensity damages it; loss combines them.",
        technical_definition="Loss = f(hazard intensity at asset, exposure attributes, vulnerability function), aggregated across assets and, for probabilistic runs, across an event set.",
        formula="loss_i = replacement_value_i × damage_ratio(intensity_i, asset_i)",
        interactive_example="In the Model panel, compare two assets at different flood depths and see how the damage ratio changes.",
        common_mistake="Confusing the hazard footprint (where it is) with the vulnerability (how much it damages a given building).",
        real_world_use="Every loss estimate in the platform is decomposable into these four stages for transparency.",
        platform_link="/model",
        knowledge_check=_kc("Vulnerability describes…", ["Where the hazard occurs", "How much damage a given intensity causes to an asset", "The value of the asset"], 1, "Vulnerability maps hazard intensity to a damage ratio for an asset type."),
    ),
    Lesson(
        lesson_id="deterministic-vs-probabilistic", order=3, title="Deterministic versus probabilistic modelling",
        one_sentence="Deterministic runs one scenario; probabilistic runs many with occurrence rates.",
        plain_language="A deterministic run answers 'what if this exact event happened?'. A probabilistic run answers 'across all possible events and their frequencies, what is the risk?'.",
        technical_definition="Deterministic evaluates loss for a single hazard footprint; probabilistic integrates loss over an event set with annual rates to produce AAL and exceedance curves.",
        formula="AAL = Σ_e λ_e × E[L_e]",
        interactive_example="Run the 100-year deterministic scenario, then open the Probabilistic tab for AAL and EP curves.",
        common_mistake="Reading a single deterministic scenario as if it were the long-run average risk.",
        real_world_use="Underwriters need probabilistic metrics (AAL, EP curves); emergency managers often want a deterministic scenario.",
        platform_link="/model",
        knowledge_check=_kc("AAL comes from…", ["One deterministic scenario", "An event set with occurrence rates", "A single worst case"], 1, "AAL integrates loss over an event set weighted by annual rates."),
    ),
    Lesson(
        lesson_id="hazard-intensity", order=4, title="Hazard intensity",
        one_sentence="Hazard intensity is the measurable severity of the hazard at a location.",
        plain_language="It is the number that says how strong the hazard is where an asset sits — flood depth in feet, wind speed, or ground shaking.",
        technical_definition="An intensity measure (IM) sampled per asset or grid cell, with units, resolution and its own uncertainty and provenance.",
        formula=None,
        interactive_example="Hover an asset in the Assets tab to see its modelled flood depth in feet.",
        common_mistake="Confusing a regulatory flood zone with a modelled flood depth — a zone is not a depth.",
        real_world_use="The hazard module supplies an IM at each asset before any damage is computed.",
        platform_link="/model",
        knowledge_check=_kc("A FEMA flood zone is…", ["The same as flood depth", "A regulatory designation, not a depth surface", "An insured loss"], 1, "A zone is a regulatory designation; depth-at-structure is a separate modelled quantity."),
    ),
    Lesson(
        lesson_id="vulnerability-fragility", order=5, title="Vulnerability and fragility",
        one_sentence="Vulnerability maps hazard intensity to damage, ideally as a distribution.",
        plain_language="A depth-damage curve says 'at 3 feet of water, a house loses about this fraction of its value'. A fragility curve gives the chance of reaching each damage state.",
        technical_definition="A conditional damage-ratio distribution D_i ~ P(D | intensity_i, asset_i, model_version); fragility curves give P(damage state ≥ s | intensity).",
        formula="D_i ~ P(D | I_i, X_i, model_version)",
        interactive_example="Open a vulnerability function to see its curve and calibration range.",
        common_mistake="Applying a curve outside its calibration range without flagging the extrapolation.",
        real_world_use="The platform flags any asset whose intensity falls outside a curve's calibration range.",
        platform_link="/model",
        knowledge_check=_kc("A fragility curve gives…", ["A single damage ratio", "The probability of reaching a damage state", "The replacement value"], 1, "Fragility curves give probabilities of damage states versus intensity."),
    ),
    Lesson(
        lesson_id="damage-states", order=6, title="Damage states and damage ratios",
        one_sentence="Damage is described by states (none→complete) and a damage ratio.",
        plain_language="A damage ratio is the share of an asset's value lost; damage states are labelled bands from none to complete.",
        technical_definition="Damage ratio ∈ [0,1] applied to replacement value; damage states {none, slight, moderate, extensive, complete} with a probability each.",
        formula="building_loss = replacement_value × damage_ratio",
        interactive_example="In the Assets tab, read each asset's damage percentage next to its loss.",
        common_mistake="Using the building damage ratio for contents and downtime — those need separate relationships.",
        real_world_use="Contents and business interruption are modelled with their own relationships, not the structural ratio.",
        platform_link="/model",
        knowledge_check=_kc("Contents damage should use…", ["The same curve as structure", "Its own relationship", "The financial deductible"], 1, "Contents and BI use separate relationships from structural damage."),
    ),
    Lesson(
        lesson_id="financial-loss", order=7, title="Financial-loss modelling",
        one_sentence="Insurance terms turn ground-up loss into gross and net insured loss.",
        plain_language="Ground-up is the total economic loss; a deductible is retained by the insured, a limit caps the payout, and coinsurance splits it.",
        technical_definition="gross = clamp(ground_up − deductible, 0, limit); net = gross × coinsurance, at policy or location level.",
        formula="gross = min(max(ground_up − deductible, 0), limit); net = gross × coinsurance",
        interactive_example="Change the deductible in the Model panel and watch gross and net update while ground-up stays fixed.",
        common_mistake="Expecting a higher deductible to increase the insured loss — it never does.",
        real_world_use="These invariants are unit-tested so financial results stay internally consistent.",
        platform_link="/model",
        knowledge_check=_kc("Raising the deductible…", ["Increases insured loss", "Never increases insured loss", "Has no effect ever"], 1, "A higher deductible can only reduce or hold the insured loss."),
    ),
    Lesson(
        lesson_id="aal", order=8, title="Average Annual Loss",
        one_sentence="AAL is the long-term modelled average loss per year.",
        plain_language="It does not mean you lose that amount every year — most years are low and a few are extreme; AAL is the average.",
        technical_definition="AAL = Σ_e λ_e × E[L_e], the rate-weighted expected loss over the event set.",
        formula="AAL = Σ_e λ_e × E[L_e]",
        interactive_example="Open the Probabilistic tab and read AAL beside the EP curves.",
        common_mistake="Interpreting AAL as a guaranteed annual cost.",
        real_world_use="AAL underpins technical pricing and mitigation benefit-cost comparisons.",
        platform_link="/model",
        knowledge_check=_kc("AAL means…", ["The loss every year", "The long-term average yearly loss", "The worst-case loss"], 1, "AAL is a long-run average, not a per-year guarantee."),
    ),
    Lesson(
        lesson_id="oep-aep", order=9, title="OEP and AEP",
        one_sentence="OEP is the largest single event per year; AEP is the aggregate per year.",
        plain_language="OEP asks 'how bad is the biggest single event in a year?'; AEP asks 'how bad is the total of all events in a year?'.",
        technical_definition="OEP is the exceedance curve of the annual maximum event loss; AEP of the annual aggregate loss. At equal return period AEP ≥ OEP.",
        formula=None,
        interactive_example="Compare the OEP and AEP rows at the same return period in the Probabilistic tab.",
        common_mistake="Using OEP and AEP interchangeably, or quoting them without the return period and loss basis.",
        real_world_use="Occurrence covers apply to OEP; aggregate covers apply to AEP.",
        platform_link="/model",
        knowledge_check=_kc("At the same return period…", ["OEP ≥ AEP", "AEP ≥ OEP", "They are always equal"], 1, "Aggregate loss is at least the largest single-event loss."),
    ),
    Lesson(
        lesson_id="return-periods", order=10, title="Return periods",
        one_sentence="A return period is the average time between events — or losses — of a given size.",
        plain_language="A '100-year' level is one exceeded on average once per 100 years; it can happen in consecutive years.",
        technical_definition="Return period = 1 / annual exceedance probability. A return-period event and a return-period loss are distinct.",
        formula="return_period = 1 / exceedance_probability",
        interactive_example="Read the return-period labels on the EP curve and note they are loss return periods.",
        common_mistake="Confusing a return-period hazard event with a return-period loss.",
        real_world_use="The platform labels EP-curve return periods as loss return periods, not event return periods.",
        platform_link="/model",
        knowledge_check=_kc("A 100-year loss…", ["Happens exactly every 100 years", "Has a 1% annual exceedance probability", "Is the same as a 100-year rainfall"], 1, "It is a 1% annual exceedance probability of loss, not a fixed schedule."),
    ),
    Lesson(
        lesson_id="var-tvar", order=11, title="VaR and TVaR",
        one_sentence="VaR is a loss quantile; TVaR is the average loss beyond it.",
        plain_language="VaR says 'we are X% sure loss won't exceed this'; TVaR says 'if it does, this is the average of how bad'.",
        technical_definition="VaR_q is the q-quantile of the loss distribution; TVaR_q is the mean of losses beyond VaR_q.",
        formula="TVaR_q = E[L | L ≥ VaR_q]",
        interactive_example="Read the VaR and TVaR tiles in the Probabilistic tab at 95/99%.",
        common_mistake="Quoting VaR without its probability and time period.",
        real_world_use="Capital and reinsurance decisions use tail measures like TVaR.",
        platform_link="/model",
        knowledge_check=_kc("TVaR captures…", ["The most likely loss", "The average loss beyond a tail threshold", "The deductible"], 1, "TVaR averages the losses beyond the VaR threshold."),
    ),
    Lesson(
        lesson_id="secondary-uncertainty", order=12, title="Secondary uncertainty",
        one_sentence="Secondary uncertainty is the spread of damage at a fixed hazard intensity.",
        plain_language="Even at exactly 3 feet of water, identical-looking buildings differ; secondary uncertainty is that spread, shown as a distribution.",
        technical_definition="The conditional variance of the damage ratio given intensity, propagated to a loss distribution via sampling.",
        formula=None,
        interactive_example="Open the Uncertainty tab to see the Monte Carlo percentile spread of loss.",
        common_mistake="Collapsing all uncertainty into one vague 'confidence' word without its drivers.",
        real_world_use="The platform shows a loss range with percentiles and lists the drivers behind the confidence band.",
        platform_link="/model",
        knowledge_check=_kc("Secondary uncertainty is about…", ["Where the hazard is", "Damage spread at a fixed intensity", "The insurance limit"], 1, "It is the damage variability at a given hazard intensity."),
    ),
    Lesson(
        lesson_id="cascading-risk", order=13, title="Cascading infrastructure risk",
        one_sentence="One failure can propagate through dependent infrastructure.",
        plain_language="A flooded substation can cut power, which stops water pumping, which strains a hospital — the first failure cascades.",
        technical_definition="A dependency graph of nodes and directed edges; failure propagates by rules (MVP) or probabilistic network models (advanced), with recovery timelines.",
        formula=None,
        interactive_example="Trace flood → substation → water → hospital in the cascade view.",
        common_mistake="Presenting an experimental cascade model as validated operational truth.",
        real_world_use="Cascading models are labelled experimental until validated.",
        platform_link="/model",
        knowledge_check=_kc("A cascade model shows…", ["Only direct damage", "How failures propagate through dependencies", "The insurance premium"], 1, "It models indirect, propagating failures across dependent systems."),
    ),
    Lesson(
        lesson_id="responsible-use", order=14, title="Ethical and responsible model use",
        one_sentence="Model outputs are decision support with limits, not certainties.",
        plain_language="Always show the assumptions, uncertainty, resolution and missing data; never present an inferred value as observed or hide disagreement.",
        technical_definition="Governance: provenance and certainty on every value, model versioning and manifests, human review before promotion, and no LLM-computed losses.",
        formula=None,
        interactive_example="Open any result and read its sources, assumptions, confidence drivers and limitations.",
        common_mistake="Showing false precision or presenting demonstration output as validated production loss.",
        real_world_use="Every result in this platform carries provenance, a confidence band with drivers, and explicit limitations.",
        platform_link="/model",
        knowledge_check=_kc("A responsible loss result must show…", ["Only the headline number", "Assumptions, uncertainty, provenance and limitations", "The engineer's opinion"], 1, "Transparency about assumptions, uncertainty, provenance and limits is required."),
    ),
]

_LESSON_BY_ID = {lesson.lesson_id: lesson for lesson in LESSONS}

GLOSSARY: list[GlossaryTerm] = [
    GlossaryTerm(term="AAL", short="Average Annual Loss", detail="The long-term modelled average loss per year; not a per-year guarantee.", related_lesson_id="aal"),
    GlossaryTerm(term="OEP", short="Occurrence Exceedance Probability", detail="Exceedance curve of the largest single event loss in a year.", related_lesson_id="oep-aep"),
    GlossaryTerm(term="AEP", short="Aggregate Exceedance Probability", detail="Exceedance curve of the total loss from all events in a year.", related_lesson_id="oep-aep"),
    GlossaryTerm(term="VaR", short="Value at Risk", detail="A selected loss quantile — the level a chosen probability will not exceed.", related_lesson_id="var-tvar"),
    GlossaryTerm(term="TVaR", short="Tail Value at Risk", detail="The average loss beyond a selected tail threshold.", related_lesson_id="var-tvar"),
    GlossaryTerm(term="Damage ratio", short="Fraction of value lost", detail="The share of an asset's replacement value lost at a given hazard intensity.", related_lesson_id="damage-states"),
    GlossaryTerm(term="Fragility curve", short="P(damage state | intensity)", detail="Probability of reaching or exceeding a damage state as intensity rises.", related_lesson_id="vulnerability-fragility"),
    GlossaryTerm(term="Return period", short="1 / annual exceedance probability", detail="Average time between events, or losses, of a given size; event ≠ loss return period.", related_lesson_id="return-periods"),
    GlossaryTerm(term="Ground-up loss", short="Total economic loss", detail="Loss before insurance terms are applied.", related_lesson_id="financial-loss"),
    GlossaryTerm(term="Secondary uncertainty", short="Damage spread at fixed intensity", detail="Variability of damage at a given hazard intensity, shown as a distribution.", related_lesson_id="secondary-uncertainty"),
]

_GLOSSARY_BY_TERM = {term.term.lower(): term for term in GLOSSARY}


def list_lessons() -> list[LessonSummary]:
    return [LessonSummary(lesson_id=le.lesson_id, order=le.order, title=le.title, one_sentence=le.one_sentence)
            for le in sorted(LESSONS, key=lambda x: x.order)]


def get_lesson(lesson_id: str) -> Lesson | None:
    return _LESSON_BY_ID.get(lesson_id)


def list_glossary() -> list[GlossaryTerm]:
    return sorted(GLOSSARY, key=lambda t: t.term.lower())


def get_glossary_term(term: str) -> GlossaryTerm | None:
    return _GLOSSARY_BY_TERM.get(term.lower())
