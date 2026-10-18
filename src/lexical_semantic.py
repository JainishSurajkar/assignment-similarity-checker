from functools import lru_cache

import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from similarity import split_paragraph


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def load_semantic_model():
    """Load the embedding model once per Python process."""
    return SentenceTransformer(MODEL_NAME)


def compare_lexical_and_semantic(text_a, text_b):
    """Compare every paragraph pair with lexical and semantic scores."""
    paragraphs_a = split_paragraph(text_a)
    paragraphs_b = split_paragraph(text_b)

    if not paragraphs_a or not paragraphs_b:
        raise ValueError("Both assignments must contain readable paragraphs.")

    all_paragraphs = paragraphs_a + paragraphs_b
    vectorizer = TfidfVectorizer()
    try:
        lexical_vectors = vectorizer.fit_transform(all_paragraphs)
    except ValueError as error:
        raise ValueError(
            "The assignments do not contain enough readable words "
            "to calculate lexical similarity."
        ) from error

    count_a = len(paragraphs_a)
    lexical_scores = cosine_similarity(
        lexical_vectors[:count_a],
        lexical_vectors[count_a:],
    )

    model = load_semantic_model()
    embeddings_a = model.encode(
        paragraphs_a,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    embeddings_b = model.encode(
        paragraphs_b,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    semantic_scores = embeddings_a @ embeddings_b.T

    results = []
    for index_a, paragraph_a in enumerate(paragraphs_a):
        for index_b, paragraph_b in enumerate(paragraphs_b):
            lexical = float(lexical_scores[index_a, index_b] * 100)
            semantic = float(semantic_scores[index_a, index_b] * 100)
            results.append({
                "paragraph_a": index_a + 1,
                "paragraph_b": index_b + 1,
                "text_a": paragraph_a,
                "text_b": paragraph_b,
                "lexical_similarity": lexical,
                "semantic_similarity": semantic,
                "difference": semantic - lexical,
            })

    return pd.DataFrame(results).sort_values(
        "semantic_similarity",
        ascending=False,
        ignore_index=True,
    )
