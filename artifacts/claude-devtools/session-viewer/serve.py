#!/usr/bin/env python3
"""~/.claude/projects 를 훑어 프로젝트·세션 목록을 보여 주고, 누른 세션을 render_session으로 렌더링하는 로컬 서버.
사용: serve.py [--port 8765] [--root ~/.claude/projects]   → http://127.0.0.1:8765
스펙: reports/claude-devtools/capabilities/claude-code-session-picker.md (worktree 묶기 제외)"""
import argparse, datetime as dt, html, json, os, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_session as rs

e = html.escape
SAFE = re.compile(r'^[\w.-]+$')
CSS = ('body{font:14px/1.5 system-ui;max-width:900px;margin:2em auto;padding:0 1em;background:#fff;color:#222}a{color:#06c;text-decoration:none}'
       'li{margin:.3em 0}.dim{color:#777;font-size:12px}h2{margin-top:1.5em;font-size:14px;color:#777}'
       '@media(prefers-color-scheme:dark){body{background:#181818;color:#ddd}a{color:#6af}}')

def page(title, body): return f'<!doctype html><meta charset="utf-8"><title>{e(title)}</title><style>{CSS}</style>{body}'.encode()

def sessions_of(d):
    out = []
    for n in os.listdir(d):
        if n.endswith('.jsonl') and SAFE.match(n):
            st = os.stat(os.path.join(d, n)); out.append((n[:-6], st.st_mtime, st.st_size))
    return sorted(out, key=lambda x: (-x[1], x[0]))  # 최근순, 같으면 id (picker R-06)

def peek(path, maxlines=300):
    """cwd와 미리보기(첫 실제 user 입력)만 앞쪽에서 찾는다. ponytail: 앞 300줄까지만, 없으면 Untitled"""
    cwd = prev = cmd = None
    for i, l in enumerate(open(path, encoding='utf-8', errors='replace')):
        if i >= maxlines or (cwd and prev): break
        try: d = json.loads(l)
        except Exception: continue  # 깨진 줄은 건너뜀 (reading R-04)
        cwd = cwd or d.get('cwd')
        if d.get('type') == 'user' and not prev and not d.get('isMeta'):
            c = (d.get('message') or {}).get('content')
            t = c if isinstance(c, str) else ''.join(b.get('text', '') for b in c or [] if isinstance(b, dict) and b.get('type') == 'text')
            t = t.strip()
            m = re.search(r'<command-name>(.*?)</command-name>', t, re.S)
            if t.startswith('<command-') and m:  # 슬래시 명령은 /이름 + 인자를 제목으로 (reading R-08 대체값)
                a = re.search(r'<command-args>(.*?)</command-args>', t, re.S)
                cmd = cmd or ' '.join((m.group(1) + ' ' + (a.group(1) if a else '')).split())[:140]
            elif t and not t.startswith(rs.SKIP_USER) and not t.startswith('[Request interrupted'): prev = ' '.join(t.split())[:140]
    return cwd, prev or cmd or 'Untitled'

def group(ts, now):
    d = (now.date() - dt.datetime.fromtimestamp(ts).date()).days
    return 'Today' if d <= 0 else 'Yesterday' if d == 1 else 'Previous 7 Days' if d <= 7 else 'Older'

def ago(ts): return dt.datetime.fromtimestamp(ts).strftime('%m-%d %H:%M')

def index(root):
    rows = []
    for n in os.listdir(root):
        d = os.path.join(root, n)
        if os.path.isdir(d) and SAFE.match(n):
            ss = sessions_of(d)
            if ss: rows.append((ss[0][1], n, len(ss), peek(os.path.join(d, ss[0][0] + '.jsonl'), 50)[0] or n))
    rows.sort(reverse=True)
    li = ''.join(f'<li><a href="/p/{quote(n)}">{e(path)}</a> <span class="dim">세션 {c} · {ago(t)}</span></li>' for t, n, c, path in rows)
    return page('Sessions', f'<h1>프로젝트</h1><ul>{li}</ul>')

def project(root, n):
    d = os.path.join(root, n); now = dt.datetime.now(); g = {}
    for sid, t, size in sessions_of(d):
        title = peek(os.path.join(d, sid + '.jsonl'))[1]
        g.setdefault(group(t, now), []).append(f'<li><a href="/s/{quote(n)}/{quote(sid)}">{e(title)}</a> <span class="dim">{ago(t)} · {size // 1024}KB</span></li>')
    body = ''.join(f'<h2>{k}</h2><ul>{"".join(g[k])}</ul>' for k in ('Today', 'Yesterday', 'Previous 7 Days', 'Older') if k in g)
    return page(n, f'<p><a href="/">← 프로젝트</a></p><h1>{e(n)}</h1>{body}')

def make(root):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = [unquote(x) for x in self.path.split('?')[0].strip('/').split('/')]
            try:
                if parts == ['']: out = index(root)
                elif len(parts) == 2 and parts[0] == 'p' and SAFE.match(parts[1]) and os.path.isdir(os.path.join(root, parts[1])): out = project(root, parts[1])
                elif len(parts) == 3 and parts[0] == 's' and SAFE.match(parts[1]) and SAFE.match(parts[2]) and os.path.isfile(os.path.join(root, parts[1], parts[2] + '.jsonl')):
                    out = rs.render(os.path.join(root, parts[1], parts[2] + '.jsonl')).encode()
                else: return self.send_error(404)
            except Exception as ex:
                return self.send_error(500, str(ex)[:100])
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(out)
        def log_message(self, *a): pass
    return H

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=8765); ap.add_argument('--root', default='~/.claude/projects'); a = ap.parse_args()
    root = os.path.expanduser(a.root)
    print(f'http://127.0.0.1:{a.port}'); ThreadingHTTPServer(('127.0.0.1', a.port), make(root)).serve_forever()  # 127.0.0.1만 연다
