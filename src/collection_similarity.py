from itertools import combinations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compare_document_collection(documents):
    """Compare every non-empty document with every other document."""
    valid_documents = {
        name: text.strip()
        for name, text in documents.items()
        if text and text.strip()
    }

    if len(valid_documents) < 2:
        raise ValueError("At least two non-empty assignments are required.")

    names = list(valid_documents)
    vectorizer = TfidfVectorizer()

    try:
        vectors = vectorizer.fit_transform(valid_documents.values())
    except ValueError as error:
        raise ValueError(
            "The uploaded assignments do not contain enough readable words "
            "to calculate similarity."
        ) from error

    scores = cosine_similarity(vectors) * 100
    similarity_df = pd.DataFrame(scores, index=names, columns=names)

    pairs = [
        {
            "assignment_a": names[first],
            "assignment_b": names[second],
            "similarity": float(scores[first, second]),
        }
        for first, second in combinations(range(len(names)), 2)
    ]
    pairs_df = pd.DataFrame(
        pairs,
        columns=["assignment_a", "assignment_b", "similarity"],
    ).sort_values("similarity", ascending=False, ignore_index=True)

    return similarity_df, pairs_df


def find_similarity_groups(similarity_df, threshold=50):
    """Find connected groups whose edges meet the percentage threshold."""
    names = list(similarity_df.index)
    visited = set()
    groups = []

    for start in names:
        if start in visited:
            continue

        stack = [start]
        visited.add(start)
        group = []

        while stack:
            current = stack.pop()
            group.append(current)

            for other in names:
                if other in visited or other == current:
                    continue
                if similarity_df.loc[current, other] >= threshold:
                    visited.add(other)
                    stack.append(other)

        if len(group) > 1:
            groups.append(group)

    return groups
