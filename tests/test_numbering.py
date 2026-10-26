from gasgis.numbering import next_asset_id, duplicates


def test_next_id():
    assert next_asset_id(["GAS-00001", "GAS-00009"]) == "GAS-00010"


def test_prefix_filter():
    assert next_asset_id(["VAL-00008"], prefix="GAS") == "GAS-00001"


def test_duplicates():
    assert duplicates(["A", "B", "A", "", None, "B"]) == ["A", "B"]
