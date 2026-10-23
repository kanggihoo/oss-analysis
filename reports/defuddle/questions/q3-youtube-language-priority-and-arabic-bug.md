---
sha: "556d74e8c8fd68c49912d4b11a4ae9ec04d7b2b5"
created: 2026-10-23
updated: 2026-10-23
sources:
  - src/extractors/youtube.ts
  - src/cli.ts
  - src/node.ts
  - CHANGELOG.md
  - tests/youtube-transcript.test.ts
  - tests/fixtures/youtube/issues--410-default-audio.html
  - tests/expected/youtube/issues--410-default-audio.json
---

# Q3. YouTube 자막 언어를 직접 지정할 수 있나 / 가끔 아랍어로 나오는 이유

## 결론 (요약)

1. **지정할 수 있다** — CLI `--lang`(`-l`) 옵션. 지정하면 다른 모든 추측 로직보다 먼저 그 언어를 찾는다.
2. **"가끔 아랍어" 증상은 실제로 있었던 버그(GitHub #410)와 정확히 일치하는 패턴이다.** 원인은 "기본 자막"을 못 찾았을 때 과거 코드가 트랙 목록의 0번째를 그냥 집었는데, YouTube는 자동 번역 자막을 알파벳 순으로 나열해서 0번째가 종종 Arabic 근처 언어였다. 이 버그는 분석 중인 커밋(`556d74e`)의 소스에는 고쳐져 들어가 있지만, **npm 레지스트리를 직접 확인한 결과 그 수정은 아직 배포되지 않았다** — `npm install defuddle`/`npx defuddle`로 받는 최신 버전(`0.19.5`)은 수정 전 코드다. 아래 "npm 배포 여부" 참고.

## 1. 언어를 직접 지정하는 법

CLI에서 `-l, --lang <code>` 옵션(BCP 47 코드, 예: `ko`, `ja`, `en`)을 주면 된다.

```bash
npx defuddle parse "https://youtube.com/watch?v=..." --markdown --lang ko
```

이 값은 그대로 전달된다: `src/cli.ts`의 `parseSource()`가 `defuddleOpts.language = options.lang`으로 세팅 → `src/node.ts`의 `Defuddle()` → 내부적으로 `options.language`로 추출기에 전달 → `YoutubeExtractor.pickCaptionTrack()`(`src/extractors/youtube.ts:229-250`)의 **제일 첫 줄**이 이 값부터 확인한다:

```ts
const preferredLang = this.options.language;
if (preferredLang) {
    const match = this.findPreferredCaptionTrack(captionTracks, preferredLang);
    if (match) return match;   // 있으면 바로 반환 — 아래 "기본값 추측" 로직은 건너뜀
}
```

즉 `--lang`을 주고 그 언어 자막이 그 영상에 실제로 존재하면, 아래에서 설명하는 "기본 언어 추측" 로직은 아예 타지 않는다. **가장 확실한 회피책은 매번 원하는 언어를 명시하는 것**이다.

## 2. `--lang`을 안 줬을 때 — "기본 언어"를 추측하는 순서

`--lang`이 없거나, 지정한 언어의 자막이 그 영상에 없으면 `pickCaptionTrack()`은 순서대로 시도한다(229~250행):

1. `getDefaultCaptionTrack()` — YouTube가 player response에 "이게 기본 오디오의 기본 자막이다"라고 명시한 인덱스(`defaultCaptionTrackIndex`)를 찾는다.
2. 그게 없으면 `getOriginalLanguageTrack()` — 자동 생성 자막(ASR, kind === 'asr')의 언어를 "원본 음성 언어"로 추정한다.
3. 그것도 실패하면 영어 트랙을 찾고, **그마저 없으면 목록의 0번째 트랙을 그냥 쓴다** (`pool[0]`, 249행).

## 3. 아랍어가 나오는 이유 — 3번 "목록의 0번째" 분기

`getDefaultCaptionTrack()` 바로 위 주석(183~185행)이 원인을 정확히 설명한다:

> YouTube's default caption for the current audio track. Translation tracks are listed alphabetically (Afrikaans, Arabic, …), so index 0 is usually a translation rather than the spoken language.

(번역: 번역 자막 트랙들은 알파벳 순으로 나열돼 있어서(Afrikaans, Arabic, …) 0번째는 보통 실제 음성 언어가 아니라 번역본이다.)

즉, **"기본"이라고 명시적으로 표시된 자막도 없고 음성 언어 추정도 실패하는 영상**(주로 자동 더빙된 영상 — 오디오 트랙이 여러 개인데 어느 게 "기본"인지 명시가 안 된 경우)을 만나면, 코드가 결국 트랙 배열의 0번째를 집는데, YouTube가 자동 번역 자막을 알파벳 순으로 정렬해두기 때문에 그 0번째가 우연히 Arabic 같은, 사용자가 원하지 않는 언어가 되는 것이다. 사용자가 겪은 증상과 정확히 일치한다.

## 4. 이 버그는 이미 고쳐졌다 — GitHub Issue #410 / 커밋 `f6ca46d`

`CHANGELOG.md`의 "Unreleased" 절(1~3행)에 정확히 이 버그가 올라와 있다:

> Fixed YouTube auto-dub captions being selected instead of the default audio language when the player response omits the default caption index (#410).

커밋 `f6ca46d`("Fix YouTube caption selection for default audio language (#411)", 2026-10-10)가 그 수정이다. 테스트(`tests/youtube-transcript.test.ts:1005-` "YouTube default audio language (#410)")에 재현 fixture가 그대로 남아있다 — 주석: "Anonymized from the report: a Japanese video with an English auto-dub. Neither audio track names a default caption, and both list the same order." (제보를 익명화한 것: 영어로 더빙된 일본어 영상. 두 오디오 트랙 모두 기본 자막을 지정하지 않았고 순서도 같았다.)

수정 내용(`git show f6ca46d`로 확인): 전에는 `defaultAudioTrackIndex`나 `defaultCaptionTrackIndex`가 없으면 그냥 `undefined`를 반환해 아래 단계(결국 `pool[0]`)로 떨어졌는데, 수정 후에는 **오디오 트랙의 언어 코드(`audioTrackId`, 예: `"ja.4"`)로 수동 자막 중 같은 언어를 먼저 찾도록** 로직이 보강됐다(`getDefaultCaptionTrack()` 196~206행, `getOriginalLanguageTrack()`도 ASR 트랙을 오디오 트랙에 연결된 인덱스로만 찾도록 강화됨, 210~227행).

`556d74e`(이번에 분석한 HEAD)는 `f6ca46d`의 후속 커밋이므로 **이 수정을 포함한다.**

## npm 배포 여부 — 확인 완료: 아직 수정판이 배포되지 않았다

`https://registry.npmjs.org/defuddle` 공개 API(로그인 불필요)를 받아 확인했다(실행 확인):

- `dist-tags.latest` = `0.19.5`, 등록된 버전 목록도 `0.19.5`가 마지막이다 — **`0.19.5` 이후로 새 버전이 npm에 올라온 적이 없다.**
- `0.19.5`의 npm 배포(publish) 시각: `2026-10-10T15:35:10.787Z`
- git 커밋 시각(UTC로 환산, `git log --date=iso-strict`):
  - `0.19.5` 태그 커밋(`e87d416`): `2026-10-10T15:32:07Z` → npm 배포(15:35:10Z) 3분 전. 태그를 찍자마자 배포됐다는 뜻
  - 버그 수정 커밋(`f6ca46d`): `2026-10-10T17:42:13Z` → **npm 배포보다 2시간 10분 뒤**
  - 분석 기준 HEAD(`556d74e`): `2026-10-10T17:59:08Z` → 역시 npm 배포 이후

즉 **수정 커밋이 npm에 `0.19.5`가 올라간 뒤에 들어갔고, 그 뒤로 새 버전이 배포된 적이 없다.** `.github/workflows/release.yml`을 보면 이 레포는 git 태그를 push할 때마다 CI가 `npm publish`를 자동 실행하는 구조인데(30~33행에서 "태그 이름 = package.json 버전"을 먼저 검증), `0.19.5` 이후 새 태그가 없으므로 자동 배포도 없었다.

**결론: 지금 `npm install defuddle`이나 `npx defuddle`로 받으면 100% 이 버그가 있는 버전(`0.19.5`)을 받는다.** 고친 버전을 쓰려면:
1. 매번 `--lang`을 명시한다(가장 간단, 이미 동작 확인됨), 또는
2. GitHub 소스를 직접 설치한다 — `npm install github:kepano/defuddle` (package.json의 `"build": "npm run clean && npm run build:types && npm run build:node && npm run build:js"`가 설치 시 돌아가야 하므로 빌드 도구가 필요할 수 있음, **미확인**: 이 설치 경로 자체를 실행해보진 않았다)
3. 메인테이너가 다음 버전을 태그·배포할 때까지 기다린다

## 검증 수준

- CLI `--lang` 전달 경로, `pickCaptionTrack()` 우선순위, 버그 원인 주석, 수정 커밋 diff, 회귀 테스트 fixture: **코드 확인**
- npm 레지스트리 최신 배포 버전·배포 시각, git 커밋 시각 대조: **실행 확인** (`registry.npmjs.org/defuddle` 공개 API 응답 기준, 2026-10-23 확인)
- `npm install github:kepano/defuddle` 설치 경로가 실제로 동작하는지: **미확인**
