import { createModels, createProvider } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/models.ts";
import { InMemoryCredentialStore } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/auth/credential-store.ts";
import { envApiKeyAuth } from "/Users/kkh/Desktop/oss-analysis/repos/pi/packages/ai/src/auth/helpers.ts";

const fakeApi: any = { stream() {}, streamSimple() {} };
const ENV = "DEMO_API_KEY";
process.env[ENV] = "KEY_FROM_ENV";            // 환경변수에는 API 키가 있다

let refreshFails = false;
const oauth: any = {
	name: "Fake OAuth",
	login: async () => { throw new Error("unused"); },
	refresh: async () => { if (refreshFails) throw new Error("invalid_grant (리프레시 토큰 거부됨)"); return { type: "oauth", access: "NEW_OAUTH", refresh: "r2", expires: Date.now() + 3600e3 }; },
	toAuth: async (c: any) => ({ apiKey: c.access }),
};

function setup(providerAuth: any) {
	const store = new InMemoryCredentialStore();
	const models = createModels({ credentials: store });
	models.setProvider(createProvider({ id: "demo", auth: providerAuth, models: [], api: fakeApi }));
	return { store, models };
}
const show = async (label: string, run: () => Promise<any>) => {
	try {
		const r = await run();
		console.log(`${label}\n   → apiKey=${r?.auth.apiKey}, source=${r?.source}`);
	} catch (e: any) {
		console.log(`${label}\n   → 오류: [${e.code ?? e.name}] ${e.message}`);
	}
};

// 경우 1: 저장된 OAuth 로그인이 유효하다 + 환경변수에도 키가 있다
{
	const { store, models } = setup({ oauth, apiKey: envApiKeyAuth("Demo key", [ENV]) });
	await store.modify("demo", async () => ({ type: "oauth", access: "STORED_OAUTH", refresh: "r", expires: Date.now() + 3600e3 }));
	await show("[경우1] 저장된 OAuth(유효) + 환경변수 키 있음", () => models.getAuth("demo"));
}

// 경우 2: 저장된 OAuth 가 만료됐고 갱신이 실패한다 + 환경변수에는 키가 있다
{
	const { store, models } = setup({ oauth, apiKey: envApiKeyAuth("Demo key", [ENV]) });
	await store.modify("demo", async () => ({ type: "oauth", access: "OLD", refresh: "r", expires: Date.now() + 1000 }));
	refreshFails = true;
	await show("[경우2] 저장된 OAuth(만료 임박) + 갱신 실패 + 환경변수 키 있음", () => models.getAuth("demo"));
	refreshFails = false;
}

// 경우 3: 저장된 것이 oauth 인데, 이 provider 에는 oauth 방식이 없다 (apiKey 방식만 있다) + 환경변수 키 있음
{
	const { store, models } = setup({ apiKey: envApiKeyAuth("Demo key", [ENV]) });
	await store.modify("demo", async () => ({ type: "oauth", access: "STORED_OAUTH", refresh: "r", expires: Date.now() + 3600e3 }));
	await show("[경우3] 저장된 oauth + provider에 oauth 처리기 없음 + 환경변수 키 있음", () => models.getAuth("demo"));
}

// 경우 4: 저장된 것이 아무것도 없다 + 환경변수 키 있음
{
	const { models } = setup({ oauth, apiKey: envApiKeyAuth("Demo key", [ENV]) });
	await show("[경우4] 저장된 것 없음 + 환경변수 키 있음", () => models.getAuth("demo"));
}
