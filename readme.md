# Assignment Similarity Checker

A Streamlit application that compares uploaded assignments paragraph by
paragraph and identifies pairs and groups with similar content.

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
- Highlight shared words when the selected threshold is below `50%`.
- Use a different color for each shared word, with the same color applied in
  both paragraphs.
- Show the similarity percentage for every displayed paragraph pair.
- Analyze a collection of 2 to 50 assignments in the collection analyzer.
- Display a document-level similarity matrix and ranked assignment pairs.
- Discover connected groups of assignments above a selected threshold.

## Requirements

- Python 3.10 or newer
- The packages listed in [`requirement.txt`](./requirement.txt)

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
   pip install -r requirement.txt
   ```

## Running the application

Run the following command from the project directory:

```powershell
streamlit run src\app.py
```

Streamlit will open the application in your browser. If it does not open
automatically, visit the local URL shown in the terminal.

## Usage

1. Upload `TXT`, `PDF`, or `DOCX` files using the single upload area.
2. Upload exactly two files for a detailed paragraph comparison, or upload
   three to fifty files for collection analysis.
3. Click **Compare assignments** after the files are successfully read.
4. Adjust the relevant similarity threshold to filter the results.
5. Expand a result to view the compared paragraphs side by side.
6. Set the threshold below `50%` to see shared words highlighted.
7. Download the results as a CSV file if needed.

The application compares every paragraph in Assignment A with every paragraph
in Assignment B. A higher threshold displays only paragraph pairs with higher
similarity scores.

### Collection analysis

When three or more files are uploaded, the app displays the similarity matrix,
summary metrics, ranked pairs, and connected groups automatically after
**Compare assignments** is clicked.

## Supported files

- **TXT**: Read as UTF-8 text.
- **PDF**: Text is extracted from each page. Scanned PDFs that contain only
  images require OCR and are not supported.
- **DOCX**: Text is extracted from the document paragraphs.

Legacy `.doc` files are not supported. Save Word documents as `.docx` before
uploading them.

## How similarity is calculated

1. Each assignment is split into paragraphs using two consecutive newline
   characters.
2. All paragraphs are converted into TF-IDF vectors with
   `TfidfVectorizer`.
3. Cosine similarity is calculated for every Assignment A and Assignment B
   paragraph pair.
4. Results are sorted from the highest similarity score to the lowest.
5. The selected threshold filters the displayed results.

When highlighting is enabled, shared words are matched case-insensitively.
Each shared word receives a deterministic color, and that same color is used
for the word in both assignments.

## Project structure

```text
assignment-similarity-checker/
├── src/
│   ├── app.py                 # Streamlit user interface
│   ├── collection_similarity.py # Collection similarity and grouping
│   ├── file_extraction.py    # TXT, PDF, and DOCX text extraction
│   ├── similarity.py          # Paragraph splitting and similarity calculation
│   └── text_preprocessing.py # Additional preprocessing examples/utilities
├── requirement.txt            # Python dependencies
├── readme.md                  # Project documentation
└── .gitignore                 # Ignored local files and environments
```

## Notes

- With two files, the slider and results are hidden until both assignments
  contain extractable text.
- With three or more files, collection results appear after at least two valid
  files remain and **Compare assignments** is clicked.
- Empty or unreadable assignments are not compared.
- Similarity scores are displayed as percentages.
- Individual uploads are limited to 10 MB.
- Collection results can be downloaded as a CSV file.
- The `.venv` directory is ignored and should not be committed to Git.
