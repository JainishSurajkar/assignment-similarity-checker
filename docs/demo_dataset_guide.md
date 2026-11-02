# Demonstration dataset

The files in `sample_data/demo` are a small, controlled dataset for presenting
the Assignment Similarity Checker to an instructor. They are intentionally
short so that the output is easy to explain during a demonstration.

## Recommended demonstration

1. Start the application:

   ```powershell
   streamlit run src\app.py
   ```

2. Upload `01_original_machine_learning.txt` and
   `03_exact_overlap.txt`.
3. Show the high similarity produced by the exact copied paragraphs.
4. Replace the second file with `02_close_paraphrase.txt` and show that the
   wording is different but the ideas are closely related.
5. Upload three to six files to demonstrate Collection Analysis.
6. Use `05_unrelated_biology.txt` to show a low-similarity comparison.

## Expected relationships

| Files | Intended relationship | Expected result |
| --- | --- | --- |
| 01 and 03 | Exact overlap | Very high similarity |
| 01 and 02 | Close paraphrase | High similarity, wording differs |
| 01 and 04 | Same broad topic, different explanation | Lower or moderate similarity |
| 01 and 05 | Unrelated subject | Low similarity |
| 01 and 06 | Shared machine-learning vocabulary only | Lower similarity than the paraphrase |

The expected result is qualitative, not a fixed percentage. The score can
change when the similarity threshold, tokenizer, or comparison implementation
changes.

This dataset demonstrates text similarity, not plagiarism detection. A shared
passage may be legitimate because of a prompt, textbook, or permitted source.
Human review and academic context are always required.
