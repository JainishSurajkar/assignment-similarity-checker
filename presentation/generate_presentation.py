from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "presentation" / "Assignment_Similarity_Checker.pptx"

SLIDES = [
    ("Assignment Similarity Checker", ["GTU Data Mining Techniques project", "A human-review aid for locating similar passages"]),
    ("Problem and scope", ["Compare assignments consistently", "Surface passages and document relationships", "Similarity is not a plagiarism verdict"]),
    ("Objectives", ["Extract TXT, PDF, DOCX, and OCR-enabled images", "Compare TF-IDF lexical similarity", "Explore semantic scores, groups, clusters, and evaluation"]),
    ("System architecture", ["Upload -> extract/OCR -> normalize paragraphs", "TF-IDF -> cosine scores -> rankings and matrix", "Cosine distance -> groups and hierarchical clusters"]),
    ("TF-IDF and cosine similarity", ["Distinctive terms receive higher weight", "cos(x,y) = (x . y) / (||x|| ||y||)", "Displayed percentage is a scaled similarity score"]),
    ("Semantic comparison and clustering", ["Optional normalized sentence embeddings", "Average-linkage clustering over cosine distance", "Silhouette is unavailable for undefined cluster layouts"]),
    ("Dataset and evaluation", ["Synthetic demo corpus is separate from the benchmark", "Seven illustrative labelled pairs with train/validation/test splits", "Thresholds are selected on validation data only"]),
    ("Experimental results", ["Run python src\\evaluate_models.py", "Populate this slide from docs/evaluation/metrics.csv", "Do not invent metrics or claim production accuracy"]),
    ("Live demonstration", ["Pair comparison and shared-word highlighting", "Collection matrix, connected groups, and clusters", "CSV export and lexical fallback when the model is unavailable"]),
    ("Limitations and conclusion", ["OCR, model downloads, common terminology, and small data affect results", "Human review and privacy remain essential", "Future work: larger reviewed benchmark and stability studies"]),
]


def add_slide(prs, title, bullets):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    box = slide.shapes.add_textbox(Inches(1), Inches(1.6), Inches(11), Inches(5))
    frame = box.text_frame
    frame.clear()
    for index, bullet in enumerate(bullets):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = bullet
        paragraph.level = 0
        paragraph.font.size = Pt(24)
    return slide


def main():
    prs = Presentation()
    for title, bullets in SLIDES:
        add_slide(prs, title, bullets)
    prs.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
