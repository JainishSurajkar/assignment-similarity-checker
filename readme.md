# Assignment Similarity Checker

A Streamlit application that compares two uploaded assignments paragraph by
paragraph and identifies pairs with similar content.

## Features

- Upload two assignments in `TXT`, `PDF`, or `DOCX` format.
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

1. Upload a `TXT`, `PDF`, or `DOCX` file under **Assignment A**.
2. Upload a `TXT`, `PDF`, or `DOCX` file under **Assignment B**.
3. The similarity threshold slider appears after both files are successfully
   read and contain text.
4. Adjust **Minimum similarity to display** to filter the results.
5. Expand a result to view Assignment A and Assignment B side by side.
6. Set the threshold below `50%` to see shared words highlighted.

The application compares every paragraph in Assignment A with every paragraph
in Assignment B. A higher threshold displays only paragraph pairs with higher
similarity scores.

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
│   ├── file_extraction.py    # TXT, PDF, and DOCX text extraction
│   ├── similarity.py          # Paragraph splitting and similarity calculation
│   └── text_preprocessing.py # Additional preprocessing examples/utilities
├── requirement.txt            # Python dependencies
├── readme.md                  # Project documentation
└── .gitignore                 # Ignored local files and environments
```

## Notes

- The slider and results are hidden until both uploaded assignments contain
  extractable text.
- Empty or unreadable assignments are not compared.
- Similarity scores are displayed as percentages.
- The `.venv` directory is ignored and should not be committed to Git.
