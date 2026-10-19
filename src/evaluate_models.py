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

from lexical_semantic import SemanticDependencyError, load_semantic_model


REQUIRED_COLUMNS = ["pair_id", "text_a", "text_b", "label"]
SCORE_COLUMNS = ["lexical_score", "semantic_score"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "docs" / "test_pairs.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "evaluation"


def load_dataset(path=DEFAULT_DATASET):
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

    scored = dataframe.copy()
    scored["lexical_score"] = lexical_scores
    try:
        model = load_semantic_model()
        embeddings = np.asarray(model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ))
    except (SemanticDependencyError, OSError, RuntimeError) as error:
        scored.attrs["semantic_error"] = str(error)
        scored["semantic_score"] = np.nan
    else:
        scored["semantic_score"] = np.sum(
            embeddings[:count] * embeddings[count:],
            axis=1,
        ) * 100
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
    dataframe = load_dataset(input_path)
    required_splits = {"train", "validation", "test"}
    if set(dataframe["split"]) != required_splits:
        raise ValueError(
            "Held-out evaluation requires exactly train, validation, and "
            "test splits. No all-data metrics were generated."
        )
    dataframe = score_dataset(dataframe)
    output_directory.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_directory / "scored_pairs.csv", index=False)

    validation = dataframe[dataframe["split"] == "validation"]
    test = dataframe[dataframe["split"] == "test"]
    if validation.empty or test.empty:
        raise ValueError(
            "Validation and test splits must each contain at least one "
            "labelled pair."
        )
    available_scores = [
        column for column in SCORE_COLUMNS
        if not validation[column].isna().all()
    ]
    if not available_scores:
        raise ValueError(
            "No evaluation model produced usable scores. Install semantic "
            "dependencies or check the evaluation inputs."
        )
    metrics = []
    for score_column in available_scores:
        threshold = select_threshold(validation, score_column)
        metrics.append(evaluate_threshold(test, score_column, threshold))
    metrics = pd.DataFrame(metrics)
    if dataframe.attrs.get("semantic_error"):
        metrics.attrs["semantic_error"] = dataframe.attrs["semantic_error"]
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


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate lexical and semantic similarity models."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_DATASET),
        help="Path to the labelled pair CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
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
