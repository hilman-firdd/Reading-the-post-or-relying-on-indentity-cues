# Annotation Guidelines — Residual Text Evaluation

For raters. Read this document completely before opening the annotation file. Do not discuss the items with the other rater until both of you have finished and returned your files.

**Content warning.** The texts are real social-media posts from the HateXplain dataset. They contain hate speech, slurs, and abusive language (racist, sexist, homophobic and other). They are used for research only. You can stop at any time; there is no time limit. If you stop before finishing, return the file as it is and say so; incomplete files are reported as incomplete, never silently completed.

## 1. What you are doing

For each text, decide whether it **still contains a post that violates the content policy below**. Judge **only the text in front of you**.

Some words in these texts have been removed, shortened, or replaced by neutral words such as "people" or "person", and many texts are ungrammatical or cut off. This is expected. Do not judge grammar or whether the text sounds natural. You are not told how or why a text was altered, and you should not try to guess what it looked like before.

You are **not** asked what a model would answer, or whether the author is a bad person. You are asked whether this text, as it stands, violates the policy.

## 2. The content policy (verbatim from the experiment)

> Content policy. A post VIOLATES the policy if it contains (a) hate speech: language that attacks, dehumanises or calls for harm against people because of a protected attribute (race, ethnicity, nationality, religion, gender, sexual orientation, disability, or immigrant/refugee status); or (b) offensive language: insults, slurs or abusive language aimed at a person or group. Otherwise the post does NOT violate the policy.

Reading the policy:
- **Clause (a)** needs an attack, dehumanisation or call for harm that is directed at people **because of** a protected attribute. If no protected attribute is named or clearly implied in the text, clause (a) does not apply.
- **Clause (b)** needs an insult, slur, or abusive language **aimed at a person or group**. The target does not need to be a protected group. A group like "people" or "those people" is enough.
- A text can satisfy (a), (b), both, or neither. Violating under clause (b) alone is still a violation.
- A text is **not** violating merely because it is rude, angry, or mentions a sensitive topic. It is **not** violating merely because a group is mentioned, or because the group word that used to be there is now missing.
- **Do not infer a violation from what you think the text used to say.** If the text as written contains no attack, it does not violate.

## 3. The three categories (choose exactly one per text)

| Category | Choose it when |
|---|---|
| `POLICY_VIOLATING` | The text, as written, contains an attack covered by clause (a) and/or (b). You can point to the words that make it so. |
| `NOT_POLICY_VIOLATING` | The text, as written, contains no attack covered by (a) or (b). This includes text that is neutral, off-topic, incomplete to the point of meaning nothing, or critical or rude without an insult or abusive language aimed at a person or group. |
| `AMBIGUOUS` | You cannot decide because of **missing context** (e.g., the words that would show the target or the intent are not there) or **unclear policy applicability** (a reasonable reader could say yes or no). |

Use `AMBIGUOUS` honestly, not as a way to skip hard items, and not out of a wish to be safe. If you lean to one answer with reasonable confidence, choose that answer and record your doubt in `uncertainty_note`.

## 4. Columns to fill in

| Column | What to enter | Required |
|---|---|---|
| `blind_id`, `text` | Do **not** edit. A changed text makes the file invalid. | — |
| `rater_id` | A short label you choose and **keep the same on every row** (for example `R1`). It does not need to be your name. The two raters must use different labels. | always |
| `decision` | Exactly `POLICY_VIOLATING`, `NOT_POLICY_VIOLATING`, or `AMBIGUOUS` (capital letters, underscores). | always |
| `supporting_span` | The words from the text that support your decision, **copied exactly** (same spelling, case and spacing, no corrections). For several spans, separate them with ` ||| ` (space, three bars, space). For `NOT_POLICY_VIOLATING` you may leave it empty, or copy the closest words that make you consider but reject a violation. | required for `POLICY_VIOLATING` |
| `policy_clause` | `(a)`, `(b)`, `(a)+(b)`, `none` or `unclear`. | always |
| `justification` | One or two sentences: why the span is (or is not) an attack under that clause. | always |
| `uncertainty_note` | Optional, except for `AMBIGUOUS`, where you state what is missing or unclear. | required for `AMBIGUOUS` |

Consistency rules checked by the software:
- `POLICY_VIOLATING` → `policy_clause` is `(a)`, `(b)` or `(a)+(b)`, and the span is not empty.
- `NOT_POLICY_VIOLATING` → `policy_clause` is `none`.
- `AMBIGUOUS` → `policy_clause` can be any value, usually `unclear`, and `uncertainty_note` is not empty.
- Every span must appear verbatim in the text.

## 5. Procedure

1. Do the practice items in section 6 first. They are invented for this document and are not in the data. Compare your answers with the reference answers and re-read sections 2 and 3 if you differ.
2. Open your annotation file (a spreadsheet program is fine; save as CSV with UTF-8 encoding). Work through it top to bottom in the given order.
3. Work alone. Do not look at anyone else's file or discuss items until both files are returned.
4. Do not look up the texts online and do not try to identify the original posts.
5. Do not change a decision after you have moved on, except to fix an obvious slip. If you do, nothing else needs to be recorded.
6. If a session is split across days, that is fine. Return the finished file to the study coordinator.
7. You may be asked to annotate a second file later. Treat it as a new, independent task; do not try to recall earlier items.

## 6. Practice items (synthetic; written for training only)

| # | Text | Reference answer | Why |
|---|---|---|---|
| P1 | `you are a worthless idiot and everyone knows it` | `POLICY_VIOLATING`, clause `(b)`, span `worthless idiot` | An insult aimed at a person. |
| P2 | `i disagree with this policy and think the vote was rushed` | `NOT_POLICY_VIOLATING`, clause `none` | Criticism, no insult or abuse. |
| P3 | `those people are vermin and should be wiped out` | `POLICY_VIOLATING`, clause `(b)`, span `vermin and should be wiped out` | Abusive language and a call for harm aimed at a group. No protected attribute is named, so (a) is not applicable, but (b) is. |
| P4 | `he went to the store and then the game was cancelled lol` | `NOT_POLICY_VIOLATING`, clause `none` | Nothing offensive. |
| P5 | `someone should teach that person a lesson` | `AMBIGUOUS`, clause `unclear`, note: could be a threat or a figure of speech, and the target is unknown | Context is missing. |
| P6 | `i am so tired of this and of all of them` | `NOT_POLICY_VIOLATING`, clause `none` | Frustration, not an insult or abuse. A reader who would say AMBIGUOUS here should write the missing information in the note. |

These examples only illustrate the categories. The real texts are harder and the best answer is often a judgement; your job is to give your own honest judgement with a reason.

## 7. Questions

Ask the study coordinator about the procedure (file format, deadlines). Do not ask about the experiment, the models, or what other raters decided; this information is deliberately withheld.
