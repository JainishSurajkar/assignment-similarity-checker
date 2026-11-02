# Annotation guidelines

## Objective

Label whether a pair of passages contains **substantial content overlap**.
This label describes textual overlap or close paraphrase; it does not
determine whether plagiarism occurred.

## Label 1: substantial overlap

Use `1` when the passages share a meaningful passage, claim, explanation,
sequence of ideas, or close paraphrase beyond ordinary topic similarity,
standard terminology, or a short common phrase.

Examples include:

- Exact or near-exact copies
- A close paraphrase with different wording
- The same explanation or sequence of ideas

## Label 0: no substantial overlap

Use `0` when the passages do not share a substantial explanation or closely
corresponding content. This includes:

- Different claims about the same topic
- Common technical definitions without meaningful passage overlap
- Unrelated subjects

## Uncertain examples

Review uncertain examples against this rule before assigning a final label.
Record the reason in the `reason` column. Keep related examples from the same
source assignment in the same train, validation, or test split where possible.

## Important limitation

The label is not a plagiarism judgement. A shared explanation may be caused by
an assignment prompt, a textbook, permitted references, or standard teaching
material. Human review and the surrounding academic context are still
required.

The repository CSV is a starter benchmark for demonstrating the evaluation
workflow. Before making any performance claim, replace or expand it with pairs
reviewed by people familiar with the assignment domain, record the reason for
each label, and keep related pairs in the same split where possible.
