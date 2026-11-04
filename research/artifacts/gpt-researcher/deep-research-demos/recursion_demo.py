"""DeepResearchSkill 의 재귀·동시성·실패·진행 이벤트·최종 컨텍스트를 가짜 LLM/가짜 GPTResearcher로 실행.
실행: python -I artifacts/gpt-researcher/deep-research-demos/recursion_demo.py
실제 코드: deep_research.py 원본(DeepResearchSkill 전체, 파서, trim). 대체물은 모두 _stubs.py 참고:
  - create_chat_completion: 프롬프트 문구를 보고 미리 정한 JSON 문자열을 돌려주는 가짜(원본 프롬프트가 파서까지 그대로 흐름)
  - GPTResearcher: 중첩 연구자 가짜. 공유 visited_urls 집합에 URL을 넣고 정해진 문자열을 돌려줌
  - get_search_results: 항상 고정 결과를 돌려주는 가짜
형식을 보이려는 예시이며, 실제 LLM 응답 품질·실제 연구 파이프라인·비용 계산은 검증하지 않는다.
"""
import asyncio
import ast
import contextlib
import gc
import io
import json
import os
import re
import sys
import warnings
from types import SimpleNamespace

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _stubs

STATE = {}
_DEL = object()


def reset(**kw):
    STATE.clear()
    STATE.update(dict(nested=[], in_flight=0, max_in_flight=0, llm_calls=[], fail_nested=lambda q: False,
                      fail_llm=lambda kind, n: False, ctx_words=3, plan_questions=2, counters={}, kw_example=None,
                      learn_text=lambda q: f"learning about {q}", search_calls=[], nested_return=None))
    STATE.update(kw)


async def fake_chat(messages, **kwargs):
    sys_msg, user = messages[0]["content"], messages[1]["content"]
    n = 0
    if "generating search queries" in sys_msg:
        kind = "queries"
        n = int(re.search(r"generate (\d+) unique search queries", user).group(1))
    elif "analyzing search results" in sys_msg:
        kind = "results"
    else:
        kind = "plan"
    STATE["counters"][kind] = STATE["counters"].get(kind, 0) + 1
    opts = {k: v for k, v in kwargs.items() if k in ("reasoning_effort", "max_tokens", "temperature")}
    STATE["llm_calls"].append((kind, opts, "cost_callback" in kwargs))
    if STATE["fail_llm"](kind, STATE["counters"][kind]):
        raise RuntimeError(f"LLM down ({kind} #{STATE['counters'][kind]})")
    if kind == "queries":
        c = STATE["counters"]["queries"]
        STATE.setdefault("query_prompts", []).append(user.split("Prompt:", 1)[1])
        items = [{"query": f"Q{c}.{i}", "researchGoal": f"goal of Q{c}.{i}"} for i in range(1, n + 1)]
        return json.dumps(items)
    if kind == "plan":
        return json.dumps({"questions": [f"plan question {i}?" for i in range(1, STATE["plan_questions"] + 1)]})
    q = re.search(r"for the query '([^']*)'", user).group(1)
    STATE.setdefault("results_prompts", []).append(user.split("Research results:", 1)[1])
    return json.dumps({"learnings": [{"insight": STATE["learn_text"](q), "sourceUrl": f"https://src.test/{q}"}],
                       "followUpQuestions": [f"follow-up of {q}?"]})


async def fake_search(query, retriever, query_domains=None, researcher=None, max_results=None):
    STATE["search_calls"].append((retriever.__name__, query, max_results))
    if getattr(retriever, "boom", False):
        raise RuntimeError("retriever misconfigured")
    return [{"href": "https://plan.test/1", "body": "snippet"}]


class FakeGPTResearcher:
    def __init__(self, **kw):
        self.kw = kw
        self.query = kw["query"]
        self.visited_urls = kw["visited_urls"] if kw["visited_urls"] is not None else set()
        self.research_sources = []
        STATE["nested"].append(self)
        if STATE["kw_example"] is None:
            STATE["kw_example"] = {k: (type(v).__name__ if k in ("visited_urls", "tone") else v) for k, v in kw.items()}

    async def conduct_research(self):
        STATE["in_flight"] += 1
        STATE["max_in_flight"] = max(STATE["max_in_flight"], STATE["in_flight"])
        try:
            await asyncio.sleep(0.02)
            if STATE["fail_nested"](self.query):
                raise RuntimeError(f"nested research failed for {self.query}")
            self.visited_urls.add(f"https://web.test/{self.query}")
            self.visited_urls.add("https://web.test/shared")
            self.research_sources.append({"url": f"https://web.test/{self.query}"})
            if STATE["nested_return"] is not None:
                return STATE["nested_return"](self.query)
            return " ".join([f"ctx-{self.query}"] + ["w"] * (STATE["ctx_words"] - 1))
        finally:
            STATE["in_flight"] -= 1


def make_outer(**cfg_over):
    class TavilySearch:
        pass

    cfg = SimpleNamespace(strategic_llm_provider="p", strategic_llm_model="m", reasoning_effort="medium", llm_kwargs={},
                          config_path=None, deep_research_breadth=3, deep_research_depth=2, deep_research_concurrency=2)
    for k, v in cfg_over.items():
        if v is _DEL:
            delattr(cfg, k)
        else:
            setattr(cfg, k, v)
    events = []
    outer = SimpleNamespace(query="how does X work", cfg=cfg, websocket=None, tone="tone", headers={"h": 1},
                            visited_urls=set(), research_sources=[], context=[], retrievers=[TavilySearch],
                            mcp_configs=None, mcp_strategy=None, log_handler=object(), cost_calls=[], events=events)
    outer.get_costs = lambda: 0.0
    outer.add_costs = lambda c: outer.cost_calls.append(c)

    async def _log_event(kind, **kw):
        events.append((kind, kw))

    outer._log_event = _log_event
    return outer


dr = _stubs.load(fake_chat, fake_search, FakeGPTResearcher)


def quiet(coro):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            return asyncio.run(coro), buf.getvalue()
        except Exception as e:  # 예외도 값으로 돌려줘 출력한다
            return e, buf.getvalue()


def header(t):
    print("\n" + "=" * 8, t)


RE_LVL = r"DEEP RESEARCH: depth=(\d+), breadth=(\d+)"

# ---------------------------------------------------------------- A. 재귀 구조와 동시성
header("A1. 설정 값 3/2/4(Config 기본값과 같은 값)로 run(): 레벨별 breadth, 중첩 연구자 수, 동시 실행 상한")
reset()
outer = make_outer(deep_research_breadth=3, deep_research_depth=2, deep_research_concurrency=4)
skill = dr.DeepResearchSkill(outer)
print("skill.breadth/depth/concurrency =", skill.breadth, skill.depth, skill.concurrency_limit)
res, out = quiet(skill.run())
print("deep_research() 호출 순서 (depth, breadth):", re.findall(RE_LVL, out))
print("중첩 GPTResearcher 수:", len(STATE["nested"]), "/ 최대 동시 실행:", STATE["max_in_flight"])
print("LLM 호출 종류별 횟수:", STATE["counters"])
print("중첩 연구자 생성 인자 예(첫 번째):", STATE["kw_example"])
print("계획용 검색 호출(retriever, query 앞 20자, max_results):", [(a, b[:20], c) for a, b, c in STATE["search_calls"]])
print("최종 반환 타입:", type(res).__name__, "/ 줄 수:", len(res.split("\n")))
print("최종 컨텍스트 앞 3줄:", res.split("\n")[:3])
print("researcher.visited_urls 타입:", type(outer.visited_urls).__name__, "/ 개수:", len(outer.visited_urls),
      "/ skill.visited_urls(처음 받은 집합):", type(skill.visited_urls).__name__, len(skill.visited_urls))
print("researcher.research_sources 개수:", len(outer.research_sources))
print("비용: outer.add_costs 호출 =", outer.cost_calls, "/ LLM 호출에 cost_callback 전달 여부 집합:", {c for _, _, c in STATE["llm_calls"]})
print("deep_research_costs 로그 details:", [kw["details"] for k, kw in outer.events if kw.get("step") == "deep_research_costs"])
print("질의 생성 프롬프트의 Prompt: 이후 문자열 (1) 최상위, (2) 첫 재귀:", [STATE["query_prompts"][0], STATE["query_prompts"][1]])
print("LLM 호출 옵션(종류, 옵션):", sorted({(k, json.dumps(o, sort_keys=True)) for k, o, _ in STATE["llm_calls"]}))

header("A2. breadth=4, depth=3: 깊이마다 breadth가 max(2, breadth//2)로 줄어든다")
reset()
outer = make_outer(deep_research_breadth=4, deep_research_depth=3, deep_research_concurrency=4)
res, out = quiet(dr.DeepResearchSkill(outer).run())
lv = re.findall(RE_LVL, out)
print("deep_research() 호출 (depth, breadth) 순서(앞 8개):", lv[:8])
cnt = {}
for d, b in lv:
    cnt[f"depth={d},breadth={b}"] = cnt.get(f"depth={d},breadth={b}", 0) + 1
print("레벨별 deep_research() 호출 수:", cnt)
print("중첩 GPTResearcher 수:", len(STATE["nested"]), "(4 + 4*2 + 4*2*2 = 28 이면 규칙과 일치)")

header("A3. depth=1: 재귀 없음")
reset()
outer = make_outer(deep_research_breadth=3, deep_research_depth=1, deep_research_concurrency=4)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("중첩 GPTResearcher 수:", len(STATE["nested"]), "/ deep_research 호출:", re.findall(RE_LVL, out))

header("A4. 동시 실행 상한(세마포어)")
reset()
outer = make_outer(deep_research_breadth=3, deep_research_depth=1, deep_research_concurrency=1)
quiet(dr.DeepResearchSkill(outer).run())
print("breadth=3 depth=1 concurrency=1 -> 최대 동시 실행:", STATE["max_in_flight"])
reset()
outer = make_outer(deep_research_breadth=3, deep_research_depth=1, deep_research_concurrency=2)
quiet(dr.DeepResearchSkill(outer).run())
print("breadth=3 depth=1 concurrency=2 -> 최대 동시 실행:", STATE["max_in_flight"])
reset()
outer = make_outer(deep_research_breadth=3, deep_research_depth=2, deep_research_concurrency=3)
quiet(dr.DeepResearchSkill(outer).run())
print("breadth=3 depth=2 concurrency=3 -> 최대 동시 실행:", STATE["max_in_flight"], "(최상위 레벨 3개가 동시에 돈다. 자식 레벨은 형제 결과마다 순차로 재귀한다)")

# ---------------------------------------------------------------- B. 기본값
header("B. getattr 기본값(4/2/2) 대 설정 객체 값")
o = make_outer(deep_research_breadth=_DEL, deep_research_depth=_DEL, deep_research_concurrency=_DEL)
s = dr.DeepResearchSkill(o)
print("cfg에 deep_research_* 속성이 없을 때: breadth/depth/concurrency =", s.breadth, s.depth, s.concurrency_limit)
src = open(os.path.join(_stubs.PKG, "config", "variables", "default.py"), encoding="utf-8").read()
tree = ast.parse(src)
node = [n for n in tree.body if isinstance(n, ast.AnnAssign) and n.target.id == "DEFAULT_CONFIG"][0]
d = ast.literal_eval(node.value)
print("default.py DEFAULT_CONFIG(원본 파일을 ast로 읽음):", {k: v for k, v in d.items() if k.startswith("DEEP_RESEARCH")})

# ---------------------------------------------------------------- C. 실패
header("C1. 일부 중첩 연구가 실패: 그 질의만 버리고 계속")
reset(fail_nested=lambda q: q == "Q1.2")
outer = make_outer(deep_research_breadth=3, deep_research_depth=1, deep_research_concurrency=4)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("최종 컨텍스트에 Q1.2 포함?", "Q1.2" in res, "/ Q1.1 포함?", "Q1.1" in res, "/ 생성된 중첩 연구자:", len(STATE["nested"]))

header("C2. 한 레벨의 모든 질의가 실패하면 그 레벨에서 중단(#1579): depth=3이어도 재귀하지 않음")
reset(fail_nested=lambda q: True)
outer = make_outer(deep_research_breadth=2, deep_research_depth=3, deep_research_concurrency=2)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("run 반환:", repr(res), "/ 중첩 연구자:", len(STATE["nested"]), "/ outer.context:", repr(outer.context),
      "/ deep_research 호출 수:", len(re.findall("DEEP RESEARCH: depth", out)))
print("조기 종료 시 outer.visited_urls:", type(outer.visited_urls).__name__, len(outer.visited_urls))
reset(fail_llm=lambda k, n: k == "results")
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=2)
sk = dr.DeepResearchSkill(outer)
res, out = quiet(sk.run())
print("C2b. 중첩 연구는 성공했지만 학습 추출 LLM이 전부 실패: 공유 집합에는 URL", len(sk.visited_urls), "개가 있지만 run 뒤 outer.visited_urls =",
      type(outer.visited_urls).__name__, len(outer.visited_urls), "/ 같은 객체인가:", outer.visited_urls is sk.visited_urls, "/ run 반환:", repr(res))

header("C3. process_research_results(LLM)가 실패하면 그 질의만 버림")
reset(fail_llm=lambda k, n: k == "results" and n == 1)
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=1)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("LLM 호출:", STATE["counters"], "/ 결과의 [Source:] 학습 줄 수:", len([ln for ln in res.split("\n") if "[Source:" in ln]))

header("C4. 깊은 레벨의 질의 생성 LLM이 실패하면 예외가 run 밖으로 나가고, 지금까지 얻은 결과는 outer에 반영되지 않음")
reset(fail_llm=lambda k, n: k == "queries" and n == 2)
outer = make_outer(deep_research_breadth=2, deep_research_depth=2, deep_research_concurrency=2)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("run 결과:", type(res).__name__, res)
print("outer.context:", repr(outer.context), "/ outer.research_sources:", outer.research_sources,
      "/ outer.visited_urls(공유 집합이라 부분적으로 채워짐):", len(outer.visited_urls), type(outer.visited_urls).__name__)
print("중첩 연구자 수(첫 레벨 완료 뒤 중단):", len(STATE["nested"]))

header("C5. 계획 단계: retriever 예외는 개별로 삼킴, 질문 0개여도 진행, 최상위 질의 0개면 빈 컨텍스트")
reset(plan_questions=0)
outer = make_outer()
outer.retrievers[0].boom = True


class DuckSearch:
    pass


outer.retrievers.append(DuckSearch)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("계획 검색 호출:", STATE["search_calls"][:2], "/ run 반환 타입:", type(res).__name__, "/ 질문 0개여도 중첩 연구 실행:", len(STATE["nested"]) > 0)
reset()


async def zero_queries(query, num_queries=3):
    return []


outer = make_outer()
sk = dr.DeepResearchSkill(outer)
sk.generate_search_queries = zero_queries
res, out = quiet(sk.run())
print("질의 0개: run 반환:", repr(res), "/ 중첩 연구자:", len(STATE["nested"]), "/ outer.context:", repr(outer.context), "/ outer.visited_urls:", type(outer.visited_urls).__name__)

# ---------------------------------------------------------------- D. 중복, 트림
header("D1. 중복: 같은 학습 텍스트는 한 번만, citation은 나중 것 / URL은 집합이라 중복 없음")
reset(learn_text=lambda q: "same learning")
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=1)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("학습 줄:", [ln for ln in res.split("\n") if "same learning" in ln])
print("visited_urls 중복 없음?", len(outer.visited_urls) == len(set(outer.visited_urls)), sorted(outer.visited_urls))

header("D2. 컨텍스트가 25,000단어를 넘으면 앞쪽 항목부터 버림 (deep_research 호출 끝의 trim, 그리고 run 끝의 trim)")
reset(ctx_words=12000)
outer = make_outer(deep_research_breadth=3, deep_research_depth=1, deep_research_concurrency=3)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("중첩 연구 3개 x 12000단어: 최종 단어 수:", len(res.split()), "/ 남은 컨텍스트 항목:", re.findall(r"ctx-Q[\d.]+", res),
      "/ 학습 줄([Source:]) 수:", res.count("[Source:"), "(deep_research 끝의 trim이 앞의 ctx-Q1.1을 버렸다)")

header("D3. run 끝의 trim은 학습 줄이 맨 앞이라 먼저 버려진다 (컨텍스트 2개 x 12498단어 + 학습 줄 2개(줄당 5단어) = 25006단어)")
reset(ctx_words=12498)
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=2)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("최종 단어 수:", len(res.split()), "/ 남은 컨텍스트 항목:", re.findall(r"ctx-Q[\d.]+", res), "/ 학습 줄 수:", res.count("[Source:"),
      "/ 학습 줄이 하나라도 남았나?:", "learning about" in res)

# ---------------------------------------------------------------- E. 진행 이벤트
header("E. on_progress 이벤트 (breadth=2, depth=2, concurrency=1). 같은 객체가 변하므로 호출 시점 값을 복사해 기록")
reset()
events = []
ids = {}


def cb(p):
    key = ids.setdefault(id(p), f"P{len(ids)}")
    events.append((key, p.current_depth, p.total_depth, p.current_breadth, p.total_breadth,
                   p.completed_queries, p.total_queries, p.current_query))


outer = make_outer(deep_research_breadth=2, deep_research_depth=2, deep_research_concurrency=1)
res, out = quiet(dr.DeepResearchSkill(outer).run(on_progress=cb))
print("(객체, cur_depth, total_depth, cur_breadth, total_breadth, completed, total_queries, current_query)")
for e in events[:16]:
    print("  ", e)
print("  ... 총 이벤트 수:", len(events), "/ 서로 다른 ResearchProgress 객체:", len(ids))


async def acb(p):
    pass


reset()
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=1)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    res, out = quiet(dr.DeepResearchSkill(outer).run(on_progress=acb))
    gc.collect()
print("async 콜백을 넘기면 await되지 않음 -> 'never awaited' 경고 수:", len([x for x in w if "never awaited" in str(x.message)]),
      "/ run은 정상 완료:", isinstance(res, str))

# ---------------------------------------------------------------- F, G
header("F. on_progress 콜백이 예외를 던질 때: 질의 처리 안(시작·완료 알림)이면 그 질의만 버려지고, 레벨 시작/끝 알림이면 전파")
reset()
n = {"i": 0}


def bad_cb_inner(p):
    n["i"] += 1
    if p.current_query == "Q1.1" and p.completed_queries == 0:
        raise ValueError("callback boom")


outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=1)
res, out = quiet(dr.DeepResearchSkill(outer).run(on_progress=bad_cb_inner))
print("질의 시작 알림에서 예외 -> run 결과 타입:", type(res).__name__, "/ Q1.1 포함?", "Q1.1" in res, "/ Q1.2 포함?", "Q1.2" in res)
reset()


def bad_cb_first(p):
    raise ValueError("callback boom at level start")


outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=1)
res, out = quiet(dr.DeepResearchSkill(outer).run(on_progress=bad_cb_first))
print("레벨 시작 알림에서 예외 -> run 결과:", type(res).__name__, res)

header("G. 중첩 연구가 빈 결과([])를 돌려줘도 학습 추출 LLM을 부르고, 그 프롬프트에는 '[]'가 들어간다")
reset(nested_return=lambda q: [])
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=1)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("results LLM 호출 수:", STATE["counters"].get("results"), "/ 프롬프트의 Research results: 이후:", repr(STATE["results_prompts"][0]))
print("run 반환(학습 줄은 LLM이 낸 것):", res.split("\n"))

# ---------------------------------------------------------------- H. 경계 값
header("H. 설정 값 경계: breadth=1, depth=0, concurrency=0 / -1 (값 검증이 없음)")
reset()
outer = make_outer(deep_research_breadth=1, deep_research_depth=2, deep_research_concurrency=2)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("breadth=1, depth=2 -> deep_research() 호출 (depth, breadth):", re.findall(RE_LVL, out), "/ 중첩 연구자:", len(STATE["nested"]), "(자식 breadth는 max(2, 1//2)=2)")
reset()
outer = make_outer(deep_research_breadth=2, deep_research_depth=0, deep_research_concurrency=2)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("depth=0 -> 한 레벨은 실행:", re.findall(RE_LVL, out), "/ 중첩 연구자:", len(STATE["nested"]))
reset()
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=0)
res, out = quiet(asyncio.wait_for(dr.DeepResearchSkill(outer).run(), timeout=1.0))
print("concurrency=0 -> 1초 안에 끝나지 않음:", type(res).__name__, "/ 중첩 연구자 생성 수:", len(STATE["nested"]))
reset()
outer = make_outer(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=-1)
res, out = quiet(dr.DeepResearchSkill(outer).run())
print("concurrency=-1 ->", type(res).__name__, res)
