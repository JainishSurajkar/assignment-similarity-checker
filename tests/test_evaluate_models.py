import pandas as pd
import pytest

from evaluate_models import (
    compare_methods,
    evaluate_threshold,
    load_dataset,
    score_dataset,
)


def test_lexical_vectorizer_is_fit_on_training_text(monkeypatch):
    class FakeVectorizer:
        fitted_on = None

        def fit(self, texts):
            self.fitted_on = list(texts)
            FakeVectorizer.fitted_on = self.fitted_on
            return self

        def transform(self, texts):
            return [[1] for _ in texts]

    monkeypatch.setattr(
        "evaluate_models.TfidfVectorizer",
        FakeVectorizer,
    )
    monkeypatch.setattr(
        "evaluate_models.cosine_similarity",
        lambda left, right: pd.DataFrame([[1, 0], [0, 1]]).to_numpy(),
    )

    class FakeModel:
        def encode(self, texts, **kwargs):
            return [[1, 0] for _ in texts]

    monkeypatch.setattr(
        "evaluate_models.load_semantic_model",
        lambda: FakeModel(),
    )
    dataframe = pd.DataFrame([
        {"pair_id": "T", "text_a": "train only", "text_b": "train pair",
         "label": 1, "split": "train"},
        {"pair_id": "V", "text_a": "validation", "text_b": "held out",
         "label": 0, "split": "validation"},
    ])
    score_dataset(dataframe)
    assert FakeVectorizer.fitted_on == [
        "train only",
        "train pair",
    ]


def test_evaluation_metrics_include_confusion_counts():
    dataframe = pd.DataFrame({
        "label": [1, 0, 1, 0],
        "score": [90, 80, 20, 10],
    })
    metrics = evaluate_threshold(dataframe, "score", 50)
    assert metrics["TP"] == 1
    assert metrics["TN"] == 1
    assert metrics["FP"] == 1
    assert metrics["FN"] == 1


def test_invalid_split_is_rejected(tmp_path):
    path = tmp_path / "pairs.csv"
    path.write_text(
        "pair_id,text_a,text_b,label,split\n"
        "P1,a,b,1,development\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid split"):
        load_dataset(path)


def test_validation_without_training_split_is_rejected():
    dataframe = pd.DataFrame([
        {
            "pair_id": "V",
            "text_a": "validation text",
            "text_b": "other text",
            "label": 0,
            "split": "validation",
        },
    ])
    with pytest.raises(ValueError, match="non-empty train"):
        score_dataset(dataframe)


def test_threshold_selection_does_not_use_test_labels():
    validation = pd.DataFrame({
        "label": [0, 1],
        "lexical_score": [10, 90],
        "semantic_score": [10, 90],
    })
    test_a = pd.DataFrame({
        "label": [0, 1],
        "lexical_score": [20, 80],
        "semantic_score": [20, 80],
    })
    test_b = test_a.copy()
    test_b["label"] = [1, 0]
    metrics_a = compare_methods(validation, test_a)
    metrics_b = compare_methods(validation, test_b)
    assert metrics_a["Threshold"].tolist() == metrics_b["Threshold"].tolist()
