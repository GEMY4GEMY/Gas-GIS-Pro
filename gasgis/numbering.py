"""Sequential asset identifiers and duplicate detection."""


def next_asset_id(existing, prefix='GAS', width=5):
    """Return the next unused identifier based on the largest numeric suffix."""
    if not prefix or width < 1:
        raise ValueError('Invalid prefix or width')
    largest = 0
    for value in existing:
        text = str(value).strip()
        if not text.startswith(prefix + '-'):
            continue
        suffix = text[len(prefix) + 1:]
        if suffix.isdecimal():
            largest = max(largest, int(suffix))
    return f'{prefix}-{largest + 1:0{width}d}'


def duplicates(values):
    seen = set()
    repeated = set()
    for value in values:
        value = str(value).strip() if value is not None else ''
        if value:
            if value in seen:
                repeated.add(value)
            seen.add(value)
    return sorted(repeated)
