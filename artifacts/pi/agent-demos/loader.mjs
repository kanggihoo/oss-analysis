const root = new URL("./", import.meta.url);
export async function resolve(specifier, context, next) {
	if (specifier === "@earendil-works/pi-ai") {
		return { url: new URL("./pi-ai-shim.ts", root).href, shortCircuit: true };
	}
	// repos/pi 에는 node_modules 가 없으므로 격리 설치 위치에서 찾는다.
	if (specifier === "partial-json" || specifier === "typebox" || specifier.startsWith("typebox/")) {
		return next(specifier, { ...context, parentURL: new URL("./x.js", root).href });
	}
	return next(specifier, context);
}
