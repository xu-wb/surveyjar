"""Explicit item scoring and dimension aggregation; no clinical algorithms."""
import math

def aggregate(values, method):
    if method == 'none' or not values or any(v is None for v in values):
        return None
    return sum(values) / len(values) if method == 'mean' else sum(values)

def score(survey, answers):
    details, missing = [], []
    raw_only = survey.get('scoreMode') == 'raw'
    for q in survey['questions']:
        value = answers.get(q['id'])
        empty = value is None or value == '' or value == []
        raw = points = None
        mode = q.get('scoring', 'none')
        if q['type'] == 'forced':
            count = q.get('chooseCount', 1)
            if len(q.get('options', [])) < 2 or type(count) is not int or not 1 <= count < len(q['options']):
                raise ValueError('迫选题的选择数量须为整数且小于选项数量：' + q['title'])
            if not empty:
                chosen = value if isinstance(value, list) else [value]
                if isinstance(value, dict) or (count == 1 and isinstance(value, list)):
                    raise ValueError('迫选题回答格式不正确：' + q['title'])
                if len(chosen) != count:
                    empty = True
        reverse = q.get('reverse', False) or mode == 'reverse'
        raw_values = []
        if q['type'] == 'substance':
            used = value.get('used') if isinstance(value, dict) else None
            duration = value.get('duration') if isinstance(value, dict) else None
            empty = used not in ('yes', 'no') or (used == 'yes' and duration in (None, ''))
            if used == 'yes' and duration not in (None, ''):
                n = float(duration)
                if not math.isfinite(n) or n <= 0:
                    raise ValueError('使用时长应大于 0：' + q['title'])
            if used == 'no' and isinstance(value, dict):
                # Clear previously entered duration when the answer changes to no.
                value = dict(value, duration='')
                answers[q['id']] = value
        elif not empty and q['type'] in ('single', 'multi', 'forced'):
            chosen = value if isinstance(value, list) else [value]
            if len(set(chosen)) != len(chosen) or any(not str(i).isdigit() or not 0 <= int(i) < len(q['options']) for i in chosen):
                raise ValueError('无效选项：' + q['title'])
            if mode != 'none':
                vals = [float(o['score']) if mode == 'custom' or survey.get('scoreVersion') == 2 else i+1
                        for i, o in enumerate(q['options'])]
                raw_values = [vals[int(i)] for i in chosen]
                raw = sum(raw_values)
                points = sum(max(vals)+min(vals)-v if reverse else v for v in raw_values)
        elif not empty and q['type'] in ('scale', 'number'):
            number = float(value)
            if not math.isfinite(number) or not float(q['min']) <= number <= float(q['max']):
                raise ValueError('数字超出范围：' + q['title'])
            if q['type'] == 'scale' and not number.is_integer():
                raise ValueError('量表请选择整数：' + q['title'])
            if mode != 'none':
                if mode == 'custom':
                    key = str(int(number)) if number.is_integer() else str(number)
                    raw = float(q.get('mapping', {}).get(key, 0))
                    vals = [float(v) for v in q.get('mapping', {}).values()] + [0]
                    points = max(vals)+min(vals)-raw if reverse else raw
                else:
                    raw = number
                    points = float(q['min'])+float(q['max'])-number if reverse else number
        if empty and (q.get('required') or q['type'] == 'forced'):
            missing.append(q['title'] + ('（是否使用及使用时长）' if q['type'] == 'substance' else ''))
        details.append({'id': q['id'], 'title': q['title'], 'value': value,
                        'rawScore': raw, 'rawOptionScores': raw_values, 'score': None if raw_only else points,
                        'reverse': reverse, 'dimensionId': q.get('dimensionId', ''),
                        'scored': mode != 'none' and q['type'] not in ('text', 'substance')})
    dimensions = []
    for d in survey.get('dimensions', []):
        members = [x for x in details if x['dimensionId'] == d['id'] and x['scored']]
        dimensions.append({'id': d['id'], 'name': d['name'], 'method': d.get('method', 'sum'),
                           'score': None if raw_only else aggregate([x['score'] for x in members], d.get('method', 'sum')),
                           'answered': sum(x['rawScore'] is not None for x in members), 'items': len(members)})
    method = survey.get('totalMethod', 'sum')
    total = None if raw_only else aggregate([d['score'] for d in details if d['scored']], method)
    return {'total': total, 'totalMethod': method, 'scoreMode': survey.get('scoreMode', 'auto'),
            'dimensions': dimensions, 'details': details}, missing
