import http from "node:http";
import { streamProxy } from "../../../repos/pi/packages/agent/src/proxy.ts";
import { model, sleep } from "./lib.ts";

const section = (t: string) => console.log(`\n=== ${t} ===`);
const sse = (o: any) => `data: ${JSON.stringify(o)}\n\n`;
const usage = { input: 1, output: 2, cacheRead: 0, cacheWrite: 0, totalTokens: 3, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } };

let lastRequest: any;
const server = http.createServer((req, res) => {
	let body = "";
	req.on("data", (c) => (body += c));
	req.on("end", async () => {
		lastRequest = { url: req.url, auth: req.headers.authorization, body: JSON.parse(body) };
		const scenario = lastRequest.body.options.metadata?.scenario;
		if (scenario === "http500") {
			res.writeHead(500, { "Content-Type": "application/json" });
			res.end(JSON.stringify({ error: "upstream down" }));
			return;
		}
		res.writeHead(200, { "Content-Type": "text/event-stream" });
		const send = (o: any) => res.write(sse(o));
		send({ type: "start" });
		if (scenario === "normal") {
			send({ type: "text_start", contentIndex: 0 });
			send({ type: "text_delta", contentIndex: 0, delta: "Hel" });
			send({ type: "text_delta", contentIndex: 0, delta: "lo" });
			send({ type: "text_end", contentIndex: 0 });
			send({ type: "toolcall_start", contentIndex: 1, id: "t1", toolName: "read" });
			send({ type: "toolcall_delta", contentIndex: 1, delta: '{"path": "a.' });
			send({ type: "toolcall_delta", contentIndex: 1, delta: 'txt"}' });
			send({ type: "toolcall_end", contentIndex: 1, toolCall: { type: "toolCall", id: "t1", name: "read", arguments: { path: "a.txt" } } });
			// 마지막 이벤트는 개행 없이 끝낸다
			res.end(`data: ${JSON.stringify({ type: "done", reason: "toolUse", usage })}`);
		} else if (scenario === "eof") {
			send({ type: "text_start", contentIndex: 0 });
			send({ type: "text_delta", contentIndex: 0, delta: "partial answer" });
			res.end();
		} else if (scenario === "cut-toolcall") {
			send({ type: "toolcall_start", contentIndex: 0, id: "t9", toolName: "read" });
			send({ type: "toolcall_delta", contentIndex: 0, delta: '{"path": "b' });
			res.end();
		} else if (scenario === "slow") {
			send({ type: "text_start", contentIndex: 0 });
			send({ type: "text_delta", contentIndex: 0, delta: "x" });
			await sleep(2000);
			res.end();
		}
	});
});
await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
const proxyUrl = `http://127.0.0.1:${(server.address() as any).port}`;

async function run(scenario: string, signal?: AbortSignal) {
	const options: any = {
		proxyUrl,
		authToken: "TOKEN",
		signal,
		metadata: { scenario },
		reasoning: "low",
		// 서버로 가면 안 되는 것들
		apiKey: "SECRET-PROVIDER-KEY",
		onPayload: () => {},
		beforeToolCall: () => {},
	};
	const stream = streamProxy(model, { messages: [{ role: "user", content: [{ type: "text", text: "hi" }], timestamp: 0 }] } as any, options);
	const types: string[] = [];
	const partials = new Set<any>();
	let argSnapshots: any[] = [];
	for await (const e of stream) {
		types.push(e.type);
		if ("partial" in e) partials.add(e.partial);
		if (e.type === "toolcall_delta") argSnapshots.push(JSON.stringify((e.partial.content[e.contentIndex] as any).arguments));
	}
	const result = await stream.result();
	return { types, result, distinctPartialObjects: partials.size, argSnapshots };
}

section("1. 정상 (toolUse 로 끝, 마지막 줄 개행 없음)");
{
	const r = await run("normal");
	console.log("events:", r.types.join(","));
	console.log("방출된 partial 객체 개수(같은 객체면 1):", r.distinctPartialObjects);
	console.log("toolcall_delta 때마다 arguments:", r.argSnapshots.join(" -> "));
	console.log("result:", JSON.stringify({ stopReason: r.result.stopReason, content: r.result.content, usage: r.result.usage.totalTokens }));
	console.log("요청 url/auth:", lastRequest.url, lastRequest.auth);
	console.log("요청 body 키:", Object.keys(lastRequest.body), "| options 키:", Object.keys(lastRequest.body.options));
	console.log("body 문자열에 SECRET 포함?", JSON.stringify(lastRequest.body).includes("SECRET"));
}
section("2. 터미널 이벤트 없이 EOF");
{
	const r = await run("eof");
	console.log("events:", r.types.join(","), "| stopReason:", r.result.stopReason, "|", r.result.errorMessage, "| content:", JSON.stringify(r.result.content));
}
section("3. HTTP 500 + {error}");
{
	const r = await run("http500");
	console.log("events:", r.types.join(","), "| stopReason:", r.result.stopReason, "|", r.result.errorMessage);
}
section("4. toolcall_end 없이 끊김: partialJson 잔존?");
{
	const r = await run("cut-toolcall");
	console.log("stopReason:", r.result.stopReason, "| content:", JSON.stringify(r.result.content));
}
section("5. 중단");
{
	const ac = new AbortController();
	setTimeout(() => ac.abort(), 150);
	const r = await run("slow", ac.signal);
	console.log("events:", r.types.join(","), "| stopReason:", r.result.stopReason, "|", r.result.errorMessage);
}
server.closeAllConnections();
server.close();
