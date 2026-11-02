from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize_text(text):
    """Normalize line endings and whitespace without joining paragraphs."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in normalized.split("\n")]
    return "\n".join(lines)


def split_paragraph(text):
    return [
        normalize_text(paragraph).strip()
        for paragraph in normalize_text(text).split("\n\n")
        if paragraph.strip()
    ]


def compare_paragraphs(text_a, text_b):
    paragraph_a = split_paragraph(text_a)
    paragraph_b = split_paragraph(text_b)

    if not paragraph_a or not paragraph_b:
        return []

    all_paragraphs = paragraph_a + paragraph_b

    vectorizer = TfidfVectorizer()
    try:
        vectors = vectorizer.fit_transform(all_paragraphs)
    except ValueError as error:
        raise ValueError(
            "The assignments do not contain enough readable words "
            "to calculate similarity."
        ) from error

    count_a = len(paragraph_a)
    similarity_matrix = cosine_similarity(
        vectors[:count_a],
        vectors[count_a:]
    )

    results = []

    for i in range(len(paragraph_a)):
        for j in range(len(paragraph_b)):
            results.append({
                "paragraph_a": i + 1,
                "paragraph_b": j + 1,
                "text_a": paragraph_a[i],
                "text_b": paragraph_b[j],
                "similarity": float(similarity_matrix[i, j])
            })

    results.sort(
        key = lambda result : result["similarity"],
        reverse = True
    )

    return results