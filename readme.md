# Assignment Similarity Checker

A Streamlit application that compares uploaded assignments paragraph by
paragraph and identifies pairs and groups with similar content.

Upload TXT, PDF, DOCX, or image files, inspect lexical and semantic similarity, and
prioritize passages for human review. Similarity scores are not plagiarism
probabilities or disciplinary decisions.

## Features

- Use one upload area for both pair comparison and collection analysis.
- Upload exactly two assignments for detailed paragraph comparison.
- Upload three to fifty assignments for collection analysis.
- Extract text automatically from each uploaded file.
- Compare every paragraph in Assignment A with every paragraph in Assignment B.
- Calculate similarity using TF-IDF and cosine similarity.
- Filter displayed paragraph pairs with a similarity threshold from `0%` to
  `100%`.
- Display matching paragraphs side by side for easier comparison.
- Optionally highlight shared individual words with a separate checkbox.
- Use a different color for each shared word, with the same color applied in
  both paragraphs.
- Show the similarity percentage for every displayed paragraph pair.
- Analyze a collection of 3 to 50 assignments in the collection analyzer.
- Display a document-level similarity matrix and ranked assignment pairs.
- Discover connected groups of assignments above a selected threshold.
- Discover hierarchical clusters with explanatory keywords and internal
  similarity summaries.
- Compare lexical TF-IDF similarity with semantic sentence-embedding
  similarity for two assignments.
- Evaluate both methods on manually labelled paragraph pairs with precision,
  recall, F1-score, and error analysis.

## Requirements

- Python 3.10 or newer
- The packages listed in [`requirements.txt`](./requirements.txt)

## Installation

1. Clone or download this repository.

2. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

3. Activate the virtual environment on Windows:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. Install the dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

## Running the application

Run the following command from the project directory:

```powershell
streamlit run src\app.py
```

Streamlit will open the application in your browser. If it does not open
automatically, visit the local URL shown in the terminal.

## Usage

1. Upload `TXT`, `PDF`, `DOCX`, or common image files using the single upload area.
2. Upload exactly two files for a detailed paragraph comparison, or upload
   three to fifty files for collection analysis.
3. Click **Compare assignments** after the files are successfully read.
4. Adjust the relevant similarity threshold to filter the results.
5. Use **Show shared-word highlighting** if you want common words marked.
6. Expand a result to view the compared paragraphs side by side.
7. Download the results as a CSV file if needed.

The application compares every paragraph in Assignment A with every paragraph
in Assignment B. The results summary shows the number of assignments, the
number of paragraph pairs compared, and the number currently displayed. A
higher threshold displays only paragraph pairs with higher similarity scores.
The highlighting option marks common individual words; it does not identify
exact copied phrases or establish plagiarism.

### Application tabs

- **Pair Comparison** handles exactly two uploads and shows overall TF-IDF
  similarity plus ranked paragraph matches.
- **Collection Analysis** handles three to fifty uploads and shows the matrix,
  ranked document pairs, and one selected pair's paragraph details.
- **Connected Groups** shows threshold-based connected components, including
  indirect links.
- **Hierarchical Clustering** shows average-linkage clusters, keywords,
  average internal similarity, and closest assignments.
- **Lexical vs Semantic** compares wording overlap with signed semantic cosine
  scores.
- **Model Evaluation** runs the offline train/validation/test benchmark only
  when all required splits are valid.

### Lexical versus semantic comparison

With exactly two uploaded files, click **Compare lexical and semantic
similarity** to calculate both scores for the same paragraph pairs. Lexical
similarity uses TF-IDF and shared word patterns. Semantic similarity uses the
`sentence-transformers/all-MiniLM-L6-v2` embedding model to estimate
meaning-related similarity. It reports a scaled semantic cosine score from
-100 to 100, not a calibrated probability of copying.

The first semantic comparison downloads the model and may take longer. Use the
two thresholds to filter pairs meeting either criterion. A positive semantic
minus lexical difference can indicate related wording with different
vocabulary; it is not evidence of plagiarism.

The semantic method is a practical baseline, not a guarantee of better
plagiarism detection. It can recognize paraphrases that share fewer words,
while TF-IDF remains more interpretable and often stronger for near-identical
copying. The embedding model may truncate very long paragraphs, so paragraph
length and domain should be considered when interpreting results.

## Evaluation

Annotation rules are documented in
[`docs/annotation_guidelines.md`](./docs/annotation_guidelines.md). Add
manually reviewed pairs to [`docs/test_pairs.csv`](./docs/test_pairs.csv),
using `1` for substantial overlap and `0` for no substantial overlap. Keep
related pairs in the same `train`, `validation`, or `test` split where
possible.

Run the evaluation script from the project root:

```powershell
python src\evaluate_models.py
```

It creates `docs\evaluation\scored_pairs.csv`, `metrics.csv`, and separate
error files for each method. Thresholds are selected by F1-score on the
validation split and measured on the held-out test split. The evaluator
requires exactly `train`, `validation`, and `test` splits and never reports
all-data metrics as held-out performance. If `sentence-transformers` is not
installed or the model cannot load, lexical held-out metrics are still
reported and the semantic method is explicitly marked unavailable.

### Collection analysis

When three or more files are uploaded, the app displays the similarity matrix,
summary metrics, and ranked pairs after **Compare assignment collection** is
clicked. Detailed paragraph comparison is calculated only for the selected
ranked pair, avoiding work for every possible pair. Connected groups and
hierarchical clustering are available in their own tabs so each result has a
single, focused location.

The **Connected Groups** tab uses the selected threshold to show direct and
indirect groups of related assignments. The **Hierarchical Clustering** tab
uses average-linkage clustering with cosine distance. Choose a clustering
setting and click **Discover or refresh clusters** to view cluster sizes,
member assignments, important TF-IDF words and phrases, average internal
similarity, and each assignment's closest member.

## Supported files

- **TXT**: Read as UTF-8 text.
- **PDF**: Text is extracted from each page. Scanned or image-only PDFs are
  rendered and read with OCR. Password-protected PDFs are not supported.
- **DOCX**: Text is extracted from document paragraphs and table rows. Embedded
  images are also read with OCR.
- **Images**: PNG, JPG, JPEG, BMP, TIF, and TIFF images are read with OCR.

OCR requires the Tesseract executable to be installed and available on the
system `PATH`. Enable the **OCR for scanned PDFs and image files** option in
the app before uploading scanned or image-based content. With OCR disabled,
the app uses normal text extraction only and image files are rejected.
Legacy `.doc` files are not supported. Save Word documents as `.docx` before
uploading them.

## How similarity is calculated

1. Line endings are normalized and excessive whitespace is removed while
   blank-line paragraph boundaries are preserved.
2. All paragraphs are converted into TF-IDF vectors with
   `TfidfVectorizer`.
3. Cosine similarity is calculated for every Assignment A and Assignment B
   paragraph pair.
4. Results are sorted from the highest similarity score to the lowest.
5. The selected threshold filters the displayed results.

For collection clustering, TF-IDF uses English stop-word removal and unigrams
plus bigrams. Cosine similarity is converted to cosine distance
(`1 - similarity`) and grouped with average-linkage agglomerative clustering.
The clustering setting controls where the hierarchy is cut; it does not prove
that every pair inside a cluster meets the selected percentage.

When highlighting is enabled, shared words are matched case-insensitively.
Each shared word receives a deterministic color, and that same color is used
for the word in both assignments.

## How it works

1. Text is extracted and checked for readable content.
2. With two files, TF-IDF ranks every cross-assignment paragraph pair.
3. With three or more files, complete-document TF-IDF produces a matrix and
   ranked assignment pairs.
4. Optional sentence embeddings provide a separate semantic comparison for two
   files.
5. The interface filters and explains results for human review.

### Score glossary and limitations

- **TF-IDF cosine similarity (%)** measures weighted vocabulary overlap.
- **Scaled semantic cosine score (%)** is normalized-embedding cosine
  similarity multiplied by 100; negative values are possible and it is not a
  probability.
- **Threshold** is a display filter and does not recalculate the comparison.
- **Shared-word highlighting** marks common individual words, not copied
  phrases.

Common teaching material, prompts, citations, and legitimate collaboration can
create similarity. Scanned PDFs require OCR, which this project does not
implement.

## Screenshots

These screenshots were captured from the running application and show the
main workflows used during a demonstration:

### Pair comparison

Upload exactly two files, click **Compare assignments**, and review the
overall TF-IDF score, paragraph matches, threshold filtering, and CSV export.

![Pair Comparison tab](./screenshots/pair-comparison.png)

### Collection analysis

Upload three to fifty files and click **Compare assignment collection** to
build the document-level similarity matrix and ranked pairs. Detailed
paragraph comparison is calculated only for the selected pair.

![Collection Analysis tab](./screenshots/collection-analysis.png)

### Connected groups

The Connected Groups tab shows assignments linked by the selected threshold,
including indirect links between documents.

![Connected Groups tab](./screenshots/connected-groups.png)

### Hierarchical clustering

The Hierarchical Clustering tab summarizes cluster membership, keywords,
internal similarity, and closest assignments.

![Hierarchical Clustering tab](./screenshots/hierarchical-clustering.png)

### Lexical versus semantic comparison

The Lexical vs Semantic tab compares TF-IDF wording overlap with the signed
semantic cosine score scaled by 100.

![Lexical vs Semantic tab](./screenshots/lexical-semantic.png)

### Model evaluation

The Model Evaluation tab reports the offline train/validation/test benchmark
separately from uploaded assignments.

![Model Evaluation tab](./screenshots/model-evaluation.png)

The original application home-screen capture is also preserved:

![Assignment Similarity Checker home screen](./docs/app-home.png)

## Limitations

Similarity scores prioritize passages for human review; they do not prove
plagiarism or represent a probability of copying. Shared words can come from
prompts, textbooks, citations, or standard terminology. Semantic scores are
scaled cosine values and can be negative. The starter evaluation dataset is
larger than the original six examples but contains illustrative labels rather
than verified domain annotations, so its metrics are not a reliable claim of
production accuracy. Replace or expand it with genuinely reviewed pairs before
presenting performance results.
Scanned PDFs require OCR, which is not implemented, and long paragraphs may
be truncated by the embedding model.

## Testing

Run the automated tests from the project root:

```powershell
pytest
```

The tests cover extraction validation, paragraph splitting and scoring,
collection grouping, singleton cluster summaries, and training-only lexical
vectorizer fitting.

## Project structure

```text
assignment-similarity-checker/
├── src/
│   ├── app.py                 # Streamlit user interface
│   ├── collection_similarity.py # Collection similarity and grouping
│   ├── cluster_analysis.py    # Hierarchical clustering and summaries
│   ├── lexical_semantic.py    # Lexical and embedding-based comparison
│   ├── evaluate_models.py     # Reproducible model evaluation
│   ├── file_extraction.py    # TXT, PDF, and DOCX text extraction
│   ├── upload_state.py        # Upload mode and signature state helpers
│   └── similarity.py          # Paragraph splitting and similarity calculation
├── requirements.txt            # Python dependencies
├── docs/
│   ├── annotation_guidelines.md
│   └── test_pairs.csv
├── screenshots/                # Real application screenshots
├── readme.md                  # Project documentation
└── .gitignore                 # Ignored local files and environments
```

## Notes

- With two files, the slider and results are hidden until both assignments
  contain extractable text; results appear after **Compare assignments**.
- With three or more files, collection results appear after at least two valid
  files remain and **Compare assignment collection** is clicked.
- Empty or unreadable assignments are not compared.
- Similarity scores are displayed as percentages.
- Individual uploads are limited to 10 MB.
- Collection results can be downloaded as a CSV file.
- The evaluation starter dataset contains 60 labelled examples across
  train/validation/test splits and should continue to grow with manually
  reviewed domain-specific pairs.
- The `.venv` directory is ignored and should not be committed to Git.
