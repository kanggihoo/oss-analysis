#!/usr/bin/env python3
"""skills-manager "갱신 적용"의 순수 파일시스템·해시 결정을 Python으로 옮겨 시나리오를 돌린다.

앱·Rust·네트워크는 실행하지 않았다. 아래 함수는 7a22192의 코드를 줄 범위 그대로 옮긴 번역본이다.
  hash_directory      <- core/content_hash.rs:7-16, 80-168 (IGNORED, walk_content_files, hash_entries)
  copy_skill_dir      <- core/installer.rs:274-299
  removed_paths       <- core/removals.rs:24-148 (is_regenerable, removed_paths, kind_of, collect, display_path)
  approval_token      <- commands/skills.rs:132-146 removal_approval_token
  swap_skill_dir      <- commands/skills.rs:3198-3222 swap_skill_directory
  pending_removals_for<- commands/skills.rs:93-129
  update_decision     <- commands/skills.rs:2157-2208, 2210-2253 (DB 쓰기는 dict로 대체)
  set_source_decision <- commands/skills.rs:2415-2429, 2459-2471
  reimport_decision   <- commands/skills.rs:2584-2615
대체한 부분: SQLite(dict), RepoLock(없음), resync_copy_targets(호출하지 않음), 원격 clone(로컬 `file://` 저장소를
`git clone --depth 1` 한 결과). Python은 정렬을 경로 성분 튜플로 하므로 ASCII 이름에서만 Rust Path::cmp와 같다.
SHA-256 바이트열은 Rust와 같은 규칙(상대 경로 바이트 + 내용 + unix 실행 비트 4바이트 LE)으로 만들지만
Rust 출력과 바이트 단위로 대조하지는 않았다.

사용법: python3 -I update-apply-decisions.py <빈 작업 디렉터리>
"""
import hashlib
import os
import shutil
import subprocess
import sys
import uuid

IGNORED = {".git", ".DS_Store", "Thumbs.db", ".gitignore", "__pycache__"}


def is_ignored(name):
    return name in IGNORED or name.endswith(".pyc")


# ---- core/content_hash.rs -------------------------------------------------
def hash_directory(d):
    entries = []
    for root, dirs, files in os.walk(d, followlinks=False):
        dirs[:] = [x for x in dirs if not is_ignored(x)]
        for f in files:
            if is_ignored(f):
                continue
            p = os.path.join(root, f)
            if os.path.islink(p):  # WalkDir file_type().is_file() 는 링크에 false
                continue
            rel = os.path.relpath(p, d)
            entries.append((tuple(rel.split(os.sep)), rel, p))
    entries.sort(key=lambda e: e[0])
    h = hashlib.sha256()
    for _, rel, p in entries:
        h.update(rel.encode())
        h.update(open(p, "rb").read())
        h.update((os.stat(p).st_mode & 0o111).to_bytes(4, "little"))
    return h.hexdigest()


# ---- core/installer.rs ----------------------------------------------------
def copy_skill_dir(src, dst):
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if name in (".git", ".DS_Store"):
            continue
        s = os.path.join(src, name)
        if os.path.islink(s):
            continue
        if os.path.isdir(s):
            copy_skill_dir(s, os.path.join(dst, name))
        else:
            shutil.copy2(s, os.path.join(dst, name))


# ---- core/removals.rs -----------------------------------------------------
def is_regenerable(name):
    return name in ("__pycache__", ".DS_Store", "Thumbs.db") or name.endswith(".pyc")


def kind_of(path):
    if os.path.islink(path):
        return 0
    return 1 if os.path.isdir(path) else 2


def removed_paths(current, replacement):
    if not os.path.lexists(current):
        return []
    if os.path.islink(current) or not os.path.isdir(current):
        return ["."]
    out = []

    def collect(prefix):
        d = os.path.join(current, prefix)
        for name in os.listdir(d):
            if is_regenerable(name):
                continue
            rel = os.path.join(prefix, name)
            cur = os.path.join(current, rel)
            rep = os.path.join(replacement, rel)
            is_dir = os.path.isdir(cur) and not os.path.islink(cur)
            if os.path.lexists(rep):
                if kind_of(rep) == kind_of(cur):
                    if is_dir:
                        collect(rel)
                else:
                    out.append(rel + ("/" if is_dir else ""))
            else:
                out.append(rel + ("/" if is_dir else ""))

    collect("")
    return sorted(out)


# ---- commands/skills.rs ---------------------------------------------------
def approval_token(revision, pending):
    h = hashlib.sha256()
    h.update(revision.encode())
    for row in sorted(f"{loc}\0{path}" for loc, path in pending):
        h.update(row.encode())
        h.update(b"\0")
    return h.hexdigest()


def pending_removals_for(library, staged, targets):
    pending = []
    if staged is not None:
        pending += [("library", p) for p in removed_paths(library, staged)]
    effective_new = staged if staged is not None else library
    for tool, mode, path in targets:
        if mode != "copy":
            continue
        pending += [(tool, p) for p in removed_paths(path, effective_new)]
    return pending


def staged_path_for(central):
    return os.path.join(os.path.dirname(central), f".{os.path.basename(central)}.staged-{uuid.uuid4()}")


def swap_skill_dir(staged, current):
    backup = os.path.join(os.path.dirname(current), f".{os.path.basename(current)}.backup-{uuid.uuid4()}")
    if os.path.exists(current):
        os.rename(current, backup)
    try:
        os.rename(staged, current)
    except OSError:
        if os.path.exists(backup):
            os.rename(backup, current)
        if os.path.exists(staged):
            shutil.rmtree(staged)
        raise
    shutil.rmtree(backup)


def update_decision(row, remote_skill_dir, revision, targets, approved):
    """update_git_skill_internal 2157-2253 의 결정과 파일 효과. row: dict(central, content_hash)."""
    new_hash = hash_directory(remote_skill_dir)
    content_changed = row["content_hash"] != new_hash
    staged = staged_path_for(row["central"])
    if content_changed:
        copy_skill_dir(remote_skill_dir, staged)
    pending = pending_removals_for(row["central"], staged if content_changed else None, targets)
    token = approval_token(revision, pending)
    if pending and approved != token:
        if content_changed:
            shutil.rmtree(staged)  # StagedPathGuard
        return ("Held", pending, token)
    if content_changed:
        swap_skill_dir(staged, row["central"])
        row["content_hash"] = hash_directory(row["central"])  # install_result.content_hash
    return ("Applied", content_changed)


def set_source_decision(row, remote_skill_dir, force, dry_run):
    new_hash = hash_directory(remote_skill_dir)
    content_changed = row["content_hash"] != new_hash
    if dry_run:
        return ("DryRun", content_changed)
    if content_changed and not force:
        return ("Refused", content_changed)
    if content_changed:
        staged = staged_path_for(row["central"])
        copy_skill_dir(remote_skill_dir, staged)
        swap_skill_dir(staged, row["central"])  # pending_removals_for 호출 없음
    row["content_hash"] = new_hash
    return ("Applied", content_changed)


def reimport_decision(row, source_dir, targets, approved):
    staged = staged_path_for(row["central"])
    copy_skill_dir(source_dir, staged)
    pending = pending_removals_for(row["central"], staged, targets)
    token = approval_token("reimport", pending)
    if pending and approved != token:
        shutil.rmtree(staged)
        return ("Held", pending, token)
    swap_skill_dir(staged, row["central"])
    row["content_hash"] = hash_directory(row["central"])
    return ("Applied",)


# ---- 시나리오 하네스 ------------------------------------------------------
def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


G = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(text)


def read(path):
    return open(path).read() if os.path.exists(path) else None


def listing(d):
    out = []
    for root, dirs, files in os.walk(d):
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), d))
    return sorted(out)


def fresh_checkout(W, upstream, name):
    """원격 head를 --depth 1 로 clone 한 임시 체크아웃(update_git_skill_internal 의 temp_dir)."""
    dest = os.path.join(W, name)
    sh("git", "clone", "-q", "--depth", "1", f"file://{upstream}", dest)
    return dest, sh("git", "rev-parse", "HEAD", cwd=dest)


def new_world(W, tag):
    base = os.path.join(W, tag)
    up = os.path.join(base, "upstream")
    lib = os.path.join(base, "library", "foo")
    os.makedirs(os.path.dirname(lib))
    sh("git", "init", "-q", up)
    write(f"{up}/skills/foo/SKILL.md", "---\nname: foo\n---\nupstream v1\n")
    write(f"{up}/skills/foo/scripts/run.py", "print('v1')\n")
    write(f"{up}/skills/bar/SKILL.md", "bar v1\n")
    sh(*G, "add", "-A", cwd=up)
    sh(*G, "commit", "-qm", "c1", cwd=up)
    co, _ = fresh_checkout(base, up, "co1")
    copy_skill_dir(f"{co}/skills/foo", lib)  # 설치
    row = {"central": lib, "content_hash": hash_directory(lib)}  # 설치가 기록한 content_hash
    return base, up, lib, row


def push(up, rel, text, msg):
    write(f"{up}/{rel}", text)
    sh(*G, "add", "-A", cwd=up)
    sh(*G, "commit", "-qm", msg, cwd=up)


def restart(row):
    """앱/CLI 프로세스 시작: reindex_from_metadata 가 content_hash 를 디스크 해시로 다시 쓴다(sync_metadata.rs:232,250)."""
    row["content_hash"] = hash_directory(row["central"])


def main(W):
    W = os.path.abspath(W)
    os.makedirs(W, exist_ok=True)
    print("git:", sh("git", "--version"))
    print("(번역본 시나리오. 앱·Rust 미실행. 코드 줄 범위는 파일 머리 주석 참고)\n")

    # S1 -------------------------------------------------------------------
    print("## S1. 로컬 수정(기존 파일) + 업스트림이 같은 폴더를 바꿈, 재시작 없음")
    base, up, lib, row = new_world(W, "s1")
    write(f"{lib}/SKILL.md", "---\nname: foo\n---\nMY EDIT\n")
    push(up, "skills/foo/SKILL.md", "---\nname: foo\n---\nupstream v2\n", "c2")
    co, rev = fresh_checkout(base, up, "co2")
    r = update_decision(row, f"{co}/skills/foo", rev, [], None)
    print("결과:", r[0], "content_changed =", r[1])
    print("라이브러리 SKILL.md:", repr(read(f"{lib}/SKILL.md")))
    print("-> 병합·충돌 감지 없음. 내가 고친 기존 파일은 목록에 안 뜨고 통째로 교체된다.\n")

    # S2 -------------------------------------------------------------------
    print("## S2. 로컬 수정 + 로컬에서만 만든 새 파일(notes.md) + 업스트림 변경")
    base, up, lib, row = new_world(W, "s2")
    write(f"{lib}/SKILL.md", "---\nname: foo\n---\nMY EDIT\n")
    write(f"{lib}/notes.md", "my notes\n")
    push(up, "skills/foo/SKILL.md", "---\nname: foo\n---\nupstream v2\n", "c2")
    co, rev = fresh_checkout(base, up, "co2")
    r = update_decision(row, f"{co}/skills/foo", rev, [], None)
    print("1차(토큰 없음):", r[0], "pending =", r[1])
    print("  파일 그대로인가: SKILL.md =", repr(read(f"{lib}/SKILL.md")), "| notes.md =", repr(read(f"{lib}/notes.md")))
    print("  임시 staged 폴더 잔존:", [n for n in os.listdir(os.path.dirname(lib)) if n.startswith(".foo.staged")])
    r2 = update_decision(row, f"{co}/skills/foo", rev, [], r[2])
    print("2차(토큰 전달):", r2[0], "content_changed =", r2[1])
    print("  결과 파일:", listing(lib), "| SKILL.md =", repr(read(f"{lib}/SKILL.md")), "\n")

    # S3/S4 ----------------------------------------------------------------
    print("## S3. 업스트림은 이 폴더를 안 바꿈(모노레포 다른 폴더만 변경), 로컬 수정, 재시작 없음")
    base, up, lib, row = new_world(W, "s3")
    write(f"{lib}/SKILL.md", "---\nname: foo\n---\nMY EDIT\n")
    push(up, "skills/bar/SKILL.md", "bar v2\n", "c2")
    co, rev = fresh_checkout(base, up, "co2")
    r = update_decision(row, f"{co}/skills/foo", rev, [], None)
    print("결과:", r[0], "content_changed =", r[1], "| SKILL.md =", repr(read(f"{lib}/SKILL.md")))
    print("-> 저장 해시(설치 때 값) == 원격 해시라 교체 안 함, 수정이 남는다.\n")

    print("## S4. S3과 같지만 그 사이 앱/CLI를 한 번 시작함(reindex가 content_hash를 디스크 해시로 덮어씀)")
    base, up, lib, row = new_world(W, "s4")
    write(f"{lib}/SKILL.md", "---\nname: foo\n---\nMY EDIT\n")
    restart(row)
    push(up, "skills/bar/SKILL.md", "bar v2\n", "c2")
    co, rev = fresh_checkout(base, up, "co2")
    r = update_decision(row, f"{co}/skills/foo", rev, [], None)
    print("결과:", r[0], "content_changed =", r[1], "| SKILL.md =", repr(read(f"{lib}/SKILL.md")))
    print("-> 저장 해시가 '수정 포함 디스크 해시'가 되어 원격(수정 전 내용)과 달라지고, 업스트림이 안 바뀌었는데도 교체된다.\n")

    # S5 -------------------------------------------------------------------
    print("## S5. 승인 토큰이 묶는 것")
    base, up, lib, row = new_world(W, "s5")
    os.makedirs(f"{lib}/outputs")
    write(f"{lib}/outputs/a.txt", "a\n")
    write(f"{lib}/mine.txt", "m\n")
    push(up, "skills/foo/SKILL.md", "---\nname: foo\n---\nupstream v2\n", "c2")
    co, rev = fresh_checkout(base, up, "co2")
    held = update_decision(row, f"{co}/skills/foo", rev, [], None)
    tok = held[2]
    print("pending:", held[1])
    write(f"{lib}/SKILL.md", "---\nname: foo\n---\nEDIT AFTER DIALOG\n")
    h2 = update_decision(row, f"{co}/skills/foo", rev, [], None)
    print("승인 뒤 기존 파일 SKILL.md 수정 -> 토큰 불변:", h2[2] == tok)
    write(f"{lib}/outputs/b.txt", "b\n")
    h3 = update_decision(row, f"{co}/skills/foo", rev, [], None)
    print("승인 뒤 사라질 폴더 outputs/ 안에 새 파일 -> 토큰 불변:", h3[2] == tok)
    write(f"{lib}/another.txt", "x\n")
    h4 = update_decision(row, f"{co}/skills/foo", rev, [], None)
    print("승인 뒤 새 최상위 파일 -> 토큰 불변:", h4[2] == tok, "(바뀌면 다시 묻는다)")
    print("리비전이 다르면 토큰 불변:", approval_token("other-rev", held[1]) == tok)
    ok = update_decision(row, f"{co}/skills/foo", rev, [], tok)
    print("옛 토큰으로 호출 ->", ok[0], "(목록이 자랐으므로 Held)")
    ok = update_decision(row, f"{co}/skills/foo", rev, [], h4[2])
    print("최신 목록의 토큰으로 호출 ->", ok[0], "| 남은 파일:", listing(lib))
    print()

    # S6 -------------------------------------------------------------------
    print("## S6. removed_paths 규칙(사라질 파일 목록이 잡는 것/못 잡는 것)")
    t = os.path.join(W, "s6")
    cur, rep = f"{t}/cur", f"{t}/new"
    write(f"{cur}/SKILL.md", "mine-edited\n")                 # 새 버전에도 있음, 내용 다름
    write(f"{cur}/scripts/run.py", "mine-edited\n")           # 새 버전에도 있음
    write(f"{cur}/templates/a.pptx", "x\n")                   # 새 버전에 폴더째 없음
    write(f"{cur}/templates/b.pptx", "x\n")
    write(f"{cur}/.gitignore", "mine\n")                      # content_hash 는 무시, removals 는 보고
    write(f"{cur}/.git/HEAD", "ref\n")                        # staged 에서는 항상 빠짐
    write(f"{cur}/scripts/__pycache__/m.pyc", "x\n")          # regenerable
    write(f"{cur}/stray.pyc", "x\n")
    write(f"{cur}/.DS_Store", "x\n")
    write(f"{cur}/thing", "file the user edited\n")           # 새 버전에서는 디렉터리
    write(f"{cur}/other/inner.txt", "x\n")                    # 새 버전에서는 파일
    os.symlink("/somewhere", f"{cur}/link")
    write(f"{rep}/SKILL.md", "upstream\n")
    write(f"{rep}/scripts/run.py", "upstream\n")
    write(f"{rep}/thing/inner.txt", "dir now\n")
    write(f"{rep}/other", "file now\n")
    print("removed_paths:", removed_paths(cur, rep))
    print("-> SKILL.md, scripts/run.py(내용만 다름)는 목록에 없다. .pyc/__pycache__/.DS_Store는 제외, .gitignore/.git/는 포함.\n")

    # S7 -------------------------------------------------------------------
    print("## S7. 복사 모드 배포 사본(agent copy)이 있을 때")
    base, up, lib, row = new_world(W, "s7")
    agent = os.path.join(base, "agent", "foo")
    copy_skill_dir(lib, agent)
    write(f"{agent}/agent-note.md", "agent wrote this\n")
    link_dir = os.path.join(base, "agent2", "foo")
    os.makedirs(link_dir)
    write(f"{link_dir}/whatever.md", "x\n")
    targets = [("claude_code", "copy", agent), ("grok", "symlink", link_dir)]
    push(up, "skills/foo/SKILL.md", "---\nname: foo\n---\nupstream v2\n", "c2")
    co, rev = fresh_checkout(base, up, "co2")
    r = update_decision(row, f"{co}/skills/foo", rev, targets, None)
    print("내용 변경 있음:", r[0], r[1])
    base2, up2, lib2, row2 = new_world(W, "s7b")
    agent2 = os.path.join(base2, "agent", "foo")
    copy_skill_dir(lib2, agent2)
    write(f"{agent2}/agent-note.md", "agent wrote this\n")
    push(up2, "skills/bar/SKILL.md", "bar v2\n", "c2")
    co2, rev2 = fresh_checkout(base2, up2, "co2")
    r = update_decision(row2, f"{co2}/skills/foo", rev2, [("claude_code", "copy", agent2)], None)
    print("내용 변경 없음(staged 없음)에서도:", r[0], r[1] if r[0] == "Held" else "")
    print("-> symlink 배포는 목록에 없고, copy 배포는 location=에이전트 키로 나온다.\n")

    # S8 -------------------------------------------------------------------
    print("## S8. swap_skill_directory 의 실패 복구")
    t = os.path.join(W, "s8")
    cur = f"{t}/lib/foo"
    write(f"{cur}/SKILL.md", "old\n")
    staged = f"{t}/lib/.foo.staged-missing"  # 존재하지 않는 staged -> 두 번째 rename 실패
    try:
        swap_skill_dir(staged, cur)
    except OSError as e:
        print("rename 실패:", type(e).__name__)
    print("복구 뒤 라이브러리:", listing(cur), "| 잔존 .backup:", [n for n in os.listdir(f"{t}/lib") if "backup" in n])
    write(f"{t}/lib/.foo.staged-ok/SKILL.md", "new\n")
    swap_skill_dir(f"{t}/lib/.foo.staged-ok", cur)
    print("성공 swap 후:", repr(read(f"{cur}/SKILL.md")), "| 디렉터리:", sorted(os.listdir(f"{t}/lib")))
    print()

    # S9 -------------------------------------------------------------------
    print("## S9. set-source (local -> git): 저장 해시 vs 원격 해시")
    base, up, lib, row = new_world(W, "s9a")
    co, rev = fresh_checkout(base, up, "co2")
    write(f"{lib}/SKILL.md", "---\nname: foo\n---\nMY EDIT\n")
    write(f"{lib}/only-mine.md", "m\n")
    print("재시작 없음, 원격=설치 때 내용:", set_source_decision(row, f"{co}/skills/foo", False, False),
          "| 로컬 수정 유지:", read(f"{lib}/SKILL.md").strip().endswith("MY EDIT"), listing(lib))
    base, up, lib, row = new_world(W, "s9b")
    co, rev = fresh_checkout(base, up, "co2")
    write(f"{lib}/SKILL.md", "---\nname: foo\n---\nMY EDIT\n")
    restart(row)
    print("재시작 뒤:", set_source_decision(row, f"{co}/skills/foo", False, False), "(--force 없이 거절)")
    print("  --dry-run:", set_source_decision(row, f"{co}/skills/foo", False, True), "| 파일 변화 없음:", listing(lib))
    write(f"{lib}/only-mine.md", "m\n")
    print("  --force:", set_source_decision(row, f"{co}/skills/foo", True, False),
          "| 결과 파일:", listing(lib), "(only-mine.md 소실, 확인 없음)")
    print()

    # S10 ------------------------------------------------------------------
    print("## S10. reimport (local/import): 해시 비교 없이 항상 교체")
    t = os.path.join(W, "s10")
    src, lib = f"{t}/source/foo", f"{t}/library/foo"
    write(f"{src}/SKILL.md", "src v1\n")
    copy_skill_dir(src, lib)
    row = {"central": lib, "content_hash": hash_directory(lib)}
    write(f"{lib}/SKILL.md", "MY EDIT\n")
    r = reimport_decision(row, src, [], None)
    print("원본 안 바뀜 + 라이브러리 수정:", r[0], "| SKILL.md =", repr(read(f"{lib}/SKILL.md")))
    write(f"{lib}/mine.txt", "m\n")
    r = reimport_decision(row, src, [], None)
    print("로컬 전용 파일 추가:", r[0], r[1] if len(r) > 1 else "")
    r2 = reimport_decision(row, src, [], r[2])
    print("토큰 전달:", r2[0], "| 남은 파일:", listing(lib))


if __name__ == "__main__":
    main(sys.argv[1])
