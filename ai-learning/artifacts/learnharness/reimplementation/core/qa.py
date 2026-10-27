"""Question-answer contract (S2): schemas, validation, answer objects, compact form.
Python re-implementation from the spec 1.1-1.6 + the 1.5 code ranges (question-core.ts etc.)."""
import json
import math
import re

# ---- JS-compatible string helpers ---------------------------------------------------
JS_WS = "\t\n\v\f\r              " \
        "    　﻿"
_DEBRIS = JS_WS + ":.\"'`"


def js_trim(s):
    return s.strip(JS_WS)


def strip_model_value_debris(value):
    return value.lstrip(_DEBRIS).rstrip(_DEBRIS)


def js_round(x):  # Math.round: ties toward +infinity (python round() is banker's)
    return math.floor(x + 0.5)


# ---- tool/kind tables (pending.ts) ----------------------------------------------------
QUESTION_TOOLS = ("quiz", "probe", "ask_user_question", "explain", "recall")


def tool_question_kind(tool):
    if tool in ("quiz", "probe"):
        return "quiz"
    if tool in ("explain", "recall"):
        return "explain"
    return "ask"


CONFIDENCE_STOPS = [0, 30, 50, 70, 90, 100]
DEFAULT_CONFIDENCE_INDEX = 2

# ---- schemas (JSON-schema dicts shaped like TypeBox output) -----------------------------
S_STR = {"type": "string"}
S_BOOL = {"type": "boolean"}


def _obj(props, required):
    return {"type": "object", "properties": props, "required": required}


_OPT_PROBE = _obj({"label": S_STR, "value": S_STR}, ["label"])
# 1.3: only ask options carry `description` (quizOptionProps/askOptionProps are outside the 1.5 ranges)
_OPT_ASK = _obj({"label": S_STR, "value": S_STR, "description": S_STR}, ["label"])
S_TYPE = {"anyOf": [{"type": "string", "const": "predict"}, {"type": "string", "const": "check"}]}
S_CORRECT = {"anyOf": [S_STR, {"type": "array", "items": S_STR}]}


def _quiz_base_props():
    return {
        "question": S_STR,
        "options": {"type": "array", "items": _OPT_PROBE, "minItems": 2},
        "multiSelect": S_BOOL,
        "explanation": S_STR,
        "correctAnswer": S_CORRECT,
        "details": S_STR,
    }


QUIZ_BASE_REQUIRED = ["question", "options", "explanation", "correctAnswer"]
PROBE_SCHEMA = _obj(_quiz_base_props(), QUIZ_BASE_REQUIRED)
QUIZ_SCHEMA = _obj({"type": S_TYPE, "nodeId": S_STR, **_quiz_base_props()}, ["type", "nodeId"] + QUIZ_BASE_REQUIRED)
EXPLAIN_BASE_SCHEMA = _obj({"question": S_STR, "correctAnswer": S_STR, "details": S_STR}, ["question", "correctAnswer"])
EXPLAIN_SCHEMA = _obj({"type": S_TYPE, "nodeId": S_STR, "question": S_STR, "correctAnswer": S_STR, "details": S_STR},
                      ["type", "nodeId", "question", "correctAnswer"])
ASK_SCHEMA = _obj({"question": S_STR, "details": S_STR,
                   "options": {"type": "array", "items": _OPT_ASK, "minItems": 2}, "multiSelect": S_BOOL},
                  ["question"])


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(schema, value, path="$"):
    """Minimal JSON-schema validator (what the agent loop's TypeBox check does before execute).
    Unknown object keys are tolerated (additionalProperties unspecified in the spec: a guess)."""
    if "anyOf" in schema:
        if any(not validate(s, value, path) for s in schema["anyOf"]):
            return []
        return [f"{path}: must match one of the allowed shapes"]
    if "const" in schema:
        return [] if value == schema["const"] and type(value) is type(schema["const"]) else [f"{path}: must be equal to constant {schema['const']!r}"]
    t = schema.get("type")
    if t == "string":
        if not isinstance(value, str):
            return [f"{path}: must be string"]
        if len(value) < schema.get("minLength", 0):
            return [f"{path}: must not be shorter than {schema['minLength']} characters"]
        return []
    if t == "boolean":
        return [] if isinstance(value, bool) else [f"{path}: must be boolean"]
    if t == "number":
        return [] if _is_num(value) else [f"{path}: must be number"]
    if t == "array":
        if not isinstance(value, list):
            return [f"{path}: must be array"]
        if len(value) < schema.get("minItems", 0):
            return [f"{path}: must have at least {schema['minItems']} items"]
        out = []
        for i, item in enumerate(value):
            out += validate(schema["items"], item, f"{path}[{i}]")
        return out
    if t == "object":
        if not isinstance(value, dict):
            return [f"{path}: must be object"]
        out = []
        for k in schema.get("required", []):
            if k not in value:
                out.append(f"{path}.{k}: required")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                out += validate(sub, value[k], f"{path}.{k}")
        return out
    return []


# ---- argument preparation (R-02) ----------------------------------------------------------
def parse_options_if_string(options):
    if not isinstance(options, str):
        return options
    try:
        parsed = json.loads(options)
        if isinstance(parsed, list):
            return parsed
    except ValueError:
        pass
    return options


def prepare_question_arguments(args):
    if isinstance(args, dict):
        if isinstance(args.get("options"), str):
            parsed = parse_options_if_string(args["options"])
            if parsed is not args["options"]:
                return {**args, "options": parsed}
        return args
    return args


_UNDEF = object()


def _literals_of(prop):
    if "anyOf" in prop:
        return [x for m in prop["anyOf"] for x in _literals_of(m)]
    return [prop["const"]] if "const" in prop else []


def _accepts_null(prop):
    return prop.get("type") == "null" or any(m.get("type") == "null" for m in prop.get("anyOf", []))


def _try_parse(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return _UNDEF


def _strict_in(v, seq):
    return any(type(v) is type(x) and v == x for x in seq)


def heal_encoded_arguments(args, schema):
    """A STRING where the schema expects literal union / boolean / number / array is JSON-parsed and kept
    when the parsed value fits. Well-formed args come back as the same object."""
    if not isinstance(args, dict):
        return args
    props = schema.get("properties")
    if not props:
        return args
    healed = None
    for key, prop in props.items():
        raw = args.get(key)
        if not isinstance(raw, str):
            continue
        parsed = _try_parse(raw)
        fixed = _UNDEF
        literals = _literals_of(prop)
        if literals:
            if _strict_in(raw, literals):
                continue
            if parsed is not _UNDEF and _strict_in(parsed, literals):
                fixed = parsed
        if fixed is _UNDEF and _accepts_null(prop) and parsed is None:
            fixed = None
        if fixed is _UNDEF and prop.get("type") == "boolean" and isinstance(parsed, bool):
            fixed = parsed
        if fixed is _UNDEF and prop.get("type") in ("number", "integer") and _is_num(parsed):
            fixed = parsed
        if fixed is _UNDEF and prop.get("type") == "array" and isinstance(parsed, list):
            fixed = parsed
        if fixed is not _UNDEF:
            if healed is None:
                healed = dict(args)
            healed[key] = fixed
    return healed if healed is not None else args


# ---- authoring problems (R-03..R-06) --------------------------------------------------------
def _option_problems(options):
    problems, keys = [], []
    for i, option in enumerate(options):
        label = js_trim(option["label"])
        if len(label) == 0:
            problems.append(f"options[{i}].label is empty — every option needs a label.")
            continue
        key = js_trim(option["value"]) if option.get("value") is not None and js_trim(option["value"]) else label
        if key in keys:
            problems.append(f'Two options resolve to the same value "{key}" — options must be distinct.')
        keys.append(key)
    return problems, keys


def ask_option_problems(options):
    return _option_problems(options)[0]


def coerce_correct_answer(correct, option_values):
    def clean(v):
        t = js_trim(v)
        return t if t in option_values else strip_model_value_debris(v)

    if isinstance(correct, list):
        return [clean(v) for v in correct]
    t = js_trim(correct)
    if t in option_values:
        return [t]
    if t.startswith("[") and t.endswith("]"):
        try:
            parsed = json.loads(t)
            if isinstance(parsed, list):
                return [clean(str(v)) for v in parsed]
        except ValueError:
            pass
    return [clean(correct)]


def quiz_input_problems(inp):
    problems, keys = _option_problems(inp["options"])
    entries = coerce_correct_answer(inp["correctAnswer"], keys)
    unique = list(dict.fromkeys(entries))
    if len(unique) == 0 or any(len(v) == 0 for v in unique):
        problems.append("correctAnswer is required — provide the value (or label) of the correct option(s).")
        return problems
    for v in unique:
        if v not in keys:
            valid = ", ".join(f'"{k}"' for k in keys)
            problems.append(f'correctAnswer "{v}" does not match any option value. Valid values: {valid}. '
                            "Copy the exact value (or label) of the intended option — never a paraphrase or slug.")
    if len(unique) > 1 and inp.get("multiSelect") is not True:
        problems.append(f"correctAnswer lists {len(unique)} values but multiSelect is not true — a single-select "
                        "question with several correct answers can never be answered correctly. "
                        "Set multiSelect: true, or make exactly one option correct.")
    return problems


def explain_input_problems(inp):
    if len(js_trim(inp["correctAnswer"])) == 0:
        return ["correctAnswer is required — commit to the full correct answer BEFORE posing the question."]
    return []


# ---- tool results (tool-execute.ts) ------------------------------------------------------------
def invalid_input_result(tool_name, problems):
    return {"content": [{"type": "text", "text": f'Invalid tool input for tool "{tool_name}":\n'
                                                 + "\n".join(f"- {p}" for p in problems)}],
            "isError": True, "details": {"tool": tool_name, "problems": list(problems)}}


def question_result():
    return {"content": [{"type": "text", "text": "Question posed — the turn ends here; the learner's graded "
                                                 "answer arrives as this call's result."}],
            "details": None, "terminate": True}


def make_question_stopper():
    """Turn-end hook (R-07): end only when every question call of this message resolved without error."""
    def stopper(message, tool_results):
        called = {c["id"] for c in message["content"]
                  if c.get("type") == "toolCall" and c.get("name") in QUESTION_TOOLS}
        if not called:
            return False
        for r in tool_results:
            if r["toolCallId"] in called and r.get("isError"):
                return False
        return True
    return stopper


# ---- reveal rule (teaching R-03) -------------------------------------------------------------------
def normalize_quiz_type(raw):
    if not isinstance(raw, str):
        return None
    v = strip_model_value_debris(raw)
    return v if v in ("predict", "check") else None


def question_needs_reveal(tool, raw_input, phase):
    if tool not in ("quiz", "explain") or phase != "teach":
        return False
    t = raw_input.get("type") if isinstance(raw_input, dict) else None
    return normalize_quiz_type(t) != "predict"


# ---- options, shuffle, grading (C-05, C-07, C-03) -----------------------------------------------------
def normalize_options(options):
    coerced = parse_options_if_string(options)
    lst = coerced if isinstance(coerced, list) else []
    seen, out = set(), []
    for o in lst:
        label = js_trim(o["label"])
        value = (js_trim(o["value"]) if o.get("value") is not None else "") or label
        desc = (js_trim(o["description"]) if o.get("description") is not None else "") or None
        if len(label) == 0:
            continue
        if value in seen:
            raise ValueError(f'duplicate option value "{value}"')
        seen.add(value)
        out.append({"label": label, "value": value, "description": desc})
    return out


_M = 0xFFFFFFFF


def seeded_random(seed):
    """FNV-1a(32) over UTF-16 code units, then mulberry32. Ported from the C-07 description."""
    h = 2166136261
    units = seed.encode("utf-16-le")
    for i in range(0, len(units), 2):
        h ^= units[i] | (units[i + 1] << 8)
        h = (h * 16777619) & _M
    a = h

    def rand():
        nonlocal a
        a = (a + 0x6D2B79F5) & _M
        t = ((a ^ (a >> 15)) * (1 | a)) & _M
        t = (((t + (((t ^ (t >> 7)) * (61 | t)) & _M)) & _M) ^ t)
        return ((t ^ (t >> 14)) & _M) / 4294967296
    return rand


def shuffle_options(options, rand=None):
    import random
    rand = rand or random.random
    out = list(options)
    for i in range(len(out) - 1, 0, -1):
        j = math.floor(rand() * (i + 1))
        out[i], out[j] = out[j], out[i]
    return out


def resolve_correct(correct, options):
    if correct is None:
        return {"indices": [], "error": "correctAnswer is required"}
    arr = coerce_correct_answer(correct, [o["value"] for o in options])
    if len(arr) == 0:
        return {"indices": [], "error": "correctAnswer is required"}
    by_value = {o["value"]: i + 1 for i, o in enumerate(options)}
    indices = []
    for raw in arr:
        v = js_trim(raw)
        if v not in by_value:
            known = ", ".join(f'"{o["value"]}"' for o in options)
            return {"indices": [], "error": f'correctAnswer "{v}" does not match any option value ({known})'}
        indices.append(by_value[v])
    return {"indices": sorted(set(indices))}


def is_correct(selected, correct):
    return len(selected) == len(correct) and sorted(selected) == sorted(correct)


# ---- QuestionData (question-dock.tsx 262-306) ------------------------------------------------------------
def make_question_data(tool, tool_call_id, inp, created_at=None):
    kind = tool_question_kind(tool)
    multi = isinstance(inp, dict) and inp.get("multiSelect") is True
    raw_opts = inp.get("options") if kind in ("quiz", "ask") else None
    if kind == "quiz":
        mode = "multi-select" if multi else "single-select"
    elif kind == "ask" and raw_opts:
        mode = "multi-select" if multi else "single-select"
    else:
        mode = "text"
    options = normalize_options(raw_opts or [])
    ordered = shuffle_options(options, seeded_random(tool_call_id)) if kind == "quiz" and options else options
    qd = {"id": tool_call_id, "kind": kind,
          "questionType": normalize_quiz_type(inp.get("type")) if kind == "quiz" else None,
          "question": inp["question"], "context": inp.get("details"), "mode": mode,
          "options": ordered, "createdAt": created_at}
    if kind == "quiz":
        qd["correctIndices"] = resolve_correct(inp.get("correctAnswer"), ordered)["indices"]  # AFTER shuffling
        qd["explanation"] = inp.get("explanation")
    if kind == "explain":
        qd["committedAnswer"] = inp.get("correctAnswer")
    return qd


# ---- answer request + object (question-dock 381-394, buildAnswer) --------------------------------------------
def build_answer_request(kind, values=None, dont_know=False, other=None, text=None, thinking=None,
                         confidence_index=None, mode=None, reading_thinking=None):
    mode = mode or ("text" if kind == "explain" else "choice")
    req = {"dontKnow": dont_know, "values": list(values or [])}
    if other is not None:
        req["other"] = other
    if mode == "text" and text is not None:
        req["text"] = text
    if mode != "text":
        t = js_trim(thinking) if thinking else ""
        if t:
            req["thinking"] = t
    if kind == "quiz":  # always sent on quiz answers: 50 means 50
        idx = DEFAULT_CONFIDENCE_INDEX if confidence_index is None else confidence_index
        req["confidence"] = CONFIDENCE_STOPS[idx]
    if reading_thinking is not None and js_trim(reading_thinking):
        req["readingThinking"] = js_trim(reading_thinking)
    return req


def _trim_or_none(s):
    return (js_trim(s) or None) if isinstance(s, str) else None


def build_answer(qd, req, tool=None, answered_at="1970-01-01T00:00:00Z"):
    base = {"kind": qd["kind"], "questionText": qd["question"],
            "options": [{"index": i + 1, "label": o["label"]} for i, o in enumerate(qd["options"])],
            "dontKnow": req.get("dontKnow") is True, "answers": [], "answeredAt": answered_at}
    if tool:
        base["tool"] = tool
    if qd.get("questionType"):
        base["questionType"] = qd["questionType"]
    for key in ("thinking", "readingThinking"):
        v = _trim_or_none(req.get(key))
        if v:
            base[key] = v
    if req.get("values"):
        by_value = {o["value"]: {**o, "index": i + 1} for i, o in enumerate(qd["options"])}
        for v in req["values"]:
            opt = by_value.get(v)
            if opt is None:
                continue  # unknown value ignored
            base["answers"].append({"label": opt["label"], "value": opt["value"], "index": opt["index"]})
        base["answers"].sort(key=lambda a: a["index"])
    for key in ("other", "text"):
        v = _trim_or_none(req.get(key))
        if v:
            base[key] = v
    if qd["kind"] == "quiz":
        ci = qd.get("correctIndices") or []
        base["correctIndices"] = ci
        if qd.get("explanation") is not None:
            base["explanation"] = qd["explanation"]
        base["correct"] = False if base["dontKnow"] else is_correct([a["index"] for a in base["answers"]], ci)
        if not base["dontKnow"] and req.get("confidence") is not None:
            base["confidence"] = max(0, min(100, js_round(req["confidence"])))
    if qd["kind"] == "explain" and qd.get("committedAnswer") is not None:
        base["committed"] = qd["committedAnswer"]
    return base


def dismissed_answer(kind, question_text, answered_at="1970-01-01T00:00:00Z"):
    return {"kind": kind, "questionText": question_text, "dontKnow": False, "answers": [],
            "dismissed": True, "answeredAt": answered_at}


def compact_answer_for_model(ad):
    if ad.get("dismissed"):
        return {"kind": ad.get("kind"), "dismissed": True}
    out = {"kind": ad.get("kind")}
    if ad.get("dontKnow"):
        out["dontKnow"] = True
    answers = ad.get("answers")
    if isinstance(answers, list) and answers:
        out["answers"] = [{"index": a["index"], "label": a["label"]} for a in answers]
    if ad.get("text"):
        out["text"] = ad["text"]
    if ad.get("other"):
        out["other"] = ad["other"]
    if ad.get("correct") is not None and not ad.get("dontKnow"):
        out["correct"] = ad["correct"]
    if ad.get("confidence") is not None:
        out["confidence"] = ad["confidence"]
    thinking = ad["thinking"] if ad.get("thinking") is not None else ad.get("note")
    if thinking:
        out["thinking"] = thinking
    if ad.get("readingThinking"):
        out["thinkingWhileReading"] = ad["readingThinking"]
    return out
