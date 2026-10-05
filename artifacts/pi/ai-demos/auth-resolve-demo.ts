import { createModels, createProvider } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/models.ts";
import { InMemoryCredentialStore } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/auth/credential-store.ts";
import { envApiKeyAuth } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/auth/helpers.ts";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const t0 = Date.now();
const log = (m: string) => console.log(`[+${String(Date.now() - t0).padStart(4)}ms] ${m}`);

// 가짜 통신 코드 (이 실험은 인증만 본다)
const fakeApi: any = { stream() {}, streamSimple() {} };

// ---------- 실험 1: OAuth 토큰 갱신은 동시에 여러 번 불러도 한 번만 한다 ----------
let refreshCalls = 0;
const oauth: any = {
	name: "Fake OAuth",
	login: async () => { throw new Error("not used"); },
	refresh: async (c: any) => {
		refreshCalls++;
		log(`  refresh() 호출됨 (누적 ${refreshCalls}번) - 네트워크 요청이라고 가정하고 100ms 걸림`);
		await sleep(100);
		return { type: "oauth", access: "NEW_ACCESS", refresh: "NEW_REFRESH", expires: Date.now() + 60 * 60 * 1000 };
	},
	toAuth: async (c: any) => ({ apiKey: c.access }),
};
const provider = createProvider({
	id: "fake-oauth",
	auth: { oauth },
	models: [],
	api: fakeApi,
});
const credentials = new InMemoryCredentialStore();
const models = createModels({ credentials });
models.setProvider(provider);

// 만료까지 1분 남은 토큰을 저장 (5분 이내면 갱신 대상)
await credentials.modify("fake-oauth", async () => ({
	type: "oauth", access: "OLD_ACCESS", refresh: "OLD_REFRESH", expires: Date.now() + 60 * 1000,
}));
log("저장된 토큰: access=OLD_ACCESS, 만료까지 1분 (5분 이내 → 갱신 대상)");

log("동시에 getAuth 5번 호출");
const results = await Promise.all([1, 2, 3, 4, 5].map(() => models.getAuth("fake-oauth")));
log(`결과 apiKey: ${results.map((r) => r?.auth.apiKey).join(", ")}`);
log(`refresh 호출 횟수: ${refreshCalls}  (5번 호출했지만 갱신은 ${refreshCalls}번)`);
log(`source 라벨: ${results[0]?.source}`);

log("이미 갱신된 토큰으로 getAuth 다시 호출");
await models.getAuth("fake-oauth");
log(`refresh 호출 횟수: ${refreshCalls}  (유효하므로 늘지 않음)`);

// ---------- 실험 2: API 키를 찾는 우선순위 ----------
console.log("");
const keyProvider = createProvider({
	id: "fake-key",
	auth: { apiKey: envApiKeyAuth("Fake API key", ["FAKE_API_KEY"]) },
	models: [],
	api: fakeApi,
});
const store2 = new InMemoryCredentialStore();
const models2 = createModels({ credentials: store2 });
models2.setProvider(keyProvider);
process.env.FAKE_API_KEY = "from-env";

const show = async (label: string, overrides?: any) => {
	const r = await models2.getAuth("fake-key", overrides);
	console.log(`${label.padEnd(44)} → apiKey=${r?.auth.apiKey}, source=${r?.source}`);
};
await show("① 환경변수 FAKE_API_KEY=from-env 만 있음");
await store2.modify("fake-key", async () => ({ type: "api_key", key: "from-store" }));
await show("② + 저장된 credential(from-store)");
await show("③ + 호출 옵션 apiKey=from-option", { apiKey: "from-option" });
delete process.env.FAKE_API_KEY;
await store2.delete("fake-key");
await show("④ 환경변수도 저장값도 없음");
