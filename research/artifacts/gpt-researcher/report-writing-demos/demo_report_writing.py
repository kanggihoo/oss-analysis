"""Offline demo for reports/gpt-researcher/capabilities/report-writing.md (2026-10-22).

Runs the REAL source of these files of repos/gpt-researcher @ 3582a68 without network,
without an LLM call and without installing packages:
  gpt_researcher/actions/markdown_processing.py   (extract_headers, extract_sections, table_of_contents, add_references)
  gpt_researcher/prompts.py                       (PromptFamily prompt generators, get_prompt_by_report_type)
  gpt_researcher/actions/report_generation.py     (generate_report, write_report_introduction, write_conclusion, generate_draft_section_titles)
  gpt_researcher/actions/utils.py                 (stream_output)
  gpt_researcher/skills/writer.py                 (ReportGenerator)
  gpt_researcher/utils/enum.py                    (ReportType, Tone, ReportSource)
and, for gpt_researcher/agent.py, the methods write_report / write_introduction /
write_report_conclusion / add_costs / _log_event are cut out of the source with ast and
exec'd on a fake `self` (agent.py itself cannot be imported: its dependencies are missing).

What is replaced (so what this demo does NOT verify):
- LLM: `gpt_researcher.utils.llm.create_chat_completion` is a scripted fake. It records every
  keyword argument it receives and returns/raises what the scenario scripts. Real provider
  behavior (streaming chunks, 10-attempt retry, empty-response retry, cost calculation) is NOT run;
  those are read from source only (llm.py:120-162, generic/base.py:378-402).
  The fake calls cost_callback(0.5) after a successful scripted reply to show that the cost
  callback is passed through; the real cost value is computed by calculate_llm_cost (not run).
- Config: a SimpleNamespace with the default values of config/variables/default.py
  (TOTAL_WORDS 1200, REPORT_FORMAT "APA", LANGUAGE "english", SMART_TOKEN_LIMIT 12000).
  Reading env vars / JSON config into Config is not run.
- gpt_researcher/__init__.py, actions/__init__.py, skills/__init__.py (they import the whole agent)
  are skipped: bare package objects are used and the real function objects are attached.
- langchain_core.documents.Document: minimal stand-in (prompts.py only imports it for type hints).
- Python-Markdown (`markdown`) is NOT installed in this environment. The demo imports the already
  unpacked copy (version printed below) that sits in the local uv cache, by appending its
  site-packages dir to sys.path. Nothing was installed or modified. Override the path with
  the env var MARKDOWN_SITE.
- Fake researcher objects (SimpleNamespace) stand in for GPTResearcher when driving ReportGenerator,
  and the fake `self` for the agent methods. The query/context texts are made-up examples.

Run: python demo_report_writing.py
"""
import ast
import asyncio
import contextlib
import importlib.util
import io
import json
import logging
import os
import sys
import textwrap
import types
import warnings
from types import SimpleNamespace

sys.dont_write_bytecode = True  # do not leave .pyc files inside repos/
sys.stdout.reconfigure(encoding="utf-8")
logging.disable(logging.CRITICAL)

REPO = r"C:\Users\SSAFY\Desktop\oss-analysis\repos\gpt-researcher"
PKG = os.path.join(REPO, "gpt_researcher")
MD_SITE = os.environ.get(
    "MARKDOWN_SITE",
    r"C:\Users\SSAFY\AppData\Local\uv\cache\archive-v0\0NDFaUedZ9HAdUJ4\Lib\site-packages",
)
sys.path.append(MD_SITE)
import markdown  # noqa: E402  (Python-Markdown, from the uv cache copy)

RESULTS = []


def check(label, cond, detail=""):
    RESULTS.append(bool(cond))
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f"  -> {detail}" if detail else ""))


def head(title):
    print("\n" + "=" * 8 + " " + title)


# ------------------------------------------------------------------ module loading
def mkpkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(PKG, rel))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


gp = mkpkg("gpt_researcher")
gp_utils = mkpkg("gpt_researcher.utils")
gp_config = mkpkg("gpt_researcher.config")
gp_actions = mkpkg("gpt_researcher.actions")
gp_skills = mkpkg("gpt_researcher.skills")

lc = mkpkg("langchain_core")
lc_docs = types.ModuleType("langchain_core.documents")


class Document:  # stand-in, prompts.py imports it only for annotations
    def __init__(self, page_content="", metadata=None):
        self.page_content, self.metadata = page_content, metadata or {}


lc_docs.Document = Document
sys.modules["langchain_core.documents"] = lc_docs


class StubConfig:  # prompts.py / report_generation.py only import the name
    pass


gp_config.Config = StubConfig
cfg_mod = types.ModuleType("gpt_researcher.config.config")
cfg_mod.Config = StubConfig
sys.modules["gpt_researcher.config.config"] = cfg_mod

logger_mod = types.ModuleType("gpt_researcher.utils.logger")
logger_mod.get_formatted_logger = lambda: logging.getLogger("demo")
sys.modules["gpt_researcher.utils.logger"] = logger_mod


class FakeLLM:
    """Scripted replacement of create_chat_completion. script items: str -> return, Exception -> raise."""

    def __init__(self):
        self.calls = []
        self.script = []

    async def __call__(self, messages, **kw):
        self.calls.append({"messages": messages, **kw})
        item = self.script.pop(0) if self.script else "FAKE LLM REPLY"
        if isinstance(item, Exception):
            raise item
        cb = kw.get("cost_callback")
        if cb:
            cb(0.5)  # the real function calls cost_callback(calculate_llm_cost(...)) on success
        return item

    def reset(self, *script):
        self.calls, self.script = [], list(script)


LLM = FakeLLM()
llm_mod = types.ModuleType("gpt_researcher.utils.llm")
llm_mod.create_chat_completion = LLM
llm_mod.construct_subtopics = None  # writer.py imports the name only
sys.modules["gpt_researcher.utils.llm"] = llm_mod

enum_mod = load("gpt_researcher.utils.enum", "utils/enum.py")
Tone, ReportType = enum_mod.Tone, enum_mod.ReportType
prompts = load("gpt_researcher.prompts", "prompts.py")
PromptFamily = prompts.PromptFamily
au = load("gpt_researcher.actions.utils", "actions/utils.py")
rg = load("gpt_researcher.actions.report_generation", "actions/report_generation.py")
mp = load("gpt_researcher.actions.markdown_processing", "actions/markdown_processing.py")
for n in ("generate_draft_section_titles", "generate_report", "write_conclusion", "write_report_introduction"):
    setattr(gp_actions, n, getattr(rg, n))
gp_actions.stream_output = au.stream_output
writer = load("gpt_researcher.skills.writer", "skills/writer.py")

DEFAULT_CFG = dict(
    agent_role=None, report_format="APA", total_words=1200, language="english",
    smart_llm_model="fake-model", smart_llm_provider="fake", smart_token_limit=12000, llm_kwargs={},
)


def make_cfg(**over):
    return SimpleNamespace(**{**DEFAULT_CFG, **over})


class WS:
    def __init__(self):
        self.events = []

    async def send_json(self, d):
        self.events.append(d)


def run(coro):
    return asyncio.run(coro)


print(f"Python-Markdown {markdown.__version__} from {markdown.__file__}")

# =================================================================== A. pure functions
head("A. markdown_processing.py (real code, real Python-Markdown)")
SAMPLE = """# Title

Intro para.

## Section A
text a

### Sub A1
text a1 **bold**

## Section B ([cite](http://x.y))
text b

Setext H1
=========
para

#### Deep
x

## Section A
dup
"""
H = mp.extract_headers(SAMPLE)
print(json.dumps(H, ensure_ascii=False))
check("A-01 extract_headers: nested by relative level, children only when present",
      H[0]["text"] == "Title" and H[0]["children"][0]["children"][0]["text"] == "Sub A1"
      and "children" not in H[0]["children"][0]["children"][0])
check("A-02 header text is inner HTML, not plain text (link stays <a>)",
      H[0]["children"][1]["text"] == 'Section B (<a href="http://x.y">cite</a>)')
check("A-03 level jump H1 -> H4 makes the H4 a direct child of the last H1 (setext H1 included)",
      H[1]["text"] == "Setext H1" and H[1]["children"][0] == {"level": 4, "text": "Deep"})
check("A-04 duplicate header text is kept, not merged",
      H[1]["children"][1] == {"level": 2, "text": "Section A"})
for v in ("", None, 5, b"x"):
    check(f"A-05 extract_headers({v!r}) == []", mp.extract_headers(v) == [])
check("A-06 text without header -> []", mp.extract_headers("plain text only") == [])
check("A-07 empty header '#' gives text ''", mp.extract_headers("#") == [{"level": 1, "text": ""}])
check("A-08 trailing hashes are dropped by Python-Markdown", mp.extract_headers("## Title ##\ntext") == [{"level": 2, "text": "Title"}])
fence = "# T\n\n```python\n# a comment\nx=1\n```\n\n## S\ntext"
HF = mp.extract_headers(fence)
print("fence case headers:", json.dumps(HF))
check("A-09 code fence is NOT recognised: '# a comment' inside ``` becomes a header",
      [h["text"] for h in HF] == ["T", "a comment"] and HF[1]["children"][0]["text"] == "S")
check("A-10 header inside a list item / blockquote is found",
      mp.extract_headers("- ## item\n\ntext") == [{"level": 2, "text": "item"}]
      and mp.extract_headers("> ## quoted\n\ntext") == [{"level": 2, "text": "quoted"}])

S = mp.extract_sections(SAMPLE)
print(json.dumps(S, ensure_ascii=False))
check("A-11 extract_sections: one entry per header with non-empty body, flat list in document order",
      [s["section_title"] for s in S] == ["Title", "Section A", "Sub A1", "Section B (<a href=\"http://x.y\">cite</a>)", "Setext H1", "Deep", "Section A"])
check("A-12 body tags stripped (**bold** -> bold); title keeps HTML",
      S[2]["written_content"] == "text a1 bold")
E = mp.extract_sections("intro before any header\n\n## A\n### B\nb text\n## C\nc text & <b>x</b> a < b")
print(json.dumps(E, ensure_ascii=False))
check("A-13 text before the first header is dropped; a header with an empty body (A) is dropped",
      [s["section_title"] for s in E] == ["B", "C"])
check("A-14 entities stay escaped in body ('&' -> &amp;, '<' -> &lt;), tags removed",
      E[1]["written_content"] == "c text &amp; x a &lt; b")
check("A-15 body of several paragraphs: tags removed, paragraphs joined by the newline between tags",
      mp.extract_sections("## H\nline1\nline2\n\nline3")[0]["written_content"] == "line1\nline2\nline3")
check("A-16 header written as raw <h2 id='x'> html is a header for extract_headers but not for extract_sections",
      mp.extract_headers("<h2 id='x'>raw</h2>\n\ntext") == [{"level": 2, "text": "raw"}]
      and mp.extract_sections("<h2 id='x'>raw</h2>\n\ntext") == [])
for v in ("", None, 5):
    check(f"A-17 extract_sections({v!r}) == []", mp.extract_sections(v) == [])

TOC = mp.table_of_contents(SAMPLE)
print(repr(TOC))
check("A-18 table_of_contents: '## Table of Contents\\n\\n' then '- text' lines, 4 spaces per depth",
      TOC == '## Table of Contents\n\n- Title\n    - Section A\n        - Sub A1\n    - Section B (<a href="http://x.y">cite</a>)\n- Setext H1\n    - Deep\n    - Section A\n')
check("A-19 indent follows tree depth, not the H-number (H4 under H1 is depth 1)", "    - Deep\n" in TOC)
check("A-20 no headers -> only the title line", mp.table_of_contents("plain") == "## Table of Contents\n\n"
      and mp.table_of_contents("") == "## Table of Contents\n\n")
check("A-21 non-str input -> '' (not the title line)", mp.table_of_contents(None) == "" and mp.table_of_contents(5) == "")
check("A-22 empty header gives a bare '- ' line", mp.table_of_contents("#") == "## Table of Contents\n\n- \n")

urls = {"https://b.example/x", "https://a.example/y"}
R = mp.add_references("# R", urls)
print(repr(R))
check("A-23 add_references: '\\n\\n\\n## References\\n\\n' + '- [url](url)\\n' per url, sorted ascending",
      R == "# R\n\n\n## References\n\n- [https://a.example/y](https://a.example/y)\n- [https://b.example/x](https://b.example/x)\n")
check("A-24 result is deterministic for equal sets", mp.add_references("# R", set(urls)) == R)
check("A-25 empty set -> heading appended with no entries", mp.add_references("# R", set()) == "# R\n\n\n## References\n\n")
check("A-26 visited_urls None -> report unchanged", mp.add_references("# R", None) == "# R")
check("A-27 report None -> '' + references; non-str report -> str(report)",
      mp.add_references(None, {"u"}) == "\n\n\n## References\n\n- [u](u)\n" and mp.add_references(5, {"u"}).startswith("5\n\n\n## References"))
check("A-28 a list is accepted and NOT de-duplicated (only sets dedupe)",
      mp.add_references("# R", ["https://b", "https://a", "https://b"]).count("- [https://b](https://b)") == 2)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    r_mixed = mp.add_references("# R", {"a", 1})
check("A-29 unsortable url set (mixed types): exception swallowed, report returned unchanged, message printed",
      r_mixed == "# R" and "Encountered exception in adding source urls" in buf.getvalue(), buf.getvalue().strip())
check("A-30 URLs are written verbatim (no escaping, no validation)",
      "- [https://x.com/a b)](https://x.com/a b))\n" in mp.add_references("# R", {"https://x.com/a b)"}))
check("A-31 a str is iterated per character", mp.add_references("# R", "abc").endswith("- [a](a)\n- [b](b)\n- [c](c)\n"))

# =================================================================== B. prompt selection
head("B. get_prompt_by_report_type and what each prompt receives (real prompts.py)")
SENT = dict(total_words=1234, language="Klingon", report_format="MLA9", tone=Tone.Formal)


def pick(rt):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        f = prompts.get_prompt_by_report_type(rt, PromptFamily)
    return f.__name__, [str(x.message).splitlines()[0] for x in w]


for rt in ["research_report", "resource_report", "outline_report", "custom_report", "subtopic_report", "deep",
           "detailed_report", "bogus", "", ReportType.ResearchReport]:
    name, warns = pick(rt)
    print(f"  {rt!r:32} -> {name:36} warnings={warns}")
exp = {"research_report": "generate_report_prompt", "resource_report": "generate_resource_report_prompt",
       "outline_report": "generate_outline_report_prompt", "custom_report": "generate_custom_report_prompt",
       "subtopic_report": "generate_subtopic_report_prompt", "deep": "generate_deep_research_prompt"}
for rt, fn in exp.items():
    check(f"B-01 {rt} -> {fn}, no warning", pick(rt) == (fn, []))
n_dr, w_dr = pick("detailed_report")
check("B-02 detailed_report has no entry: UserWarning + falls back to generate_report_prompt",
      n_dr == "generate_report_prompt" and len(w_dr) == 1 and "Invalid report type: detailed_report" in w_dr[0])
check("B-03 unknown string and '' also fall back with a warning",
      pick("bogus")[0] == "generate_report_prompt" and pick("")[0] == "generate_report_prompt" and pick("bogus")[1])
check("B-04 the ReportType enum member itself (not .value) is NOT a key: warning + fallback",
      pick(ReportType.ResearchReport)[0] == "generate_report_prompt" and pick(ReportType.ResearchReport)[1])
check("B-05 mapping is a dict of 6 entries (detailed_report absent)", len(prompts.report_type_mapping) == 6
      and "detailed_report" not in prompts.report_type_mapping)

ctx, q = "CTXMARK", "QMARK"
matrix = {}
for rt in ["research_report", "resource_report", "outline_report", "custom_report", "deep"]:
    f = prompts.get_prompt_by_report_type(rt, PromptFamily)
    p_web = f(q, ctx, "web", **SENT)
    p_loc = f(q, ctx, "local", **SENT)
    matrix[rt] = dict(
        context="CTXMARK" in p_web, question="QMARK" in p_web,
        words="1234" in p_web, language="Klingon" in p_web, fmt="MLA9" in p_web, tone=Tone.Formal.value in p_web,
        web_vs_local_differ=p_web != p_loc, date_line="current date" in p_web.lower(),
    )
    print(f"  {rt:16}", matrix[rt])
sub = prompts.get_prompt_by_report_type("subtopic_report", PromptFamily)
p_sub = sub(q, ["HDRMARK"], ["WRITTENMARK"], "MAINMARK", ctx, report_format="MLA9", tone=Tone.Formal, total_words=1234, language="Klingon")
matrix["subtopic_report"] = dict(
    context="CTXMARK" in p_sub, question="QMARK" in p_sub, words="1234" in p_sub, language="Klingon" in p_sub,
    fmt="MLA9" in p_sub, tone=Tone.Formal.value in p_sub, headers="HDRMARK" in p_sub, written="WRITTENMARK" in p_sub, main="MAINMARK" in p_sub)
print("  subtopic_report ", matrix["subtopic_report"])
check("B-06 research_report prompt uses context, question, words, language, MLA9 format, tone", all(matrix["research_report"][k] for k in ("context", "question", "words", "language", "fmt", "tone")))
check("B-07 resource_report uses words and language but NOT format or tone",
      matrix["resource_report"]["words"] and matrix["resource_report"]["language"] and not matrix["resource_report"]["fmt"] and not matrix["resource_report"]["tone"])
check("B-08 outline_report uses words only (no language, no format, no tone)",
      matrix["outline_report"]["words"] and not matrix["outline_report"]["language"] and not matrix["outline_report"]["fmt"] and not matrix["outline_report"]["tone"])
check("B-09 custom_report prompt is just context + query (no words/language/format/tone)",
      not any(matrix["custom_report"][k] for k in ("words", "language", "fmt", "tone"))
      and prompts.PromptFamily.generate_custom_report_prompt("Q?", "CTX", "web") == '"CTX"\n\nQ?')
check("B-10 deep prompt uses words, language, format, tone",
      all(matrix["deep"][k] for k in ("words", "language", "fmt", "tone")))
check("B-11 subtopic prompt uses existing headers, written contents, main topic, words, language, format, tone",
      all(matrix["subtopic_report"][k] for k in ("headers", "written", "main", "words", "language", "fmt", "tone")))
check("B-12 report_source != 'web' switches the reference paragraph (research/resource/deep); outline and custom ignore it",
      matrix["research_report"]["web_vs_local_differ"] and matrix["resource_report"]["web_vs_local_differ"]
      and matrix["deep"]["web_vs_local_differ"] and not matrix["outline_report"]["web_vs_local_differ"]
      and not matrix["custom_report"]["web_vs_local_differ"])
rep_w = prompts.PromptFamily.generate_report_prompt("Q", "C", "web", tone=Tone.Objective)
rep_h = prompts.PromptFamily.generate_report_prompt("Q", "C", "hybrid", tone=Tone.Objective)
rep_s = prompts.PromptFamily.generate_report_prompt("Q", "C", "static", tone=Tone.Objective)
check("B-13 research_report: 'web' -> source URLs wording; hybrid/static/anything else -> document names wording",
      "source urls" in rep_w and "source document names" in rep_h and "source document names" in rep_s)
check("B-14 research_report with tone=None omits the tone sentence",
      "tone." not in prompts.PromptFamily.generate_report_prompt("Q", "C", "web", tone=None))
check("B-15 defaults when the generator is called without options: 1000 words, 'apa', 'english'",
      "at least 1000 words" in prompts.PromptFamily.generate_report_prompt("Q", "C", "web")
      and "in apa format" in prompts.PromptFamily.generate_report_prompt("Q", "C", "web")
      and "language: english" in prompts.PromptFamily.generate_report_prompt("Q", "C", "web"))
check("B-16 subtopic prompt: report_format is upper-cased, research prompt keeps it as given",
      "follow the MLA9 format" in p_sub and "MLA9 format" in p_sub
      and "mla9" not in p_sub and "markdown syntax and mla9 format" in prompts.PromptFamily.generate_report_prompt("Q", "C", "web", report_format="mla9"))

# =================================================================== C. generate_report
head("C. generate_report (real code, fake LLM)")


def gen(**kw):
    base = dict(query="Q?", context="CTX", agent_role_prompt="ROLE", report_type="research_report",
                tone=Tone.Objective, report_source="web", websocket=None, cfg=make_cfg())
    base.update(kw)
    return run(rg.generate_report(**base))


LLM.reset("THE REPORT")
out = gen(cost_callback=lambda c: None)
c0 = LLM.calls[0]
print({k: v for k, v in c0.items() if k != "messages"})
check("C-01 returns the LLM text", out == "THE REPORT")
check("C-02 call: system=agent_role_prompt, user=prompt; temperature 0.35; stream True; smart model/provider/token limit",
      [m["role"] for m in c0["messages"]] == ["system", "user"] and c0["messages"][0]["content"] == "ROLE"
      and c0["temperature"] == 0.35 and c0["stream"] is True and c0["model"] == "fake-model"
      and c0["llm_provider"] == "fake" and c0["max_tokens"] == 12000 and c0["llm_kwargs"] == {})
user = c0["messages"][1]["content"]
check("C-03 research_report prompt carries context, query, 1200 words, APA, tone sentence, language, date line",
      '"CTX"' in user and '"Q?"' in user and "at least 1200 words" in user and "markdown syntax and APA format" in user
      and "Write the report in a Objective (impartial" in user and "language: english" in user and "current date" in user)

LLM.reset()
gen(report_type="custom_report", query="MY OWN INSTRUCTION")
check("C-04 custom_report without custom_prompt: user message == '\"CTX\"\\n\\nMY OWN INSTRUCTION' (query is the instruction)",
      LLM.calls[0]["messages"][1]["content"] == '"CTX"\n\nMY OWN INSTRUCTION')
for rt in ("research_report", "resource_report", "outline_report", "custom_report", "deep"):
    LLM.reset()
    gen(report_type=rt, custom_prompt="CUSTOM PROMPT")
    check(f"C-05 custom_prompt wins over {rt}: 'CUSTOM PROMPT\\n\\nContext: CTX'",
          LLM.calls[0]["messages"][1]["content"] == "CUSTOM PROMPT\n\nContext: CTX")
LLM.reset()
gen(report_type="subtopic_report", custom_prompt="CUSTOM PROMPT", main_topic="MAIN", existing_headers=["H1"], relevant_written_contents=["W1"])
u = LLM.calls[0]["messages"][1]["content"]
check("C-06 custom_prompt is IGNORED for subtopic_report (subtopic prompt used)",
      "CUSTOM PROMPT" not in u and "under the main topic: MAIN" in u)
check("C-07 subtopic prompt: query is the subtopic, existing headers / written contents inserted as Python list repr",
      "construct a detailed report on the subtopic: Q? under" in u and "    ['H1']" in u and "    ['W1']" in u)
check("C-08 subtopic prompt: 1200 words (cfg.total_words overrides the prompt default 800), Formal-free Objective tone",
      "minimum length of 1200 words" in u and "Use an Objective (impartial" in u)

LLM.reset()
gen(report_type="research_report", main_topic="MAIN", existing_headers=["HDRMARK"], relevant_written_contents=["WRITTENMARK"])
u = LLM.calls[0]["messages"][1]["content"]
check("C-09 existing_headers / relevant_written_contents / main_topic are ignored by non-subtopic prompts",
      "HDRMARK" not in u and "WRITTENMARK" not in u and "MAIN" not in u)
LLM.reset()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    gen(report_type="detailed_report")
check("C-10 report_type 'detailed_report' reaches generate_report -> research_report prompt (with a UserWarning)",
      "in a detailed report" in LLM.calls[0]["messages"][1]["content"])

LLM.reset()
gen(context=["alpha\nbeta", "gamma"])
u = LLM.calls[0]["messages"][1]["content"]
check("C-11 list context is interpolated as Python repr: \"['alpha\\nbeta', 'gamma']\" (escaped, quoted)",
      "\"['alpha\\nbeta', 'gamma']\"" in u, u.split("\n")[1][:60])
LLM.reset()
gen(context="")
check("C-12 generate_report itself has no empty-context guard (prompt with empty context is sent)",
      len(LLM.calls) == 1 and 'Information: ""' in LLM.calls[0]["messages"][1]["content"])

LLM.reset()
gen(cfg=make_cfg(report_format="MLA9", language="Klingon", total_words=1234, smart_llm_model="m2", smart_token_limit=777), tone=Tone.Formal)
c = LLM.calls[0]
u = c["messages"][1]["content"]
check("C-24 generate_report takes format/words/language from cfg and tone from its argument; model and max_tokens from cfg",
      "at least 1234 words" in u and "markdown syntax and MLA9 format" in u and "language: Klingon" in u
      and "Write the report in a Formal (adheres" in u and c["model"] == "m2" and c["max_tokens"] == 777)

# images
IMGS = [
    {"url": "http://i/1.png", "title": "T1", "section_hint": "Intro"},
    None,
    "notadict",
    {"title": "no url"},
    {"url": ""},
    {"url": "http://i/2.png", "alt_text": "ALT2"},
    {"url": "http://i/3.png"},
]
LLM.reset()
gen(available_images=IMGS)
u = LLM.calls[0]["messages"][1]["content"]
img_block = u[u.index("AVAILABLE IMAGES:"):]
print(img_block)
check("C-13 images block appended after the prompt; only dicts with non-empty url; numbered 1..n over valid rows",
      "- Image 1: ![T1](http://i/1.png) - Intro" in img_block and "- Image 2: ![ALT2](http://i/2.png) - General" in img_block
      and "- Image 3: ![Illustration](http://i/3.png) - General" in img_block and "Image 4" not in img_block)
check("C-14 alt text order: title, then alt_text, then 'Illustration'; hint defaults to 'General'",
      "![T1](" in img_block and "![ALT2](" in img_block and "![Illustration](" in img_block)
LLM.reset()
gen(available_images=[None, {"title": "x"}, "s"])
check("C-15 no valid image -> no AVAILABLE IMAGES block", "AVAILABLE IMAGES" not in LLM.calls[0]["messages"][1]["content"])
LLM.reset()
gen(available_images=None)
check("C-16 available_images=None -> treated as []", "AVAILABLE IMAGES" not in LLM.calls[0]["messages"][1]["content"])
LLM.reset()
gen(available_images=[{"url": "http://i/1.png"}], custom_prompt="CP")
check("C-17 image block is also appended after a custom_prompt", LLM.calls[0]["messages"][1]["content"].startswith("CP\n\nContext: CTX\n\nAVAILABLE IMAGES:"))

# failure handling
LLM.reset(RuntimeError("boom"), "SECOND TRY")
out = gen()
check("C-18 first LLM call raises -> one more call, same settings, ONE user message '<role>\\n\\n<content>'; its text is returned",
      out == "SECOND TRY" and len(LLM.calls) == 2 and [m["role"] for m in LLM.calls[1]["messages"]] == ["user"]
      and LLM.calls[1]["messages"][0]["content"] == "ROLE\n\n" + LLM.calls[0]["messages"][1]["content"]
      and LLM.calls[1]["temperature"] == 0.35 and LLM.calls[1]["stream"] is True)
LLM.reset(RuntimeError("boom1"), RuntimeError("boom2"))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    out = gen()
check("C-19 both calls raise -> returns '' (no exception), message printed to stdout with the second error only",
      out == "" and len(LLM.calls) == 2 and "Error in generate_report: boom2" in buf.getvalue() and "boom1" not in buf.getvalue(), buf.getvalue().strip())
costs = []
LLM.reset(RuntimeError("boom"), "OK")
gen(cost_callback=costs.append)
check("C-20 cost_callback is passed to both attempts (fake calls it only on success: 1 call)", costs == [0.5])
LLM.reset()
gen(foo=1, bar="x")
check("C-21 extra **kwargs are forwarded to the LLM call", LLM.calls[0]["foo"] == 1 and LLM.calls[0]["bar"] == "x")
for label, kw in (("tone is a str", dict(tone="Formal")),):
    LLM.reset()
    try:
        gen(**kw)
        ok = False
    except AttributeError as e:
        ok = True
    check(f"C-22 prompt construction errors are outside the try: {label} -> AttributeError, 0 LLM calls", ok and not LLM.calls)
LLM.reset()
try:
    gen(report_type="subtopic_report", tone=None)
    ok = False
except AttributeError:
    ok = True
check("C-23 subtopic prompt with tone=None -> AttributeError (tone.value is unconditional); research_report with tone=None works",
      ok and (LLM.reset() or gen(tone=None) == "FAKE LLM REPLY"))

# =================================================================== D. introduction / conclusion / draft titles
head("D. introduction, conclusion, draft titles (real code, fake LLM)")
cfg = make_cfg(report_format="MLA9", language="Klingon", total_words=1234)
LLM.reset("INTRO TEXT")
out = run(rg.write_report_introduction(query="Q?", context="CTX", agent_role_prompt="ROLE", config=cfg, websocket="WSMARK",
                                       cost_callback=lambda c: None, prompt_family=PromptFamily))
c = LLM.calls[0]
u = c["messages"][1]["content"]
print({k: v for k, v in c.items() if k != "messages"})
check("D-01 introduction: system=role, temperature 0.25, stream True, websocket forwarded, smart model",
      out == "INTRO TEXT" and c["messages"][0] == {"role": "system", "content": "ROLE"} and c["temperature"] == 0.25
      and c["stream"] is True and c["websocket"] == "WSMARK" and c["model"] == "fake-model" and c["max_tokens"] == 12000)
check("D-02 introduction prompt: context first, query, 'H1 heading', language from config; report_format is NOT passed (always APA)",
      u.startswith("CTX\n") and "topic -- Q?" in u and "preceded by an H1 heading" in u and "output must be in Klingon language" in u
      and "APA format" in u and "MLA9" not in u)
check("D-03 introduction ignores tone and total_words", "1234" not in u and "Formal" not in u and "tone" not in u.lower())
LLM.reset("CONC TEXT")
out = run(rg.write_conclusion(query="Q?", context="REPORT BODY", agent_role_prompt="ROLE", config=cfg, websocket=None,
                              cost_callback=None, prompt_family=PromptFamily))
u = LLM.calls[0]["messages"][1]["content"]
check("D-04 conclusion: report body as context, 2-3 paragraphs, '## Conclusion' title rule, language, APA fixed",
      out == "CONC TEXT" and "Research task: Q?" in u and "Research Report: REPORT BODY" in u and "2-3 paragraphs" in u
      and '"## Conclusion" section title' in u and "written in Klingon language" in u and "APA format" in u and "MLA9" not in u
      and LLM.calls[0]["temperature"] == 0.25)
for label, fn, kw in (("introduction", rg.write_report_introduction, {}), ("conclusion", rg.write_conclusion, {})):
    LLM.reset(RuntimeError("x"), RuntimeError("y"))
    o = run(fn(query="Q", context="C", agent_role_prompt="R", config=cfg, **kw))
    check(f"D-05 {label}: LLM error -> '' (no retry here, one call, no exception)", o == "" and len(LLM.calls) == 1)
LLM.reset("### A\n### B")
o = run(rg.generate_draft_section_titles(query="MAIN", current_subtopic="SUB", context="CTX", role="ROLE", config=cfg,
                                         websocket="WSMARK", prompt_family=PromptFamily))
check("D-06 draft titles: split on '\\n', websocket NOT forwarded (None), temperature 0.25",
      o == ["### A", "### B"] and LLM.calls[0]["websocket"] is None and LLM.calls[0]["temperature"] == 0.25)
LLM.reset(RuntimeError("x"))
check("D-07 draft titles: error -> []", run(rg.generate_draft_section_titles(query="M", current_subtopic="S", context="C", role="R", config=cfg)) == [])

# =================================================================== E. ReportGenerator
head("E. ReportGenerator.write_report (real skills/writer.py, fake researcher and LLM)")


def make_researcher(**over):
    costs = []
    r = SimpleNamespace(
        query="Q?", role=None, report_type="research_report", report_source="web", tone=Tone.Objective,
        websocket=None, cfg=make_cfg(), headers={}, kwargs={}, verbose=False, context="CTX", parent_query="",
        prompt_family=PromptFamily, subtopics=[], research_images=[], costs=costs,
    )
    r.add_costs = costs.append
    r.get_research_images = lambda top_k=10: r.research_images[:top_k]
    for k, v in over.items():
        setattr(r, k, v)
    return r


def gw(r=None, **kw):
    r = r or make_researcher()
    g = writer.ReportGenerator(r)
    return run(g.write_report(**kw)), r


LLM.reset()
out, r = gw()
check("E-01 normal call returns the LLM text; add_costs is the cost_callback", out == "FAKE LLM REPLY" and r.costs == [0.5])
APOLOGY_START = 'I could not gather any source material for "Q?". '
for ctxv in ("", [], None, "  \n ", ["", "  "], 0):
    LLM.reset()
    out, r = gw(make_researcher(context=ctxv))
    check(f"E-02 empty/blank context {ctxv!r}: apology string returned, 0 LLM calls, no cost",
          out.startswith(APOLOGY_START) and "not able to produce a reliable, sourced report." in out and not LLM.calls and not r.costs)
print("  apology text:", out)
LLM.reset()
try:
    gw(make_researcher(context=[{"title": "x"}]))
    ok = False
except TypeError as e:
    ok = True
    err = str(e)
check("E-03 list context with a non-str element: TypeError escapes (the emptiness check does '\\n'.join)", ok and not LLM.calls, err)
LLM.reset()
gw(make_researcher(context={"a": 1}))
check("E-04 dict context passes the guard through str() and is interpolated as repr", "{'a': 1}" in LLM.calls[0]["messages"][1]["content"])
LLM.reset()
gw(make_researcher(context="INTERNAL"), ext_context="EXTERNAL")
check("E-05 ext_context wins over researcher.context", "EXTERNAL" in LLM.calls[0]["messages"][1]["content"] and "INTERNAL" not in LLM.calls[0]["messages"][1]["content"])
for e in ("", [], None):
    LLM.reset()
    gw(make_researcher(context="INTERNAL"), ext_context=e)
    check(f"E-06 falsy ext_context {e!r} -> researcher.context used", "INTERNAL" in LLM.calls[0]["messages"][1]["content"])
LLM.reset()
gw(make_researcher(context=[]), ext_context="ONLY EXTERNAL")
check("E-07 ext_context rescues an empty researcher.context (guard sees the chosen context)", len(LLM.calls) == 1)

# subtopic params
LLM.reset()
r = make_researcher(report_type="subtopic_report", query="SUBTOPIC", parent_query="MAIN TOPIC")
gw(r, existing_headers=[{"subtopic task": "t", "headers": []}], relevant_written_contents=["W"])
u = LLM.calls[0]["messages"][1]["content"]
check("E-08 subtopic_report: query -> current_subtopic, parent_query -> main_topic, headers/contents inserted",
      "on the subtopic: SUBTOPIC under the main topic: MAIN TOPIC" in u and "{'subtopic task': 't', 'headers': []}" in u and "['W']" in u)
LLM.reset()
r = make_researcher(report_type="research_report")
gw(r, existing_headers=["HDRMARK"], relevant_written_contents=["WRITTENMARK"])
u = LLM.calls[0]["messages"][1]["content"]
check("E-09 non-subtopic report_type: existing_headers / relevant_written_contents never reach the prompt",
      "HDRMARK" not in u and "WRITTENMARK" not in u)

# role resolution
LLM.reset()
r = make_researcher()
g = writer.ReportGenerator(r)           # constructed while role is still None
r.role = "ROLE CHOSEN LATER"
run(g.write_report())
check("E-10 role set after ReportGenerator construction is still used (re-read at call time)",
      LLM.calls[0]["messages"][0]["content"] == "ROLE CHOSEN LATER")
LLM.reset()
r = make_researcher(role="CHOSEN", cfg=make_cfg(agent_role="CONFIG ROLE"))
gw(r)
check("E-11 cfg.agent_role (AGENT_ROLE) beats researcher.role", LLM.calls[0]["messages"][0]["content"] == "CONFIG ROLE")
LLM.reset()
gw(make_researcher(role=None))
check("E-12 no role anywhere: system message is the literal string 'None'", LLM.calls[0]["messages"][0]["content"] == "None")
LLM.reset()
r = make_researcher()
g = writer.ReportGenerator(r)
r.report_type = "outline_report"      # changed after construction
run(g.write_report())
check("E-13 report_type is a snapshot taken at construction (later change not used by the prompt)",
      "in a detailed report" in LLM.calls[0]["messages"][1]["content"] and "generate an outline" not in LLM.calls[0]["messages"][1]["content"])
LLM.reset()
gw(make_researcher(kwargs={"foo": 7}))
check("E-14 researcher.kwargs are forwarded to the LLM call", LLM.calls[0]["foo"] == 7)
LLM.reset()
gw(make_researcher(report_type="custom_report", query="DO THIS"), custom_prompt="CP2")
check("E-15 custom_prompt arrives through write_report", LLM.calls[0]["messages"][1]["content"] == "CP2\n\nContext: CTX")

# events
LLM.reset()
ws = WS()
r = make_researcher(websocket=ws, verbose=True, research_images=["http://s/1.jpg", "http://s/2.jpg"])
out, _ = gw(r, available_images=[{"url": "http://g/1.png"}])
seq = [(e["type"], e["content"]) for e in ws.events]
print("  events:", seq)
check("E-16 verbose+websocket+images: selected_images, images_available, writing_report, report_written in this order",
      seq == [("images", "selected_images"), ("logs", "images_available"), ("logs", "writing_report"), ("logs", "report_written")])
img_ev = ws.events[0]
check("E-17 selected_images event: output = json string of scraped image URLs, metadata = the list (scraped images, not generated ones)",
      img_ev["output"] == json.dumps(["http://s/1.jpg", "http://s/2.jpg"]) and img_ev["metadata"] == ["http://s/1.jpg", "http://s/2.jpg"])
LLM.reset()
ws = WS()
gw(make_researcher(websocket=ws, verbose=False, research_images=["http://s/1.jpg"]), available_images=[{"url": "http://g/1.png"}])
check("E-18 verbose=False: only the selected_images event is sent (it ignores verbose)", [(e["type"], e["content"]) for e in ws.events] == [("images", "selected_images")])
LLM.reset()
ws = WS()
gw(make_researcher(websocket=ws, verbose=True, research_images=[]))
check("E-19 no scraped images: no selected_images event", [e["content"] for e in ws.events] == ["writing_report", "report_written"])
LLM.reset()
ws = WS()
out, _ = gw(make_researcher(websocket=ws, verbose=True, context="", research_images=["http://s/1.jpg"]))
check("E-20 empty context: images event IS sent (before the guard), but no 'logs' events and no LLM call",
      [e["content"] for e in ws.events] == ["selected_images"] and out.startswith(APOLOGY_START) and not LLM.calls)
LLM.reset(RuntimeError("1"), RuntimeError("2"))
ws = WS()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    out, _ = gw(make_researcher(websocket=ws, verbose=True))
check("E-21 LLM failure: write_report returns '' and still sends 'report_written'", out == "" and ws.events[-1]["content"] == "report_written")
check("E-22 the LLM call receives the researcher's websocket (the provider streams paragraphs to it)", LLM.calls[0]["websocket"] is ws)

# intro / conclusion via ReportGenerator
LLM.reset("I")
r = make_researcher(context="RESEARCH CTX", role="ROLE R", kwargs={"foo": 3})
out = run(writer.ReportGenerator(r).write_introduction())
c = LLM.calls[0]
check("E-23 write_introduction uses researcher.context (not an argument), role, kwargs, add_costs, websocket",
      out == "I" and "RESEARCH CTX" in c["messages"][1]["content"] and c["messages"][0]["content"] == "ROLE R" and c["foo"] == 3 and r.costs == [0.5])
LLM.reset("C")
out = run(writer.ReportGenerator(make_researcher(context="IGNORED CTX")).write_report_conclusion("THE BODY"))
check("E-24 write_report_conclusion uses the report passed in, not researcher.context",
      "Research Report: THE BODY" in LLM.calls[0]["messages"][1]["content"] and "IGNORED CTX" not in LLM.calls[0]["messages"][1]["content"])
LLM.reset("I")
run(writer.ReportGenerator(make_researcher(context="")).write_introduction())
check("E-25 write_introduction has NO empty-context guard (LLM is called)", len(LLM.calls) == 1)
ws = WS()
LLM.reset("I")
run(writer.ReportGenerator(make_researcher(websocket=ws, verbose=True)).write_introduction())
check("E-26 intro events: writing_introduction, introduction_written (verbose only)", [e["content"] for e in ws.events] == ["writing_introduction", "introduction_written"])

# =================================================================== F. agent.py methods
head("F. agent.py methods (source cut out with ast, run on a fake self)")
src = open(os.path.join(PKG, "agent.py"), encoding="utf-8").read()
tree = ast.parse(src)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "GPTResearcher")
ns = {}
for fn in cls.body:
    if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name in (
            "write_report", "write_introduction", "write_report_conclusion", "add_costs", "_log_event"):
        code = textwrap.dedent(ast.get_source_segment(src, fn))
        exec(code, ns)
        print(f"  extracted {fn.name} (agent.py:{fn.lineno}-{fn.end_lineno})")


class RecHandler:
    def __init__(self):
        self.steps = []

    async def on_research_step(self, step, details):
        self.steps.append((step, details))


class RecGen:
    def __init__(self):
        self.calls = []

    async def write_report(self, **kw):
        self.calls.append(("write_report", kw))
        return "REPORT-X"

    async def write_report_conclusion(self, body):
        self.calls.append(("conclusion", body))
        return "CONC"

    async def write_introduction(self):
        self.calls.append(("intro",))
        return "INTRO"


def make_self(**over):
    s = SimpleNamespace(available_images=[], _current_step="research", context=["INTERNAL"], log_handler=RecHandler(),
                        report_generator=RecGen(), research_costs=0.0, step_costs={})
    for n in ("write_report", "write_introduction", "write_report_conclusion", "add_costs", "_log_event"):
        setattr(s, n, types.MethodType(ns[n], s))
    for k, v in over.items():
        setattr(s, k, v)
    return s


s = make_self()
out = run(s.write_report())
kw = s.report_generator.calls[0][1]
print("  steps:", [(a, b) for a, b in s.log_handler.steps])
check("F-01 write_report: sets _current_step='report_writing', passes defaults to the generator, returns its text",
      out == "REPORT-X" and s._current_step == "report_writing" and kw["existing_headers"] == [] and kw["relevant_written_contents"] == []
      and kw["custom_prompt"] == "" and kw["ext_context"] == ["INTERNAL"] and kw["available_images"] == [])
check("F-02 log_handler events: writing_report {existing_headers, context_source 'internal', available_images_count}, then report_completed {report_length, images_embedded}",
      s.log_handler.steps[0] == ("writing_report", {"existing_headers": [], "context_source": "internal", "available_images_count": 0})
      and s.log_handler.steps[1] == ("report_completed", {"report_length": len("REPORT-X"), "images_embedded": 0}))
s = make_self()
run(s.write_report(ext_context="EXT"))
check("F-03 ext_context passed through; context_source 'external'", s.report_generator.calls[0][1]["ext_context"] == "EXT"
      and s.log_handler.steps[0][1]["context_source"] == "external")
for e in ("", [], None):
    s = make_self()
    run(s.write_report(ext_context=e))
    check(f"F-04 falsy ext_context {e!r}: falls back to self.context and is logged as 'internal'",
          s.report_generator.calls[0][1]["ext_context"] == ["INTERNAL"] and s.log_handler.steps[0][1]["context_source"] == "internal")
imgs = [{"url": "u1"}, {"url": "u2"}]
s = make_self(available_images=imgs)
run(s.write_report(existing_headers=["h"], relevant_written_contents=["w"], custom_prompt="cp"))
kw = s.report_generator.calls[0][1]
check("F-05 available_images (made earlier by conduct_research) is passed as is; images_embedded logs len(input), not the number actually embedded",
      kw["available_images"] is imgs and kw["existing_headers"] == ["h"] and kw["relevant_written_contents"] == ["w"] and kw["custom_prompt"] == "cp"
      and s.log_handler.steps[1][1]["images_embedded"] == 2)
s = make_self(log_handler=None)
check("F-06 no log_handler: write_report still works", run(s.write_report()) == "REPORT-X")
s = make_self()
run(s.write_introduction()); run(s.write_report_conclusion("BODY"))
check("F-07 write_introduction / write_report_conclusion do NOT change _current_step; log steps writing_introduction/introduction_completed/writing_conclusion/conclusion_completed",
      s._current_step == "research" and [x[0] for x in s.log_handler.steps] == ["writing_introduction", "introduction_completed", "writing_conclusion", "conclusion_completed"])
s = make_self()
s.add_costs(0.25); s._current_step = "report_writing"; s.add_costs(1)
check("F-08 add_costs adds to research_costs and to step_costs[_current_step]", s.research_costs == 1.25 and s.step_costs == {"research": 0.25, "report_writing": 1})
for bad in ("1", None, [1]):
    try:
        make_self().add_costs(bad)
        ok = False
    except ValueError:
        ok = True
    check(f"F-09 add_costs({bad!r}) -> ValueError", ok)

import gc  # noqa: E402
s = make_self()
with warnings.catch_warnings(record=True) as wl:
    warnings.simplefilter("always")
    s.add_costs(0.1)
    gc.collect()
msgs = [str(w.message) for w in wl]
check("F-10 add_costs with a log_handler calls self._log_event(...) WITHOUT await: coroutine never runs, no 'cost_update' step is recorded",
      any("was never awaited" in m for m in msgs) and not any(x[0] == "cost_update" for x in s.log_handler.steps), msgs[:1])

# =================================================================== summary
head("SUMMARY")
print(f"  {sum(RESULTS)} PASS / {len(RESULTS) - sum(RESULTS)} FAIL of {len(RESULTS)} checks")
sys.exit(0 if all(RESULTS) else 1)
