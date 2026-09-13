# 배포 및 인프라

<details>
<summary>관련 소스 파일</summary>

이 위키 페이지를 생성하는 데 다음 파일들이 컨텍스트로 사용되었습니다:

- [docker/china/Dockerfile](docker/china/Dockerfile)
- [docker/compose.yaml](docker/compose.yaml)
- [docker/global/Dockerfile](docker/global/Dockerfile)
- [docs/en/quick_start/docker_deployment.md](docs/en/quick_start/docker_deployment.md)
- [docs/zh/quick_start/docker_deployment.md](docs/zh/quick_start/docker_deployment.md)

</details>



이 페이지는 MinerU의 배포 전략 및 인프라 지원에 대한 고수준의 개요를 제공합니다. 컨테이너화, 다양한 플랫폼에서의 하드웨어 가속, 다중 GPU 또는 엔터프라이즈 환경으로의 스케일링을 다룹니다.

## 배포 개요

MinerU는 로컬 CPU 전용 컴퓨터에서 고성능 GPU 클러스터에 이르기까지 다양한 환경에서 이식 가능하도록 설계되었습니다. 이 시스템은 추론 가속화를 위해 `vLLM` 및 `lmdeploy`를 활용하며, 다양한 사용 사례에 맞는 여러 진입점을 제공합니다 [docs/zh/quick_start/docker_deployment.md:18-25]().

### 시스템 진입점 및 인프라
다음 다이어그램은 다양한 배포 모드(CLI, API, Web)가 기본 하드웨어 및 추론 엔진과 상호작용하는 방식을 보여줍니다.

**인프라 디스패치 다이어그램**
```mermaid
graph TD
    subgraph "Interface_Layer"
        ["mineru_CLI"] --> ["Execution_Layer"]
        ["mineru-api_FastAPI"] --> ["Execution_Layer"]
        ["mineru-gradio"] --> ["Execution_Layer"]
        ["mineru-openai-server"] --> ["Execution_Layer"]
        ["mineru-router"] --> ["mineru-api_FastAPI"]
    end

    subgraph "Execution_Layer"
        ["Inference_Engines"]
        ["Pipeline_Backend"]
        ["vlm-http-client"]
    end

    subgraph "Hardware_Layer"
        ["Inference_Engines"] --> ["NVIDIA_CUDA"]
        ["Inference_Engines"] --> ["Apple_MPS"]
        ["Inference_Engines"] --> ["Huawei_Ascend_NPU"]
        ["Inference_Engines"] --> ["Domestic_Accelerators"]
        
        ["Domestic_Accelerators"] --> ["Cambricon_MLU"]
        ["Domestic_Accelerators"] --> ["METAX_MACA"]
        ["Domestic_Accelerators"] --> ["T-Head_PPU"]
        ["Domestic_Accelerators"] --> ["Iluvatar_COREX"]
    end

    ["Pipeline_Backend"] --> ["NVIDIA_CUDA"]
    ["vlm-http-client"] --> ["mineru-openai-server"]
```
출처: [docs/zh/quick_start/docker_deployment.md:18-25](), [docker/compose.yaml:60-93](), [docs/en/quick_start/docker_deployment.md:58-67]()

---

## Docker 배포

MinerU는 의존성 관리를 단순화하기 위해 전문화된 Docker 환경을 제공하며, 특히 `vLLM`과 같은 복잡한 추론 프레임워크에 유용합니다 [docs/en/quick_start/docker_deployment.md:3-14]().

- **지역별 이미지**: 글로벌 및 중국 지역 사용자를 위한 별도의 Dockerfile이 존재합니다. 중국 지역 버전은 모델 다운로드를 위해 `DaoCloud` 미러 및 `ModelScope`를 사용합니다 [docker/china/Dockerfile:5-24](). 글로벌 버전은 기본적으로 HuggingFace를 사용합니다 [docker/global/Dockerfile:5-24]().
- **베이스 이미지**: 지역별 Dockerfile은 호환되는 NVIDIA 하드웨어에서 `vLLM` 가속을 지원하기 위해 `vllm/vllm-openai:v0.21.0` (또는 CUDA 12.9의 경우 `v0.21.0-cu129`)을 베이스 이미지로 활용합니다 [docker/global/Dockerfile:5-6](), [docker/china/Dockerfile:5-6]().
- **오케스트레이션**: `compose.yaml` 파일은 `openai-server`, `api`, `router` 및 `gradio`를 위한 프로필을 지원합니다 [docker/compose.yaml:1-123](). 여기에는 헬스 체크와 `nvidia` 드라이버 및 `gpu` 기능을 사용한 NVIDIA GPU 자원 예약이 포함됩니다 [docker/compose.yaml:20-28]().
- **컨테이너 생명주기**: 공식 Dockerfile의 `ENTRYPOINT`는 실행 중에 컨테이너가 미리 다운로드된 모델을 사용하도록 `MINERU_MODEL_SOURCE=local`로 설정합니다 [docker/global/Dockerfile:27-27](), [docker/china/Dockerfile:27-27]().

컨테이너 빌드 및 실행에 대한 자세한 내용은 [Docker Deployment](#5.1)를 참조하십시오.

출처: [docker/global/Dockerfile:1-27](), [docker/china/Dockerfile:1-27](), [docs/en/quick_start/docker_deployment.md:5-50](), [docker/compose.yaml:1-123]()

---

## 하드웨어 가속

MinerU는 다양한 하드웨어 가속기를 지원합니다. 시스템은 런타임에 사용 가능한 하드웨어를 감지하여 성능을 최적화하며, 종종 `vLLM`과 `lmdeploy` 백엔드 중 선택할 수 있도록 지원합니다.

- **NVIDIA GPU**: CUDA를 통해 지원됩니다. `vLLM` 가속을 위해서는 8GB+ VRAM을 갖춘 Volta 아키텍처 이상이 필요합니다 [docs/en/quick_start/docker_deployment.md:18-25](). 사용자는 `compose.yaml` 내의 `--gpu-memory-utilization` 플래그를 통해 VRAM 사용량을 조정할 수 있습니다 [docker/compose.yaml:12-15]().
- **Apple Silicon**: macOS를 위한 MPS 및 MLX 가속이 기본적으로 지원되지만, macOS에서의 Docker 배포는 이러한 하드웨어 기능에 액세스할 수 없으므로 권장되지 않습니다 [docs/en/quick_start/docker_deployment.md:5-7]().
- **중국 국산 가속기**: METAX (MACA), T-Head (PPU) 등을 포함한 중국 국산 하드웨어에 대한 광범위한 지원을 제공합니다. 이들은 일반적으로 `docker run` 시 특정 베이스 이미지 및 디바이스 매핑이 필요합니다 [docs/en/quick_start/docker_deployment.md:30-36]().
- **경량 클라이언트 모드**: 고성능 GPU가 없는 기기의 경우, 경량 `mineru` 클라이언트가 `vlm-http-client` 백엔드를 사용하여 원격 OpenAI 호환 서버에 연결할 수 있습니다 [docs/en/quick_start/docker_deployment.md:58-67]().

장치 감지 및 특정 하드웨어 구성에 대한 자세한 내용은 [Hardware Acceleration](#5.2)을 참조하십시오.

출처: [docs/en/quick_start/docker_deployment.md:5-25](), [docs/en/quick_start/docker_deployment.md:58-67](), [docker/compose.yaml:12-15]()

---

## 다중 GPU 및 엔터프라이즈 배포

높은 처리량이 요구되는 경우, MinerU는 여러 GPU로 확장하거나 엔터프라이즈 작업 대기열로 통합할 수 있습니다.

- **서비스 라우팅**: `mineru-router` 서비스는 `--upstream-url` 플래그를 사용하여 서로 다른 GPU의 여러 `mineru-api` 인스턴스를 집계하거나, `--local-gpus auto`를 통해 로컬 워커를 관리할 수 있습니다 [docker/compose.yaml:60-83]().
- **VRAM 관리**: `--gpu-memory-utilization`과 같은 매개변수를 통해 KV 캐시 크기(예: `0.5` 이하로 설정)를 튜닝하여 `vLLM` 환경에서 OOM(Out-Of-Memory) 오류를 예방할 수 있습니다 [docker/compose.yaml:15-15]().
- **장치 격리**: `compose.yaml` 자원 예약에서 `device_ids`를 수정하여 특정 GPU를 대상으로 배포할 수 있습니다 [docker/compose.yaml:27-27](), [docker/compose.yaml:57-57]().

**다중 가속기 배포 로직**
```mermaid
graph LR
    subgraph "Configuration_Layer"
        ["MINERU_MODEL_SOURCE"] --> ["mineru-router"]
        ["gpu-memory-utilization"] --> ["mineru-api"]
    end

    subgraph "Routing_Layer"
        ["mineru-router"]
    end

    subgraph "Service_Instances"
        ["mineru-router"] --> ["mineru-api_Instance_0"]
        ["mineru-router"] --> ["mineru-api_Instance_1"]
    end

    subgraph "Hardware_Cluster"
        ["mineru-api_Instance_0"] --> ["Accelerator_Device_0"]
        ["mineru-api_Instance_1"] --> ["Accelerator_Device_1"]
    end
```
출처: [docker/compose.yaml:60-93](), [docker/compose.yaml:15-15](), [docker/compose.yaml:10-10]()

확장 및 엔터프라이즈 통합에 대한 자세한 내용은 [Multi-GPU & Enterprise Deployments](#5.3)를 참조하십시오.
