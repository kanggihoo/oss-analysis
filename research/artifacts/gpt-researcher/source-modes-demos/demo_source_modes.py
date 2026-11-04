"""Offline demo for reports/gpt-researcher/capabilities/source-modes.md (2026-10-22).

Runs the REAL source of these files (repos/gpt-researcher @ 3582a68) without network
and without installing packages:
  gpt_researcher/skills/researcher.py   (ResearchConductor: conduct_research, _get_context_by_web_search,
                                          _process_sub_query, _get_context_from_initial_results,
                                          _combine_mcp_and_web_context, _get_new_urls)
  gpt_researcher/document/document.py, online_document.py, azure_document_loader.py, langchain_document.py
  gpt_researcher/utils/url_security.py, utils/enum.py
  gpt_researcher/config/config.py (+ config/variables/*.py): only the Config() constructor path for DOC_PATH
  prompts.py: only the three join_local_web_documents functions, extracted with ast.

NOT installed here, so replaced by stubs (and therefore NOT verified by this demo):
- langchain_community.document_loaders.*: stub loader classes that mimic only the interface
  (constructor(file_path), .load() -> [Document(page_content, metadata={"source": path})]).
  Real parsing of pdf/docx/pptx/csv/xlsx/epub/md/html and what the real constructors do when an
  optional package (unstructured, pymupdf, bs4) is missing are NOT verified. "md"/"html"/"txt" stubs just
  return the raw file text. The stub PyMuPDFLoader returns two pages for any file.
- langchain_core.documents.Document: minimal stand-in.
- aiohttp: scripted fake (no socket). Real redirect handling and the meaning of timeout=6 are NOT verified.
- azure.storage.blob.BlobServiceClient: in-memory fake. Real Azure behaviour is NOT verified.
- json_repair, llm_provider.generic.base (ReasoningEfforts, _SUPPORTED_PROVIDERS), memory.embeddings
  (_SUPPORTED_PROVIDERS), retrievers.utils.get_all_retriever_names: stubs so that the real Config() can be
  constructed. Only Config.doc_path / report_source behaviour is looked at.
- gpt_researcher/__init__.py, skills/__init__.py, utils/__init__.py, actions/ (agent_creator,
  query_processing, utils), utils/logging_config: skipped or stubbed. Retrievers, scrapers, LLM calls,
  context selection (select_context) are replaced by recorders; this demo does not verify them.
- The researcher object passed to ResearchConductor is a SimpleNamespace with only the fields the
  real code reads.

Run: python -I demo_source_modes.py
"""
import ast
import asyncio
import collections
import importlib
import io
import os
import sys
import tempfile
import textwrap
import types
from contextlib import redirect_stdout

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", "repos", "gpt-researcher"))
PKG = os.path.join(REPO, "gpt_researcher")
SCRATCH = os.environ.get("DEMO_TMP") or tempfile.gettempdir()
tempfile.tempdir = SCRATCH


# ---------------------------------------------------------------- STUBS
class Doc:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata if metadata is not None else {}


CONSTRUCTED = []  # (loader class name, file_path)
BEHAVIOR = {"construct_fail": set(), "load_fail": set()}


def make_loader(name, mode):
    class L:
        def __init__(self, file_path, **kw):
            CONSTRUCTED.append((name, file_path))
            if name in BEHAVIOR["construct_fail"]:
                raise ImportError(f"stub: {name} dependency missing")
            self.file_path = file_path

        def load(self):
            if name in BEHAVIOR["load_fail"]:
                raise RuntimeError(f"stub: {name} could not parse the file")
            if mode == "text":
                with open(self.file_path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
                return [Doc(text, {"source": self.file_path})]
            if mode == "pdf":
                b = os.path.basename(self.file_path)
                return [Doc(f"[stub pdf page 1 of {b}]", {"source": self.file_path, "page": 0}),
                        Doc(f"[stub pdf page 2 of {b}]", {"source": self.file_path, "page": 1})]
            b = os.path.basename(self.file_path)
            return [Doc(f"[stub {name} parsed {b}]", {"source": self.file_path})]

    L.__name__ = name
    return L


def install_stubs():
    m = types.ModuleType("langchain_core"); sys.modules["langchain_core"] = m
    m = types.ModuleType("langchain_core.documents"); m.Document = Doc
    sys.modules["langchain_core.documents"] = m

    lc = types.ModuleType("langchain_community")
    sys.modules["langchain_community"] = lc
    dl = types.ModuleType("langchain_community.document_loaders")
    spec = {"PyMuPDFLoader": "pdf", "TextLoader": "text", "UnstructuredMarkdownLoader": "text",
            "BSHTMLLoader": "text", "UnstructuredCSVLoader": "x", "UnstructuredEPubLoader": "x",
            "UnstructuredExcelLoader": "x", "UnstructuredPowerPointLoader": "x",
            "UnstructuredWordDocumentLoader": "x"}
    for n, mode in spec.items():
        setattr(dl, n, make_loader(n, mode))
    sys.modules["langchain_community.document_loaders"] = dl

    # aiohttp fake
    ai = types.ModuleType("aiohttp")

    class ClientError(Exception):
        pass

    ai.ClientError = ClientError
    ai.REQUESTS = []
    ai.RESPONSES = {}

    class _Resp:
        def __init__(self, status, body):
            self.status = status
            self._body = body

        async def read(self):
            return self._body

    class _GetCtx:
        def __init__(self, url):
            self.url = url

        async def __aenter__(self):
            r = ai.RESPONSES[self.url]
            if isinstance(r, Exception):
                raise r
            return _Resp(*r)

        async def __aexit__(self, *a):
            return False

    class ClientSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def get(self, url, headers=None, timeout=None):
            ai.REQUESTS.append({"url": url, "headers": headers, "timeout": timeout})
            return _GetCtx(url)

    ai.ClientSession = ClientSession
    sys.modules["aiohttp"] = ai

    # azure fake
    for n in ("azure", "azure.storage"):
        sys.modules[n] = types.ModuleType(n)
    az = types.ModuleType("azure.storage.blob")
    az.CALLS = []
    az.BLOBS = {}

    class _Blob:
        def __init__(self, name):
            self.name = name

    class _Data:
        def __init__(self, b):
            self.b = b

        def readall(self):
            return self.b

    class _BlobClient:
        def __init__(self, name):
            self.name = name

        def download_blob(self):
            return _Data(az.BLOBS[self.name])

    class _Container:
        def list_blobs(self):
            return [_Blob(n) for n in az.BLOBS]

        def get_blob_client(self, name):
            return _BlobClient(name)

    class _Client:
        def get_container_client(self, name):
            az.CALLS.append(("get_container_client", name))
            return _Container()

    class BlobServiceClient:
        @staticmethod
        def from_connection_string(cs):
            az.CALLS.append(("from_connection_string", cs))
            return _Client()

    az.BlobServiceClient = BlobServiceClient
    sys.modules["azure.storage.blob"] = az

    # bare packages so the heavy __init__ files are skipped
    for name, sub in (("gpt_researcher", ""), ("gpt_researcher.utils", "utils"), ("gpt_researcher.skills", "skills")):
        pk = types.ModuleType(name)
        pk.__path__ = [os.path.join(PKG, sub) if sub else PKG]
        sys.modules[name] = pk

    lg = types.ModuleType("gpt_researcher.utils.logging_config")
    lg.get_json_handler = lambda: None
    sys.modules["gpt_researcher.utils.logging_config"] = lg

    sys.modules["gpt_researcher.actions"] = types.ModuleType("gpt_researcher.actions")
    ac = types.ModuleType("gpt_researcher.actions.agent_creator")

    async def choose_agent(**kw):
        raise AssertionError("choose_agent must not be reached: agent/role are preset")

    ac.choose_agent = choose_agent
    sys.modules["gpt_researcher.actions.agent_creator"] = ac
    qp = types.ModuleType("gpt_researcher.actions.query_processing")
    qp.get_search_results = None
    qp.plan_research_outline = None
    sys.modules["gpt_researcher.actions.query_processing"] = qp
    au = types.ModuleType("gpt_researcher.actions.utils")

    async def stream_output(*a, **k):
        return None

    au.stream_output = stream_output
    sys.modules["gpt_researcher.actions.utils"] = au


    # stubs needed to construct the real Config
    import json as _json
    jr = types.ModuleType("json_repair"); jr.loads = _json.loads
    sys.modules["json_repair"] = jr
    import typing as _typing
    te = types.ModuleType("typing_extensions"); te.TypedDict = _typing.TypedDict
    sys.modules["typing_extensions"] = te
    import enum as _enum

    class ReasoningEfforts(_enum.Enum):
        High = "high"
        Medium = "medium"
        Low = "low"

    for n in ("gpt_researcher.llm_provider", "gpt_researcher.llm_provider.generic"):
        sys.modules[n] = types.ModuleType(n)
    lb = types.ModuleType("gpt_researcher.llm_provider.generic.base")
    lb.ReasoningEfforts = ReasoningEfforts
    lb._SUPPORTED_PROVIDERS = {"openai"}
    sys.modules["gpt_researcher.llm_provider.generic.base"] = lb
    sys.modules["gpt_researcher.memory"] = types.ModuleType("gpt_researcher.memory")
    me = types.ModuleType("gpt_researcher.memory.embeddings"); me._SUPPORTED_PROVIDERS = {"openai"}
    sys.modules["gpt_researcher.memory.embeddings"] = me
    sys.modules["gpt_researcher.retrievers"] = types.ModuleType("gpt_researcher.retrievers")
    ru = types.ModuleType("gpt_researcher.retrievers.utils"); ru.get_all_retriever_names = lambda: ["tavily"]
    sys.modules["gpt_researcher.retrievers.utils"] = ru


install_stubs()
ENUM = importlib.import_module("gpt_researcher.utils.enum")
DOC = importlib.import_module("gpt_researcher.document")
AZ_LOADER = importlib.import_module("gpt_researcher.document.azure_document_loader")
RM = importlib.import_module("gpt_researcher.skills.researcher")
AIO = sys.modules["aiohttp"]
AZ = sys.modules["azure.storage.blob"]


def head(t):
    print(f"\n======== {t}")


def show(label, value):
    print(f"  {label}: {value}")


def run(coro):
    return asyncio.run(coro)


def quiet_run(coro):
    """Run and capture what the real code print()s, so we can show it indented."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            res = run(coro)
        err = None
    except Exception as e:  # noqa
        res, err = None, e
    for line in buf.getvalue().splitlines():
        print(f"    [stdout of real code] {line}")
    return res, err


# ---------------------------------------------------------------- 0. enum
head("0. ReportSource enum (real gpt_researcher/utils/enum.py)")
show("values", [(m.name, m.value) for m in ENUM.ReportSource])

# ---------------------------------------------------------------- 1. DocumentLoader
head("1. DocumentLoader(path).load() on a directory (stub langchain loaders)")
root = tempfile.mkdtemp(prefix="srcmodes_docs_")
files = {
    "a.txt": "alpha text",
    "B.TXT": "upper-case extension",
    "notes.md": "# Title\nmd body",
    "page.html": "<html><body>hi</body></html>",
    "data.xyz": "unsupported",
    "README": "no extension",
    "empty.txt": "",
    "doc.pdf": "%PDF-fake",
    os.path.join("sub", "c.txt"): "nested file",
    os.path.join("sub", "a.txt"): "same basename, different folder",
}
for rel, text in files.items():
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
CONSTRUCTED.clear()
docs, err = quiet_run(DOC.DocumentLoader(root).load())
show("error", err)
for d in sorted(docs, key=lambda d: (d["url"], d["raw_content"])):
    print(f"    url={d['url']!r:12} raw_content={d['raw_content'][:40]!r} keys={sorted(d)}")
show("count", len(docs))
per_file = collections.Counter(os.path.basename(p) for _, p in CONSTRUCTED)
show("loader constructors called per file (name -> count)", dict(sorted(per_file.items())))
show("distinct loader classes constructed for data.xyz",
     sorted({n for n, p in CONSTRUCTED if p.endswith("data.xyz")}))

head("1b. DocumentLoader with a list of paths")
lst = [os.path.join(root, "a.txt"), root, os.path.join(root, "missing.txt"),
       os.path.join(root, "sub", "c.txt"), os.path.join(root, "data.xyz")]
docs, err = quiet_run(DOC.DocumentLoader(lst).load())
show("error", err)
show("urls", [d["url"] for d in docs or []])
docs, err = quiet_run(DOC.DocumentLoader([root, os.path.join(root, "missing.txt")]).load())
show("list with no valid file -> error", repr(err))

head("1c. DocumentLoader failure cases")
docs, err = quiet_run(DOC.DocumentLoader(os.path.join(root, "no-such-dir")).load())
show("nonexistent directory", repr(err))
empty = tempfile.mkdtemp(prefix="srcmodes_empty_")
docs, err = quiet_run(DOC.DocumentLoader(empty).load())
show("empty directory", repr(err))
docs, err = quiet_run(DOC.DocumentLoader(123).load())
show("path of invalid type (int)", repr(err))
BEHAVIOR["load_fail"] = {"UnstructuredMarkdownLoader"}
docs, err = quiet_run(DOC.DocumentLoader(root).load())
show("md loader .load() raises -> error", err)
show("md loader .load() raises -> urls still loaded", sorted(d["url"] for d in docs))
BEHAVIOR["load_fail"] = set()
BEHAVIOR["construct_fail"] = {"UnstructuredEPubLoader"}
docs, err = quiet_run(DOC.DocumentLoader(root).load())
show("one loader CONSTRUCTOR raises (epub) -> error", repr(err))
BEHAVIOR["construct_fail"] = set()

# ---------------------------------------------------------------- 2. OnlineDocumentLoader
head("2. OnlineDocumentLoader (fake aiohttp, real validate_url, stub loaders)")
for u in ["https://h.example/Report.PDF?sig=1", "http://h/a", "http://h/a.tar.gz", "http://h/a.txt#frag",
          "http://h/a.TXT", "http://h/dir.v2/file"]:
    show(f"_get_extension({u!r})", repr(DOC.OnlineDocumentLoader._get_extension(u)))

os.environ.pop("ALLOW_PRIVATE_URLS", None)
ok_pdf = "http://93.184.216.34/a.pdf?sig=1"
ok_txt404 = "http://93.184.216.34/b.TXT"
ok_noext = "http://93.184.216.34/c"
ok_html = "http://93.184.216.34/d.html"
ok_txt = "http://93.184.216.34/e.txt"
err_url = "http://93.184.216.34/f.txt"
AIO.REQUESTS.clear()
AIO.RESPONSES.update({
    ok_pdf: (200, b"%PDF-fake"),
    ok_txt404: (404, b""),
    ok_noext: (200, b"no extension body"),
    ok_html: (200, b"<html>x</html>"),
    ok_txt: (200, b"text body from the net"),
    err_url: AIO.ClientError("connection reset"),
})
urls = ["file:///etc/passwd", "http://127.0.0.1/x.txt", ok_pdf, ok_txt404, ok_noext, ok_html, err_url, ok_txt]
docs, err = quiet_run(DOC.OnlineDocumentLoader(urls).load())
show("error", err)
show("requests actually issued", [r["url"] for r in AIO.REQUESTS])
show("request headers / timeout of first request", (AIO.REQUESTS[0]["headers"], AIO.REQUESTS[0]["timeout"]))
for d in docs:
    exists = os.path.exists(d["url"]) if d["url"] else None
    print(f"    raw_content={d['raw_content'][:34]!r} url={d['url']!r}  url_is_original_url={d['url'] in urls}  url_file_still_exists={exists}")
docs, err = quiet_run(DOC.OnlineDocumentLoader(["file:///etc/passwd", ok_html]).load())
show("only unsafe / unsupported URLs -> error", repr(err))
os.environ["ALLOW_PRIVATE_URLS"] = "true"
AIO.REQUESTS.clear()
AIO.RESPONSES["http://127.0.0.1/x.txt"] = (200, b"private ok")
docs, err = quiet_run(DOC.OnlineDocumentLoader(["http://127.0.0.1/x.txt"]).load())
show("ALLOW_PRIVATE_URLS=true, loopback url -> request issued / docs", ([r["url"] for r in AIO.REQUESTS], [d["raw_content"] for d in docs or []]))
os.environ.pop("ALLOW_PRIVATE_URLS", None)

# ---------------------------------------------------------------- 3. Azure
head("3. AzureDocumentLoader (fake BlobServiceClient) + DocumentLoader reuse")
AZ.CALLS.clear()
AZ.BLOBS.clear()
AZ.BLOBS.update({"report.txt": b"azure report body", "sub/dir/note.md": b"# azure note"})
loader = AZ_LOADER.AzureDocumentLoader(container_name="cont", connection_string="CS")
paths = run(loader.load())
show("fake client calls", AZ.CALLS)
show("returned paths are under one mkdtemp dir", len({os.path.dirname(os.path.dirname(os.path.dirname(p))) for p in paths}) >= 1)
show("relative to temp dir", sorted(os.path.relpath(p, os.path.commonpath(paths)) for p in paths))
docs, err = quiet_run(DOC.DocumentLoader(paths).load())
show("DocumentLoader(paths) urls (folder prefix lost)", sorted(d["url"] for d in docs))
show("temp dir still exists after load (no cleanup)", all(os.path.exists(p) for p in paths))
for bad in ["../escape.txt", "/abs.txt", "a/../b.txt", "a\\..\\b.txt"]:
    try:
        AZ_LOADER.AzureDocumentLoader._get_blob_path(__import__("pathlib").Path(root).resolve(), bad)
        print(f"    _get_blob_path({bad!r}) -> accepted")
    except ValueError as e:
        print(f"    _get_blob_path({bad!r}) -> ValueError({e})")
print("    _get_blob_path('a\\\\b.txt') ->",
      os.path.relpath(AZ_LOADER.AzureDocumentLoader._get_blob_path(__import__("pathlib").Path(root).resolve(), "a\\b.txt"), root))
AZ.BLOBS.clear()
AZ.BLOBS.update({"ok.txt": b"fine", "../escape.txt": b"nope"})
try:
    run(AZ_LOADER.AzureDocumentLoader("cont", "CS").load())
except ValueError as e:
    show("unsafe blob name aborts the whole load", repr(e))
AZ.BLOBS.clear()
paths = run(AZ_LOADER.AzureDocumentLoader("cont", "CS").load())
show("empty container -> paths", paths)
docs, err = quiet_run(DOC.DocumentLoader(paths).load())
show("empty container -> DocumentLoader", repr(err))

# ---------------------------------------------------------------- 4. LangChainDocumentLoader
head("4. LangChainDocumentLoader (real file, stub Document)")
lcd = DOC.LangChainDocumentLoader([Doc("body one", {"title": "T1", "source": "S1"}),
                                   Doc("body two", {"source": "S2"}),
                                   Doc("", {"title": "T3"})])
out = run(lcd.load())
show("load()", out)
show("load(metadata_source_index='source')", run(lcd.load(metadata_source_index="source")))
show("empty list", run(DOC.LangChainDocumentLoader([]).load()))
try:
    run(DOC.LangChainDocumentLoader(None).load())
except Exception as e:
    show("None", repr(e))

# ---------------------------------------------------------------- 5. join_local_web_documents
head("5. join_local_web_documents (functions extracted from prompts.py with ast)")
src = open(os.path.join(PKG, "prompts.py"), encoding="utf-8").read()
tree = ast.parse(src)


def method_source(cls_name, meth):
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == cls_name:
            for b in n.body:
                if isinstance(b, ast.FunctionDef) and b.name == meth:
                    return textwrap.dedent(ast.get_source_segment(src, b))
    raise KeyError((cls_name, meth))


def extract(cls_name):
    code = method_source(cls_name, "join_local_web_documents")
    code = code.replace("@staticmethod\n", "").replace("@classmethod\n", "")
    ns = {}
    exec(code, ns)
    return ns["join_local_web_documents"]


default_join = extract("PromptFamily")
g3 = extract("Granite3PromptFamily")
g33 = extract("Granite33PromptFamily")
G3 = types.SimpleNamespace(_DOCUMENTS_PREFIX="<|start_of_role|>documents<|end_of_role|>\n",
                           _DOCUMENTS_SUFFIX="\n<|end_of_text|>")
show("default (docs='D', web='W')", repr(default_join("D", "W")))
show("default with failed passes ([] , [])", repr(default_join([], [])))
show("granite3 ('D','W')", repr(g3(G3, "D", "W")))
show("granite3.3 ('D','W')", repr(g33(None, "D", "W")))
for nm, fn, a in (("granite3", g3, (G3, [], "W")), ("granite3.3", g33, (None, [], "W"))):
    try:
        fn(*a)
    except Exception as e:
        show(f"{nm} with docs_context=[] (a failed pass)", repr(e))

# ---------------------------------------------------------------- 6. conduct_research branches
head("6. ResearchConductor.conduct_research branch dispatch (real code; sub-methods recorded)")


class FakeRetriever:
    def __init__(self, *a, **k):
        pass


def make_researcher(**over):
    base = dict(
        query="Q", verbose=False, websocket=None, agent="A", role="R", parent_query="", report_type="research_report",
        headers={}, prompt_family=types.SimpleNamespace(join_local_web_documents=default_join),
        retrievers=[FakeRetriever], source_urls=None, document_urls=None, complement_source_urls=False,
        query_domains=["dom.example"], documents=None, vector_store=None, vector_store_filter=None,
        report_source="web", visited_urls=set(), mcp_strategy=None,
        cfg=types.SimpleNamespace(doc_path=root, curate_sources=False, mcp_strategy="fast",
                                  max_search_results_per_query=5),
        context=[], kwargs={}, add_costs=lambda c: None, get_costs=lambda: 0.0, mcp_configs=None,
        scraper_manager=None, context_manager=None, source_curator=None,
    )
    base.update(over)
    return types.SimpleNamespace(**base)


def recorded_conductor(r):
    c = RM.ResearchConductor(r)
    calls = []

    async def fake_urls(urls):
        calls.append(("_get_context_by_urls", list(urls)))
        return "URLCTX"

    async def fake_web(query, scraped_data=None, query_domains=None):
        label = "docs" if scraped_data else "no-docs"
        calls.append(("_get_context_by_web_search", label,
                      [d["url"] for d in scraped_data] if scraped_data else None,
                      "query_domains=" + repr(query_domains)))
        return f"WEB[{label}]"

    async def fake_vs(query, flt=None):
        calls.append(("_get_context_by_vectorstore", flt))
        return ["VSCTX"]

    c._get_context_by_urls = fake_urls
    c._get_context_by_web_search = fake_web
    c._get_context_by_vectorstore = fake_vs
    return c, calls


def branch(title, **over):
    r = make_researcher(**over)
    c, calls = recorded_conductor(r)
    res, err = quiet_run(c.conduct_research())
    print(f"  -- {title}")
    for call in calls:
        print(f"       call: {call}")
    print(f"       result: {res!r}" + (f"   ERROR: {err!r}" if err else ""))
    return r


branch("web", report_source="web")
branch("web + source_urls=[] (falsy)", report_source="web", source_urls=[])
branch("local + source_urls truthy (source_urls wins, no doc loading)", report_source="local",
       source_urls=["http://u1", "http://u2"], cfg=types.SimpleNamespace(doc_path=os.path.join(root, "no-such-dir"), curate_sources=False, mcp_strategy="fast", max_search_results_per_query=5))
branch("source_urls + complement_source_urls=True", report_source="web", source_urls=["http://u1"], complement_source_urls=True)
branch("local (doc dir has files)", report_source="local")
vs_calls = []
vs = types.SimpleNamespace(load=lambda d: vs_calls.append(len(d)))
branch("local + vector_store present (excluded path; only the load call is shown)", report_source="local", vector_store=vs)
show("vector_store.load called with n documents", vs_calls)
branch("local, doc dir does not exist", report_source="local",
       cfg=types.SimpleNamespace(doc_path=os.path.join(root, "no-such-dir"), curate_sources=False, mcp_strategy="fast", max_search_results_per_query=5))
branch("hybrid, no document_urls (doc_path used)", report_source="hybrid")
branch("hybrid, document_urls given but doc_path ignored", report_source="hybrid",
       document_urls=[ok_txt, ok_pdf],
       cfg=types.SimpleNamespace(doc_path=os.path.join(root, "no-such-dir"), curate_sources=False, mcp_strategy="fast", max_search_results_per_query=5))
branch("hybrid, empty doc dir (web pass never runs)", report_source="hybrid",
       cfg=types.SimpleNamespace(doc_path=empty, curate_sources=False, mcp_strategy="fast", max_search_results_per_query=5))
branch("local + document_urls (ignored)", report_source="local", document_urls=[ok_txt])
for rs in ["static", "doc", "web_search", "online", "Local", None]:
    branch(f"unknown report_source={rs!r}", report_source=rs)
branch("langchain_vectorstore (excluded; only the dispatch)", report_source="langchain_vectorstore",
       vector_store_filter={"k": "v"})
branch("langchain_documents with 2 docs", report_source="langchain_documents",
       documents=[Doc("one", {"title": "T1"}), Doc("two", {"title": "T2"})])
branch("langchain_documents with []", report_source="langchain_documents", documents=[])
branch("langchain_documents with None", report_source="langchain_documents", documents=None)
AZ.BLOBS.clear()
AZ.BLOBS.update({"report.txt": b"azure report body"})
os.environ["AZURE_CONTAINER_NAME"] = "cont-from-env"
os.environ["AZURE_CONNECTION_STRING"] = "CS-from-env"
AZ.CALLS.clear()
branch("azure", report_source="azure")
show("fake azure client calls (env vars read)", AZ.CALLS)
os.environ.pop("AZURE_CONTAINER_NAME")
os.environ.pop("AZURE_CONNECTION_STRING")

# ---------------------------------------------------------------- 7. web-search path with supplied documents
head("7. real _get_context_by_web_search / _process_sub_query with and without supplied documents")


def web_path(title, scraped_data):
    r = make_researcher(report_source="local")
    log = []

    async def sel(query, pages):
        log.append(("select", query, len(pages)))
        return f"SEL[{query}|{len(pages)}]"

    r.context_manager = types.SimpleNamespace(get_similar_content_by_query=sel)
    c = RM.ResearchConductor(r)

    async def initial(query, query_domains=None):
        log.append(("initial_search", query, query_domains))
        return [{"href": "http://planning.example/1", "body": "snippet"}]

    async def plan(query, query_domains=None, *, search_results=None):
        log.append(("plan", "n_initial_results=%d" % len(search_results)))
        return ["sq1", "sq2"]

    async def scrape(sub_query, query_domains=None, *, initial_results=None):
        log.append(("scrape_data_by_urls", sub_query, "initial_results" if initial_results is not None else "search"))
        return [{"url": "http://scraped/" + sub_query, "raw_content": "x"}]

    c._get_initial_search_results = initial
    c.plan_research = plan
    c._scrape_data_by_urls = scrape
    res, err = quiet_run(c._get_context_by_web_search("Q", scraped_data, ["dom.example"]))
    print(f"  -- {title}")
    for e in log:
        print(f"       {e}")
    print(f"       result: {res!r}" + (f"  ERROR: {err!r}" if err else ""))
    print(f"       visited_urls after: {sorted(r.visited_urls)}")


web_path("scraped_data = 2 documents", [{"url": "a.txt", "raw_content": "A"}, {"url": "b.txt", "raw_content": "B"}])
web_path("scraped_data = []", [])

# ---------------------------------------------------------------- 8. source_urls path (real _get_context_by_urls)
head("8. real _get_context_by_urls (scraper and selection replaced by recorders)")


def urls_path(title, urls, visited):
    r = make_researcher(visited_urls=set(visited))
    log = []

    async def browse(new_urls):
        log.append(("browse_urls", list(new_urls)))
        return [{"url": u, "raw_content": "page " + u} for u in new_urls if "fail" not in u]

    async def sel(query, pages):
        log.append(("select", query, [p["url"] for p in pages]))
        return f"SEL[{query}|{len(pages)}]"

    r.scraper_manager = types.SimpleNamespace(browse_urls=browse)
    r.context_manager = types.SimpleNamespace(get_similar_content_by_query=sel)
    c = RM.ResearchConductor(r)
    res, err = quiet_run(c._get_context_by_urls(urls))
    print(f"  -- {title}")
    for e in log:
        print(f"       {e}")
    print(f"       result: {res!r}" + (f"  ERROR: {err!r}" if err else ""))
    print(f"       visited_urls after: {sorted(r.visited_urls)}")


urls_path("two new urls", ["http://u1", "http://u2"], [])
urls_path("one already visited", ["http://u1", "http://u2"], ["http://u1"])
urls_path("all urls already visited", ["http://u1"], ["http://u1"])
urls_path("all fail to scrape", ["http://fail1"], [])

# ---------------------------------------------------------------- 9. Config doc_path
head("9. real Config() and DOC_PATH / REPORT_SOURCE (json_repair, provider lists, retriever names stubbed)")
import json as _json
CFG = importlib.import_module("gpt_researcher.config.config")
cfg_root = tempfile.mkdtemp(prefix="srcmodes_cfg_")
KEYS = ("DOC_PATH", "REPORT_SOURCE", "CONFIG_PATH")


def make_cfg(name, env, json_cfg=None):
    for k in KEYS:
        os.environ.pop(k, None)
    os.environ.update(env)
    path = None
    if json_cfg is not None:
        path = os.path.join(cfg_root, "cfg_" + name + ".json")
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(json_cfg, f)
    buf = io.StringIO()
    with redirect_stdout(buf):
        c = CFG.Config(path)
    for line in buf.getvalue().splitlines():
        print(f"    [stdout of real code] {line}")
    for k in KEYS:
        os.environ.pop(k, None)
    return c


env_dir = os.path.join(cfg_root, "from_env")
json_dir = os.path.join(cfg_root, "from_json")
c = make_cfg("A", {"DOC_PATH": env_dir})
show("A default dict (REPORT_SOURCE web) + env DOC_PATH -> doc_path / dir created",
     (os.path.relpath(c.doc_path, cfg_root), os.path.exists(env_dir)))
c = make_cfg("B", {"DOC_PATH": env_dir}, {"REPORT_SOURCE": "local", "DOC_PATH": json_dir})
show("B json REPORT_SOURCE=local + env DOC_PATH -> doc_path / json dir created / env dir created",
     (os.path.relpath(c.doc_path, cfg_root), os.path.exists(json_dir), os.path.exists(env_dir)))
blocker = os.path.join(cfg_root, "a_file")
open(blocker, "w").close()
c = make_cfg("C", {}, {"REPORT_SOURCE": "local", "DOC_PATH": os.path.join(blocker, "sub")})
show("C json local + DOC_PATH under a regular file (makedirs fails) -> doc_path", c.doc_path)
env_dir2 = os.path.join(cfg_root, "from_env2")
c = make_cfg("D", {"REPORT_SOURCE": "local", "DOC_PATH": env_dir2})
show("D env REPORT_SOURCE=local only -> cfg.report_source / doc_path / dir created",
     (c.report_source, os.path.relpath(c.doc_path, cfg_root), os.path.exists(env_dir2)))
c = make_cfg("E", {})
show("E nothing set -> cfg.report_source / cfg.doc_path", (c.report_source, c.doc_path))

print("\n(done)")
