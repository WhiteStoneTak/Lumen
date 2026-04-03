from typing import Any

def group_and_aggregate(pairs: list[tuple[Any, ...]]) -> dict[Any, Any]:
    """
    Preconditions:
    - None.

    Postconditions:
    - Group (key, value) pairs and compute per-group statistics

    Invariants:
    - None.
    """
    result: dict = {}
    for key, value in pairs:
        if key not in result:
            result[key] = {'count': 1, 'sum': value, 'min': value, 'max': value}
        else:
            entry = result[key]
            entry['count'] += 1
            entry['sum'] += value
            if value < entry['min']:
                entry['min'] = value
            if value > entry['max']:
                entry['max'] = value
    return result
