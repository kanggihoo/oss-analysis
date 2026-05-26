# awesome-gpt-image-2 분석 보고서

분석 기준: 다국어 README 중 `README_ko-KR.md`를 대표 언어 산출물로 선택했다. 대상 저장소 코드는 수정하지 않았다.

## 1. 이 프로젝트의 목적

`awesome-gpt-image-2`는 GPT Image 2용 이미지 생성 프롬프트를 모아 보여주는 큐레이션 저장소다. 저장소의 핵심 산출물은 언어별 `README*.md`이며, 각 README는 프롬프트 제목, 설명, 원문 프롬프트, 생성 이미지, 작성자/출처/언어 메타데이터, 웹 갤러리 링크를 포함한다.

한국어 산출물인 `README_ko-KR.md` 기준으로 현재 README는 총 프롬프트 6458개, 추천 프롬프트 6개, 일반 프롬프트 120개 표시, 나머지 6338개는 웹 갤러리로 유도하는 구조다.

근거 파일:
- `README_ko-KR.md`
- `scripts/utils/markdown-generator.ts`
- `scripts/generate-readme.ts`

## 2. 프로젝트 유형과 사용 방식

유형은 애플리케이션 서버나 라이브러리라기보다 "문서 큐레이션 + 자동 생성 도구 + GitHub Actions 운영 자동화"에 가깝다.

사용자는 GitHub Issue로 프롬프트를 제출한다. 운영자가 `approved` 라벨을 붙이면 GitHub Actions가 이슈 내용을 CMS에 동기화한다. 별도 스케줄 워크플로는 CMS에서 프롬프트와 카테고리를 읽어 언어별 README를 재생성하고 커밋한다.

주요 실행 방식:
- 로컬 README 생성: `pnpm run generate`
- 승인 이슈 CMS 동기화: `pnpm run sync`
- 운영 자동화: `.github/workflows/update-readme.yml`, `.github/workflows/sync-approved-to-cms.yml`

## 3. 핵심 기능

1. 다국어 README 생성
   - `SUPPORTED_LANGUAGES`에 정의된 locale과 파일명에 따라 `README.md`, `README_ko-KR.md` 등 16개 README 파일을 생성한다.
   - 한국어 locale은 `{ code: 'ko-KR', name: '한국어', readmeFileName: 'README_ko-KR.md' }`로 연결된다.

2. CMS 기반 프롬프트 수집
   - `CMS_HOST`, `CMS_API_KEY`를 사용해 Payload CMS 계열 API로 보이는 `/api/prompts`, `/api/prompt-categories`를 호출한다.
   - `model = gpt-image-2` 조건으로 추천 프롬프트와 카테고리별 프롬프트를 가져온다.

3. GitHub Issue 제출/승인 흐름
   - `.github/ISSUE_TEMPLATE/submit-prompt.yml`이 프롬프트 제목, 프롬프트 본문, 설명, 이미지 URL, 작성자, 출처, 언어, 라이선스 동의를 받는다.
   - 이슈가 `prompt-submission` 라벨을 갖고 있고, 추가된 라벨이 `approved`이면 CMS 동기화 워크플로가 실행된다.

4. 이미지 업로드
   - 제출된 이미지 URL을 fetch한 뒤 CMS `/api/media`로 업로드하고, 업로드된 media id를 프롬프트의 relation 필드에 연결한다.

5. README 표시 최적화
   - GitHub README 길이 제한 때문에 일반 프롬프트는 최대 120개만 표시한다.
   - 나머지는 YouMind 웹 갤러리 링크로 유도한다.

## 4. 실행/사용 진입점

주요 진입점은 두 TypeScript 스크립트다.

- `scripts/generate-readme.ts`
  - `SUPPORTED_LANGUAGES`를 순회한다.
  - locale별 카테고리와 프롬프트를 CMS에서 가져온다.
  - `sortPrompts()`로 추천/일반 프롬프트를 나눈다.
  - `generateMarkdown()`으로 markdown 문자열을 만들고 `fs.writeFileSync()`로 언어별 README 파일을 쓴다.

- `scripts/sync-approved-to-cms.ts`
  - GitHub Actions에서 전달한 `ISSUE_NUMBER`, `ISSUE_BODY`, `GITHUB_REPOSITORY`를 읽는다.
  - Octokit으로 이슈 라벨을 확인한다.
  - 이슈 본문을 파싱해 CMS prompt payload를 만든다.
  - 기존 `sourceMeta.github_issue`가 있으면 update, 없으면 create를 수행한다.
  - 성공 후 이슈가 열려 있으면 닫는다.

워크플로 진입점:
- `.github/workflows/update-readme.yml`: schedule, workflow_dispatch, scripts 변경 push에서 README 생성.
- `.github/workflows/sync-approved-to-cms.yml`: issue labeled 이벤트에서 승인된 prompt submission을 CMS로 전송.

## 5. 주요 모듈과 책임

- `README*.md`
  - 최종 사용자에게 보이는 다국어 큐레이션 문서. 대부분 생성 산출물로 봐야 한다.

- `README_ko-KR.md`
  - 이번 분석에서 선택한 대표 언어 파일. 섹션은 웹 갤러리, 카테고리 탐색, 목차, GPT Image 2 소개, 통계, 추천 프롬프트, 전체 프롬프트, 기여 방법, 라이선스, 감사, 스타 히스토리로 구성된다.

- `scripts/generate-readme.ts`
  - README 생성의 top-level orchestration.

- `scripts/utils/markdown-generator.ts`
  - 언어 목록, locale별 URL 생성, README 섹션 조립, 프롬프트 카드 markdown 생성, 표시 제한 정책을 담당한다.

- `scripts/utils/i18n.ts`
  - `t(key, locale)` 형태의 정적 번역 테이블. 한국어는 `const ko`와 `I18N['ko-KR']`에 연결된다.

- `scripts/utils/cms-client.ts`
  - CMS API 호출, prompt/category 타입, 이미지 URL 정규화, featured/regular 분류 보조 함수를 담당한다.

- `scripts/utils/image-uploader.ts`
  - 외부 이미지 URL을 내려받아 CMS media API에 업로드한다.

- `.github/ISSUE_TEMPLATE/*.yml`
  - 프롬프트 제출과 버그 리포트 입력 양식.

- `.github/workflows/*.yml`
  - README 자동 갱신, 승인 이슈 CMS 동기화, 라벨 동기화, stale issue 자동 종료.

## 6. 핵심 개념과 용어

- Prompt
  - GPT Image 2에 입력할 프롬프트 콘텐츠와 제목, 설명, 이미지, 작성자, 출처, 언어, featured 여부를 담는 CMS 문서 단위.

- Media
  - CMS에 업로드된 이미지 문서. README 생성 시 `media.url` 또는 `sourceMedia`가 이미지 표시 소스로 쓰인다.

- Locale
  - README 생성 언어 코드. 예: `en`, `zh`, `zh-TW`, `ko-KR`, `ja-JP`.

- Featured / Regular
  - 추천 프롬프트와 일반 프롬프트 구분. `sortPrompts()`는 `featured` 플래그로 배열을 나눈다.

- Prompt Category / use-cases
  - CMS 카테고리 중 `parentSlug === 'use-cases'`인 항목을 기준으로 카테고리별 프롬프트를 수집한다.

- `approved`, `prompt-submission`
  - GitHub Issue 기반 제출 흐름의 핵심 라벨. 승인 동기화 워크플로는 두 라벨 조건을 모두 확인한다.

## 7. 입력/데이터/상태/제어 흐름

기여 흐름:

1. 사용자가 `submit-prompt.yml` 이슈 템플릿으로 프롬프트를 제출한다.
2. 이슈에는 자동으로 `prompt-submission` 라벨이 붙는다.
3. 관리자가 `approved` 라벨을 추가한다.
4. `.github/workflows/sync-approved-to-cms.yml`이 실행된다.
5. `scripts/sync-approved-to-cms.ts`가 이슈 본문을 `###` 헤딩 기준으로 파싱한다.
6. 이미지 URL은 `uploadImageToCMS()`를 통해 CMS media로 업로드된다.
7. `sourceMeta.github_issue` 기준으로 기존 프롬프트를 찾고, 있으면 update, 없으면 create한다.
8. 이슈가 open 상태이면 close한다.

README 생성 흐름:

1. `.github/workflows/update-readme.yml` 또는 로컬 `pnpm run generate`가 `scripts/generate-readme.ts`를 실행한다.
2. `SUPPORTED_LANGUAGES`의 각 locale을 순회한다.
3. `fetchPromptCategories(locale)`로 카테고리를 가져온다.
4. `fetchAllPrompts(locale, allCategories)`가 featured prompt와 use-case category별 prompt를 가져온다.
5. `sortPrompts()`가 featured/regular/stats를 만든다.
6. `generateMarkdown()`이 header, language navigation, gallery CTA, TOC, stats, featured, all prompts, contribute, footer를 순서대로 붙인다.
7. `README_ko-KR.md` 같은 언어별 파일에 저장된다.

## 8. 설정 및 환경 구성

필수 환경변수:
- `CMS_HOST`
- `CMS_API_KEY`

CMS 동기화 추가 환경변수:
- `GITHUB_TOKEN`
- `GITHUB_REPOSITORY`
- `ISSUE_NUMBER`
- `ISSUE_BODY`

근거:
- `.env.example`
- `docs/LOCAL_DEVELOPMENT.md`
- `.github/workflows/update-readme.yml`
- `.github/workflows/sync-approved-to-cms.yml`

TypeScript 설정:
- `target`: `ES2022`
- `module`: `ES2022`
- `moduleResolution`: `node`
- `strict`: `true`
- `rootDir`: `./scripts`
- `outDir`: `./dist`

## 9. 의존성 구조

런타임 의존성:
- `node-fetch`: CMS/API/image URL fetch.
- `qs-esm`: Payload CMS API 쿼리 문자열 생성.

개발/실행 의존성:
- `tsx`: TypeScript 스크립트 직접 실행.
- `typescript`: 타입 검사/컴파일 기반.
- `dotenv`: `.env` 로딩.
- `@octokit/rest`: GitHub Issue 조회/닫기.
- `@types/node`: Node 타입.

패키지 매니저는 `pnpm@9.15.9`로 명시되어 있다.

## 10. 빌드/실행/테스트 방식

`package.json`에 정의된 스크립트:

- `pnpm run generate`
  - `tsx scripts/generate-readme.ts`

- `pnpm run sync`
  - `tsx scripts/sync-approved-to-cms.ts`

로컬 개발 문서 기준:
- `pnpm install`
- `.env`에 CMS 설정 추가
- `pnpm run generate`로 README 생성 테스트
- 동기화 테스트는 GitHub 토큰, repository, issue number/body가 필요하다.

테스트 전용 스크립트는 `package.json`에 정의되어 있지 않다. 따라서 현재 저장소에서 확인되는 검증 방식은 실제 스크립트 실행과 GitHub Actions 실행 결과에 의존한다.

## 11. 에러 처리와 디버깅 포인트

- CMS API 호출 실패
  - `cms-client.ts`는 `response.ok`가 아니면 `CMS API error: ...`를 throw한다.
  - `docs/LOCAL_DEVELOPMENT.md`는 401 발생 시 `CMS_API_KEY`, `CMS_HOST` trailing slash, 권한을 확인하라고 안내한다.

- `ISSUE_NUMBER` 누락
  - `sync-approved-to-cms.ts`는 `ISSUE_NUMBER`가 없으면 즉시 throw한다.

- 이미지 업로드 실패
  - 개별 이미지 업로드 실패는 로그만 남기고 다음 이미지 처리를 계속한다.

- README 생성 실패
  - `generate-readme.ts`의 top-level catch가 에러를 출력하고 `process.exit(1)`로 종료한다.

- push 충돌
  - `update-readme.yml`은 auto commit 후 push가 실패하면 최대 5회 `git pull --rebase origin main` 후 재시도한다.

- 확인 필요
  - `docs/FAQ.md`와 한국어 README 문구는 README가 "4시간 이내" 반영된다고 설명하지만, `update-readme.yml`의 cron은 `0 0,12 * * *`로 하루 2회 실행이다. 실제 운영에서 별도 워크플로가 더 있는지, 문구가 오래된 것인지 확인이 필요하다.
  - `SUPPORTED_LANGUAGES`는 16개 언어를 정의하지만, 한국어 README/i18n 문구에는 "17개 언어 지원"이라고 표시된다. CMS나 웹 갤러리 쪽 언어 수를 포함한 문구인지 확인이 필요하다.

## 12. 확장하거나 기여할 때 봐야 할 구조

새 언어를 추가하려면:
1. `scripts/utils/markdown-generator.ts`의 `SUPPORTED_LANGUAGES`에 locale과 README 파일명을 추가한다.
2. `scripts/utils/i18n.ts`에 해당 locale 번역 객체를 추가하고 `I18N`에 매핑한다.
3. `.github/ISSUE_TEMPLATE/submit-prompt.yml`의 Prompt Language 옵션과 `scripts/sync-approved-to-cms.ts`의 `LANGUAGE_MAP`도 함께 확인한다.
4. CMS가 해당 locale을 지원하는지 확인한다.

새 README 섹션을 추가하려면:
1. `scripts/utils/markdown-generator.ts`에서 `generateMarkdown()` 조립 순서를 확인한다.
2. 섹션 생성 함수를 추가하거나 기존 `generateHeader`, `generateGalleryCTA`, `generatePromptSection`, `generateFooter` 등을 수정한다.
3. 필요한 문구는 `i18n.ts`의 `Translation` 인터페이스와 각 locale 객체에 추가한다.

프롬프트 제출 필드를 바꾸려면:
1. `.github/ISSUE_TEMPLATE/submit-prompt.yml`의 field id/label을 수정한다.
2. `scripts/sync-approved-to-cms.ts`의 `IssueFields`, `FIELD_NAME_MAP`, `parseIssue()` 후 payload 생성부를 함께 수정한다.
3. CMS prompt schema와 필드명이 맞는지 확인한다.

## 13. 처음 기여자가 먼저 읽어야 할 파일

1. `README_ko-KR.md`
   - 최종 산출물이 어떤 모양인지 가장 빨리 이해할 수 있다.

2. `docs/CONTRIBUTING.md`
   - 제출 방식, 필수 정보, 이미지 요구사항, 라이선스 동의, 리뷰 절차를 확인한다.

3. `docs/LOCAL_DEVELOPMENT.md`
   - 로컬 실행, `.env`, 스크립트, 트러블슈팅, 운영 워크플로를 확인한다.

4. `package.json`
   - 실제 실행 가능한 npm scripts와 의존성을 확인한다.

5. `scripts/generate-readme.ts`
   - README 자동 생성 전체 흐름을 이해한다.

6. `scripts/utils/markdown-generator.ts`
   - 다국어 README 구조와 각 섹션 생성 방식을 이해한다.

7. `scripts/utils/cms-client.ts`
   - 데이터가 어디에서 오고 어떤 필터/정렬로 가져오는지 이해한다.

8. `.github/workflows/sync-approved-to-cms.yml`
   - 승인된 이슈가 CMS에 들어가는 운영 흐름을 이해한다.

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- CMS schema는 저장소 안에 없다. `Prompt`, `Media`, `PromptCategory` 타입은 클라이언트 코드에 정의되어 있지만 실제 Payload CMS 컬렉션 스키마는 범위 내 단서 없음.
- 웹 갤러리 애플리케이션 코드는 이 저장소에 없다. `https://youmind.com/.../gpt-image-2-prompts`와의 실제 라우팅/검색/생성 기능은 범위 내 단서 없음.
- README 반영 주기 문구와 GitHub Actions cron이 일치하지 않는다. 문서는 4시간, workflow는 하루 2회로 보인다.
- 언어 수 문구가 `17개 언어 지원`인데 코드상 README 생성 언어는 16개다. 실제 서비스 지원 언어 수와 README 생성 언어 수가 다른지 확인 필요.
- 저장소에 테스트 스크립트가 없다. 자동화의 회귀 검증은 현재 GitHub Actions와 실제 CMS 응답에 의존하는 것으로 보인다.
