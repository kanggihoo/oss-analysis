"""~/.claude/projects 전체에서 type=attachment 줄의 하위 type과 prompt_snapshot 보유 세션 비율을 센다.
내용은 출력하지 않는다(길이·키만)."""
import json, glob, os, collections
root = os.path.expanduser('~/.claude/projects')
sub = collections.Counter(); sess = with_snap = 0
snap_keys = collections.Counter(); sp_shape = collections.Counter(); sp_len = []
for f in glob.glob(f'{root}/*/*.jsonl'):
    sess += 1; has = False
    for l in open(f, errors='replace'):
        try: d = json.loads(l)
        except Exception: continue
        if d.get('type') != 'attachment': continue
        a = d.get('attachment') or {}
        sub[a.get('type')] += 1
        if a.get('type') == 'prompt_snapshot':
            has = True; snap_keys.update(a.keys())
            sp = a.get('systemPrompt'); sp_shape[type(sp).__name__] += 1
            sp_len.append(sum(len(x) for x in sp) if isinstance(sp, list) else len(str(sp)))
    with_snap += has
print('sessions', sess, 'with prompt_snapshot', with_snap)
print('attachment subtypes', sub.most_common())
print('prompt_snapshot keys', dict(snap_keys)); print('systemPrompt shape', dict(sp_shape))
if sp_len: print('systemPrompt chars min/max', min(sp_len), max(sp_len))
