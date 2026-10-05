// openai-codex-responses.ts 의 일부를 줄 번호 범위로 그대로 복사한 것 (formatThrownValue 만 diagnostics.ts import 대신 간단히 대체)
const formatThrownValue = (e: unknown): string => (e instanceof Error ? e.message : String(e));
// :62
const WEBSOCKET_MESSAGE_TOO_BIG_CLOSE_CODE = 1009;
// :695-704 CodexProtocolError
class CodexProtocolError extends Error {
	readonly payload?: unknown;

	constructor(message: string, options?: { payload?: unknown; cause?: unknown }) {
		super(message);
		this.name = "CodexProtocolError";
		this.payload = options?.payload;
		this.cause = options?.cause;
	}
}
// :869-877 WebSocketLike
type WebSocketEventType = "open" | "message" | "error" | "close";
type WebSocketListener = (event: unknown) => void;

interface WebSocketLike {
	close(code?: number, reason?: string): void;
	send(data: string): void;
	addEventListener(type: WebSocketEventType, listener: WebSocketListener): void;
	removeEventListener(type: WebSocketEventType, listener: WebSocketListener): void;
}
// :1027-1039 WebSocketCloseError
class WebSocketCloseError extends Error {
	readonly code?: number;
	readonly reason?: string;
	readonly wasClean?: boolean;

	constructor(message: string, options?: { code?: number; reason?: string; wasClean?: boolean }) {
		super(message);
		this.name = "WebSocketCloseError";
		this.code = options?.code;
		this.reason = options?.reason;
		this.wasClean = options?.wasClean;
	}
}
// :1056-1060 closeWebSocketSilently
function closeWebSocketSilently(socket: WebSocketLike, code = 1000, reason = "done"): void {
	try {
		socket.close(code, reason);
	} catch {}
}
// :1250-1305 extractWebSocketError ~ decodeWebSocketData
function extractWebSocketError(event: unknown): Error {
	if (event && typeof event === "object") {
		const message = "message" in event ? (event as { message?: unknown }).message : undefined;
		if (typeof message === "string" && message.length > 0) {
			return new Error(message);
		}

		const nestedError = "error" in event ? (event as { error?: unknown }).error : undefined;
		if (nestedError instanceof Error && nestedError.message.length > 0) {
			return nestedError;
		}
		if (nestedError && typeof nestedError === "object" && "message" in nestedError) {
			const nestedMessage = (nestedError as { message?: unknown }).message;
			if (typeof nestedMessage === "string" && nestedMessage.length > 0) {
				return new Error(nestedMessage);
			}
		}
	}
	return new Error("WebSocket error");
}

function extractWebSocketCloseError(event: unknown): Error {
	if (event && typeof event === "object") {
		const code = "code" in event ? (event as { code?: unknown }).code : undefined;
		const reason = "reason" in event ? (event as { reason?: unknown }).reason : undefined;
		const wasClean = "wasClean" in event ? (event as { wasClean?: unknown }).wasClean : undefined;
		const codeText = typeof code === "number" ? ` ${code}` : "";
		let reasonText = typeof reason === "string" && reason.length > 0 ? ` ${reason}` : "";
		if (!reasonText && code === WEBSOCKET_MESSAGE_TOO_BIG_CLOSE_CODE) {
			reasonText = " message too big";
		}
		return new WebSocketCloseError(`WebSocket closed${codeText}${reasonText}`.trim(), {
			code: typeof code === "number" ? code : undefined,
			reason: typeof reason === "string" && reason.length > 0 ? reason : undefined,
			wasClean: typeof wasClean === "boolean" ? wasClean : undefined,
		});
	}
	return new Error("WebSocket closed");
}

async function decodeWebSocketData(data: unknown): Promise<string | null> {
	if (typeof data === "string") return data;
	if (data instanceof ArrayBuffer) {
		return new TextDecoder().decode(new Uint8Array(data));
	}
	if (ArrayBuffer.isView(data)) {
		const view = data as ArrayBufferView;
		return new TextDecoder().decode(new Uint8Array(view.buffer, view.byteOffset, view.byteLength));
	}
	if (data && typeof data === "object" && "arrayBuffer" in data) {
		const blobLike = data as { arrayBuffer: () => Promise<ArrayBuffer> };
		const arrayBuffer = await blobLike.arrayBuffer();
		return new TextDecoder().decode(new Uint8Array(arrayBuffer));
	}
	return null;
}
// :1307-1423 parseWebSocket
async function* parseWebSocket(
	socket: WebSocketLike,
	signal?: AbortSignal,
	idleTimeoutMs?: number,
): AsyncGenerator<Record<string, unknown>> {
	const queue: Record<string, unknown>[] = [];
	let pending: (() => void) | null = null;
	let done = false;
	let failed: Error | null = null;
	let sawCompletion = false;

	const wake = () => {
		if (!pending) return;
		const resolve = pending;
		pending = null;
		resolve();
	};

	const onMessage: WebSocketListener = (event) => {
		void (async () => {
			let text: string | null = null;
			try {
				if (!event || typeof event !== "object" || !("data" in event)) return;
				text = await decodeWebSocketData((event as { data?: unknown }).data);
				if (!text) return;
				const parsed = JSON.parse(text) as Record<string, unknown>;
				const type = typeof parsed.type === "string" ? parsed.type : "";
				if (type === "response.completed" || type === "response.done" || type === "response.incomplete") {
					sawCompletion = true;
					done = true;
				}
				queue.push(parsed);
				wake();
			} catch (cause) {
				failed = new CodexProtocolError(`Invalid Codex WebSocket JSON: ${formatThrownValue(cause)}`, {
					cause,
					payload: text,
				});
				done = true;
				wake();
			}
		})();
	};

	const onError: WebSocketListener = (event) => {
		failed = extractWebSocketError(event);
		done = true;
		wake();
	};

	const onClose: WebSocketListener = (event) => {
		if (sawCompletion) {
			done = true;
			wake();
			return;
		}
		if (!failed) {
			failed = extractWebSocketCloseError(event);
		}
		done = true;
		wake();
	};

	const onAbort = () => {
		failed = new Error("Request was aborted");
		done = true;
		wake();
	};

	socket.addEventListener("message", onMessage);
	socket.addEventListener("error", onError);
	socket.addEventListener("close", onClose);
	signal?.addEventListener("abort", onAbort);

	try {
		while (true) {
			if (signal?.aborted) {
				throw new Error("Request was aborted");
			}
			if (queue.length > 0) {
				yield queue.shift()!;
				continue;
			}
			if (done) break;
			let timeout: ReturnType<typeof setTimeout> | undefined;
			await new Promise<void>((resolve, reject) => {
				pending = resolve;
				if (idleTimeoutMs !== undefined && idleTimeoutMs > 0) {
					timeout = setTimeout(() => {
						const error = new Error(`WebSocket idle timeout after ${idleTimeoutMs}ms`);
						failed = error;
						done = true;
						pending = null;
						closeWebSocketSilently(socket, 1000, "idle_timeout");
						reject(error);
					}, idleTimeoutMs);
				}
			}).finally(() => {
				if (timeout) {
					clearTimeout(timeout);
				}
			});
		}

		if (failed) {
			throw failed;
		}
		if (!sawCompletion) {
			throw new Error("WebSocket stream closed before response.completed");
		}
	} finally {
		socket.removeEventListener("message", onMessage);
		socket.removeEventListener("error", onError);
		socket.removeEventListener("close", onClose);
		signal?.removeEventListener("abort", onAbort);
	}
}
// :799-859 parseSSE
async function* parseSSE(response: Response, signal?: AbortSignal): AsyncGenerator<Record<string, unknown>> {
	if (!response.body) return;

	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";
	const onAbort = () => {
		void reader.cancel().catch(() => {});
	};
	signal?.addEventListener("abort", onAbort, { once: true });

	try {
		while (true) {
			if (signal?.aborted) {
				throw new Error("Request was aborted");
			}
			const { done, value } = await reader.read();
			if (signal?.aborted) {
				throw new Error("Request was aborted");
			}
			buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
			// Treat EOF as terminating the residual SSE frame.
			if (done && buffer.trim()) buffer += "\n\n";

			let idx = buffer.indexOf("\n\n");
			while (idx !== -1) {
				const chunk = buffer.slice(0, idx);
				buffer = buffer.slice(idx + 2);

				const dataLines = chunk
					.split("\n")
					.filter((l) => l.startsWith("data:"))
					.map((l) => l.slice(5).trim());
				if (dataLines.length > 0) {
					const data = dataLines.join("\n").trim();
					if (data && data !== "[DONE]") {
						try {
							yield JSON.parse(data) as Record<string, unknown>;
						} catch (cause) {
							throw new CodexProtocolError(`Invalid Codex SSE JSON: ${formatThrownValue(cause)}`, {
								cause,
								payload: data,
							});
						}
					}
				}
				idx = buffer.indexOf("\n\n");
			}

			if (done) break;
		}
	} finally {
		signal?.removeEventListener("abort", onAbort);
		try {
			await reader.cancel();
		} catch {}
		try {
			reader.releaseLock();
		} catch {}
	}
}

// ================= 실험 1: SSE (parseSSE) =================
const sseRaw =
  'event: response.created\ndata: {"type":"response.created","response":{"id":"r1"}}\n\n' +
  'data: {"type":"response.output_text.delta","output_index":0,"delta":"안"}\n\n' +
  'data: {"type":"response.output_text.delta","output_index":0,"delta":"녕"}\n\n' +
  'data: [DONE]\n\n' +
  'data: {"type":"response.completed","response":{"status":"completed"}}\n\n';
const sseChunks: string[] = [];
for (let i = 0; i < sseRaw.length; i += 29) sseChunks.push(sseRaw.slice(i, i + 29));
console.log(`[SSE] 원본 ${sseRaw.length}글자를 ${sseChunks.length}개 덩어리(29글자씩)로 잘라서 보낸다. 첫 덩어리 2개:`);
sseChunks.slice(0, 2).forEach((c, i) => console.log(`  덩어리${i + 1}: ${JSON.stringify(c)}`));
const enc = new TextEncoder();
let sentSse = 0;
const sseBody = new ReadableStream<Uint8Array>({
  async pull(c) {
    await new Promise((r) => setTimeout(r, 20));
    if (sentSse < sseChunks.length) c.enqueue(enc.encode(sseChunks[sentSse++]));
    else c.close();
  },
});
for await (const ev of parseSSE(new Response(sseBody))) {
  console.log(`[SSE] 객체 1개: type=${ev.type}`, (ev as any).delta ? `delta="${(ev as any).delta}"` : "");
}
console.log("[SSE] ('data: [DONE]' 은 무시되어 객체가 나오지 않았다)\n");

// ================= 실험 2: WebSocket (parseWebSocket) =================
const socket: any = new EventTarget(); // addEventListener / removeEventListener 를 가진 가짜 소켓
const t0 = Date.now();
const log = (m: string) => console.log(`[WS +${String(Date.now() - t0).padStart(3)}ms] ${m}`);
const send = (obj: unknown) => socket.dispatchEvent(new MessageEvent("message", { data: JSON.stringify(obj) }));

(async () => {
  log("소비자: for await (parseWebSocket) 시작");
  for await (const ev of parseWebSocket(socket)) log(`소비자: '${ev.type}' 받음`);
  log("소비자: for await 종료");
})();
setTimeout(() => { log("서버: response.created 전송"); send({ type: "response.created" }); }, 50);
setTimeout(() => {
  log("서버: output_text.delta 2개를 연달아 전송");
  send({ type: "response.output_text.delta", delta: "안" });
  send({ type: "response.output_text.delta", delta: "녕" });
}, 120);
setTimeout(() => { log("서버: response.completed 전송"); send({ type: "response.completed" }); }, 200);
setTimeout(() => { log("서버: 연결 닫음"); socket.dispatchEvent(new Event("close")); }, 260);
