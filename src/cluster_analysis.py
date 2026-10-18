import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _cluster_keywords(tfidf_matrix, feature_names, member_indices, limit=8):
    cluster_vectors = tfidf_matrix[member_indices]
    mean_weights = np.asarray(cluster_vectors.mean(axis=0)).ravel()
    ranked_indices = np.argsort(mean_weights)[::-1]
    return [
        feature_names[index]
        for index in ranked_indices
        if mean_weights[index] > 0
    ][:limit]


def cluster_documents(documents, similarity_threshold=55):
    """Cluster documents with average-linkage cosine-distance clustering."""
    valid_documents = {
        name: text.strip()
        for name, text in documents.items()
        if text and text.strip()
    }

    if len(valid_documents) < 2:
        raise ValueError("At least two non-empty assignments are required.")
    if not 1 <= similarity_threshold <= 99:
        raise ValueError("Similarity threshold must be between 1 and 99.")

    names = list(valid_documents)
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=10000,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(valid_documents.values())
    except ValueError as error:
        raise ValueError(
            "The assignments do not contain enough usable text for clustering."
        ) from error

    similarities = cosine_similarity(tfidf_matrix)
    distances = np.clip(1 - similarities, 0, 1)
    distance_threshold = 1 - (similarity_threshold / 100)

    model = AgglomerativeClustering(
        n_clusters=None,
        metric="precomputed",
        linkage="average",
        distance_threshold=distance_threshold,
    )
    labels = model.fit_predict(distances)

    similarity_df = pd.DataFrame(
        similarities * 100,
        index=names,
        columns=names,
    )
    feature_names = vectorizer.get_feature_names_out()
    assignment_rows = []
    summary_rows = []

    for cluster_id in sorted(set(labels)):
        member_indices = np.where(labels == cluster_id)[0]
        member_names = [names[index] for index in member_indices]
        keywords = _cluster_keywords(
            tfidf_matrix,
            feature_names,
            member_indices,
        )

        if len(member_indices) > 1:
            internal_scores = similarities[np.ix_(
                member_indices,
                member_indices,
            )]
            upper_triangle = internal_scores[
                np.triu_indices(len(member_indices), k=1)
            ]
            average_similarity = float(upper_triangle.mean() * 100)
        else:
            average_similarity = 100.0

        for name in member_names:
            own_index = names.index(name)
            other_indices = [
                index
                for index in member_indices
                if index != own_index
            ]
            closest_similarity = (
                float(similarities[own_index, other_indices].max() * 100)
                if other_indices
                else None
            )
            assignment_rows.append({
                "Assignment": name,
                "Cluster": int(cluster_id) + 1,
                "Closest member similarity (%)": closest_similarity,
            })

        summary_rows.append({
            "Cluster": int(cluster_id) + 1,
            "Size": len(member_names),
            "Keywords": ", ".join(keywords) or "No distinctive terms",
            "Average internal similarity (%)": round(
                average_similarity,
                2,
            ),
            "Assignments": ", ".join(member_names),
        })

    assignments_df = pd.DataFrame(assignment_rows)
    cluster_summary_df = pd.DataFrame(summary_rows)
    return assignments_df, cluster_summary_df, similarity_df
