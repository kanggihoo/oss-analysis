// 세션 도중 도구가 바뀔 때 (1) agent가 기록에 무엇을 쌓는지, (2) ai의 Anthropic 요청에서 앞부분(tools, system)이 유지되는지 확인한다.
// agent 쪽은 실제 Agent 클래스, ai 쪽은 AI_SRC 가 가리키는 실제 anthropic-messages.ts 의 buildParams 를 쓴다.
// 네트워크 호출 없음: onPayload 에서 요청 본문을 잡고 throw 한다.
import { Agent } from "../../../repos/pi/packages/agent/src/agent.ts";
import { assistant, text, tool, reply } from "./lib.ts";

const AI_SRC = process.env.AI_SRC!;
const { stream: anthropicStream } = await import(`${AI_SRC}/api/anthropic-messages.ts`);

const mk = (native: boolean): any => ({
	id: "claude-test", name: "claude-test", api: "anthropic-messages", provider: "anthropic", baseUrl: "https://example.invalid",
	reasoning: false, input: ["text"], cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }, contextWindow: 200000, maxTokens: 1000,
	compat: native ? { supportsMidConvoSystemMessages: true, supportsMidConvoToolChanges: true } : {},
});
const t = (name: string, description = name) => tool(name, async () => ({ content: [text("ok")], details: {} }), { description });
const user = (s: string) => ({ role: "user" as const, content: [text(s)], timestamp: Date.now() });
const clone = (x: any) => JSON.parse(JSON.stringify(x));

/** 실제 Agent 로 두 번 prompt 하면서 사이에 tools 를 바꾸고, 매 요청의 context 를 모은다 */
async function collect(before: any[], after: any[]) {
	const ctxs: any[] = [];
	const agent = new Agent({
		initialState: { model: mk(true), systemPrompt: "SYS", tools: before },
		streamFn: ((_m: any, ctx: any) => {
			ctxs.push(clone(ctx));
			return reply(assistant([text("answer")]));
		}) as any,
	});
	await agent.prompt("hi");
	agent.state.tools = after;
	await agent.prompt("again");
	return ctxs;
}

async function build(native: boolean, ctx: any) {
	let params: any;
	const s = anthropicStream(mk(native), ctx, {
		client: {} as any,
		onPayload: (p: any) => { params = clone(p); throw new Error("stop"); },
	});
	await s.result();
	return params;
}

const strip = (x: any): any => JSON.parse(JSON.stringify(x, (k, v) => (k === "cache_control" ? undefined : v)));
const toolSummary = (p: any) => (p.tools ?? []).map((x: any) => x.name + (x.defer_loading ? "[defer]" : "")).join(", ") || "(없음)";
const blocks = (p: any) =>
	p.messages
		.filter((m: any) => m.role === "system")
		.map((m: any) => (Array.isArray(m.content) ? m.content : []).map((b: any) => b.type === "text" ? "text" : `${b.type}:${b.tool?.name ?? ""}${b.tool?.type === "tool_definition" ? "(정의)" : ""}`).join("+"));

async function scenario(title: string, native: boolean, before: any[], after: any[]) {
	console.log(`\n=== ${title} (native=${native}) ===`);
	const ctxs = await collect(before, after);
	const sysMsgs = ctxs[1].messages.filter((m: any) => m.role === "system");
	console.log(`agent 기록(요청 2): roles=${ctxs[1].messages.map((m: any) => m.role).join(",")}`);
	console.log(`  system 메시지 ${sysMsgs.length}개: ${sysMsgs.map((m: any, i: number) => `#${i} toolsAdded=[${(m.toolsAdded ?? []).map((x: any) => x.name)}] toolsRemoved=[${(m.toolsRemoved ?? []).map((x: any) => x.name)}]`).join(" | ")}`);
	console.log(`  맨 앞 system 메시지가 요청 1과 요청 2에서 같은가: ${JSON.stringify(ctxs[0].messages[0]) === JSON.stringify(ctxs[1].messages[0])}`);
	const p1 = await build(native, ctxs[0]);
	const p2 = await build(native, ctxs[1]);
	console.log(`Anthropic 요청 1: tools=[${toolSummary(p1)}]`);
	console.log(`Anthropic 요청 2: tools=[${toolSummary(p2)}]  중간 system 메시지 블록=${JSON.stringify(blocks(p2))}`);
	// defer_loading 도구는 캐시 표시가 붙은 마지막 일반 도구 뒤에 놓이므로, 앞부분 비교에서는 일반 도구만 본다(요청 본문만 보는 비교이고 실제 캐시 적중은 서버에서만 알 수 있다).
	const active = (p: any) => strip((p.tools ?? []).filter((x: any) => !x.defer_loading));
	const sameTools = JSON.stringify(active(p1)) === JSON.stringify(active(p2));
	const sameSystem = JSON.stringify(strip(p1.system)) === JSON.stringify(strip(p2.system));
	const m1 = strip(p1.messages), m2 = strip(p2.messages);
	const sameMsgPrefix = JSON.stringify(m2.slice(0, m1.length)) === JSON.stringify(m1);
	console.log(`앞부분 유지(캐시 가능): 일반 tools 동일=${sameTools}, system 동일=${sameSystem}, 요청 1의 messages가 요청 2의 앞부분=${sameMsgPrefix}`);
}

await scenario("S1 도구 추가", true, [t("read"), t("bash")], [t("read"), t("bash"), t("edit")]);
await scenario("S2 도구 제거", true, [t("read"), t("bash")], [t("read")]);
await scenario("S3 같은 이름 재정의", true, [t("read", "v1")], [t("read", "v2")]);
await scenario("S4 추가, 모델이 중간 변경 미지원", false, [t("read"), t("bash")], [t("read"), t("bash"), t("edit")]);
