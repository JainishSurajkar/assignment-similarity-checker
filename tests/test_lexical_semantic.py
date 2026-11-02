import builtins

import numpy as np
import pytest

import lexical_semantic


def test_semantic_model_import_is_lazy():
    assert "SentenceTransformer" not in lexical_semantic.__dict__


def test_missing_semantic_dependency_has_clear_error(monkeypatch):
    lexical_semantic.load_semantic_model.cache_clear()
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError("dependency unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    with pytest.raises(
        lexical_semantic.SemanticDependencyError,
        match="sentence-transformers",
    ):
        lexical_semantic.load_semantic_model()
    lexical_semantic.load_semantic_model.cache_clear()


def test_semantic_scores_preserve_negative_cosine_values(monkeypatch):
    class FakeModel:
        def encode(self, texts, **kwargs):
            return np.array([[1.0, 0.0], [-1.0, 0.0]])

    monkeypatch.setattr(
        lexical_semantic,
        "load_semantic_model",
        lambda: FakeModel(),
    )
    results = lexical_semantic.compare_lexical_and_semantic(
        "alpha words",
        "beta words\n\nother words",
    )
    assert results.iloc[0]["semantic_similarity"] == pytest.approx(100.0)
    assert results.iloc[1]["semantic_similarity"] == pytest.approx(-100.0)
