from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def split_paragraph(text):
    return [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

def compare_paragraphs(text_a, text_b):
    paragraph_a = split_paragraph(text_a)
    paragraph_b = split_paragraph(text_b)

    if not paragraph_a or not paragraph_b:
        return []

    all_paragraphs = paragraph_a + paragraph_b

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(all_paragraphs)

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




# assignment_a = """
# Machine learning helps computers learn from data.
# It is used in healthcare and education.
# """

# assignment_b = """
# Computers learn patterns from data using machine learning.
# It is useful in healthcare and education.
# """

# documents = [assignment_a, assignment_b]

# vectorizer = TfidfVectorizer()
# tfidf_matrix = vectorizer.fit_transform(documents)

# score = cosine_similarity(
#     tfidf_matrix[0:1],
#     tfidf_matrix[1:2]
# )[0][0]

# print(f"Similarity: {score * 100:.2f}%")
