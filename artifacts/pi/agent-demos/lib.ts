import { Type } from "typebox";
import { AssistantMessageEventStream } from "../../../repos/pi/packages/ai/src/utils/event-stream.ts";

export const usage = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } };
export const model: any = { id: "fake", name: "fake", api: "fake", provider: "fake", baseUrl: "", reasoning: false, input: ["text"], cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }, contextWindow: 1000, maxTokens: 100 };

export const text = (t: string) => ({ type: "text" as const, text: t });
export const call = (id: string, name: string, args: any = {}) => ({ type: "toolCall" as const, id, name, arguments: args });

export function assistant(content: any[], stopReason: any = "stop", extra: any = {}): any {
	return { role: "assistant", content, api: "fake", provider: "fake", model: "fake", usage, stopReason, timestamp: Date.now(), ...extra };
}

/** 응답 한 개를 start -> (delta) -> done/error 로 내보내는 스트림 */
export function reply(msg: any): AssistantMessageEventStream {
	const s = new AssistantMessageEventStream();
	queueMicrotask(() => {
		s.push({ type: "start", partial: { ...msg, content: [] } });
		if (msg.stopReason === "error" || msg.stopReason === "aborted") s.push({ type: "error", reason: msg.stopReason, error: msg });
		else s.push({ type: "done", reason: msg.stopReason, message: msg });
	});
	return s;
}

export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function tool(name: string, run: (args: any, signal?: AbortSignal) => Promise<any>, extra: any = {}): any {
	return {
		name, label: name, description: name,
		parameters: Type.Object({ n: Type.Optional(Type.Number()) }),
		execute: async (id: string, args: any, signal?: AbortSignal) => run(args, signal),
		...extra,
	};
}
export const ok = (t: string, extra: any = {}) => ({ content: [text(t)], details: {}, ...extra });

export const brief = (e: any) => {
	if (e.type === "message_start" || e.type === "message_end") return `${e.type}(${e.message.role}${e.message.role === "toolResult" ? ":" + e.message.toolName : ""})`;
	if (e.type === "tool_execution_start" || e.type === "tool_execution_end") return `${e.type}(${e.toolName})`;
	if (e.type === "turn_end") return `turn_end(stop=${e.message.stopReason}, results=${e.toolResults.length})`;
	if (e.type === "agent_end") return `agent_end(messages=${e.messages.length})`;
	return e.type;
};
