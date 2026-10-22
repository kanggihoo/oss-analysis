"""Offline demo for reports/gpt-researcher/capabilities/detailed-report.md (2026-10-22).

Runs the REAL source of these files of repos/gpt-researcher @ 3582a68 without network,
without an LLM call and without installing packages:
  backend/report_type/detailed_report/detailed_report.py   (DetailedReport: whole class)
  gpt_researcher/actions/markdown_processing.py            (extract_headers/extract_sections/table_of_contents/add_references)
  gpt_researcher/skills/context_manager.py                 (ContextManager, similar written contents)
  gpt_researcher/context/lexical.py                        (rank_written_sections, bm25_scores)
  gpt_researcher/context/compression.py                    (WrittenContentCompressor)
  gpt_researcher/context/retriever.py                      (SectionRetriever)
  gpt_researcher/utils/llm.py                              (construct_subtopics)
  gpt_researcher/utils/validators.py                       (Subtopic, Subtopics; pydantic)
  gpt_researcher/prompts.py                                (generate_subtopics_prompt, generate_subtopic_report_prompt)
  gpt_researcher/utils/enum.py                             (ReportType, Tone, ReportSource)

What is replaced (so what this demo does NOT verify):
- GPTResearcher (gpt_researcher/agent.py cannot be imported: its dependencies are missing).
  Part A drives the real DetailedReport class with a FakeResearcher that records the
  constructor keyword arguments and the call order and returns scripted texts. The
  FakeResearcher delegates extract_headers / extract_sections / table_of_contents /
  add_references to the REAL markdown_processing functions (agent.py:700-743 only forward to them).
  Everything the real GPTResearcher does inside conduct_research / write_report /
  write_introduction / get_draft_section_titles (LLM, search, scrape) is scripted, so this demo
  says nothing about their content, only about what DetailedReport passes in and does with the results.
- LLM calls, embedding models: none. The "embedding model" is a stub whose only job is to exist or raise.
- langchain_core (Document, BaseRetriever, PromptTemplate, PydanticOutputParser), langchain_text_splitters
  (RecursiveCharacterTextSplitter), langchain_classic (ContextualCompressionRetriever, EmbeddingsFilter,
  DocumentCompressorPipeline) are NOT installed here and are replaced by minimal stand-ins:
  * RecursiveCharacterTextSplitter splits on blank lines only (the real one splits by size 1000/100);
    test texts are short so that, by assumption, one paragraph = one chunk. It records the
    (chunk_size, chunk_overlap) the real code passes.
  * EmbeddingsFilter keeps chunks whose text contains the marker "KEEP" (the real one compares embedding
    similarity with the threshold); it records the threshold the real code passes.
  * PromptTemplate renders with str.format; PydanticOutputParser parses JSON and validates with the
    REAL pydantic models of validators.py. The real langchain parser's output-format text
    (get_format_instructions) and JSON extraction are NOT verified.
- gpt_researcher/__init__.py and the *__init__.py files that import the whole agent are skipped.
- Python-Markdown and pydantic are NOT installed. This demo appends the already unpacked copies in the
  local uv cache to sys.path (Python-Markdown 3.10.3, pydantic 2.13.5). Nothing was installed or modified.
- All query / context / report texts are made-up examples that only show the format.

Run: python demo_detailed_report.py   (no -I: it needs sys.path.append)
"""
import ast
import asyncio
import contextlib
import copy
import importlib.util
import io
import json
import logging
import os
import sys
import types
import warnings
from types import SimpleNamespace

sys.dont_write_bytecode = True  # do not leave .pyc files inside repos/
sys.stdout.reconfigure(encoding="utf-8")
logging.disable(logging.CRITICAL)

REPO = r"C:\Users\SSAFY\Desktop\oss-analysis\repos\gpt-researcher"
PKG = os.path.join(REPO, "gpt_researcher")
SITE = os.environ.get(
    "MARKDOWN_SITE",
    r"C:\Users\SSAFY\AppData\Local\uv\cache\archive-v0\0NDFaUedZ9HAdUJ4\Lib\site-packages",
)
sys.path.append(SITE)
import markdown  # noqa: E402,F401
import pydantic  # noqa: E402

RESULTS = []


def check(label, cond, detail=""):
    RESULTS.append(bool(cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"  -> {detail}" if detail else ""))


def head(title):
    print("\n" + "=" * 8 + " " + title)


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------------ module plumbing
def mkpkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m


def mod(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


gp = mkpkg("gpt_researcher")
gp_utils = mkpkg("gpt_researcher.utils")
gp_actions = mkpkg("gpt_researcher.actions")
gp_skills = mkpkg("gpt_researcher.skills")
gp_context = mkpkg("gpt_researcher.context")
gp_memory = mkpkg("gpt_researcher.memory")
gp_llmprov = mkpkg("gpt_researcher.llm_provider")
mkpkg("gpt_researcher.llm_provider.generic")


# ---- stand-ins for third-party packages
class Document:
    def __init__(self, page_content="", metadata=None):
        self.page_content, self.metadata = page_content, metadata or {}


SPLITTER_CALLS = []


class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size=4000, chunk_overlap=200, **kw):
        self.chunk_size, self.chunk_overlap = chunk_size, chunk_overlap
        SPLITTER_CALLS.append((chunk_size, chunk_overlap))

    def split_text(self, text):
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    def split_documents(self, docs):
        out = []
        for d in docs:
            for part in self.split_text(d.page_content):
                out.append(Document(part, dict(d.metadata)))
        return out


class BaseRetriever:  # pydantic-free stand-in; kwargs become attributes
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def invoke(self, query, **kw):
        return self._get_relevant_documents(query, run_manager=None)


FILTER_CALLS = []


class EmbeddingsFilter:
    def __init__(self, embeddings, similarity_threshold):
        self.embeddings, self.similarity_threshold = embeddings, similarity_threshold
        FILTER_CALLS.append(similarity_threshold)

    def keep(self, docs):
        return [d for d in docs if "KEEP" in d.page_content]


class DocumentCompressorPipeline:
    def __init__(self, transformers):
        self.transformers = transformers


class ContextualCompressionRetriever:
    def __init__(self, base_compressor, base_retriever):
        self.base_compressor, self.base_retriever = base_compressor, base_retriever

    def invoke(self, query, **kw):
        docs = self.base_retriever.invoke(query)
        splitter, flt = self.base_compressor.transformers
        return flt.keep(splitter.split_documents(docs))


lc = mkpkg("langchain_core")
mod("langchain_core.documents", Document=Document)
mod("langchain_core.callbacks", CallbackManagerForRetrieverRun=object)
mod("langchain_core.retrievers", BaseRetriever=BaseRetriever)
mkpkg("langchain_text_splitters").RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
mkpkg("langchain_classic")
mod("langchain_classic.retrievers", ContextualCompressionRetriever=ContextualCompressionRetriever)
mod("langchain_classic.retrievers.document_compressors",
    DocumentCompressorPipeline=DocumentCompressorPipeline, EmbeddingsFilter=EmbeddingsFilter)
sys.modules["langchain_classic"].retrievers = sys.modules["langchain_classic.retrievers"]

# ---- real files with trivial dependencies
enum_mod = load("gpt_researcher.utils.enum", os.path.join(PKG, "utils", "enum.py"))
gp_utils.enum = enum_mod


class StubConfig:
    pass


mod("gpt_researcher.config", Config=StubConfig)
prompts = load("gpt_researcher.prompts", os.path.join(PKG, "prompts.py"))
PromptFamily = prompts.PromptFamily
mdp = load("gpt_researcher.actions.markdown_processing", os.path.join(PKG, "actions", "markdown_processing.py"))
validators = load("gpt_researcher.utils.validators", os.path.join(PKG, "utils", "validators.py"))
ctx_retriever = load("gpt_researcher.context.retriever", os.path.join(PKG, "context", "retriever.py"))
lexical = load("gpt_researcher.context.lexical", os.path.join(PKG, "context", "lexical.py"))

COST_CALLS = []
mod("gpt_researcher.memory.embeddings", OPENAI_EMBEDDING_MODEL="stub-embedding-model")
mod("gpt_researcher.utils.costs",
    estimate_embedding_cost=lambda model, docs: COST_CALLS.append((model, len(docs))) or 0.25,
    calculate_llm_cost=lambda **kw: 0.0)
mod("gpt_researcher.vector_store", VectorStoreWrapper=object)
compression = load("gpt_researcher.context.compression", os.path.join(PKG, "context", "compression.py"))

mod("gpt_researcher.utils.logger", get_formatted_logger=lambda: logging.getLogger("demo"))
actions_utils = load("gpt_researcher.actions.utils", os.path.join(PKG, "actions", "utils.py"))
mod("gpt_researcher.context.select", select_context=None)
context_manager = load("gpt_researcher.skills.context_manager", os.path.join(PKG, "skills", "context_manager.py"))


# ================================================================== A. DetailedReport (real class, fake GPTResearcher)
class WS:  # stand-in for fastapi.WebSocket
    pass


mod("fastapi", WebSocket=WS)

EVENTS = []  # global call-order log


class Script:
    """What the fake GPTResearcher returns. Set per scenario."""

    def __init__(self):
        self.contexts = {"Q": "MAIN CTX", "T1": "T1 CTX", "T2": "T2 CTX"}
        self.urls = {"Q": ["https://m1", "https://m2"], "T1": ["https://t1a"], "T2": ["https://m1", "https://t2a"]}
        self.subtopics = ["T1", "T2"]
        self.intro = "# Intro\n\nintro text"
        self.reports = {
            "T1": "## T1 Heading\n\n### A1\n\ntext a1 ([c](https://x))\n\n### B1\n\ntext b1",
            "T2": "## T2 Heading\n\n### A2\n\ntext a2",
        }
        self.conclusion = "## Conclusion\n\nconcl"
        self.draft_titles = ["### A1", "### B1"]
        self.similar = ["SIMILAR-1"]
        self.subtopics_obj = "auto"   # "auto" -> built from self.subtopics, or set to any object (e.g. [])
        self.raise_in = {}            # {(query, method): Exception}
        self.sleep = 0.0


SCRIPT = Script()


class FakeResearcher:
    instances = []

    def __init__(self, **kw):
        self.kw = kw
        self.query = kw["query"]
        self.report_type = kw.get("report_type", "research_report")
        self.visited_urls = kw["visited_urls"] if kw.get("visited_urls") is not None else set()
        self.agent, self.role = kw.get("agent"), kw.get("role")
        self.mcp_configs = kw.get("mcp_configs")
        self.mcp_strategy = kw.get("mcp_strategy") or "fast"
        self.cfg = SimpleNamespace(max_search_results_per_query=5)
        self.context = kw.get("context") or []
        self.calls = []
        FakeResearcher.instances.append(self)

    def _tag(self):
        return "main" if self.report_type == "research_report" else self.query

    def _maybe_raise(self, method):
        exc = SCRIPT.raise_in.get((self.query, method))
        if exc:
            raise exc

    async def conduct_research(self):
        EVENTS.append(f"{self._tag()}.conduct:start")
        await asyncio.sleep(SCRIPT.sleep)
        self._maybe_raise("conduct_research")
        if not (self.agent and self.role):
            self.agent, self.role = "Agent-X", "Role-X"
        self.context = SCRIPT.contexts[self.query]       # real code overwrites the preset context (agent.py:392)
        self.visited_urls.update(SCRIPT.urls[self.query])
        EVENTS.append(f"{self._tag()}.conduct:end")
        return self.context

    async def get_subtopics(self):
        EVENTS.append("main.get_subtopics")
        if SCRIPT.subtopics_obj != "auto":
            return SCRIPT.subtopics_obj
        return SimpleNamespace(subtopics=[SimpleNamespace(task=t) for t in SCRIPT.subtopics])

    async def write_introduction(self):
        EVENTS.append("main.write_introduction")
        self.intro_context_seen = self.context
        return SCRIPT.intro

    async def get_draft_section_titles(self, current_subtopic):
        EVENTS.append(f"{self._tag()}.draft_titles")
        return SCRIPT.draft_titles   # real function returns list[str] (section_titles.split("\n"))

    async def get_similar_written_contents_by_draft_section_titles(self, subtopic, titles, written, max_results=10):
        EVENTS.append(f"{self._tag()}.get_similar")
        self.similar_args = (subtopic, copy.deepcopy(titles), copy.deepcopy(written))
        return SCRIPT.similar

    async def write_report(self, existing_headers=[], relevant_written_contents=[], **kw):
        EVENTS.append(f"{self._tag()}.write_report")
        self.write_args = {"existing_headers": copy.deepcopy(existing_headers),
                           "relevant_written_contents": copy.deepcopy(relevant_written_contents), **kw}
        self._maybe_raise("write_report")
        return SCRIPT.reports[self.query]

    async def write_report_conclusion(self, body):
        EVENTS.append("main.write_report_conclusion")
        self.conclusion_arg = body
        return SCRIPT.conclusion

    # agent.py:700-743 only forward to markdown_processing
    def extract_headers(self, t):
        return mdp.extract_headers(t)

    def extract_sections(self, t):
        return mdp.extract_sections(t)

    def table_of_contents(self, t):
        return mdp.table_of_contents(t)

    def add_references(self, r, v):
        return mdp.add_references(r, v)


gp.GPTResearcher = FakeResearcher
dr_mod = load("detailed_report_real", os.path.join(REPO, "backend", "report_type", "detailed_report", "detailed_report.py"))
DetailedReport = dr_mod.DetailedReport


def fresh(**script_over):
    global SCRIPT
    SCRIPT = Script()
    for k, v in script_over.items():
        setattr(SCRIPT, k, v)
    FakeResearcher.instances.clear()
    EVENTS.clear()


def make(**kw):
    base = dict(query="Q", report_type="detailed_report", report_source="web")
    base.update(kw)
    return DetailedReport(**base)


head("A1. constructor: main researcher arguments and defaults (detailed_report.py:11-76)")
fresh()
d = make()
main = FakeResearcher.instances[0]
check("main researcher kwargs are exactly these keys",
      set(main.kw) == {"query", "query_domains", "report_type", "report_source", "source_urls", "document_urls",
                       "config_path", "tone", "websocket", "headers", "complement_source_urls"},
      sorted(main.kw))
check("main report_type is hard-coded 'research_report' although the argument says 'detailed_report'",
      main.kw["report_type"] == "research_report" and d.report_type == "detailed_report")
check("defaults: source_urls [] document_urls [] query_domains [] config_path None tone '' websocket None headers {} complement False",
      main.kw["source_urls"] == [] and main.kw["document_urls"] == [] and main.kw["query_domains"] == []
      and main.kw["config_path"] is None and main.kw["tone"] == "" and main.kw["websocket"] is None
      and main.kw["headers"] == {} and main.kw["complement_source_urls"] is False)
check("no documents / subtopics / mcp / log_handler / verbose / visited_urls given to main",
      not ({"documents", "subtopics", "mcp_configs", "mcp_strategy", "log_handler", "verbose", "visited_urls",
            "agent", "role", "parent_query"} & set(main.kw)))
check("DetailedReport has no 'documents' parameter",
      "documents" not in DetailedReport.__init__.__code__.co_varnames[:DetailedReport.__init__.__code__.co_argcount])
check("initial state: existing_headers [], global_context [], global_written_sections [], global_urls set()",
      d.existing_headers == [] and d.global_context == [] and d.global_written_sections == [] and d.global_urls == set())
rid = d.research_id
check("research_id = 'detailed_<unix seconds>_<md5(query)[:8]>' and it is not read anywhere else",
      rid.startswith("detailed_") and rid.endswith("_" + __import__("hashlib").md5(b"Q").hexdigest()[:8]), rid)
check("global_urls is seeded with set(source_urls) when given",
      make(source_urls=["https://s1"]).global_urls == {"https://s1"})
fresh()
d = make(mcp_configs=[{"name": "srv"}], mcp_strategy="deep", max_search_results="7")
main = FakeResearcher.instances[0]
check("mcp_configs / mcp_strategy are passed to main only when not None", main.kw["mcp_configs"] == [{"name": "srv"}] and main.kw["mcp_strategy"] == "deep")
check("max_search_results overrides main cfg.max_search_results_per_query with int()", main.cfg.max_search_results_per_query == 7)
fresh()
d = make(max_search_results=None)
check("max_search_results None leaves cfg untouched", FakeResearcher.instances[0].cfg.max_search_results_per_query == 5)
fresh()
try:
    make(max_search_results="abc")
    check("max_search_results='abc' raises ValueError in the constructor", False)
except ValueError as e:
    check("max_search_results='abc' raises ValueError in the constructor", True, str(e))
fresh()
shared_default_a = DetailedReport.__init__.__defaults__
check("mutable default arguments [] are shared across instances (source_urls default list is one object)",
      make().source_urls is make().source_urls)

head("A2. run(): order of steps, sequential subtopics (detailed_report.py:84-91, 110-120)")
fresh(sleep=0.01)
d = make()
report = run(d.run())
EXPECT = ["main.conduct:start", "main.conduct:end", "main.get_subtopics", "main.write_introduction",
          "T1.conduct:start", "T1.conduct:end", "T1.draft_titles", "T1.get_similar", "T1.write_report",
          "T2.conduct:start", "T2.conduct:end", "T2.draft_titles", "T2.get_similar", "T2.write_report",
          "main.write_report_conclusion"]
check("call order = initial research, subtopics, introduction, per subtopic (conduct, draft titles, similar, write), conclusion",
      EVENTS == EXPECT, " > ".join(EVENTS))
check("subtopics run strictly one after another (T2 starts after T1.write_report), even with awaits that yield",
      EVENTS.index("T1.write_report") < EVENTS.index("T2.conduct:start"))
check("introduction is written BEFORE any subtopic report and from the main researcher's initial context",
      EVENTS.index("main.write_introduction") < EVENTS.index("T1.conduct:start")
      and FakeResearcher.instances[0].intro_context_seen == "MAIN CTX")
check("conclusion receives the report body (subtopic reports joined), not the introduction",
      FakeResearcher.instances[0].conclusion_arg == "\n\n\n" + SCRIPT.reports["T1"] + "\n\n\n" + SCRIPT.reports["T2"])

head("A3. subtopic researcher arguments (detailed_report.py:138-165)")
sub1, sub2 = FakeResearcher.instances[1], FakeResearcher.instances[2]
main = FakeResearcher.instances[0]
check("subtopic kwargs are exactly these keys",
      set(sub1.kw) == {"query", "query_domains", "report_type", "report_source", "websocket", "headers", "parent_query",
                       "subtopics", "visited_urls", "agent", "role", "tone", "complement_source_urls", "source_urls",
                       "mcp_configs", "mcp_strategy"}, sorted(sub1.kw))
check("report_type 'subtopic_report', query = subtopic task, parent_query = main query",
      sub1.kw["report_type"] == "subtopic_report" and sub1.kw["query"] == "T1" and sub1.kw["parent_query"] == "Q")
check("document_urls, documents, config_path, log_handler, verbose, context, max_subtopics are NOT passed to subtopic researchers",
      not ({"document_urls", "documents", "config_path", "log_handler", "verbose", "context", "max_subtopics"} & set(sub1.kw)))
check("visited_urls: the very same set object is shared (main.visited_urls is d.global_urls is sub.kw['visited_urls'])",
      main.visited_urls is d.global_urls and sub1.kw["visited_urls"] is d.global_urls and sub2.kw["visited_urls"] is d.global_urls)
check("agent and role are the main researcher's chosen values", sub1.kw["agent"] == "Agent-X" and sub1.kw["role"] == "Role-X")
check("mcp_configs / mcp_strategy are copied from the main researcher (None / 'fast' when MCP unused)",
      sub1.kw["mcp_configs"] is None and sub1.kw["mcp_strategy"] == "fast")
check("subtopics=self.subtopics ([]) goes to subtopic researchers; the main researcher never gets it",
      sub1.kw["subtopics"] == [] and "subtopics" not in main.kw)
check("subtopic researcher's context is overwritten by its own conduct_research (T1 context is 'T1 CTX', not the preset)",
      sub1.context == "T1 CTX")

fresh()
d = make(mcp_configs=[{"name": "srv"}], mcp_strategy="deep", max_search_results=9, source_urls=["https://s1"],
         complement_source_urls=True, query_domains=["a.com"], tone="Formal", headers={"k": "v"}, websocket=WS(),
         document_urls=["https://doc"], config_path="cfg.json", report_source="hybrid")
run(d.run())
m, s1 = FakeResearcher.instances[0], FakeResearcher.instances[1]
check("when set: subtopic gets source_urls, complement_source_urls, query_domains, tone, headers, websocket, report_source",
      s1.kw["source_urls"] == ["https://s1"] and s1.kw["complement_source_urls"] is True and s1.kw["query_domains"] == ["a.com"]
      and s1.kw["tone"] == "Formal" and s1.kw["headers"] == {"k": "v"} and s1.kw["websocket"] is d.websocket
      and s1.kw["report_source"] == "hybrid")
check("main got document_urls and config_path, subtopic got neither",
      m.kw["document_urls"] == ["https://doc"] and m.kw["config_path"] == "cfg.json" and "document_urls" not in s1.kw and "config_path" not in s1.kw)
check("mcp_configs/strategy: subtopic copies the main researcher's attributes", s1.kw["mcp_configs"] == [{"name": "srv"}] and s1.kw["mcp_strategy"] == "deep")
check("max_search_results=9 is set on the main and on every subtopic researcher's cfg",
      m.cfg.max_search_results_per_query == 9 and all(i.cfg.max_search_results_per_query == 9 for i in FakeResearcher.instances[1:]))
check("the same websocket object is shared by main and subtopic researchers", m.kw["websocket"] is s1.kw["websocket"])

head("A4. global state: visited_urls, written sections, existing_headers, hashable_context")
fresh()
d = make()
run(d.run())
sub1, sub2 = FakeResearcher.instances[1], FakeResearcher.instances[2]
check("global_urls accumulates every researcher's visited URLs (same object, duplicates collapse)",
      d.global_urls == {"https://m1", "https://m2", "https://t1a", "https://t2a"})
check("the two update() calls at run():89 and :188 act on the same object, so they change nothing",
      d.gpt_researcher.visited_urls is d.global_urls)
check("T1 write_report saw existing_headers == [] and T2 saw only T1's entry",
      sub1.write_args["existing_headers"] == [] and
      sub2.write_args["existing_headers"] == [{"subtopic task": "T1", "headers": [
          {"level": 2, "text": "T1 Heading", "children": [{"level": 3, "text": "A1"}, {"level": 3, "text": "B1"}]}]}],
      json.dumps(sub2.write_args["existing_headers"]))
check("after the run existing_headers has one entry per subtopic in order",
      [e["subtopic task"] for e in d.existing_headers] == ["T1", "T2"])
check("relevant_written_contents given to write_report is exactly what the similar-content step returned",
      sub1.write_args["relevant_written_contents"] == ["SIMILAR-1"])
check("T1 similar-content call: written sections so far == [] ; T2 call gets T1's sections (empty-body headings skipped)",
      sub1.similar_args[2] == [] and sub2.similar_args[2] ==
      [{"section_title": "A1", "written_content": "text a1 (c)"}, {"section_title": "B1", "written_content": "text b1"}],
      json.dumps(sub2.similar_args[2]))
check("global_written_sections after the run = sections of T1 then T2",
      [s["section_title"] for s in d.global_written_sections] == ["A1", "B1", "A2"])
check("write_report is called with only existing_headers and relevant_written_contents (no ext_context / custom_prompt)",
      set(sub1.write_args) == {"existing_headers", "relevant_written_contents"})

hc = DetailedReport._hashable_context
check("_hashable_context: str items -> str, other -> str(), dict -> 'Title: {title}\\nContent: {body or content}'",
      hc(None, ["a", 3, {"title": "T", "body": "B"}, {"content": "C"}, {}]) ==
      ["a", "3", "Title: T\nContent: B", "Title: No title\nContent: C", "Title: No title\nContent: "])
chars = hc(None, "abca")
check("_hashable_context('abca') iterates the STRING character by character -> ['a','b','c','a']", chars == ["a", "b", "c", "a"])
check("so global_context after a run is the unique CHARACTERS of the last subtopic's context string",
      sorted(d.global_context) == sorted(set("T2 CTX")), str(sorted(d.global_context)))
check("_hashable_context([]) == []", hc(None, []) == [])
check("list(set(...)) removes duplicates but does not keep order",
      sorted(list(set(hc(None, ["x", "y", "x"])))) == ["x", "y"])

head("A5. assembly string (detailed_report.py:197-205)")
fresh()
d = make()
report = run(d.run())
body = "\n\n\n" + SCRIPT.reports["T1"] + "\n\n\n" + SCRIPT.reports["T2"]
toc = ("## Table of Contents\n\n- T1 Heading\n    - A1\n    - B1\n- T2 Heading\n    - A2\n")
refs = "\n\n\n## References\n\n- [https://m1](https://m1)\n- [https://m2](https://m2)\n- [https://t1a](https://t1a)\n- [https://t2a](https://t2a)\n"
expected = SCRIPT.intro + "\n\n" + toc + "\n\n" + body + "\n\n" + SCRIPT.conclusion + refs
check("report == intro + '\\n\\n' + toc + '\\n\\n' + body + '\\n\\n' + conclusion + references(of the conclusion only)", report == expected)
print("  --- report (repr) ---")
print("  " + repr(report))
check("toc is built from the body only (intro and conclusion headings are not listed)",
      "Intro" not in toc and "Conclusion" not in toc and report.count("## Table of Contents") == 1)
check("references are appended to the conclusion and listed sorted; they end the report",
      report.endswith("- [https://t2a](https://t2a)\n") and report.index("## References") > report.index("## Conclusion"))
check("each non-empty subtopic report is prefixed by three newlines in the body", body.count("\n\n\n##") == 2)

head("A6. empty / failed pieces inside the assembly")
fresh(reports={"T1": "", "T2": "I could not gather any source material for \"T2\". No sources were retrieved (searches may have returned nothing or been blocked), so I am not able to produce a reliable, sourced report."})
d = make()
report = run(d.run())
check("a '' subtopic report is left out of the body but its state updates still happen (existing_headers entry with headers [])",
      "T1 Heading" not in report and d.existing_headers[0] == {"subtopic task": "T1", "headers": []})
check("the fixed no-material sentence (report-writing R-03) is truthy, so it IS appended to the body like a report",
      "I could not gather any source material for \"T2\"" in report)
check("that sentence has no header: toc is just the title line, global_written_sections stays empty",
      "## Table of Contents\n\n\n\n" in report and d.global_written_sections == [])
fresh(subtopics_obj=[])
d = make()
SCRIPT.intro, SCRIPT.conclusion = "", ""
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    report = run(d.run())
check("get_subtopics returning [] (what construct_subtopics returns on failure) -> prints 'Unexpected subtopics data format: []' and continues with no subtopic",
      "Unexpected subtopics data format: []" in buf.getvalue() and not any(e.startswith("T1") for e in EVENTS))
check("no-subtopic report with failed intro and conclusion: toc title + references only",
      report == "" + "\n\n" + "## Table of Contents\n\n" + "\n\n" + "" + "\n\n" + "" + "\n\n\n## References\n\n- [https://m1](https://m1)\n- [https://m2](https://m2)\n",
      repr(report))
check("conclusion is still requested with an empty body when there are no subtopics",
      "main.write_report_conclusion" in EVENTS and FakeResearcher.instances[0].conclusion_arg == "")
fresh(subtopics_obj=SimpleNamespace(subtopics=[]))
d = make()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    run(d.run())
check("a parsed object whose .subtopics is empty takes the same 'Unexpected subtopics data format' path", "Unexpected subtopics data format" in buf.getvalue())
fresh(subtopics_obj=SimpleNamespace(subtopics=[SimpleNamespace(task=f"T{i}") for i in (1, 2, 3, 4, 5)]))
SCRIPT.contexts.update({f"T{i}": "c" for i in (3, 4, 5)})
SCRIPT.urls.update({f"T{i}": [] for i in (3, 4, 5)})
SCRIPT.reports.update({f"T{i}": f"## T{i}\n\ntext" for i in (3, 4, 5)})
d = make()
run(d.run())
check("DetailedReport does not cap or deduplicate subtopics: 5 parsed subtopics -> 5 subtopic researchers",
      len([i for i in FakeResearcher.instances if i.report_type == "subtopic_report"]) == 5)

head("A7. failures propagate; nothing is caught in DetailedReport")
fresh(raise_in={("T2", "conduct_research"): RuntimeError("boom in T2")})
d = make()
try:
    run(d.run())
    check("exception in a subtopic researcher aborts run()", False)
except RuntimeError as e:
    check("exception in a subtopic researcher aborts run() with that exception", str(e) == "boom in T2")
check("... after T1 is fully processed and the introduction already written; no conclusion, no partial report",
      "T1.write_report" in EVENTS and "main.write_introduction" in EVENTS and "main.write_report_conclusion" not in EVENTS
      and [e["subtopic task"] for e in d.existing_headers] == ["T1"])
fresh(raise_in={("Q", "conduct_research"): RuntimeError("boom initial")})
d = make()
try:
    run(d.run())
except RuntimeError:
    pass
check("exception in the initial research stops before get_subtopics", EVENTS == ["main.conduct:start"])
fresh(raise_in={("T1", "write_report"): RuntimeError("boom write")})
d = make()
try:
    run(d.run())
    check("exception in a subtopic write_report aborts run()", False)
except RuntimeError:
    check("exception in a subtopic write_report aborts run() (global_written_sections/existing_headers not updated for it)",
          d.existing_headers == [] and d.global_written_sections == [])

head("A8. draft section titles never reach the similar-content search")
fresh(draft_titles=["### A1", "### B1"])
d = make()
run(d.run())
t1 = FakeResearcher.instances[1]
check("the real get_draft_section_titles returns list[str]; detailed_report.py:169-170 turns a non-str into str(list)",
      str(SCRIPT.draft_titles) == "['### A1', '### B1']")
check("extract_headers(str(list)) finds NO header (the '###' is mid-line), so the title list passed on is []",
      mdp.extract_headers(str(SCRIPT.draft_titles)) == [] and t1.similar_args[1] == [])
check("only a real str with line-start '###' would produce headers", [h["text"] for h in mdp.extract_headers("### A1\n### B1")] == ["A1", "B1"])
check("empty list from a failed LLM call: str([]) = '[]' -> [] as well", mdp.extract_headers(str([])) == [])
parsed = mdp.extract_headers(str(SCRIPT.draft_titles))
check("get_similar_written_contents... is called as (task, [], global_written_sections): queries = [task] only",
      t1.similar_args[0] == "T1" and t1.similar_args[1] == [])

head("A9. existing_headers / relevant_written_contents as the subtopic prompt shows them (prompts.py:595-670, real)")
eh = [{"subtopic task": "T1", "headers": [{"level": 2, "text": "T1 Heading", "children": [{"level": 3, "text": "A1"}]}]}]
rw = ["Title: A1\nContent: text a1 (c)\n"]
p = PromptFamily.generate_subtopic_report_prompt("T2", eh, rw, "Q", "CTX", report_format="APA", total_words=1200, tone=enum_mod.Tone.Objective)
check("existing_headers is inserted with Python repr (single quotes, key 'subtopic task')",
      "{'subtopic task': 'T1', 'headers': [{'level': 2, 'text': 'T1 Heading', 'children': [{'level': 3, 'text': 'A1'}]}]}" in p)
check("relevant_written_contents strings are inserted with repr (the newline is the two characters backslash-n)",
      "['Title: A1\\nContent: text a1 (c)\\n']" in p)

head("A10. ContextManager: similar written contents (real context_manager.py + real lexical.py)")


class Memory:
    def __init__(self, embeddings=None, error=None):
        self.embeddings, self.error = embeddings, error

    def get_embeddings(self):
        if self.error:
            raise self.error
        return self.embeddings


class FakeCR:  # researcher stand-in for ContextManager
    def __init__(self, memory, kwargs=None, verbose=False):
        self.memory, self.kwargs, self.verbose, self.websocket = memory, kwargs or {}, verbose, None
        self.costs = []
        self.prompt_family = PromptFamily

    def add_costs(self, c):
        self.costs.append(c)


sections = [
    {"section_title": "Battery chemistry", "written_content": "Lithium iron phosphate batteries last longer and are safer."},
    {"section_title": "Solar panels", "written_content": "Panel efficiency has risen and installation costs fell."},
    {"section_title": "Grid storage", "written_content": "Grid storage uses batteries to shift evening demand."},
]
class BoomWCC:
    def __init__(self, *a, **k):
        raise AssertionError("WrittenContentCompressor must not be built on the keyword path")


context_manager.WrittenContentCompressor = BoomWCC
cm = context_manager.ContextManager(FakeCR(Memory(error=RuntimeError("no embedding model"))))
res = run(cm.get_similar_written_contents_by_draft_section_titles("battery storage", [], sections))
check("no embedding model (get_embeddings raises) -> rank_written_sections keyword ranking is used, result is list[str]",
      isinstance(res, list) and all(isinstance(x, str) for x in res) and len(res) >= 1, repr(res))
check("each item is 'Title: <section_title>\\nContent: <chunk>\\n'", all(x.startswith("Title: ") and "\nContent: " in x and x.endswith("\n") for x in res))
check("the keyword path never builds WrittenContentCompressor (constructing it would raise AssertionError here)", True)
check("empty written_contents (first subtopic) with keyword ranking -> []",
      run(cm.get_similar_written_contents_by_draft_section_titles("battery storage", [], [])) == [])

# --- rank_written_sections itself
r = lexical.rank_written_sections("battery storage", sections, max_results=10)
titles_ranked = [x.split("\n")[0] for x in r]
check("rank_written_sections: only sections scoring >= 0.5 * best are returned, best first",
      titles_ranked[0] in ("Title: Grid storage", "Title: Battery chemistry") and "Title: Solar panels" not in titles_ranked, str(titles_ranked))
check("rank_written_sections: no keyword overlap -> []", lexical.rank_written_sections("zebra giraffe", sections) == [])
check("rank_written_sections: empty sections -> []", lexical.rank_written_sections("battery", []) == [])
check("rank_written_sections: max_results caps the list", len(lexical.rank_written_sections("battery storage", sections, max_results=1)) == 1)
check("rank_written_sections: missing keys -> '' title / '' content do not raise",
      lexical.rank_written_sections("battery", [{"written_content": "battery"}, {"section_title": "battery"}, {}]) is not None)
r1 = lexical.rank_written_sections("battery storage", sections)
check("rank_written_sections: title is part of the scored text (a section matched only by its title is found)",
      lexical.rank_written_sections("solar", [{"section_title": "Solar", "written_content": "unrelated words only"}]) ==
      ["Title: Solar\nContent: unrelated words only\n"])
check("rank_written_sections: splitter built with (chunk_size=1000, chunk_overlap=100)", (1000, 100) in SPLITTER_CALLS)

# --- embeddings available -> WrittenContentCompressor
calls = []


class RecWCC:
    def __init__(self, documents, embeddings, similarity_threshold, **kw):
        self.args = (documents, embeddings, similarity_threshold, kw)

    async def async_get_context(self, query, max_results=5, cost_callback=None):
        calls.append((query, max_results, cost_callback is not None, self.args[2]))
        return {"battery storage": ["S1", "S2"], "### x": ["S2", "S3"]}.get(query, [])


context_manager.WrittenContentCompressor = RecWCC
fcr = FakeCR(Memory(embeddings="EMB"))
cm = context_manager.ContextManager(fcr)
res = run(cm.get_similar_written_contents_by_draft_section_titles("battery storage", ["### x", "### y"], sections))
check("embeddings available: one WrittenContentCompressor call per query in [subtopic] + draft titles (3 calls)", len(calls) == 3, str(calls))
check("each call uses similarity_threshold=0.5, max_results=10 and passes a cost_callback",
      all(c[3] == 0.5 and c[1] == 10 and c[2] for c in calls))
check("results are united as a set (duplicates collapse): {S1,S2,S3}", sorted(res) == ["S1", "S2", "S3"], repr(res))
many = []


class ManyWCC(RecWCC):
    async def async_get_context(self, query, max_results=5, cost_callback=None):
        return [f"{query}-{i}" for i in range(8)]


context_manager.WrittenContentCompressor = ManyWCC
res = run(context_manager.ContextManager(FakeCR(Memory(embeddings="EMB"))).get_similar_written_contents_by_draft_section_titles(
    "a", ["b", "c"], sections))
check("union of 24 distinct strings is cut to the first 10 of list(set) (max_results=10); which 10 depends on set order",
      len(res) == 10 and set(res) <= {f"{q}-{i}" for q in "abc" for i in range(8)})


class FailWCC(RecWCC):
    async def async_get_context(self, query, max_results=5, cost_callback=None):
        raise RuntimeError("embedding API down")


context_manager.WrittenContentCompressor = FailWCC
try:
    run(context_manager.ContextManager(FakeCR(Memory(embeddings="EMB"))).get_similar_written_contents_by_draft_section_titles("a", [], sections))
    check("an error inside WrittenContentCompressor is NOT caught (only get_embeddings() errors fall back to keywords)", False)
except RuntimeError as e:
    check("an error inside WrittenContentCompressor is NOT caught (only get_embeddings() errors fall back to keywords)", str(e) == "embedding API down")
context_manager.WrittenContentCompressor = compression.WrittenContentCompressor

head("A11. real WrittenContentCompressor with stand-in langchain pieces")
SPLITTER_CALLS.clear(); FILTER_CALLS.clear(); COST_CALLS.clear()
docs = [{"section_title": "Keep me", "written_content": "KEEP this paragraph.\n\nnot this one"},
        {"section_title": "Drop me", "written_content": "nothing relevant"}]
wcc = compression.WrittenContentCompressor(documents=docs, embeddings="EMB", similarity_threshold=0.5)
costs = []
out = run(wcc.async_get_context("q", max_results=5, cost_callback=costs.append))
check("output items are 'Title: <section_title>\\nContent: <page_content>\\n' built from the kept chunks", out == ["Title: Keep me\nContent: KEEP this paragraph.\n"], repr(out))
check("pipeline built as splitter(1000,100) then EmbeddingsFilter(threshold=0.5)", SPLITTER_CALLS == [(1000, 100)] and FILTER_CALLS == [0.5])
check("cost_callback is called once BEFORE the retrieval with estimate_embedding_cost(OPENAI_EMBEDDING_MODEL, all documents)",
      costs == [0.25] and COST_CALLS == [("stub-embedding-model", 2)])
check("no cost_callback -> no cost call", (COST_CALLS.clear() or run(wcc.async_get_context("q"))) and COST_CALLS == [])
top = run(compression.WrittenContentCompressor(docs * 3, "EMB", 0.5).async_get_context("q", max_results=2))
check("max_results truncates the formatted list (3 kept, 2 returned)", len(top) == 2)
sec = ctx_retriever.SectionRetriever(sections=[{"section_title": "T", "written_content": "C"}, {}])
dd = sec._get_relevant_documents("q", run_manager=None)
check("SectionRetriever: one Document per section, metadata only section_title ('' when missing), content '' when missing",
      [(x.page_content, x.metadata) for x in dd] == [("C", {"section_title": "T"}), ("", {"section_title": ""})])

head("A12. construct_subtopics (real llm.py) with fake langchain chain")


class Chain:
    def __init__(self, parts):
        self.parts = parts

    def __or__(self, other):
        return Chain(self.parts + [other])

    async def ainvoke(self, inputs, **kw):
        tmpl, model, parser = self.parts
        LLM_CALLS.append({"inputs": inputs, "kw": kw, "rendered": tmpl.render(inputs)})
        return parser.parse(model.reply())


class PromptTemplate:
    def __init__(self, template, input_variables, partial_variables):
        self.template, self.input_variables, self.partial = template, input_variables, partial_variables
        PT_ARGS.append((input_variables, sorted(partial_variables)))

    def render(self, inputs):
        return self.template.format(**inputs, **self.partial)

    def __or__(self, other):
        return Chain([self, other])


class PydanticOutputParser:
    def __init__(self, pydantic_object):
        self.cls = pydantic_object

    def get_format_instructions(self):
        return "<FORMAT INSTRUCTIONS STAND-IN>"

    def parse(self, text):
        return self.cls.model_validate_json(text)


LLM_CALLS, PT_ARGS, PROVIDER_KW = [], [], []
REPLY = {"text": ""}


class FakeModel:
    def reply(self):
        if isinstance(REPLY["text"], Exception):
            raise REPLY["text"]
        return REPLY["text"]


mod("langchain_core.output_parsers", PydanticOutputParser=PydanticOutputParser)
mod("langchain_core.prompts", PromptTemplate=PromptTemplate)
mod("gpt_researcher.llm_provider.generic.base", NO_SUPPORT_TEMPERATURE_MODELS=[],
    SUPPORT_REASONING_EFFORT_MODELS=["reasoning-model"],
    ReasoningEfforts=types.SimpleNamespace(High=types.SimpleNamespace(value="high"), Medium=types.SimpleNamespace(value="medium")))
llm_mod = load("gpt_researcher.utils.llm", os.path.join(PKG, "utils", "llm.py"))


def fake_get_llm(provider_name, **kw):
    PROVIDER_KW.append((provider_name, kw))
    return SimpleNamespace(llm=FakeModel())


llm_mod.get_llm = fake_get_llm
cfg = SimpleNamespace(smart_llm_model="plain-model", smart_llm_provider="openai", llm_kwargs={}, temperature=0.4,
                      smart_token_limit=12000, max_subtopics=3)
REPLY["text"] = json.dumps({"subtopics": [{"task": "S1"}, {"task": "S2"}]})
out = run(llm_mod.construct_subtopics("Q", "CTX", cfg, subtopics=[], prompt_family=PromptFamily))
check("success: returns the parsed Subtopics object (pydantic) with Subtopic.task", isinstance(out, validators.Subtopics) and [s.task for s in out.subtopics] == ["S1", "S2"])
check("template input variables task/data/subtopics/max_subtopics; chain input carries config.max_subtopics (3), task, data, subtopics",
      PT_ARGS[-1][0] == ["task", "data", "subtopics", "max_subtopics"] and LLM_CALLS[-1]["inputs"] ==
      {"task": "Q", "data": "CTX", "subtopics": [], "max_subtopics": 3})
check("the limit exists only as prompt text 'Limit the number of subtopics to a maximum of 3'",
      "Limit the number of subtopics to a maximum of 3" in LLM_CALLS[-1]["rendered"])
check("provider: config.smart_llm_provider, model config.smart_llm_model, temperature=config.temperature (non-reasoning model), max_tokens=smart_token_limit; no cost_callback anywhere",
      PROVIDER_KW[-1] == ("openai", {"model": "plain-model", "temperature": 0.4, "max_tokens": 12000}))
cfg2 = SimpleNamespace(**{**cfg.__dict__, "smart_llm_model": "reasoning-model", "llm_kwargs": {"foo": 1}})
run(llm_mod.construct_subtopics("Q", "CTX", cfg2, subtopics=[], prompt_family=PromptFamily))
check("reasoning model: reasoning_effort='high' instead of temperature; llm_kwargs merged",
      PROVIDER_KW[-1][1] == {"model": "reasoning-model", "foo": 1, "reasoning_effort": "high", "max_tokens": 12000})
REPLY["text"] = json.dumps({"subtopics": [{"task": f"S{i}"} for i in range(5)]})
out = run(llm_mod.construct_subtopics("Q", "CTX", cfg, subtopics=[], prompt_family=PromptFamily))
check("more subtopics than max_subtopics (3) are returned untouched: no truncation in code", len(out.subtopics) == 5)
check("duplicates are not removed by the model either (two identical tasks stay two)",
      len(validators.Subtopics.model_validate({"subtopics": [{"task": "a"}, {"task": "a"}]}).subtopics) == 2)
for label, text in [("LLM exception", RuntimeError("llm down")), ("invalid JSON", "not json"),
                    ("empty task (min_length=1)", json.dumps({"subtopics": [{"task": ""}]})),
                    ("wrong shape", json.dumps({"topics": []}))]:
    REPLY["text"] = text
    if label == "wrong shape":
        # model_validate_json of {"topics": []} succeeds with default [] -> not a failure
        o = run(llm_mod.construct_subtopics("Q", "CTX", cfg, subtopics=["PRE"], prompt_family=PromptFamily))
        check(f"{label}: pydantic default 'subtopics: []' makes it a valid EMPTY Subtopics (no exception)",
              isinstance(o, validators.Subtopics) and o.subtopics == [])
        continue
    o = run(llm_mod.construct_subtopics("Q", "CTX", cfg, subtopics=["PRE"], prompt_family=PromptFamily))
    check(f"{label}: exception is logged and the INPUT `subtopics` list is returned (not a Subtopics object)", o == ["PRE"])
REPLY["text"] = "not json"
o = run(llm_mod.construct_subtopics("Q", "CTX", cfg, prompt_family=PromptFamily))
check("failure with the default subtopics argument returns [] (the mutable default list)", o == [])
try:
    validators.Subtopic(task="")
    check("Subtopic(task='') raises ValidationError", False)
except pydantic.ValidationError:
    check("Subtopic(task='') raises ValidationError", True)

head("A13. server/CLI call shapes (arguments only; backend/server/websocket_manager.py:144-157, cli.py:274-281 are read, not run)")
src_ws = open(os.path.join(REPO, "backend", "server", "websocket_manager.py"), encoding="utf-8").read()
src_cli = open(os.path.join(REPO, "cli.py"), encoding="utf-8").read()
check("server passes report_type=<'detailed_report'>, report_source, source_urls, document_urls, tone, config_path, websocket=logs_handler, headers, mcp_*, max_search_results",
      "researcher = DetailedReport(" in src_ws and "websocket=logs_handler" in src_ws and "document_urls=document_urls" in src_ws)
check("CLI passes only query, query_domains, report_type='research_report', report_source='web_search'",
      'report_source="web_search"' in src_cli and 'report_type="research_report"' in src_cli)

head("A14. CLI report_source='web_search' has no research branch (real researcher.py branch text)")
rs = open(os.path.join(PKG, "skills", "researcher.py"), encoding="utf-8").read()
branches = ["ReportSource.Web.value", "ReportSource.Local.value", "ReportSource.Hybrid.value", "ReportSource.Azure.value",
            "ReportSource.LangChainDocuments.value", "ReportSource.LangChainVectorStore.value"]
values = {enum_mod.ReportSource.Web.value, enum_mod.ReportSource.Local.value, enum_mod.ReportSource.Hybrid.value,
          enum_mod.ReportSource.Azure.value, enum_mod.ReportSource.LangChainDocuments.value, enum_mod.ReportSource.LangChainVectorStore.value}
check("'web_search' is not one of the six values compared in ResearchConductor.conduct_research", "web_search" not in values and all(b in rs for b in branches), str(sorted(values)))

print("\n" + "=" * 8 + f" SUMMARY: {sum(RESULTS)} PASS / {len(RESULTS) - sum(RESULTS)} FAIL of {len(RESULTS)} checks")
sys.exit(0 if all(RESULTS) else 1)
