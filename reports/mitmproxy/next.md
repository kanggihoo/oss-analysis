# Next Session Plan: mitmproxy

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `77355977e5ea540b51ed029a40ed1dc2f1c2ba7b`
- **작성/갱신 일자**: `2026-10-15`

---

## 1. 이번 세션에서 확인한 범위

- [x] clone, 메타데이터(`artifacts/mitmproxy/`), GitHub 정보 수집
- [x] 디렉터리 구조 파악, CLI 3종 엔트리(`pyproject.toml`)
- [x] 프록시 모드 목록 확인 (`mode_specs.py`), TCP/UDP 폴백 로직 위치 확인 (`next_layer.py`)
- [x] 공식 문서 `concepts/modes.md`, `protocols.md`로 local capture·프로토콜 제약 확인
- [x] overview.md에 주요 기능 정리
- [x] 관점 변경: 소스 분석보다 **기능 / 설치·삭제 / 사용법** 중심으로 overview.md 3절 작성 (공식 문서 `docs/src/content/` 기준, 실행은 하지 않음). 삭제 절차는 공식 문서에 없어 `추론` 표시

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 분석 목적 확정 (학습 / 설계 참고 / 도입 검토)
- [ ] 프록시 코어는 Layer 스택을 어떻게 구성하나? (`layer.py`, `context.py`, `commands.py`/`events.py`의 sans-IO 구조 여부)
- [ ] 대표 실행 흐름: 클라이언트 연결 → `next_layer` → TLS 핸드셰이크 → `HttpLayer` → addon hook
- [ ] TLS 복호화: CA 생성과 도메인별 인증서 발급 경로 (`certs.py`, `tlsconfig.py`)
- [ ] local 모드는 어떻게 앱 설정 없이 캡처하나? (`mitmproxy_rs`는 별도 레포라 이 레포로는 한계)
- [ ] (선택) 실제 클라이언트(curl, Node.js 앱 등)로 regular / local 모드 캡처 실행 실험 — 클라이언트별 프록시 환경변수·CA 신뢰 지원 확인

---

## 3. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `mitmproxy/tools/main.py` | `mitmproxy`, `mitmdump`, `mitmweb` | 세 CLI가 같은 코어를 부팅하는 경로 |
| `mitmproxy/master.py`, `addons/proxyserver.py` | `Master`, `Proxyserver` | 모드별 서버 시작, 연결 수락 |
| `mitmproxy/proxy/layer.py`, `server.py` | `Layer`, `ConnectionHandler` | Layer 스택과 이벤트 구동 방식 |
| `mitmproxy/addons/next_layer.py` | `NextLayer._next_layer` | 프로토콜 판별 분기 (HTTP/TLS/TCP/UDP/DNS) |
| `mitmproxy/proxy/layers/tls.py`, `addons/tlsconfig.py`, `certs.py` | `ClientTLSLayer`, `CertStore` | TLS 가로채기와 인증서 발급 |
| `mitmproxy/proxy/layers/http/__init__.py` | `HttpLayer` | HTTP 요청·응답 처리와 addon 훅 호출 지점 |
| `docs/src/content/concepts/how-mitmproxy-works.md` | — | 공식 설명과 코드의 교차 검증 |

---

## 4. 참고 사항 및 후속 제안

- 이 PC의 `python`은 uv로 설치한 3.12(`~/.local/bin/python.exe`). mitmproxy 실행은 `AGENTS.md`(레포 내) 지침상 `uv run`을 쓴다. 지금 단계에서는 **실행하지 않고 코드만 읽음**
- 실행 실험을 하면 요청 본문(인증 헤더, 대화 내용)이 평문 로그에 남으니 `artifacts/`에 저장 시 민감정보 마스킹 필요
- 제안 질문(그림을 본 뒤): ① Layer 스택은 왜 sans-IO 구조인가 ② addon 훅 순서와 확장 지점 ③ HTTPS 복호화 실패(인증서 거부) 시 처리 ④ 스트리밍(SSE) 응답은 어떻게 다루나 ⑤ local 모드와 regular 모드의 경계
