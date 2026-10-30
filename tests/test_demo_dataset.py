from demo_dataset import discover_sample_files, sample_dataset_signature


def test_discover_sample_files_loads_supported_files(tmp_path):
    (tmp_path / "second.txt").write_text("second", encoding="utf-8")
    (tmp_path / "first.TXT").write_text("first", encoding="utf-8")
    (tmp_path / "notes.csv").write_text("ignored", encoding="utf-8")

    files, errors = discover_sample_files(tmp_path)

    assert [file.name for file in files] == ["first.TXT", "second.txt"]
    assert errors == ["notes.csv: unsupported file type; it was not loaded."]


def test_discover_sample_files_reports_missing_and_empty_directories(tmp_path):
    missing_files, missing_errors = discover_sample_files(tmp_path / "missing")
    empty_files, empty_errors = discover_sample_files(tmp_path)

    assert missing_files == []
    assert "was not found" in missing_errors[0]
    assert empty_files == []
    assert empty_errors == ["The sample dataset directory is empty."]


def test_sample_dataset_signature_changes_when_a_file_changes(tmp_path):
    sample_file = tmp_path / "assignment.txt"
    sample_file.write_text("before", encoding="utf-8")
    first_signature = sample_dataset_signature(tmp_path)
    sample_file.write_text("after", encoding="utf-8")

    assert sample_dataset_signature(tmp_path) != first_signature
