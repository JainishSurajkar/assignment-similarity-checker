import pandas as pd

from evaluate_models import score_dataset


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
