MAX_ASSIGNMENTS = 50


def upload_mode(upload_count):
    if upload_count == 2:
        return "pair"
    if 3 <= upload_count <= MAX_ASSIGNMENTS:
        return "collection"
    return "inactive"


def upload_state_changed(previous_mode, previous_signature, mode, signature):
    return (mode, signature) != (previous_mode, previous_signature)
