from upload_state import upload_mode, upload_state_changed


def test_upload_mode_selects_pair_collection_or_inactive():
    assert upload_mode(0) == "inactive"
    assert upload_mode(1) == "inactive"
    assert upload_mode(2) == "pair"
    assert upload_mode(3) == "collection"
    assert upload_mode(50) == "collection"
    assert upload_mode(51) == "inactive"


def test_upload_state_changes_when_mode_or_files_change():
    assert not upload_state_changed("pair", "same", "pair", "same")
    assert upload_state_changed("pair", "same", "collection", "same")
    assert upload_state_changed("pair", "same", "pair", "different")
