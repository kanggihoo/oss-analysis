---
sha: "556d74e8c8fd68c49912d4b11a4ae9ec04d7b2b5"
created: 2026-10-23
updated: 2026-10-23
sources:
  - src/extractors/youtube.ts
  - src/utils/transcript.ts
---

# Q2. YouTube 자막은 어떻게 가져오는가 — 처음 fetch한 HTML 안에 이미 들어있는가

## 결론 (요약)

아니다. 처음 받은 watch 페이지 HTML 안에는 **자막 트랙의 "위치(URL) 정보"만** 들어있고, 실제 자막 텍스트는 그 URL로 **별도 HTTP 요청을 한 번 더** 보내야 받을 수 있다. 추가로 defuddle은 그 정보가 최신인지 보장하기 위해 YouTube의 비공식 내부 API("InnerTube")에도 요청을 보낸다. 즉 최소 2번, 최대 3번의 네트워크 요청이 걸린다.

## 입력 → 내부 동작 → 반환값

**입력**: YouTube watch 페이지 URL(예: `youtube.com/watch?v=...`), `fetch()`로 받은 HTML 문서

**내부 동작** (`YoutubeExtractor.extractAsync()`, `src/extractors/youtube.ts:95-106`):

1. **1단계 — 처음 fetch한 HTML에서 캡션 "목록"만 꺼낸다.** YouTube는 watch 페이지를 만들 때 플레이어 상태 전체를 `ytInitialPlayerResponse`라는 전역 변수로 `<script>` 태그 안에 JSON 통째로 박아둔다(`parseInlineJson()`, 566~602행). 이 JSON의 `captions.playerCaptionsTracklistRenderer.captionTracks` 배열(`getCaptionTracks()`, 133~136행)에 언어별 자막 "트랙" 목록이 있는데, 각 트랙은 `{ languageCode, baseUrl, kind, ... }` 형태다 — **`baseUrl`은 자막 파일을 받을 수 있는 URL일 뿐, 자막 텍스트 자체가 아니다.**
2. **2단계 — (병렬로) YouTube 내부 API에도 물어본다.** `fetchPlayerData()`(796~888행)가 YouTube 공식 웹페이지가 아니라 **YouTube 모바일 앱이 쓰는 비공식 내부 API**(`INNERTUBE_API_URL = https://www.youtube.com/youtubei/v1/player`)에 iOS 클라이언트 → Android 클라이언트 → Web 클라이언트 순으로 각각 다른 "클라이언트 신분증"(`context.client.clientName`)을 사칭해 POST 요청을 보낸다. 성공하면 1단계보다 더 신뢰할 수 있는(새로고침된) 캡션 트랙 목록을 얻는다. 코드 주석(29행)은 "Unofficial InnerTube API"라고 명시한다 — 공식 문서화된 API가 아니라 리버스 엔지니어링된 엔드포인트라는 뜻.
3. **3단계 — 트랙 하나를 고른다.** 사용자가 지정한 언어(`options.language`) → 기본 언어 → 원본 음성 언어 순으로 `pickCaptionTrack()`(229행대)이 1순위 트랙을 고른다.
4. **4단계 — 그제서야 실제 자막 파일을 받는다.** `fetchCaptionXml()`(649~681행)이 3단계에서 고른 트랙의 `baseUrl`로 **또 한 번 GET 요청**을 보낸다. 응답은 XML(YouTube의 `srv3` 자막 포맷, `<p t="1234"><s>단어</s>...</p>` 형태)이고, `parseTranscriptXml()`(983행~)이 이 XML을 파싱해서 타임스탬프 있는 문장 목록으로 바꾼다. **이 응답 본문이 실제 자막 텍스트가 들어있는 유일한 곳이다.**
5. (부가) 챕터(소제목)는 `fetchChapters()`(890행~)가 역시 InnerTube의 다른 엔드포인트(`/youtubei/v1/next`)에서 따로 받아오거나, 있으면 인라인 JSON에서 꺼낸다.

보안 장치 하나: `fetchCaptionXml()`은 받은 `baseUrl`의 호스트가 `*.youtube.com`이 맞는지 검사한다(655~656행) — 공격자가 조작한 페이지가 엉뚱한 서버로 요청을 보내게 만드는 SSRF를 막기 위함(**추론**: 주석은 "prevent SSRF"라고 명시하지만 공식 위협 모델 문서는 없음).

**반환값**: `{ html, text, languageCode }` 형태의 트랜스크립트(타임스탬프 + 화자 구분 포함) — `buildResult()`를 거쳐 최종 `DefuddleResponse.content`에 들어간다.

## 코드 대응 표

| 단계 | 실제 요청 대상 | 파일:줄 |
|---|---|---|
| 1. 인라인 JSON에서 트랙 "목록"만 추출 | 없음(이미 받은 HTML 파싱) | `src/extractors/youtube.ts:566-602`, `133-136` |
| 2. InnerTube API로 최신 트랙 목록 재확인 | `POST https://www.youtube.com/youtubei/v1/player` (iOS→Android→Web 클라이언트 순) | `src/extractors/youtube.ts:796-888` |
| 3. 트랙 선택(언어 우선순위) | 없음 | `src/extractors/youtube.ts:229-` |
| 4. 실제 자막 텍스트 요청 | `GET <선택된 track.baseUrl>` (`*.youtube.com`만 허용) | `src/extractors/youtube.ts:649-681` |
| 5. XML → 문장 변환 | 없음 | `src/extractors/youtube.ts:983-` |
| (부가) 챕터 | `POST https://www.youtube.com/youtubei/v1/next` | `src/extractors/youtube.ts:890-919` |

## 참고: 다른 실행 환경에서는 경로가 다르다

위는 CLI/Node/Cloudflare Worker처럼 **`fetch()`로 받은 정적 HTML**(linkedom 파싱, 자바스크립트 미실행)에서 동작하는 경로다. 반면 브라우저 확장(Obsidian Web Clipper 등, `new Defuddle(document)`)처럼 **실제 브라우저가 이미 렌더링한 살아있는 페이지**에서 돌 때는 `extractTranscriptFromOpenedDom()`(730~756행)이라는 또 다른 경로가 있다 — "자막 보기" 버튼을 실제로 클릭(`transcriptButton.click()`)하고 화면에 나타난 자막 패널 DOM을 읽는다. 이건 fetch로 받은 정적 HTML에서는 애초에 불가능한 방식이다(클릭할 버튼이 "진짜로 그려져" 있지 않으므로). 이번 질문은 fetch 경로에 한정해 답했다.

## 미확인

- 실제 네트워크 요청을 보내 InnerTube API 응답이나 캡션 XML을 실행 확인하지는 않았다(외부 서비스 접속 — 워크플로 9장에 따라 사용자 동의 없이 바로 실행하지 않음). 원하면 실행해서 보여줄 수 있다.
- InnerTube API의 공식 사양은 Google이 공개하지 않으므로, 클라이언트 신분증 사칭 방식이 정확히 어떤 약관적 지위인지는 **미확인**.
