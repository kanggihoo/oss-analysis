"""Claude Code 세션 JSONL의 형식 통계만 출력한다 (대화 내용은 출력하지 않음).

사용: python -I inspect_session_log.py <session.jsonl>
claude-devtools 스펙(wiki/capabilities/claude-code-session-log-reading.md)의 근거 확인용.
"""
import collections
import json
import sys

path = sys.argv[1]
types = collections.Counter()
no_uuid = collections.Counter()
malformed = 0
first_cwd_line = None
by_request = collections.defaultdict(list)

for i, line in enumerate(open(path, encoding="utf-8")):
    if not line.strip():
        continue
    try:
        e = json.loads(line)
    except Exception:
        malformed += 1
        continue
    t = e.get("type")
    types[t] += 1
    if not e.get("uuid"):
        no_uuid[t] += 1
    if first_cwd_line is None and e.get("cwd"):
        first_cwd_line = i
    if t == "assistant" and e.get("requestId"):
        m = e["message"]
        u = m.get("usage") or {}
        by_request[e["requestId"]].append(
            (tuple(b.get("type") for b in m.get("content", [])), m.get("id"),
             (u.get("input_tokens"), u.get("output_tokens"), u.get("cache_read_input_tokens")))
        )

multi = {k: v for k, v in by_request.items() if len(v) > 1}
print("types:", dict(types))
print("types without uuid:", dict(no_uuid))
print("malformed lines:", malformed)
print("first line index with cwd:", first_cwd_line)
print("requestIds:", len(by_request), "| with >1 entries:", len(multi),
      "| max entries per requestId:", max((len(v) for v in by_request.values()), default=0))
print("multi-entry requestIds sharing one message.id:", sum(1 for v in multi.values() if len({x[1] for x in v}) == 1))
print("multi-entry requestIds whose entries carry different blocks:", sum(1 for v in multi.values() if len({x[0] for x in v}) > 1))
print("multi-entry requestIds with identical usage on every entry:", sum(1 for v in multi.values() if len({x[2] for x in v}) == 1))
