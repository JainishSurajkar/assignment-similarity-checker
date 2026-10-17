import streamlit as st
from similarity import compare_paragraphs


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


col1, col2 = st.columns(2)

with col1:
    assignment_a = st.text_area(
        "Assignment A",
        height=250,
        placeholder="Paste the first assignment here...",
        key="assignment_a"
    )

with col2:
    assignment_b = st.text_area(
        "Assignment B",
        height=250,
        placeholder="Paste the second assignment here...",
        key="assignment_b"
    )


if "results" not in st.session_state:
    st.session_state.results = None
if "similarity_threshold" not in st.session_state:
    st.session_state.similarity_threshold = 20
if "input_error" not in st.session_state:
    st.session_state.input_error = None

st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)

threshold = st.slider(
    "Minimum similarity to display",
    min_value=0,
    max_value=100,
    key="similarity_threshold",
    on_change=compare_on_threshold_change
)

if st.session_state.input_error:
    st.error(st.session_state.input_error)

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
            st.markdown("**Assignment A**")
            st.write(match["text_a"])

            st.markdown("**Assignment B**")
            st.write(match["text_b"])
