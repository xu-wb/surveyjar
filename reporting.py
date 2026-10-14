"""One row per project session, one column per item; never change stored answers."""
from copy import deepcopy
import json
from scoring import score


def report_survey(response, current=None):
    survey = deepcopy(response['survey'])
    if current:
        # Keep the original response scale and option scores. Only update direction/grouping.
        mapping = {q['id']: q for q in current['questions']}
        for q in survey['questions']:
            config = mapping.get(q['id'])
            if config:
                q['reverse'] = config.get('reverse', False) or config.get('scoring') == 'reverse'
                if q.get('scoring') == 'reverse':
                    q['scoring'] = 'forward'
                q['dimensionId'] = config.get('dimensionId', '')
        for key in ('dimensions', 'totalMethod', 'scoreMode'):
            if key in current:
                survey[key] = deepcopy(current[key])
    return survey


def wide_report(responses, current_surveys, selection):
    ids = set(selection.get('surveyIds', []))
    if not ids:
        raise ValueError('请至少选择一份问卷')
    project_id = str(selection.get('projectId', ''))
    records = [r for r in responses if r['survey_id'] in ids
               and (not project_id or str(r.get('projectId', '')) == project_id)
               and (selection.get('includeDrafts') or r['status'] == 'submitted')]
    if not records:
        raise ValueError('筛选范围内没有可导出的答卷；未完成答卷可勾选「包含草稿」')
    headers = ['被试编号', '项目', '作答批次', '状态', '计分依据']
    schemas, groups, warnings = {}, {}, []
    current = {s['id']: s for s in current_surveys}
    for r in reversed(records):
        s = report_survey(r, current.get(r['survey_id']) if selection.get('basis') == 'current' else None)
        result, _ = score(s, deepcopy(r['answers']))
        signature = (r['survey_id'], json.dumps(s, sort_keys=True, ensure_ascii=False))
        if signature not in schemas:
            version = 1 + sum(key[0] == r['survey_id'] for key in schemas)
            prefix = s['title'] + (f'（版本{version}）' if version > 1 else '')
            columns = []
            for n, q in enumerate(s['questions'], 1):
                title = (q.get('groupTitle', '') + ' / ' if q.get('groupId') else '') + q['title']
                label = f'{prefix} · 第{n}条目 {title}' if q.get('groupId') else f'{prefix} · 第{n}题 {title}'
                if q['type'] == 'substance':
                    columns.extend([(label+' · 是否使用（0否1是）', q['id'], 'used'),
                                    (label+' · 使用时长（年）', q['id'], 'duration')])
                elif q['type'] == 'forced' and q.get('scoring') == 'none':
                    choices = '；'.join(f'{i+1}={o["label"]}' for i, o in enumerate(q['options']))
                    columns.append((label+' · 选择（'+choices+'；非得分）', q['id'], 'choice'))
                elif q.get('scoring', 'none') != 'none' and q['type'] != 'text':
                    columns.append((label+' · 原始分', q['id'], 'rawScore'))
                    if q.get('reverse') or q.get('scoring') == 'reverse':
                        columns.append((label+' · 反向计分', q['id'], 'score'))
                elif q['type'] in ('number', 'scale'):
                    columns.append((label+' · 原始数值', q['id'], 'number'))
            for d in s.get('dimensions', []):
                numbers = ','.join(str(i+1) for i,q in enumerate(s['questions']) if q.get('dimensionId') == d['id'])
                columns.append((f'{prefix} · {d["name"]}（'+('平均分' if d.get('method')=='mean' else '总分')+f'；题号{numbers or "未分配"}）', d['id'], 'dimension'))
            columns.append((prefix+' · 问卷总分', '', 'total'))
            schemas[signature] = (len(headers), columns)
            headers.extend(c[0] for c in columns)
        start, columns = schemas[signature]
        group_key = ('batch', r['batchId']) if r.get('batchId') else ('response', r['id'])
        if group_key not in groups:
            participant = r.get('participant') or '未填写编号'
            groups[group_key] = {'meta': [participant, r.get('projectName', '单独填写'),
                                 r.get('batchId') or f'单次-{r["id"]}', '已提交',
                                 '当前反向/维度规则' if selection.get('basis')=='current' else '作答时规则'], 'values': {},
                                 'expected': set(r.get('batchSurveyIds', [])) & ids, 'submitted': set()}
        group = groups[group_key]
        if r['status'] != 'submitted':
            group['meta'][3] = '含草稿'
        else:
            group['submitted'].add(r['survey_id'])
        items = {d['id']: d for d in result['details']}
        dims = {d['id']: d['score'] for d in result['dimensions']}
        for offset, (_, item, kind) in enumerate(columns):
            v = r['answers'].get(item)
            if kind in ('rawScore', 'score'):
                value = items.get(item, {}).get(kind)
            elif kind == 'choice':
                value = '、'.join(str(int(i)+1) for i in v) if isinstance(v, list) else int(v)+1 if v not in (None, '') else None
            elif kind == 'number':
                value = float(v) if v not in (None, '') else None
            elif kind == 'used':
                value = {'yes': 1, 'no': 0}.get(v.get('used')) if isinstance(v, dict) else None
            elif kind == 'duration':
                value = float(v['duration']) if isinstance(v, dict) and v.get('used')=='yes' and v.get('duration') not in (None,'') else None
            elif kind == 'dimension':
                value = dims.get(item)
            else:
                value = result['total']
            group['values'][start+offset] = value
    for g in groups.values():
        if g['expected'] - g['submitted']:
            g['meta'][3] = '部分问卷未完成'
    rows = [g['meta'] + [g['values'].get(i) for i in range(5,len(headers))] for g in groups.values()]
    warnings.append('每行是一名被试的一次项目作答；单独填写的答卷不自动合并。空白表示缺失、不适用或未计算，不等于0。')
    warnings.append('非计分文本及非计分普通选项不进入分数表。迫选题无量表分值时仅保留1/2选择值（不是分数），其含义写在列名中。不同问卷不相加为跨量表总分。')
    return {'headers': headers, 'rows': rows, 'warnings': warnings}
