"""deep_research.py 의 파서 함수 5개와 trim_context_to_word_limit 오프라인 실행.
실행: python -I artifacts/gpt-researcher/deep-research-demos/parsers_demo.py
실제 코드: deep_research.py 원본을 import. 대체물: json_repair(엄격한 json.loads 가짜). _stubs.py 참고.
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _stubs

dr = _stubs.load(None, None, None)

def show(title, value):
    print(f"[{title}]\n  -> {value!r}")

print("== 1. parse_search_queries_response (num_queries=3) ==")
Q = dr.parse_search_queries_response
show("JSON 배열", Q('[{"query":"q1","researchGoal":"g1"},{"query":"q2","researchGoal":"g2"}]', 3))
show("코드펜스+앞말", Q('Sure.\n```json\n[{"query":"q1","researchGoal":"g1"}]\n```', 3))
show("dict 래퍼 queries", Q('{"queries":[{"query":"a","researchGoal":"b"}]}', 3))
show("dict 래퍼 searchQueries", Q('{"searchQueries":[{"query":"a","researchGoal":"b"}]}', 3))
show("항목 일부 불량(goal 누락/공백/비문자열)", Q('[{"query":"a"},{"query":"  ","researchGoal":"g"},{"query":"b","researchGoal":5},{"query":" ok ","researchGoal":" goal "}]', 3))
show("개수 초과 -> 앞에서 num_queries개", Q('[{"query":"1","researchGoal":"g"},{"query":"2","researchGoal":"g"},{"query":"3","researchGoal":"g"},{"query":"4","researchGoal":"g"}]', 3))
show("줄 형식 번호", Q("1. Query: q1\n   Goal: g1\n2. Query: q2\n   Goal: g2", 3))
show("줄 형식 불릿+Research Goal", Q("- Query: q1\n- Research Goal: g1", 3))
show("줄 형식 Goal 없는 마지막 Query는 버림", Q("Query: q1\nGoal: g1\nQuery: q2", 3))
show("줄 형식 Query 앞에 Goal만", Q("Goal: g0\nQuery: q1\nGoal: g1", 3))
show("JSON인데 모두 불량 -> 줄 파서로 내려가 []", Q('[{"query":"","researchGoal":"x"}]', 3))
show("빈 문자열", Q("", 3))
show("자연어 문단", Q("I cannot help with that.", 3))
show("JSON 객체에 배열이 문자열 중간 (정규식 후보 [..])", Q('Here: [{"query":"z","researchGoal":"y"}] thanks', 3))

print("\n== 2. parse_follow_up_questions_response (num_questions=3) ==")
F = dr.parse_follow_up_questions_response
show("questions 객체", F('{"questions":["What A?","What B?"]}', 3))
show("followUpQuestions 키", F('{"followUpQuestions":["What A?"]}', 3))
show("비문자열 요소는 str()", F('{"questions":["A?", 5, "", "  "]}', 3))
show("배열 그대로", F('["A?","B?","C?","D?"]', 3))
show("줄 형식 Question:", F("1. Question: What A?\n2. Question: What B?", 3))
show("줄 형식 물음표로 끝나는 줄만", F("- What A?\n- not a question\n- What B?", 3))
show("questions 비어 있음 -> 줄 파서 -> []", F('{"questions":[]}', 3))

print("\n== 3. parse_research_results_response (num_learnings=3) ==")
R = dr.parse_research_results_response
show("정상 JSON", R('{"learnings":[{"insight":"I1","sourceUrl":"https://a.test"},{"insight":"I2","sourceUrl":""}],"followUpQuestions":["N1?","N2?"]}', 3))
show("learning/citation 별칭 키", R('{"learnings":[{"learning":"L1","citation":"https://c.test"}],"questions":["Q?"]}', 3))
show("learnings가 문자열 리스트", R('{"learnings":["plain1","plain2"]}', 3))
show("같은 insight 두 번(citation은 나중 것)", R('{"learnings":[{"insight":"dup","sourceUrl":"https://1"},{"insight":"dup","sourceUrl":"https://2"}]}', 3))
show("learnings 4개, 질문 4개 -> 둘 다 3개로 자름", R('{"learnings":["a","b","c","d"],"followUpQuestions":["1?","2?","3?","4?"]}', 3))
show("JSON 정상이지만 둘 다 비어 있음 -> 줄 파서로 -> 빈 결과", R('{"learnings":[],"followUpQuestions":[]}', 3))
show("줄 형식 Learning [url]:", R("1. Learning [https://a.test]: Insight 1\n2. Learning [https://b.test]: Insight 2\n3. Question: What next?", 3))
show("줄 형식 본문 속 URL 추출", R("Learning: stuff happened at https://example.com/api/v1?key=value", 3))
show("줄 형식 URL 뒤에 따옴표 있으면 URL에서 제외", R('Learning: see "https://x.test/a" ok', 3))
show("빈 문자열", R("", 3))

print("\n== 4. count_words / trim_context_to_word_limit ==")
T = dr.trim_context_to_word_limit
print("MAX_CONTEXT_WORDS =", dr.MAX_CONTEXT_WORDS)
w = lambda n, tag: " ".join([tag] * n)
r = T([w(6, "a"), w(5, "b"), w(4, "c")], max_words=10)
show("max=10, 6+5+4단어 -> 뒤에서부터 채움", [x.split()[0] + f"x{len(x.split())}" for x in r])
r = T([w(3, "a"), w(20, "b"), w(2, "c")], max_words=10)
show("max=10, 3/20/2 -> 가운데가 넘치면 거기서 중단(앞의 a도 버림)", [x.split()[0] + f"x{len(x.split())}" for x in r])
r = T([w(3, "a"), w(20, "b")], max_words=10)
show("max=10, 마지막 항목 하나가 한도 초과 -> 앞 10단어로 잘라 그것만", [x.split()[0] + f"x{len(x.split())}" for x in r])
show("빈 목록", T([], max_words=10))
show("dict 항목은 str(dict)=\"{'Content': 'x y z'}\" 의 단어 수(4)로 셈 -> max=4면 dict 그대로", T([{"Content": "x y z"}], max_words=4))
show("dict 항목 하나가 한도 초과(max=3) -> str(dict)를 앞 3단어로 잘라 문자열로 바꿈", T([{"Content": "x y z"}], max_words=3))
show("리스트 항목(중첩)", T([["a b", "c d"], "e f"], max_words=4))
show("빈 문자열 항목은 0단어라 항상 들어감", T(["", w(2, "z")], max_words=2))
