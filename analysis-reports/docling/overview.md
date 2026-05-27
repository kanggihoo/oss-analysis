# Docling 문서 중심 사용자 관점 분석

분석 범위: `README.md`, `docs/**/*.md`, `mkdocs.yml`, `pyproject.toml`, `packages/*/README.md`, `packages/docling/pyproject.toml`

제외 범위: 실제 구현 소스(`docling/**/*.py`)와 테스트 코드는 사용자의 요청에 따라 분석하지 않았다. API 이름, CLI 이름, 옵션 이름은 문서와 패키지 메타데이터에 드러난 내용만 근거로 정리했다.

## 1. 이 프로젝트의 목적

Docling은 PDF, Office 문서, HTML, Markdown, 이미지, 오디오/비디오 등 다양한 입력을 하나의 구조화 표현인 `DoclingDocument`로 변환하고, 이를 Markdown, HTML, JSON, Text, DocTags, WebVTT 등으로 내보내는 Python SDK와 CLI 프로젝트다.

문서 관점에서 Docling의 핵심 목적은 "AI 애플리케이션이 바로 소비할 수 있는 문서 표현을 만드는 것"에 가깝다. 단순히 새 문서를 생성하는 모듈이라기보다는, 기존 파일/URL/바이너리 스트림을 읽어 레이아웃, 읽기 순서, 표 구조, 이미지, 코드, 수식, OCR 결과, 오디오 전사 등을 구조화하고, RAG/검색/요약/에이전트 도구에 넣기 좋은 형태로 변환하는 도구다.

근거 문서:

- `docling/README.md`
- `docling/docs/index.md`
- `docling/docs/usage/supported_formats.md`
- `docling/docs/concepts/docling_document.md`
- `docling/packages/docling/pyproject.toml`

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 혼합형이다.

- Python SDK: `DocumentConverter`를 사용해 파일 경로, URL, `DocumentStream` 등을 변환한다.
- CLI 도구: `docling` 명령으로 문서를 변환하고, `docling-tools`로 모델 다운로드 같은 보조 작업을 수행한다.
- 문서 처리 프레임워크: 포맷별 backend, pipeline, pipeline options를 조합해 변환 방식을 바꾼다.
- AI/RAG 생태계 도구: LangChain, LlamaIndex, Haystack, CrewAI 등과 연동한다.
- 에이전트 도구: MCP 서버, agent skill 예제, Jobkit 기반 분산 처리 문서가 제공된다.

가장 기본적인 사용 흐름은 다음과 같다.

```python
from docling.document_converter import DocumentConverter

source = "https://arxiv.org/pdf/2408.09869"
converter = DocumentConverter()
result = converter.convert(source)
print(result.document.export_to_markdown())
```

CLI에서는 다음처럼 쓴다.

```bash
docling https://arxiv.org/pdf/2206.01062
docling myfile.pdf --to json --to md --no-ocr
docling ./input/dir --from pdf --from docx --to md --to json --output ./scratch
```

근거 문서:

- `docling/docs/getting_started/quickstart.md`
- `docling/docs/v2.md`
- `docling/docs/usage/index.md`
- `docling/docs/reference/cli.md`

## 3. 핵심 기능

핵심 기능은 다음과 같다.

- 다중 포맷 입력 파싱: PDF, DOCX, XLSX, PPTX, HTML/XHTML, Markdown, AsciiDoc, LaTeX, CSV, 이미지, 오디오, 비디오, WebVTT, USPTO XML, JATS XML, XBRL XML, Docling JSON.
- 고급 PDF 이해: 페이지 레이아웃, 읽기 순서, 표 구조, 코드 블록, 수식, 이미지 분류 등을 처리한다.
- 통합 문서 모델: 변환 결과를 `DoclingDocument`라는 Pydantic 기반 표현으로 제공한다.
- 내보내기: Markdown, HTML, JSON, Text, DocTags, WebVTT를 지원한다.
- OCR: EasyOCR, Tesseract, Tesseract CLI, OcrMac, RapidOCR, OnnxTR 등 여러 OCR 엔진을 선택할 수 있다.
- VLM 파이프라인: GraniteDocling, SmolDocling 등 vision-language model을 사용해 페이지 이미지를 구조화 출력으로 변환한다.
- Enrichment: 코드 이해, 수식 이해, 그림 분류, 그림 설명 생성 기능을 옵션으로 켤 수 있다.
- 청킹: `HybridChunker`, `LineBasedTokenChunker`, `HierarchicalChunker`로 RAG용 chunk를 만든다.
- 품질 신호: `ConversionResult.confidence`에 변환 품질 grade/score를 제공한다.
- 오디오/비디오 전사: ASR extra를 통해 Whisper Turbo 기반으로 오디오/비디오를 `DoclingDocument`로 변환한다.
- 로컬/오프라인 실행: 모델을 미리 받아 air-gapped 환경에서 사용할 수 있다.
- 원격 모델 사용: 기본은 로컬 실행이지만, 명시적으로 `enable_remote_services=True`를 켜면 원격 OCR/VLM/API 서비스를 사용할 수 있다.
- 플러그인: pluggy와 setuptools entry point 기반으로 OCR 엔진 같은 기능을 확장할 수 있다.

근거 문서:

- `docling/docs/usage/supported_formats.md`
- `docling/docs/usage/enrichments.md`
- `docling/docs/usage/vision_models.md`
- `docling/docs/usage/model_catalog.md`
- `docling/docs/concepts/chunking.md`
- `docling/docs/concepts/confidence_scores.md`
- `docling/docs/concepts/plugins.md`

## 4. 실행/사용 진입점

사용자 관점의 주요 진입점은 네 가지다.

1. `pip install docling`
   - 일반 사용자는 `docling` 패키지가 권장된다.
   - Python 3.10 이상이 필요하다.

2. `docling` CLI
   - 기본 변환 명령이다.
   - `--from`, `--to`, `--output`, `--no-ocr`, `--no-tables`, `--pipeline vlm`, `--vlm-model`, `--enable-remote-services`, `--artifacts-path` 같은 옵션을 문서에서 예시로 제시한다.

3. Python API `DocumentConverter`
   - 단일 입력은 `convert()`, 여러 입력은 `convert_all()`을 사용한다.
   - 포맷별 옵션은 `format_options={InputFormat.PDF: PdfFormatOption(...)}` 형태로 전달한다.

4. AI 프레임워크/서비스 연동
   - LangChain은 `DoclingLoader`를 통해 문서 로드와 chunking을 감싼다.
   - LlamaIndex는 `Docling Reader`와 `Docling Node Parser`를 제공한다.
   - Haystack은 converter 형태로 제공된다.
   - MCP는 `docling-mcp-server`를 `uvx --from=docling-mcp`로 실행하는 설정 예시가 있다.
   - Jobkit은 local/Ray/Kubeflow 기반 batch job 실행을 제공한다.

근거 문서:

- `docling/docs/getting_started/installation.md`
- `docling/docs/getting_started/quickstart.md`
- `docling/docs/usage/mcp.md`
- `docling/docs/usage/jobkit.md`
- `docling/docs/integrations/langchain.md`
- `docling/docs/integrations/llamaindex.md`
- `docling/docs/integrations/haystack.md`

## 5. 주요 모듈과 책임

문서에 드러난 개념 기준의 주요 모듈/책임은 다음과 같다.

- `DocumentConverter`: 입력 포맷을 감지하거나 지정된 포맷 옵션을 바탕으로 변환을 실행하는 사용자 API의 중심.
- Format option 계열: PDF, Word, Audio 등 포맷별 pipeline/backend/options를 지정하는 설정 단위.
- Backend: 포맷별 원문 파싱을 담당한다. 문서에서는 PDF backend를 바꿀 수 있다고 설명한다.
- Pipeline: 변환 과정을 orchestration한다. 표준 PDF pipeline, VLM pipeline, ASR pipeline이 문서에서 명시된다.
- `ConversionResult`: 변환 결과 컨테이너. `document`와 `confidence`가 사용자에게 중요하다.
- `DoclingDocument`: 변환된 문서의 표준 표현. `texts`, `tables`, `pictures`, `key_value_items`, `body`, `furniture`, `groups` 같은 구조를 가진다.
- Serializer: `DoclingDocument`를 Markdown, HTML, DocTags 등 텍스트 표현으로 바꾼다.
- Chunker: `DoclingDocument`를 RAG/embedding에 적합한 chunk stream으로 바꾼다.
- Enrichment model: 코드/수식/이미지 등 특정 요소에 추가 의미 정보를 붙인다.
- Plugin factory: 외부 OCR 엔진 등 기능을 등록한다.

근거 문서:

- `docling/docs/concepts/architecture.md`
- `docling/docs/concepts/docling_document.md`
- `docling/docs/concepts/serialization.md`
- `docling/docs/concepts/chunking.md`
- `docling/docs/concepts/plugins.md`

## 6. 핵심 개념과 용어

- `DoclingDocument`: Docling의 표준 문서 모델. 텍스트, 표, 그림, 키-값, 본문/헤더/푸터 구조, provenance, layout bounding box를 담을 수 있다.
- `InputFormat`: PDF, DOCX, HTML, AUDIO 같은 입력 포맷 식별자.
- `Pipeline`: 문서 변환을 실제로 구성하는 처리 흐름. 표준 PDF, VLM, ASR 등으로 나뉜다.
- `Backend`: 특정 포맷을 읽고 파싱하는 컴포넌트.
- `DocTags`: 문서 이해에 최적화된 구조화 markup 형식으로 설명된다.
- `Serializer`: 문서를 Markdown/HTML/DocTags 등으로 내보내는 전략.
- `Chunker`: AI 검색/RAG를 위해 문서를 작은 단위로 나누는 전략.
- `HybridChunker`: 계층 구조 기반 chunking 위에 tokenizer-aware split/merge를 적용한다.
- `ConfidenceReport`: 변환 품질을 page-level/document-level score와 grade로 표현한다.
- `Enrichment`: 기본 변환 후 코드, 수식, 그림 등에 추가 분석 결과를 붙이는 단계.
- `VLM pipeline`: 페이지를 이미지로 보고 vision-language model이 구조화 출력으로 변환하는 pipeline.
- `enable_remote_services`: 사용자 데이터가 외부 서비스로 나갈 수 있는 기능을 명시적으로 허용하는 옵션.

근거 문서:

- `docling/docs/concepts/docling_document.md`
- `docling/docs/concepts/serialization.md`
- `docling/docs/concepts/chunking.md`
- `docling/docs/concepts/confidence_scores.md`
- `docling/docs/usage/advanced_options.md`
- `docling/docs/usage/vision_models.md`

## 7. 입력/데이터/상태/제어 흐름

문서 기반으로 보면 일반적인 흐름은 다음과 같다.

1. 사용자가 파일 경로, URL, 디렉터리, 바이너리 스트림, 또는 포맷별 입력을 제공한다.
2. `DocumentConverter`가 입력 포맷에 맞는 backend와 pipeline을 선택한다.
3. pipeline이 OCR, layout detection, table structure recognition, VLM conversion, ASR transcription, enrichment 같은 단계를 실행한다.
4. 결과는 `ConversionResult`로 반환된다.
5. 사용자는 `result.document`에서 `DoclingDocument`를 얻는다.
6. `DoclingDocument`를 Markdown/HTML/JSON/DocTags/Text/WebVTT로 export하거나, serializer/chunker로 후처리한다.
7. RAG/검색/요약/에이전트/벡터 DB 등 downstream workflow에 넣는다.

문서가 제시하는 사용 패턴은 "원문 -> 구조화 문서 -> export/chunk/integrate"다. 특히 RAG 사용자는 Markdown으로 한번 내보낸 뒤 직접 chunking할 수도 있고, `DoclingDocument` 위에서 native chunker를 사용할 수도 있다.

근거 문서:

- `docling/docs/concepts/architecture.md`
- `docling/docs/getting_started/quickstart.md`
- `docling/docs/concepts/chunking.md`
- `docling/docs/usage/processing_audio_media.md`

## 8. 설정 및 환경 구성

설치와 환경 구성에서 중요한 포인트는 다음과 같다.

- Python: `packages/docling/pyproject.toml` 기준 `>=3.10,<4.0`.
- 일반 설치: `pip install docling`.
- 선택 설치:
  - `docling[asr]`: 오디오/비디오 ASR.
  - `docling[vlm]`: VLM inline processing.
  - `docling[easyocr]`, `docling[tesserocr]`, `docling[ocrmac]`, `docling[rapidocr]`: OCR 엔진별 extra.
  - `docling[htmlrender]`: HTML rendering.
  - `docling[xbrl]`: XBRL.
- 경량 설치: `docling-slim`은 필요한 extra만 선택해 설치하는 패키지다. 일반 사용자는 `docling`이 권장된다.
- 모델 아티팩트:
  - 기본은 첫 사용 시 자동 다운로드.
  - 오프라인 환경은 `docling-tools models download`로 미리 받고, `--artifacts-path` 또는 `DOCLING_ARTIFACTS_PATH`로 경로를 지정한다.
- 원격 서비스:
  - 사용자 데이터가 외부로 나가는 기능은 `enable_remote_services=True`가 필요하다.
  - 설정하지 않으면 `OperationNotAllowed()`가 발생한다고 문서에 명시되어 있다.
- GPU:
  - `AcceleratorOptions(device=AcceleratorDevice.CUDA)` 또는 `AUTO`를 사용할 수 있다.
  - batch/concurrency 설정은 표준 pipeline과 VLM pipeline에서 별도로 다룬다.
- 시스템 의존성:
  - Tesseract OCR은 시스템 패키지와 `TESSDATA_PREFIX` 설정이 필요할 수 있다.
  - 일부 audio/video 포맷과 video 처리는 `ffmpeg`가 필요하다.

근거 문서:

- `docling/docs/getting_started/installation.md`
- `docling/docs/usage/advanced_options.md`
- `docling/docs/usage/gpu.md`
- `docling/docs/usage/processing_audio_media.md`
- `docling/packages/docling/pyproject.toml`
- `docling/packages/docling-slim/README.md`

## 9. 의존성 구조

문서와 패키지 메타데이터 기준으로 Docling은 두 패키지 레이어로 나뉜다.

- `docling`: 사용자용 meta-package. `docling-slim[standard]==2.95.0`에 의존한다.
- `docling-slim`: 실제 `docling` Python 모듈과 CLI entry point를 제공하는 경량/모듈형 패키지다.

`docling-slim`의 base dependency는 상대적으로 작게 유지되고, 기능은 extra로 분리된다.

- base: `pydantic`, `docling-core`, `pydantic-settings`, `filetype`, `requests`, `certifi`, `pluggy`, `tqdm`.
- format extras: PDF, Office, HTML/Markdown, LaTeX, XBRL, audio, HTML render.
- OCR extras: RapidOCR, EasyOCR, Tesseract/tesserocr, OcrMac, ONNXRuntime.
- model extras: local PyTorch/docling-ibm-models, remote Triton client, VLM inline, ONNXRuntime.
- feature extras: chunking, service client, CLI.

사용자 입장에서는 기본적으로 `pip install docling`을 쓰고, 설치 크기나 배포 제약이 크면 `docling-slim[...]`로 필요한 기능만 선택하는 구조다.

근거 문서:

- `docling/pyproject.toml`
- `docling/packages/docling/pyproject.toml`
- `docling/packages/docling-slim/README.md`

## 10. 빌드/실행/테스트 방식

사용자 실행 방식:

- CLI 단일 변환: `docling FILE_OR_URL`
- CLI batch 변환: `docling ./input/dir --from pdf --to md --to json --output ./scratch`
- VLM CLI: `docling --pipeline vlm --vlm-model granite_docling FILE`
- 모델 다운로드: `docling-tools models download`
- Jobkit local 실행: `uv run docling-jobkit-local [configuration-file-path]`
- MCP 서버: MCP client 설정에 `uvx --from=docling-mcp docling-mcp-server` 등록

개발 환경:

- 문서상 개발 설치는 `uv sync --all-extras`.
- `pyproject.toml`에는 docs, examples, dev, typecheck 등 dependency group이 있다.
- 테스트 코드는 이번 요청 범위에서 확인하지 않았다.

근거 문서:

- `docling/docs/getting_started/quickstart.md`
- `docling/docs/v2.md`
- `docling/docs/usage/advanced_options.md`
- `docling/docs/usage/jobkit.md`
- `docling/docs/usage/mcp.md`
- `docling/docs/getting_started/installation.md`
- `docling/pyproject.toml`

## 11. 에러 처리와 디버깅 포인트

문서에서 사용자가 자주 만날 수 있는 문제는 다음과 같다.

- 원격 서비스 차단: `enable_remote_services=True` 없이 원격 OCR/VLM/API를 쓰면 `OperationNotAllowed()`가 발생한다.
- 오프라인 실행: 모델 아티팩트 경로를 지정해야 한다. `docling-tools models download`, `--artifacts-path`, `DOCLING_ARTIFACTS_PATH`가 핵심이다.
- 모델 다운로드 SSL 오류: `certifi` 업데이트, `pip-system-certs`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE` 설정이 FAQ에 제시된다.
- macOS Intel: 최신 PyTorch wheel 문제로 `docling[mac_intel]` 또는 호환 PyTorch/NumPy 조합이 필요하다.
- headless Linux/OpenCV: `libGL.so.1` 오류는 `opencv-python-headless` 사용 또는 `libgl1`/`mesa-libGL` 설치가 해결책으로 제시된다.
- OCR 언어: OCR 엔진별 지원 언어가 다르며, `pipeline_options.ocr_options.lang`로 지정한다.
- WMF 이미지: Word/PowerPoint의 WMF 이미지는 Windows 외 OS에서 누락될 수 있다.
- `HybridChunker` tokenizer 경고: 길이 경고가 나와도 실제 chunk는 split될 수 있으므로 최종 chunk 길이를 확인하라고 FAQ가 설명한다.
- GPU/VLM 성능: standard pipeline과 VLM pipeline의 batch/concurrency 설정이 다르고, VLM은 local inference server(vLLM/LM Studio/Ollama)를 권장한다.
- 품질 판단: `ConversionResult.confidence`의 `mean_grade`, `low_grade`를 보고 manual review나 pipeline 변경 여부를 판단할 수 있다.

근거 문서:

- `docling/docs/usage/advanced_options.md`
- `docling/docs/faq/index.md`
- `docling/docs/concepts/confidence_scores.md`
- `docling/docs/usage/gpu.md`

## 12. 확장하거나 기여할 때 봐야 할 구조

문서만 기준으로 보면 확장 포인트는 다음이다.

- OCR plugin: `docling` entry point에 plugin module을 등록하고, `ocr_engines()`가 OCR 엔진 목록을 반환하는 구조다.
- External plugin 사용: `allow_external_plugins=True` 또는 CLI `--allow-external-plugins`가 필요하다.
- Enrichment model 개발: picture enrichment, formula understanding, `DoclingDocument` enrichment 예제가 문서 내 examples로 연결된다.
- Serializer 확장: `BaseDocSerializer`, `BaseTextSerializer`, `BaseTableSerializer`, `BaseSerializerProvider` 계층이 문서에 설명된다.
- Chunker 확장: `BaseChunker.chunk()`와 `BaseChunker.contextualize()` 인터페이스가 문서에 설명된다.
- AI framework integration: LangChain, LlamaIndex, Haystack 같은 별도 extension 패키지와 연동된다.
- Agent skill: `docs/examples/agent_skill/docling-document-intelligence/`는 assistant가 Docling CLI를 써서 변환/평가/개선 루프를 수행하는 예시 bundle이다.

근거 문서:

- `docling/docs/concepts/plugins.md`
- `docling/docs/concepts/serialization.md`
- `docling/docs/concepts/chunking.md`
- `docling/docs/usage/enrichments.md`
- `docling/docs/examples/agent_skill/docling-document-intelligence/README.md`

## 13. 처음 기여자가 먼저 읽어야 할 파일

실사용자 이해 목적이라면 다음 순서가 가장 효율적이다.

1. `docling/README.md`
   - 프로젝트 목적, 빠른 설치, CLI/Python 기본 사용법을 파악한다.

2. `docling/docs/getting_started/quickstart.md`
   - 가장 짧은 Python/CLI 사용 흐름을 확인한다.

3. `docling/docs/usage/supported_formats.md`
   - 어떤 입력/출력을 지원하는지 확인한다.

4. `docling/docs/concepts/architecture.md`
   - converter, backend, pipeline, result, document, serializer, chunker 흐름을 잡는다.

5. `docling/docs/concepts/docling_document.md`
   - 변환 결과의 데이터 모델을 이해한다.

6. `docling/docs/usage/advanced_options.md`
   - 오프라인, 원격 서비스, table extraction, 파일 크기/page 제한 등 실전 옵션을 본다.

7. `docling/docs/concepts/chunking.md`
   - RAG용 chunking 전략을 이해한다.

8. `docling/docs/usage/vision_models.md`와 `docling/docs/usage/model_catalog.md`
   - VLM pipeline과 모델 선택 기준을 본다.

9. `docling/docs/integrations/index.md`
   - LangChain/LlamaIndex/Haystack/CrewAI 등 연결 지점을 확인한다.

10. `docling/packages/docling-slim/README.md`
    - 설치 크기와 optional extra 설계를 이해한다.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- 실제 CLI 옵션 전체 표는 `reference/cli.md`가 `mkdocs-click` directive만 담고 있어, 렌더링된 문서나 실제 `docling --help` 실행 없이 전체 옵션 목록을 문서 원문만으로 확인하기 어렵다.
- 구조화 정보 추출(beta)은 README/examples index에 언급되지만, 자세한 설명은 notebook 예제(`extraction.ipynb`) 쪽에 있어 이번 Markdown 중심 범위에서는 세부 API를 확정하지 않았다.
- 문서에 "latest additions는 codebase를 확인하라"는 식의 모델 catalog note가 있어, 실제 최신 모델 preset 전체 목록은 소스 확인 없이는 확정하지 않았다.
- `docling.service_client`는 examples README에서 experimental이라고 되어 있으며, 실제 API 안정성은 추가 확인이 필요하다.
- 실제 품질, 속도, 모델 호환성은 문서상 예시와 하드웨어 조건에 의존한다. 운영 도입 전에는 대상 문서 샘플로 pipeline별 결과를 비교해야 한다.
