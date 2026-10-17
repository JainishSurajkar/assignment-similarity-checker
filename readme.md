# Assignment Similarity Checker

A Streamlit application that compares two assignments paragraph by paragraph and identifies pairs with similar content.

## Features

- Compare two assignment texts side by side.
- Split assignments into paragraphs using blank lines.
- Calculate paragraph similarity with TF-IDF and cosine similarity.
- Choose a minimum similarity threshold from `0%` to `100%`.
- Automatically update the results when the threshold slider changes.
- Expand each result to view the compared paragraphs and similarity score.

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

Start the Streamlit application from the project directory:

```powershell
streamlit run app.py
```

Streamlit will open the application in your browser. If it does not open automatically, visit the local URL shown in the terminal.

## Usage

1. Paste the first assignment into **Assignment A**.
2. Paste the second assignment into **Assignment B**.
3. Separate paragraphs with a blank line.
4. Adjust the **Minimum similarity to display** slider.
5. Review the matching paragraph pairs shown below the slider.

The application compares every paragraph in Assignment A with every paragraph in Assignment B. Increasing the threshold shows only more closely matching pairs.

## Project structure

```text
assignment-similarity-checker/
├── app.py                 # Streamlit user interface
├── similarity.py          # Paragraph splitting and similarity calculations
├── requirement.txt        # Python dependencies
├── readme.md              # Project documentation
└── .gitignore             # Ignored local files and environments
```

## How similarity is calculated

1. Each assignment is split into paragraphs using two consecutive newline characters.
2. All paragraphs are converted into TF-IDF vectors with `TfidfVectorizer`.
3. Cosine similarity is calculated for every Assignment A and Assignment B paragraph pair.
4. Results are sorted from the highest similarity score to the lowest.
5. The selected slider threshold filters the displayed results.

## Notes

- Empty assignments are not compared.
- A similarity score is displayed as a percentage.
- The `.venv` directory is ignored and should not be committed to Git.
