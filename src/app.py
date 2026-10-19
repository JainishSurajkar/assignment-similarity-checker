import hashlib
import html
import re
from io import StringIO
import csv

import streamlit as st
from docx.opc.exceptions import PackageNotFoundError
from cluster_analysis import cluster_documents
from collection_similarity import (
    compare_document_collection,
    find_similarity_groups,
)
from file_extraction import SUPPORTED_FILE_TYPES, extract_text
from lexical_semantic import (
    SemanticDependencyError,
    compare_lexical_and_semantic,
)
from pypdf.errors import FileNotDecryptedError, PdfReadError
from similarity import compare_paragraphs


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
            "similarity_percent",
            "text_a",
            "text_b",
        ],
    )
    writer.writeheader()
    for result in results:
        writer.writerow({
            "paragraph_a": result["paragraph_a"],
            "paragraph_b": result["paragraph_b"],
            "similarity_percent": round(result["similarity"] * 100, 2),
            "text_a": result["text_a"],
            "text_b": result["text_b"],
        })
    return output.getvalue()


def lexical_semantic_csv(results):
    return results.to_csv(index=False)


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
    except ValueError as error:
        st.session_state.results = None
        st.session_state.input_error = str(error)


def collection_signature(uploaded_files):
    digest = hashlib.sha256()
    for uploaded_file in sorted(uploaded_files, key=lambda file: file.name):
        digest.update(uploaded_file.name.encode("utf-8"))
        digest.update(uploaded_file.getvalue())
    return digest.hexdigest()


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


def clear_pair_results():
    st.session_state.results = None
    clear_semantic_results()


def clear_semantic_results():
    st.session_state.lexical_semantic_results = None
    st.session_state.lexical_semantic_signature = None


def render_pair_content(match, show_highlighting=False):
    assignment_col, comparison_col = st.columns(2)

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
                highlight_shared_words(match["text_a"], colors),
                unsafe_allow_html=True
            )
        with comparison_col:
            st.markdown(
                highlight_shared_words(match["text_b"], colors),
                unsafe_allow_html=True
            )
    else:
        with assignment_col:
            st.write(match["text_a"])
        with comparison_col:
            st.write(match["text_b"])


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
    st.subheader("Similar Paragraphs")
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

    st.subheader("Lexical vs semantic comparison")
    st.write(
        "TF-IDF measures shared wording, while sentence embeddings estimate "
        "meaning-related similarity. The semantic value is a scaled cosine "
        "score, not a probability of plagiarism. The first run downloads the "
        "embedding model and may take longer."
    )
    semantic_signature = collection_signature(uploaded_files)
    if st.button(
        "Compare lexical and semantic similarity",
        type="secondary",
        key="compare_semantic",
    ):
        with st.spinner("Loading the semantic model and comparing paragraphs..."):
            try:
                st.session_state.lexical_semantic_results = (
                    compare_lexical_and_semantic(
                        st.session_state.assignment_a,
                        st.session_state.assignment_b,
                    )
                )
                st.session_state.lexical_semantic_signature = semantic_signature
            except (
                ValueError,
                OSError,
                SemanticDependencyError,
                RuntimeError,
            ) as error:
                st.session_state.lexical_semantic_results = None
                st.error(f"Semantic comparison failed: {error}")

    semantic_results = st.session_state.lexical_semantic_results
    if (
        semantic_results is not None
        and st.session_state.lexical_semantic_signature == semantic_signature
    ):
        lexical_threshold = st.slider(
            "Minimum lexical similarity (%)",
            min_value=0,
            max_value=100,
            value=20,
            key="lexical_threshold",
        )
        semantic_threshold = st.slider(
            "Minimum scaled semantic cosine score (%)",
            min_value=-100,
            max_value=100,
            value=50,
            key="semantic_threshold",
        )
        semantic_matches = semantic_results[
            (semantic_results["lexical_similarity"] >= lexical_threshold)
            | (semantic_results["semantic_similarity"] >= semantic_threshold)
        ]
        st.caption(
            f"Showing {len(semantic_matches)} of {len(semantic_results)} "
            "paragraph pairs meeting at least one selected threshold."
        )
        st.download_button(
            "Download lexical/semantic results (CSV)",
            data=lexical_semantic_csv(semantic_results),
            file_name="lexical-semantic-results.csv",
            mime="text/csv",
            key="download_semantic_results",
        )
        for result in semantic_matches.itertuples(index=False):
            with st.expander(
                f"Paragraph A{result.paragraph_a} ↔ "
                f"B{result.paragraph_b} — "
                f"lexical {result.lexical_similarity:.1f}% · "
                f"semantic {result.semantic_similarity:.1f}%"
            ):
                st.write(
                    f"Semantic minus lexical difference: "
                    f"{result.difference:+.1f} percentage points."
                )
                render_pair_content(
                    {
                        "text_a": result.text_a,
                        "text_b": result.text_b,
                    },
                    show_highlighting=show_highlighting,
                )
    elif semantic_results is not None:
        st.info("The uploaded assignments changed. Run the semantic comparison again.")


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
    if st.button("Compare assignments", type="primary"):
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
    st.download_button(
        "Download collection results (CSV)",
        data=pairs.to_csv(index=False),
        file_name="assignment-similarity-results.csv",
        mime="text/csv",
        key="download_collection_results",
    )

    st.subheader("Similarity matrix")
    st.dataframe(
        matrix.style.format("{:.1f}%").background_gradient(
            cmap="RdYlGn",
            vmin=0,
            vmax=100,
        ),
        width="stretch",
    )

    st.subheader("Groups of similar assignments")
    group_threshold = st.slider(
        "Minimum similarity for a group connection (%)",
        min_value=1,
        max_value=100,
        value=50,
        key="group_threshold",
    )
    show_highlighting = st.checkbox(
        "Show shared-word highlighting in paragraph details",
        key="collection_show_shared_word_highlighting",
        help=(
            "Highlights common individual words, not exact matching phrases "
            "and not proof of plagiarism."
        ),
    )
    groups = find_similarity_groups(matrix, group_threshold)
    if not groups:
        st.info("No groups of two or more assignments meet this threshold.")
    for index, group in enumerate(groups, start=1):
        with st.expander(f"Group {index} — {len(group)} assignments"):
            for document in group:
                st.write(f"- {document}")

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
        try:
            paragraph_results = compare_paragraphs(
                documents[pair["assignment_a"]],
                documents[pair["assignment_b"]],
            )
        except ValueError as error:
            st.warning(f"Paragraph comparison is unavailable: {error}")
        else:
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

    st.subheader("Clustering and pattern discovery")
    st.write(
        "Group assignments with similar text patterns using hierarchical "
        "clustering. Cluster membership is an investigation aid, not proof "
        "of plagiarism."
    )
    cluster_threshold = st.slider(
        "Clustering similarity setting (%)",
        min_value=10,
        max_value=90,
        value=55,
        step=5,
        help=(
            "A higher setting generally creates smaller, stricter groups. "
            "This is an average-linkage distance setting and is not a "
            "guaranteed minimum for every pair in a cluster."
        ),
        key="cluster_threshold",
    )
    if st.button("Discover assignment clusters", type="primary"):
        try:
            assignments, summary, similarity_matrix = cluster_documents(
                documents,
                similarity_threshold=cluster_threshold,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state.cluster_assignments = assignments
            st.session_state.cluster_summary = summary
            st.session_state.cluster_similarity_matrix = similarity_matrix
            st.session_state.cluster_input_signature = (
                st.session_state.collection_signature
            )

    if (
        st.session_state.cluster_summary is not None
        and st.session_state.cluster_input_signature
        == st.session_state.collection_signature
    ):
        st.subheader("Cluster overview")
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
    elif st.session_state.cluster_summary is not None:
        st.info("The uploaded assignments changed. Run clustering again.")


st.set_page_config(
    page_title="Assignment Similarity Checker",
    page_icon="📚",
    layout="wide"
)

st.title("Assignment Similarity Checker")
st.write(
    "Compare two assignments or analyze a collection of assignments. "
    "Similarity scores are not a probability of plagiarism."
)

for key, default in (
    ("assignment_a", ""),
    ("assignment_b", ""),
    ("assignment_a_upload_signature", None),
    ("assignment_b_upload_signature", None),
    ("assignment_a_error", None),
    ("assignment_b_error", None),
    ("results", None),
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
    ("lexical_semantic_results", None),
    ("lexical_semantic_signature", None),
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
    clear_pair_results()
    clear_collection_results()
elif len(uploaded_files) < 2:
    clear_pair_results()
    clear_collection_results()
    st.info(
        "Upload exactly 2 files for a detailed comparison, or at least 3 "
        "files to analyze a collection."
    )
elif len(uploaded_files) == 2:
    render_two_assignment_mode(uploaded_files)
else:
    render_collection_mode(uploaded_files)
