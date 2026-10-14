"""Read horizontal text and ordinary Word questionnaire tables, offline."""
import io
import math
import re
from zipfile import ZipFile, BadZipFile
from xml.etree import ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
MODES = {'auto', 'mixed', 'forced', 'matrix', 'form', 'independent'}
NUMBER = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$')

def question(title, options=None):
    return {'title': title.strip(), 'type': 'single' if options else 'text',
            'required': True, 'scoring': 'none', 'options': options or []}

def option(text):
    text = re.sub(r'^[A-Za-z][.．、)）]\s*', '', text.strip())
    match = re.match(r'^(.*?)\s*[=＝]\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*$', text)
    if match:
        return {'label': match[1].strip(), 'score': float(match[2])}, True
    return {'label': text, 'score': 0}, False

def options_from(cells):
    parsed = [option(c) for c in cells]
    if any(not o['label'] for o, _ in parsed):
        raise ValueError('选项内容不能为空')
    if any(scored for _, scored in parsed) and not all(scored for _, scored in parsed):
        raise ValueError('同一题的选项应全部标分或全部不标分')
    return [o for o, _ in parsed], all(scored for _, scored in parsed)

def numeric(text):
    return bool(NUMBER.fullmatch(text)) and math.isfinite(float(text))

def forced_rows(rows):
    """Accept a numbered three-column body, with at most one heading row."""
    body = rows if rows and rows[0][0].isdigit() else rows[1:]
    if not body or any(len(row) != 3 or not row[0].isdigit() or not all(row[1:]) for row in body):
        return None
    numbers = [int(row[0]) for row in body]
    if numbers != list(range(numbers[0], numbers[0]+len(numbers))):
        return None
    return body

class Importer:
    def __init__(self, title):
        self.surveys = []
        self.warnings = []
        self.current = None
        self.default_title = title
        self.header = None
        self.common = None

    def section(self, title, description=''):
        self.current = {'title': title, 'description': description, 'questions': [], 'scoreVersion': 2, 'scoreMode': 'raw' if 'MCQ' in title or '货币选择' in title else 'auto', 'totalMethod': 'sum', 'dimensions': []}
        self.surveys.append(self.current)
        self.header = self.common = None

    def ensure(self):
        if self.current is None:
            self.section(self.default_title)

    def add(self, q):
        self.ensure()
        q['id'] = f'import_{len(self.surveys)}_{len(self.current["questions"])+1}'
        if q['type'] == 'forced':
            q['required'] = True
            if len(q['options']) < 2:
                raise ValueError('迫选题至少需要两个选项：' + q['title'])
        self.current['questions'].append(q)

    def paragraph(self, text):
        text = text.strip()
        if not text:
            return
        match = re.match(r'^【(.+?)】\s*(.*)$', text)
        if match:
            self.section(match[1], match[2])
        elif re.match(r'^标题[:：]', text):
            self.section(re.sub(r'^标题[:：]\s*', '', text))
        elif re.match(r'^(说明|指导语)[:：]', text):
            self.ensure()
            self.current['description'] += ('\n' if self.current['description'] else '') + text
        elif self.current and not self.current['questions']:
            self.current['description'] += ('\n' if self.current['description'] else '') + text
        else:
            self.warnings.append('未作为题目导入的段落：' + text)

    def matrix_row(self, cells):
        if len(cells) != len(self.header):
            raise ValueError('选项列数与表头不一致：' + cells[0])
        labels = self.header[1:]
        values = cells[1:]
        if all(numeric(v) for v in values):
            q = question(cells[0], [{'label': l, 'score': float(v)} for l, v in zip(labels, values)])
            q['scoring'] = 'custom'
        elif all(not v or v in ('□', '☐', '○') for v in values):
            opts, scored = options_from(labels)
            q = question(cells[0], opts)
            q['scoring'] = 'custom' if scored else 'none'
        else:
            raise ValueError('分值行包含无法识别的内容：' + cells[0])
        self.add(q)
        if '几天' in q['title'] and any('频繁' in label for label in labels):
            self.warnings.append('题目与选项含义可能不一致，已原样保留，请核对：' + q['title'])

    def table(self, rows, mode='auto', merged_answers=None):
        if mode not in MODES:
            raise ValueError('未知导入结构类型')
        if mode == 'mixed':
            mode = 'auto'
        rows = [r for r in rows if any(r)]
        if not rows:
            return
        self.ensure()
        if mode == 'independent':
            if rows[0][0] in ('题目', '问题', '题号'):
                rows = rows[1:]
            for row in rows:
                if not row[0]:
                    raise ValueError('缺少题目内容')
                cells = list(row[1:])
                while cells and not cells[-1]:
                    cells.pop()
                opts, scored = options_from(cells) if cells else ([], False)
                q = question(row[0], opts)
                q['scoring'] = 'custom' if scored else 'none'
                self.add(q)
            return 'independent'
        if mode == 'form' and any(len(r) != 2 for r in rows):
            raise ValueError('基础信息表需要两列：项目名称和填写内容或选项。')
        numbered = forced_rows(rows)
        if mode == 'forced':
            body = rows if rows[0][0].isdigit() else rows[1:]
            numbers = [int(r[0]) for r in body if r[0].isdigit()]
            if body and len(numbers) == len(body) and numbers == list(range(numbers[0], numbers[0]+len(numbers))) and all(len(r) >= 3 and all(r[1:]) for r in body):
                numbered = body
        if mode == 'auto' and numbered and any(numeric(c) for row in numbered for c in row[1:]):
            raise ValueError('题号后的内容含纯数字，无法确定是选项还是分值，请手动选择读取方式。')
        if mode == 'forced' or (mode == 'auto' and numbered and all(not numeric(c) for row in numbered for c in row[1:])):
            if not numbered:
                raise ValueError('迫选题需为连续题号＋至少两个非空选项，可带一行表头。请检查题号与空白选项。')
            for row in numbered:
                number, left, right = row[:3]
                q = question('你更愿意选择哪种奖励方式？' if '获得' in left and '获得' in right else '请按要求选择',
                             [{'label': value, 'score': 0} for value in row[1:]])
                q.update(type='forced', required=True, sourceNumber=number)
                immediate = re.fullmatch(r'立即获得(\d+(?:\.\d+)?)(美元|元人民币|人民币|元)', left)
                delayed = re.fullmatch(r'(\d+)天后获得(\d+(?:\.\d+)?)(美元|元人民币|人民币|元)', right)
                if len(row) == 3 and immediate and delayed and immediate[2] == delayed[3]:
                    q['choiceAttributes'] = {'immediateAmount': float(immediate[1]), 'delayedAmount': float(delayed[2]),
                                             'delayDays': int(delayed[1]), 'currency': immediate[2]}
                self.add(q)
            self.current['scoreMode'] = 'raw'
            return 'forced'
        first = rows[0]
        if mode == 'matrix' or (mode == 'auto' and len(first) >= 3 and all(first[1:])):
            if len(first) < 3 or not all(first[1:]):
                raise ValueError('共用选项量表需要完整的选项表头，不能使用合并的标题作为选项。')
            self.header = first
            for index, row in enumerate(rows[1:], 1):
                if index in (merged_answers or set()):
                    self.add(question(row[0]))
                    self.warnings.append('合并的空白作答区按文本题保留，请核对：'+row[0])
                else:
                    self.matrix_row(row)
            self.header = None
            return 'matrix'
        if all(len(r) == 2 for r in rows):
            # Two-column forms: preserve free text instead of inventing numeric bounds.
            unit = ''
            group_title = ''
            group_id = f'group_{len(self.surveys)}_{len(self.current["questions"])+1}'
            if first[1] and ('时长' in first[1] or '单位' in first[1]):
                self.current['description'] += '\n' + first[0]
                unit = first[1]
                group_title = first[0]
                rows = rows[1:]
            elif first[0] in ('项目', '题目', '问题') and first[1] in ('内容', '填写内容', '选项', '回答'):
                rows = rows[1:]
            for label, value in rows:
                if unit and '时长' in unit:
                    category = re.sub(r'^[a-zA-Z][.．、]\s*', '', label)
                    category = re.split(r'[（(]', category, maxsplit=1)[0].strip()
                    q = question(category)
                    q.update(type='substance', unit='年', scoring='none', groupId=group_id, groupTitle=group_title or '物质使用')
                    self.add(q)
                    continue
                title = label + (' — ' + unit if unit else '')
                inline = re.match(r'^(.*?)[（(]([^()（）]*[、,，][^()（）]*)[）)]$', label)
                choices = value if value and '、' in value else inline[2] if inline else ''
                if choices:
                    opts, _ = options_from(re.split('[、,，]', choices))
                    self.add(question(inline[1] if inline else title, opts))
                else:
                    self.add(question(title + ('（' + value + '）' if value else '')))
            self.warnings.append('双列表单按文本题／明确选项导入，默认必填且不计分；请核对题型与必填设置。')
            return 'form'
        raise ValueError('暂不支持该表格结构，请使用横排文本整理后导入。')

    def finish(self):
        surveys = [s for s in self.surveys if s['questions']]
        if not surveys:
            raise ValueError('未识别到题目。请包含表头和题目行，或使用横排模板。')
        self.warnings.insert(0, '默认必填；只采用明确分值，不推断反向题、维度或专业量表算法。未标分的题目不计分。请在编辑器核对后保存。')
        return {'surveys': surveys, 'warnings': list(dict.fromkeys(self.warnings))}

def parse_docx(data, title='导入问卷', overrides=None, mode='auto'):
    if mode not in MODES:
        raise ValueError('未知导入结构类型')
    reader = Importer(title)
    tables, errors = [], []
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
    except (BadZipFile, KeyError, ET.ParseError) as error:
        raise ValueError('无法读取 DOCX，请选择有效的 Word .docx 文件') from error
    def text(node):
        return ''.join(n.text or '' for n in node.findall('.//w:t', NS)).strip()
    for block in root.find('w:body', NS):
        if block.tag.endswith('}p'):
            reader.paragraph(text(block))
        elif block.tag.endswith('}tbl'):
            rows, merged = [], set()
            for index, row in enumerate(block.findall('w:tr', NS)):
                cells = row.findall('w:tc', NS)
                rows.append([' '.join(text(p) for p in cell.findall('w:p', NS)).strip() for cell in cells])
                if len(cells) == 2 and not rows[-1][1]:
                    span = cells[1].find('w:tcPr/w:gridSpan', NS)
                    if span is not None and int(span.get('{'+NS['w']+'}val', '1')) > 1:
                        merged.add(index)
            reader.ensure()
            table_id = str(len(tables))
            table_mode = (overrides or {}).get(table_id, mode)
            start = len(reader.current['questions'])
            info = {'id': table_id, 'title': reader.current['title'], 'mode': table_mode, 'preview': rows[:3]}
            try:
                info['detected'] = reader.table(rows, table_mode, merged)
                info['count'] = len(reader.current['questions'])-start
            except ValueError as error:
                del reader.current['questions'][start:]
                info.update(detected='unknown', error=str(error), count=0)
                errors.append(f'表格 {int(table_id)+1}（{reader.current["title"]}）：{error}')
            tables.append(info)
    result = reader.finish() if any(s['questions'] for s in reader.surveys) else {'surveys': [], 'warnings': []}
    if not tables and not result['surveys']:
        raise ValueError('未找到可读取的问卷表格')
    result.update(tables=tables, errors=errors)
    return result


def parse_text(text, title='粘贴导入的问卷', mode='auto'):
    if mode not in MODES:
        raise ValueError('未知导入结构类型')
    reader = Importer(title)
    if mode != 'auto':
        pending = []
        def flush():
            if pending:
                reader.table(pending, 'auto' if mode == 'mixed' else mode)
                pending.clear()
        for raw in text.lstrip('\ufeff').splitlines():
            line = raw.strip()
            if not line and mode == 'mixed':
                flush()
            if not line or line.startswith('#'):
                continue
            if re.match(r'^(【|标题[:：]|说明[:：]|指导语[:：])', line):
                flush()
                reader.paragraph(line)
            else:
                pending.append([c.strip() for c in re.split(r'\t|[|｜]', raw)])
        flush()
        result = reader.finish()
        result['readingLabel'] = {'forced': '迫选题表格', 'matrix': '共用选项量表', 'form': '基础信息表', 'independent': '逐题独立选项', 'mixed': '混合问卷'}[mode]
        return result
    rows = [[c.strip() for c in re.split(r'\t|[|｜]', line)] for line in text.lstrip('\ufeff').splitlines() if line.strip() and not line.startswith('#')]
    numbered = forced_rows(rows)
    if numbered:
        detected = reader.table(rows, mode)
        result = reader.finish()
        result['readingLabel'] = '迫选题表格' if detected == 'forced' else '共用选项量表'
        return result
    for line_no, raw in enumerate(text.lstrip('\ufeff').splitlines(), 1):
        if not raw.strip():
            continue
        line = raw.strip()
        if line.startswith('#'):
            continue
        if re.match(r'^(【|标题[:：]|说明[:：]|指导语[:：])', line):
            reader.paragraph(line)
            continue
        if re.match(r'^选项[:：]', line):
            reader.common = options_from(re.split(r'\t|[|｜]', re.sub(r'^选项[:：]\s*', '', line)))
            reader.header = None
            continue
        # Preserve initial/trailing empty Word cells; only trim individual cells.
        cells = [c.strip() for c in re.split(r'\t|[|｜]', raw)]
        if len(cells) == 1:
            cells = [c.strip() for c in re.split(r'\s+(?=[A-Za-z][.．、)）])', line)]
        first = cells[0]
        if len(cells) >= 3 and (first in ('', '题目', '状态描述', '选择奖励方式') or first == '问题'):
            reader.header = cells
            continue
        if reader.header:
            if len(cells) == 1:
                reader.warnings.append(f'第 {line_no} 行未导入（非表格行）：{line}')
            else:
                reader.matrix_row(cells)
            continue
        mode = None
        qtype = 'single'
        required = True
        for tag in re.findall(r'[\[【](单选|多选|迫选|文本|物质使用|选填|必填|正向|反向|不计分)[\]】]', first):
            first = re.sub(r'[\[【]' + tag + r'[\]】]', '', first).strip()
            if tag in ('单选', '多选', '迫选', '文本', '物质使用'):
                qtype = {'单选': 'single', '多选': 'multi', '迫选': 'forced', '文本': 'text', '物质使用': 'substance'}[tag]
            elif tag in ('必填', '选填'):
                required = tag == '必填'
            else:
                mode = tag
        try:
            if qtype in ('text', 'substance'):
                opts, scored = [], False
            elif len(cells) > 1:
                opts, scored = options_from(cells[1:])
            elif reader.common:
                opts, scored = reader.common
                opts = [dict(o) for o in opts]
            else:
                raise ValueError('未找到选项；文本题请在题目前标 [文本]')
            q = question(first, opts)
            q.update(type=qtype, required=required, scoring='custom' if scored else 'none')
            if mode in ('正向', '反向') and opts:
                values = [o['score'] for o in opts] if scored else list(range(1, len(opts)+1))
                for o, value in zip(opts, values):
                    o['score'] = value
                q['scoring'] = 'custom'
                q['reverse'] = mode == '反向'
            elif mode == '不计分' or qtype in ('text', 'substance'):
                q['scoring'] = 'none'
            if not first:
                raise ValueError('缺少题目内容')
            reader.add(q)
        except ValueError as error:
            raise ValueError(f'第 {line_no} 行：{error}') from error
    return reader.finish()


if __name__ == '__main__':
    # Direct execution opens the same workspace as the normal launcher.
    import runpy
    from pathlib import Path
    print('正在启动问卷工作台。请在网页中点击「导入问卷」→「选择文件」。', flush=True)
    runpy.run_path(str(Path(__file__).with_name('server.py')), run_name='__main__')
