import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.metrics.pairwise import cosine_similarity

from lexical_semantic import load_semantic_model


REQUIRED_COLUMNS = ["pair_id", "text_a", "text_b", "label"]
SCORE_COLUMNS = ["lexical_score", "semantic_score"]


def load_dataset(path="docs/test_pairs.csv"):
    dataframe = pd.read_csv(path)
    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]
    if missing:
        raise ValueError(f"Missing CSV columns: {missing}")

    dataframe = dataframe.dropna(subset=REQUIRED_COLUMNS).copy()
    if dataframe.empty:
        raise ValueError("The dataset contains no valid pairs.")
    if not dataframe["label"].isin([0, 1]).all():
        raise ValueError("Labels must be either 0 or 1.")
    if (
        dataframe["text_a"].astype(str).str.strip().eq("").any()
        or dataframe["text_b"].astype(str).str.strip().eq("").any()
    ):
        raise ValueError("Text fields must not be empty.")

    dataframe["label"] = dataframe["label"].astype(int)
    if "split" not in dataframe.columns:
        dataframe["split"] = "all"
    else:
        valid_splits = {"train", "validation", "test"}
        invalid_splits = sorted(
            set(dataframe["split"].astype(str)) - valid_splits
        )
        if invalid_splits:
            raise ValueError(
                f"Invalid split values: {invalid_splits}. Use train, "
                "validation, or test."
            )
    return dataframe


def score_dataset(dataframe):
    """Add lexical and scaled semantic cosine scores.

    The lexical vectorizer is fitted on training text only when labelled
    splits are available, then applied unchanged to validation and test text.
    """
    training = dataframe[dataframe["split"] == "train"]
    if (
        "split" in dataframe
        and set(dataframe["split"]) != {"all"}
        and training.empty
    ):
        raise ValueError(
            "A labelled evaluation dataset must contain a non-empty train "
            "split before validation or test scoring."
        )
    fit_dataframe = training if not training.empty else dataframe
    fit_texts = (
        fit_dataframe["text_a"].astype(str).tolist()
        + fit_dataframe["text_b"].astype(str).tolist()
    )
    texts = (
        dataframe["text_a"].astype(str).tolist()
        + dataframe["text_b"].astype(str).tolist()
    )
    try:
        vectorizer = TfidfVectorizer().fit(fit_texts)
        lexical_vectors = vectorizer.transform(texts)
    except ValueError as error:
        raise ValueError(
            "The evaluation text does not contain enough readable words."
        ) from error

    count = len(dataframe)
    lexical_scores = cosine_similarity(
        lexical_vectors[:count],
        lexical_vectors[count:],
    ).diagonal() * 100

    model = load_semantic_model()
    embeddings = np.asarray(model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ))
    semantic_scores = np.sum(
        embeddings[:count] * embeddings[count:],
        axis=1,
    ) * 100

    scored = dataframe.copy()
    scored["lexical_score"] = lexical_scores
    scored["semantic_score"] = semantic_scores
    return scored


def evaluate_threshold(dataframe, score_column, threshold):
    y_true = dataframe["label"].astype(int)
    y_pred = (dataframe[score_column] >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    ).ravel()
    return {
        "Method": score_column,
        "Threshold": threshold,
        "Precision": precision_score(y_true, y_pred, zero_division=0),
        "Recall": recall_score(y_true, y_pred, zero_division=0),
        "F1-score": f1_score(y_true, y_pred, zero_division=0),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp),
        "Count": len(dataframe),
    }


def select_threshold(validation_dataframe, score_column):
    best_threshold = 0.0
    best_f1 = -1.0
    minimum = -100 if score_column == "semantic_score" else 0
    for threshold in np.linspace(minimum, 100, 201):
        metrics = evaluate_threshold(
            validation_dataframe,
            score_column,
            float(threshold),
        )
        if metrics["F1-score"] > best_f1:
            best_f1 = metrics["F1-score"]
            best_threshold = float(threshold)
    return best_threshold


def compare_methods(validation_dataframe, test_dataframe):
    rows = []
    for score_column in SCORE_COLUMNS:
        threshold = select_threshold(validation_dataframe, score_column)
        rows.append(
            evaluate_threshold(
                test_dataframe,
                score_column,
                threshold,
            )
        )
    return pd.DataFrame(rows)


def get_misclassified_pairs(dataframe, score_column, threshold):
    result = dataframe.copy()
    result["predicted_label"] = (
        result[score_column] >= threshold
    ).astype(int)
    errors = result[result["label"] != result["predicted_label"]].copy()
    errors["error_type"] = np.where(
        errors["predicted_label"] == 1,
        "False positive",
        "False negative",
    )
    columns = [
        column for column in [
            "pair_id",
            "text_a",
            "text_b",
            "label",
            "predicted_label",
            "error_type",
            score_column,
            "reason",
        ]
        if column in errors.columns
    ]
    return errors[columns]


def run_evaluation(input_path, output_directory):
    dataframe = score_dataset(load_dataset(input_path))
    output_directory.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_directory / "scored_pairs.csv", index=False)

    split_values = set(dataframe["split"])
    if {"train", "validation", "test"} <= split_values:
        validation = dataframe[dataframe["split"] == "validation"]
        test = dataframe[dataframe["split"] == "test"]
        if validation.empty or test.empty:
            raise ValueError(
                "Validation and test splits must each contain at least one "
                "labelled pair."
            )
        metrics = compare_methods(validation, test)
        metrics.to_csv(output_directory / "metrics.csv", index=False)
        for row in metrics.itertuples(index=False):
            errors = get_misclassified_pairs(
                test,
                row.Method,
                row.Threshold,
            )
            errors.to_csv(
                output_directory / f"{row.Method}-errors.csv",
                index=False,
            )
        return metrics

    metrics = pd.DataFrame([
        evaluate_threshold(dataframe, column, 50)
        for column in SCORE_COLUMNS
    ])
    metrics.to_csv(output_directory / "metrics.csv", index=False)
    return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate lexical and semantic similarity models."
    )
    parser.add_argument(
        "--input",
        default="docs/test_pairs.csv",
        help="Path to the labelled pair CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/evaluation",
        help="Directory for scored pairs, metrics, and error CSVs.",
    )
    args = parser.parse_args()
    metrics = run_evaluation(
        Path(args.input),
        Path(args.output_dir),
    )
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
