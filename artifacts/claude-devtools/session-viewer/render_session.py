#!/usr/bin/env python3
"""Claude Code 세션 .jsonl -> 자기완결형 HTML. 사용: render_session.py <session.jsonl> [-o out.html]
스펙: reports/claude-devtools/capabilities/claude-code-session-log-reading.md (R-04,R-09,R-11,R-15)
데이터는 HTML에 직접 넣으므로 file://에서 fetch가 필요 없다. 모든 문자열은 html.escape 한다."""
import argparse, collections, html, json, sys

LIMIT = 5000  # ponytail: 긴 tool_result는 앞부분만. 전체가 필요하면 --full
QUIET = {'total_tokens_reminder', 'silent_turn_reminder', 'date'}  # 개수만 표시
SKIP_TYPES = {'file-history-snapshot', 'queue-operation'}
SKIP_USER = ('<local-command-stdout>', '<local-command-stderr>', '<local-command-caveat>', '<system-reminder>')
e = html.escape

def det(summary, body, cls='', open_=False):
    return f'<details class="{cls}"{" open" if open_ else ""}><summary>{summary}</summary>{body}</details>'

def fmt(v, ind=0):
    """dict/list를 JSON 대신 `key: 값` 텍스트로. 여러 줄 문자열은 \\n 없이 실제 줄바꿈으로 보여 준다."""
    pad = '  ' * ind
    def one(k, x):
        head = f'{pad}{k}' if k is not None else f'{pad}-'
        if isinstance(x, (dict, list)) and x: return f'{head}:\n{fmt(x, ind + 1)}' if k is not None else f'{head}\n{fmt(x, ind + 1)}'
        if isinstance(x, str) and '\n' in x: return f'{head}{":" if k is not None else ""}\n' + '\n'.join(pad + '  ' + y for y in x.split('\n'))
        x = x if not isinstance(x, (dict, list)) else ('{}' if isinstance(x, dict) else '[]')
        return f'{head}: {x}' if k is not None else f'{head} {x}'
    if isinstance(v, dict): return '\n'.join(one(k, x) for k, x in v.items())
    if isinstance(v, list): return '\n'.join(one(None, x) for x in v)
    return f'{pad}{v}'

def pre(t, full=False):
    t = t if isinstance(t, str) else fmt(t)
    cut = '' if full or len(t) <= LIMIT else f'\n… ({len(t) - LIMIT}자 생략)'
    return f'<pre>{e(t if full else t[:LIMIT])}{cut}</pre>'

def load(path):
    rows, bad = [], 0
    for l in open(path, encoding='utf-8', errors='replace'):
        if not l.strip(): continue
        try: rows.append(json.loads(l))
        except Exception: bad += 1  # R-04/R-09: 깨진 줄은 건너뛰고 센다
    return rows, bad

def system_section(atts, full):
    out, quiet = [], collections.Counter()
    snaps = [a for a in atts if a.get('type') == 'prompt_snapshot']
    # cliPrefix·tools는 일부 스냅샷에만 있어 처음 나온 값을 합친다
    snap = dict(snaps[0], **{k: next((x[k] for x in snaps if x.get(k)), None) for k in ('cliPrefix', 'tools')}) if snaps else None
    if snap:
        parts = ([snap['cliPrefix']] if snap.get('cliPrefix') else []) + list(snap.get('systemPrompt') or [])
        text = '\n\n'.join(parts)  # 로그의 조각 경계는 구현 세부라 이어 붙여 한 덩어리로 보여 준다
        out.append(det(f'System prompt ({len(text)}자)', pre(text, True), 'sys'))
        tools = snap.get('tools')
        if isinstance(tools, list):
            body = ''.join(det(e(str(t.get('name'))), pre({k: v for k, v in t.items() if k != 'name'}, True)) for t in tools if isinstance(t, dict))
            out.append(det(f'도구 정의 {len(tools)}개', body, 'sys'))
    groups = collections.defaultdict(list)
    for a in atts:
        t = a.get('type')
        if t == 'prompt_snapshot': continue
        if t in QUIET: quiet[t] += 1
        else: groups[t].append(a)
    for t, items in sorted(groups.items()):
        items = [{k: v for k, v in x.items() if k != 'type'} for x in items]
        body = pre(items[0], True) if len(items) == 1 else ''.join(det(str(i + 1), pre(x, True)) for i, x in enumerate(items))
        out.append(det(f'{e(str(t))}' + (f' ×{len(items)}' if len(items) > 1 else ''), body, 'sys'))
    if quiet: out.append(f'<p class="dim">개수만: {e(", ".join(f"{k} {v}" for k, v in quiet.items()))}</p>')
    return ''.join(out)

def blocks(content, results, full):
    if isinstance(content, str): content = [{'type': 'text', 'text': content}]
    out = []
    for b in content:
        t = b.get('type')
        if t == 'text': out.append(f'<div class="text">{e(b.get("text", ""))}</div>')
        elif t == 'thinking': out.append(det('thinking', pre(b.get('thinking', ''), full), 'think'))
        elif t == 'tool_use':
            r = results.get(b.get('id'))
            res = det('결과' + (' (error)' if r and r.get('is_error') else ''), pre(r.get('content') if r else '(결과 없음)', full))
            out.append(det(f'🔧 {e(str(b.get("name")))}', f'<b>input</b>{pre(b.get("input"), full)}{res}', 'tool'))
        elif t == 'image': out.append('<div class="dim">[image]</div>')
        elif t == 'tool_result': pass  # tool_use 쪽에 붙임
        else: out.append(det(f'? {e(str(t))}', pre(b, full)))  # 모르는 블록은 원문 그대로
    return ''.join(out)

def render(path, full=False):
    rows, bad = load(path)
    results = {}
    for d in rows:  # tool_use_id -> tool_result
        c = (d.get('message') or {}).get('content')
        if d.get('type') == 'user' and isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get('type') == 'tool_result': results[b.get('tool_use_id')] = b
    atts = [d['attachment'] for d in rows if d.get('type') == 'attachment' and isinstance(d.get('attachment'), dict)]
    body, last_req = [], None
    for d in rows:
        t, m = d.get('type'), d.get('message') or {}
        side = ' side' if d.get('isSidechain') else ''
        ts = e(str(d.get('timestamp', '')))
        if t == 'assistant':
            rid = d.get('requestId')
            inner = blocks(m.get('content') or [], results, full)
            if rid and rid == last_req and body: body[-1] = body[-1][:-6] + inner + '</div>'  # R-11: 같은 requestId는 한 말풍선
            else: body.append(f'<div class="msg a{side}"><div class="who">assistant · {e(str(m.get("model", "")))} · {ts}</div>{inner}</div>')
            last_req = rid
        elif t == 'user':
            c = m.get('content')
            if isinstance(c, list) and all(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c): continue
            txt = c if isinstance(c, str) else ''.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
            meta = d.get('isMeta') or txt.lstrip().startswith(SKIP_USER)
            inner = blocks(c, results, full)
            body.append(f'<div class="msg u{side}{" meta" if meta else ""}"><div class="who">user{" (meta)" if meta else ""} · {ts}</div>{inner}</div>')
            last_req = None
        elif t == 'system': body.append(f'<p class="dim">system · {e(str(d.get("subtype", "")))} · {e(str(d.get("content", ""))[:300])}</p>')
        elif t == 'summary': body.append(f'<p class="dim">summary: {e(str(d.get("summary", "")))}</p>')
        # 그 밖의 type(attachment 제외)은 R-09대로 건너뜀
    head = f'<h1>{e(path)}</h1><p class="dim">줄 {len(rows)} · 깨진 줄 {bad} · attachment {len(atts)}</p>'
    css = ('body{font:14px/1.5 system-ui;max-width:900px;margin:2em auto;padding:0 1em;background:#fff;color:#222}'
           '.msg{border-radius:8px;padding:.6em 1em;margin:.8em 0}.u{background:#e8f0fe}.a{background:#f4f4f4}.meta{opacity:.55}.side{border-left:4px solid #e90}'
           '.who,.dim{color:#777;font-size:12px}.text{white-space:pre-wrap}pre{white-space:pre-wrap;word-break:break-word;background:#0001;padding:.5em;border-radius:4px;font-size:12px}'
           'details{margin:.3em 0}.tool>summary{color:#06c}.think>summary{color:#888}.sys>summary{color:#a50}'
           '@media(prefers-color-scheme:dark){body{background:#181818;color:#ddd}.u{background:#1c2a44}.a{background:#262626}}')
    return f'<!doctype html><meta charset="utf-8"><title>{e(path)}</title><style>{css}</style>{head}<h2>System / injected</h2>{system_section(atts, full)}<h2>대화</h2>{"".join(body)}'

def _check():
    import tempfile, os
    L = [{'type': 'attachment', 'uuid': 'a0', 'attachment': {'type': 'prompt_snapshot', 'systemPrompt': ['SP<b>']}}, {'type': 'attachment', 'uuid': 'a', 'attachment': {'type': 'prompt_snapshot', 'cliPrefix': 'PFX', 'systemPrompt': ['SP<b>']}},
         {'type': 'user', 'uuid': 'u', 'message': {'content': 'hi <script>'}},
         {'type': 'assistant', 'uuid': 'x1', 'requestId': 'r', 'message': {'content': [{'type': 'tool_use', 'id': 't', 'name': 'Bash', 'input': {'c': 1}}]}},
         {'type': 'assistant', 'uuid': 'x2', 'requestId': 'r', 'message': {'content': [{'type': 'text', 'text': 'done'}]}},
         {'type': 'user', 'uuid': 'u2', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 't', 'content': 'OUT'}]}}]
    p = os.path.join(tempfile.mkdtemp(), 's.jsonl')
    open(p, 'w').write('\n'.join(json.dumps(x) for x in L) + '\n{broken\n')
    h = render(p)
    assert 'PFX' in h and 'SP&lt;b&gt;' in h and '<script>' not in h  # R-15 + 이스케이프
    assert h.count('class="msg a') == 1 and 'OUT' in h and 'done' in h  # R-11 + 결과 연결
    assert '깨진 줄 1' in h  # R-04
    print('check ok')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('jsonl', nargs='?'); ap.add_argument('-o'); ap.add_argument('--full', action='store_true'); ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check: _check(); sys.exit()
    out = a.o or a.jsonl.rsplit('/', 1)[-1].replace('.jsonl', '.html')
    open(out, 'w', encoding='utf-8').write(render(a.jsonl, a.full)); print(out)
