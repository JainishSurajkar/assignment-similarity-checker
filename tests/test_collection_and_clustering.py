from collection_similarity import (
    compare_document_collection,
    find_similarity_groups,
)
from cluster_analysis import cluster_documents


def test_collection_groups_similar_documents():
    matrix, pairs = compare_document_collection({
        "a.txt": "shared assignment content",
        "b.txt": "shared assignment content",
        "c.txt": "different topic entirely",
    })
    assert len(pairs) == 3
    assert find_similarity_groups(matrix, threshold=90) == [["a.txt", "b.txt"]]
    assert len(pairs[pairs["similarity"] >= 90]) == 1


def test_singleton_cluster_has_no_closest_assignment():
    assignments, summary, _ = cluster_documents({
        "a.txt": "alpha beta gamma",
        "b.txt": "delta epsilon zeta",
    }, similarity_threshold=90)
    singleton_rows = summary[summary["Size"] == 1]
    assert not singleton_rows.empty
    assert (singleton_rows["Average internal similarity (%)"] == "N/A").all()
    assert "Closest assignment" in assignments.columns
    assert (assignments["Closest assignment"] == "N/A").all()
