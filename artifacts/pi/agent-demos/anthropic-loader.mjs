const root = new URL("./", import.meta.url);
export async function resolve(specifier, context, next) {
	if (specifier === "@earendil-works/pi-ai") return { url: new URL("./pi-ai-shim.ts", root).href, shortCircuit: true };
	// 요청을 만들기만 하고 보내지 않으므로 SDK 본체는 필요 없다. 기본 export 자리만 채운다.
	if (specifier === "@anthropic-ai/sdk") return { url: new URL("./anthropic-sdk-stub.mjs", root).href, shortCircuit: true };
	if (specifier === "partial-json" || specifier === "typebox" || specifier.startsWith("typebox/")) {
		return next(specifier, { ...context, parentURL: new URL("./x.js", root).href });
	}
	return next(specifier, context);
}
