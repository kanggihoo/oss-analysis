# Deployment & Infrastructure

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docker/china/Dockerfile](docker/china/Dockerfile)
- [docker/compose.yaml](docker/compose.yaml)
- [docker/global/Dockerfile](docker/global/Dockerfile)
- [docs/en/quick_start/docker_deployment.md](docs/en/quick_start/docker_deployment.md)
- [docs/zh/quick_start/docker_deployment.md](docs/zh/quick_start/docker_deployment.md)

</details>



This page provides a high-level overview of the deployment strategies and infrastructure support for MinerU. It covers containerization, hardware acceleration across diverse platforms, and scaling to multi-GPU or enterprise environments.

## Deployment Overview

MinerU is designed to be portable across different environments, ranging from local CPU-only machines to high-performance GPU clusters. The system leverages `vLLM` and `lmdeploy` for inference acceleration and provides several entry points for different use cases [docs/zh/quick_start/docker_deployment.md:18-25]().

### System Entry Points and Infrastructure
The following diagram illustrates how different deployment modes (CLI, API, Web) interact with the underlying hardware and inference engines.

**Infrastructure Dispatch Diagram**
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
Sources: [docs/zh/quick_start/docker_deployment.md:18-25](), [docker/compose.yaml:60-93](), [docs/en/quick_start/docker_deployment.md:58-67]()

---

## Docker Deployment

MinerU provides specialized Docker environments to simplify dependency management, especially for complex inference frameworks like `vLLM` [docs/en/quick_start/docker_deployment.md:3-14]().

- **Regional Images**: Separate Dockerfiles exist for global and China-region users. The China-region version uses `DaoCloud` mirrors and `ModelScope` for model downloads [docker/china/Dockerfile:5-24](). The global version defaults to HuggingFace [docker/global/Dockerfile:5-24]().
- **Base Images**: Regional Dockerfiles utilize `vllm/vllm-openai:v0.21.0` (or `v0.21.0-cu129` for CUDA 12.9) as the base image to provide support for `vLLM` acceleration on compatible NVIDIA hardware [docker/global/Dockerfile:5-6](), [docker/china/Dockerfile:5-6]().
- **Orchestration**: A `compose.yaml` file supports profiles for `openai-server`, `api`, `router`, and `gradio` [docker/compose.yaml:1-123](). It includes health checks and resource reservations for NVIDIA GPUs using the `nvidia` driver and `gpu` capabilities [docker/compose.yaml:20-28]().
- **Container Lifecycle**: The `ENTRYPOINT` in official Dockerfiles sets `MINERU_MODEL_SOURCE=local` to ensure the container uses pre-downloaded models during execution [docker/global/Dockerfile:27-27](), [docker/china/Dockerfile:27-27]().

For details on building and running containers, see [Docker Deployment](#5.1).

Sources: [docker/global/Dockerfile:1-27](), [docker/china/Dockerfile:1-27](), [docs/en/quick_start/docker_deployment.md:5-50](), [docker/compose.yaml:1-123]()

---

## Hardware Acceleration

MinerU supports a wide array of hardware accelerators. The system detects available hardware at runtime to optimize performance, often allowing a choice between `vLLM` and `lmdeploy` backends.

- **NVIDIA GPUs**: Supported via CUDA. Requires Volta architecture or later with 8GB+ VRAM for `vLLM` acceleration [docs/en/quick_start/docker_deployment.md:18-25](). Users can tune VRAM usage via the `--gpu-memory-utilization` flag in `compose.yaml` [docker/compose.yaml:12-15]().
- **Apple Silicon**: Native support for MPS and MLX acceleration is available for macOS, though Docker deployment on macOS is discouraged as it cannot access these hardware features [docs/en/quick_start/docker_deployment.md:5-7]().
- **Domestic Accelerators**: Extensive support for Chinese domestic hardware including METAX (MACA), T-Head (PPU), and others. These typically require specific base images and device mapping during `docker run` [docs/en/quick_start/docker_deployment.md:30-36]().
- **Lightweight Client Mode**: For devices without high-performance GPUs, a lightweight `mineru` client can connect to remote OpenAI-compatible servers using the `vlm-http-client` backend [docs/en/quick_start/docker_deployment.md:58-67]().

For details on device detection and specific hardware configurations, see [Hardware Acceleration](#5.2).

Sources: [docs/en/quick_start/docker_deployment.md:5-25](), [docs/en/quick_start/docker_deployment.md:58-67](), [docker/compose.yaml:12-15]()

---

## Multi-GPU & Enterprise Deployments

For high-throughput requirements, MinerU can be scaled across multiple GPUs or integrated into enterprise task queues.

- **Service Routing**: The `mineru-router` service can aggregate multiple `mineru-api` instances across different GPUs using the `--upstream-url` flag or manage local workers with `--local-gpus auto` [docker/compose.yaml:60-83]().
- **VRAM Management**: Parameters like `--gpu-memory-utilization` allow tuning the KV cache size (e.g., setting to `0.5` or lower) to prevent Out-Of-Memory (OOM) errors in `vLLM` environments [docker/compose.yaml:15-15]().
- **Device Isolation**: Deployments can target specific GPUs by modifying `device_ids` in the `compose.yaml` resource reservations [docker/compose.yaml:27-27](), [docker/compose.yaml:57-57]().

**Multi-Accelerator Deployment Logic**
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
Sources: [docker/compose.yaml:60-93](), [docker/compose.yaml:15-15](), [docker/compose.yaml:10-10]()

For details on scaling and enterprise integration, see [Multi-GPU & Enterprise Deployments](#5.3).
