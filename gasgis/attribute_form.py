"""Attribute entry for new vector features."""
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit


def prompt_attributes(parent, layer, defaults=None):
    dialog = QDialog(parent)
    dialog.setWindowTitle("New gas asset")
    form = QFormLayout(dialog)
    editors = {}
    for field in layer.fields():
        if field.name().lower() in ("fid", "ogc_fid"):
            continue
        editor = QLineEdit(dialog)
        editor.setText(str((defaults or {}).get(field.name(), "")))
        form.addRow(field.name(), editor)
        editors[field.name()] = editor
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec_() != QDialog.Accepted:
        return None
    values = {}
    for name, editor in editors.items():
        raw = editor.text().strip()
        if raw:
            values[name] = raw
    return values
