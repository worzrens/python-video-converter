# writing-rules

Style rules for prose written into `knowledge_base/`. `kb-compile` applies these when drafting or updating
an article; `kb-lint` audits existing articles against them and fixes unambiguous violations directly.

Adapted from Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
essay, narrowed to what applies to a small technical KB: single-source-of-truth documentation of one repo's
own code, not open-ended synthesis of external sources. Sections below map to categories from that page —
vocabulary, sentence patterns, structural formulas, attribution habits, formatting tics.

**Scope**: applies to the body prose of any file under `wiki/concepts/`, `wiki/decisions/`, and prose-heavy
files under `outputs/` (e.g. `outputs/qna/*.md`). Does **not** apply to navigation files (`_index.md`,
`QUESTIONS.md`, `README.md`, `raw/**/meta.md`, `raw/**/source.md`) or direct quotes/verbatim code excerpts,
which are preserved as-is even if they'd otherwise trip a rule below.

## Spelling

American English, matching the rest of this repo (`organize`, `color`, `-ize` endings). Don't introduce
British spellings.

## Banned words and phrases

Swap these for plainer alternatives, or cut them, when the replacement is unambiguous. If no clean
replacement fits, leave it and let `kb-lint` flag it as a judgement call rather than forcing an awkward
rewrite. A single instance of one of these words isn't automatically a violation — the tell is several of
them clustering in the same paragraph, or the same word/pattern recurring across unrelated articles.

**Vague-significance vocabulary** — words that assert importance instead of showing it:
"crucial," "key," "vital," "pivotal," "significant" (as filler, not a measured claim), "enduring," "profound"
→ name the actual mechanism or consequence instead ("this fixes X" beats "this plays a key role in X").

**Inflated-verb vocabulary** — words that dress up a plain action:
"leverage" → "use"; "utilize" → "use"; "delve into" → "look at" / "cover"; "boast(s)" → "has"; "showcase" →
"show" / "demonstrate"; "underscore(s)" → "shows"; "highlight(s)" (as a transition, not a literal UI
highlight) → "shows" / cut; "foster(ing)" → cut or name the real effect; "garner" → "get"; "enhance" → "improve"
/ name the specific change; "bolster(ed)" → "support(ed)."

**Vague-quality vocabulary** — words that stand in for a property instead of stating it:
"robust" → name the actual property ("handles X without crashing," not "robust error handling"); "seamless(ly)"
→ cut, or name what actually connects; "intricate(cies)" → cut or describe the specific complexity;
"meticulous(ly)" → cut or name the specific care taken; "comprehensive" → cut unless quantified.

**Legacy/framing filler** — phrases that manufacture significance around a fact:
"stands/serves as a testament to," "marks a turning point," "represents a shift," "reflects broader," "sets
the stage for," "evolving landscape," "rich tapestry" → cut the framing, state the fact.

**Marketing/puffery** — phrases that read as promotional copy, not documentation:
"cutting-edge," "state-of-the-art," "game-changer," "groundbreaking," "renowned," "diverse array,"
"vibrant," "nestled," "in the heart of," "offers users/visitors" → cut, or replace with the concrete fact
being dressed up.

**Throat-clearing** — phrases that delay the actual content:
"in today's ...," "in the fast-paced world of ...," "it's worth noting that," "it's important to note that,"
"needless to say" → cut entirely; start with the fact.

**Hedged-importance pattern** — conceding a fact is minor, then asserting significance anyway ("though this
saw limited use, it contributes to the broader ..."). If a detail is minor, say so and stop; don't recover
significance with a dependent clause.

## Sentence patterns to avoid

- **Copula avoidance.** Don't replace a plain "is"/"are"/"has" with "serves as," "stands as," "represents,"
  "boasts," "features," "maintains" as a reflex. Use the plain verb unless the fancier one is genuinely more
  precise.
- **Negative parallelism as a crutch.** "Not just X, but Y," "not only X but also Y," "it's not X — it's Y"
  are fine occasionally but become a tell when reached for repeatedly. If a fact can be stated directly,
  state it directly instead of setting up a straw version to knock down first.
- **Rule-of-three padding.** Adjective or phrase triplets ("fast, flexible, and reliable") used to make a
  thin point sound comprehensive. Only list three things when there really are three distinct things worth
  naming.
- **Unattributed "-ing" tails.** Don't tack a present-participle clause onto a fact to imply significance
  without sourcing it — "`_repair_metadata_text()` fixes mojibake, reflecting the tool's attention to
  real-world edge cases" is the pattern to avoid. State what the code does; skip the unsourced editorializing
  about what it "reflects" or "underscores."

## Structural tics to avoid

- **Boilerplate "Challenges and Future" sections.** Don't append a formulaic closing section that raises
  vague challenges and gestures at future improvement just to give an article a wrap-up. If there's a real,
  sourced limitation or open question, it belongs in the article body or `wiki/QUESTIONS.md` — not a generic
  "despite its strengths, X faces challenges going forward" paragraph.
- **Key-takeaways bullet dumps.** Don't close an article with a bolded-header bullet list re-summarizing
  what the prose just said. `## See also` and `## Open Questions`-style sections (where used) exist for
  navigation, not restatement.
- **Undue significance for mundane facts.** Don't dress up a routine implementation detail in
  historical/legacy language. State what a function does and why, at the scale the fact actually warrants.

## Attribution rules

Don't attribute claims to vague, uncited sources: "industry reports," "observers have noted," "experts
argue," "several sources suggest." This KB has exactly one class of source — the actual repo (code, git
history, design docs) — so every claim traces to a specific file, commit, or raw entry already, per the
no-fabrication rule in `README.md`. If a claim can't be pinned to one of those, it doesn't get stated as
fact; it goes in `wiki/QUESTIONS.md` instead.

## Formatting rules

- **Em-dash bullet pattern.** Don't use `**Term** —` to open a labeled bullet. Use `**Term:**` instead — a
  colon is the right punctuation for a label-and-description bullet. (Em-dashes are fine elsewhere in a
  sentence — this rule is about bullet-opening labels specifically.)
- **No emoji as structural markers.** Don't use emoji in place of bullets, headers, or spacing.
- **No mechanical over-bolding.** Bold a term once to introduce it, not every time it recurs in the article.
- **Sentence-case headings**, matching this repo's existing convention (`# ffmpeg pipeline`, not `# Ffmpeg
  Pipeline` or `# FFmpeg Pipeline System`).

## `/kb-ask` answer provenance line

Every `/kb-ask` answer — both the chat response and the filed `outputs/qna/*.md` copy, if filed — opens with
a one-line provenance tag, before the actual answer, stating how it was produced:

- `**Answer source:** existing Q&A` — an already-filed `outputs/qna/*.md` entry directly answers this;
  reused as-is, no new research.
- `**Answer source:** wiki` — fully answered from `wiki/concepts/`/`wiki/decisions/` articles, no repo-source
  fallback needed.
- `**Answer source:** wiki + repo source` — the wiki covered part of it; the rest came from a fresh read of
  actual repo files.
- `**Answer source:** repo source` — the wiki didn't cover this at all; answered entirely from a fresh read
  of actual repo files.

This exists so a reader (or the person deciding whether to trust an answer as cheap-to-regenerate) can tell
at a glance how much fresh work went into it. It's a factual tag, not a quality signal — don't round up to a
cheaper-sounding tier. If any part of the answer needed a fresh source read, say so, even if most of it came
from the wiki.

## General tone

Plain, specific, technical prose — the voice already used across `wiki/concepts/` and `wiki/decisions/`:
short paragraphs, concrete function/commit references, no padding, no marketing language, no unearned
superlatives. Prefer naming the actual mechanism (`_repair_metadata_text() re-encodes as cp1251...`) over
describing it abstractly ("robustly handles encoding issues"). Reusing the same function or module name
across a paragraph is fine and often clearer than varying the wording for its own sake — don't swap in a
synonym just to avoid repetition.
