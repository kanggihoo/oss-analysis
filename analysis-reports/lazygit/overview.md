# lazygit 문서 중심 사용자 관점 분석

분석 기준:
- 실제 소스/테스트 코드보다 `README.md`, `docs/`, `CONTRIBUTING.md`, `VISION.md` 등 문서와 Markdown 파일을 우선 확인했다.
- `docs-master/`는 릴리스용 문서 원본/복사본 성격으로 보이며, 파일 구성은 `docs/`와 동일했다. 사용자 관점 설명은 `docs/`를 기준으로 한다.
- `docs/keybindings/Keybindings_ko.md`는 로컬 터미널 출력에서 인코딩이 깨져 보여, 단축키 근거는 `docs/keybindings/Keybindings_en.md`와 `docs/Config.md`의 자동 생성 keybinding 설정을 기준으로 해석했다.

## 1. 이 프로젝트의 목적

lazygit은 Git CLI를 직접 조합하지 않아도 터미널 안에서 Git 작업을 빠르게 처리할 수 있게 해주는 TUI 애플리케이션이다. `README.md`의 설명과 기능 목록을 보면 핵심 목표는 "Git은 강력하지만 일상 작업은 번거롭다"는 문제를 줄이는 것이다. 사용자는 `lazygit`을 Git 저장소 안에서 실행하고, 파일/브랜치/커밋/stash/remote/submodule/worktree 같은 Git 객체를 패널 단위로 보면서 키보드 중심으로 조작한다.

문서상 제품 방향은 `VISION.md`에 명확하다. lazygit은 "가장 즐거운 Git UI"를 지향하며, 발견 가능성, 단순함, 안전성, 파워 유저 기능, 속도, Git과의 일관성을 설계 원칙으로 둔다. 그래서 단순 작업은 키 하나로 처리하고, 위험한 작업은 확인 팝업을 두며, 복잡한 작업은 메뉴/커스텀 명령/설정으로 확장하는 구조다.

근거:
- `README.md`: Elevator Pitch, Features, Usage
- `VISION.md`: Vision and Design Principles
- `docs/README.md`: 사용자 문서 목차

## 2. 프로젝트 유형과 사용 방식

프로젝트 유형은 Go로 작성된 터미널 기반 Git 애플리케이션이다. 저장소는 `main.go`, `go.mod`, `Makefile`, `justfile`을 갖고 있으며, 실행 단위는 `lazygit` CLI/TUI다. 사용자는 Git 저장소 안에서 다음처럼 실행한다.

```sh
lazygit
```

자주 쓰는 alias로 `lg='lazygit'`를 등록하는 사용법도 README에 제시되어 있다. lazygit 안에서 다른 저장소로 이동한 뒤 종료 시 현재 쉘 디렉터리도 바꾸고 싶다면 `LAZYGIT_NEW_DIR_FILE`을 사용하는 쉘 함수 예제가 제공된다. 일반 종료는 `q`, lazygit 안에서 이동한 디렉터리 변경을 반영하지 않는 종료는 `Shift+Q`로 안내된다.

설치 방식은 매우 다양하다.
- 바이너리 릴리스: Windows, macOS, Linux용 릴리스 다운로드
- macOS/Linux: Homebrew `brew install lazygit`
- Windows: Scoop, Chocolatey, Winget
- Debian/Ubuntu 최신 배포판: `sudo apt install lazygit`
- Go: `go install github.com/jesseduffield/lazygit@latest`
- 직접 빌드: 저장소 clone 후 `go install`
- Nix, Conda, FreeBSD, Termux 등

근거:
- `README.md`: Installation, Usage, Changing Directory On Exit
- `go.mod`: Go 모듈 및 의존성
- `Makefile`, `justfile`: 개발용 실행/빌드 명령

## 3. 핵심 기능

사용자 문서 기준 핵심 기능은 다음과 같다.

### 파일 변경 관리

Files 패널에서 `Space`로 선택 파일의 staged 상태를 토글하고, `a`로 전체 파일을 stage/unstage할 수 있다. 파일을 선택한 상태에서 `Enter`를 누르면 staging view로 들어가 hunk/line 단위 staging을 할 수 있다. staging view에서는 `Space`로 줄 또는 hunk를 stage/unstage하고, `a`로 line-by-line/hunk selection 모드를 전환한다. `d`는 선택 변경을 discard하거나 staged 변경을 unstage한다.

관련 단축키:
- `Space`: 파일 stage 토글
- `a`: 전체 파일 stage/unstage
- `Enter`: 파일의 hunk/line staging view 진입
- staging view의 `Space`: 선택 줄/hunk stage
- staging view의 `d`: 변경 discard 또는 unstage
- `c`: staged 변경 commit
- `w`: pre-commit hook 없이 commit
- `C`: Git editor를 사용해 commit
- `A`: 마지막 commit amend

근거:
- `README.md`: Stage individual lines
- `docs/keybindings/Keybindings_en.md`: Files, Main panel (staging)

### 브랜치/remote 관리

Local branches 패널에서는 브랜치 checkout, 새 브랜치 생성, rebase, merge, rename, upstream 설정, Git-flow 옵션, PR 생성/열기 등을 수행한다. remote와 remote branch 패널에서는 fetch, remote 추가/수정/삭제, remote branch checkout, upstream 설정 등이 가능하다.

관련 단축키:
- 브랜치 `Space`: checkout
- `n`: 새 브랜치
- `c`: 이름으로 checkout, 입력값 `-`로 이전 브랜치 전환 가능
- `-`: 이전 브랜치 checkout
- `F`: 강제 checkout
- `r`: 현재 브랜치를 선택 브랜치 위로 rebase
- `M`: 선택 브랜치를 현재 브랜치로 merge/squash merge 메뉴
- `u`: upstream 옵션
- `i`: Git-flow 옵션
- remote `f`: fetch
- remote `F`: fork remote 추가

근거:
- `docs/keybindings/Keybindings_en.md`: Local branches, Remote branches, Remotes
- `README.md`: Git flow support, Show GitHub pull requests

### 커밋 조작과 interactive rebase

Commits 패널은 lazygit의 강한 영역이다. `i`로 interactive rebase를 시작하고, rebase TODO 안에서 squash/fixup/drop/edit/pick/move를 키로 조작한다. 이미 rebase 모드가 아니어도 특정 커밋에서 단발성 squash/fixup/drop/amend 같은 작업을 실행하면 lazygit이 내부적으로 rebase를 수행한다.

관련 단축키:
- `i`: interactive rebase 시작
- `s`: 선택 커밋을 아래 커밋으로 squash
- `f`: 선택 커밋을 아래 커밋으로 fixup
- `d`: 선택 커밋 drop
- `e`: 선택 커밋 edit, 또는 선택 커밋부터 rebase 시작
- `p`: rebase 중 pick 표시
- `Ctrl+j` / `Ctrl+k`: 커밋 아래/위로 이동
- `r`: commit message reword
- `R`: editor로 reword
- `A`: staged 변경을 선택 커밋에 amend
- `a`: author/co-author 조정
- `t`: revert commit 생성
- `T`: tag 생성
- `g`: reset 옵션
- `m`: merge/rebase 중 abort/continue/skip 옵션 메뉴

근거:
- `README.md`: Interactive Rebase, Amend an old commit
- `docs/keybindings/Keybindings_en.md`: Commits, Global keybindings

### Cherry-pick과 commit range 작업

커밋을 `C`로 복사하고 local commits view에서 `V`로 붙여넣으면 cherry-pick한다. range select와 함께 쓰면 여러 커밋을 한 번에 복사/적용할 수 있다. 선택 해제는 `Esc` 또는 `Ctrl+r`로 가능하다.

관련 단축키:
- `C`: cherry-pick 대상으로 commit copy
- `V`: copied commit paste/cherry-pick
- `Ctrl+r`: cherry-pick 선택 초기화
- `v`: sticky range select 토글
- `Shift+Up` / `Shift+Down`: non-sticky range 확장

근거:
- `README.md`: Cherry-pick
- `docs/Range_Select.md`
- `docs/keybindings/Keybindings_en.md`: Commits, List panel navigation

### Stash, worktree, submodule, tag

Stash 패널에서는 stash apply/pop/drop/rename/new branch가 가능하다. Worktrees 패널에서는 worktree 생성, 전환, editor 열기, 제거가 가능하다. Branches 패널에서도 `w`로 worktree 옵션을 열 수 있고, README는 선택 브랜치에서 worktree를 만들고 전환하는 흐름을 소개한다.

Submodules 패널은 submodule enter/update/init/remove/bulk options를 제공한다. Tags 패널은 tag checkout, 생성, 삭제, push, reset 옵션을 제공한다.

근거:
- `README.md`: Worktrees
- `docs/keybindings/Keybindings_en.md`: Stash, Worktrees, Submodules, Tags

### Diff, custom patch, custom pager

main panel과 commit file view에서 diff를 확인하고, `Ctrl+t`로 외부 difftool을 열 수 있다. `W` 또는 `Ctrl+e`는 두 ref/commit을 비교하는 diffing 메뉴를 연다. README의 "Rebase magic"은 오래된 커밋의 일부 줄만 custom patch에 담고, 그 patch를 현재 커밋에서 제거하거나 index에 반대로 적용하는 식의 고급 흐름을 소개한다.

custom pager는 `config.yml`의 `git.pagers` 배열로 설정한다. `delta`, `diff-so-fancy`, `ydiff`, `difftastic` 같은 도구를 사용할 수 있고, 여러 pager를 등록하면 `|`로 순환한다. Windows는 네이티브 지원에 제한이 있어 PowerShell 스크립트로 external diff command를 흉내내는 우회 예제가 제공된다.

근거:
- `README.md`: Rebase magic, Compare two commits
- `docs/Custom_Pagers.md`
- `docs/keybindings/Keybindings_en.md`: Global keybindings, Commit files, Main panel

### 검색과 필터링

대부분의 view에서 `/`는 현재 view의 검색 또는 필터 prompt를 연다. 문서상 filtering은 결과를 줄이고, searching은 항목을 그대로 둔 채 매치를 highlight하고 `n`/`N`으로 이동한다. Files view는 `Ctrl+b`로 staged/unstaged 상태 필터링이 가능하다. Commits view는 파일 경로 기준 필터링을 지원하며, 실행 시 `lazygit -f my/path`를 쓰거나 내부에서 `Ctrl+s` 후 경로를 입력한다.

근거:
- `docs/Searching.md`
- `docs/Config.md`: Filtering
- `docs/keybindings/Keybindings_en.md`: Global keybindings, Files

### Undo/Redo

`z`는 undo, `Z`는 redo다. lazygit의 undo/redo는 reflog를 읽어 이전 Git 상태로 되돌리는 방식이다. lazygit 내부에서 한 작업뿐 아니라 CLI에서 직접 수행한 reflog 기반 작업도 되돌릴 수 있다. 단, working tree 변경, stash 변경, push 같은 원격 변경, branch 생성처럼 reflog에 충분히 남지 않는 작업은 되돌릴 수 없다. rebase 중에는 reflog 정보가 충분하지 않아 undo/redo가 지원되지 않으며, rebase를 빠져나가려면 `m` 메뉴에서 abort를 쓰는 것이 권장된다.

주의: `README.md`와 `docs/keybindings/Keybindings_en.md`는 redo를 `Shift+Z`/`Z`로 설명한다. `docs/Undoing.md` 첫 줄에는 redo가 `ctrl+z`라고 되어 있어 문서 간 충돌이 있다. 실제 자동 생성 keybinding 문서와 config 기본값은 `redo: Z`다.

근거:
- `README.md`: Undo
- `docs/Undoing.md`
- `docs/keybindings/Keybindings_en.md`: Global keybindings
- `docs/Config.md`: keybinding.universal.redo

### GitHub pull request 연동

Branches 패널에서 branch와 연결된 GitHub PR을 아이콘과 색으로 보여줄 수 있고, `G`로 브라우저에서 PR을 연다. github.com은 별도 lazygit 설정 없이 동작하지만 `gh` CLI 설치와 `gh auth login`이 필요하다. GitHub Enterprise는 `gh auth login --hostname <webDomain>`과 `services` 설정이 필요하다.

근거:
- `README.md`: Show GitHub pull requests
- `docs/Config.md`: Custom pull request URLs

## 4. 실행/사용 진입점

사용자 진입점:
- `lazygit`: Git 저장소 안에서 TUI 실행
- `lazygit -f <path>`: 특정 파일 경로와 관련된 commit만 필터링해서 보기
- `lazygit --debug`: debug 모드 실행
- `lazygit --logs`: lazygit 로그 tail 보기
- `lazygit --use-config-file=<file>` 또는 `LG_CONFIG_FILE=<file>`: 설정 파일 위치/목록 지정

TUI 내부 진입점:
- `?`: keybindings 메뉴
- `:`: shell command prompt
- `e` on Status panel: config 파일 편집
- `o` on Status panel: config 파일 열기
- `q`: 종료
- `Esc`: 취소/상위 context 복귀
- `Tab`: view 전환
- `0`: main view focus
- `1`-`5`: 주요 window jump

개발자 진입점:
- `go run main.go`
- `make run`, `just run`
- `go run main.go -debug`
- `go run main.go --logs`
- `make unit-test`, `just unit-test`
- `go run cmd/integration_test/main.go tui`
- `go run cmd/integration_test/main.go cli ...`

근거:
- `README.md`: Usage, Debugging Locally
- `docs/Searching.md`
- `docs/Config.md`: Overriding default config file location
- `CONTRIBUTING.md`: Debugging
- `Makefile`, `justfile`

## 5. 주요 모듈과 책임

사용자 문서 중심 요청이므로 코드 내부는 깊게 보지 않았지만, `docs/dev/Codebase_Guide.md`가 contributor에게 필요한 큰 구조를 설명한다.

- `pkg/app`: 시작 코드, logging/user config 초기화, GUI 시작, 일부 error handling
- `pkg/app/daemon`: interactive rebase TODO 설정처럼 Git에 넘겨주는 짧은 백그라운드 프로세스
- `pkg/cheatsheet`: `docs/keybindings` cheatsheet 생성
- `pkg/commands/git_commands`: Git 바이너리 호출
- `pkg/commands/oscommands`: OS 명령 호출
- `pkg/commands/git_config`: Git config 읽기
- `pkg/commands/hosting_service`: Git hosting service/forge 연동
- `pkg/commands/models`: commit, branch, file 등 Git 객체 모델
- `pkg/commands/patch`: Git patch parsing/처리
- `pkg/config`: lazygit user config 구조와 기본값
- `pkg/i18n`: 다국어 문자열
- `pkg/integration`: E2E/integration tests
- `pkg/logs`: logger 및 `lazygit --logs`
- `pkg/tasks`: 비동기 task 실행
- `pkg/theme`: 색상 theme
- `pkg/updates`: update 확인/다운로드/설치
- `pkg/gui`: GUI 전반
- `pkg/gui/context`: 각 view별 context와 상태
- `pkg/gui/controllers`: keybinding과 handler 연결
- `pkg/gui/mergeconflicts`: merge conflict 처리
- `pkg/gui/services/custom_commands`: 사용자 정의 custom commands
- `vendor/github.com/jesseduffield/gocui`: underlying TUI event loop, keypress, rendering

근거:
- `docs/dev/Codebase_Guide.md`

## 6. 핵심 개념과 용어

문서상 중요한 개념은 다음과 같다.

- View: 화면에 렌더링되는 내용 buffer. gocui의 View를 기반으로 한다.
- Context: 특정 view에 붙은 상태와 로직. 예: branches context.
- Controller: keybinding과 handler 목록. 여러 context에 붙을 수 있다.
- Helper: controller 간 공유 로직.
- Window: 화면의 특정 영역. 기본 view 이름을 따서 부른다.
- Panel: 과거 용어이며 view/window를 가리키는 경우가 있다.
- Tab: window 안에서 전환되는 view.
- Model: commit, branch, file 같은 Git 객체 표현.
- ViewModel: context가 view 상태를 유지하기 위한 모델.
- Keybinding: key와 action의 연결.
- Action: key를 눌렀을 때 실행되는 작업. Git 명령일 수도 있고 navigation일 수도 있다.
- Common struct: logger, i18n, config 같은 공통 의존성을 담는 구조.

사용자 관점 핵심 용어:
- Staging view: 파일 변경을 hunk/line 단위로 stage/unstage하는 main panel 상태
- Range select: 여러 파일/커밋 등 연속 범위 선택
- Custom patch: 과거 커밋 일부 변경을 patch로 선택해 rebase 작업에 활용하는 기능
- Fixup commit: `fixup!`/`amend!` prefix를 가진 review 대응용 커밋
- Marked base commit: `git rebase --onto` 흐름에서 기준 커밋으로 표시한 커밋
- Pager: diff 출력을 후처리/렌더링하는 외부 도구
- Custom command: 사용자가 `config.yml`에 정의하는 lazygit 내부 단축키 명령

근거:
- `docs/dev/Codebase_Guide.md`
- `docs/Range_Select.md`
- `docs/Fixup_Commits.md`
- `docs/Custom_Command_Keybindings.md`
- `docs/Custom_Pagers.md`

## 7. 입력/데이터/상태/제어 흐름

사용자 관점의 기본 흐름:

1. 사용자가 Git 저장소에서 `lazygit` 실행
2. lazygit이 Git 상태를 읽고 side panels에 files/branches/commits/stash/remotes 등을 표시
3. 사용자가 현재 focus된 view에서 단축키를 입력
4. context/controller가 해당 action을 실행
5. action은 필요 시 Git 명령 또는 OS 명령을 실행
6. 상태 refresh 후 view가 다시 렌더링

주요 상태 흐름:
- `R`: Git 상태 refresh. `git status`, `git branch` 등을 백그라운드로 다시 읽지만 fetch는 하지 않는다.
- `git.autoFetch`: 기본 true, 주기적으로 remote fetch
- `git.autoRefresh`: 기본 true, 파일/submodule 상태 주기 refresh
- `refresher.refreshInterval`: 기본 10초
- `refresher.fetchInterval`: 기본 60초
- config는 실행 중 reload될 수 있으며, 대부분 controller/helper는 `common.Common`의 최신 UserConfig를 참조한다.

제어 흐름 예시:
- commit 작성: Files view에서 stage -> `c` -> commit message 입력 -> Git commit 실행 -> 상태 refresh
- line staging: file 선택 -> `Enter` -> staging view -> hunk/line 선택 -> `Space`
- interactive rebase: Commits view -> `i` 또는 `e` -> commit action 지정 -> `m` 메뉴에서 continue/abort/skip
- custom command: config의 context/key와 매칭 -> prompts 실행 -> template placeholder 해석 -> command 실행 -> output 정책에 따라 terminal/log/popup 표시
- undo/redo: `z`/`Z` -> reflog 읽기 -> 이전/다음 commit/branch 상태로 이동

근거:
- `docs/keybindings/Keybindings_en.md`
- `docs/Config.md`
- `docs/Custom_Command_Keybindings.md`
- `docs/Undoing.md`
- `docs/dev/Codebase_Guide.md`

## 8. 설정 및 환경 구성

기본 global config 경로:
- Linux: `~/.config/lazygit/config.yml`
- macOS: `~/Library/Application Support/lazygit/config.yml`
- Windows: `%LOCALAPPDATA%\lazygit\config.yml`, 또한 `%APPDATA%\lazygit\config.yml`도 탐색

구버전 경로:
- Linux: `~/.config/jesseduffield/lazygit/config.yml`
- macOS: `~/Library/Application Support/jesseduffield/lazygit/config.yml`
- Windows: `%APPDATA%\jesseduffield\lazygit\config.yml`

repo-specific config:
- `<repo>/.git/lazygit.yml`: global config override
- repo 상위 디렉터리의 `.lazygit.yml`: 여러 저장소에 공통 설정 적용 가능

설정 파일 위치 override:
- `CONFIG_DIR="$HOME/.config/lazygit"`
- `lazygit --use-config-file="$HOME/.base_lg_conf,$HOME/.light_theme_lg_conf"`
- `LG_CONFIG_FILE="$HOME/.base_lg_conf,$HOME/.light_theme_lg_conf" lazygit`

주요 설정 영역:
- `gui`: UI 폭/분할, mouse events, language, theme, file tree, icons, commit author 표시 등
- `git`: pagers, commit wrapping, merge args, main branches, autoFetch, autoRefresh, branch sorting, diff context, rename threshold 등
- `update`: update check 방식과 주기
- `refresher`: refresh/fetch interval
- `os`: editor/open/clipboard/shell command 관련 설정
- `customCommands`: 사용자 custom command 목록
- `services`: PR URL/provider mapping
- `notARepository`: Git 저장소 밖에서 실행했을 때 동작
- `keybinding`: 기본 단축키 override/disable

편집기 설정:
- `os.editPreset`으로 `vim`, `nvim`, `nvim-remote`, `emacs`, `nano`, `micro`, `vscode`, `sublime`, `helix`, `zed` 등 지정 가능
- 개별 command를 직접 지정하려면 `os.edit`, `os.editAtLine`, `os.editAtLineAndWait`, `os.editInTerminal`, `os.openDirInEditor` 사용

shell command prompt:
- `:`로 lazygit 안에서 shell command 실행
- alias/function을 쓰려면 `os.shellFunctionsFile` 지정

keybinding 설정:
- `keybinding` 아래에서 기본 단축키를 바꿀 수 있다.
- 특정 keybinding은 `<disabled>`로 비활성화 가능하다.
- 가능한 키 표기는 `docs/keybindings/Custom_Keybindings.md`에 정리되어 있다.

근거:
- `docs/Config.md`
- `docs/keybindings/Custom_Keybindings.md`

## 9. 의존성 구조

문서와 메타데이터 기준 의존성:
- Go 모듈: `github.com/jesseduffield/lazygit`
- TUI 렌더링/키 이벤트: vendored `gocui`, 그리고 `github.com/gdamore/tcell/v3`
- CLI arg parsing: `github.com/integrii/flaggy`
- GitHub 연동: `github.com/cli/go-gh/v2`, 외부 `gh` CLI 필요
- config/data: `gopkg.in/yaml.v3`, JSON schema generator 관련 의존성
- fuzzy/search: `github.com/sahilm/fuzzy`, `gopkg.in/ozeidan/fuzzy-patricia.v3`
- clipboard: `github.com/atotto/clipboard`
- update/logging/theme/utils 관련 여러 Go 의존성

사용자가 설치하면 유용한 외부 도구:
- `gh`: GitHub PR 표시/열기
- `delta`, `diff-so-fancy`, `ydiff`, `difftastic`: custom pager/diff
- 사용자의 editor: vim/nvim/vscode/helix 등
- Nerd Fonts: 파일/브랜치 아이콘 표시

근거:
- `go.mod`
- `README.md`: Show GitHub pull requests
- `docs/Custom_Pagers.md`
- `docs/Config.md`: Display Nerd Fonts Icons, Configuring File Editing

## 10. 빌드/실행/테스트 방식

사용자 실행:
- 설치 후 Git repo에서 `lazygit`
- 버전 확인: `lazygit --version`

개발 실행:
- `go run main.go`
- `make run` 또는 `just run`
- debug/log 확인: 한 터미널에서 `go run main.go -debug`, 다른 터미널에서 `go run main.go --logs` 또는 `lazygit --logs`
- 로그 레벨: `LOG_LEVEL=warn go run main.go -debug`

빌드/설치:
- `go install`
- `make build`, `just build`
- `nix build`, `nix run`, `nix develop`

테스트:
- unit test: `go test ./... -short`, `make unit-test`, `just unit-test`
- integration test TUI: `go run cmd/integration_test/main.go tui`
- integration test CLI: `go run cmd/integration_test/main.go cli [--slow or --sandbox] [testname or testpath...]`
- CI/headless integration: `go test pkg/integration/clients/*.go`
- generated files: `go generate ./...`
- formatting: `gofumpt`
- lint: `./scripts/golangci-lint-shim.sh run`

근거:
- `README.md`: Installation, Debugging Locally
- `CONTRIBUTING.md`: Running, Debugging, Testing
- `pkg/integration/README.md`
- `Makefile`, `justfile`

## 11. 에러 처리와 디버깅 포인트

사용자 관점:
- 위험 작업은 confirmation popup이 붙는 경우가 많다. `VISION.md`는 되돌리기 어려운 작업에 확인을 요구하는 안전 원칙을 명시한다.
- `Esc`는 대부분의 transient situation에서 빠져나오는 키로 설계되어 있다.
- rebase/merge 도중에는 `m` 메뉴에서 abort/continue/skip을 선택한다.
- undo/redo는 reflog 기반이므로 working tree/stash/remote push 등은 복구 범위 밖이다.
- custom command가 의도대로 template을 해석하는지 확인하려면 command를 `echo`로 감싸고 `output: popup`을 사용하라는 debugging 방법이 문서에 있다.

개발자 관점:
- `lazygit --debug`와 `lazygit --logs`를 두 터미널에서 같이 사용한다.
- `LOG_LEVEL=warn`처럼 로그 레벨을 조절할 수 있다.
- `LAZYGIT_LOG_PATH`를 쓰면 vendor/gocui 쪽에서도 global logger로 로그를 남길 수 있다.
- integration test runner는 `--sandbox`로 setup만 재사용하고 사용자가 직접 TUI를 조작할 수 있다.

근거:
- `VISION.md`: Safety
- `README.md`: Debugging Locally
- `docs/Undoing.md`
- `docs/Custom_Command_Keybindings.md`: Debugging
- `CONTRIBUTING.md`: Debugging
- `pkg/integration/README.md`

## 12. 확장하거나 기여할 때 봐야 할 구조

현재 `CONTRIBUTING.md`의 최신 정책은 "기본적으로 pull request를 받지 않는다"에 가깝다. 문서상 관리자는 일반 PR을 기본적으로 닫을 수 있으며, 진지하게 기여하려면 먼저 issue를 열고 계획을 설명하며, Go와 lazygit codebase 이해가 충분함을 보여야 한다. 코드 PR이 아니어도 issue, feature request, UX design discussion, 번역 기여는 환영된다.

기여자가 봐야 할 문서:
- `CONTRIBUTING.md`: 최신 기여 정책, 개발 환경, 디버깅, 테스트
- `VISION.md`: 기능 설계 판단 기준
- `docs/dev/Codebase_Guide.md`: package 구조와 핵심 개념
- `docs/dev/README.md`: dev docs index
- `pkg/integration/README.md`: integration test 작성/실행 방식
- `pkg/i18n/translations/README.md`: Crowdin 번역 sync 방식
- `docs/Fixup_Commits.md`: 프로젝트가 선호하는 review 중 fixup commit 흐름

확장 포인트:
- 새 사용자 설정: `pkg/config/user_config.go`와 JSON schema/docs generation 구조
- 새 keybinding/action: controller/context/keybinding 구조
- custom command 관련 기능: `pkg/gui/services/custom_commands`
- 새 사용자-facing 문구: `pkg/i18n/english.go`와 번역 관리
- UI 렌더링/패널: `pkg/gui`, context/controller/helper 구조
- Git 조작: `pkg/commands/git_commands`

근거:
- `CONTRIBUTING.md`
- `VISION.md`
- `docs/dev/Codebase_Guide.md`
- `pkg/integration/README.md`
- `pkg/i18n/translations/README.md`

## 13. 처음 기여자가 먼저 읽어야 할 파일

사용자로서 먼저 읽을 파일:
1. `README.md`: 설치, 실행, 기능 overview
2. `docs/README.md`: 문서 목차
3. `docs/keybindings/Keybindings_en.md`: 전체 기본 단축키
4. `docs/Config.md`: config 위치와 주요 옵션
5. `docs/Undoing.md`: undo/redo 가능 범위
6. `docs/Searching.md`: 검색/필터링
7. `docs/Range_Select.md`: 여러 항목 선택
8. `docs/Custom_Command_Keybindings.md`: custom commands
9. `docs/Custom_Pagers.md`: diff pager 설정
10. `docs/Fixup_Commits.md`: review 중 fixup/amend workflow
11. `docs/Stacked_Branches.md`: stacked branch workflow

기여자라면 추가로:
1. `CONTRIBUTING.md`
2. `VISION.md`
3. `docs/dev/README.md`
4. `docs/dev/Codebase_Guide.md`
5. `pkg/integration/README.md`
6. `Makefile`, `justfile`
7. `go.mod`

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- `docs/Undoing.md`는 redo를 `ctrl+z`라고 설명하지만, `README.md`, `docs/keybindings/Keybindings_en.md`, `docs/Config.md`의 기본값은 `Z`다. 자동 생성 keybinding 쪽을 신뢰하는 것이 맞아 보이나, 실제 동작은 실행 버전에서 확인하면 더 정확하다.
- `docs/keybindings/Keybindings_ko.md`는 로컬 출력 인코딩이 깨져 한국어 단축키 표기는 사용하지 않았다. 원격 GitHub 렌더링 또는 UTF-8 처리 환경에서는 정상일 수 있다.
- 분석은 사용자 문서 중심으로 수행했기 때문에, 실제 구현이 문서와 100% 일치하는지는 소스 레벨 검증을 하지 않았다.
- `docs-master/`와 `docs/`의 파일 목록은 동일하며 `scripts/update_docs_for_release.sh`가 `docs-master`에서 `docs`로 복사하는 흐름을 보여준다. 각 파일 내용까지 전부 diff하지는 않았다.

