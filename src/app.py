import hashlib
import html
import re

import streamlit as st
from docx.opc.exceptions import PackageNotFoundError
from file_extraction import SUPPORTED_FILE_TYPES, extract_text
from pypdf.errors import PdfReadError
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


def sync_uploaded_file(uploaded_file, text_key, upload_key):
    if uploaded_file is None:
        st.session_state[text_key] = ""
        st.session_state[upload_key] = None
        return

    file_bytes = uploaded_file.getvalue()
    file_signature = hashlib.sha256(file_bytes).hexdigest()

    if st.session_state.get(upload_key) == file_signature:
        return

    try:
        st.session_state[text_key] = extract_text(uploaded_file)
        st.session_state[upload_key] = file_signature
        st.session_state.input_error = None
    except (
        UnicodeDecodeError,
        ValueError,
        OSError,
        PdfReadError,
        PackageNotFoundError,
    ) as error:
        st.session_state[text_key] = ""
        st.session_state[upload_key] = file_signature
        st.session_state.input_error = str(error)


def compare_on_threshold_change():
    assignment_a = st.session_state.assignment_a
    assignment_b = st.session_state.assignment_b

    if not assignment_a.strip() or not assignment_b.strip():
        st.session_state.results = None
        st.session_state.input_error = (
            "Please provide both assignments before adjusting the slider."
        )
        return

    st.session_state.input_error = None
    st.session_state.results = compare_paragraphs(
        assignment_a,
        assignment_b
    )


st.set_page_config(
    page_title="Assignment Similarity Checker",
    page_icon="📄",
    layout="wide"
)

st.title("Assignment Similarity and Citation Checker")

st.write(
    "Compare two assignments and identify passages "
    "that may require closer review."
)

if "results" not in st.session_state:
    st.session_state.results = None
if "similarity_threshold" not in st.session_state:
    st.session_state.similarity_threshold = 20
if "input_error" not in st.session_state:
    st.session_state.input_error = None


col1, col2 = st.columns(2)

with col1:
    uploaded_a = st.file_uploader(
        "Upload Assignment A",
        type=SUPPORTED_FILE_TYPES,
        key="uploaded_assignment_a",
        help="Supported formats: TXT, PDF, and DOCX.",
    )
    sync_uploaded_file(
        uploaded_a,
        "assignment_a",
        "assignment_a_upload_signature",
    )

with col2:
    uploaded_b = st.file_uploader(
        "Upload Assignment B",
        type=SUPPORTED_FILE_TYPES,
        key="uploaded_assignment_b",
        help="Supported formats: TXT, PDF, and DOCX.",
    )
    sync_uploaded_file(
        uploaded_b,
        "assignment_b",
        "assignment_b_upload_signature",
    )

both_assignments_uploaded = bool(
    uploaded_a
    and uploaded_b
    and st.session_state.assignment_a.strip()
    and st.session_state.assignment_b.strip()
)

if both_assignments_uploaded:
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)

    threshold = st.slider(
        "Minimum similarity to display",
        min_value=0,
        max_value=100,
        key="similarity_threshold",
        on_change=compare_on_threshold_change
    )

    if st.session_state.results is not None:
        st.subheader("Similar Paragraphs")

        matches = [
            result for result in st.session_state.results
            if result["similarity"] * 100 >= threshold
        ]

        st.caption(
            f"Showing {len(matches)} of {len(st.session_state.results)} "
            f"paragraph pairs with similarity of at least {threshold}%."
        )

        if not matches:
            st.info("No paragraph pairs meet this threshold.")

        for match in matches:
            with st.expander(
                f"Paragraph A{match['paragraph_a']} - "
                f"Paragraph B{match['paragraph_b']} - "
                f"{match['similarity'] * 100:.1f}%"
            ):
                assignment_col, comparison_col = st.columns(2)

                with assignment_col:
                    st.markdown("**Assignment A**")
                with comparison_col:
                    st.markdown("**Assignment B**")

                if threshold < 50:
                    common_words = shared_words(
                        match["text_a"],
                        match["text_b"]
                    )
                    colors = word_colors(common_words)
                    with assignment_col:
                        st.markdown(
                            highlight_shared_words(
                                match["text_a"],
                                colors
                            ),
                            unsafe_allow_html=True
                        )
                    with comparison_col:
                        st.markdown(
                            highlight_shared_words(
                                match["text_b"],
                                colors
                            ),
                            unsafe_allow_html=True
                        )
                else:
                    with assignment_col:
                        st.write(match["text_a"])
                    with comparison_col:
                        st.write(match["text_b"])

elif st.session_state.input_error:
    st.error(st.session_state.input_error)
