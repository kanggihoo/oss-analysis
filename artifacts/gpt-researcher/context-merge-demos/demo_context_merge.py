"""Offline demo: how sub-query results are merged into one context string.
(repos/gpt-researcher @ 3582a68). Run: python -I demo_context_merge.py

REAL source (cut out of the files with ast and exec'd, unmodified):
  researcher.py  ResearchConductor: _get_context_by_web_search, _process_sub_query,
                 _scrape_data_by_urls, _search_relevant_source_urls, _get_new_urls,
                 _get_context_from_initial_results, _combine_mcp_and_web_context,
                 _get_mcp_strategy, _tavily_mcp_redundant_with_direct
  context_manager.py ContextManager.get_similar_content_by_query
  select.py   select_context, resolve_context_filter, _as_documents
  retriever.py SearchAPIRetriever   (with stub langchain_core base classes)
  prompts.py  PromptFamily.pretty_print_docs
STUBS (so what is NOT verified): plan_research / _get_initial_search_results (fixed lists),
  fake retriever classes, fake scraper_manager.browse_urls (returns pages from a table, drops
  failures, raises for a chosen URL), stream_output (no-op), langchain Document/BaseRetriever.
  Lexical/BM25 and Jev paths are NOT exercised: pages are < COMPRESSION_THRESHOLD (8000 chars)
  and <= 10 pages, so select_context takes its 'little content' branch.
"""
import ast
import asyncio
import logging
import os
import random
import re
import sys
import textwrap
import types

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
REPO = r"C:\Users\SSAFY\Desktop\oss-analysis\repos\gpt-researcher"
P = os.path.join(REPO, "gpt_researcher")
logging.basicConfig(level=logging.CRITICAL)


def src(rel):
    return open(os.path.join(P, rel), encoding="utf-8").read()


def cut(source, cls, names):
    tree = ast.parse(source)
    out = {}
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == cls:
            for f in n.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name in names:
                    out[f.name] = textwrap.dedent(ast.get_source_segment(source, f))
    return out


def cut_funcs(source, names):
    tree = ast.parse(source)
    out = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names:
            out[n.name] = ast.get_source_segment(source, n)
    return out


# ---- langchain stubs, then the real retriever.py
class Document:
    def __init__(self, page_content, metadata=None):
        self.page_content, self.metadata = page_content, metadata or {}


class BaseRetriever:
    pages = []

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def invoke(self, q):
        return self._get_relevant_documents(q, run_manager=None)


for name, attrs in {
    "langchain_core": {},
    "langchain_core.callbacks": {"CallbackManagerForRetrieverRun": object},
    "langchain_core.documents": {"Document": Document},
    "langchain_core.retrievers": {"BaseRetriever": BaseRetriever},
}.items():
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
ns_ret = {}
exec(compile(src("context/retriever.py"), "retriever.py", "exec"), ns_ret)
SearchAPIRetriever = ns_ret["SearchAPIRetriever"]

# ---- real pretty_print_docs
pp_src = cut(src("prompts.py"), "PromptFamily", {"pretty_print_docs"})["pretty_print_docs"]
pp_src = pp_src.replace("@staticmethod\n", "")


class PromptFamily:
    pass


ns_pp = {"Document": Document}
exec("from __future__ import annotations\n" + pp_src, ns_pp)
PromptFamily.pretty_print_docs = staticmethod(ns_pp["pretty_print_docs"])


# ---- real select_context
class _Boom:
    def __init__(self, *a, **k):
        raise RuntimeError("Lexical/Jev not used in this demo")


f = cut_funcs(src("context/select.py"), {"resolve_context_filter", "_as_documents", "select_context"})
ns_sel = dict(
    os=os, logger=logging.getLogger("sel"), CONTEXT_FILTERS=("auto", "jev", "keyword", "embeddings", "none"),
    SearchAPIRetriever=SearchAPIRetriever, PromptFamily=PromptFamily, Document=Document,
    JevContextCompressor=_Boom, JevError=Exception, LexicalContextCompressor=_Boom,
    KEYWORD_RELATIVE_THRESHOLD=0.5, KEYWORD_MAX_RESULTS=25, Callable=object,
)
for s in ("resolve_context_filter", "_as_documents", "select_context"):
    exec("from __future__ import annotations\n" + f[s], ns_sel)

# ---- real ContextManager.get_similar_content_by_query
cm = cut(src("skills/context_manager.py"), "ContextManager", {"get_similar_content_by_query"})
ns_cm = dict(select_context=ns_sel["select_context"], stream_output=None)
exec("from __future__ import annotations\n" + cm["get_similar_content_by_query"], ns_cm)


class ContextManager:
    get_similar_content_by_query = ns_cm["get_similar_content_by_query"]


# ---- real ResearchConductor methods
names = {
    "_get_context_by_web_search", "_process_sub_query", "_scrape_data_by_urls", "_search_relevant_source_urls",
    "_get_new_urls", "_get_context_from_initial_results", "_combine_mcp_and_web_context", "_get_mcp_strategy",
    "_tavily_mcp_redundant_with_direct", "_execute_mcp_research_for_queries", "_execute_mcp_research",
}
rc = cut(src("skills/researcher.py"), "ResearchConductor", names)


async def stream_output(*a, **k):
    return None


ns_rc = dict(asyncio=asyncio, random=random, stream_output=stream_output)
for s in rc.values():
    exec("from __future__ import annotations\n" + s, ns_rc)


class Conductor:
    pass


for k in rc:
    setattr(Conductor, k, ns_rc[k])
assert len(rc) == len(names), set(names) - set(rc)

# ---------------------------------------------------------------- fakes
PAGES = {  # url -> content (None => scrape failure, dropped like Scraper.run drops raw_content None)
    "u1": "PAGE-U1 " + "alpha " * 30, "u2": "PAGE-U2 " + "beta " * 30, "u3": None,
    "u4": "PAGE-U4 " + "delta " * 30, "u9": "PAGE-U9 " + "omega " * 30, "uC": "PAGE-UC boom",
}
SEARCH = {}  # query -> (delay, results or Exception)
CALLS = []   # browse_urls call log


class FakeRetriever:
    requires_scraping = True

    def __init__(self, query, query_domains=None):
        self.query = query

    def search(self, max_results=5):
        import time
        delay, res_ = SEARCH[self.query]
        time.sleep(delay)  # runs inside asyncio.to_thread in the real code
        if isinstance(res_, Exception):
            raise res_
        return [dict(r) for r in res_]


class FakePrefetchRetriever(FakeRetriever):
    requires_scraping = False


class Cfg:
    max_search_results_per_query = 5
    context_filter = "keyword"
    mcp_strategy = "fast"


class FakeScraperMgr:
    async def browse_urls(self, urls):
        CALLS.append(list(urls))
        await asyncio.sleep(0)
        out = []
        for u in urls:
            if u == "uC":
                raise RuntimeError("scraper crashed (simulated; the real Scraper catches these per URL)")
            if PAGES.get(u):
                out.append({"url": u, "raw_content": PAGES[u], "title": f"T-{u}"})
        return out


class Researcher:
    def __init__(self, retr):
        self.retrievers = list(retr) if isinstance(retr, (list, tuple)) else [retr]
        self.mcp_configs = []
        self.cfg = Cfg()
        self.verbose = False
        self.websocket = None
        self.visited_urls = set()
        self.research_sources = []
        self.vector_store = None
        self.report_type = "research_report"
        self.prompt_family = PromptFamily
        self.scraper_manager = FakeScraperMgr()
        self.context_manager = ContextManager()
        self.context_manager.researcher = self
        self.headers = {}
        self.query_domains = []
        self.mcp_strategy = None

    def add_research_sources(self, s):
        self.research_sources.extend(s)

    def add_costs(self, c):
        pass


def make(retr, plan, initial):
    r = Researcher(retr)
    c = Conductor()
    c.researcher = r
    c.logger = logging.getLogger("rc")
    c.json_handler = None
    c._mcp_results_cache = None
    c._mcp_cache_lock = asyncio.Lock()
    c._mcp_query_count = 0

    async def _init(q, d=None):
        return initial

    async def _plan(q, d=None, *, search_results=None):
        return list(plan)

    orig = c._process_sub_query

    async def traced(sub_query, scraped_data=[], query_domains=[]):
        o = await orig(sub_query, scraped_data, query_domains)
        got = re.findall(r"Source: (\S+)", o) if isinstance(o, str) else o
        print(f"   [sub-query {sub_query!r}] returned {type(o).__name__}: sources={got}")
        return o

    c._process_sub_query = traced
    c._get_initial_search_results = _init
    c.plan_research = _plan
    return c, r


def res(*urls):
    return [{"href": u, "title": u, "body": "snippet"} for u in urls]


def show(title, out):
    print("=" * 78)
    print(title)
    print("-" * 78)
    print("type:", type(out).__name__, "| len:", len(out))
    if isinstance(out, str):
        short = re.sub(r"(?:(?:alpha|beta|delta|omega|gamma) ?)+", "<f>", out)
        print("repr (repeated filler words collapsed to <f>):", repr(short))


async def scenario1(a_delay, b_delay, label):
    CALLS.clear()
    SEARCH.clear()
    SEARCH.update({"A": (a_delay, res("u1", "u2")), "B": (b_delay, res("u2", "u3")),
                   "C": (0.01, res("uC")), "Q": (0.03, res("u1", "u4"))})
    # first retriever's 'initial results' are given to the conductor directly: u1, u9
    c, r = make(FakeRetriever, ["A", "B", "C"], res("u1", "u9"))
    out = await c._get_context_by_web_search("Q", [], [])
    show(label, out)
    print("browse_urls calls (order):", CALLS)
    print("visited_urls:", sorted(r.visited_urls))
    return out


async def scenario_all_empty():
    SEARCH.clear()
    SEARCH.update({"A": (0, []), "Q": (0, [])})
    c, r = make(FakeRetriever, ["A"], [])
    show("S3 all sub-queries return no search results, no initial results",
         await c._get_context_by_web_search("Q", [], []))


async def scenario_prefetched():
    CALLS.clear()
    SEARCH.clear()
    content = "FULLTEXT-P1 " + "gamma " * 30
    row = {"href": "p1", "raw_content": content, "title": "P1"}
    SEARCH.update({"A": (0, [row]), "B": (0.01, [row]), "Q": (0.02, [row])})
    c, r = make(FakePrefetchRetriever, ["A", "B"], [])
    out = await c._get_context_by_web_search("Q", [], [])
    show("S4 retriever with requires_scraping=False returns the SAME url for A, B, Q", out)
    print("occurrences of 'Source: p1':", out.count("Source: p1"), "| browse_urls calls:", CALLS)
    print("research_sources urls:", [s["url"] for s in r.research_sources], "| visited:", sorted(r.visited_urls))


async def scenario_retriever_exc():
    CALLS.clear()
    SEARCH.clear()
    SEARCH.update({"A": (0, RuntimeError("search API 429")), "B": (0, res("u1")), "Q": (0, res("u4"))})
    c, r = make(FakeRetriever, ["A", "B"], [])
    out = await c._get_context_by_web_search("Q", [], [])
    show("S5 retriever.search raises for A (caught inside _search_relevant_source_urls)", out)


class MCPRetriever:
    def __init__(self, query, headers=None, query_domains=None, websocket=None, researcher=None):
        self.query = query

    def search(self, max_results=5):
        return [{"title": "MCP-T", "href": "mcp://srv", "body": "MCP-BODY for " + self.query}]


async def scenario_mcp():
    CALLS.clear()
    SEARCH.clear()
    SEARCH.update({"A": (0, res("u1")), "B": (0.01, res("u2")), "Q": (0.02, res("u4"))})
    c, r = make([FakeRetriever, MCPRetriever], ["A", "B"], [])
    out = await c._get_context_by_web_search("Q", [], [])
    show("S7 web retriever + MCP retriever (mcp_strategy=fast): same cached MCP result per sub-query", out)
    print("occurrences of 'MCP-BODY':", out.count("MCP-BODY"), "(3 sub-queries A, B, Q)")


async def scenario_mcp_only():
    SEARCH.clear()
    c, r = make([MCPRetriever], ["Q"], [])  # plan_research_outline returns [query] for MCP-only
    out = await c._get_context_by_web_search("Q", [], [])
    show("S8 MCP-only: planner returns [Q] and Q is appended again -> Q runs twice", out)
    print("occurrences of 'MCP-BODY':", out.count("MCP-BODY"))


async def scenario_planning_exc():
    SEARCH.clear()
    SEARCH.update({"Q": (0, res("u1"))})
    c, r = make(FakeRetriever, ["A"], [])

    async def _plan(q, d=None, *, search_results=None):
        raise RuntimeError("LLM planning failed")

    c.plan_research = _plan
    print("=" * 78)
    try:
        await c._get_context_by_web_search("Q", [], [])
    except Exception as e:
        print("S6 plan_research raises ->", type(e).__name__, str(e), "(propagates out of _get_context_by_web_search)")


async def main():
    await scenario1(0.00, 0.02,
                    "S1 initial=[u1,u9]; A=[u1,u2] (fast); B=[u2,u3(scrape fails)]; C=browse_urls raises; Q=[u1,u4]")
    await scenario1(0.04, 0.00, "S2 same inputs, but B's search finishes before A's")
    await scenario_all_empty()
    await scenario_prefetched()
    await scenario_retriever_exc()
    await scenario_mcp()
    await scenario_mcp_only()
    await scenario_planning_exc()


asyncio.run(main())
