import { Agent } from "../../../repos/pi/packages/agent/src/agent.ts";
import { agentLoop } from "../../../repos/pi/packages/agent/src/agent-loop.ts";
import { setDefaultStreamFn } from "../../../repos/pi/packages/agent/src/stream-fn.ts";
import { assistant, brief, call, model, ok, reply, sleep, text, tool } from "./lib.ts";

const section = (t: string) => console.log(`\n=== ${t} ===`);
const user = (t: string) => ({ role: "user" as const, content: [text(t)], timestamp: Date.now() });

function makeAgent(responses: any[], extra: any = {}, tools: any[] = []) {
	const requests: any[] = [];
	let i = 0;
	const agent = new Agent({
		initialState: { model, systemPrompt: "SYS", tools },
		streamFn: ((m: any, ctx: any, opts: any) => {
			requests.push({ roles: ctx.messages.map((x: any) => x.role), opts });
			const r = responses[Math.min(i++, responses.length - 1)];
			return reply(typeof r === "function" ? r() : r);
		}) as any,
		...extra,
	});
	const events: string[] = [];
	agent.subscribe((e) => {
		events.push(brief(e));
	});
	return { agent, requests, events };
}

// A. 기본 한 바퀴 + 훅 호출 순서 + 옵션/apiKey
section("A. 기본: prompt -> 도구 -> 답, 호출 순서와 streamFn 옵션");
{
	const order: string[] = [];
	const { agent, requests, events } = makeAgent(
		[assistant([call("c1", "read", { n: 1 })], "toolUse"), assistant([text("done")])],
		{
			transformContext: async (m: any) => {
				order.push("transformContext");
				return m;
			},
			convertToLlm: (m: any) => {
				order.push("convertToLlm");
				return m.filter((x: any) => x.role !== "notification");
			},
			getApiKey: (p: string) => {
				order.push(`getApiKey(${p})`);
				return "KEY-" + p;
			},
			prepareRequest: () => {
				order.push("prepareRequest");
				return undefined;
			},
			beforeToolCall: async () => {
				order.push("beforeToolCall");
				return undefined;
			},
			afterToolCall: async () => {
				order.push("afterToolCall");
				return undefined;
			},
			finishTurn: () => {
				order.push("finishTurn");
				return undefined;
			},
			prepareNextTurn: () => {
				order.push("prepareNextTurn");
				return undefined;
			},
		},
		[
			tool("read", async () => {
				order.push("execute");
				return ok("file");
			}),
		],
	);
	await agent.prompt("hi");
	console.log("hook order :", order.join(" > "));
	console.log("events     :", events.join(" | "));
	console.log("request[0] roles:", requests[0].roles, " request[1] roles:", requests[1].roles);
	console.log("apiKey in opts :", requests[0].opts.apiKey, "| opts has beforeToolCall fn:", typeof requests[0].opts.beforeToolCall);
	console.log("state.messages roles:", agent.state.messages.map((m: any) => m.role), "| isStreaming:", agent.state.isStreaming);
}

// B. 병렬 / 순차 이벤트 순서
for (const mode of ["parallel", "sequential"] as const) {
	section(`B. 도구 3개 (A 느림, B 빠름, C 빠름) toolExecution=${mode}`);
	const { agent, events } = makeAgent(
		[assistant([call("a", "A"), call("b", "B"), call("c", "C")], "toolUse"), assistant([text("ok")])],
		{ toolExecution: mode },
		[
			tool("A", async () => {
				await sleep(60);
				return ok("a");
			}),
			tool("B", async () => ok("b")),
			tool("C", async () => ok("c")),
		],
	);
	await agent.prompt("go");
	console.log(events.filter((e) => /tool_execution|toolResult/.test(e)).join("\n"));
}
section("B2. 도구 하나가 executionMode=sequential 이면 전체 순차");
{
	const { agent, events } = makeAgent(
		[assistant([call("a", "A"), call("b", "B")], "toolUse"), assistant([text("ok")])],
		{},
		[
			tool(
				"A",
				async () => {
					await sleep(50);
					return ok("a");
				},
				{ executionMode: "sequential" },
			),
			tool("B", async () => ok("b")),
		],
	);
	await agent.prompt("go");
	console.log(events.filter((e) => /tool_execution/.test(e)).join(" | "));
}

// C. 종료 우선순위
section("C1. 모든 도구 terminate=true -> 다음 요청 없음");
{
	const { agent, requests } = makeAgent([assistant([call("a", "T")], "toolUse"), assistant([text("never")])], {}, [
		tool("T", async () => ok("x", { terminate: true })),
	]);
	await agent.prompt("go");
	console.log("requests:", requests.length);
}
section("C2. 도구 2개 중 1개만 terminate -> 계속");
{
	const { agent, requests } = makeAgent([assistant([call("a", "T"), call("b", "N")], "toolUse"), assistant([text("more")])], {}, [
		tool("T", async () => ok("x", { terminate: true })),
		tool("N", async () => ok("y")),
	]);
	await agent.prompt("go");
	console.log("requests:", requests.length);
}
section("C3. finishTurn=continue (도구 없음, 큐 없음) -> 요청 1회 추가");
{
	let n = 0;
	const { agent, requests } = makeAgent([assistant([text("a")]), assistant([text("b")])], {
		finishTurn: () => (n++ === 0 ? { action: "continue" } : undefined),
	});
	await agent.prompt("go");
	console.log("requests:", requests.length);
}
section("C4. finishTurn=continue 인데 도구 호출이 있었다 -> 추가 요청 없음(이미 계속)");
{
	let n = 0;
	const { agent, requests } = makeAgent(
		[assistant([call("a", "N")], "toolUse"), assistant([text("b")]), assistant([text("c")])],
		{ finishTurn: () => (n++ === 0 ? { action: "continue" } : undefined) },
		[tool("N", async () => ok("y"))],
	);
	await agent.prompt("go");
	console.log("requests:", requests.length, "(도구 턴 1 + 답 1 = 2 이면 중복 없음)");
}
section("C5. finishTurn=end -> 큐에 follow-up이 있어도 종료");
{
	const { agent, requests } = makeAgent([assistant([text("a")]), assistant([text("b")])], { finishTurn: () => ({ action: "end" }) });
	agent.followUp(user("later"));
	await agent.prompt("go");
	console.log("requests:", requests.length, "| follow-up 남음:", agent.hasQueuedMessages());
}
section("C6. stopReason=error 이면 finishTurn(continue)도 무시");
{
	let called = 0;
	const { agent, requests, events } = makeAgent([assistant([], "error", { errorMessage: "boom" }), assistant([text("b")])], {
		finishTurn: () => {
			called++;
			return { action: "continue" };
		},
	});
	await agent.prompt("go");
	console.log("requests:", requests.length, "| finishTurn 호출:", called, "| state.errorMessage:", agent.state.errorMessage, "|", events.slice(-2).join(" | "));
}
section("C7. stopReason=length 이면 도구를 실행하지 않고 에러 결과");
{
	let ran = 0;
	const { agent, requests } = makeAgent([assistant([call("a", "N")], "length"), assistant([text("retry")])], {}, [
		tool("N", async () => {
			ran++;
			return ok("y");
		}),
	]);
	await agent.prompt("go");
	const tr: any = agent.state.messages.find((m: any) => m.role === "toolResult");
	console.log("execute 호출:", ran, "| isError:", tr.isError, "| text:", tr.content[0].text.slice(0, 60), "| requests:", requests.length);
}

// D. 큐
section("D. steering one-at-a-time vs all");
for (const mode of ["one-at-a-time", "all"] as const) {
	const { agent, requests } = makeAgent(
		[assistant([call("a", "N")], "toolUse"), assistant([text("x")]), assistant([text("y")]), assistant([text("z")])],
		{ steeringMode: mode },
		[tool("N", async () => ok("y"))],
	);
	agent.steer(user("s1"));
	agent.steer(user("s2"));
	await agent.prompt("go");
	console.log(mode, "requests:", requests.length, "roles per request:", JSON.stringify(requests.map((r) => r.roles.join(","))));
}

// E. 훅 throw 와 Agent 복구
section("E. convertToLlm 이 throw -> handleRunFailure");
{
	const { agent, events } = makeAgent([assistant([text("x")])], {
		convertToLlm: () => {
			throw new Error("convert failed");
		},
	});
	await agent.prompt("go");
	const last: any = agent.state.messages.at(-1);
	console.log("events:", events.join(" | "));
	console.log("last message:", last.role, last.stopReason, last.errorMessage, "| isStreaming:", agent.state.isStreaming);
}

// F. 중단 시 toolResult 누락
section("F. 순차 실행 중 중단 -> 남은 도구 toolResult 누락?");
{
	const ref: { a?: Agent } = {};
	const { agent } = makeAgent(
		[assistant([call("a", "A"), call("b", "B")], "toolUse"), assistant([text("after")])],
		{ toolExecution: "sequential" },
		[
			tool("A", async () => {
				ref.a!.abort();
				return ok("a");
			}),
			tool("B", async () => ok("b")),
		],
	);
	ref.a = agent;
	await agent.prompt("go");
	const calls = agent.state.messages
		.filter((m: any) => m.role === "assistant")
		.flatMap((m: any) => m.content.filter((c: any) => c.type === "toolCall")).length;
	const results = agent.state.messages.filter((m: any) => m.role === "toolResult").length;
	console.log("toolCall:", calls, "toolResult:", results, "| roles:", agent.state.messages.map((m: any) => m.role).join(","));
}

// G. run 도중 model 변경은 현재 run 에 반영되나
section("G. run 도중 state.model 변경");
{
	const seen: string[] = [];
	const { agent } = makeAgent([], {}, [
		tool("N", async () => {
			agent.state.model = { ...model, id: "changed" };
			return ok("y");
		}),
	]);
	agent.streamFunction = ((m: any) => {
		seen.push(m.id);
		return reply(seen.length === 1 ? assistant([call("a", "N")], "toolUse") : assistant([text("x")]));
	}) as any;
	await agent.prompt("go");
	console.log("한 run 안에서 모델 id 순서:", seen.join(" -> "));
	await agent.prompt("again");
	console.log("다음 run 모델 id:", seen.at(-1));
}

// H. agentLoop 기본 streamFn 없음
section("H1. agentLoop (스트림 반환판) + 기본 streamFn 없음");
{
	let unhandled: any;
	process.once("unhandledRejection", (e) => {
		unhandled = e;
	});
	setDefaultStreamFn(undefined);
	const s = agentLoop([user("hi")], { messages: [], tools: [] }, { model, convertToLlm: (m: any) => m } as any, undefined, undefined as any);
	const winner = await Promise.race([
		(async () => {
			for await (const _ of s) {
			}
			return "stream ended";
		})(),
		sleep(300).then(() => "stream NOT ended after 300ms"),
	]);
	await sleep(50);
	console.log(winner, "| unhandledRejection:", unhandled?.message);
}
