import { AssistantMessageEventStream } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/utils/event-stream.ts";

const s = new AssistantMessageEventStream();
const t0 = Date.now();
const log = (m: string) => console.log(`[+${String(Date.now() - t0).padStart(3)}ms] ${m}`);
const waitingCount = () => (s as any).waiting.length; // 기다리는 소비자가 맡겨 둔 열쇠(resolve)의 개수
const queueCount = () => (s as any).queue.length; // 아직 안 꺼낸 이벤트 개수

// ---------- 소비자: for await 로 이벤트를 꺼낸다 (실제 코드에서는 agent-loop.ts:414, lazy.ts:35) ----------
async function consumer() {
	log("소비자: for await 시작");
	for await (const e of s) {
		log(`소비자: '${e.type}' 이벤트를 받음   (waiting=${waitingCount()}, queue=${queueCount()})`);
	}
	log("소비자: for await 종료");
}

consumer(); // 호출만 하고 기다리지 않는다
log(`메인: consumer() 호출 직후. 소비자는 이미 멈춰 있음 (waiting=${waitingCount()} ← 소비자의 열쇠가 들어 있음)`);

// ---------- 생산자: 시간 간격을 두고 push 한다 (실제 코드에서는 anthropic-messages.ts 의 stream() 안쪽 함수) ----------
const msg: any = { role: "assistant", content: [], stopReason: "stop" };
setTimeout(() => {
	log("생산자: push(start)");
	s.push({ type: "start", partial: msg });
}, 100);
setTimeout(() => {
	log("생산자: push(text_delta) 를 연속 2번");
	s.push({ type: "text_delta", contentIndex: 0, delta: "안", partial: msg });
	s.push({ type: "text_delta", contentIndex: 0, delta: "녕", partial: msg });
	log(`생산자: 두 번 push 직후  (waiting=${waitingCount()}, queue=${queueCount()})  ← 소비자가 아직 못 꺼낸 이벤트가 쌓임`);
}, 200);
setTimeout(() => {
	log("생산자: push(done)");
	s.push({ type: "done", reason: "stop", message: msg });
}, 300);

// ---------- 최종 결과: .result() 는 done/error 가 push 되면 채워진다 ----------
s.result().then((r) => log(`result() 가 채워짐: stopReason=${r.stopReason}`));
