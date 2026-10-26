"""Basic vector editing actions for the selected layer.

No topology-aware digitizing is provided yet.
"""


def start_editing(layer):
    if layer is None or not layer.isValid() or not layer.isSpatial():
        raise ValueError("Select a valid spatial layer")
    if not layer.isEditable() and not layer.startEditing():
        raise RuntimeError("Layer provider does not allow editing")
    return True


def save_edits(layer):
    if layer is None or not layer.isEditable():
        raise ValueError("Selected layer is not in edit mode")
    if not layer.commitChanges():
        errors = "; ".join(layer.commitErrors())
        raise RuntimeError(errors or "Commit failed; changes remain pending")
    return True


def rollback_edits(layer):
    if layer is None or not layer.isEditable():
        raise ValueError("Selected layer is not in edit mode")
    if not layer.rollBack():
        raise RuntimeError("Unable to discard edits")
    return True
