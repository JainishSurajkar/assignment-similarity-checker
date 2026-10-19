import hashlib
import html
import re
from io import StringIO
import csv
from pathlib import Path

import pandas as pd
import streamlit as st
from docx.opc.exceptions import PackageNotFoundError
from cluster_analysis import cluster_documents
from collection_similarity import (
    compare_document_collection,
    find_similarity_groups,
)
from file_extraction import SUPPORTED_FILE_TYPES, extract_text
from lexical_semantic import compare_lexical_and_semantic
from evaluate_models import load_dataset, run_evaluation
from pypdf.errors import FileNotDecryptedError, PdfReadError
from similarity import compare_paragraphs
from upload_state import upload_mode, upload_state_changed


WORD_PATTERN = re.compile(r"(?u)\b\w\w+\b")
HIGHLIGHT_COLORS = (
    "#ffd6a5",
    "#fdffb6",
    "#caffbf",
    "#9bf6ff",
    "#bdb2ff",
    "#ffc6ff",
    "#a0c4ff",
    "#f1c0e8",
)
MAX_ASSIGNMENTS = 50
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DATASET = PROJECT_ROOT / "docs" / "test_pairs.csv"
EVALUATION_OUTPUT = PROJECT_ROOT / "docs" / "evaluation"


def shared_words(text_a, text_b):
    words_a = {
        word.casefold()
        for word in WORD_PATTERN.findall(text_a)
    }
    words_b = {
        word.casefold()
        for word in WORD_PATTERN.findall(text_b)
    }
    return words_a & words_b


def word_colors(words):
    return {
        word: HIGHLIGHT_COLORS[index % len(HIGHLIGHT_COLORS)]
        for index, word in enumerate(sorted(words))
    }


def highlight_shared_words(text, colors):
    highlighted_text = []
    last_end = 0

    for match in WORD_PATTERN.finditer(text):
        highlighted_text.append(html.escape(text[last_end:match.start()]))

        color = colors.get(match.group().casefold())
        if color:
            highlighted_text.append(
                f"<mark style='background-color: {color}; "
                "padding: 0 2px; border-radius: 3px;'>"
                f"{html.escape(match.group())}</mark>"
            )
        else:
            highlighted_text.append(html.escape(match.group()))

        last_end = match.end()

    highlighted_text.append(html.escape(text[last_end:]))
    return "".join(highlighted_text).replace("\n", "<br>")


def paragraph_results_csv(results):
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "paragraph_a",
            "paragraph_b",
            "Lexical similarity (TF-IDF cosine similarity, %)",
            "text_a",
            "text_b",
        ],
    )
    writer.writeheader()
    for result in results:
        writer.writerow({
            "paragraph_a": result["paragraph_a"],
            "paragraph_b": result["paragraph_b"],
            "Lexical similarity (TF-IDF cosine similarity, %)": round(
                result["similarity"] * 100,
                2,
            ),
            "text_a": result["text_a"],
            "text_b": result["text_b"],
        })
    return output.getvalue()


def lexical_semantic_csv(results):
    return results.rename(columns={
        "lexical_similarity": (
            "Lexical similarity (TF-IDF cosine similarity, %)"
        ),
        "semantic_similarity": "Semantic cosine score × 100",
        "difference": "Semantic minus lexical score difference",
    }).to_csv(index=False)


def sync_uploaded_file(uploaded_file, text_key, upload_key, error_key):
    if uploaded_file is None:
        st.session_state[text_key] = ""
        st.session_state[upload_key] = None
        st.session_state[error_key] = None
        clear_pair_results()
        return

    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        st.session_state[text_key] = ""
        st.session_state[upload_key] = None
        st.session_state[error_key] = (
            f"'{uploaded_file.name}' is larger than 10 MB."
        )
        clear_pair_results()
        st.session_state.input_error = (
            f"'{uploaded_file.name}' is larger than 10 MB."
        )
        return

    file_signature = hashlib.sha256(file_bytes).hexdigest()

    if st.session_state.get(upload_key) == file_signature:
        return

    clear_pair_results()
    st.session_state.input_error = None
    st.session_state[error_key] = None
    try:
        st.session_state[text_key] = extract_text(uploaded_file)
        st.session_state[upload_key] = file_signature
    except (
        UnicodeDecodeError,
        ValueError,
        OSError,
        FileNotDecryptedError,
        PdfReadError,
        PackageNotFoundError,
    ) as error:
        st.session_state[text_key] = ""
        st.session_state[upload_key] = file_signature
        st.session_state[error_key] = str(error)


def compare_assignments():
    assignment_a = st.session_state.assignment_a
    assignment_b = st.session_state.assignment_b

    if not assignment_a.strip() or not assignment_b.strip():
        st.session_state.results = None
        st.session_state.input_error = (
            "Please upload two readable assignments before comparing."
        )
        return

    st.session_state.input_error = None
    try:
        st.session_state.results = compare_paragraphs(
            assignment_a,
            assignment_b
        )
        matrix, _ = compare_document_collection({
            "Assignment A": assignment_a,
            "Assignment B": assignment_b,
        })
        st.session_state.overall_lexical_similarity = float(
            matrix.loc["Assignment A", "Assignment B"]
        )
    except ValueError as error:
        st.session_state.results = None
        st.session_state.overall_lexical_similarity = None
        st.session_state.input_error = str(error)


def collection_signature(uploaded_files):
    digest = hashlib.sha256()
    for uploaded_file in sorted(uploaded_files, key=lambda file: file.name):
        digest.update(uploaded_file.name.encode("utf-8"))
        digest.update(uploaded_file.getvalue())
    return digest.hexdigest()


def sync_upload_mode(uploaded_files):
    mode = upload_mode(len(uploaded_files))
    signature = collection_signature(uploaded_files)
    previous_mode = st.session_state.get("upload_mode")
    previous_signature = st.session_state.get("upload_signature")

    if upload_state_changed(
        previous_mode,
        previous_signature,
        mode,
        signature,
    ):
        clear_pair_results()
        clear_collection_results()
        st.session_state.upload_mode = mode
        st.session_state.upload_signature = signature


def unique_document_name(name, existing_names):
    if name not in existing_names:
        return name

    stem, separator, extension = name.rpartition(".")
    if not separator:
        stem, extension = name, ""

    index = 2
    candidate = name
    while candidate in existing_names:
        suffix = f" ({index})"
        candidate = f"{stem}{suffix}"
        if extension:
            candidate = f"{candidate}.{extension}"
        index += 1
    return candidate


def extract_documents(uploaded_files):
    documents = {}
    errors = []

    for uploaded_file in uploaded_files:
        name = unique_document_name(uploaded_file.name, documents)
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            errors.append(f"{uploaded_file.name}: file is larger than 10 MB.")
            continue
        try:
            text = extract_text(uploaded_file)
        except (
            UnicodeDecodeError,
            ValueError,
            OSError,
            FileNotDecryptedError,
            PdfReadError,
            PackageNotFoundError,
        ) as error:
            errors.append(f"{uploaded_file.name}: {error}")
            continue

        if not text.strip():
            errors.append(
                f"{uploaded_file.name}: no readable text was found."
            )
            continue

        documents[name] = text

    return documents, errors


def clear_collection_results():
    st.session_state.collection_signature = None
    st.session_state.collection_documents = {}
    st.session_state.collection_matrix = None
    st.session_state.collection_pairs = None
    st.session_state.collection_errors = []
    st.session_state.cluster_assignments = None
    st.session_state.cluster_summary = None
    st.session_state.cluster_similarity_matrix = None
    st.session_state.cluster_input_signature = None
    st.session_state.collection_detail_signature = None
    st.session_state.collection_detail_results = None


def clear_pair_results():
    st.session_state.results = None
    st.session_state.overall_lexical_similarity = None
    clear_semantic_results()


def clear_semantic_results():
    st.session_state.lexical_semantic_results = None
    st.session_state.lexical_semantic_signature = None


def render_pair_content(match, show_highlighting=False):
    assignment_col, comparison_col = st.columns(2)
    panel_style = (
        "background-color:#f8fafc !important;"
        "color:#111827 !important;"
        "border:1px solid #cbd5e1;"
        "border-radius:8px;"
        "padding:14px 16px;"
        "min-height:48px;"
        "line-height:1.55;"
        "overflow-wrap:anywhere;"
    )

    with assignment_col:
        st.markdown("**Assignment A**")
    with comparison_col:
        st.markdown("**Assignment B**")

    if show_highlighting:
        colors = word_colors(
            shared_words(match["text_a"], match["text_b"])
        )
        with assignment_col:
            st.markdown(
                (
                    f"<div class='assignment-text' style='{panel_style}'>"
                    + highlight_shared_words(match["text_a"], colors)
                    + "</div>"
                ),
                unsafe_allow_html=True
            )
        with comparison_col:
            st.markdown(
                (
                    f"<div class='assignment-text' style='{panel_style}'>"
                    + highlight_shared_words(match["text_b"], colors)
                    + "</div>"
                ),
                unsafe_allow_html=True
            )
    else:
        with assignment_col:
            st.markdown(
                f"<div class='assignment-text' style='{panel_style}'>"
                + html.escape(match["text_a"]).replace("\n", "<br>")
                + "</div>",
                unsafe_allow_html=True,
            )
        with comparison_col:
            st.markdown(
                f"<div class='assignment-text' style='{panel_style}'>"
                + html.escape(match["text_b"]).replace("\n", "<br>")
                + "</div>",
                unsafe_allow_html=True,
            )


def render_pair_result(match, show_highlighting):
    with st.expander(
        f"Paragraph A{match['paragraph_a']} - "
        f"Paragraph B{match['paragraph_b']} - "
        f"{match['similarity'] * 100:.1f}%"
    ):
        render_pair_content(match, show_highlighting)


def render_two_assignment_mode(uploaded_files):
    uploaded_a, uploaded_b = uploaded_files
    sync_uploaded_file(
        uploaded_a,
        "assignment_a",
        "assignment_a_upload_signature",
        "assignment_a_error",
    )
    sync_uploaded_file(
        uploaded_b,
        "assignment_b",
        "assignment_b_upload_signature",
        "assignment_b_error",
    )

    both_uploaded = bool(
        st.session_state.assignment_a.strip()
        and st.session_state.assignment_b.strip()
    )
    if not both_uploaded:
        errors = [
            st.session_state.get("assignment_a_error"),
            st.session_state.get("assignment_b_error"),
        ]
        for error in errors:
            if error:
                st.error(error)
        return

    st.markdown("### Pair Comparison")
    st.caption(
        f"Assignment A: {uploaded_a.name} · "
        f"{len(st.session_state.assignment_a):,} extracted characters\n\n"
        f"Assignment B: {uploaded_b.name} · "
        f"{len(st.session_state.assignment_b):,} extracted characters"
    )

    if st.button("Compare assignments", type="primary", key="compare_two"):
        with st.spinner("Comparing assignment paragraphs..."):
            compare_assignments()

    threshold = st.slider(
        "Minimum score to display (%)",
        min_value=0,
        max_value=100,
        key="similarity_threshold",
    )
    show_highlighting = st.checkbox(
        "Show shared-word highlighting",
        key="show_shared_word_highlighting",
        help=(
            "Highlights common individual words. This does not identify "
            "exactly copied phrases or prove plagiarism."
        ),
    )

    if st.session_state.results is None:
        if st.session_state.input_error:
            st.error(st.session_state.input_error)
        else:
            st.info("Click **Compare assignments** to calculate the comparison.")
        return

    matches = [
        result for result in st.session_state.results
        if result["similarity"] * 100 >= threshold
    ]
    st.subheader("Results · Similar Paragraphs")
    st.warning(
        "Similarity scores identify overlapping or related content; they do "
        "not prove plagiarism. Common terminology, assignment instructions, "
        "quotations, and legitimate citations may produce high similarity. "
        "Review the highlighted passages and their context before drawing "
        "conclusions."
    )
    st.caption(
        f"Showing {len(matches)} of {len(st.session_state.results)} "
        f"paragraph pairs with a TF-IDF cosine similarity of at least "
        f"{threshold}%."
    )
    summary_columns = st.columns(3)
    summary_columns[0].metric("Assignments", 2)
    summary_columns[1].metric(
        "Pairs compared",
        f"{len(st.session_state.results):,}",
    )
    summary_columns[2].metric("Matches shown", len(matches))
    score_columns = st.columns(2)
    score_columns[0].metric(
        "Lexical similarity (TF-IDF cosine similarity, %)",
        f"{st.session_state.overall_lexical_similarity:.1f}%",
    )
    score_columns[1].metric(
        "Highest paragraph similarity",
        f"{max(result['similarity'] for result in st.session_state.results) * 100:.1f}%",
    )
    if st.session_state.results:
        st.download_button(
            "Download paragraph results (CSV)",
            data=paragraph_results_csv(st.session_state.results),
            file_name="paragraph-similarity-results.csv",
            mime="text/csv",
            key="download_two_results",
        )
    if not matches:
        st.info("No paragraph pairs meet the selected score threshold.")
    for match in matches:
        render_pair_result(match, show_highlighting)

def render_collection_mode(uploaded_files):
    signature = collection_signature(uploaded_files)
    if signature != st.session_state.collection_signature:
        documents, errors = extract_documents(uploaded_files)
        st.session_state.collection_signature = signature
        st.session_state.collection_documents = documents
        st.session_state.collection_errors = errors
        st.session_state.collection_matrix = None
        st.session_state.collection_pairs = None
        st.session_state.cluster_assignments = None
        st.session_state.cluster_summary = None
        st.session_state.cluster_similarity_matrix = None
        st.session_state.cluster_input_signature = None

    for error in st.session_state.collection_errors:
        st.warning(error)

    documents = st.session_state.collection_documents
    if len(documents) < 2:
        st.info("At least two valid assignments are required for comparison.")
        return
    st.markdown("### Collection Analysis")
    st.caption(
        f"{len(documents)} readable assignments loaded. Collection analysis "
        "compares complete-document TF-IDF scores first; paragraph details "
        "are calculated only for one selected pair."
    )
    if st.button("Compare assignment collection", type="primary"):
        with st.spinner("Building the similarity matrix..."):
            try:
                matrix, pairs = compare_document_collection(documents)
            except ValueError as error:
                st.error(str(error))
                st.session_state.collection_matrix = None
                st.session_state.collection_pairs = None
            else:
                st.session_state.collection_matrix = matrix
                st.session_state.collection_pairs = pairs

    matrix = st.session_state.collection_matrix
    pairs = st.session_state.collection_pairs
    if matrix is None or pairs is None:
        return

    threshold = st.slider(
        "Minimum similarity for displayed pairs (%)",
        min_value=0,
        max_value=100,
        value=20,
        key="collection_threshold",
    )
    above_threshold = pairs[pairs["similarity"] >= threshold]
    metrics = st.columns(3)
    metrics[0].metric("Assignments", len(matrix))
    metrics[1].metric("Unique pairs", len(pairs))
    metrics[2].metric("Pairs above threshold", len(above_threshold))
    st.warning(
        "Similarity scores identify overlapping or related content; they do "
        "not prove plagiarism. Common terminology, assignment instructions, "
        "quotations, and legitimate citations may produce high similarity. "
        "Review the highlighted passages and their context before drawing "
        "conclusions."
    )
    st.download_button(
        "Download collection results (CSV)",
        data=pairs.to_csv(index=False),
        file_name="assignment-similarity-results.csv",
        mime="text/csv",
        key="download_collection_results",
    )

    st.subheader("Results · Similarity Matrix")
    st.dataframe(
        matrix.style.format("{:.1f}%").background_gradient(
            cmap="RdYlGn",
            vmin=0,
            vmax=100,
        ),
        width="stretch",
    )

    show_highlighting = st.checkbox(
        "Show shared-word highlighting in paragraph details",
        key="collection_show_shared_word_highlighting",
        help=(
            "Highlights common individual words, not exact matching phrases "
            "and not proof of plagiarism."
        ),
    )
    st.subheader("Most similar assignment pairs")
    if above_threshold.empty:
        st.info("No assignment pairs meet the selected threshold.")
    else:
        ranked_options = above_threshold.head(100)
        pair_labels = [
            f"{pair.assignment_a} ↔ {pair.assignment_b} — "
            f"{pair.similarity:.1f}%"
            for pair in ranked_options.itertuples(index=False)
        ]
        selected_label = st.selectbox(
            "Select one assignment pair for paragraph inspection",
            pair_labels,
            key="selected_collection_pair",
        )
        selected_index = pair_labels.index(selected_label)
        pair = ranked_options.iloc[selected_index]
        st.caption(
            f"Showing the top {len(ranked_options)} ranked pairs for selection. "
            "Detailed paragraph comparison is calculated only for the "
            "selected pair."
        )
        detail_signature = (
            f"{st.session_state.collection_signature}:"
            f"{pair['assignment_a']}:{pair['assignment_b']}"
        )
        if detail_signature != st.session_state.collection_detail_signature:
            try:
                st.session_state.collection_detail_results = (
                    compare_paragraphs(
                        documents[pair["assignment_a"]],
                        documents[pair["assignment_b"]],
                    )
                )
                st.session_state.collection_detail_signature = detail_signature
            except ValueError as error:
                st.session_state.collection_detail_results = None
                st.session_state.collection_detail_signature = detail_signature
                st.warning(f"Paragraph comparison is unavailable: {error}")

        paragraph_results = st.session_state.collection_detail_results
        if paragraph_results is not None:
            for result in paragraph_results[:10]:
                with st.expander(
                    f"Paragraph {result['paragraph_a']} ↔ "
                    f"{result['paragraph_b']} — "
                    f"{result['similarity'] * 100:.1f}%"
                ):
                    render_pair_content(
                        result,
                        show_highlighting=show_highlighting,
                    )

def render_connected_groups_tab():
    st.caption(
        "Connected components use the selected similarity threshold. "
        "Assignments can be linked indirectly, so not every pair in a group "
        "must exceed the threshold."
    )
    matrix = st.session_state.collection_matrix
    if matrix is None:
        st.info(
            "Upload at least three assignments and run Collection Analysis "
            "first."
        )
        return
    threshold = st.slider(
        "Group connection threshold (%)",
        1,
        100,
        50,
        key="groups_tab_threshold",
    )
    groups = find_similarity_groups(matrix, threshold)
    if not groups:
        st.info("No connected groups meet the selected threshold.")
        return
    for index, group in enumerate(groups, 1):
        st.subheader(f"Group {index} · {len(group)} assignments")
        st.dataframe(
            pd.DataFrame({"Assignment": group}),
            hide_index=True,
            width="stretch",
        )


def render_clustering_tab():
    st.caption(
        "Average-linkage hierarchical clustering organizes documents by "
        "similarity. It does not guarantee every pair inside a cluster "
        "exceeds the selected setting."
    )
    documents = st.session_state.collection_documents
    if len(documents) < 2:
        st.info(
            "Upload at least three assignments and run Collection Analysis "
            "first."
        )
        return
    threshold = st.slider(
        "Clustering similarity setting (%)",
        10,
        90,
        55,
        step=5,
        key="clustering_tab_threshold",
    )
    if st.button("Discover or refresh clusters", type="primary"):
        with st.spinner("Building hierarchical clusters..."):
            try:
                assignments, summary, matrix = cluster_documents(
                    documents,
                    similarity_threshold=threshold,
                )
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state.cluster_assignments = assignments
                st.session_state.cluster_summary = summary
                st.session_state.cluster_similarity_matrix = matrix
                st.session_state.cluster_input_signature = (
                    st.session_state.collection_signature
                )
    if st.session_state.cluster_input_signature != (
        st.session_state.collection_signature
    ):
        st.info("Run clustering to generate results for the current uploads.")
        return
    if st.session_state.cluster_summary is None:
        st.info("Click **Discover or refresh clusters** to begin.")
        return
    st.subheader("Cluster summaries")
    st.dataframe(
        st.session_state.cluster_summary,
        hide_index=True,
        width="stretch",
    )
    st.subheader("Assignments by cluster")
    st.dataframe(
        st.session_state.cluster_assignments,
        hide_index=True,
        width="stretch",
    )


def render_evaluation_tab():
    st.caption(
        "This is an offline benchmark, separate from uploaded assignments. "
        "Thresholds are selected on validation data and final metrics are "
        "calculated only on the held-out test split."
    )
    try:
        dataset = load_dataset(EVALUATION_DATASET)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Evaluation dataset is invalid: {error}")
        return
    split_counts = dataset["split"].value_counts()
    st.dataframe(
        split_counts.rename("Pairs").rename_axis("Split").reset_index(),
        hide_index=True,
        width="stretch",
    )
    st.warning(
        "The starter labels are illustrative and are not a reliable "
        "production-accuracy claim. Replace them with genuinely reviewed "
        "domain-specific pairs before presenting performance metrics."
    )
    if st.button("Run held-out model evaluation", type="primary"):
        with st.spinner("Scoring the labelled dataset..."):
            try:
                metrics = run_evaluation(
                    EVALUATION_DATASET,
                    EVALUATION_OUTPUT,
                )
            except (OSError, ValueError, RuntimeError) as error:
                st.session_state.evaluation_metrics = None
                st.session_state.evaluation_semantic_error = None
                st.error(f"Evaluation could not be completed: {error}")
            else:
                st.session_state.evaluation_metrics = metrics
                st.session_state.evaluation_semantic_error = (
                    metrics.attrs.get("semantic_error")
                )
    metrics = st.session_state.evaluation_metrics
    if metrics is None:
        st.info("Run the evaluation to display held-out metrics.")
        return
    st.subheader("Held-out test metrics")
    if st.session_state.get("evaluation_semantic_error"):
        st.warning(
            "Lexical evaluation completed, but semantic evaluation was "
            "skipped: "
            + st.session_state.evaluation_semantic_error
        )
    st.dataframe(metrics, hide_index=True, width="stretch")
    st.caption(
        "False-positive and false-negative CSV reports are written to "
        "docs/evaluation/."
    )


def render_semantic_tab(uploaded_files):
    if len(uploaded_files) != 2:
        st.info("Upload exactly two readable assignments first.")
        return
    if not (
        st.session_state.assignment_a.strip()
        and st.session_state.assignment_b.strip()
    ):
        st.info("Both uploaded assignments must contain readable text.")
        return
    st.info(
        "**Lexical similarity (TF-IDF cosine similarity, %)** measures "
        "weighted word overlap. **Semantic cosine score × 100** estimates "
        "meaning-related similarity from sentence embeddings. Neither score "
        "is a plagiarism probability."
    )
    signature = collection_signature(uploaded_files)
    if st.button(
        "Run lexical and semantic comparison",
        type="primary",
        key="semantic_tab_compare",
    ):
        with st.spinner("Loading the embedding model and scoring paragraphs..."):
            try:
                st.session_state.lexical_semantic_results = (
                    compare_lexical_and_semantic(
                        st.session_state.assignment_a,
                        st.session_state.assignment_b,
                    )
                )
                st.session_state.lexical_semantic_signature = signature
            except (ValueError, OSError, RuntimeError) as error:
                st.session_state.lexical_semantic_results = None
                st.error(f"Semantic comparison failed: {error}")
    results = st.session_state.lexical_semantic_results
    if results is None or st.session_state.lexical_semantic_signature != signature:
        st.info("Run the comparison to display semantic results.")
        return
    lexical_threshold = st.slider(
        "Minimum lexical similarity (TF-IDF cosine similarity, %)",
        0,
        100,
        20,
        key="semantic_tab_lexical_threshold",
    )
    semantic_threshold = st.slider(
        "Minimum semantic cosine score × 100",
        -100,
        100,
        50,
        key="semantic_tab_threshold",
    )
    matches = results[
        (results["lexical_similarity"] >= lexical_threshold)
        | (results["semantic_similarity"] >= semantic_threshold)
    ]
    st.caption(f"Showing {len(matches)} of {len(results)} paragraph pairs.")
    st.download_button(
        "Download lexical and semantic results (CSV)",
        data=lexical_semantic_csv(results),
        file_name="lexical-semantic-results.csv",
        mime="text/csv",
        key="semantic_tab_download",
    )
    for result in matches.itertuples(index=False):
        with st.expander(
            f"Paragraph A{result.paragraph_a} ↔ B{result.paragraph_b} · "
            f"Lexical {result.lexical_similarity:.1f}% · "
            f"Semantic {result.semantic_similarity:.1f}%"
        ):
            st.write(
                f"Semantic minus lexical score difference: "
                f"{result.difference:+.1f}"
            )
            render_pair_content(
                {"text_a": result.text_a, "text_b": result.text_b},
                show_highlighting=False,
            )


st.set_page_config(
    page_title="Assignment Similarity Checker",
    page_icon="📚",
    layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1200px; padding-top: 2rem; padding-bottom: 3rem;}
    h1 {letter-spacing: -0.02em;}
    h2, h3 {margin-top: 1.4rem;}
    [data-testid="stMetric"] {background: #f7f9fc; border: 1px solid #e4e9f0;
        padding: 0.8rem; border-radius: 0.5rem;}
    [data-testid="stMetric"] [data-testid="stMetricLabel"],
    [data-testid="stMetric"] [data-testid="stMetricLabel"] *,
    [data-testid="stMetric"] [data-testid="stMetricValue"],
    [data-testid="stMetric"] [data-testid="stMetricValue"] *,
    [data-testid="stMetric"] [data-testid="stMetricDelta"],
    [data-testid="stMetric"] [data-testid="stMetricDelta"] * {
        color: #111827 !important;
    }
    .viva-subtitle {color: #52606d; font-size: 1.08rem; margin-top: -0.6rem;}
    .assignment-text {
        background: #ffffff !important;
        color: #1f2937 !important;
        border: 1px solid #d7dee8;
        border-radius: 0.5rem;
        padding: 0.9rem 1rem;
        min-height: 3rem;
        line-height: 1.55;
        overflow-wrap: anywhere;
    }
    .assignment-text p,
    .assignment-text span,
    .assignment-text div {
        background: transparent !important;
        color: #1f2937 !important;
    }
    .assignment-text mark {
        color: #1f2937 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Assignment Similarity Checker")
st.markdown(
    '<p class="viva-subtitle">Compare assignment wording and semantic '
    "similarity to identify content that deserves human review.</p>",
    unsafe_allow_html=True,
)
with st.expander("How it works", expanded=False):
    st.write(
        "Upload exactly two assignments for paragraph-level comparison, or "
        "three to fifty assignments for collection analysis. TF-IDF measures "
        "weighted word overlap; optional sentence embeddings estimate related "
        "meaning. Thresholds filter results only and never determine whether "
        "plagiarism occurred."
    )
st.markdown("### Upload assignments")
st.caption(
    "Use exactly 2 files for Pair Comparison, or 3–50 files for Collection "
    "Analysis. Supported formats: TXT, PDF, and DOCX. Each file is limited "
    "to 10 MB."
)

for key, default in (
    ("assignment_a", ""),
    ("assignment_b", ""),
    ("assignment_a_upload_signature", None),
    ("assignment_b_upload_signature", None),
    ("assignment_a_error", None),
    ("assignment_b_error", None),
    ("results", None),
    ("overall_lexical_similarity", None),
    ("similarity_threshold", 20),
    ("input_error", None),
    ("collection_signature", None),
    ("collection_documents", {}),
    ("collection_matrix", None),
    ("collection_pairs", None),
    ("collection_errors", []),
    ("cluster_assignments", None),
    ("cluster_summary", None),
    ("cluster_similarity_matrix", None),
    ("cluster_input_signature", None),
    ("collection_detail_signature", None),
    ("collection_detail_results", None),
    ("lexical_semantic_results", None),
    ("lexical_semantic_signature", None),
    ("upload_mode", None),
    ("upload_signature", None),
    ("evaluation_metrics", None),
    ("evaluation_semantic_error", None),
):
    if key not in st.session_state:
        st.session_state[key] = default

uploaded_files = st.file_uploader(
    "Upload assignments",
    type=SUPPORTED_FILE_TYPES,
    accept_multiple_files=True,
    key="assignment_uploads",
    help=(
        "Upload exactly 2 files for paragraph comparison, or 3–50 files "
        "for collection analysis. Supported formats: TXT, PDF, and DOCX."
    ),
)

if len(uploaded_files) > MAX_ASSIGNMENTS:
    st.error("Please upload no more than 50 assignments.")
else:
    sync_upload_mode(uploaded_files)
    pair_tab, collection_tab, groups_tab, clustering_tab, semantic_tab, evaluation_tab = st.tabs([
        "Pair Comparison",
        "Collection Analysis",
        "Connected Groups",
        "Hierarchical Clustering",
        "Lexical vs Semantic",
        "Model Evaluation",
    ])
    with pair_tab:
        if len(uploaded_files) == 2:
            render_two_assignment_mode(uploaded_files)
        else:
            st.info("Upload exactly two files to use Pair Comparison.")
    with collection_tab:
        if len(uploaded_files) >= 3:
            render_collection_mode(uploaded_files)
        else:
            st.info("Upload three to fifty files to use Collection Analysis.")
    with groups_tab:
        render_connected_groups_tab()
    with clustering_tab:
        render_clustering_tab()
    with semantic_tab:
        render_semantic_tab(uploaded_files)
    with evaluation_tab:
        render_evaluation_tab()
