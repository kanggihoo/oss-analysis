---
sha: "538eb3a757db94826cb90c4297279e50c5dd0f83"
created: 2026-11-18
updated: 2026-11-18
sources:
  - rea_video/speech.py
  - rea_video/speakers.py
  - rea_video/stems.py
  - rea_video/effects.py
  - rea_video/util.py
  - pyproject.toml
  - docs/cli.md
---

# [Q4] 8번(음성 인식·화자 분리)에 API 키나 GPU가 필요한가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 정적 읽기. 실행·다운로드·속도 측정은 하지 않았다.

## 1. 결론

**둘 다 필요 없다. 로컬 CPU에서 돈다.** 다만 선택 설치와 **첫 실행 시 모델 다운로드**가 필요하다.

| 항목 | 내용 | 근거 | 검증 수준 |
|---|---|---|---|
| 음성 인식 | `sherpa-onnx`의 **SenseVoice**(중·영·일·한·광둥어) + 음성 구간 검출(VAD). 클라우드 API 호출 없음. 모델은 sherpa-onnx GitHub release에서 내려받는다(약 160MB) | `speech.py` docstring, `BASE_URL`, `MODEL_DIR`, `OfflineRecognizer.from_sense_voice` | 코드 확인 |
| 화자 분리 | `sherpa-onnx`의 pyannote 분할 모델 + 3D-Speaker 임베딩(약 35MB). 한 명뿐이거나 모델이 없으면 건너뜀 | `speakers.py` `diarize`, `SEG_URL`, `EMB_URL`, `available()` | 코드 확인 |
| 소리 분리(7번 행, 인식의 앞단) | onnxruntime 세션을 `CPUExecutionProvider`로 고정해 만든다. UVR MDX-Net(약 67MB), BandIt v2(약 149MB) | `stems.py` 70·75행, `effects.py` 97행 | 코드 확인 |
| GPU | `grep`으로 `cuda`·`coreml` 등 GPU provider 지정이 없음을 확인했다. GPU를 쓰는 코드 경로가 없다 | `rea_video/*.py` grep | 코드 확인(부재) |
| 스레드 수 | 기기에서 자동 결정(애플 칩은 성능 코어 수, 그 외는 물리 코어 수, 최대 8). `REA_VIDEO_THREADS`로 지정 | `util.py` `model_threads`, `docs/cli.md` | 코드 확인 |
| 필수 의존 | 기본 설치에 `onnxruntime`은 포함. 음성 인식·화자 분리는 `pip install "rea-video[asr]"`(`sherpa-onnx>=1.12`)를 따로 설치해야 하고, 없으면 해당 기능이 조용히 꺼진다(`speakers.available()`가 `not_installed` 반환) | `pyproject.toml` `[project.optional-dependencies]`, `speakers.py` | 코드 확인 |

## 2. 주의

- 인식 결과는 **기계 전사본**이다. 화면 자막과 VLM 전사가 있으면 그쪽이 우선이다(`speech.py` docstring).
- 인식은 가능하면 분리한 **인성 트랙**에 돌린다. 배경음 위에서 돌리면 말을 지어낸다(같은 docstring).
- SenseVoice는 벵골어를 못 들어 `--asr-lang bn`으로 다른 모델(Vosk zipformer, 약 90MB)로 바꾼다.
- 속도: `docs/cli.md`는 BandIt 분리가 오디오 길이의 1.5배라고 적는다(문서 수치, 미측정).
- 오프라인 환경이면 첫 실행의 모델 다운로드가 실패한다(`util.fetch`가 GitHub release에서 받음).
