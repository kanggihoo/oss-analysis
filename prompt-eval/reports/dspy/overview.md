---
sha: "3fdb93f205b0f24a9338449c5bbad0092b5cce1c"
created: 2026-10-22
updated: 2026-10-22
sources:
  - README.md
  - LICENSE
  - pyproject.toml
  - dspy/__init__.py
  - dspy/__metadata__.py
  - dspy/dsp/utils/settings.py
  - dspy/signatures/signature.py
  - dspy/predict/predict.py
  - dspy/predict/__init__.py
  - dspy/primitives/module.py
  - dspy/primitives/base_module.py
  - dspy/primitives/example.py
  - dspy/adapters/base.py
  - dspy/adapters/chat_adapter.py
  - dspy/clients/lm.py
  - dspy/clients/base_lm.py
  - dspy/clients/execution.py
  - dspy/clients/backend_selection.py
  - dspy/clients/_litellm.py
  - dspy/clients/cache.py
  - dspy/clients/__init__.py
  - dspy/clients/costs.py
  - dspy/clients/model_metadata/__init__.py
  - dspy/clients/model_metadata/LICENSE
  - dspy/utils/caching.py
  - dspy/utils/parallelizer.py
  - dspy/utils/usage_tracker.py
  - dspy/evaluate/evaluate.py
  - dspy/evaluate/auto_evaluation.py
  - dspy/teleprompt/__init__.py
  - dspy/teleprompt/teleprompt.py
  - dspy/teleprompt/vanilla.py
  - dspy/teleprompt/bootstrap.py
  - dspy/teleprompt/random_search.py
  - dspy/teleprompt/mipro_optimizer_v2.py
  - dspy/teleprompt/simba.py
  - dspy/teleprompt/simba_utils.py
  - dspy/teleprompt/copro_optimizer.py
  - dspy/teleprompt/infer_rules.py
  - dspy/teleprompt/avatar_optimizer.py
  - dspy/teleprompt/bettertogether.py
  - dspy/teleprompt/bootstrap_finetune.py
  - dspy/teleprompt/gepa/gepa.py
  - dspy/teleprompt/gepa/gepa_utils.py
  - dspy/teleprompt/gepa/instruction_proposal.py
  - dspy/teleprompt/reanchor/reanchor.py
  - dspy/experimental/__init__.py
  - dspy/predict/flex/flex.py
  - dspy/lm15.py
  - dspy/_vendor/lm15-LICENSE
  - dspy/_vendor/lm15-provenance.txt
  - dspy/_vendor/UPDATING.md
  - dspy/_vendor/lm15/auth.py
  - dspy/_vendor/lm15/registry.py
  - dspy/_vendor/lm15/router.py
  - docs/docs/learn/optimization/optimizers.md
  - docs/README.md
  - .github/.internal_dspyai/pyproject.toml
  - scripts/update_model_metadata.py
---

# DSPy Analysis Overview

경로 표기: 이 문서의 `파일:심볼`은 모두 `repos/dspy/` 기준이다(작업 폴더 `prompt-eval/repos/dspy/`). 검증 수준은 `코드 확인` / `추론` / `미확인`만 쓴다. 이번 분석은 설치·실행을 하지 않았으므로 `실행 확인`은 없다(구조도 HTML의 브라우저 검사는 3절에 따로 적는다).

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/stanfordnlp/dspy` (`prompt-eval/artifacts/dspy/repo-metadata.txt`)
- **작업트리 상태**: Clean (shallow clone `--depth 50`, 2026-10-22, 브랜치 `main`, 커밋 날짜 2026-10-22, 버전 `3.4.1`: `pyproject.toml` `version`, `dspy/__metadata__.py`)
- **분석 목적**: 내가 만든 스킬(SKILL.md)·프롬프트를 (1) 같은 케이스로 평가하고, (2) 어떤 모델에서 가장 잘 되는지 비교하고, (3) 평가 지표로 개선하는 데 쓸 도구를 파악한다. 2절 "목적 질문에 대한 초기 답"이 이 목적에 한정한 답이고, 기능 지도는 레포 전체를 본다.
- **라이선스**: MIT — `LICENSE`(1줄 "MIT License", 3줄 "Copyright (c) 2023 Stanford Future Data Systems"). 하위 LICENSE 두 개도 모두 MIT다: `dspy/_vendor/lm15-LICENSE`(Copyright 2026 lm15 contributors, 벤더링한 lm15용), `dspy/clients/model_metadata/LICENSE`(Copyright 2023 Berri AI. 머리에 "`enterprise/` 디렉터리가 있으면 그 안은 `enterprise/LICENSE`를 따른다"는 문구가 있으나 이 레포에는 `enterprise/`가 없고, 같은 파일의 본문은 MIT, 이 폴더의 데이터는 LiteLLM 모델 가격표 스냅샷). `find`로 확인한 LICENSE 파일은 이 3개뿐이다. (코드 확인)
- **분석 대상 제품**: Python 라이브러리 `dspy`(`pyproject.toml` `[project] name="dspy"`, Python `>=3.10, <3.16`, 패키지 `dspy`·`dspy.*`만 배포: `[tool.setuptools.packages.find]`). 중첩·별도 입구:
  - `dspy/_vendor/lm15/`: 외부 레포 `cmpnd-ai/lm15-python`을 subtree로 들여온 LM 전송 계층(`dspy/_vendor/lm15-provenance.txt`, `dspy/_vendor/UPDATING.md`). 패키지에 포함되어 배포된다.
  - `dspy/experimental/`, `dspy/predict/flex/`, `dspy/teleprompt/reanchor/`: 실험 표시(`@experimental`)가 붙은 기능.
  - `.github/.internal_dspyai/pyproject.toml`: 호환 별칭 패키지 `dspy-ai`(`dependencies = ["dspy>=3.4.1"]`). 릴리스용.
  - `docs/`(MkDocs 문서 사이트와 빌드 스크립트), `scripts/`(벤더·모델 메타데이터 갱신), `tests/`(열지 않음).
- **스펙 범위**: 지도만(기능 스펙 미작성) · 제외: 전체 — 사용자 결정(2026-10-22), 이유: 평가셋·채점 함수가 먼저 있어야 하고 최적화 호출 비용이 크며, 이번 목적(스킬 평가·개선·모델 적합도 기록 환경)은 promptfoo·prompt-optimizer로 먼저 다룬다. 평가 케이스가 쌓이면 다시 검토한다.

용어(처음 한 번만).
- **Signature**: 입력·출력 필드와 지시문(instructions, 클래스 docstring)을 선언한 클래스. DSPy에서 "프롬프트"의 뼈대다.
- **demos**: 프롬프트에 끼워 넣는 few-shot 예시(`Predict.demos`).
- **옵티마이저(teleprompter)**: `compile(student, trainset=...)`로 프로그램의 지시문 또는 demos를 바꾼 복사본을 돌려주는 알고리즘(`dspy/teleprompt/teleprompt.py` `Teleprompter.compile`).
- **metric**: `(example, prediction)`을 받아 점수를 돌려주는 함수.

---

## 2. 프로젝트 개요

README는 DSPy를 "언어 모델을 프롬프팅이 아니라 프로그래밍하는 프레임워크"로 소개하고, 프롬프트와 가중치를 최적화하는 알고리즘을 제공한다고 쓴다(`README.md` 앞부분). 코드로 보면 구성은 세 층이다. (1) 프로그램 층: `Signature`로 입출력과 지시문을 선언하고 `Predict`·`Module`로 호출한다. (2) LM 층: `Adapter`가 signature·demos·입력을 messages로 바꾸고 `dspy.LM`이 엔진(벤더링 lm15 또는 litellm)으로 제공자 API를 호출한다. (3) 개선 층: `Evaluate`가 devset에 metric을 매기고 `dspy.teleprompt`의 옵티마이저가 그 점수로 지시문·demos·(옵션) 가중치를 바꾼다. (코드 확인: `dspy/predict/predict.py` `Predict.forward`, `dspy/clients/lm.py` `LM`, `dspy/evaluate/evaluate.py` `Evaluate.__call__`, `dspy/teleprompt/__init__.py`)

### 목적 질문에 대한 초기 답

이 소절은 "SKILL.md·프롬프트 평가·모델 비교·개선"에 한정한다. 아래 조립 예는 읽은 코드로 짠 것이며 실행하지 않았다.

**요점부터.** DSPy가 자동으로 고치는 대상은 `Signature.instructions`(지시문)와 `Predict.demos`다. SKILL.md 전체를 입력으로 주면 알아서 평가하는 기능은 없다. SKILL.md 본문을 지시문 문자열로 넣어 한 프로그램으로 만들면 평가·개선 대상이 된다. 다만 DSPy는 그 지시문을 LM 한 번(또는 모듈이 정한 횟수)의 호출 안에서 돌릴 뿐, Claude Code가 스킬을 불러 쓰는 실행 환경(도구·파일 접근)은 재현하지 않는다(추론: 호출 경로가 messages 한 벌을 만드는 구조임을 코드로 확인, 하네스 재현 여부는 코드에 해당 기능이 없다는 근거).

#### Q1. 평가: 같은 케이스를 여러 모델에 돌려 비교하려면 입력을 어떻게 구성하나

| 구성 요소 | 하는 일 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|
| 프롬프트를 프로그램으로 | 지시문 문자열을 `dspy.Signature("입력 -> 출력", instructions=...)` 또는 `ensure_signature(str, instructions)`로 넣고 `dspy.Predict`(또는 `ChainOfThought` 등)로 감싼다. `Signature.with_instructions(text)`는 필드는 그대로 두고 지시문만 바꾼 새 클래스를 돌려준다. 어댑터는 지시문을 시스템 메시지의 "your objective is: …"로 넣는다 | `dspy/signatures/signature.py` `ensure_signature`, `Signature.with_instructions`; `dspy/adapters/chat_adapter.py` `ChatAdapter.format_task_description` | 코드 확인 |
| 케이스 | `dspy.Example(**row).with_inputs("입력필드")`의 리스트가 devset. `with_inputs`로 표시한 필드만 프로그램에 입력으로 가고 나머지는 정답(label)이다. CSV·JSON·HF 등에서 불러오는 `DataLoader`도 있다 | `dspy/primitives/example.py` `Example.with_inputs`, `Example.inputs`; `dspy/datasets/dataloader.py` `DataLoader.from_csv`·`from_json` | 코드 확인 |
| 채점 | `dspy.Evaluate(devset=, metric=, num_threads=)(program)`이 각 예시에 `program(**example.inputs())`를 부르고 `metric(example, prediction)`을 매긴다. 반환은 `EvaluationResult(score, results)`이며 `score`는 점수 합을 예시 수로 나눈 백분율, `results`는 `(example, prediction, score)` 목록이다. 예외가 난 예시는 `failure_score`(기본 0.0)로 센다. 결과는 `save_as_csv`/`save_as_json`으로 저장 가능 | `dspy/evaluate/evaluate.py` `Evaluate.__call__` | 코드 확인 |
| metric 작성 | 불리언·숫자를 돌려주는 함수, 또는 LLM 심사 모듈(`dspy.SemanticF1`, `dspy.CompleteAndGrounded`. 둘 다 `forward(example, pred, trace=None)`). 안전한 시그니처는 `metric(example, pred, trace=None)`이다: `BootstrapFewShot`은 `metric(example, prediction, trace)`로, `Evaluate`와 `SIMBA`는 두 인자로 부른다. GEPA만 5인자 `(gold, pred, trace, pred_name, pred_trace)`를 요구한다 | `dspy/evaluate/auto_evaluation.py` `SemanticF1.forward`; `dspy/teleprompt/bootstrap.py` `BootstrapFewShot._bootstrap_one_example` 호출부(`self.metric(example, prediction, trace)`); `dspy/teleprompt/simba_utils.py` `wrap_program`; `dspy/teleprompt/gepa/gepa.py` `GEPA.__init__`(`inspect.signature(metric).bind(None, None, None, None, None)`) | 코드 확인 |
| 모델 지정 | `dspy.LM("provider/model", temperature=, max_tokens=, cache=, num_retries=3, engine="auto")`. 모델 문자열 형식은 `provider/model`. OpenAI 추론 계열(`o1`, `gpt-5…`)은 `temperature=1.0`(또는 None)과 `max_tokens>=16000`(또는 None)이 아니면 `LMConfigurationError`를 낸다 | `dspy/clients/lm.py` `LM.__init__`, `LM._get_initial_kwargs`, `_is_openai_reasoning_model` | 코드 확인 |
| 모델 전환 (방법 4가지) | (a) `dspy.configure(lm=...)`: 전역 기본값. 처음 호출한 스레드만 다시 호출 가능. (b) `with dspy.context(lm=...):` 블록 안에서만 덮어씀. `Evaluate`의 병렬 워커에도 이 override가 복사되어 전달된다. (c) `program.set_lm(lm)`: 모든 Predict의 `lm` 속성에 지정(`Predict.lm`이 전역보다 우선). (d) 호출마다 `predict(lm=..., **inputs)`. 같은 program·같은 devset에 LM만 바꿔 `Evaluate`를 반복하면 모델 비교가 된다 | `dspy/dsp/utils/settings.py` `Settings.configure`, `Settings.context`; `dspy/primitives/module.py` `Module.set_lm`; `dspy/predict/predict.py` `Predict._forward_preprocess`(`kwargs.pop("lm", self.lm) or settings.lm`); `dspy/utils/parallelizer.py` `ParallelExecutor`(`thread_local_overrides` 복사) | 코드 확인 |
| 공정 비교 장치 | 응답 캐시 키는 요청 전체(모델명 포함: `request_to_dict`의 `"model"`)를 해시하므로 모델 사이에 캐시가 섞이지 않는다. 같은 모델·같은 입력의 재실행은 캐시에서 나온다(재현성↑, 비용↓). 샘플링을 다시 하고 싶으면 `rollout_id`나 `cache=False` | `dspy/clients/execution.py` `PreparedCall.key`; `dspy/_vendor/lm15/serde.py` `request_to_dict`; `dspy/clients/cache.py` `Cache.cache_key` | 코드 확인(키 구성) / 캐시 동작은 미실행 |

조립 예(실행하지 않은 스케치, 추론):

```python
skill = open("SKILL.md").read()
sig = dspy.Signature("task -> result", instructions=skill)
prog = dspy.Predict(sig)
ev = dspy.Evaluate(devset=devset, metric=metric, num_threads=8)
for name in ["openai/…", "anthropic/…"]:
    with dspy.context(lm=dspy.LM(name)):
        print(name, ev(prog).score)
```

#### Q2. 개선: 평가 지표를 받아 프롬프트를 고치는 기능

모든 옵티마이저는 `Teleprompter.compile(student, trainset=..., ...)`로 프로그램 복사본을 돌려준다(`dspy/teleprompt/teleprompt.py`). 필요한 입력은 공통으로 (1) 프로그램, (2) metric, (3) trainset(`dspy.Example` 목록, 라벨 없이 입력만 있어도 되는 경우가 문서에 있음: `docs/docs/learn/optimization/optimizers.md`)이다. 옵티마이저별 차이는 아래 표다.

| 옵티마이저 | 무엇을 바꾸나 | 한 줄 설명 | 추가 입력·특이점 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|---|
| `GEPA` | 지시문(instruction)만 (+ 실험 `dspy.Flex` 코드) | 실행 트레이스와 metric이 돌려준 텍스트 피드백을 `reflection_lm`이 읽고 predictor별 새 지시문을 제안하는 진화 탐색. 외부 패키지 `gepa==0.1.4`의 `optimize`를 호출 | metric이 `{"score":…, "feedback":…}`를 돌려주면 피드백으로 쓰인다. `reflection_lm` 또는 `instruction_proposer` 필수. 예산은 `auto`/`max_full_evals`/`max_metric_calls` 중 정확히 하나. valset 없으면 trainset을 valset으로 씀. 기본 제안기 `InstructionProposer(skills=[SKILL.md 경로|디렉터리|문자열])`로 SKILL.md를 반영 제안 시 참고 자료로 줄 수 있다(최적화 대상이 아니라 제안 LM에 주는 참고 자료) | `dspy/teleprompt/gepa/gepa.py` `GEPA.__init__`·`compile`(`seed_candidate = {name: pred.signature.instructions}`); `dspy/teleprompt/gepa/instruction_proposal.py` `_SkillLoader`, `InstructionProposer` | 코드 확인(DSPy 쪽) / `gepa` 패키지 내부는 미탐색 |
| `MIPROv2` | 지시문 + few-shot demos 둘 다 | 데이터·프로그램 요약을 보고 지시문 후보를 `prompt_model`로 쓰고, 부트스트랩 demos 후보와 함께 Optuna(베이지안 탐색)로 조합을 고른다. `max_bootstrapped_demos=0`이고 `max_labeled_demos=0`이면 지시문만(zero-shot) 최적화 | `metric`, `prompt_model`(제안용), `task_model`(평가용), `auto`(`light`/`medium`/`heavy`) 또는 `num_candidates`+`num_trials`. `optuna` 선택 의존성 필요 | `dspy/teleprompt/mipro_optimizer_v2.py` `MIPROv2.__init__`·`compile`·`AUTO_RUN_SETTINGS`; `dspy/propose/grounded_proposer.py` `GroundedProposer` | 코드 확인 |
| `SIMBA` | 지시문에 규칙 덧붙이기 + demos 추가(둘 다) | 미니배치에서 출력 변동이 큰 어려운 예시를 골라, LM이 실패를 돌아보고 규칙을 지시문 뒤에 붙이거나(`append_a_rule`) 성공 예시를 demo로 붙인다(`append_a_demo`). `max_demos=0`이면 규칙만 | `metric`, `trainset`(`len(trainset) >= bsize` 필수), 별도 valset 입력 없음. `prompt_model` | `dspy/teleprompt/simba.py` `SIMBA.__init__`·`compile`; `dspy/teleprompt/simba_utils.py` `append_a_rule`(`with_instructions(old + "\n\n" + advice)`), `append_a_demo` | 코드 확인 |
| `COPRO` | 지시문(와 마지막 출력 필드 접두어) | 지시문 후보 `breadth`개를 생성해 trainset으로 채점하고 `depth` 번 좌표 상승 | `metric`, `prompt_model`, `breadth`, `depth` | `dspy/teleprompt/copro_optimizer.py` `COPRO.compile` | 코드 확인(헤더·호출 구조) / 후보 선택 세부는 미탐색 |
| `InferRules` | 지시문에 규칙 덧붙임 + 부트스트랩 demos | `BootstrapFewShot`을 상속. 학습 예시에서 자연어 규칙 `num_rules`개를 유도해 지시문 뒤에 붙이고 valset으로 후보 `num_candidates`개를 비교 | `metric`, trainset(valset 없으면 앞 50%를 train으로) | `dspy/teleprompt/infer_rules.py` `InferRules.compile`, `update_program_instructions` | 코드 확인(구조) / 규칙 유도 프롬프트는 미탐색 |
| `AvatarOptimizer` | 지시문(Avatar 에이전트 actor) | 성공·실패 사례를 비교해 actor 지시문을 고침. `dspy.Avatar` 모듈 전용이며 `dspy.predict` 공개 export에는 없다 | `metric`, `max_iters`, `lower_bound` | `dspy/teleprompt/avatar_optimizer.py` `AvatarOptimizer`(`with_instructions` 사용); `dspy/predict/__init__.py`에 avatar 없음 | 코드 확인(지시문 갱신 위치) / 전체 흐름 미탐색 |
| `BootstrapFewShot` | few-shot demos만 | `teacher`(기본: 자기 자신)로 학습 예시를 돌려 metric을 통과한 트레이스를 demo로 모은다. 라벨 예시도 `max_labeled_demos`까지 섞는다 | `metric`, `trainset`, `teacher`(선택), `max_bootstrapped_demos`(4), `max_labeled_demos`(16), `max_rounds` | `dspy/teleprompt/bootstrap.py` `BootstrapFewShot.compile` | 코드 확인 |
| `BootstrapFewShotWithRandomSearch` (별칭 `BootstrapRS`) | few-shot demos만 | `BootstrapFewShot`을 후보 `num_candidate_programs`(16)개 만들어 valset으로 고른다 | `metric`, `trainset`, `valset`(없으면 trainset) | `dspy/teleprompt/random_search.py` `BootstrapFewShotWithRandomSearch.compile`; `dspy/__init__.py` `BootstrapRS` | 코드 확인 |
| `BootstrapFewShotWithOptuna`, `KNNFewShot`, `LabeledFewShot` | few-shot demos만 | Optuna로 demos 조합 탐색 / 입력과 가까운 학습 예시를 k-NN으로 골라 부트스트랩 / 라벨 예시 `k`개를 무작위(또는 앞에서) 선택(LM 호출 없음) | `KNNFewShot`은 `Embedder` 필요, `LabeledFewShot`은 metric 불필요 | `dspy/teleprompt/teleprompt_optuna.py`, `dspy/teleprompt/knn_fewshot.py`, `dspy/teleprompt/vanilla.py` `LabeledFewShot.compile` | 코드 확인(compile 시그니처·구조) |
| `BootstrapFinetune`, `GRPO`, `BetterTogether` | LM 가중치(파인튜닝/RL), BetterTogether는 둘의 순서 조합 | 프롬프트가 아니라 모델을 학습시킨다. 파인튜닝 가능한 제공자(`Provider.finetune`)가 필요하다. `GRPO`는 `dspy.teleprompt.grpo`로만 import 가능(최상위 `__all__`에 없음) | 이 목적(프롬프트 개선)과는 거리가 멀다 | `dspy/teleprompt/bootstrap_finetune.py` `BootstrapFinetune.compile`; `dspy/teleprompt/bettertogether.py` `BetterTogether.__init__`; `dspy/clients/provider.py` `Provider` | 코드 확인(구조만) |
| `Ensemble`, `ReAnchor`(실험) | 프로그램 합성 / 결정 출력의 임계값 | 지시문을 고치지 않는다 | — | `dspy/teleprompt/ensemble.py`; `dspy/teleprompt/reanchor/reanchor.py` | 코드 확인(docstring·compile) |

정리하면 **지시문 자체를 고치는 것**은 `GEPA`(지시문만), `COPRO`, `MIPROv2`(옵션으로 demos 동시), `SIMBA`·`InferRules`(지시문에 규칙을 덧붙임, demos 병행)이고, **few-shot 예시만 고르는 것**은 `LabeledFewShot`, `BootstrapFewShot`, `BootstrapFewShotWithRandomSearch`, `BootstrapFewShotWithOptuna`, `KNNFewShot`이다. 결과 프로그램은 `Module.save("x.json")`(상태만)·`dspy.load`로 저장·복원하며 상태에 지시문과 demos가 들어 있다(`dspy/primitives/base_module.py` `BaseModule.save`, `Predict.dump_state`; 코드 확인). 옵티마이저는 모델별로 다시 돌려야 한다고 보는 것이 안전하다(추론: 탐색에 쓰이는 LM 호출이 task 모델의 실제 출력에 의존함).

#### Q3. 한계: 비용·데이터 경로·라이선스

| 항목 | 내용 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|
| 평가 비용 | LM 호출 수 ≈ `len(devset)` × (프로그램 1회 실행의 호출 수) + LLM 심사 metric 호출. 프로그램 호출 수는 모듈이 정한다(`ChainOfThought`는 1회, `ReAct`는 `max_iters`까지, `RLM`은 `max_llm_calls` 등). 호출 수에 영향 주는 인자: `n`(생성 수), `num_retries`(기본 3, 일시 오류 재시도), `ChatAdapter(use_json_adapter_fallback=True)`의 파싱 실패 시 JSONAdapter 재호출, `Refine(N=)`·`BestOfN(N=)`, `Evaluate(num_threads=)`는 호출 수가 아니라 동시성(속도·레이트리밋) | `dspy/evaluate/evaluate.py` `Evaluate.__call__`; `dspy/clients/lm.py` `LM.__init__`; `dspy/adapters/chat_adapter.py` `ChatAdapter.__call__`; `dspy/predict/refine.py` `Refine.__init__`; `dspy/predict/rlm.py` `RLM.__init__` | 코드 확인 |
| 최적화 비용 | `MIPROv2`: `_estimate_lm_calls`가 "데이터 요약 10회 + 후보×predictor 수 + (predictor 수+1)" 프롬프트 모델 호출과 `minibatch_size×num_trials + len(valset)×full_eval_steps` 태스크 모델 호출을 계산해 로그에 찍는다(`auto`: light n=6/val 100, medium n=12/val 300, heavy n=18/val 1000). `GEPA`: `auto_budget`이 총 metric 호출 수를 계산하며 `max_metric_calls`로 직접 지정 가능, 이에 더해 `reflection_lm` 호출이 든다. `SIMBA`: 단계마다 `bsize × num_candidates`번 프로그램 실행, `max_steps`회. `BootstrapRS`: 후보 `num_candidate_programs`개마다 부트스트랩+valset 평가 | `dspy/teleprompt/mipro_optimizer_v2.py` `_estimate_lm_calls`; `dspy/teleprompt/gepa/gepa.py` `GEPA.auto_budget`; `dspy/teleprompt/simba.py` `SIMBA.compile`("`self.bsize * self.num_candidates`" 단언); `dspy/teleprompt/random_search.py` | 코드 확인(호출 수식) / 실제 비용은 미실행 |
| 비용 측정 | `dspy.track_usage()`/`settings.track_usage`로 토큰 집계, `Prediction.get_lm_usage()`, LM 히스토리 항목의 `cost`. 가격은 번들 가격표 스냅샷(+첫 사용 시 원격 갱신)에서 계산하며 모르는 모델·구독 로그인(`claude-code`, `openai-codex`)은 `None`(0이 아님)이다 | `dspy/utils/usage_tracker.py` `track_usage`; `dspy/clients/costs.py` `estimate_cost`; `dspy/clients/base_lm.py`(history `"cost"`) | 코드 확인 |
| 데이터가 나가는 곳 (기본 경로) | `dspy.LM` 호출 → `prepare`/`select_backend`가 엔진을 고른다. `engine="auto"`는 벤더링한 lm15로 제공자 API에 직접 HTTPS 전송(예: `https://api.openai.com/v1`, `https://api.anthropic.com/v1`, `https://generativelanguage.googleapis.com/v1beta`). 다음 경우 litellm으로 간다: `engine="litellm"`, `model_type="text"`, lm15가 모르는 클라이언트 설정(`api_version`, `headers` 등), `<PROVIDER>_API_BASE`/`_BASE_URL` 환경변수가 있을 때. `api_base`/`base_url`을 지정하면 그 주소로 간다. 프롬프트·입력은 이 경로로만 전송된다고 코드에서 확인되는 범위는 LM 호출 경로이며, 그 밖의 송신은 아래 행 | `dspy/clients/backend_selection.py` `select_backend`; `dspy/_vendor/lm15/providers/openai.py`·`anthropic.py`·`gemini.py`의 `_DEFAULT_BASE_URL`; `dspy/clients/engines/lm15_engine.py` | 코드 확인(경로·기본 URL) / 실제 전송은 미실행 |
| 데이터가 나가는 곳 (옵티마이저) | `MIPROv2`/`SIMBA`/`COPRO`는 `prompt_model`에, `GEPA`는 `reflection_lm`에 학습 예시·트레이스를 프롬프트로 보낸다. 제안용 모델과 평가 대상 모델을 다르게 둘 수 있다(`MIPROv2(prompt_model=, task_model=)`). `GEPA(use_wandb=True/use_mlflow=True)`는 로그를 외부 서비스로 보내는 옵션이다(기본 꺼짐, 전송 내용은 `gepa` 패키지 쪽이라 미탐색) | `dspy/teleprompt/mipro_optimizer_v2.py` `MIPROv2.__init__`; `dspy/teleprompt/gepa/gepa.py` `GEPA.__init__` | 코드 확인(인자) / 전송 내용 미확인 |
| LM 호출 외 네트워크·저장 | (1) 모델 메타데이터: 첫 사용 시 `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json`을 GET(타임아웃 5초). 실패하면 번들 스냅샷. `LITELLM_LOCAL_MODEL_COST_MAP=true`면 요청 안 함. 프롬프트는 포함되지 않는다. (2) litellm 사용 시 `litellm.telemetry = False`로 설정. (3) 응답 캐시: 메모리+디스크(`DSPY_CACHEDIR` 또는 `~/.dspy_cache`, 기본 한도 30GB `DSPY_CACHE_LIMIT`)에 모델 응답이 저장된다(`cache=False`로 끔). 디스크 직렬화는 기본이 제한 없는 pickle(`restrict_pickle=False`). (4) 구독 로그인 경로: `claude-code`는 `~/.claude/.credentials.json`, `openai-codex`는 `~/.codex/auth.json`의 로컬 로그인을 읽어 쓴다 | `dspy/clients/model_metadata/__init__.py` `_load`; `dspy/clients/_litellm.py` `_configure_litellm_defaults`; `dspy/utils/caching.py` `default_cache_dir`; `dspy/clients/cache.py` `Cache.__init__`; `dspy/_vendor/lm15/auth.py`(`CLAUDE_CODE_CREDENTIALS_PATH`, `CODEX_CLI_AUTH_PATH`); `dspy/_vendor/lm15/registry.py` | 코드 확인 / `dspy.LM`에 어떤 문자열을 넘겨야 `claude-code` 문을 쓰는지는 미확인 |
| 라이선스 | MIT. 사내·상업 사용 제약은 LICENSE 본문에 없음(1절). 하위 LICENSE 2개도 MIT | `LICENSE`, `dspy/_vendor/lm15-LICENSE`, `dspy/clients/model_metadata/LICENSE` | 코드 확인 |

### 기능 지도

나누는 기준은 디렉터리가 아니라 상태 소유자와 사용 목적이다. 같은 계약을 구현한 모듈류·어댑터·옵티마이저류는 한 행으로 묶고 고유 상태가 큰 `MIPROv2`·`GEPA`·`SIMBA`는 따로 뺐다. 선행은 재구현에 필요한 다른 행의 계약이다. 스펙은 아직 쓰지 않았으므로 상태는 모두 "미작성"이다.

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 전역 설정·문맥 | `dspy.configure(lm=, adapter=, …)`(소유 스레드만 재호출)와 `with dspy.context(...)`(스레드·async 태스크별 override). 설정 저장·로드는 cloudpickle(`save`/`load(allow_pickle)`) | `dspy/dsp/utils/settings.py` `Settings.configure`·`context`; `dspy/__init__.py`(`configure`, `context` 별칭) | 없음 | 핵심 | `capabilities/settings.md` · 미작성 | 코드 확인 |
| 시그니처 | `dspy.Signature` 클래스·문자열 `"a, b -> c"`, `InputField`/`OutputField`, 지시문=docstring, `with_instructions`/`append`/`delete` 등으로 변형한 새 클래스 반환. 상태 저장 `dump_state`/`load_state` | `dspy/signatures/signature.py` `Signature`, `SignatureMeta`, `ensure_signature`, `make_signature`; `dspy/signatures/field.py` | 없음 | 핵심 | `capabilities/signature.md` · 미작성 | 코드 확인(공개 메서드) / 문자열 파서(`_parse_type_node`) 세부 미탐색 |
| Predict·Module 실행 | `dspy.Predict(sig)(**inputs)`가 LM을 호출해 `Prediction`을 돌려준다. `Module.forward` 합성, `named_predictors`, `set_lm`, `batch`, 트레이스 기록(`settings.trace`). 위치 인자는 `ValueError` | `dspy/predict/predict.py` `Predict.forward`·`_forward_preprocess`; `dspy/primitives/module.py` `Module.__call__`·`set_lm`; `dspy/primitives/base_module.py` | 시그니처, 전역 설정, 어댑터 패밀리, LM 호출 | 핵심 | `capabilities/predict-module.md` · 미작성 | 코드 확인 |
| 추론·제어 모듈 패밀리 | `ChainOfThought`(reasoning 필드 추가), `MultiChainComparison`, `BestOfN`, `Refine`(reward_fn으로 N번 시도), `Parallel`, `KNN`, `majority` — 모두 `Predict`를 감싸는 `Module` | `dspy/predict/chain_of_thought.py`, `refine.py`, `best_of_n.py`, `parallel.py`, `multi_chain_comparison.py`, `knn.py`, `aggregation.py` | Predict·Module | 핵심 | `capabilities/reasoning-modules.md` · 미작성 | 코드 확인(클래스·생성자 인자) / 각 알고리즘 세부 미탐색 |
| 도구 사용 모듈과 도구 변환 | `ReAct`/`ReActV2`(도구 목록으로 반복 호출, `max_iters`), `Tool`, MCP 도구·LangChain 도구를 `Tool`로 변환 | `dspy/predict/react.py` `ReAct`; `dspy/predict/react_v2.py` `ReActV2`; `dspy/utils/mcp.py` `convert_mcp_tool`; `dspy/utils/langchain_tool.py` `convert_langchain_tool` | Predict·Module, 입출력 타입 패밀리 | 핵심 | `capabilities/tool-modules.md` · 미작성 | 코드 확인(진입점·생성자) / 루프 세부 미탐색 |
| 코드 실행 모듈·인터프리터 | `CodeAct`, `ProgramOfThought`, `RLM`(샌드박스 REPL에서 LLM이 코드를 써 긴 컨텍스트를 탐색, `max_llm_calls`)과 이를 돌리는 `PythonInterpreter`(Deno/Pyodide), `LocalInterpreter`(호스트 서브프로세스) | `dspy/predict/rlm.py` `RLM`; `dspy/predict/code_act.py`; `dspy/predict/program_of_thought.py`; `dspy/primitives/python_interpreter.py`; `dspy/primitives/local_interpreter.py` | Predict·Module | 핵심 | `capabilities/code-execution.md` · 미작성 | 코드 확인(진입점·생성자·모듈 docstring) / 샌드박스 격리 정도는 미확인 |
| 어댑터 패밀리 | `ChatAdapter`(기본, `[[ ## field ## ]]` 구분), `JSONAdapter`, `XMLAdapter`, `BAMLAdapter`, `TwoStepAdapter`가 signature·demos·입력 → messages, 응답 → 필드 값. `ChatAdapter`는 파싱 실패 시 `JSONAdapter`로 한 번 재시도 | `dspy/adapters/base.py` `Adapter.__call__`·`format`·`parse`; `dspy/adapters/chat_adapter.py`; `json_adapter.py`; `xml_adapter.py`; `baml_adapter.py`; `two_step_adapter.py` | 시그니처 | 핵심 | `capabilities/adapters.md` · 미작성 | 코드 확인(`__call__`·`ChatAdapter`) / 나머지 어댑터 `parse` 세부 미탐색 |
| 입출력 타입 패밀리 | `Image`, `Audio`, `File`, `History`, `Reasoning`, `Code`, `Tool`/`ToolCalls`, 실험 `Citations`·`Document`가 `Type` 계약(`BaseType`)으로 필드에 쓰임 | `dspy/adapters/types/base_type.py`; `dspy/adapters/types/*.py`; `dspy/__init__.py` | 어댑터 패밀리 | 핵심 | `capabilities/io-types.md` · 미작성 | 코드 확인(export·파일 목록) / 각 타입 직렬화 세부 미탐색 |
| LM 클라이언트 | `dspy.LM(model, model_type, temperature, max_tokens, cache, num_retries, engine, …)`, `BaseLM` 확장, `lm(prompt)`·`lm(messages=)` 호출, 엔진 선택(`auto`/`lm15`/`litellm`/사용자 엔진), 재시도·오류 계층 | `dspy/clients/lm.py` `LM`; `dspy/clients/base_lm.py` `BaseLM.__call__`; `dspy/clients/execution.py` `prepare`·`execute`; `dspy/clients/backend_selection.py` `select_backend`; `dspy/clients/engines/*.py`; `dspy/utils/exceptions.py` | 응답 캐시, 벤더링 lm15 전송 계층 | 핵심 | `capabilities/lm-client.md` · 미작성 | 코드 확인(생성자·엔진 선택) / `execution.py` 실행 본문은 일부만 읽음 |
| 응답 캐시 | 메모리(LRU)+디스크(diskcache) 2단 캐시, `configure_cache`, `rollout_id`로 캐시 우회, `DSPY_CACHEDIR`·`DSPY_CACHE_LIMIT` | `dspy/clients/cache.py` `Cache`, `request_cache`; `dspy/clients/__init__.py` `configure_cache`, `_get_dspy_cache`; `dspy/utils/caching.py` | 없음 | 핵심 | `capabilities/response-cache.md` · 미작성 | 코드 확인(키·계층) |
| 비용·사용량·히스토리·모델 메타데이터 | `dspy.track_usage()`, `lm.history`/`dspy.inspect_history`, 가격 추정(`estimate_cost`), 번들 `snapshot.json.gz`+원격 갱신 | `dspy/utils/usage_tracker.py`; `dspy/clients/costs.py`; `dspy/clients/model_metadata/__init__.py` `_load`; `dspy/utils/inspect_history.py` | LM 클라이언트 | 핵심 | `capabilities/usage-cost.md` · 미작성 | 코드 확인(원격 GET·추정 진입) / 가격 계산 세부 미탐색 |
| 벤더링 lm15 전송 계층 | 기본 엔진이 쓰는 제공자 HTTP 클라이언트·라우터·자격 증명(API 키 환경변수, `claude-code`·`openai-codex` 로그인 재사용)·`dspy.lm15.register_provider`. 외부 레포의 subtree이므로 직접 수정하지 않는다(`UPDATING.md`) | `dspy/lm15.py`; `dspy/_vendor/lm15/router.py`; `dspy/_vendor/lm15/registry.py`; `dspy/_vendor/lm15/auth.py`; `dspy/_vendor/lm15/providers/*.py` | 없음 | 핵심(경계만. 내부는 외부 레포) | `capabilities/vendored-lm15.md` · 미작성 | 코드 확인(라우팅 진입·기본 URL·자격 증명 경로) / 82개 파일 대부분 미탐색 |
| 임베딩·검색 | `Embedder`(호스팅 모델 또는 사용자 함수), `Embeddings`(FAISS/브루트포스 검색), `Retrieve`와 `DatabricksRM`·`WeaviateRM`, `ColBERTv2` | `dspy/clients/embedding.py` `Embedder`; `dspy/retrievers/embeddings.py` `Embeddings`; `dspy/retrievers/retrieve.py`; `dspy/dsp/colbertv2.py` | LM 클라이언트(`Embedder`는 litellm 경로) | 핵심 | `capabilities/embedding-retrieval.md` · 미작성 | 코드 확인(클래스 목록·docstring) / 검색 알고리즘 세부 미탐색 |
| 평가 실행 | `dspy.Evaluate(devset, metric, num_threads, max_errors, failure_score, save_as_csv/json, display_table)(program)` → `EvaluationResult(score, results)` | `dspy/evaluate/evaluate.py` `Evaluate.__call__`; `dspy/utils/parallelizer.py` `ParallelExecutor` | Predict·Module, 전역 설정 | 핵심 | `capabilities/evaluate.md` · 미작성 | 코드 확인 |
| 메트릭 패밀리 | 문자열 매칭(`EM`, `answer_exact_match`, `answer_passage_match`, `normalize_text`)과 LLM 심사 모듈(`SemanticF1`, `CompleteAndGrounded`) | `dspy/evaluate/metrics.py`; `dspy/evaluate/auto_evaluation.py` | Predict·Module(LLM 심사만) | 핵심 | `capabilities/metrics.md` · 미작성 | 코드 확인(함수·클래스 시그니처) / F1 계산 세부 미탐색 |
| 데이터 로딩·내장 데이터셋 | `DataLoader.from_csv/json/parquet/pandas/huggingface`, `train_test_split`, 내장 `HotPotQA`·`GSM8K`·`MATH`·`Colors`·`alfworld` | `dspy/datasets/dataloader.py` `DataLoader`; `dspy/datasets/dataset.py`; `dspy/datasets/*.py` | 공유 계약 `Example` | 핵심 | `capabilities/datasets.md` · 미작성 | 코드 확인(메서드 목록) / 로딩 세부 미탐색 |
| few-shot 선택 옵티마이저 패밀리 | `LabeledFewShot`, `BootstrapFewShot`, `BootstrapFewShotWithRandomSearch`(`BootstrapRS`), `BootstrapFewShotWithOptuna`, `KNNFewShot`: demos만 바꿈. `compile(student, trainset=, teacher=)` | `dspy/teleprompt/vanilla.py`; `bootstrap.py`; `random_search.py`; `teleprompt_optuna.py`; `knn_fewshot.py` | Predict·Module, 평가 실행, 공유 계약 Teleprompter | 핵심 | `capabilities/fewshot-optimizers.md` · 미작성 | 코드 확인(`BootstrapFewShot`·`LabeledFewShot`·`RandomSearch` 시그니처) / Optuna·KNN 본문 미탐색 |
| MIPROv2 | 지시문 후보(`GroundedProposer`)와 demos 후보를 Optuna로 탐색. `prompt_model`/`task_model` 분리, `auto` 예산 | `dspy/teleprompt/mipro_optimizer_v2.py` `MIPROv2.compile`; `dspy/propose/grounded_proposer.py`; `dspy/teleprompt/utils.py` | few-shot 선택 패밀리(부트스트랩), 평가 실행 | 핵심 | `capabilities/miprov2.md` · 미작성 | 코드 확인(`compile` 흐름·예산식) / 제안기 프롬프트 본문 미탐색 |
| GEPA | 반사(reflection) 기반 지시문 진화. 외부 패키지 `gepa` 의존, 텍스트 피드백 metric, `InstructionProposer(skills=…)`, 병합·파레토 선택, `log_dir` 체크포인트 | `dspy/teleprompt/gepa/gepa.py` `GEPA.compile`; `gepa_utils.py` `DspyAdapter`; `instruction_proposal.py` `InstructionProposer` | 평가 실행, 공유 계약 Teleprompter | 핵심 | `capabilities/gepa.md` · 미작성 | 코드 확인(DSPy 쪽 인자·시드 후보·예산) / `gepa` 패키지 내부와 `DspyAdapter.make_reflective_dataset` 세부 미탐색 |
| SIMBA | 어려운 예시에서 규칙·demo를 덧붙이는 확률적 미니배치 상승 | `dspy/teleprompt/simba.py` `SIMBA.compile`; `simba_utils.py` | 평가 실행 | 핵심 | `capabilities/simba.md` · 미작성 | 코드 확인(생성자·루프 구조·`append_a_rule`) / 후보 선택 세부 미탐색 |
| 그 밖의 지시문·합성 옵티마이저 | `COPRO`(지시문 좌표 상승), `InferRules`(규칙 유도), `AvatarOptimizer`(Avatar actor 지시문), `Ensemble`(프로그램 앙상블) | `dspy/teleprompt/copro_optimizer.py`; `infer_rules.py`; `avatar_optimizer.py`; `ensemble.py` | 평가 실행(+ `BootstrapFewShot` 상속은 `InferRules`) | 핵심 | `capabilities/misc-optimizers.md` · 미작성 | 코드 확인(생성자·지시문 갱신 위치) / 후보 생성 프롬프트 미탐색 |
| 가중치 학습 옵티마이저 패밀리 | `BootstrapFinetune`, `GRPO`, `BetterTogether`와 학습 제공자(`Provider`, `OpenAIProvider`, `DatabricksProvider`, `LocalProvider`) | `dspy/teleprompt/bootstrap_finetune.py`; `grpo.py`; `bettertogether.py`; `dspy/clients/provider.py`; `openai.py`; `databricks.py`; `lm_local.py`; `utils_finetune.py` | LM 클라이언트, 평가 실행 | 핵심 | `capabilities/weight-optimizers.md` · 미작성 | 코드 확인(compile·Provider 계약) / 학습 작업 세부 미탐색 |
| 프로그램 저장·불러오기 | `Module.save(path)`(`.json`/`.pkl` 상태 또는 `save_program=True` 디렉터리), `dspy.load`, `load_state`. 피클은 `allow_pickle=True`일 때만, LM 상태의 `api_base` 등은 기본적으로 무시 | `dspy/primitives/base_module.py` `BaseModule.save`·`load`; `dspy/utils/saving.py` `load`; `dspy/predict/predict.py` `_sanitize_lm_state` | Predict·Module | 핵심 | `capabilities/save-load.md` · 미작성 | 코드 확인 |
| 스트리밍·비동기·병렬·콜백 | `streamify`/`StreamListener`, `asyncify`/`syncify`, `ParallelExecutor`, `BaseCallback`, 로깅 켜고 끄기 | `dspy/streaming/streamify.py`; `dspy/utils/asyncify.py`; `dspy/utils/parallelizer.py`; `dspy/utils/callback.py`; `dspy/utils/logging_utils.py` | 전역 설정 | 핵심 | `capabilities/streaming-async.md` · 미작성 | 코드 확인(공개 함수·`ParallelExecutor` 컨텍스트 복사) / 스트림 조립 세부 미탐색 |
| 실험 기능 | `dspy.Flex`(최적화 가능한 코드 모듈, GEPA가 `module_src`를 다시 씀), 결정 출력 타입 `Choice`·`Noul`·`Score`, `ReAnchor`(임계값 보정), 외부 `typesafe` 제공자 | `dspy/experimental/__init__.py`; `dspy/predict/flex/flex.py` `Flex`; `dspy/teleprompt/reanchor/reanchor.py` `ReAnchor`; `dspy/adapters/decision.py` | Predict·Module, GEPA(Flex) | 부속(`@experimental`, 기본 사용 경로 밖) | `capabilities/experimental.md` · 미작성 | 코드 확인(export·docstring) / 내부 동작 미탐색 |
| 문서 사이트 | `docs/`의 MkDocs 사이트: 가이드·API·튜토리얼, API 문서 자동 생성·버전 게시 스크립트, Vercel 설정 | `docs/mkdocs.yml`; `docs/scripts/generate_api_docs.py`; `docs/scripts/build_docs.py`; `docs/README.md` | 없음 | 부속 | `capabilities/docs-site.md` · 미작성 | 코드 확인(README·스크립트 머리) / 튜토리얼 72개·API 문서 87개 본문 미탐색 |
| 릴리스·벤더 갱신 도구 | `scripts/update_vendored_lm15.py`(git subtree로 lm15 갱신), `scripts/update_model_metadata.py`(LiteLLM 가격표 스냅샷 갱신), `dspy-ai` 호환 패키지, 릴리스 체크리스트 | `scripts/update_vendored_lm15.py`; `scripts/update_model_metadata.py`; `.github/.internal_dspyai/pyproject.toml` | 없음 | 부속 | `capabilities/release-tooling.md` · 미작성 | 코드 확인(머리 주석·매니페스트) / 스크립트 본문 미탐색 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| `Example`(입력/라벨 분리, `with_inputs`)·`Prediction`(+`Completions`) 값 객체 | 평가 실행, 모든 옵티마이저, 데이터 로딩, Predict·Module | `dspy/primitives/example.py` `Example`; `dspy/primitives/prediction.py` `Prediction.from_completions` | `capabilities/example-prediction.md` · 미작성 | 코드 확인 |
| `Teleprompter.compile(student, trainset, …) -> Module` 계약과 `dspy.Module`의 predictor 열거(`named_predictors`, `reset_copy`, `deepcopy`) | 옵티마이저 전부 | `dspy/teleprompt/teleprompt.py` `Teleprompter`; `dspy/primitives/base_module.py` | `capabilities/teleprompter-contract.md` · 미작성 | 코드 확인 |
| metric 호출 계약: `(example, pred[, trace])` → 숫자·불리언·`Prediction(score=…)`, GEPA만 5인자 | 평가 실행, 옵티마이저 전부, 메트릭 패밀리 | `dspy/evaluate/evaluate.py`; `dspy/teleprompt/bootstrap.py`; `dspy/teleprompt/simba_utils.py` `wrap_program`; `dspy/teleprompt/gepa/gepa.py` | `capabilities/metric-contract.md` · 미작성 | 코드 확인 |
| LM 호출 계약: `BaseLM.__call__(prompt=None, messages=None, **kwargs)`와 엔진의 `complete(Request) -> Response` | Predict, 어댑터, 임베딩 외 LM을 쓰는 모든 기능, 사용자 정의 엔진 | `dspy/clients/base_lm.py` `BaseLM.__call__`; `dspy/clients/engines/base.py`; `dspy/lm15.py` | `capabilities/lm-client.md` | 코드 확인(시그니처) |
| 문맥 override 전파(`settings.context` + `ParallelExecutor`가 override 복사) | 평가 실행, 옵티마이저, `Parallel`, `asyncify` | `dspy/dsp/utils/settings.py`; `dspy/utils/parallelizer.py` | `capabilities/settings.md` | 코드 확인 |

**대조한 범위와 미탐색 영역**
- 대조: `README.md` 전체(설치·논문 목록 외 기능 목록 없음), `dspy/__init__.py`의 공개 export, `dspy/predict/__init__.py`·`dspy/teleprompt/__init__.py`·`dspy/evaluate/__init__.py`·`dspy/primitives/__init__.py`·`dspy/clients/__init__.py`·`dspy/experimental/__init__.py`의 `__all__`, `pyproject.toml`(의존성·extras·패키지 데이터), `docs/docs/learn/optimization/optimizers.md`(옵티마이저 분류), `docs/docs/api/` 파일 목록, 위 표의 `파일:심볼` 구간. 연 이유: `pyproject.toml`·`.github/.internal_dspyai/pyproject.toml`은 배포 입구·의존성을 정하고, `dspy/clients/model_metadata/__init__.py`는 외부 요청 여부를 정하므로 열었다.
- 문서와 구현의 차이: ① `dspy.Avatar`/`AvatarOptimizer`: `AvatarOptimizer`는 `dspy.teleprompt` export에 있으나(`dspy/teleprompt/__init__.py`) 문서 `docs/docs/api/optimizers/` 목록에는 없고, `dspy/predict/avatar`는 `dspy/predict/__init__.py` export에 없다. ② `GRPO`는 `dspy/teleprompt/grpo.py`에 있으나 `dspy.teleprompt.__all__`에는 없고 문서 API 목록에도 없다. ③ `dspy.GEPA`는 `gepa` 패키지가 없으면(Python 3.15 이상 기본 설치 제외) 호출 시 `ImportError`를 내는 대체 클래스다(`dspy/teleprompt/__init__.py`). ④ `litellm`은 `pyproject.toml` 기본 의존성(Python < 3.15)에 포함되나 코드 주석은 번들 lm15 엔진이 litellm 없이 LM 호출을 처리한다고 쓴다(`pyproject.toml` 의존성 주석). ⑤ `LM` docstring은 OpenAI 스타일 `messages=` 딕셔너리가 DSPy 3.5에서 제거될 예정이라고 쓴다(`dspy/clients/lm.py` `LM`).
- 미탐색: `tests/`(기본 제외 규칙), `.github/` 워크플로·이슈 템플릿(제외 규칙), `docs/docs/`의 튜토리얼 72개·API 문서·`static/`(문서 본문, 목적 질문과 무관), `dspy/_vendor/lm15/` 82개 파일 중 `router.py`·`registry.py`·`auth.py`·`providers`의 기본 URL 행 외 전부, `dspy/teleprompt/gepa/`의 `gepa_utils.make_reflective_dataset`·`gepa_flex_utils.py`, 외부 패키지 `gepa`·`litellm`·`optuna`의 코드(레포 밖), `dspy/primitives/python_interpreter.py`·`local_interpreter*.py`·`runner.js` 본문, `dspy/adapters/` 중 JSON·XML·BAML·TwoStep 본문, `dspy/clients/engines/`·`provider.py`·`databricks.py`·`lm_local.py` 본문, `dspy/datasets/` 본문, `dspy/retrievers/` 본문, `dspy/dsp/colbertv2.py`, `dspy/predict/flex/` 본문, `dspy/streaming/` 본문, `dspy/predict/retry.py`와 `dspy/predict/avatar/`(레거시로 보이나 확인 안 함), `dspy/propose/` 제안기 프롬프트 본문, `scripts/` 본문, `uv.lock`.
- 실행: 설치·실행 금지 조건이므로 하지 않았다. 따라서 이 문서의 "동작" 서술은 모두 코드 읽기 기준이다.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 프로그램 경로, 평가·최적화 경로, LM 호출·전송 경로 |

구조도 검증 결과(세 가지를 구분한다).
- **산출물 검증**(`archify deliver … --quality showcase --repo-root repos/dspy`): 통과. 아티팩트 검사 9/9, 구성 오류 0·경고 0, 소스 증거(`meta.repository` url·revision, 컴포넌트 `sources` 11개)를 로컬 clone으로 검증함. 마지막 전달 시 사양 sha256 `cd37504e…cc682c91`, HTML sha256 `68e6e706…46dcd24`(720,607바이트). 이는 결정적 산출물 검사이며 브라우저 확인이 아니다.
- **브라우저 확인**(`archify visual-check`): 통과(자동 Chrome, 상태 `pass`). 1440×900과 1600×1000에서 `scrollWidth/Height`가 창 크기 이내(overflow 없음), 노드 최소 글자 투영 크기 7.6px로 기준 6px 이상 등. 2048×1320도 측정·캡처되었다. 이 검사는 시각적 완성도를 보증하지 않는다.
- **시각 검토**: 1440×900 라이트 스크린샷 한 장을 이미지로 직접 보고 확인했다(노드 겹침·라벨 가림 없음, 한글 라벨 표시 정상, 간선 교차 없음). 다크 테마와 다른 해상도의 스크린샷은 눈으로 검토하지 않았다. 검토 후 `visual-check`가 만든 스크린샷·sidecar는 폴더 정리를 위해 삭제했다.
- 한국어가 주 언어이므로 `meta.locale`을 생략했다. 뷰어 고정 UI(Light/Dark, Present 등)와 `<html lang>`은 영어로 대체된다(archify 규칙).

### 그림 해설
그림을 열지 않고 이 글만 읽어도 구조와 흐름이 이해되도록 쓴다. 그림의 12개 노드 중 `gepa 패키지`, `litellm`, `LLM 제공자 API`는 레포 밖이다.

**읽는 순서**
1. 아래 가운데 행(`Predict · Module → Adapter → dspy.LM → lm15 엔진 → LLM 제공자 API`): 프롬프트 한 번이 나가는 경로. 진입은 `dspy/predict/predict.py` `Predict.forward`.
2. 위 행(`Example 데이터 → 옵티마이저 → Evaluate → Predict · Module`): 평가와 개선이 같은 프로그램 경로를 반복 호출하는 방식. 진입은 `dspy/evaluate/evaluate.py` `Evaluate.__call__`과 `dspy/teleprompt/teleprompt.py` `Teleprompter.compile`.
3. 아래 행(`settings`, `응답 캐시`, `litellm`): 전역 기본값, 캐시, 호환 엔진.

**구조도: 모듈별 역할**
| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| Predict · Module | 입력 검증·경고, LM·어댑터 결정(`self.lm or settings.lm`, `settings.adapter or ChatAdapter()`), 결과를 `Prediction`으로 묶고 트레이스에 기록 | 입력: 키워드 인자·`config`·`lm`. 출력: `Prediction`. 어댑터를 호출 | `dspy/predict/predict.py` `Predict._forward_preprocess`·`forward`·`_forward_postprocess` | 코드 확인 |
| settings | 전역 기본값(`lm`, `adapter`, `num_threads=8`, `max_errors=10` 등)과 스레드·태스크별 override | `Predict`와 `Evaluate`가 읽음. `configure`는 소유 스레드만 | `dspy/dsp/utils/settings.py` `DEFAULT_CONFIG`, `Settings.configure`·`context` | 코드 확인 |
| Adapter | signature·demos·입력으로 messages(시스템: 필드 설명·구조·"your objective is" 지시문, demos: user/assistant 쌍, 마지막 user: 입력)를 만들고 응답을 필드로 파싱 | `lm(messages=…, **lm_kwargs)` 호출, 반환 값에서 출력 필드 dict 생성 | `dspy/adapters/base.py` `Adapter.__call__`·`format`; `dspy/adapters/chat_adapter.py` | 코드 확인 |
| dspy.LM | 요청을 준비하고(`prepare`) 엔진을 고르고(`select_backend`) 캐시 조회·재시도·히스토리·사용량 기록 | 입력: messages·kwargs. 출력: 응답 텍스트 목록. 캐시와 엔진을 호출 | `dspy/clients/lm.py` `LM`; `dspy/clients/execution.py` `prepare`·`execute`; `dspy/clients/backend_selection.py` | 코드 확인(생성자·선택 규칙) / `execute` 본문은 일부만 읽음 |
| 응답 캐시 | 요청 해시를 키로 메모리·디스크에 응답 보관 | `LM`이 조회·저장 | `dspy/clients/cache.py` `Cache.get`·`put`·`cache_key` | 코드 확인 |
| lm15 엔진 | 기본 엔진. 모델 문자열을 제공자로 풀어 직접 HTTPS 호출 | `Request` → `Response` | `dspy/clients/engines/lm15_engine.py` `LM15Engine`; `dspy/_vendor/lm15/router.py` | 코드 확인(경계) / 내부 미탐색 |
| litellm | 호환 엔진(`engine="litellm"` 또는 lm15가 처리 못 하는 설정). 선택 의존성이 아니라 기본 의존성(Python < 3.15) | `Request` → litellm 호출 → 제공자 | `dspy/clients/engines/litellm_engine.py`; `dspy/clients/_litellm.py` | 코드 확인(경계) |
| LLM 제공자 API | 레포 밖. 프롬프트가 도착하는 곳 | HTTPS | `dspy/_vendor/lm15/providers/*.py` `_DEFAULT_BASE_URL` | 코드 확인(주소 상수) / 서버 동작은 미확인 |
| Evaluate | devset을 `ParallelExecutor`로 병렬 실행, metric 점수 집계 | 입력: program·devset·metric. 출력: `EvaluationResult` | `dspy/evaluate/evaluate.py` `Evaluate.__call__` | 코드 확인 |
| 옵티마이저 | 프로그램 복사본에서 지시문·demos 후보를 만들고 `Evaluate`와 LM(제안용 포함)을 반복 호출해 고름 | 입력: student·trainset·metric. 출력: 개선된 프로그램 | `dspy/teleprompt/mipro_optimizer_v2.py` `MIPROv2.compile`(`Evaluate(...)` 생성); `dspy/teleprompt/bootstrap.py`; `simba.py` | 코드 확인(MIPROv2·Bootstrap·SIMBA) |
| gepa 패키지 | 레포 밖의 진화 탐색 엔진. DSPy는 `DspyAdapter`로 평가·트레이스·지시문 제안을 연결 | `gepa.optimize(seed_candidate, trainset, valset, adapter, …)` → `GEPAResult` | `dspy/teleprompt/gepa/gepa.py` `GEPA.compile`; `gepa_utils.py` `DspyAdapter.evaluate` | 코드 확인(호출부) / 패키지 내부 미탐색 |
| Example 데이터 | 입력/라벨을 구분한 학습·평가 데이터 | `inputs()`는 프로그램 입력으로, 나머지는 metric에 | `dspy/primitives/example.py` `Example.with_inputs`; `dspy/datasets/dataloader.py` | 코드 확인 |

**실행 흐름은 그리지 않았다**(구조도 한 장만 요구됨). 대신 평가 한 번의 호출 순서를 글로 적는다.
1. `Evaluate.__call__(program)` — 입력 `devset`, `metric`, `num_threads` → `ParallelExecutor`가 스레드에 부모 `settings` override를 복사해 실행(`dspy/utils/parallelizer.py`).
2. 각 예시 `process_item` — `program(**example.inputs())` → `Predict.forward`가 어댑터로 messages를 만들고 `LM`을 호출 → `Prediction`(`dspy/evaluate/evaluate.py`, `dspy/predict/predict.py`).
3. `metric(example, prediction)` 점수 → 실패 예시는 `failure_score` → `EvaluationResult(score=round(100*ncorrect/ntotal, 2), results=…)`(`dspy/evaluate/evaluate.py`).

**미확인 영역**
- 그림에 넣지 않은 것: 어댑터·모듈 패밀리의 개별 구현, 도구·코드 실행 모듈, 임베딩·검색, 스트리밍, 파인튜닝 제공자, 실험 기능, 문서 사이트, 릴리스 도구(지도 표에는 있음).
- 코드로 확인하지 못한 것: `execute`가 캐시·재시도·엔진 호출 순서를 어떻게 잇는지의 세부(일부만 읽음), 벤더링 lm15 내부, `gepa` 패키지 내부, 제공자 서버의 동작, 실제 실행 결과 전부.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **스펙 범위 승인 필요**: 지도의 어느 행을 스펙으로 쓸지 사용자 승인이 필요하다. `부속` 3행(실험 기능, 문서 사이트, 릴리스·벤더 갱신 도구)은 각각 따로 물어야 한다. 이 목적(스킬·프롬프트 평가·개선)에는 `평가 실행`, `메트릭 패밀리`, `Predict·Module 실행`, `시그니처`, `LM 클라이언트`, `전역 설정·문맥`, `MIPROv2`, `GEPA`, `SIMBA`, `few-shot 선택 옵티마이저 패밀리`, `프로그램 저장·불러오기`가 직접 관련된다(추론).
- **먼저 확인하면 좋은 미탐색**: `gepa` 패키지 내부(GEPA의 피드백 사용 방식), `DspyAdapter.make_reflective_dataset`, `dspy.LM`에 `claude-code` 로그인 경로를 쓰는 모델 문자열 형식, 실제 실행 시 비용(소규모 devset으로 `Evaluate`·`MIPROv2 auto="light"` 호출 수 측정).
- **다음 세션 계획**: `next.md`는 아직 없음(승인 후 작성).
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸.
