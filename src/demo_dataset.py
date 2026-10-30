import hashlib
from dataclasses import dataclass
from pathlib import Path

from file_extraction import SUPPORTED_FILE_TYPES


@dataclass(frozen=True)
class LocalUploadedFile:
    """Small UploadedFile-compatible wrapper for files stored in the repo."""

    name: str
    _file_bytes: bytes

    @property
    def size(self):
        return len(self._file_bytes)

    def getvalue(self):
        return self._file_bytes


def discover_sample_files(dataset_directory):
    """Return supported sample files and errors for unsupported entries."""
    directory = Path(dataset_directory)
    if not directory.exists():
        return [], [f"Sample dataset directory was not found: {directory}"]
    if not directory.is_dir():
        return [], [f"Sample dataset path is not a directory: {directory}"]

    files = []
    errors = []
    supported_extensions = {f".{extension}" for extension in SUPPORTED_FILE_TYPES}
    for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file():
            continue
        if path.suffix.casefold() not in supported_extensions:
            errors.append(
                f"{path.name}: unsupported file type; it was not loaded."
            )
            continue
        try:
            files.append(LocalUploadedFile(path.name, path.read_bytes()))
        except OSError as error:
            errors.append(f"{path.name}: could not be read ({error}).")
    if not files and not errors:
        errors.append("The sample dataset directory is empty.")
    return files, errors


def sample_dataset_signature(dataset_directory, use_ocr=False):
    """Return a stable signature so sample files are extracted only when needed."""
    directory = Path(dataset_directory)
    digest = hashlib.sha256()
    digest.update(str(use_ocr).encode("ascii"))
    if directory.exists() and directory.is_dir():
        for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
            if path.is_file():
                try:
                    stat = path.stat()
                except OSError:
                    continue
                digest.update(path.name.encode("utf-8"))
                digest.update(str(stat.st_size).encode("ascii"))
                digest.update(str(stat.st_mtime_ns).encode("ascii"))
    else:
        digest.update(b"missing")
    return digest.hexdigest()
