import { retryProviderRequest } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/provider-retry.ts';
import { retryAssistantCall, isRetryableAssistantError, retryDelayMs } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/retry.ts';
import { isContextOverflow, isRecoverableLength } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/overflow.ts';
import { estimateContextTokens } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/estimate.ts';
import { sanitizeSurrogates } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/sanitize-unicode.ts';
import { shortHash } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/hash.ts';
import { uuidv7 } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/uuid.ts';
import { normalizeProviderError, formatProviderError } from '/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/error-body.ts';

// json-parse.ts 는 partial-json 이 설치되어 있지 않아 repairJson / parseJsonWithRepair 부분(:3-95)만 그대로 복사
const VALID_JSON_ESCAPES = new Set(['"', "\\", "/", "b", "f", "n", "r", "t", "u"]);

function isControlCharacter(char: string): boolean {
	const codePoint = char.codePointAt(0);
	return codePoint !== undefined && codePoint >= 0x00 && codePoint <= 0x1f;
}

function escapeControlCharacter(char: string): string {
	switch (char) {
		case "\b":
			return "\\b";
		case "\f":
			return "\\f";
		case "\n":
			return "\\n";
		case "\r":
			return "\\r";
		case "\t":
			return "\\t";
		default:
			return `\\u${char.codePointAt(0)?.toString(16).padStart(4, "0") ?? "0000"}`;
	}
}

/**
 * Repairs malformed JSON string literals by:
 * - escaping raw control characters inside strings
 * - doubling backslashes before invalid escape characters
 */
export function repairJson(json: string): string {
	let repaired = "";
	let inString = false;

	for (let index = 0; index < json.length; index++) {
		const char = json[index];

		if (!inString) {
			repaired += char;
			if (char === '"') {
				inString = true;
			}
			continue;
		}

		if (char === '"') {
			repaired += char;
			inString = false;
			continue;
		}

		if (char === "\\") {
			const nextChar = json[index + 1];
			if (nextChar === undefined) {
				repaired += "\\\\";
				continue;
			}

			if (nextChar === "u") {
				const unicodeDigits = json.slice(index + 2, index + 6);
				if (/^[0-9a-fA-F]{4}$/.test(unicodeDigits)) {
					repaired += `\\u${unicodeDigits}`;
					index += 5;
					continue;
				}
			}

			if (VALID_JSON_ESCAPES.has(nextChar)) {
				repaired += `\\${nextChar}`;
				index += 1;
				continue;
			}

			repaired += "\\\\";
			continue;
		}

		repaired += isControlCharacter(char) ? escapeControlCharacter(char) : char;
	}

	return repaired;
}

export function parseJsonWithRepair<T>(json: string): T {
	try {
		return JSON.parse(json) as T;
	} catch (error) {
		const repairedJson = repairJson(json);
		if (repairedJson !== json) {
			return JSON.parse(repairedJson) as T;
		}
		throw error;
	}
}

const t0 = Date.now();
const log = (m: string) => console.log(`[+${String(Date.now() - t0).padStart(4)}ms] ${m}`);
class ProviderErr extends Error { status: number | undefined; headers: Headers | undefined;
  constructor(msg: string, status?: number, headers?: Record<string, string>) { super(msg); this.status = status; this.headers = headers ? new Headers(headers) : undefined; } }

console.log("=== 1. retryProviderRequest (통신 코드가 요청을 보낼 때 감싸는 재시도) ===");
{ let n = 0;
  const r = await retryProviderRequest(async () => { n++; log(`  요청 ${n}번째 시도`); if (n < 3) throw new ProviderErr("Service Unavailable", 503); return "성공"; }, { maxRetries: 3 });
  log(`→ 결과: ${r} (총 ${n}번 시도, 503은 재시도 대상)`); }
{ let n = 0;
  try { await retryProviderRequest(async () => { n++; throw new ProviderErr("Bad Request", 400); }, { maxRetries: 3 }); }
  catch (e: any) { log(`→ 400은 재시도하지 않고 바로 실패 (시도 ${n}번): ${e.message}`); } }
{ let n = 0;
  try { await retryProviderRequest(async () => { n++; throw new ProviderErr("Rate limited", 429, { "retry-after": "120" }); }, { maxRetries: 3 }); }
  catch (e: any) { log(`→ 서버가 120초 대기를 요청하면 즉시 실패 (시도 ${n}번): ${e.message}`); } }
{ let n = 0;
  try { await retryProviderRequest(async () => { n++; throw new ProviderErr("boom", 503); }, {}); }
  catch (e: any) { log(`→ maxRetries 를 안 주면 기본 0회라서 재시도 없음 (시도 ${n}번)`); } }

console.log("\n=== 2. 오류 문구로 재시도 여부 판정: isRetryableAssistantError ===");
const mk = (stopReason: string, errorMessage?: string, extra: any = {}): any => ({ role: "assistant", content: [], api: "x", provider: "p", model: "m", stopReason, errorMessage,
  usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } }, timestamp: 1, ...extra });
for (const m of ["Anthropic: overloaded_error", "429 Too many requests", "fetch failed", "WebSocket closed 1006", "insufficient_quota: billing", "subscription_sharing_usage_limit_exceeded", "Validation failed for tool", "prompt is too long: 213462 tokens > 200000 maximum"])
  console.log(`  ${String(isRetryableAssistantError(mk("error", m))).padEnd(5)} ← ${m}`);

console.log("\n=== 3. retryAssistantCall (에이전트 수준 재시도, coding-agent 요약 호출 등이 사용) ===");
{ let n = 0;
  const res = await retryAssistantCall(async () => { n++; return n < 3 ? mk("error", "model is at capacity") : mk("stop"); },
    { enabled: true, maxRetries: 3, baseDelayMs: 100 }, undefined,
    { onRetryScheduled: (a, max, d, e) => log(`  재시도 예약 ${a}/${max}, ${d}ms 후 (${e})`), onRetryFinished: (ok, a) => log(`  재시도 종료: 성공=${ok}, 재시도 횟수=${a}`) });
  log(`→ 최종 stopReason=${res.stopReason}, produce 호출 ${n}번`); }
{ let n = 0;
  const res = await retryAssistantCall(async () => { n++; return mk("error", "insufficient_quota"); }, { enabled: true, maxRetries: 3, baseDelayMs: 100 }, undefined);
  log(`→ 한도 소진 오류는 재시도 없이 반환: produce 호출 ${n}번, stopReason=${res.stopReason}`); }
console.log("  지연 시간 (baseDelayMs=1000): " + [1, 2, 3, 4, 5, 6, 7].map((a) => `${a}회째 ${retryDelayMs({ baseDelayMs: 1000 }, a)}ms`).join(", ") + "  ← 60초에서 잘림");

console.log("\n=== 4. 컨텍스트 초과 판정: isContextOverflow ===");
for (const m of ["prompt is too long: 213462 tokens > 200000 maximum", "Your input exceeds the context window of this model", "The input token count (1196265) exceeds the maximum number of tokens allowed (1048575)", "Throttling error: Too many tokens, please wait before trying again.", "rate limit: too many tokens per minute", "some unrelated error"])
  console.log(`  ${String(isContextOverflow(mk("error", m))).padEnd(5)} ← ${m}`);
console.log(`  조용한 초과(z.ai식): stopReason=stop 인데 input 150000 > contextWindow 128000 → ${isContextOverflow(mk("stop", undefined, { usage: { input: 150000, output: 10, cacheRead: 0, cacheWrite: 0, totalTokens: 150010, cost: {} } }), 128000)}`);
console.log(`  길이 종료 초과(MiMo식): stopReason=length, output=0, input 127500 ≥ 128000*0.99 → ${isContextOverflow(mk("length", undefined, { usage: { input: 127500, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 127500, cost: {} } }), 128000)}`);
console.log(`  isRecoverableLength(length 종료, output 100 < 원하던 4000) → ${isRecoverableLength(mk("length", undefined, { usage: { input: 1, output: 100, cacheRead: 0, cacheWrite: 0, totalTokens: 101, cost: {} } }), 4000)}`);

console.log("\n=== 5. 토큰 추정: estimateContextTokens ===");
{ const msgs: any[] = [
    { role: "user", content: "a".repeat(400), timestamp: 1 },
    mk("stop", undefined, { timestamp: 2, usage: { input: 900, output: 100, cacheRead: 0, cacheWrite: 0, totalTokens: 1000, cost: {} }, content: [{ type: "text", text: "b".repeat(400) }] }),
    { role: "user", content: "c".repeat(800), timestamp: 3 } ];
  const e = estimateContextTokens(msgs);
  console.log(`  마지막 응답이 보고한 토큰=${e.usageTokens}, 그 뒤 추가된 메시지 추정=${e.trailingTokens} (800글자/4), 합계=${e.tokens}`);
  const e2 = estimateContextTokens([msgs[0], msgs[2]]);
  console.log(`  사용량 기록이 없으면 전부 글자수/4로 추정: ${e2.tokens} (1200글자/4)`); }

console.log("\n=== 6. 잘못된 JSON 복구: parseJsonWithRepair ===");
for (const [label, s] of [["문자열 안의 실제 줄바꿈", '{"a":"line1\nline2"}'], ["잘못된 이스케이프", '{"p":"C:\\Users\\x"}'], ["이미 올바른 JSON", '{"ok":true}']] as const) {
  try { console.log(`  ${label}: ${JSON.stringify(parseJsonWithRepair(s))}`); } catch (e: any) { console.log(`  ${label}: 실패 ${e.message}`); } }

console.log("\n=== 7. 작은 도구들 ===");
console.log(`  sanitizeSurrogates("Hi 🙈 \\uD83D end") → ${JSON.stringify(sanitizeSurrogates("Hi 🙈 " + String.fromCharCode(0xd83d) + " end"))}  (짝 맞는 이모지는 유지, 홀로 남은 것만 제거)`);
console.log(`  shortHash("a".repeat(500)) → ${shortHash("a".repeat(500))}  (같은 입력은 항상 같은 값: ${shortHash("a".repeat(500)) === shortHash("a".repeat(500))})`);
const ids = [uuidv7(), uuidv7(), uuidv7()];
console.log(`  uuidv7 3개: ${ids.join(", ")}  (시간순 정렬 가능: ${JSON.stringify(ids) === JSON.stringify([...ids].sort())})`);
const norm = normalizeProviderError(Object.assign(new Error("403 status code (no body)"), { status: 403, error: { error: { message: "blocked by gateway" } } }));
console.log(`  오류 본문 복구: ${formatProviderError(norm, "OpenAI API error")}`);
