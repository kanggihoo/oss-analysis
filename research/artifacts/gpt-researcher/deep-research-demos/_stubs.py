"""deep_research.py 원본 소스를 오프라인으로 불러오는 도우미.

실제 코드: repos/gpt-researcher/gpt_researcher/skills/deep_research.py 를 파일 그대로 import 한다.
대체물(형식을 보이려는 가짜):
  - json_repair: 설치되어 있지 않아 json.loads 를 감싼 가짜. 진짜 json_repair 의 "복구" 동작(쉼표·따옴표 보정)은 재현하지 않는다.
  - gpt_researcher 패키지 __init__, llm_provider.generic.base(ReasoningEfforts), utils.llm(create_chat_completion),
    actions.query_processing(get_search_results), GPTResearcher 클래스: 모두 가짜. 실제 LLM·네트워크 호출 없음.
  - gpt_researcher.utils.enum 은 원본 파일을 그대로 쓴다.
"""
import enum
import importlib.util
import json
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "repos", "gpt-researcher"))
PKG = os.path.join(ROOT, "gpt_researcher")


def _pkg(name, path=None):
    m = types.ModuleType(name)
    m.__path__ = [path] if path else []
    sys.modules[name] = m
    return m


def load(create_chat_completion, get_search_results, GPTResearcher):
    # json_repair 가짜: 엄격한 json.loads. 실패하면 예외(원본 _load_repaired_json 이 잡아서 다음 후보로 넘어감)
    jr = types.ModuleType("json_repair")
    jr.loads = lambda s: json.loads(s)
    sys.modules["json_repair"] = jr

    gp = _pkg("gpt_researcher", PKG)
    gp.GPTResearcher = GPTResearcher
    _pkg("gpt_researcher.llm_provider")
    _pkg("gpt_researcher.llm_provider.generic")
    base = types.ModuleType("gpt_researcher.llm_provider.generic.base")

    class ReasoningEfforts(enum.Enum):
        High = "high"
        Medium = "medium"
        Low = "low"

    base.ReasoningEfforts = ReasoningEfforts
    sys.modules["gpt_researcher.llm_provider.generic.base"] = base

    _pkg("gpt_researcher.utils")
    llm = types.ModuleType("gpt_researcher.utils.llm")
    llm.create_chat_completion = create_chat_completion
    sys.modules["gpt_researcher.utils.llm"] = llm
    sys.modules["gpt_researcher.utils"].llm = llm
    # 원본 enum 파일
    spec = importlib.util.spec_from_file_location("gpt_researcher.utils.enum", os.path.join(PKG, "utils", "enum.py"))
    enum_mod = importlib.util.module_from_spec(spec)
    sys.modules["gpt_researcher.utils.enum"] = enum_mod
    spec.loader.exec_module(enum_mod)

    _pkg("gpt_researcher.actions")
    qp = types.ModuleType("gpt_researcher.actions.query_processing")
    qp.get_search_results = get_search_results
    sys.modules["gpt_researcher.actions.query_processing"] = qp

    _pkg("gpt_researcher.skills", os.path.join(PKG, "skills"))
    spec = importlib.util.spec_from_file_location(
        "gpt_researcher.skills.deep_research", os.path.join(PKG, "skills", "deep_research.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gpt_researcher.skills.deep_research"] = mod
    spec.loader.exec_module(mod)
    return mod
