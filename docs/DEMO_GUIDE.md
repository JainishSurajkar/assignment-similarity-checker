# Demonstration guide

1. Create and activate the virtual environment, install `requirements.txt`,
   and start with `streamlit run src\app.py`.
2. Upload `sample_data/demo/01_preprocessing_pipeline.txt` and
   `03_exact_overlap.txt`. Click **Compare assignments**.
3. Show the ranked paragraph scores and enable **Show shared-word
   highlighting**.
4. Open **Lexical vs Semantic** and click its comparison button. This step
   may download `all-MiniLM-L6-v2`; if the model is unavailable, explain the
   lexical results and continue.
5. Upload at least three demo files and click **Compare assignment
   collection**. Show the matrix and ranked pairs.
6. Open **Connected Groups**, then **Hierarchical Clustering**. Explain that
   connected groups can contain indirect links and that silhouette is
   unavailable for undefined cluster layouts.
7. Open **Model Evaluation**, run the held-out benchmark, and distinguish
   validation threshold selection from test metrics.
8. Download a CSV result and explain that percentages are similarity scores,
   not probabilities or plagiarism verdicts.
9. Finish with limitations: synthetic demo data, small illustrative
   benchmark, OCR/model prerequisites, and required human review.

If network access is unavailable, skip the semantic tab and demonstrate the
lexical pair, collection matrix, groups, clusters, CSV export, and evaluation
lexical metrics.
