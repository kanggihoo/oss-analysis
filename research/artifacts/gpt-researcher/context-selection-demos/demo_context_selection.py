"""Offline demo for reports/gpt-researcher/capabilities/context-selection.md (2026-10-22).

Runs the REAL source of gpt_researcher/context/{select,lexical,jev_filter,retriever}.py
(repos/gpt-researcher @ 3582a68) without network and without installing packages.
langchain_core, langchain_text_splitters and httpx are NOT installed here, so these
four are replaced by stubs (see STUBS below). Everything else is the original code.

What the stubs change (and therefore what this demo does NOT verify):
- RecursiveCharacterTextSplitter: stub splits on blank lines only. Test pages use
  paragraphs of 500-900 chars so that, by assumption (not verified), the real splitter
  would also give one chunk per paragraph. Real chunk boundaries/overlap: not verified.
  The stub records the (chunk_size, chunk_overlap) arguments the real code passes.
- httpx.AsyncClient: scripted fake server, no socket is opened. Real TypeSafe scoring: not verified.
- Document / BaseRetriever / PromptFamily wrapper: minimal stand-ins. The real
  PromptFamily.pretty_print_docs (prompts.py:555-562) is extracted from source with ast and used.
- gpt_researcher/__init__.py (imports the whole agent) is skipped; a bare package object is used.
- compression.py (embeddings mode) is the real file but its import fails because
  langchain_classic is missing; that real ImportError is what triggers the keyword fallback.

Run: python -I demo_context_selection.py
"""
import ast
import asyncio
import importlib
import logging
import os
import sys
import textwrap
import types

REPO = r"C:\Users\SSAFY\Desktop\oss-analysis\repos\gpt-researcher"
PKG = os.path.join(REPO, "gpt_researcher")

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="  [log %(levelname)s] %(message)s")


# ---------------------------------------------------------------- STUBS
class Document:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class BaseRetriever:
    pages = []

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def invoke(self, query):
        return self._get_relevant_documents(query, run_manager=None)


SPLITTER_CALLS = []


class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size=4000, chunk_overlap=200, **kw):
        self.chunk_size, self.chunk_overlap = chunk_size, chunk_overlap
        SPLITTER_CALLS.append((chunk_size, chunk_overlap))

    def split_documents(self, docs):
        out = []
        for d in docs:
            for part in d.page_content.split("\n\n"):
                part = part.strip()
                if part:
                    out.append(Document(part, dict(d.metadata)))
        return out


class FakeHTTPError(Exception):
    pass


class FakeResponse:
    def __init__(self, status, body=None, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeServer:
    handler = None
    calls = []
    inflight = 0
    max_inflight = 0


class FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None, timeout=None):
        FakeServer.calls.append((url, json, headers, timeout))
        FakeServer.inflight += 1
        FakeServer.max_inflight = max(FakeServer.max_inflight, FakeServer.inflight)
        try:
            await asyncio.sleep(0.005)
            return FakeServer.handler(json)
        finally:
            FakeServer.inflight -= 1


def _real_pretty_print_docs():
    src = open(os.path.join(PKG, "prompts.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "PromptFamily":
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "pretty_print_docs":
                    code = textwrap.dedent(ast.get_source_segment(src, fn))
                    code = code.replace("@staticmethod\n", "")
                    ns = {"Document": Document}
                    exec(code, ns)
                    return ns["pretty_print_docs"]
    raise RuntimeError("pretty_print_docs not found")


class PromptFamily:
    pretty_print_docs = staticmethod(_real_pretty_print_docs())


def load(env=None):
    """Fresh import of the real context modules with env applied (constants are read at import)."""
    for k in list(sys.modules):
        if k.startswith(("gpt_researcher", "langchain", "httpx")):
            del sys.modules[k]
    for k in ("KEYWORD_RELATIVE_THRESHOLD", "KEYWORD_MAX_RESULTS", "MAX_CONTENT_CHARS", "COMPRESSION_THRESHOLD",
              "CONTEXT_FILTER", "TYPESAFE_API_KEY", "JEV_CONCURRENCY", "JEV_MIN_SCORE", "JEV_CHUNK_SIZE", "JEV_MODEL"):
        os.environ.pop(k, None)
    os.environ.update(env or {})

    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m
        return m

    mod("langchain_core")
    mod("langchain_core.documents", Document=Document)
    mod("langchain_core.callbacks", CallbackManagerForRetrieverRun=object)
    mod("langchain_core.retrievers", BaseRetriever=BaseRetriever)
    mod("langchain_text_splitters", RecursiveCharacterTextSplitter=RecursiveCharacterTextSplitter)
    mod("httpx", HTTPError=FakeHTTPError, AsyncClient=FakeAsyncClient)
    g = mod("gpt_researcher"); g.__path__ = [PKG]
    c = mod("gpt_researcher.context"); c.__path__ = [os.path.join(PKG, "context")]
    mod("gpt_researcher.prompts", PromptFamily=PromptFamily)
    sel = importlib.import_module("gpt_researcher.context.select")
    lex = importlib.import_module("gpt_researcher.context.lexical")
    jev = importlib.import_module("gpt_researcher.context.jev_filter")
    return sel, lex, jev


# ---------------------------------------------------------------- data helpers
def para(first, n=700):
    s = first + " "
    filler = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore "
    while len(s) < n:
        s += filler
    return s[:n].rstrip()


def page(url, title, *paras):
    return {"url": url, "title": title, "raw_content": "\n\n".join(paras)}


def head(t):
    print("\n" + "=" * 8, t)


def titles(text):
    return [l for l in text.splitlines() if l.startswith("Content: ")]


class Cfg:
    def __init__(self, **kw):
        self.__dict__.update(kw)


async def main():
    # ---------------------------------------------------------- 1. resolve_context_filter
    head("1. resolve_context_filter")
    sel, lex, jev = load()
    for key in (None, "TYPESAFE"):
        if key:
            os.environ["TYPESAFE_API_KEY"] = "k"
        for s in (None, "", "auto", " JEV ", "Keyword", "embeddings", "none", "foo", "bm25"):
            print(f"  key={'set' if key else 'unset'} setting={s!r:14} -> {sel.resolve_context_filter(s)}")
    os.environ.pop("TYPESAFE_API_KEY", None)
    os.environ["TYPESAFE_API_KEY"] = ""
    print(f"  key='' (empty string) setting='auto' -> {sel.resolve_context_filter('auto')}")
    os.environ.pop("TYPESAFE_API_KEY")

    # ---------------------------------------------------------- 2. tokenize / BM25
    head("2. tokenize / stem / bm25")
    print("  tokenize:", lex.tokenize("The batteries costs of Classes in 2024: A Movies, glass! 전기차 배터리 비용"))
    print("  stems:", {w: lex._stem(w) for w in ["batteries", "costs", "classes", "boxes", "watches", "glass", "movies", "cars", "bus"]})
    sc = lex.bm25_scores("battery cost", ["battery cost battery", "cost only here", "nothing relevant", ""])
    print("  bm25 scores:", [round(x, 4) for x in sc])
    print("  bm25 empty passages:", lex.bm25_scores("x", []), " all-stopword query:", lex.bm25_scores("the of", ["battery cost"]))

    # ---------------------------------------------------------- 3. keyword select
    head("3. LexicalContextCompressor: relative threshold and cap")
    p1 = page("http://a", "A",
              para("Battery cost battery cost trends in 2024 battery cost falls."),   # strongest
              para("Battery prices and cost per kWh."),                                # medium
              para("Weather report for the weekend."),
              para("Cost of living index."),
              para("Another battery paragraph about chemistry."))
    comp = lambda **kw: lex.LexicalContextCompressor(documents=[p1], **kw)
    chunks = comp()._chunks()
    texts = [c.page_content for c in chunks]
    scores = lex.bm25_scores("battery cost", [c.page_content for c in chunks])
    print("  chunk scores:", [round(s, 3) for s in scores], " best:", round(max(scores), 3))
    for th in (0.0, 0.5, 0.9):
        out = comp(relative_threshold=th).select("battery cost", 25)
        print(f"  threshold={th}: kept chunk indexes {[texts.index(c.page_content) for c in out]}")
    out = comp(relative_threshold=0.0).select("battery cost", 2)
    print("  threshold=0 max_results=2: kept", [texts.index(c.page_content) for c in out])
    print("  (ties keep chunk order): sorted key (-score, index) verified by indexes above")

    head("4. keyword: no overlap fallback = first N chunks across pages (not one per page)")
    pa = page("http://a", "A", *[para(f"alpha paragraph {i}") for i in range(5)])
    pb = page("http://b", "B", para("beta opening paragraph"))
    c2 = lex.LexicalContextCompressor(documents=[pa, pb], relative_threshold=0.5)
    for q in ("quantum zebra", "the of and", ""):
        out = c2.select(q, 3)
        print(f"  query={q!r}: sources of kept chunks {[d.metadata['source'] for d in out]}")

    # ---------------------------------------------------------- 5. select_context paths
    head("5. select_context paths (keyword mode)")
    big_pages = [page(f"http://p{i}", f"P{i}", para(f"page {i} battery cost info"), para("lorem " * 100),
                      para("battery cost detail") if i == 3 else para("unrelated filler text"))
                 for i in range(6)]
    total = sum(len(p["raw_content"]) for p in big_pages)
    print(f"  6 pages, total chars {total} (>8000 -> filtering)")
    out = await sel.select_context("battery cost", big_pages, Cfg(context_filter="keyword"))
    srcs = [l for l in out.splitlines() if l.startswith("Source: ")]
    print("  keyword result sources in order:", [s[8:] for s in srcs])
    print("  KEYWORD constants:", sel.KEYWORD_RELATIVE_THRESHOLD, sel.KEYWORD_MAX_RESULTS)

    small = [page("http://s1", "S1", "tiny one"), page("http://s2", "S2", "tiny two battery")]
    out = await sel.select_context("battery cost", small, Cfg(context_filter="keyword"))
    print("  small fast path (2 pages, <8000 chars) returns all in input order, unfiltered:")
    print("   ", repr(out))
    many_small = [page(f"http://m{i}", f"M{i}", f"short {i}") for i in range(11)]
    out = await sel.select_context("battery cost", many_small, Cfg(context_filter="keyword"))
    print("  11 tiny pages (>max_results=10, no overlap with query) -> filtered path; chunks returned:", out.count("Source: "),
          "(first-N fallback, cap 25)")
    out = await sel.select_context("q", [], Cfg(context_filter="keyword"))
    print("  zero pages ->", repr(out))
    out = await sel.select_context("q", [{"url": "u", "title": "t", "raw_content": None}], Cfg(context_filter="keyword"))
    print("  raw_content None page ->", repr(out))
    out = await sel.select_context("q", [{"url": "u", "raw_content": "x"}], Cfg(context_filter="keyword"))
    print("  page without title key ->", repr(out))

    head("6. mode none: every page, but each page cut at MAX_CONTENT_CHARS")
    sel, lex, jev = load({"MAX_CONTENT_CHARS": "50"})
    pg = [page("http://n", "N", "x" * 120)]
    out = await sel.select_context("q", pg, Cfg(context_filter="none"))
    print("  MAX_CONTENT_CHARS=50, none mode; content length returned:", len(out.split("Content: ")[1].rstrip("\n")))
    sel, lex, jev = load()
    many = [page(f"http://z{i}", f"Z{i}", "y" * 10) for i in range(15)]
    out = await sel.select_context("q", many, Cfg(context_filter="none"))
    print("  none mode with 15 pages returns", out.count("Source: "), "pages (no cap)")
    out = await sel.select_context("q", many, Cfg(context_filter="keyword"))
    print("  keyword mode, same 15 tiny pages returns", out.count("Source: "), "chunks")
    sel, lex, jev = load({"COMPRESSION_THRESHOLD": "abc"})
    try:
        await sel.select_context("q", many, Cfg(context_filter="keyword"))
    except Exception as e:
        print("  COMPRESSION_THRESHOLD='abc' ->", type(e).__name__, e)
    sel, lex, jev = load({"COMPRESSION_THRESHOLD": "0"})
    out = await sel.select_context("q", small, Cfg(context_filter="keyword"))
    print("  COMPRESSION_THRESHOLD=0 and 2 tiny pages: chunks returned", out.count("Source: "), "(fast path disabled)")
    for bad in ({"KEYWORD_MAX_RESULTS": "ten"}, {"KEYWORD_RELATIVE_THRESHOLD": "half"}):
        try:
            load(bad)
        except Exception as e:
            print(f"  import with {bad} ->", type(e).__name__, e)
    sel, lex, jev = load({"KEYWORD_MAX_RESULTS": "2", "KEYWORD_RELATIVE_THRESHOLD": "0.0"})
    out = await sel.select_context("battery cost", big_pages, Cfg(context_filter="keyword"), max_results=10)
    print("  KEYWORD_MAX_RESULTS=2 -> chunks returned", out.count("Source: "), "; select_context max_results=10 ignored by keyword path")

    # ---------------------------------------------------------- 7. embeddings fallback
    head("7. embeddings mode in this environment (langchain_classic missing)")
    sel, lex, jev = load()
    calls = []
    out = await sel.select_context("battery cost", big_pages, Cfg(context_filter="embeddings", similarity_threshold=0.42),
                                   embeddings=lambda: calls.append(1) or object())
    print("  embeddings factory called:", len(calls), "times; fell back to keyword; chunks:", out.count("Source: "))
    out = await sel.select_context("battery cost", small, Cfg(context_filter="embeddings"), embeddings=lambda: calls.append(1))
    print("  embeddings mode, small input: fast path, factory calls total:", len(calls))

    # ---------------------------------------------------------- 8. jev
    head("8. jev mode with a scripted fake server (no network)")
    jp = [page("http://j", "J",
               para("ANSWER the battery cost is 100 dollars."),
               para("partial info about batteries"),
               para("filler paragraph one"),
               para("ANSWER another direct fact about cost"),
               para("filler paragraph two"),
               *[para(f"filler padding {i}") for i in range(10)])]

    def ok_handler(payload):
        s = payload["state"]
        score = 3.0 if "ANSWER" in s else 1.6 if "partial" in s else 0.4
        return FakeResponse(200, {"answers": {"usefulness": {"score": score}}, "usage": {"input_tokens": 200}})

    def reset(handler):
        FakeServer.handler, FakeServer.calls, FakeServer.max_inflight, FakeServer.inflight = handler, [], 0, 0
        SPLITTER_CALLS.clear()

    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo", "JEV_CONCURRENCY": "4", "JEV_CHUNK_SIZE": "800"})
    reset(ok_handler)
    costs = []
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="auto"), cost_callback=costs.append)
    print("  auto + key -> jev. requests:", len(FakeServer.calls), "max in flight:", FakeServer.max_inflight,
          "(JEV_CONCURRENCY=4); splitter args:", SPLITTER_CALLS)
    url, payload, headers, timeout = FakeServer.calls[0]
    print("  url:", url); print("  headers:", headers); print("  timeout:", timeout)
    print("  payload keys:", sorted(payload), " model:", payload["model"])
    print("  payload.questions:", payload["questions"])
    print("  kept chunks:", [l[9:40] for l in titles(out)], "cost callback:", costs, "(200 tokens x", len(FakeServer.calls), "x 0.042/1e6)")

    reset(ok_handler)
    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo", "JEV_MIN_SCORE": "3.0"})
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="jev"))
    print("  JEV_MIN_SCORE=3.0 kept:", len(titles(out)), "chunks")
    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo", "JEV_MIN_SCORE": "9"})
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="jev"))
    print("  JEV_MIN_SCORE=9 (nothing passes) -> result", repr(out), "(no keyword fallback for 'nothing relevant')")

    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo", "JEV_MIN_SCORE": "0"})
    reset(ok_handler)
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="jev"), max_results=10)
    print("  JEV_MIN_SCORE=0, 15 chunks, max_results=10 -> kept", len(titles(out)), "; first 2 are the score-3.0 chunks:",
          [l[9:30] for l in titles(out)[:2]])

    # failures
    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo"})
    reset(lambda p: FakeResponse(401, text="unauthorized"))
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="jev"))
    print("  401 -> requests:", len(FakeServer.calls), "(each chunk tried once, no retry); fell back to keyword, chunks:", out.count("Source: "))

    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo"})
    state = {"n": 0}
    def flaky(p):
        state["n"] += 1
        return FakeResponse(429, text="slow down") if state["n"] <= 2 else ok_handler(p)
    reset(flaky)
    client = jev.JevClient()
    import time
    t = time.time()
    async with client.session() as http:
        v = await client.score_relevance(http, "q", "ANSWER x")
    print(f"  429,429,200 -> score {v} after {state['n']} attempts, {time.time()-t:.2f}s (backoff 0.5 + 1.0)")

    reset(lambda p: FakeResponse(429, text="slow down"))
    t = time.time()
    try:
        async with client.session() as http:
            await client.score_relevance(http, "q", "x")
    except jev.JevError as e:
        print(f"  429 x4 -> JevError after {len(FakeServer.calls)} attempts, {time.time()-t:.2f}s (0.5+1+2): {e}")

    reset(lambda p: FakeResponse(529, text="overloaded"))
    t = time.time()
    try:
        async with client.session() as http:
            await client.score_relevance(http, "q", "x")
    except jev.JevError as e:
        print(f"  529 also retried: attempts {len(FakeServer.calls)}")

    def net_err(p):
        raise FakeHTTPError("connect failed")
    reset(net_err)
    try:
        async with client.session() as http:
            await client.score_relevance(http, "q", "x")
    except jev.JevError as e:
        print(f"  httpx.HTTPError -> retried, attempts {len(FakeServer.calls)}: {e}")

    for name, resp in (("200 without answers key", FakeResponse(200, {"foo": 1}, text='{"foo":1}')),
                       ("200 non-JSON body", FakeResponse(200, None, text="<html>")),
                       ("200 score not a number", FakeResponse(200, {"answers": {"usefulness": {"score": "abc"}}}))):
        reset(lambda p, r=resp: r)
        try:
            async with client.session() as http:
                await client.score_relevance(http, "q", "x")
        except jev.JevError as e:
            print(f"  {name} -> JevError, attempts {len(FakeServer.calls)} (no retry): {str(e)[:60]}")

    reset(lambda p: FakeResponse(200, {"answers": {"usefulness": {"score": 2}}}))
    async with client.session() as http:
        v = await client.score_relevance(http, "q", "x")
    print("  200 without usage ->", v, "input_tokens stays", client.input_tokens - 200 * 0 if False else client.input_tokens)

    # one failing chunk fails the whole jev pass
    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo"})
    def one_bad(p):
        return FakeResponse(500, text="boom") if "filler padding 3" in p["state"] else ok_handler(p)
    reset(one_bad)
    costs = []
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="jev"), cost_callback=costs.append)
    print("  one chunk HTTP 500 -> whole jev pass dropped; keyword used; cost_callback calls:", costs, "; chunks:", out.count("Source: "))

    # explicit jev without key
    sel, lex, jev = load()
    reset(ok_handler)
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="jev"))
    print("  jev without TYPESAFE_API_KEY -> requests", len(FakeServer.calls), "-> keyword chunks:", out.count("Source: "))

    # non-JevError escapes
    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo", "JEV_MIN_SCORE": "high"})
    try:
        await sel.select_context("battery cost", jp, Cfg(context_filter="jev"))
    except Exception as e:
        print("  JEV_MIN_SCORE='high' ->", type(e).__name__, "escapes select_context (only JevError is caught)")
    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo", "JEV_CONCURRENCY": "x"})
    reset(ok_handler)
    try:
        await sel.select_context("battery cost", jp, Cfg(context_filter="jev"))
    except Exception as e:
        print("  JEV_CONCURRENCY='x' ->", type(e).__name__, "escapes select_context")
    sel, lex, jev = load({"TYPESAFE_API_KEY": "sk-demo"})
    reset(ok_handler)
    out = await sel.select_context("battery cost", jp, Cfg(context_filter="jev"))
    print("  jev default JEV_CONCURRENCY semaphore per loop:", list(jev._SEMAPHORES.values())[0]._value, "free slots after run")

    head("9. output format")
    sel, lex, jev = load()
    out = await sel.select_context("q", [page("http://a", "A", "one"), page("http://b", "B", "two")], Cfg(context_filter="keyword"))
    print(repr(out))


asyncio.run(main())
