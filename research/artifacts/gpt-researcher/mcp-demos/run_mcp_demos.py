# -*- coding: utf-8 -*-
"""MCP 연동 스펙(reports/gpt-researcher/capabilities/mcp-client.md) 오프라인 실행 확인.

방식: repos/gpt-researcher 의 소스 줄 범위를 읽어 그대로 exec 한다. 패키지를 import하지 않고(langchain-mcp-adapters,
json_repair 등이 이 환경에 없다), 네트워크·LLM·MCP 서버도 쓰지 않는다. 대체한 부분은 각 섹션 머리말에 적었다.
- 실제 코드(줄 범위를 그대로 실행): MCPClientManager 전체(client.py), _process_tool_result, conduct_research_with_tools,
  select_relevant_tools, _fallback_tool_selection, MCPRetriever.search/search_async/_get_all_tools, PromptFamily의 MCP 프롬프트,
  _resolve_mcp_strategy, _process_mcp_configs, ResearchConductor의 MCP 관련 메서드, get_search_results,
  plan_research_outline, get_retriever/get_retrievers.
- 대체물(형식을 보이려는 가짜): MCP 서버·MultiServerMCPClient, LLM, 도구 객체, 검색 retriever 클래스, stream_output,
  generate_sub_queries, 스크랩(`_scrape_data_by_urls`), 컨텍스트 선별(`get_similar_content_by_query`), json_repair(→json.loads).
"""
import asyncio
import json
import logging
import re
import sys
import time
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[3] / "repos" / "gpt-researcher"
PKG = "gpt_researcher"

FAILS = []


def src(rel, a, b, sub=()):
    """repos/gpt-researcher/<rel> 의 a~b줄(1-based, 포함)을 문자열로. sub=[(정규식, 치환)]."""
    lines = (REPO / rel).read_text(encoding="utf-8").splitlines()[a - 1:b]
    text = "\n".join(lines)
    for pat, rep in sub:
        text = re.sub(pat, rep, text, flags=re.M)
    return text


def make_class(name, chunks, g):
    body = "from __future__ import annotations\nclass %s:\n" % name + "\n\n".join(chunks) + "\n"
    ns = dict(g)
    exec(compile(body, "<%s>" % name, "exec"), ns)
    return ns[name]


def check(label, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + label + (("  -> " + str(detail)) if detail != "" else ""))
    if not cond:
        FAILS.append(label)


def section(title):
    print("\n=== " + title + " ===")


logging.basicConfig(level=logging.CRITICAL)
LOG = logging.getLogger("demo")
BASE_G = dict(asyncio=asyncio, logging=logging, json=json, time=time, urlsplit=urlsplit, Any=Any, Dict=Dict,
              List=List, Optional=Optional, logger=LOG)

print("MCP demos | repo SHA 3582a6841fe7dc801e2a34e34ee408641aea9bce | run date 2026-10-22 | python %s" % sys.version.split()[0])

# ---------------------------------------------------------------------------------------------
section("A. 미설치 동작: 실제 파일을 그대로 exec (이 환경에는 langchain_mcp_adapters 가 없다)")
try:
    import langchain_mcp_adapters  # noqa
    ADAPTERS = True
except ImportError:
    ADAPTERS = False
print("  langchain_mcp_adapters importable:", ADAPTERS)

ns_client = dict(BASE_G, __name__="client_demo")
exec(compile(src("gpt_researcher/mcp/client.py", 1, 192), "<mcp/client.py>", "exec"), ns_client)
check("client.py: HAS_MCP_ADAPTERS == False 로 import 성공", ns_client["HAS_MCP_ADAPTERS"] is False)

ns_mcp_init = dict(BASE_G, __name__="gpt_researcher.mcp")
exec(compile(src("gpt_researcher/mcp/__init__.py", 1, 42), "<mcp/__init__.py>", "exec"), ns_mcp_init)
check("mcp/__init__.py: HAS_MCP_ADAPTERS False, __all__ == ['HAS_MCP_ADAPTERS']",
      ns_mcp_init["HAS_MCP_ADAPTERS"] is False and ns_mcp_init["__all__"] == ["HAS_MCP_ADAPTERS"], ns_mcp_init["__all__"])

ns_ret_init = dict(BASE_G, __name__="gpt_researcher.retrievers.mcp")
exec(compile(src("gpt_researcher/retrievers/mcp/__init__.py", 1, 32), "<retrievers/mcp/__init__.py>", "exec"), ns_ret_init)
check("retrievers/mcp/__init__.py: MCPRetriever is None", ns_ret_init["MCPRetriever"] is None)

# get_retriever / get_retrievers 실제 소스 + 가짜 retrievers 패키지(MCPRetriever=None, 위에서 실제로 얻은 값)
fake_retrievers = types.ModuleType("gpt_researcher.retrievers")


class TavilySearch:  # 가짜 Tavily
    pass


fake_retrievers.TavilySearch = TavilySearch
fake_retrievers.MCPRetriever = ns_ret_init["MCPRetriever"]
sys.modules["gpt_researcher"] = types.ModuleType("gpt_researcher")
sys.modules["gpt_researcher.retrievers"] = fake_retrievers
ns_ar = dict(BASE_G, entry_points=lambda **k: [], RETRIEVER_ENTRY_POINT_GROUP="g")
exec(compile("from __future__ import annotations\n" + src("gpt_researcher/actions/retriever.py", 16, 204), "<actions/retriever.py>", "exec"), ns_ar)
res = ns_ar["get_retrievers"]({}, SimpleNamespace(retrievers=["tavily", "mcp"], retriever=None))
check("MCPRetriever=None 이면 retrievers=['tavily','mcp'] 는 [Tavily, Tavily] (mcp가 조용히 Tavily로 대체)",
      res == [TavilySearch, TavilySearch], [c.__name__ for c in res])
res = ns_ar["get_retrievers"]({"retrievers": "tavily"}, SimpleNamespace(retrievers=["tavily", "mcp"], retriever=None))
check("헤더 retrievers 가 있으면 cfg.retrievers(mcp 포함)는 읽히지 않는다", res == [TavilySearch], [c.__name__ for c in res])

# MCPClientManager 미설치 경로
CM = ns_client["MCPClientManager"]


async def part_a_client():
    m = CM([{"name": "s", "command": "x"}])
    c = await m.get_or_create_client()
    check("미설치: get_or_create_client() -> None", c is None)
    check("미설치: get_all_tools() -> []", await m.get_all_tools() == [])
    m2 = CM([])
    ns_client["HAS_MCP_ADAPTERS"] = True  # 설치된 것으로 가정(가짜 클라이언트)

    class FakeClient:
        made = 0

        def __init__(self, cfg):
            FakeClient.made += 1
            self.cfg = cfg
            self.fail = False

        async def get_tools(self):
            if self.fail:
                raise RuntimeError("server spawn failed")
            return ["t1", "t2"]

    ns_client["MultiServerMCPClient"] = FakeClient
    check("설치+설정 없음: get_or_create_client() -> None", await m2.get_or_create_client() is None)
    m3 = CM([{"name": "s", "command": "x"}])
    c1 = await m3.get_or_create_client()
    c2 = await m3.get_or_create_client()
    check("설치+설정 있음: 클라이언트는 한 번만 만들고 캐시한다", c1 is c2 and FakeClient.made == 1, FakeClient.made)
    check("get_all_tools 정상: 도구 목록 반환", await m3.get_all_tools() == ["t1", "t2"])
    c1.fail = True
    check("get_tools 예외는 삼키고 []", await m3.get_all_tools() == [])
    await m3.close_client()
    check("close_client 뒤 _client is None (참조만 버림)", m3._client is None)
    c3 = await m3.get_or_create_client()
    check("close 뒤 다시 get_or_create 하면 새 클라이언트", c3 is not c1 and FakeClient.made == 2, FakeClient.made)

    class BoomClient:
        def __init__(self, cfg):
            raise ValueError("bad config")

    ns_client["MultiServerMCPClient"] = BoomClient
    m4 = CM([{"name": "s", "command": "x"}])
    check("생성자 예외는 삼키고 None", await m4.get_or_create_client() is None)
    ns_client["HAS_MCP_ADAPTERS"] = False


asyncio.run(part_a_client())

# ---------------------------------------------------------------------------------------------
section("B. mcp_configs 변환 규칙: MCPClientManager.convert_configs_to_langchain_format 실제 소스")


def conv(configs):
    return CM(configs).convert_configs_to_langchain_format()


r = conv([{"name": "fs", "command": "npx", "args": "-y @x/server /tmp", "env": {"K": "v"}}])
check("stdio: args 문자열은 공백으로 split, env 전달", r == {"fs": {"transport": "stdio", "command": "npx", "args": ["-y", "@x/server", "/tmp"], "env": {"K": "v"}}}, r)
r = conv([{"command": "py", "args": ["a.py"]}])
check("name 없으면 mcp_server_<목록 위치+1>", list(r) == ["mcp_server_1"], r)
r = conv(["bad", {"command": "py"}, 7])
check("dict가 아닌 항목은 건너뛰고, 기본 이름의 번호는 원래 목록 위치를 따른다", list(r) == ["mcp_server_2"], r)
r = conv([{"name": "a", "connection_url": "https://h/mcp", "connection_type": "sse", "connection_token": "tk", "connection_headers": {"X": "1"}}])
check("https URL: transport=streamable_http, connection_type 무시(sse 지정해도), headers·token 전달",
      r["a"] == {"transport": "streamable_http", "url": "https://h/mcp", "headers": {"X": "1"}, "token": "tk"}, r)
r = conv([{"name": "a", "connection_url": "WSS://h/ws"}])
check("대문자 스킴도 websocket", r["a"] == {"transport": "websocket", "url": "WSS://h/ws"}, r)
r = conv([{"name": "a", "connection_url": "tcp://h:1", "connection_type": "websocket"}])
check("ws/http 외 스킴: connection_type 사용, websocket이면 url 설정", r["a"] == {"transport": "websocket", "url": "tcp://h:1"}, r)
r = conv([{"name": "a", "connection_url": "tcp://h:1"}])
check("ws/http 외 스킴 + connection_type 없음: stdio, command 없으니 {'transport': 'stdio'}만", r["a"] == {"transport": "stdio"}, r)
r = conv([{"name": "a", "connection_url": "h:1/sse", "connection_type": "sse"}])
check("connection_type=sse 는 url 없이 transport만 넘어간다(url 누락)", r["a"] == {"transport": "sse"}, r)
r = conv([{"name": "a", "connection_type": "http"}])
check("URL 없이 connection_type=http: transport 'http', url 없음", r["a"] == {"transport": "http"}, r)
r = conv([{"name": "a", "command": "c", "connection_token": "tk", "connection_headers": {"X": "1"}, "tool_name": "search"}])
check("stdio에도 token이 붙고, headers는 붙지 않고, tool_name은 읽지 않는다", r["a"] == {"transport": "stdio", "command": "c", "args": [], "token": "tk"}, r)
r = conv([{"name": "dup", "command": "one"}, {"name": "dup", "command": "two"}])
check("같은 name 은 뒤의 것이 덮어쓴다", r["dup"]["command"] == "two" and len(r) == 1, r)
r = conv([])
check("빈 목록 -> {}", r == {})
r = conv([{"name": "a", "command": "c", "args": None}])
check("args=None 은 그대로 None 으로 전달(검증 없음)", r["a"]["args"] is None, r)

# ---------------------------------------------------------------------------------------------
section("C. 전략 결정: GPTResearcher._resolve_mcp_strategy 실제 소스 (agent.py:217-281)")
Agent = make_class("Agent", [src("gpt_researcher/agent.py", 217, 281)], BASE_G)


def rs(param, legacy, cfg_value="__unset__"):
    cfg = SimpleNamespace() if cfg_value == "__unset__" else SimpleNamespace(mcp_strategy=cfg_value)
    a = Agent()
    a.cfg = cfg
    return a._resolve_mcp_strategy(param, legacy)


cases = [
    (("fast", None, "deep"), "fast"), (("deep", None), "deep"), (("disabled", None), "disabled"),
    (("optimized", None), "fast"), (("comprehensive", None), "deep"), (("bogus", None, "deep"), "fast"),
    ((None, 0), "disabled"), ((None, 1), "fast"), ((None, -1), "deep"), ((None, 7), "fast"),
    (("deep", 0), "deep"), ((None, None, "deep"), "deep"), ((None, None, "optimized"), "fast"),
    ((None, None, "comprehensive"), "deep"), ((None, None, "bogus"), "fast"), ((None, None), "fast"),
    ((None, 0, "deep"), "disabled"),
]
for args, want in cases:
    got = rs(*args)
    check("resolve%r == %s" % (args, want), got == want, got)

# ---------------------------------------------------------------------------------------------
section("D. mcp_configs -> retrievers: GPTResearcher._process_mcp_configs 실제 소스 (agent.py:295-321)")
PA = make_class("PA", [src("gpt_researcher/agent.py", 295, 321)], BASE_G)


def pm(retrievers, configs=({"command": "x"},)):
    a = PA()
    a.cfg = SimpleNamespace(retrievers=retrievers)
    a._process_mcp_configs(list(configs))
    return a.cfg.retrievers, a.mcp_configs


check("['tavily'] -> ['tavily','mcp'] (끝에 덧붙임)", pm(["tavily"])[0] == ["tavily", "mcp"])
check("이미 mcp가 있으면 순서 유지", pm(["mcp", "tavily"])[0] == ["mcp", "tavily"])
check("문자열 'tavily, exa' -> ['tavily','exa','mcp']", pm("tavily, exa")[0] == ["tavily", "exa", "mcp"])
check("빈 retrievers -> ['mcp']", pm([])[0] == ["mcp"])

# ---------------------------------------------------------------------------------------------
section("E. 도구 선택: MCPToolSelector 실제 소스 + 프롬프트 실제 소스 (대체: LLM 응답, json_repair->json.loads)")
PF = make_class("PromptFamily", [src("gpt_researcher/prompts.py", 39, 83), src("gpt_researcher/prompts.py", 85, 118)], BASE_G)
sel_g = dict(BASE_G, json_repair=SimpleNamespace(loads=json.loads))
sel_chunks = [
    src("gpt_researcher/mcp/tool_selector.py", 37, 125, sub=[(r"^(\s*)from \.\.prompts import PromptFamily", r"\1PromptFamily = _PF")]),
    src("gpt_researcher/mcp/tool_selector.py", 161, 202),
]
sel_g["_PF"] = PF
Selector = make_class("Selector", sel_chunks, sel_g)


def make_tools(names):
    return [SimpleNamespace(name=n, description=d) for n, d in names]


TOOLS = make_tools([("web_search", "Search the web"), ("read_file", "Read a file"), ("delete_all", "Danger"),
                    ("get_weather", "weather"), ("calc", None)])


def run_select(response, tools=TOOLS, max_tools=3, raise_llm=False):
    s = Selector()
    s.prompts = []

    async def fake_llm(prompt):
        s.prompts.append(prompt)
        if raise_llm:
            return ""
        return response

    s._call_llm_for_tool_selection = fake_llm
    out = asyncio.run(s.select_relevant_tools("Q?", tools, max_tools=max_tools))
    return [t.name for t in out], s


names, s = run_select(json.dumps({"selected_tools": [{"index": 1, "name": "read_file"}, {"index": 0}], "selection_reasoning": "r"}))
check("LLM이 준 index 순서대로 선택", names == ["read_file", "web_search"], names)
p = s.prompts[0]
check("프롬프트에 'EXACTLY 3', 쿼리, 도구 JSON(index/name/description) 포함, description 없으면 'No description available'",
      "EXACTLY 3" in p and '"Q?"' in p and '"index": 4' in p and "No description available" in p)
names, _ = run_select(json.dumps({"selected_tools": [{"index": 0}, {"index": 0}, {"index": 1}, {"index": 2}]}))
check("중복 index 와 max_tools 초과를 걸러내지 않는다", names == ["web_search", "web_search", "read_file", "delete_all"], names)
names, _ = run_select(json.dumps({"selected_tools": [{"index": 9}]}))
check("범위 밖 index 만 있으면 선택 0개 -> 폴백", names == ["web_search", "read_file", "get_weather"], names)
names, _ = run_select(json.dumps({"selected_tools": [{"index": 1}, {"index": 1.0}]}))
check("float index 하나가 있으면 TypeError -> 이미 고른 것도 버리고 전체 폴백", names == ["web_search", "read_file", "get_weather"], names)
names, _ = run_select(json.dumps({"selected_tools": ["x", {"index": "1"}]}))
check("문자열 index('1')도 비교 TypeError -> 폴백", names == ["web_search", "read_file", "get_weather"], names)
names, _ = run_select(json.dumps([1, 2]))
check("JSON이 객체가 아니면 폴백", names == ["web_search", "read_file", "get_weather"], names)
names, _ = run_select("", raise_llm=True)
check("LLM 호출 실패(빈 응답) -> 폴백", names == ["web_search", "read_file", "get_weather"], names)
names, _ = run_select("not json at all")
check("파싱 불가(대체 json.loads) -> 폴백", names == ["web_search", "read_file", "get_weather"], names)
names, s = run_select(json.dumps({"selected_tools": [{"index": 0}]}), tools=TOOLS[:2], max_tools=3)
check("도구 수 < max_tools 이면 max_tools=도구 수, LLM은 여전히 호출", "EXACTLY 2" in s.prompts[0] and names == ["web_search"], names)
names, s = run_select("x", tools=[])
check("도구가 없으면 LLM 호출 없이 []", names == [] and s.prompts == [])
only_unrelated = make_tools([("delete_all", "danger"), ("zap", "boom")])
names, _ = run_select("", tools=only_unrelated, raise_llm=True)
check("폴백: 패턴(search/get/read/...)에 하나도 안 맞으면 [] 가능", names == [], names)
scored = make_tools([("misc", "can search and fetch"), ("search_get", "x"), ("read", "read it")])
names, _ = run_select("", tools=scored, raise_llm=True)
check("폴백 점수: 이름 일치 3점/설명 일치 1점, 높은 순(동점은 원래 순서)", names == ["search_get", "read", "misc"], names)

# ---------------------------------------------------------------------------------------------
section("F. 도구 실행·결과 정규화: MCPResearchSkill 실제 소스 (대체: GenericLLMProvider, LLM 응답, 도구)")
res_g = dict(BASE_G, PromptFamily=PF)
CUR = {}


class FakeGLP:
    @staticmethod
    def from_provider(provider, **kw):
        CUR["provider_args"] = (provider, kw)
        return SimpleNamespace(llm=CUR["llm"])


res_g["_GLP"] = FakeGLP
res_g["_PF2"] = PF
res_chunks = [
    src("gpt_researcher/mcp/research.py", 34, 156,
        sub=[(r"^(\s*)from \.\.llm_provider\.generic\.base import GenericLLMProvider", r"\1GenericLLMProvider = _GLP"),
             (r"^(\s*)from \.\.prompts import PromptFamily", r"\1PromptFamily = _PF2")]),
    src("gpt_researcher/mcp/research.py", 158, 271),
]
Skill = make_class("Skill", res_chunks, res_g)
skill = Skill()
skill.cfg = SimpleNamespace(strategic_llm_model="m1", strategic_llm_provider="p1", llm_kwargs={"verbose": True})
skill.researcher = None


class FakeLLM:
    def __init__(self, response=None, boom=False):
        self.response, self.boom, self.calls, self.bound = response, boom, 0, None

    def bind_tools(self, tools):
        self.bound = tools
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        self.messages = messages
        if self.boom:
            raise RuntimeError("llm down")
        return self.response


class FakeTool:
    def __init__(self, name, result=None, boom=False):
        self.name, self.result, self.boom, self.calls = name, result, boom, []

    async def ainvoke(self, args):
        self.calls.append(args)
        if self.boom:
            raise RuntimeError("tool failed")
        return self.result


def run_skill(response, tools, boom=False):
    CUR["llm"] = FakeLLM(response, boom)
    out = asyncio.run(skill.conduct_research_with_tools("Q?", tools))
    return out, CUR["llm"]


t_ok = FakeTool("web_search", [{"title": "A", "content": "ca", "url": "http://a"}, "str-item", {"foo": 1}])
t_bad = FakeTool("read_file", boom=True)
t_empty = FakeTool("get", "")
resp = SimpleNamespace(tool_calls=[{"name": "web_search", "args": {"q": 1}}, {"name": "read_file", "args": {}},
                                    {"name": "nope", "args": {}}, {"name": "get", "args": {}}], content="my analysis")
out, llm = run_skill(resp, [t_ok, t_bad, t_empty])
check("LLM 호출은 정확히 1번(도구 결과를 LLM에 되돌려 주지 않는다)", llm.calls == 1, llm.calls)
check("provider 인자: strategic 제공자/모델 + llm_kwargs 전달", CUR["provider_args"] == ("p1", {"model": "m1", "verbose": True}), CUR["provider_args"])
check("실패한 도구·없는 도구·빈 결과는 건너뛰고 나머지는 계속, 마지막에 LLM Analysis 추가",
      [r["title"] for r in out] == ["A", "Result from web_search", "LLM Analysis: Q?"], [r["title"] for r in out])
check("list 결과: dict 아닌 항목(str-item)은 버려지고 title+content 없는 dict는 str(dict)", out[1]["body"] == "{'foo': 1}" and out[1]["href"] == "mcp://web_search/2", out[1])
check("LLM Analysis 항목: href=mcp://llm_analysis, body=response.content", out[-1]["href"] == "mcp://llm_analysis" and out[-1]["body"] == "my analysis")
check("도구는 LLM이 준 args 로 호출됨", t_ok.calls == [{"q": 1}])
out, llm = run_skill(SimpleNamespace(tool_calls=[], content="only text"), [t_ok])
check("tool_calls 없음: LLM Analysis 한 건만", [r["title"] for r in out] == ["LLM Analysis: Q?"], out)
out, llm = run_skill(SimpleNamespace(tool_calls=[], content=""), [t_ok])
check("tool_calls 없고 content 비어 있음: []", out == [])
out, llm = run_skill(None, [t_ok], boom=True)
check("LLM ainvoke 예외: 전체 []", out == [])
check("선택 도구 없음: LLM 호출 없이 []", asyncio.run(skill.conduct_research_with_tools("Q?", [])) == [])
out, llm = run_skill(SimpleNamespace(tool_calls=[], content=[{"type": "text", "text": "blocks"}]), [t_ok])
check("content가 블록 리스트면 body도 리스트가 된다(문자열로 바꾸지 않음)", isinstance(out[0]["body"], list), out[0]["body"])
LIST_BODY_RESULT = out[0]

# _process_tool_result 분기표
P = skill._process_tool_result
x = P("t", {"structured_content": {"results": [{"title": "T", "url": "u", "content": "c"}, "skip"]}})
check("래퍼 dict + structured_content.results: 항목마다 title/href(href>url>mcp://t/i)/body(body>content)", x == [{"title": "T", "href": "u", "body": "c"}], x)
x = P("t", {"structured_content": {"title": "S", "x": 1}})
check("structured_content dict(results 리스트 없음): 한 건, body=str(dict)", len(x) == 1 and x[0]["title"] == "S" and x[0]["href"] == "mcp://t", x)
x = P("t", {"structured_content": {"results": []}, "content": [{"type": "text", "text": "a"}, {"text": 5}, {"k": 1}, "z"]})
check("results가 빈 리스트면 content 폴백: text 파트를 빈 줄로 이음, 알 수 없는 파트는 str(part)", x == [{"title": "Result from t", "href": "mcp://t", "body": "a\n\n5\n\n{'k': 1}\n\nz"}], x)
x = P("t", {"content": "plain"})
check("content 문자열", x[0]["body"] == "plain")
x = P("t", {"content": 3})
check("content가 그 밖의 타입이면 body=str(result 전체)", x[0]["body"] == "{'content': 3}", x)
x = P("t", [{"title": "A", "body": "b"}, {"title": "no content"}, 5])
check("리스트: title+(body|content) 있으면 그대로 변환, 아니면 일반 제목, 비-dict 항목은 버림",
      x == [{"title": "A", "href": "mcp://t/0", "body": "b"}, {"title": "Result from t", "href": "mcp://t/1", "body": "{'title': 'no content'}"}], x)
x = P("t", ["a", "b"])
check("문자열 리스트는 결과 0건", x == [])
x = P("t", {"title": "D", "href": "h", "body": "b"})
check("래퍼 키가 없는 dict: 한 건", x == [{"title": "D", "href": "h", "body": "b"}], x)
x = P("t", "text")
check("그 밖의 타입: str(result) 한 건", x == [{"title": "Result from t", "href": "mcp://t", "body": "text"}], x)

# ---------------------------------------------------------------------------------------------
section("G. MCPRetriever.search / search_async / _get_all_tools 실제 소스 (대체: client_manager, tool_selector, mcp_researcher, streamer)")


class Streamer:
    def __init__(self):
        self.ev = []

    async def stream_stage_start(self, s, d): self.ev.append(("start", s))
    async def stream_warning(self, m): self.ev.append(("warn", m))
    async def stream_error(self, m): self.ev.append(("error", m))
    async def stream_research_results(self, n, c=None): self.ev.append(("results", n, c))
    async def stream_log(self, m, d=None): self.ev.append(("log", m))
    def stream_log_sync(self, m, d=None): self.ev.append(("sync", m))


ret_g = dict(BASE_G)
Ret = make_class("Ret", [src("gpt_researcher/retrievers/mcp/retriever.py", 116, 199),
                         src("gpt_researcher/retrievers/mcp/retriever.py", 201, 298),
                         src("gpt_researcher/retrievers/mcp/retriever.py", 300, 324)], ret_g)


def make_ret(tools=("a", "b"), selected=("a",), results=None, configs=({"x": 1},), raise_in="", slow=0.0):
    r = Ret()
    r.query = "Q"
    r.mcp_configs = list(configs)
    r._all_tools_cache = None
    r.streamer = Streamer()
    r.closed = 0
    r.sel_calls = []

    async def get_all_tools():
        if raise_in == "tools":
            raise RuntimeError("boom")
        await asyncio.sleep(slow)
        return list(tools)

    async def close_client():
        r.closed += 1
        if raise_in == "close":
            raise RuntimeError("close boom")

    async def select(q, all_tools, max_tools=3):
        r.sel_calls.append(max_tools)
        if raise_in == "select":
            raise RuntimeError("sel boom")
        return list(selected)

    async def research(q, sel):
        return results if results is not None else [{"title": "t%d" % i, "href": "h", "body": "b" * 3} for i in range(7)]

    r.client_manager = SimpleNamespace(get_all_tools=get_all_tools, close_client=close_client)
    r.tool_selector = SimpleNamespace(select_relevant_tools=select)
    r.mcp_researcher = SimpleNamespace(conduct_research_with_tools=research)
    return r


r = make_ret()
out = asyncio.run(r.search_async(5))
check("search_async: 결과를 max_results 개로 자른다(뒤쪽 잘림), max_tools=3으로 선택 호출, 끝에 close_client", len(out) == 5 and r.sel_calls == [3] and r.closed == 1, (len(out), r.sel_calls, r.closed))
check("search_async: 단계 이벤트 Stage 1~3 + 결과 요약", [e for e in r.streamer.ev if e[0] == "start"] == [("start", "Stage 1"), ("start", "Stage 2"), ("start", "Stage 3")] and r.streamer.ev[-1][0] == "results", r.streamer.ev)
r = make_ret(tools=())
check("도구 0개: [] + warning, close_client 는 호출", asyncio.run(r.search_async(5)) == [] and r.closed == 1 and ("warn", "No MCP tools available, skipping MCP research") in r.streamer.ev)
r = make_ret(selected=())
check("선택 0개: [] + warning", asyncio.run(r.search_async(5)) == [] and ("warn", "No relevant tools selected, skipping MCP research") in r.streamer.ev)
r = make_ret(configs=())
check("mcp_configs 없음: [] 이고 close_client 호출 없음(finally 이전 반환)", asyncio.run(r.search_async(5)) == [] and r.closed == 0)
r = make_ret(raise_in="select")
check("선택 단계 예외: [] + error 이벤트 + close_client", asyncio.run(r.search_async(5)) == [] and r.closed == 1 and any(e[0] == "error" for e in r.streamer.ev))
r = make_ret(raise_in="tools")
check("도구 로드 예외(_get_all_tools가 삼킴): [] ", asyncio.run(r.search_async(5)) == [] and r.closed == 1)
r = make_ret(raise_in="close")
check("close_client 예외는 삼키고 결과 반환", len(asyncio.run(r.search_async(5))) == 5)
r = make_ret()


async def tools_cache():
    a = await r._get_all_tools()
    r.client_manager.get_all_tools = None  # 두 번째 호출은 캐시만 써야 한다
    b = await r._get_all_tools()
    return a, b


a, b = asyncio.run(tools_cache())
check("_get_all_tools: 같은 인스턴스에서는 도구 목록을 캐시", a == b == ["a", "b"])

# search(): 동기 래퍼. 실행 중인 이벤트 루프 안에서 부르면 다른 스레드의 새 루프에서 돌고, 호출한 루프는 막힌다.
r = make_ret(slow=0.6)


async def blocking_probe():
    ticks = 0

    async def ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.05)
            ticks += 1

    t = asyncio.create_task(ticker())
    await asyncio.sleep(0)
    t0 = time.time()
    out = r.search(5)          # _execute_mcp_research 가 하는 것처럼 코루틴 안에서 동기 호출
    dt = time.time() - t0
    during = ticks
    await asyncio.sleep(0.2)
    t.cancel()
    return out, dt, during, ticks


out, dt, during, after = asyncio.run(blocking_probe())
check("루프 안에서 search() 호출 시 결과 반환", len(out) == 5, len(out))
check("search() 가 끝날 때까지 호출한 이벤트 루프가 멈춘다(ticker 0회) -- 최소 0.6s 블로킹", during == 0 and dt >= 0.6, "ticks_during=%d dt=%.2fs ticks_after=%d" % (during, dt, after))
r = make_ret()
out = r.search(3)  # 루프 없음 -> asyncio.run 경로
check("루프 밖에서 search(): asyncio.run 경로로 같은 결과", len(out) == 3)
# 타임아웃 상수 300 을 0.3 으로 치환한 변형(대체: 상수만 바꿈): 시간 초과 시 결과와 실제 대기 시간
Ret_short = make_class("Ret_short", [src("gpt_researcher/retrievers/mcp/retriever.py", 201, 298, sub=[(r"timeout=300\)", "timeout=0.3)")])], ret_g)
rs_ = Ret_short()
rs_.mcp_configs = [{"x": 1}]
rs_.query = "Q"
rs_.streamer = Streamer()


async def slow_search_async(max_results):
    await asyncio.sleep(1.0)
    return ["late"]


rs_.search_async = slow_search_async


async def timeout_probe():
    t0 = time.time()
    out = rs_.search(5)
    return out, time.time() - t0


out, dt = asyncio.run(timeout_probe())
check("future.result(timeout) 초과 시 search()는 [] 를 돌려주지만, with ThreadPoolExecutor 종료가 스레드 완료를 기다려 실제로는 1초 작업이 끝난 뒤에야 반환(타임아웃 0.3s 치환본)",
      out == [] and dt >= 1.0 and any("MCP search" in e[1] for e in rs_.streamer.ev), "out=%r dt=%.2fs" % (out, dt))
r = make_ret(configs=())
check("search(): mcp_configs 없음 -> [] (예외 없음)", r.search(3) == [] and ("sync", "❌ MCP retriever cannot proceed without server configurations.") in r.streamer.ev)

# ---------------------------------------------------------------------------------------------
section("H. ResearchConductor 의 MCP 경로 (실제 소스 + 대체: retriever 클래스, 스크랩, 선별, 서브쿼리 계획 LLM, stream_output)")
EVENTS = []


async def stream_output(type, content, output, websocket=None, output_log=True, metadata=None):
    EVENTS.append(content)
    await asyncio.sleep(0)  # websocket 전송처럼 한 번 양보한다


MCP_CALLS = []


class TavilySearch2:
    def __init__(self, query, query_domains=None): pass
    def search(self, max_results=5): return [{"href": "https://t/1", "body": "x"}]


class MCPRetriever:  # 이름에 'mcpretriever' 포함 (소문자 비교)
    def __init__(self, query, headers=None, query_domains=None, websocket=None, researcher=None, **kw):
        self.query = query

    def search(self, max_results=10):
        MCP_CALLS.append(self.query)
        return [{"title": "T:%s" % self.query, "href": "https://mcp.example/x", "body": "mcp body for %s" % self.query},
                {"title": "LLM Analysis: %s" % self.query, "href": "mcp://llm_analysis", "body": "analysis"}]


PLANNER = {"queries": ["s1", "s2"]}


async def generate_sub_queries(*a, **k):
    return list(PLANNER["queries"])


cond_g = dict(BASE_G, random=__import__("random"), os=__import__("os"), stream_output=stream_output,
              get_json_handler=lambda: None, generate_sub_queries=generate_sub_queries)
exec(compile("from __future__ import annotations\n" + src("gpt_researcher/actions/query_processing.py", 44, 81), "<gsr>", "exec"), cond_g)
exec(compile("from __future__ import annotations\n" + src("gpt_researcher/actions/query_processing.py", 158, 215), "<pro>", "exec"), cond_g)
cond_g["Config"] = object
cond_chunks = [src("gpt_researcher/skills/researcher.py", a, b) for a, b in [
    (34, 48), (50, 66), (68, 95), (298, 408), (410, 434), (436, 490), (492, 517), (520, 663), (665, 737), (739, 790), (836, 849)]]
Cond = make_class("Cond", cond_chunks, cond_g)


def make_cond(retrievers, strategy, mcp_configs, report_type="research_report", planned=("s1", "s2")):
    PLANNER["queries"] = list(planned)
    ctx = SimpleNamespace()

    async def sim(sub_query, data):
        return "WEB[%s]" % sub_query

    ctx.get_similar_content_by_query = sim
    researcher = SimpleNamespace(retrievers=retrievers, mcp_configs=mcp_configs, mcp_strategy=strategy, verbose=True,
                                 websocket=None, headers={}, query_domains=[], role="role", parent_query="",
                                 report_type=report_type, add_costs=lambda c: None, kwargs={},
                                 cfg=SimpleNamespace(max_search_results_per_query=5, mcp_strategy="fast", strategic_llm_model="m"),
                                 context_manager=ctx)
    c = Cond(researcher)

    async def scrape(sub_query, query_domains=None, initial_results=None):
        has_web = any("mcpretriever" not in r.__name__.lower() for r in researcher.retrievers)
        return [{"url": "u", "raw_content": "c"}] if has_web else []

    c._scrape_data_by_urls = scrape
    return c


def run_web(c, query="Q"):
    del MCP_CALLS[:]
    del EVENTS[:]
    out = asyncio.run(c._get_context_by_web_search(query, [], []))
    return out, list(MCP_CALLS), list(EVENTS)


TAV_MCP = [{"name": "github", "command": "npx", "args": ["server-github"]}]
WEB_MCP = [TavilySearch2, MCPRetriever]
print("  [서브쿼리 계획 대체: LLM 이 ['s1','s2'] 를 줌 -> 원 질문 Q 가 덧붙어 [s1, s2, Q]; MCP 단독이면 [Q]+[Q]]")

out, calls, ev = run_web(make_cond(WEB_MCP, "fast", TAV_MCP))
check("fast + [web, mcp]: MCP 1회(원 질문), 서브쿼리 3개 모두 캐시 재사용", calls == ["Q"] and ev.count("mcp_cache_reuse") == 3, (calls, ev.count("mcp_cache_reuse")))
check("fast: 서브쿼리마다 MCP 본문이 결과에 반복된다(3번)", out.count("mcp body for Q") == 3, out.count("mcp body for Q"))
out, calls, ev = run_web(make_cond(WEB_MCP, "deep", TAV_MCP))
check("deep + [web, mcp]: MCP 3회(서브쿼리 s1, s2, Q 각각), 캐시 없음", sorted(calls) == ["Q", "s1", "s2"] and "mcp_cache_reuse" not in ev, calls)
out, calls, ev = run_web(make_cond(WEB_MCP, "deep", TAV_MCP, report_type="subtopic_report"))
check("deep + subtopic_report: 원 질문이 안 붙으므로 2회", sorted(calls) == ["s1", "s2"], calls)
out, calls, ev = run_web(make_cond(WEB_MCP, "disabled", TAV_MCP))
check("disabled + [web, mcp]: MCP 0회, 웹 결과는 정상", calls == [] and "WEB[s1]" in out and "mcp body" not in out and "mcp_disabled" in ev, (calls, ev.count("mcp_disabled")))
out, calls, ev = run_web(make_cond([MCPRetriever], "fast", TAV_MCP))
check("fast + [mcp] 단독: 선점 1회 + 초기 검색 1회 = 2회, 서브쿼리는 [Q, Q]", calls == ["Q", "Q"], calls)
out, calls, ev = run_web(make_cond([MCPRetriever], "deep", TAV_MCP))
check("deep + [mcp] 단독: 초기 검색 1회 + 서브쿼리 [Q, Q] 2회 = 3회", calls == ["Q", "Q", "Q"], calls)
out, calls, ev = run_web(make_cond([MCPRetriever], "disabled", TAV_MCP))
check("disabled + [mcp] 단독: 초기 검색은 전략과 무관하게 MCP를 1회 실행하고 그 결과는 쓰이지 않는다", calls == ["Q"] and "mcp body" not in out, (calls, out))
out, calls, ev = run_web(make_cond([MCPRetriever, TavilySearch2], "fast", TAV_MCP))
check("fast + [mcp, web]: 선점 1 + 초기 검색 1 = 2회", calls == ["Q", "Q"], calls)

TAVILY_CFG = [{"name": "tavily", "command": "npx", "args": ["-y", "tavily-mcp@0.1.2"]}]
tavily_direct = type("TavilySearch", (), {"__init__": TavilySearch2.__init__, "search": TavilySearch2.search})
out, calls, ev = run_web(make_cond([tavily_direct, MCPRetriever], "fast", TAVILY_CFG))
check("Tavily MCP 중복 + fast: 서브쿼리에서는 MCP를 쓰지 않지만 선점 단계에서는 MCP가 1회 실행된다(낭비)",
      calls == ["Q"] and "mcp body" not in out and ev.count("mcp_tavily_deduped") == 3, (calls, ev.count("mcp_tavily_deduped")))
out, calls, ev = run_web(make_cond([tavily_direct, MCPRetriever], "deep", TAVILY_CFG))
check("Tavily MCP 중복 + deep: MCP 0회", calls == [] and "mcp body" not in out, calls)

# 동시 실행(하이브리드의 두 패스) — 잠금 효과
async def two_passes(c):
    return await asyncio.gather(c._get_context_by_web_search("Q", [], []), c._get_context_by_web_search("Q", [], []))


class NullLock:
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False


c = make_cond(WEB_MCP, "fast", TAV_MCP)
del MCP_CALLS[:]
asyncio.run(two_passes(c))
check("fast, 동시 두 패스: 잠금 덕분에 MCP 선점은 1회", len(MCP_CALLS) == 1, MCP_CALLS)
c = make_cond(WEB_MCP, "fast", TAV_MCP)
c._mcp_cache_lock = NullLock()
del MCP_CALLS[:]
asyncio.run(two_passes(c))
check("(대조) 잠금을 no-op 으로 바꾸면 2회 -- 잠금이 중복 실행을 막는다", len(MCP_CALLS) == 2, MCP_CALLS)
c = make_cond(WEB_MCP, "deep", TAV_MCP)
del MCP_CALLS[:]
asyncio.run(two_passes(c))
check("deep, 동시 두 패스: 패스마다 3회씩 6회(캐시 없음)", len(MCP_CALLS) == 6, len(MCP_CALLS))

# 캐시 수명: 같은 인스턴스에서 두 번째 conduct 는 첫 질문의 MCP 결과를 재사용
c = make_cond(WEB_MCP, "fast", TAV_MCP)
del MCP_CALLS[:]
o1 = asyncio.run(c._get_context_by_web_search("Q", [], []))
o2 = asyncio.run(c._get_context_by_web_search("OTHER", [], []))
check("fast: 같은 ResearchConductor 의 두 번째 호출은 MCP를 다시 실행하지 않고 첫 질문('Q')의 결과를 쓴다",
      MCP_CALLS == ["Q"] and "mcp body for Q" in o2 and "mcp body for OTHER" not in o2, MCP_CALLS)
check("캐시 항목 형식: content/url/title/query/source_type", set(c._mcp_results_cache[0]) == {"content", "url", "title", "query", "source_type"} and c._mcp_results_cache[0]["source_type"] == "mcp", c._mcp_results_cache[0])
check("캐시에는 LLM Analysis 항목도 들어간다(내용이 있으면)", [e["title"] for e in c._mcp_results_cache] == ["T:Q", "LLM Analysis: Q"], [e["title"] for e in c._mcp_results_cache])

# MCP 가 빈 결과이면 빈 리스트가 캐시되어 다시 실행하지 않는다
class EmptyMCP(MCPRetriever):
    def search(self, max_results=10):
        MCP_CALLS.append(self.query)
        return []


EmptyMCP.__name__ = "MCPRetriever"
c = make_cond([TavilySearch2, EmptyMCP], "fast", TAV_MCP)
del MCP_CALLS[:]
o = asyncio.run(c._get_context_by_web_search("Q", [], []))
check("fast + MCP 빈 결과: 캐시는 [] (None 아님)이라 재실행 없음, 웹 결과만 반환", c._mcp_results_cache == [] and MCP_CALLS == ["Q"] and "WEB[s1]" in o, (c._mcp_results_cache, MCP_CALLS))


class BoomMCP(MCPRetriever):
    def search(self, max_results=10):
        MCP_CALLS.append(self.query)
        raise RuntimeError("mcp exploded")


BoomMCP.__name__ = "MCPRetriever"
c = make_cond([TavilySearch2, BoomMCP], "deep", TAV_MCP)
o = asyncio.run(c._get_context_by_web_search("Q", [], []))
check("MCP search 예외(deep): 서브쿼리는 계속되고 웹 결과가 남는다", "WEB[s1]" in o and "mcp body" not in o)
del EVENTS[:]
o = asyncio.run(c._get_context_by_web_search("Q", [], []))
check("  (확인) mcp_research_error 이벤트", "mcp_research_error" in EVENTS, EVENTS.count("mcp_research_error"))

# 리스트 본문 때문에 결합이 실패해 서브쿼리 전체(웹 컨텍스트 포함)가 ""가 되는 경우
c = make_cond(WEB_MCP, "fast", TAV_MCP)
c._mcp_results_cache = [{"content": LIST_BODY_RESULT["body"], "url": "mcp://llm_analysis", "title": "LLM Analysis: Q", "query": "Q", "source_type": "mcp"}]
o = asyncio.run(c._process_sub_query("s1", [], []))
check("MCP 본문이 str 이 아니면(예: 블록 리스트) 결합에서 AttributeError -> 그 서브쿼리 결과는 웹 컨텍스트까지 포함해 ''", o == "", repr(o))

# 알 수 없는 전략 값(researcher.mcp_strategy 가 None 이고 cfg 값이 잘못된 경우)
c = make_cond(WEB_MCP, None, TAV_MCP)
c.researcher.cfg.mcp_strategy = "foo"
out, calls, ev = run_web(c)
check("알 수 없는 전략: 선점은 fast처럼 1회 캐시, 그런데 서브쿼리 쪽은 캐시를 안 쓰고 서브쿼리마다 실행 -> 총 4회", calls[0] == "Q" and len(calls) == 4, calls)
c = make_cond(WEB_MCP, None, TAV_MCP)
c.researcher.cfg.mcp_strategy = "deep"
check("_get_mcp_strategy: researcher.mcp_strategy 가 None 이면 cfg.mcp_strategy", c._get_mcp_strategy() == "deep")
c.researcher.mcp_strategy = "disabled"
check("_get_mcp_strategy: researcher.mcp_strategy 가 우선", c._get_mcp_strategy() == "disabled")

# Tavily 중복 판정 단위
section("I. _tavily_mcp_redundant_with_direct 단위 (실제 소스)")
c = make_cond(WEB_MCP, "fast", TAV_MCP)
Tv = type("TavilySearch", (), {})
Mc = MCPRetriever


def red(non_mcp, configs):
    c.researcher.mcp_configs = configs
    return c._tavily_mcp_redundant_with_direct([Mc], non_mcp)


check("name에 tavily -> 중복", red([Tv], [{"name": "tavily-mcp", "command": "x"}]) is True)
check("args 리스트에 tavily -> 중복", red([Tv], [{"name": "a", "command": "npx", "args": ["-y", "tavily-mcp@0.1.2"]}]) is True)
check("command에 tavily -> 중복", red([Tv], [{"name": "a", "command": "/opt/tavily-mcp"}]) is True)
check("args가 문자열이면 글자 단위로 이어져 'tavily'를 못 찾는다 -> 중복 아님", red([Tv], [{"name": "a", "command": "npx", "args": "-y tavily-mcp"}]) is False)
check("connection_url만 tavily -> 중복 아님", red([Tv], [{"name": "a", "connection_url": "https://mcp.tavily.com/mcp"}]) is False)
check("서버 중 하나라도 tavily가 아니면 중복 아님", red([Tv], [{"name": "tavily"}, {"name": "gh", "command": "gh"}]) is False)
check("직접 Tavily retriever가 없으면 중복 아님", red([type("Exa", (), {})], [{"name": "tavily"}]) is False)
check("non-MCP retriever가 없으면 중복 아님", red([], [{"name": "tavily"}]) is False)
check("비-dict 항목이 섞이면 중복 아님", red([Tv], [{"name": "tavily"}, "x"]) is False)
check("mcp_configs 비어 있음 -> 중복 아님", red([Tv], []) is False)

# 결합 형식
section("J. _combine_mcp_and_web_context 형식 (실제 소스)")
comb = c._combine_mcp_and_web_context
mc = [{"content": "  c1  ", "url": "https://u", "title": "T1"}, {"content": "c2", "url": "mcp://llm_analysis", "title": "LLM Analysis"},
      {"content": "c3", "url": "", "title": "T3"}, {"content": "   ", "url": "x", "title": "blank"}, {"content": "c5", "url": "mcp://tool/1", "title": ""}]
got = comb(mc, "  web  ", "q")
want = "web\n\nc1\n\n*Source: T1 (https://u)*\n\n---\n\nc2\n\n*Source: LLM Analysis*\n\n---\n\nc3\n\n*Source: T3*\n\n---\n\nc5\n\n*Source:  (mcp://tool/1)*"
check("web(strip) + 빈 줄 + MCP 항목들(본문 strip + '*Source: 제목 (URL)*'), 항목 사이 '---', 공백뿐인 본문 제외", got == want, repr(got))
check("web 없음 -> MCP만", comb(mc[:1], "", "q") == "c1\n\n*Source: T1 (https://u)*")
check("둘 다 없음 -> ''", comb([], "  ", "q") == "")
check("MCP 항목이 전부 빈 본문 -> web만", comb([mc[3]], "w", "q") == "w")

print("\n요약: 실패 %d건" % len(FAILS))
for f in FAILS:
    print("  - " + f)
sys.exit(1 if FAILS else 0)
