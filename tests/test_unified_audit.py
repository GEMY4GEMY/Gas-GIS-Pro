from gasgis.unified_audit import audit_network


def test_unified_audit():
    parts = [('P1', (0, 0), (2, 2)), ('P2', (0, 2), (2, 0))]
    issues = audit_network(parts, parts, [('V1', 0, 0)])
    assert sum(i['issue'] == 'CROSSING' for i in issues) == 1
    assert sum(i['issue'] == 'NO_NEARBY_NODE' for i in issues) == 3
    assert sum(i['issue'] == 'LOOSE_END' for i in issues) == 4


def test_empty_audit():
    assert audit_network([], []) == []
