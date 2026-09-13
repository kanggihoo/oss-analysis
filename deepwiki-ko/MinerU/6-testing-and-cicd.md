# 테스트 및 CI/CD

<details>
<summary>관련 소스 파일</summary>

이 위키 페이지를 생성하는 데 컨텍스트로 사용된 파일은 다음과 같습니다:

- [.github/workflows/cla.yml](.github/workflows/cla.yml)
- [.github/workflows/cli.yml](.github/workflows/cli.yml)
- [.github/workflows/mkdocs.yml](.github/workflows/mkdocs.yml)
- [.github/workflows/python-package.yml](.github/workflows/python-package.yml)
- [tests/clean_coverage.py](tests/clean_coverage.py)
- [update_version.py](update_version.py)

</details>



이 페이지는 MinerU 프로젝트의 테스트 전략 및 지속적 통합/지속적 배포(CI/CD) 파이프라인에 대한 고수준 개요를 제공합니다. 코드베이스는 유닛 테스트부터 엔드투엔드(E2E) CLI 검증에 이르기까지 다층적인 테스트 접근 방식을 채택하고 있으며, 이 모든 과정은 GitHub Actions를 통해 오케스트레이션됩니다.

## 테스트 전략 개요

MinerU의 테스트 인프라는 다양한 백엔드 및 하드웨어 구성에서 문서 파싱의 신뢰성을 보장하도록 설계되었습니다. 테스트 스위트에는 기존의 유닛 테스트, CLI 및 SDK에 대한 통합 테스트, 모델 성능과 추출 정확도를 평가하기 위한 특화된 벤치마크 스크립트가 포함되어 있습니다. 

테스트 전략은 원시 PDF 바이트에서 최종 `middle_json` 및 Markdown 출력에 이르는 흐름을 검증합니다. CI 환경은 `[test]` 추가 패키지(extra)의 빠른 의존성 설치를 위해 `uv`를 사용하며 [[.github/workflows/cli.yml:28-36]()], Python 3.12 환경에서 테스트를 실행합니다 [[.github/workflows/cli.yml:34]()]. 자동화된 커버리지 보고가 워크플로우에 통합되어 있어, `clean_coverage.py`를 사용하여 환경을 준비하고 `get_coverage.py`를 사용하여 결과를 집계합니다 [[.github/workflows/cli.yml:37-39](), [tests/clean_coverage.py:24-27]().

다음 다이어그램은 테스트 도구와 핵심 코드베이스 엔티티 간의 관계를 보여줍니다.

**테스트 엔티티 맵**
```mermaid
graph TD
    subgraph "Testing_Tools"
        T1["test_unit.py"]
        T2["test_e2e.py"]
        T3["benchmark.py"]
        T4["get_coverage.py"]
        T5["clean_coverage.py"]
    end

    subgraph "Core_Codebase"
        C1["mineru_CLI"]
        C2["middle_json"]
        C3["pipeline_doc_analyze_streaming"]
        C4["union_make"]
        C5["FileBasedDataWriter"]
    end

    T2 -->| "calls" | C3
    T2 -->| "converts_output_via" | C4
    T2 -->| "validates" | C2
    T2 -->| "writes_results" | C5
    T4 -->| "measures" | C3
    T5 -->| "deletes" | H["htmlcov/"]
```
Sources: [.github/workflows/cli.yml:37-39](), [tests/clean_coverage.py:8-25]()

테스트 파일(`test_table.py` 및 `test_metascan_classify.py` 포함), CLI 통합 테스트(`test_cli_sdk.py`), 벤치마크 점수 계산(`calculate_score.py`), 그리고 커버리지 보고에 대한 자세한 분석은 **[테스트 스위트](#6.1)**를 참조하세요.

## CI/CD 파이프라인

MinerU는 GitHub Actions를 활용하여 테스트, 문서 배포, 릴리스 프로세스를 자동화합니다. 네 가지 주요 워크플로우가 있습니다:

1.  **CLI 테스트 워크플로우**: `master` 및 `dev` 브랜치로의 푸시에 의해 트리거됩니다 [[.github/workflows/cli.yml:5-9]()]. 신속한 의존성 관리를 위해 `uv`를 사용하며 [[.github/workflows/cli.yml:28-29]()], `coverage run`을 통해 커버리지 보고와 함께 테스트 스위트를 실행합니다 [[.github/workflows/cli.yml:38-39]().
2.  **문서 워크플로우**: 메인 브랜치에 변경 사항이 푸시될 때마다 MkDocs 기반 문서를 GitHub Pages에 자동으로 배포합니다 [[.github/workflows/mkdocs.yml:1-7]()]. 배포 수명 주기를 관리하기 위해 `mkdocs-deploy-gh-pages`를 사용합니다 [[.github/workflows/mkdocs.yml:17-22]().
3.  **릴리스 워크플로우**: 특정 릴리스 태그(예: `*released`)에 의해 트리거되는 복잡한 파이프라인입니다 [[.github/workflows/python-package.yml:7-9]()]. 버전 동기화, 여러 버전에 걸친 설치 확인(Python 3.10 ~ 3.13), PyPI 배포를 처리합니다 [[.github/workflows/python-package.yml:57-63](), [.github/workflows/python-package.yml:140-144]().
4.  **CLA 어시스턴트(CLA Assistant)**: `CLAAssistant` 작업을 통해 풀 리퀘스트에 대한 기여자 라이선스 동의서(Contributor License Agreement)를 관리합니다 [[.github/workflows/cla.yml:15-16]()]. 코드가 병합되기 전에 기여자가 `MinerU_CLA.md`에 서명했는지 확인하고 [[.github/workflows/cla.yml:29]()], 서명 내역을 `signatures/version1/cla.json`에 기록합니다 [[.github/workflows/cla.yml:28]().

### 릴리스 및 버전 관리 수명 주기

릴리스 프로세스는 `update_version.py`에 의해 제어되며, 이 스크립트는 `get_version()` 함수를 통해 `git describe --tags`를 사용하여 Git 태그에서 버전 정보를 추출하고 [[update_version.py:6-17]()], `write_version_to_commons()`를 사용하여 내부 `mineru/version.py` 파일을 업데이트합니다 [[update_version.py:20-23]()]. 이를 통해 CLI, API, PyPI 패키지 간에 `__version__` 문자열이 일관되게 유지되도록 보장합니다. `build` 작업은 wheel 파일을 생성한 다음, 이를 배포하기 전에 GitHub 아티팩트로 업로드합니다 [[.github/workflows/python-package.yml:108-117]().

**릴리스 파이프라인 흐름**
```mermaid
graph LR
    Tag["Git_Tag_(*released)"] --> UV["update_version.py"]
    UV --> CI["check-install_Job"]
    CI --> Build["build_Job_(wheel)"]
    Build --> Release["GitHub_Release"]
    Release --> PyPI["twine_upload"]

    subgraph "Code_Entities"
        UV_File["mineru/version.py"]
        Dist["dist/*.whl"]
        V_Func["get_version()"]
        V_Write["write_version_to_commons()"]
    end

    UV -.->| "calls" | V_Func
    UV -.->| "calls" | V_Write
    V_Write -.->| "updates" | UV_File
    Build -.->| "generates" | Dist
```
Sources: [.github/workflows/python-package.yml:15-144](), [update_version.py:6-28]()

릴리스 작업, `twine`을 통한 PyPI 배포, 자동 버전 관리 로직에 대한 자세한 내용은 **[릴리스 파이프라인 및 버전 관리](#6.2)**를 참조하세요.

## CI 구성 요소 요약 표

| 구성 요소 | 파일 / 도구 | 목적 |
| :--- | :--- | :--- |
| **의존성 관리자** | `uv` | `.[test]` 및 `.[core]` 추가 패키지의 빠른 설치 [[.github/workflows/cli.yml:28-36]()]. |
| **커버리지** | `coverage.py` | 테스트 실행 경로 측정; `clean_coverage.py`를 통해 관리 [[.github/workflows/cli.yml:38-39](), [tests/clean_coverage.py:24-25](). |
| **버전 관리** | `update_version.py` | `get_version()`을 통해 Git 태그와 `mineru/version.py`를 동기화 [[update_version.py:6-17](). |
| **배포 (Publishing)** | `twine` | `PYPI_TOKEN`을 사용하여 PyPI에 wheel 파일을 검증하고 업로드 [[.github/workflows/python-package.yml:142-144](). |
| **문서** | `mkdocs` | `mkdocs-deploy-gh-pages`를 통해 GitHub Pages에 기술 문서 빌드 및 배포 [[.github/workflows/mkdocs.yml:17-22](). |
| **호환성** | `check-install` | Python 3.10, 3.11, 3.12, 3.13 환경에서 설치 여부 검증 [[.github/workflows/python-package.yml:57-63](). |
| **법적 사항/CLA** | `cla.yml` | `signatures/version1/cla.json`에서 기여자 서명 추적 [[.github/workflows/cla.yml:28](). |

Sources: [.github/workflows/cli.yml:28-39](), [.github/workflows/python-package.yml:57-145](), [update_version.py:6-28](), [tests/clean_coverage.py:8-25](), [.github/workflows/cla.yml:1-32]()
