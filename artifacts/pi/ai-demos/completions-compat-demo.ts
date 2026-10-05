// openai-completions.ts:1585-1726 (detectCompat, getCompat) 를 그대로 복사한 부분
type ResolvedOpenAICompletionsCompat = any; type Model<T> = any;
function detectCompat(model: Model<"openai-completions">): ResolvedOpenAICompletionsCompat {
	const provider = model.provider;
	const baseUrl = model.baseUrl;

	const isZai =
		provider === "zai" ||
		provider === "zai-coding-cn" ||
		baseUrl.includes("api.z.ai") ||
		baseUrl.includes("open.bigmodel.cn");
	const isTogether =
		provider === "together" || baseUrl.includes("api.together.ai") || baseUrl.includes("api.together.xyz");
	const isMoonshot = provider === "moonshotai" || provider === "moonshotai-cn" || baseUrl.includes("api.moonshot.");
	const isOpenRouter = provider === "openrouter" || baseUrl.includes("openrouter.ai");
	const isCloudflareWorkersAI = provider === "cloudflare-workers-ai" || baseUrl.includes("api.cloudflare.com");
	const isCloudflareAiGateway = provider === "cloudflare-ai-gateway" || baseUrl.includes("gateway.ai.cloudflare.com");
	const isNvidia = provider === "nvidia" || baseUrl.includes("integrate.api.nvidia.com");
	const isAntLing = provider === "ant-ling" || baseUrl.includes("api.ant-ling.com");
	const isCerebras = provider === "cerebras" || baseUrl.includes("cerebras.ai");
	const isDeepSeek = provider === "deepseek" || baseUrl.toLowerCase().includes("deepseek.com");

	const isNonStandard =
		isNvidia ||
		isCerebras ||
		provider === "xai" ||
		baseUrl.includes("api.x.ai") ||
		isTogether ||
		baseUrl.includes("chutes.ai") ||
		isDeepSeek ||
		isZai ||
		isMoonshot ||
		provider === "opencode" ||
		baseUrl.includes("opencode.ai") ||
		isCloudflareWorkersAI ||
		isCloudflareAiGateway ||
		isAntLing;

	const useMaxTokens =
		baseUrl.includes("chutes.ai") ||
		isDeepSeek ||
		isMoonshot ||
		isCloudflareAiGateway ||
		isTogether ||
		isNvidia ||
		isAntLing ||
		isZai;

	const isGrok = provider === "xai" || baseUrl.includes("api.x.ai");
	const isOpenRouterDeveloperRoleModel =
		isOpenRouter && (model.id.startsWith("anthropic/") || model.id.startsWith("openai/"));
	const cacheControlFormat = provider === "openrouter" && model.id.startsWith("anthropic/") ? "anthropic" : undefined;

	return {
		supportsStore: !isNonStandard,
		supportsDeveloperRole: isOpenRouterDeveloperRoleModel || (!isNonStandard && !isOpenRouter),
		supportsReasoningEffort:
			!isGrok && !isZai && !isMoonshot && !isTogether && !isCloudflareAiGateway && !isNvidia && !isAntLing,
		supportsUsageInStreaming: true,
		supportsFinishReason: true,
		maxTokensField: useMaxTokens ? "max_tokens" : "max_completion_tokens",
		requiresToolResultName: false,
		requiresAssistantAfterToolResult: false,
		requiresThinkingAsText: false,
		requiresReasoningContentOnAssistantMessages: isDeepSeek,
		thinkingFormat: isDeepSeek
			? "deepseek"
			: isZai
				? "zai"
				: isTogether
					? "together"
					: isAntLing
						? "ant-ling"
						: isOpenRouter
							? "openrouter"
							: "openai",
		openRouterRouting: {},
		vercelGatewayRouting: {},
		chatTemplateKwargs: {},
		chatTemplateArgs: {},
		zaiToolStream: false,
		supportsThinkingTokenBudget: false,
		thinkingTokenBudgetField: undefined,
		// OpenAI compatibility alone does not imply strict JSON-schema tool support.
		supportsStrictMode: false,
		supportsOpenAIGrammarTools: false,
		supportsMidConvoSystemMessages: false,
		supportsMidConvoToolAdditions: false,
		cacheControlFormat,
		sendSessionAffinityHeaders: isOpenRouter,
		sessionAffinityFormat: isOpenRouter ? "openrouter" : "openai",
		supportsLongCacheRetention: !(
			isTogether ||
			isCloudflareWorkersAI ||
			isCloudflareAiGateway ||
			isNvidia ||
			isAntLing
		),
	};
}

/**
 * Get resolved compatibility settings for a model.
 * Auto-detects from provider/URL then overrides with explicit model.compat.
 */
function getCompat(model: Model<"openai-completions">): ResolvedOpenAICompletionsCompat {
	const detected = detectCompat(model);
	if (!model.compat) return detected;

	return {
		supportsStore: model.compat.supportsStore ?? detected.supportsStore,
		supportsDeveloperRole: model.compat.supportsDeveloperRole ?? detected.supportsDeveloperRole,
		supportsReasoningEffort: model.compat.supportsReasoningEffort ?? detected.supportsReasoningEffort,
		supportsUsageInStreaming: model.compat.supportsUsageInStreaming ?? detected.supportsUsageInStreaming,
		supportsFinishReason: model.compat.supportsFinishReason ?? detected.supportsFinishReason,
		maxTokensField: model.compat.maxTokensField ?? detected.maxTokensField,
		requiresToolResultName: model.compat.requiresToolResultName ?? detected.requiresToolResultName,
		requiresAssistantAfterToolResult:
			model.compat.requiresAssistantAfterToolResult ?? detected.requiresAssistantAfterToolResult,
		requiresThinkingAsText: model.compat.requiresThinkingAsText ?? detected.requiresThinkingAsText,
		requiresReasoningContentOnAssistantMessages:
			model.compat.requiresReasoningContentOnAssistantMessages ??
			detected.requiresReasoningContentOnAssistantMessages,
		thinkingFormat: model.compat.thinkingFormat ?? detected.thinkingFormat,
		openRouterRouting: model.compat.openRouterRouting ?? {},
		vercelGatewayRouting: model.compat.vercelGatewayRouting ?? detected.vercelGatewayRouting,
		chatTemplateKwargs: model.compat.chatTemplateKwargs ?? detected.chatTemplateKwargs,
		chatTemplateArgs: model.compat.chatTemplateArgs ?? detected.chatTemplateArgs,
		zaiToolStream: model.compat.zaiToolStream ?? detected.zaiToolStream,
		supportsThinkingTokenBudget: model.compat.supportsThinkingTokenBudget ?? detected.supportsThinkingTokenBudget,
		thinkingTokenBudgetField: model.compat.thinkingTokenBudgetField ?? detected.thinkingTokenBudgetField,
		supportsStrictMode: model.compat.supportsStrictMode ?? detected.supportsStrictMode,
		supportsOpenAIGrammarTools: model.compat.supportsOpenAIGrammarTools ?? detected.supportsOpenAIGrammarTools,
		supportsMidConvoSystemMessages:
			model.compat.supportsMidConvoSystemMessages ?? detected.supportsMidConvoSystemMessages,
		supportsMidConvoToolAdditions:
			model.compat.supportsMidConvoToolAdditions ?? detected.supportsMidConvoToolAdditions,
		cacheControlFormat: model.compat.cacheControlFormat ?? detected.cacheControlFormat,
		sendSessionAffinityHeaders: model.compat.sendSessionAffinityHeaders ?? detected.sendSessionAffinityHeaders,
		sessionAffinityFormat: model.compat.sessionAffinityFormat ?? detected.sessionAffinityFormat,
		supportsLongCacheRetention: model.compat.supportsLongCacheRetention ?? detected.supportsLongCacheRetention,
		vllmPriority: model.compat.vllmPriority,
	};
}

// ================= 실험: 같은 코드가 provider/주소에 따라 설정을 다르게 정한다 =================
const cases: [string, any][] = [
  ["OpenAI (api.openai.com)", { provider: "openai", baseUrl: "https://api.openai.com/v1", id: "gpt-x" }],
  ["DeepSeek", { provider: "deepseek", baseUrl: "https://api.deepseek.com", id: "deepseek-x" }],
  ["OpenRouter + anthropic/ 모델", { provider: "openrouter", baseUrl: "https://openrouter.ai/api/v1", id: "anthropic/claude-x" }],
  ["내 컴퓨터의 로컬 서버(알 수 없는 provider)", { provider: "local", baseUrl: "http://localhost:8080/v1", id: "my-model" }],
];
const keys = ["supportsStore", "supportsDeveloperRole", "supportsReasoningEffort", "maxTokensField", "thinkingFormat",
  "requiresReasoningContentOnAssistantMessages", "supportsStrictMode", "cacheControlFormat", "sendSessionAffinityHeaders", "supportsLongCacheRetention"];
console.log("설정 이름".padEnd(46) + cases.map(([n]) => n.slice(0, 18).padEnd(20)).join(""));
for (const k of keys) {
  console.log(k.padEnd(46) + cases.map(([, m]) => String(getCompat(m)[k]).padEnd(20)).join(""));
}
// 모델의 compat 이 detect 결과를 덮어쓰는지 확인
const overridden = getCompat({ ...cases[3][1], compat: { maxTokensField: "max_tokens", supportsStrictMode: true } });
console.log(`\n로컬 서버 + model.compat { maxTokensField: "max_tokens", supportsStrictMode: true } 를 주면 → maxTokensField=${overridden.maxTokensField}, supportsStrictMode=${overridden.supportsStrictMode}`);
