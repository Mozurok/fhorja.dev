"""Calibration implementations and deliberate faults; never an agent treatment."""
import json
import sys
from itertools import groupby


def aggregate(request, variant='reference', fault=None):
    try:
        if not isinstance(request, dict) or not isinstance(request.get('rows'), list):
            raise ValueError()
        blocked = request.get('blocked', [])
        if not isinstance(blocked, list) or any(not isinstance(s, str) or not s.strip() for s in blocked):
            raise ValueError()
        blocked = {s.strip().casefold() for s in blocked}
        normalized = []
        for row in request['rows']:
            if (not isinstance(row, dict) or not isinstance(row.get('sku'), str) or not row['sku'].strip()
                    or (not isinstance(row.get('delta'), int) if fault == 'allow-bool' else type(row.get('delta')) is not int)):
                raise ValueError()
            name, delta = row['sku'].strip().casefold(), row['delta']
            if name not in blocked:
                if fault == 'absolute':
                    delta = abs(delta)
                normalized.append((name, delta))
        if fault == 'deduplicate':
            normalized = list(dict.fromkeys(normalized))
        if variant == 'alternative':
            order = list(dict.fromkeys(name for name, _ in normalized))
            groups = {name: sum(delta for _, delta in group) for name, group in groupby(sorted(normalized), key=lambda row: row[0])}
            totals = [(name, groups[name]) for name in order]
        else:
            values = {}
            for name, delta in normalized:
                values[name] = values.get(name, 0) + delta
            totals = list(values.items())
        if fault == 'sorted':
            totals.sort()
        if fault == 'float':
            totals = [(name, int(float(delta))) for name, delta in totals]
        if fault == 'drop-zero':
            totals = [(name, delta) for name, delta in totals if delta]
        return [{'sku': name, 'units': delta} for name, delta in totals]
    except ValueError:
        return [] if fault == 'bad-error' else {'error': 'invalid'}


if __name__ == '__main__':
    variant = sys.argv[1] if len(sys.argv) > 1 else 'reference'
    fault = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps({'result': aggregate(json.load(sys.stdin), variant, fault)}, ensure_ascii=False))
