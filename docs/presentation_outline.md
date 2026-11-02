# Presentation outline

1. **Title** — Assignment Similarity Checker and the GTU DMT motivation.
2. **Problem and scope** — finding passages for human review, not declaring
   plagiarism.
3. **Objectives** — extraction, lexical similarity, optional semantic scores,
   collection analysis, clustering, and evaluation.
4. **Architecture** — upload, extraction/OCR, normalization, vectors, scores,
   groups, clusters, and exports.
5. **TF-IDF and cosine** — equations, percent display, and interpretation.
6. **Semantic comparison and clustering** — embeddings, average linkage,
   thresholds, and silhouette limitations.
7. **Dataset and evaluation** — synthetic demo corpus versus 60-pair
   illustrative benchmark; validation threshold selection and held-out test.
8. **Experimental results** — populate from `docs/evaluation/metrics.csv`;
   otherwise show “pending run” rather than inventing values.
9. **Live demonstration** — pair, highlighting, collection, groups, clusters,
   evaluation, and CSV export using `sample_data/demo/`.
10. **Conclusion and future scope** — human review, larger reviewed data,
    stronger leakage controls, and privacy.
