---
title: graphify LLM Semantic Extraction
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [graphify, knowledge-graph, inference, tooling, architecture, workflow, evidence]
sources:
  - artifacts/graphify/deepwiki/pages-md/2.2-extraction-engine.md
  - repos/graphify/graphify/__main__.py
  - repos/graphify/graphify/llm.py
  - repos/graphify/graphify/cache.py
  - repos/graphify/pyproject.toml
  - repos/graphify/tests/test_llm_backends.py
  - repos/graphify/tests/test_provider_registry.py
confidence: high
---

# graphify LLM Semantic Extraction

이 페이지는 [[graphify]]가 AST만으로 부족한 입력을 처리할 때 사용하는 LLM backend 흐름을 정리한다. 핵심은 **code-only corpus는 로컬 AST만으로 처리하고, 문서/PDF/이미지 같은 semantic input 또는 명시적 LLM 옵션이 있을 때만 LLM backend가 동작한다**는 점이다.

## 언제 LLM backend가 동작하는가

`graphify extract <path>`의 현재 source 기준 동작은 다음이다.

1. `graphify/detect.py:detect()`가 파일을 `code`, `document`, `paper`, `image`, `video`로 분류한다.
2. `graphify/__main__.py`는 `code_files`를 AST extraction 대상으로, `doc_files + paper_files + image_files`를 semantic extraction 대상으로 분리한다.
3. `semantic_files`가 하나라도 있거나 `--dedup-llm`이 지정되면 `needs_llm = True`가 된다.
4. `needs_llm`일 때만 backend auto-detection과 API key 검사가 수행된다.
5. code-only corpus는 API key 없이 로컬 AST extraction만으로 실행된다.

즉 다음은 LLM이 필요 없다.

```bash
graphify extract ./src-only-project
```

단, 프로젝트 안에 `.md`, `.txt`, `.pdf`, `.png` 같은 document/paper/image가 포함되어 semantic extraction 대상이 되면 LLM backend가 필요해진다.

```bash
graphify extract . --backend gemini
```

## LLM이 쓰이는 주요 위치

| 위치 | 트리거 | 역할 |
|---|---|---|
| Semantic extraction | `doc_files + paper_files + image_files`가 있을 때 | 자연어 문서, 논문, 이미지에서 graph fragment 추출 |
| LLM dedup tie-breaker | `graphify extract ... --dedup-llm` | 문자열 유사도만으로 애매한 dedup 후보를 LLM으로 판정 |
| Community labeling | `graphify cluster-only` 또는 `graphify label`에서 label file이 없거나 강제 relabel 시 | `Community N` 대신 2-5단어 community 이름 생성 |
| Lightweight prompt calls | `graphify/llm.py:_call_llm()` 호출 경로 | dedup/label 등 JSON extraction이 아닌 짧은 응답 |

주의: `faster-whisper` 기반 audio/video transcription은 LLM backend와 별도 경로다. URL ingestion도 직접 LLM이 아니라 URL을 Markdown 등 graph-ready source로 만드는 전처리이며, 그 결과 document/paper로 분류되면 이후 semantic extraction에서 LLM을 사용할 수 있다.

## 설정 방법

가장 직접적인 사용 형태는 다음이다.

```bash
graphify extract . --backend gemini
```

모델을 직접 지정할 수도 있다.

```bash
graphify extract . --backend openai --model gpt-4.1-mini
```

semantic extraction 튜닝 옵션은 다음이 중요하다.

```bash
graphify extract . \
  --backend gemini \
  --mode deep \
  --token-budget 60000 \
  --max-concurrency 4 \
  --api-timeout 600
```

- `--backend`: 사용할 backend 선택. 생략하면 환경변수 기반 auto-detection.
- `--model`: backend default model 대신 특정 model 사용.
- `--mode deep`: 더 풍부한 semantic extraction prompt 사용.
- `--token-budget`: chunk packing 기준 token budget. 기본값은 `60_000`.
- `--max-concurrency`: semantic chunk 병렬 처리 수. 기본값은 `4`지만 `ollama`와 `claude-cli`는 기본적으로 직렬 처리된다.
- `--api-timeout`: API timeout seconds. 내부적으로 `GRAPHIFY_API_TIMEOUT`으로 전달된다.
- `--dedup-llm`: dedup의 애매한 pair 판정에 LLM을 추가 사용한다.

## 지원 backend와 환경변수

현재 `repos/graphify/graphify/llm.py`의 `BACKENDS` 기준 builtin backend는 다음이다.

| Backend | API/auth 설정 | 기본 모델/특징 |
|---|---|---|
| `gemini` | `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` | 기본 `gemini-3-flash-preview`, `GRAPHIFY_GEMINI_MODEL`로 override 가능, vision 지원 |
| `kimi` | `MOONSHOT_API_KEY` | 기본 `kimi-k2.6`, OpenAI-compatible endpoint 사용, vision 지원 |
| `claude` | `ANTHROPIC_API_KEY` | 기본 `claude-sonnet-4-6`, Anthropic SDK 경로, vision 지원 |
| `openai` | `OPENAI_API_KEY` | 기본 `gpt-4.1-mini`, `GRAPHIFY_OPENAI_MODEL`로 override 가능, vision 지원 |
| `deepseek` | `DEEPSEEK_API_KEY` | 기본 `deepseek-v4-flash`, `GRAPHIFY_DEEPSEEK_MODEL`로 override 가능 |
| `azure` | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` | deployment는 `AZURE_OPENAI_DEPLOYMENT` 또는 `GRAPHIFY_AZURE_MODEL`, API version은 `AZURE_OPENAI_API_VERSION` |
| `bedrock` | AWS credential chain: `AWS_PROFILE`, `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID` 등 | 기본 Anthropic Claude Sonnet Bedrock model, `GRAPHIFY_BEDROCK_MODEL` override |
| `ollama` | `OLLAMA_BASE_URL`, 선택적으로 `OLLAMA_MODEL`, `OLLAMA_API_KEY` | 기본 `qwen2.5-coder:7b`, 로컬 OpenAI-compatible endpoint |
| `claude-cli` | 로컬 `claude` CLI 설치 및 인증 | Claude Code 구독 인증 사용, API key 없이 `--backend claude-cli`로 명시 선택 |

`pyproject.toml` extras 기준 backend별 추가 dependency는 대략 다음이다.

```bash
uv tool install "graphifyy[gemini]" --force
uv tool install "graphifyy[kimi]" --force
uv tool install "graphifyy[openai]" --force
uv tool install "graphifyy[ollama]" --force
uv tool install "graphifyy[anthropic]" --force
uv tool install "graphifyy[bedrock]" --force
```

`azure`와 `deepseek`는 현재 source상 OpenAI SDK 호환 경로를 사용하므로 OpenAI SDK 설치가 필요하다. 누락 시 `graphify/llm.py`의 backend package hint가 `uv tool install "graphifyy[<extra>]" --force` 형태의 설치 힌트를 출력한다.

## Auto-detection 우선순위

`detect_backend()`의 현재 우선순위는 다음이다.

```text
gemini → kimi → claude → openai → deepseek → azure → bedrock → ollama → custom providers
```

`ollama`는 의도적으로 마지막이다. `OLLAMA_BASE_URL`이 우연히 설정되어 있더라도, 유료 API key가 있으면 그것이 먼저 선택되도록 해서 corpus가 의도치 않게 로컬/원격 Ollama endpoint로 빠지는 것을 막는다. `claude-cli`는 builtin backend지만 auto-detection 대상이 아니므로 명시적으로 `--backend claude-cli`를 줘야 한다.

## Custom providers

사용자는 OpenAI-compatible custom backend를 추가할 수 있다.

Global provider file:

```text
~/.graphify/providers.json
```

예시:

```json
{
  "nvidia": {
    "base_url": "https://integrate.api.nvidia.com/v1",
    "default_model": "minimaxai/minimax-m2.7",
    "env_key": "NVIDIA_API_KEY",
    "pricing": {"input": 0.0, "output": 0.0},
    "temperature": 0
  }
}
```

Project-local provider file도 가능하지만 보안상 기본적으로 무시된다.

```text
.graphify/providers.json
```

이 파일은 cloned/shared repo와 함께 따라오며 corpus와 API key가 전송될 endpoint를 바꿀 수 있기 때문에, 명시적으로 다음 opt-in이 있어야 로드된다.

```bash
GRAPHIFY_ALLOW_LOCAL_PROVIDERS=1 graphify extract . --backend lab
```

custom provider는 builtin backend 이름을 shadowing할 수 없고, `base_url`은 `http`/`https` scheme이어야 한다. non-loopback plaintext HTTP는 허용되더라도 경고가 출력된다.

## Chunking, cache, retry

Semantic extraction은 모든 파일을 한 번에 보내지 않는다.

- `extract_corpus_parallel()`이 token budget 기준으로 파일을 chunking한다.
- 기본 `token_budget`은 `60_000`이다.
- chunk는 parent directory 기준으로 묶어 관련 파일이 같은 prompt에 들어가도록 한다.
- 기본 병렬성은 `max_concurrency=4`다.
- `ollama`와 `claude-cli`는 기본적으로 직렬 실행된다.
- context overflow, `finish_reason="length"`, hollow response가 발생하면 `_extract_with_adaptive_retry()`가 chunk를 반으로 나눠 재시도한다.
- semantic result는 `graphify-out/cache/semantic/`에 cache되어 incremental run에서 재사용된다.

## 보안/운영 주의점

LLM backend는 source corpus를 외부 provider 또는 local endpoint로 보낸다. 따라서 [[workspace-boundaries]]와 [[evidence-backed-analysis]] 관점에서 다음을 지킨다.

- private repo, secret, credential file이 포함되지 않도록 `.graphifyignore`와 detect skip 결과를 확인한다.
- project-local `.graphify/providers.json`는 신뢰한 repo에서만 `GRAPHIFY_ALLOW_LOCAL_PROVIDERS=1`로 활성화한다.
- `ollama`라도 `OLLAMA_BASE_URL`이 remote HTTP endpoint면 corpus가 그 endpoint로 전송된다.
- `INFERRED`/`AMBIGUOUS` semantic edges는 source verification 전까지 hypothesis로 취급한다.

## 관련 페이지

- [[graphify]]
- [[graphify-cli-reference]]
- [[graphify-agent-skill-integration]]
- [[graphify-knowledge-graph-pipeline]]
- [[graphify-graph-analysis]]
- [[workspace-boundaries]]
