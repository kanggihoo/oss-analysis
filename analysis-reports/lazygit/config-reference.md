# lazygit 환경설정 정리

근거 문서:
- `lazygit/docs/Config.md`
- 보조 근거: `lazygit/docs/Custom_Command_Keybindings.md`, `lazygit/docs/Custom_Pagers.md`, `lazygit/docs/keybindings/Custom_Keybindings.md`

## 설정 파일 위치

기본 전역 설정 파일은 OS별로 다르다.

| OS | 기본 경로 |
|---|---|
| Linux | `~/.config/lazygit/config.yml` |
| macOS | `~/Library/Application Support/lazygit/config.yml` |
| Windows | `%LOCALAPPDATA%\lazygit\config.yml`, 보조로 `%APPDATA%\lazygit\config.yml` |

구버전 설치 경로도 계속 고려된다.

| OS | 구버전 경로 |
|---|---|
| Linux | `~/.config/jesseduffield/lazygit/config.yml` |
| macOS | `~/Library/Application Support/jesseduffield/lazygit/config.yml` |
| Windows | `%APPDATA%\jesseduffield\lazygit\config.yml` |

저장소별 설정도 가능하다.

| 위치 | 의미 |
|---|---|
| `<repo>/.git/lazygit.yml` | 해당 repo에서만 global config를 덮어쓴다. |
| 상위 디렉터리의 `.lazygit.yml` | 여러 repo 묶음에 공통 설정을 적용할 때 쓸 수 있다. |

설정 파일 위치를 바꾸는 방법:

```sh
CONFIG_DIR="$HOME/.config/lazygit" lazygit
lazygit --use-config-file="$HOME/.base_lg_conf,$HOME/.light_theme_lg_conf"
LG_CONFIG_FILE="$HOME/.base_lg_conf,$HOME/.light_theme_lg_conf" lazygit
```

`config.yml`에는 JSON schema를 붙일 수 있다.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/jesseduffield/lazygit/master/schema/config.json
```

## 전체 설정 그룹

`Config.md`의 기본 YAML은 크게 다음 그룹으로 나뉜다.

| 그룹 | 목적 |
|---|---|
| `gui` | UI, 레이아웃, 색상, 표시 방식, 검색 방식, 파일 트리, 화면 모드 |
| `git` | Git 동작, diff/log/pager, fetch/refresh, commit/merge, branch 정렬 |
| `update` | lazygit 업데이트 확인 방식 |
| `refresher` | 자동 refresh/fetch 주기 |
| `confirmOnQuit` | 종료 확인 팝업 |
| `quitOnTopLevelReturn` | 최상위에서 `Esc` 입력 시 종료 여부 |
| `os` | editor, file open, clipboard, shell function 연동 |
| `disableStartupPopups` | 시작 안내 팝업 비활성화 |
| `customCommands` | 사용자 정의 명령/단축키 |
| `services` | Git hosting provider URL 매핑 |
| `notARepository` | Git repo 밖에서 실행했을 때 동작 |
| `promptToReturnFromSubprocess` | subprocess 종료 후 lazygit 복귀 전 확인 |
| `keybinding` | 기본 키 바인딩 override/disable |

## `gui`: 화면과 표시 방식

### 색상과 식별 표시

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.authorColors` | `{}` | commit author별 색상 지정. wildcard `*` 가능 |
| `gui.branchColorPatterns` | `{}` | branch 이름 regex 패턴별 색상 지정 |
| `gui.customIcons.filenames` | `{}` | 특정 filename에 아이콘/색상 지정 |
| `gui.customIcons.extensions` | `{}` | 특정 extension에 아이콘/색상 지정 |
| `gui.theme.*` | 여러 기본값 | border, selected line, copied commit, marked base commit, unstaged change 등의 색상 |

색상 속성은 색상 하나와 modifier 조합으로 표현한다.

색상:
- `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`
- hex 색상 예: `'#ff00ff'`

modifier:
- `bold`
- `default`
- `reverse`
- `underline`
- `strikethrough`

예:

```yaml
gui:
  theme:
    selectedLineBgColor:
      - reverse
```

### 스크롤과 diff 표시

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.scrollHeight` | `2` | main window 스크롤 단위 |
| `gui.scrollPastBottom` | `true` | content 끝 아래까지 스크롤 허용 |
| `gui.scrollOffMargin` | `2` | 선택 줄 아래에 남겨둘 여유 줄 수 |
| `gui.scrollOffBehavior` | `margin` | `margin` 또는 `jump` |
| `gui.tabWidth` | `4` | main view/diff에서 tab 폭 |
| `gui.wrapLinesInStagingView` | `true` | staging view에서 긴 줄 wrap |
| `gui.useHunkModeInStagingView` | `true` | staging view 진입 시 hunk mode 기본 사용 |
| `gui.splitDiff` | `auto` | staged/unstaged가 같이 있을 때 main window split 방식. `auto`, `always` |

`scrollOffBehavior: margin`은 선택 줄이 화면 하단에 가까워지면 조금 일찍 스크롤해 다음 내용을 보이게 한다. `jump`는 끝에 도달했을 때 반 페이지 단위로 이동한다.

### 마우스와 경고 팝업

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.mouseEvents` | `true` | terminal mouse event capture |
| `gui.skipAmendWarning` | `false` | amend warning 생략 |
| `gui.skipDiscardChangeWarning` | `false` | staging view discard warning 생략 |
| `gui.skipStashWarning` | `false` | stash apply/pop warning 생략 |
| `gui.skipNoStagedFilesWarning` | `false` | staged file 없이 commit할 때 warning 생략 |
| `gui.skipRewordInEditorWarning` | `false` | editor로 reword할 때 warning 생략 |
| `gui.skipSwitchWorktreeOnCheckoutWarning` | `false` | 다른 worktree checkout 전환 확인 생략 |

위 설정들은 편의성과 안전성의 trade-off다. lazygit은 기본적으로 위험한 작업을 확인하게 두고, 사용자가 원하면 warning을 줄일 수 있게 한다.

### 레이아웃과 화면 모드

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.sidePanelWidth` | `0.3333` | 좌측 side section 폭 비율 |
| `gui.expandFocusedSidePanel` | `false` | focused side window 높이를 크게 만드는 accordion 효과 |
| `gui.expandedSidePanelWeight` | `2` | expanded side panel 상대 높이 |
| `gui.mainPanelSplitMode` | `flexible` | main panel split 방향. `horizontal`, `vertical`, `flexible` |
| `gui.enlargedSideViewLocation` | `left` | half screen mode에서 side view 위치. `left`, `top` |
| `gui.screenMode` | `normal` | 기본 focused window 크기. `normal`, `half`, `full` |
| `gui.border` | `rounded` | border 스타일. `rounded`, `single`, `double`, `hidden`, `bold` |
| `gui.portraitMode` | `auto` | UI component를 세로로 쌓을지 여부. `auto`, `always`, `never` |
| `gui.portraitModeAutoMaxWidth` | `84` | portrait auto 적용 최대 폭 |
| `gui.portraitModeAutoMinHeight` | `46` | portrait auto 적용 최소 높이 |

화면 모드는 lazygit 안에서 `+`와 `_`로 바꿀 수 있지만, config 기본값 자체는 바뀌지 않는다.

### 언어, 시간, font/icon

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.language` | `auto` | UI 언어. `auto`, `en`, `zh-CN`, `zh-TW`, `pl`, `nl`, `ja`, `ko`, `ru`, `pt` |
| `gui.timeFormat` | `02 Jan 06` | commit time 표시 형식 |
| `gui.shortTimeFormat` | `3:04PM` | 24시간 이내 시간 표시 형식 |
| `gui.nerdFontsVersion` | `""` | Nerd Fonts icon 버전. 빈 값이면 icon 표시 안 함 |
| `gui.showFileIcons` | `true` | Nerd Fonts 사용 시 file icon 표시 |

Nerd Fonts 아이콘을 보려면:

```yaml
gui:
  nerdFontsVersion: "3"
```

### 파일 트리와 list 표시

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.showListFooter` | `true` | list view 하단에 `5 of 20` 같은 footer 표시 |
| `gui.showFileTree` | `true` | file view를 tree로 표시. lazygit 안에서 `` ` `` 키로 toggle 가능 |
| `gui.showRootItemInFileTree` | `true` | 필요할 때 root `/` item 표시 |
| `gui.fileTreeSortOrder` | `mixed` | `mixed`, `filesFirst`, `foldersFirst` |
| `gui.fileTreeSortCaseSensitive` | `true` | file tree 정렬 시 대소문자 구분 |
| `gui.showNumstatInFilesView` | `false` | Files view에 변경 line 수 표시 |

### commit/log 표시

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.commitLength.show` | `true` | commit message length indicator 표시 |
| `gui.commitAuthorShortLength` | `2` | 일반 commit view author 길이 |
| `gui.commitAuthorLongLength` | `17` | expanded commit view author 길이 |
| `gui.commitHashLength` | `8` | commits view hash 길이 |
| `gui.showBranchCommitHash` | `false` | branches view에 commit hash 표시 |
| `gui.showDivergenceFromBaseBranch` | `none` | base branch divergence 표시. `none`, `onlyArrow`, `arrowAndNumber` |

### command log, 검색, status panel

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `gui.showRandomTip` | `true` | 시작 시 command log에 tip 표시 |
| `gui.showCommandLog` | `true` | command log 표시 |
| `gui.commandLogSize` | `8` | command log view 높이 |
| `gui.showBottomLine` | `true` | 하단 keybinding/help line 표시 |
| `gui.showPanelJumps` | `true` | window title에 jump key 표시 |
| `gui.filterMode` | `substring` | `/` 검색/필터 방식. `substring`, `fuzzy` |
| `gui.spinner.frames` | `|`, `/`, `-`, `\` | loading spinner frame |
| `gui.spinner.rate` | `50` | spinner 속도(ms) |
| `gui.statusPanelView` | `dashboard` | status panel 기본 view. `dashboard`, `allBranchesLog` |
| `gui.switchToFilesAfterStashPop` | `true` | stash pop 후 Files panel 이동 |
| `gui.switchToFilesAfterStashApply` | `true` | stash apply 후 Files panel 이동 |
| `gui.switchTabsWithPanelJumpKeys` | `false` | panel jump key 대상이 이미 active면 다음 tab으로 이동 |

`filterMode: substring`은 입력 문자열을 그대로 찾고, 대문자가 있으면 case-sensitive로 동작한다. `fuzzy`는 글자들이 순서대로 포함되는지를 기준으로 더 느슨하게 찾는다.

## `git`: Git 동작

### Pagers와 diff

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `git.pagers` | `[]` | diff 출력 후처리 도구 목록 |
| `git.ignoreWhitespaceInDiffView` | `false` | diff에서 whitespace 무시. lazygit 안에서 `Ctrl+w`로 toggle |
| `git.diffContextSize` | `3` | diff hunk 주변 context line 수. `{`, `}`로 조절 |
| `git.renameSimilarityThreshold` | `50` | deletion/addition을 rename으로 볼 유사도 threshold. `(`, `)`로 조절 |

pager 예:

```yaml
git:
  pagers:
    - pager: delta --dark --paging=never
    - colorArg: never
      pager: ydiff -p cat -s --wrap --width={{columnWidth}}
    - externalDiffCommand: difft --color=always
```

각 pager entry의 필드:

| 필드 | 의미 |
|---|---|
| `pager` | `git diff` 출력을 후처리할 command. 예: `delta`, `diff-so-fancy`, `ydiff` |
| `colorArg` | `git diff --color` 값을 `always` 또는 `never`로 조정 |
| `externalDiffCommand` | diff 전체를 직접 처리하는 external diff command. 예: `difftastic` |
| `useExternalDiffGitConfig` | Git의 `diff.external` 설정 사용 |

여러 pager를 등록하면 lazygit 안에서 `|` 키로 순환한다.

### Commit

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `git.commit.signOff` | `false` | commit 시 `--signoff` 사용 |
| `git.commit.autoWrapCommitMessage` | `true` | commit message 입력 중 자동 wrapping |
| `git.commit.autoWrapWidth` | `72` | commit message wrap 폭 |
| `git.skipHookPrefix` | `WIP` | commit message가 해당 prefix로 시작하면 hook skip |
| `git.commitPrefix` | `[]` | branch 이름에서 commit message prefix 자동 생성 |
| `git.commitPrefixes` | `{}` | repo별 commit prefix rule |

`commitPrefix` 예:

```yaml
git:
  commitPrefix:
    - pattern: "^\\w+\\/(\\w+-\\w+).*"
      replace: '[$1] '
```

branch `feature/AB-123`에서 commit message prefix `[AB-123] `를 만들 수 있다.

### Merge와 rebase 보조

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `git.merging.manualCommit` | `false` | merge commit message가 필요한 경우 subprocess로 merge 실행 |
| `git.merging.args` | `""` | `git merge`에 추가 arg 전달. 예: `--no-ff` |
| `git.merging.squashMergeMessage` | `Squash merge {{selectedRef}} into {{currentBranch}}` | squash merge commit message template |
| `git.autoStageResolvedConflicts` | `true` | conflict가 해결된 파일 자동 stage 및 merge/rebase continue 제안 |

### Branch와 fetch/refresh

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `git.mainBranches` | `master`, `main` | main branch로 취급할 branch 목록 |
| `git.autoFetch` | `true` | 주기적으로 remote fetch |
| `git.autoRefresh` | `true` | 파일/submodule 상태 주기 refresh |
| `git.autoForwardBranches` | `onlyMainBranches` | fetch 후 local branch 자동 fast-forward. `none`, `onlyMainBranches`, `allBranches` |
| `git.fetchAll` | `true` | fetch 시 `--all` 사용 |
| `git.localBranchSortOrder` | `date` | local branch 정렬. `date`, `recency`, `alphabetical` |
| `git.remoteBranchSortOrder` | `date` | remote branch 정렬. `date`, `alphabetical` |
| `git.branchPrefix` | `""` | 새 branch 생성 시 prefix |

동적 branch prefix 예:

```yaml
git:
  branchPrefix: "firstlast/{{ runCommand "date +\"%Y/%-m\"" }}/"
```

### Log 표시

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `git.branchLogCmd` | `git log --graph ... {{branchName}} --` | 선택 branch log를 main window에 보여주는 command |
| `git.allBranchesLogCmds` | `git log --graph --all ...` | all branches log command 목록 |
| `git.log.order` | `topo-order` | commit log 정렬. `date-order`, `author-date-order`, `topo-order`, `default` |
| `git.log.showGraph` | `always` | commit graph 표시. `always`, `never`, `when-maximised` |
| `git.log.showWholeGraph` | `false` | 전체 graph 기본 표시 여부 |
| `git.truncateCopiedCommitHashesTo` | `12` | clipboard 복사 commit hash 길이. `40`이면 줄이지 않음 |

`git.branchLogCmd`는 원하는 `git log` 형식으로 바꿀 수 있다.

### 기타 Git 안전 옵션

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `git.overrideGpg` | `false` | GPG 사용 시 별도 process spawn을 막음 |
| `git.disableForcePushing` | `false` | force push 금지 |
| `git.parseEmoji` | `false` | commit message의 `:rocket:` 같은 emoji string rendering |

## `update`와 `refresher`

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `update.method` | `prompt` | update check 방식. `prompt`, `background`, `never` |
| `update.days` | `14` | update check 주기 |
| `refresher.refreshInterval` | `10` | file/submodule refresh 간격(초) |
| `refresher.fetchInterval` | `60` | fetch 간격(초) |

`refresher`는 `git.autoRefresh`, `git.autoFetch`가 켜져 있을 때 의미가 있다.

## `os`: 외부 editor, file open, clipboard, shell

### 파일 열기와 편집

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `os.edit` | `""` | file 편집 command. `{{filename}}` 포함 필요 |
| `os.editAtLine` | `""` | 특정 line으로 file 편집. `{{filename}}`, 선택적으로 `{{line}}` |
| `os.editAtLineAndWait` | `""` | 편집 종료까지 기다리는 line 편집 command |
| `os.editInTerminal` | `false` | editor 실행 중 lazygit을 suspend할지 |
| `os.openDirInEditor` | `""` | directory를 editor로 여는 command |
| `os.editPreset` | `""` | editor preset |
| `os.open` | `""` | file을 OS 기본 app으로 여는 command |
| `os.openLink` | `""` | URL link를 여는 command |

`o`는 OS 기본 앱으로 열기, `e`는 editor로 편집하기에 해당한다.

지원 editor preset:
- `vim`
- `nvim`
- `nvim-remote`
- `lvim`
- `emacs`
- `nano`
- `micro`
- `vscode`
- `sublime`
- `bbedit`
- `kakoune`
- `helix`
- `xcode`
- `zed`
- `acme`

예:

```yaml
os:
  editPreset: 'vscode'
```

직접 command를 지정하는 예:

```yaml
os:
  edit: 'myeditor {{filename}}'
  editAtLine: 'myeditor --line={{line}} {{filename}}'
  editAtLineAndWait: 'myeditor --block --line={{line}} {{filename}}'
  editInTerminal: true
  openDirInEditor: 'myeditor {{dir}}'
```

플랫폼별 기본 `open` 예:

```yaml
# Windows
os:
  open: 'start "" {{filename}}'

# Linux
os:
  open: 'xdg-open {{filename}} >/dev/null'

# macOS
os:
  open: 'open {{filename}}'
```

### Clipboard

| 설정 | 기본값 | 의미 |
|---|---:|---|
| `os.copyToClipboardCmd` | `""` | clipboard 복사 command. `{{text}}` 사용 |
| `os.readFromClipboardCmd` | `""` | clipboard 읽기 command. stdout으로 clipboard content 출력 |

OSC52 terminal clipboard를 쓰는 예:

```yaml
os:
  copyToClipboardCmd: printf "\033]52;c;$(printf {{text}} | base64 -w 0)\a" > /dev/tty
```

tmux에서는 escape sequence wrapper가 필요하다.

### Shell aliases/functions

`:` 키는 lazygit 안에서 shell command prompt를 연다. 여기서 shell alias/function을 쓰고 싶으면 별도 파일을 지정한다.

```yaml
os:
  shellFunctionsFile: ~/.my_aliases.sh
```

zsh alias는 직접 사용할 수 없고 function으로 바꿔야 한다. 이 파일은 `:` prompt뿐 아니라 custom command와 editor open에도 사용된다.

## `customCommands`: 사용자 정의 명령

`customCommands`는 `config.yml`에 정의하는 사용자 명령 목록이다. 특정 context에서 특정 key를 누르면 shell command를 실행할 수 있다.

기본 구조:

```yaml
customCommands:
  - key: '<c-r>'
    context: 'commits'
    command: 'hub browse -- "commit/{{.SelectedLocalCommit.Hash}}"'
```

주요 필드:

| 필드 | 필수 | 의미 |
|---|---|---|
| `key` | 아니오 | 실행 key. 없으면 `?` keybindings menu에서 선택 가능 |
| `command` | 예 | 실행할 command. Go template 사용 |
| `context` | 예 | 어느 view/context에서 동작할지 |
| `prompts` | 아니오 | 실행 전 사용자 입력 prompt |
| `loadingText` | 아니오 | 실행 중 표시할 text |
| `description` | 아니오 | keybindings menu에 보일 label |
| `output` | 아니오 | 출력 위치. `none`, `terminal`, `log`, `logWithPty`, `popup` |
| `outputTitle` | 아니오 | popup title |
| `after` | 아니오 | 실행 후 후속 작업. 예: conflict check |

지원 context:

| context | 의미 |
|---|---|
| `status` | Status tab |
| `files` | Files tab |
| `worktrees` | Worktrees tab |
| `submodules` | Submodules tab |
| `localBranches` | Local Branches tab |
| `remotes` | Remotes tab |
| `remoteBranches` | remote 안으로 들어간 branch context |
| `tags` | Tags tab |
| `commits` | Commits tab |
| `reflogCommits` | Reflog tab |
| `subCommits` | branch 안으로 들어갔을 때 commit context |
| `commitFiles` | commit/stash entry 안의 files context |
| `stash` | Stash tab |
| `global` | 어디서든 동작 |

prompt type:
- `input`
- `confirm`
- `menu`
- `menuFromCommand`

placeholder로 접근 가능한 주요 object:
- `SelectedCommit`
- `SelectedCommitRange`
- `SelectedFile`
- `SelectedPath`
- `SelectedSubmodule`
- `SelectedLocalBranch`
- `SelectedRemoteBranch`
- `SelectedRemote`
- `SelectedTag`
- `SelectedStashEntry`
- `SelectedCommitFile`
- `SelectedWorktree`
- `CheckedOutBranch`

함수:
- `quote`: OS에 맞게 shell quoting
- `runCommand`: command 실행 후 단일 line output 사용

debugging tip:

```yaml
output: popup
command: "echo ..."
```

실제 command 대신 `echo`로 감싸면 placeholder가 어떻게 해석되는지 popup으로 확인할 수 있다.

## `services`: Git hosting service URL

사내 GitLab처럼 Git clone domain과 web/API domain이 다른 경우 `services`로 mapping한다.

```yaml
services:
  '<gitDomain>': '<provider>:<webDomain>'
```

지원 provider:
- `github`
- `bitbucket`
- `bitbucketServer`
- `azuredevops`
- `gitlab`
- `gitea`
- `codeberg`

## `notARepository`

Git repo가 아닌 위치에서 lazygit을 실행했을 때 동작을 정한다.

| 값 | 동작 |
|---|---|
| `prompt` | 기본값. repo 초기화 또는 최근 repo 열기 여부를 물음 |
| `create` | 묻지 않고 새 repo 초기화 |
| `skip` | repo 생성 없이 최근 repo 열기 |
| `quit` | 즉시 종료 |

## `keybinding`: 기본 키 override

기본 keybinding은 `Config.md`의 `keybinding` 섹션에 설정 키 이름으로 정리되어 있고, 사용자에게 보이는 표는 `docs/keybindings/Keybindings_*.md`에 있다.

비활성화 예:

```yaml
keybinding:
  universal:
    edit: <disabled>
```

Colemak 사용자 예시처럼 여러 key를 재배치할 수도 있다.

```yaml
keybinding:
  universal:
    prevItem-alt: 'u'
    nextItem-alt: 'e'
    undo: 'l'
    redo: '<c-r>'
  files:
    ignoreFile: 'I'
```

가능한 특수 key 표기는 `docs/keybindings/Custom_Keybindings.md`에 있다.

## 자주 바꿀 만한 설정 조합

### VS Code를 editor로 사용

```yaml
os:
  editPreset: vscode
```

### Nerd Font icon 표시

```yaml
gui:
  nerdFontsVersion: "3"
```

### delta pager 사용

```yaml
git:
  pagers:
    - pager: delta --dark --paging=never
```

### fuzzy filtering 사용

```yaml
gui:
  filterMode: fuzzy
```

### 자동 fetch 끄기

```yaml
git:
  autoFetch: false
```

### force push 금지

```yaml
git:
  disableForcePushing: true
```

### repo 밖에서 실행하면 바로 종료

```yaml
notARepository: quit
```

## 확인한 주의점

- `Config.md`의 기본 YAML은 자동 생성 영역이다. 문서는 전체 복붙보다 바꾸고 싶은 설정만 `config.yml`에 쓰는 것을 권장한다.
- `keybinding`의 내부 설정 이름과 `Keybindings_en.md`의 사용자 표시 action 이름은 1:1로 완전히 같은 문자열이 아니다. 예를 들어 `keybinding.universal.cyclePagers`는 사용자 문서에서 `Cycle pagers`로 보인다.
- custom keybinding이 같은 context의 built-in keybinding과 충돌하면 custom keybinding이 실행된다. 단, global custom keybinding과 더 구체적인 context built-in keybinding이 충돌하면 구체적인 context built-in이 우선한다.
