# lazygit 기본 키 정리

근거 문서:
- `lazygit/docs/keybindings/Keybindings_en.md`
- `lazygit/docs/keybindings/Custom_Keybindings.md`
- 보조 근거: `lazygit/docs/Config.md`의 `keybinding` 섹션

## 문서 구성

`docs/keybindings/`에는 다음 파일이 있다.

| 파일 | 역할 |
|---|---|
| `Keybindings_en.md` | 영어 기본 keybinding 문서. 자동 생성 파일이며 가장 안정적인 기준으로 사용했다. |
| `Keybindings_ko.md` | 한국어 keybinding 문서. 로컬 출력에서는 일부 인코딩 문제가 있었지만 파일 자체는 존재한다. |
| `Keybindings_ja.md` | 일본어 keybinding 문서 |
| `Keybindings_nl.md` | 네덜란드어 keybinding 문서 |
| `Keybindings_pl.md` | 폴란드어 keybinding 문서 |
| `Keybindings_pt.md` | 포르투갈어 keybinding 문서 |
| `Keybindings_ru.md` | 러시아어 keybinding 문서 |
| `Keybindings_zh-CN.md` | 중국어 간체 keybinding 문서 |
| `Keybindings_zh-TW.md` | 중국어 번체 keybinding 문서 |
| `Custom_Keybindings.md` | config/custom command에서 쓸 수 있는 key 표기법 |

언어별 `Keybindings_*.md`는 같은 기본 키 구성을 각 언어로 표시하는 문서다. 아래 정리는 `Keybindings_en.md`를 기준으로 한국어 설명을 붙였다.

## 표기 규칙

`Keybindings_en.md`의 legend:

| 표기 | 의미 |
|---|---|
| `<c-b>` | `Ctrl+b` |
| `<a-b>` | `Alt+b` |
| `B` | `Shift+b` |
| `<s-up>` | `Shift+Up` |
| `<space>` | Space |
| `<enter>` | Enter |
| `<esc>` | Escape |
| `<backtab>` | Shift+Tab 계열 |

`Custom_Keybindings.md`에서 확인한 주요 특수 key 표기:

| config 표기 | 실제 key |
|---|---|
| `<f1>` - `<f12>` | Function key |
| `<insert>` | Insert |
| `<delete>` | Delete |
| `<home>` | Home |
| `<end>` | End |
| `<pgup>` | Page Up |
| `<pgdown>` | Page Down |
| `<up>`, `<down>`, `<left>`, `<right>` | 방향키 |
| `<s-up>`, `<s-down>` | Shift+방향키 |
| `<tab>` | Tab |
| `<enter>` | Enter |
| `<a-enter>` | Alt+Enter |
| `<esc>` | Escape |
| `<backspace>` | Backspace |
| `<space>` | Space |
| `<c-a>` 등 | Ctrl 조합 |

## Global keybindings

어느 view에서든 기본적으로 쓰이는 키다.

| Key | 동작 |
|---|---|
| `<c-r>` | 최근 repo로 전환 |
| `<pgup>` / `fn+up` / `Shift+k` | main window 위로 스크롤 |
| `<pgdown>` / `fn+down` / `Shift+j` | main window 아래로 스크롤 |
| `@` | command log options 보기 |
| `P` | 현재 branch push |
| `p` | 현재 branch pull |
| `)` | rename similarity threshold 증가 |
| `(` | rename similarity threshold 감소 |
| `}` | diff context size 증가 |
| `{` | diff context size 감소 |
| `:` | shell command 실행 prompt |
| `<c-p>` | custom patch options 보기 |
| `m` | merge/rebase options 보기. abort/continue/skip 등 |
| `R` | Git 상태 refresh. fetch는 하지 않음 |
| `+` | 다음 screen mode. normal/half/fullscreen |
| `_` | 이전 screen mode |
| `|` | configured pager 순환 |
| `<esc>` | cancel |
| `?` | keybindings menu 열기 |
| `<c-s>` | commit log filter options |
| `W` | diffing options |
| `<c-e>` | diffing options 대체 키 |
| `q` | quit |
| `<c-z>` | app suspend |
| `<c-w>` | diff view whitespace 표시 toggle |
| `z` | undo |
| `Z` | redo |

관련 config key:
- `keybinding.universal.pushFiles: P`
- `keybinding.universal.pullFiles: p`
- `keybinding.universal.refresh: R`
- `keybinding.universal.cyclePagers: '|'`
- `keybinding.universal.undo: z`
- `keybinding.universal.redo: Z`
- `keybinding.universal.executeShellCommand: ':'`
- `keybinding.universal.diffingMenu: W`
- `keybinding.universal.filteringMenu: <c-s>`

## List panel navigation

list 형태 view에서 공통으로 쓰는 이동 키다.

| Key | 동작 |
|---|---|
| `,` | 이전 page |
| `.` | 다음 page |
| `<` 또는 `<home>` | 맨 위로 |
| `>` 또는 `<end>` | 맨 아래로 |
| `v` | range select toggle |
| `<s-down>` | range select 아래로 확장 |
| `<s-up>` | range select 위로 확장 |
| `/` | 현재 view 검색 |
| `H` | 왼쪽 스크롤 |
| `L` | 오른쪽 스크롤 |
| `]` | 다음 tab |
| `[` | 이전 tab |

관련 config key:
- `keybinding.universal.prevPage`
- `keybinding.universal.nextPage`
- `keybinding.universal.gotoTop`
- `keybinding.universal.gotoBottom`
- `keybinding.universal.toggleRangeSelect`
- `keybinding.universal.rangeSelectDown`
- `keybinding.universal.rangeSelectUp`
- `keybinding.universal.startSearch`
- `keybinding.universal.nextTab`
- `keybinding.universal.prevTab`

## Files

working tree의 파일 변경을 다루는 view다.

| Key | 동작 |
|---|---|
| `<c-o>` | path를 clipboard로 복사 |
| `<space>` | 선택 file stage/unstage toggle |
| `<c-b>` | staged/unstaged 상태로 file filter |
| `y` | clipboard로 복사 |
| `c` | staged changes commit |
| `w` | pre-commit hook 없이 commit |
| `A` | 마지막 commit amend |
| `C` | Git editor로 commit |
| `<c-f>` | fixup 대상 base commit 찾기 |
| `e` | 외부 editor로 file 편집 |
| `o` | OS 기본 app으로 file 열기 |
| `i` | file ignore/exclude |
| `r` | files refresh |
| `s` | 전체 변경 stash |
| `S` | stash options 보기 |
| `a` | 전체 files stage/unstage |
| `<enter>` | file이면 hunk/line staging view 진입, directory면 collapse/expand |
| `d` | discard options |
| `g` | upstream reset options |
| `D` | working tree reset options. nuke 포함 |
| `` ` `` | flat/tree file view toggle |
| `<c-t>` | external diff tool 열기 |
| `M` | merge conflict options |
| `f` | fetch |
| `-` | file tree 전체 collapse |
| `=` | file tree 전체 expand |
| `0` | main view focus |
| `/` | 현재 view filter |

관련 config key:
- `keybinding.files.commitChanges`
- `keybinding.files.commitChangesWithoutHook`
- `keybinding.files.amendLastCommit`
- `keybinding.files.commitChangesWithEditor`
- `keybinding.files.findBaseCommitForFixup`
- `keybinding.files.ignoreFile`
- `keybinding.files.refreshFiles`
- `keybinding.files.stashAllChanges`
- `keybinding.files.viewStashOptions`
- `keybinding.files.toggleStagedAll`
- `keybinding.files.viewResetOptions`
- `keybinding.files.openStatusFilter`

## Main panel: staging

Files view에서 파일로 들어가 hunk/line 단위 staging을 할 때 쓰는 key다.

| Key | 동작 |
|---|---|
| `<left>` | 이전 hunk |
| `<right>` | 다음 hunk |
| `v` | range select toggle |
| `a` | line-by-line/hunk selection mode toggle |
| `<c-o>` | 선택 text clipboard 복사 |
| `<space>` | 선택 line/hunk stage/unstage |
| `d` | unstaged change discard 또는 staged change unstage |
| `o` | file 열기 |
| `e` | file 편집 |
| `<esc>` | Files panel로 복귀 |
| `<tab>` | staged/unstaged view 전환 |
| `E` | 선택 hunk를 external editor로 편집 |
| `c` | staged changes commit |
| `w` | hook 없이 commit |
| `C` | Git editor로 commit |
| `<c-f>` | fixup 대상 base commit 찾기 |
| `/` | 현재 view 검색 |

관련 config key:
- `keybinding.main.toggleSelectHunk: a`
- `keybinding.main.editSelectHunk: E`
- 공통 `keybinding.files.*` commit/fixup 키와 함께 사용됨

## Main panel: normal

일반 main view에서 diff/log를 볼 때 쓰는 key다.

| Key | 동작 |
|---|---|
| mouse wheel down / `fn+up` | 아래로 스크롤 |
| mouse wheel up / `fn+down` | 위로 스크롤 |
| `<tab>` | view 전환 |
| `<esc>` | side panel로 복귀 |
| `/` | 현재 view 검색 |

## Main panel: merging

merge conflict 해결 중 main panel에서 쓰는 key다.

| Key | 동작 |
|---|---|
| `<space>` | hunk 선택 |
| `b` | 모든 hunk 선택 |
| `<up>` | 이전 hunk |
| `<down>` | 다음 hunk |
| `<left>` | 이전 conflict |
| `<right>` | 다음 conflict |
| `z` | 마지막 merge conflict resolution undo |
| `e` | file 편집 |
| `o` | file 열기 |
| `M` | merge conflict options 보기 |
| `<esc>` | Files panel로 복귀 |

관련 config key:
- `keybinding.main.pickBothHunks: b`

## Main panel: patch building

과거 commit의 일부 변경을 custom patch로 선택할 때 쓰는 key다.

| Key | 동작 |
|---|---|
| `<left>` | 이전 hunk |
| `<right>` | 다음 hunk |
| `v` | range select toggle |
| `a` | line-by-line/hunk selection mode toggle |
| `<c-o>` | 선택 text clipboard 복사 |
| `o` | file 열기 |
| `e` | file 편집 |
| `<space>` | patch에 line 추가/제거 |
| `d` | 선택 line을 commit에서 제거 |
| `<esc>` | custom patch builder 종료 |
| `/` | 현재 view 검색 |

## Commits

commit graph/list에서 commit history를 조작하는 핵심 view다.

| Key | 동작 |
|---|---|
| `<c-o>` | abbreviated commit hash 복사 |
| `<c-r>` | copied/cherry-picked commit selection reset |
| `b` | bisect options |
| `s` | 선택 commit을 아래 commit으로 squash |
| `f` | 선택 commit을 아래 commit으로 fixup |
| `c` | fixup message option 설정 |
| `r` | commit message reword |
| `R` | editor로 reword |
| `d` | commit drop. rebase로 branch에서 제거 |
| `e` | edit, 또는 선택 commit부터 interactive rebase 시작 |
| `i` | interactive rebase 시작 |
| `p` | rebase 중 pick 표시 |
| `F` | 선택 commit 대상 `fixup!` commit 생성 |
| `S` | fixup commits autosquash/apply |
| `<c-j>` | commit 하나 아래로 이동 |
| `<c-k>` | commit 하나 위로 이동 |
| `V` | copied commit paste/cherry-pick |
| `B` | 다음 rebase의 base commit으로 mark |
| `A` | staged changes를 선택 commit에 amend |
| `a` | author/co-author 설정 |
| `t` | revert commit 생성 |
| `T` | tag 생성 |
| `<c-l>` | log options |
| `G` | pull request browser에서 열기 |
| `<space>` | detached HEAD로 checkout |
| `y` | commit attribute 복사 |
| `o` | commit browser에서 열기 |
| `n` | commit에서 새 branch 생성 |
| `N` | unpushed commits를 새 branch로 이동 |
| `g` | reset options |
| `C` | cherry-pick copy |
| `<c-t>` | external diff tool |
| `*` | 현재 branch의 commits 선택 |
| `0` | main view focus |
| `<enter>` | commit files 보기 |
| `w` | worktree options |
| `/` | 현재 view 검색 |

관련 config key:
- `keybinding.commits.squashDown`
- `keybinding.commits.markCommitAsFixup`
- `keybinding.commits.createFixupCommit`
- `keybinding.commits.squashAboveCommits`
- `keybinding.commits.moveDownCommit`
- `keybinding.commits.moveUpCommit`
- `keybinding.commits.amendToCommit`
- `keybinding.commits.cherryPickCopy`
- `keybinding.commits.pasteCommits`
- `keybinding.commits.markCommitAsBaseForRebase`
- `keybinding.commits.openLogMenu`
- `keybinding.commits.viewBisectOptions`
- `keybinding.commits.startInteractiveRebase`

## Commit files

commit 또는 stash entry 안의 파일 목록에서 쓰는 key다.

| Key | 동작 |
|---|---|
| `<c-o>` | path clipboard 복사 |
| `y` | clipboard 복사 |
| `c` | 해당 commit의 file version checkout |
| `d` | 이 commit의 해당 file 변경 discard. 내부적으로 interactive rebase |
| `o` | file 열기 |
| `e` | file 편집 |
| `<c-t>` | external diff tool |
| `<space>` | custom patch에 file 포함/제외 |
| `a` | 모든 file을 custom patch에 포함/제외 |
| `<enter>` | file 안으로 들어가 line patch 선택, directory면 collapse toggle |
| `` ` `` | flat/tree view toggle |
| `-` | 모든 file collapse |
| `=` | 모든 file expand |
| `0` | main view focus |
| `/` | 현재 view filter |

관련 config key:
- `keybinding.commitFiles.checkoutCommitFile: c`

## Commit summary

| Key | 동작 |
|---|---|
| `<enter>` | confirm |
| `<esc>` | close |

## Local branches

local branch 목록에서 branch 작업을 수행한다.

| Key | 동작 |
|---|---|
| `<c-o>` | branch name 복사 |
| `i` | git-flow options |
| `<space>` | checkout |
| `n` | 새 branch |
| `N` | unpushed commits를 새 branch로 이동 |
| `o` | pull request 생성 |
| `O` | pull request 생성 options |
| `G` | pull request browser에서 열기 |
| `<c-y>` | pull request URL 복사 |
| `c` | 이름으로 checkout. input에 `-` 입력 시 이전 branch |
| `-` | 이전 branch checkout |
| `F` | force checkout. working directory local changes discard |
| `d` | local/remote branch delete options |
| `r` | 현재 branch를 선택 branch 위로 rebase |
| `M` | 선택 branch를 현재 branch로 merge/squash merge |
| `f` | upstream에서 fast-forward |
| `T` | 새 tag |
| `s` | sort order |
| `g` | reset |
| `R` | branch rename |
| `u` | upstream options |
| `<c-t>` | external diff tool |
| `0` | main view focus |
| `<enter>` | commits 보기 |
| `w` | worktree options |
| `/` | 현재 view filter |

관련 config key:
- `keybinding.branches.createPullRequest`
- `keybinding.branches.openPullRequestInBrowser`
- `keybinding.branches.checkoutBranchByName`
- `keybinding.branches.forceCheckoutBranch`
- `keybinding.branches.checkoutPreviousBranch`
- `keybinding.branches.rebaseBranch`
- `keybinding.branches.mergeIntoCurrentBranch`
- `keybinding.branches.moveCommitsToNewBranch`
- `keybinding.branches.viewGitFlowOptions`
- `keybinding.branches.setUpstream`

## Remote branches

| Key | 동작 |
|---|---|
| `<c-o>` | branch name 복사 |
| `<space>` | remote branch 기반 local branch checkout 또는 detached HEAD checkout |
| `n` | 새 branch |
| `M` | 현재 branch로 merge/squash merge |
| `r` | 현재 branch를 선택 remote branch 위로 rebase |
| `d` | remote branch 삭제 |
| `u` | 현재 branch upstream으로 설정 |
| `s` | sort order |
| `g` | reset options |
| `<c-t>` | external diff tool |
| `0` | main view focus |
| `<enter>` | commits 보기 |
| `w` | worktree options |
| `/` | 현재 view filter |

## Remotes

| Key | 동작 |
|---|---|
| `<enter>` | remote branches 보기 |
| `n` | 새 remote |
| `d` | remote 제거 |
| `e` | remote name 또는 URL 편집 |
| `f` | fetch |
| `F` | fork remote 추가 |
| `/` | 현재 view filter |

관련 config key:
- `keybinding.branches.fetchRemote: f`
- `keybinding.branches.addForkRemote: F`

## Reflog

reflog commit 목록은 commits/sub-commits와 유사한 작업을 제공한다.

| Key | 동작 |
|---|---|
| `<c-o>` | abbreviated commit hash 복사 |
| `<space>` | detached HEAD checkout |
| `y` | commit attribute 복사 |
| `o` | commit browser에서 열기 |
| `n` | commit에서 새 branch 생성 |
| `N` | unpushed commits를 새 branch로 이동 |
| `g` | reset options |
| `C` | cherry-pick copy |
| `<c-r>` | copied commit selection reset |
| `<c-t>` | external diff tool |
| `*` | 현재 branch commits 선택 |
| `0` | main view focus |
| `<enter>` | commits 보기 |
| `w` | worktree options |
| `/` | 현재 view filter |

## Sub-commits

branch 안으로 들어가 본 commit 목록이다. Reflog/Commits와 유사한 읽기/checkout/cherry-pick 동작을 제공한다.

| Key | 동작 |
|---|---|
| `<c-o>` | abbreviated commit hash 복사 |
| `<space>` | detached HEAD checkout |
| `y` | commit attribute 복사 |
| `o` | commit browser에서 열기 |
| `n` | commit에서 새 branch 생성 |
| `N` | unpushed commits를 새 branch로 이동 |
| `g` | reset options |
| `C` | cherry-pick copy |
| `<c-r>` | copied commit selection reset |
| `<c-t>` | external diff tool |
| `*` | 현재 branch commits 선택 |
| `0` | main view focus |
| `<enter>` | files 보기 |
| `w` | worktree options |
| `/` | 현재 view 검색 |

## Stash

| Key | 동작 |
|---|---|
| `<space>` | stash apply |
| `g` | stash pop |
| `d` | stash drop |
| `n` | stash entry에서 새 branch 생성 |
| `r` | stash rename |
| `0` | main view focus |
| `<enter>` | stash files 보기 |
| `w` | worktree options |
| `/` | 현재 view filter |

관련 config key:
- `keybinding.stash.popStash: g`
- `keybinding.stash.renameStash: r`

## Status

| Key | 동작 |
|---|---|
| `o` | config file을 기본 app으로 열기 |
| `e` | config file을 editor로 편집 |
| `u` | update check |
| `<enter>` | 최근 repo로 전환 |
| `a` | all branch logs show/cycle |
| `A` | all branch logs reverse cycle |
| `0` | main view focus |

관련 config key:
- `keybinding.status.checkForUpdate`
- `keybinding.status.recentRepos`
- `keybinding.status.allBranchesLogGraph`
- `keybinding.status.allBranchesLogGraphReverse`

## Submodules

| Key | 동작 |
|---|---|
| `<c-o>` | submodule name 복사 |
| `<enter>` | submodule 진입. `<esc>`로 parent repo 복귀 |
| `d` | submodule 제거 |
| `u` | selected submodule update |
| `n` | 새 submodule |
| `e` | submodule URL update |
| `i` | submodule initialize |
| `b` | bulk submodule options |
| `/` | 현재 view filter |

관련 config key:
- `keybinding.submodules.init: i`
- `keybinding.submodules.update: u`
- `keybinding.submodules.bulkMenu: b`

## Tags

| Key | 동작 |
|---|---|
| `<c-o>` | tag 복사 |
| `<space>` | tag checkout as detached HEAD |
| `n` | 현재 commit에서 새 tag 생성 |
| `d` | local/remote tag delete options |
| `P` | tag push |
| `g` | reset options |
| `<c-t>` | external diff tool |
| `0` | main view focus |
| `<enter>` | commits 보기 |
| `w` | worktree options |
| `/` | 현재 view filter |

## Worktrees

| Key | 동작 |
|---|---|
| `n` | 새 worktree |
| `<space>` | 선택 worktree로 switch |
| `o` | editor에서 열기 |
| `d` | worktree 제거. directory와 `.git` metadata 제거 |
| `/` | 현재 view filter |

관련 config key:
- `keybinding.worktrees.viewWorktreeOptions: w`

## Menu, prompt, confirmation, secondary

### Menu

| Key | 동작 |
|---|---|
| `<enter>` | execute |
| `<esc>` | close/cancel |
| `/` | menu filter |

### Input prompt

| Key | 동작 |
|---|---|
| `<enter>` | confirm |
| `<esc>` | close/cancel |

### Confirmation panel

| Key | 동작 |
|---|---|
| `<enter>` | confirm |
| `<esc>` | close/cancel |
| `<c-o>` | clipboard 복사 |

### Secondary

| Key | 동작 |
|---|---|
| `<tab>` | staged/unstaged 등 다른 view로 전환 |
| `<esc>` | side panel로 복귀 |
| `/` | 현재 view 검색 |

## 설정 파일에서 keybinding을 바꾸는 방법

기본 키는 `config.yml`의 `keybinding` 섹션에서 바꾼다.

예: edit file 비활성화

```yaml
keybinding:
  universal:
    edit: <disabled>
```

예: 일부 이동 키를 Colemak용으로 바꾸기

```yaml
keybinding:
  universal:
    prevItem-alt: 'u'
    nextItem-alt: 'e'
    prevBlock-alt: 'n'
    nextBlock-alt: 'i'
  commits:
    moveDownCommit: '<c-e>'
    moveUpCommit: '<c-u>'
```

## custom command key와 built-in key 충돌

`Custom_Command_Keybindings.md` 기준:

- custom keybinding이 같은 context의 built-in keybinding과 충돌하면 custom keybinding이 실행된다.
- global custom keybinding과 특정 context built-in keybinding이 충돌하면 특정 context built-in keybinding이 우선한다.
- key를 지정하지 않은 custom command는 `?` keybindings menu에서 선택할 수 있다.

## 주의할 점

- `Keybindings_en.md`는 자동 생성 파일이다. 문구를 수정하려면 `pkg/i18n` 쪽을 수정하고 `go generate ./...`를 실행하는 구조로 보인다.
- `docs/Undoing.md`에는 redo가 `ctrl+z`라고 적힌 부분이 있지만, `Keybindings_en.md`와 `Config.md`의 기본값은 `Z`다. 기본 key 보고서는 자동 생성 keybinding 문서와 config 기본값을 우선했다.
- `Keybindings_ko.md`는 파일은 존재하지만, 이 환경의 일부 출력에서 한국어가 깨져 보였다. 그래서 이 정리는 영어 keybinding 문서를 기준으로 한국어 설명을 붙였다.
