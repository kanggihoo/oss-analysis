import { createModels, createProvider } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/models.ts";
import { InMemoryCredentialStore } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/auth/credential-store.ts";
import { envApiKeyAuth } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/auth/helpers.ts";
import { lazyApi } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/api/lazy.ts";
import { AssistantMessageEventStream } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/event-stream.ts";

const t0 = Date.now();
const log = (m: string) => console.log(`[+${String(Date.now() - t0).padStart(3)}ms] ${m}`);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// ---- 가짜 "통신 코드" (api/*.ts 자리). 통신만 가짜이고, 이 코드로 들어오는 인자는 실제 Models 가 만든 것이다 ----
const fakeWire: any = {
	stream() { throw new Error("unused"); },
	streamSimple(model: any, ctx: any, opts: any) {
		log(`  ⑥ 통신 코드 streamSimple() 호출됨`);
		const first = ctx.messages[0];
		log(`     model: provider=${model.provider}, api=${model.api}, id=${model.id}, baseUrl=${model.baseUrl}`);
		log(`     context(TranscriptContext): messages=${ctx.messages.map((m: any) => m.role).join(", ")}`);
		log(`     맨 앞 system 메시지: content=${JSON.stringify(first.content)}, toolsAdded=${JSON.stringify((first.toolsAdded ?? []).map((t: any) => t.name))}`);
		log(`     options: apiKey=${opts.apiKey}, reasoning=${opts.reasoning}, headers=${JSON.stringify(opts.headers)}`);
		const out: any = { role: "assistant", content: [], api: model.api, provider: model.provider, model: model.id,
			usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } }, stopReason: "pending", timestamp: Date.now() };
		const stream = new AssistantMessageEventStream();
		(async () => {
			await sleep(30);
			stream.push({ type: "start", partial: out });
			const block: any = { type: "text", text: "" }; out.content.push(block);
			stream.push({ type: "text_start", contentIndex: 0, partial: out });
			for (const piece of ["안", "녕"]) { await sleep(20); block.text += piece; stream.push({ type: "text_delta", contentIndex: 0, delta: piece, partial: out }); }
			stream.push({ type: "text_end", contentIndex: 0, content: block.text, partial: out });
			out.stopReason = "stop";
			stream.push({ type: "done", reason: "stop", message: out });
			stream.end();
		})();
		return stream;
	},
};

const FAKE_MODEL: any = { id: "fake-1", name: "Fake 1", api: "fake-api", provider: "demo", baseUrl: "https://example.invalid/v1",
	reasoning: true, input: ["text"], cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }, contextWindow: 100000, maxTokens: 4096 };

const provider = createProvider({
	id: "demo", name: "Demo", baseUrl: "https://example.invalid/v1",
	auth: { apiKey: envApiKeyAuth("Demo API key", ["DEMO_FLOW_KEY"]) },
	models: [FAKE_MODEL],
	api: lazyApi(async () => { log("  (지연 로딩) 통신 코드 모듈을 불러옴"); await sleep(10); return fakeWire; }),   // 02 §2.3
});
const models = createModels({ credentials: new InMemoryCredentialStore() });
models.setProvider(provider);

process.env.DEMO_FLOW_KEY = "KEY_FROM_ENV";

// ============ 호출 1: 정상 ============
console.log("=== 호출 1: models.streamSimple(model, context, options) ===");
const model = models.getModel("demo", "fake-1")!;                                      // ①
log(`① getModel → ${model.provider}/${model.id} (api=${model.api})`);
const context = { systemPrompt: "너는 도우미야", tools: [{ name: "read", description: "파일 읽기", parameters: { type: "object", properties: {} } as any }],
	messages: [{ role: "user" as const, content: "안녕?", timestamp: Date.now() }] };
const s = models.streamSimple(model, context, { reasoning: "high" });                   // ②
log("② streamSimple() 반환됨 ← 이 시점에 호출한 쪽은 스트림 객체를 이미 받았다. 인증과 통신 코드 로딩은 아직 안 끝났을 수 있다");
(async () => {
	for await (const e of s) log(`  ⑦ 호출한 쪽이 받은 이벤트: ${e.type}${(e as any).delta ? ` "${(e as any).delta}"` : ""}`);
})();
const final = await s.result();
log(`⑧ result(): stopReason=${final.stopReason}, content=${JSON.stringify(final.content)}`);

// ============ 호출 2: 인증 없음 ============
console.log("\n=== 호출 2: 환경변수 키를 지운 뒤 같은 호출 ===");
delete process.env.DEMO_FLOW_KEY;
const s2 = models.streamSimple(model, context, { reasoning: "high" });
log("streamSimple() 반환됨 (예외가 던져지지 않았다)");
const evs: string[] = [];
(async () => { for await (const e of s2) evs.push(e.type); })();
const f2 = await s2.result();
await sleep(5);
log(`이벤트: ${evs.join(", ")}`);
log(`result(): stopReason=${f2.stopReason}, errorMessage=${f2.errorMessage}`);

// ============ 호출 3: complete ============
console.log("\n=== 호출 3: models.completeSimple (이벤트 없이 완성본만) ===");
process.env.DEMO_FLOW_KEY = "KEY_FROM_ENV";
const r3 = await models.completeSimple(model, context, { reasoning: "low" });
log(`completeSimple → stopReason=${r3.stopReason}, text=${(r3.content[0] as any).text}`);

// ============ 호출 4: 호출 옵션으로 키를 직접 ============
console.log("\n=== 호출 4: 옵션으로 apiKey 를 직접 넘김 ===");
const r4 = await models.completeSimple(model, context, { apiKey: "KEY_FROM_OPTION", headers: { "x-trace": "abc" } });
log(`stopReason=${r4.stopReason}`);
