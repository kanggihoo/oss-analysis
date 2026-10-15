use std::fs;
use std::path::Path;

use cc_switch_lib::{AppType, ImportSkillSelection, SkillApps, SkillService};

#[path = "support.rs"]
mod support;
use support::{create_test_state, ensure_test_home, reset_test_fs, test_mutex};

fn write(p: &Path, s: &str) {
    fs::create_dir_all(p.parent().unwrap()).unwrap();
    fs::write(p, s).unwrap();
}

fn dump(label: &str, dir: &Path) {
    println!("--- {label}: {}", dir.display());
    if !dir.exists() && dir.symlink_metadata().is_err() {
        println!("  (없음)");
        return;
    }
    let link = dir
        .symlink_metadata()
        .map(|m| m.file_type().is_symlink())
        .unwrap_or(false);
    println!("  symlink={link}");
    fn walk(base: &Path, cur: &Path) {
        let mut es: Vec<_> = fs::read_dir(cur).unwrap().flatten().collect();
        es.sort_by_key(|e| e.file_name());
        for e in es {
            let p = e.path();
            if p.is_dir() {
                walk(base, &p);
            } else {
                let rel = p.strip_prefix(base).unwrap().display().to_string();
                let body = fs::read_to_string(&p).unwrap_or_default().replace('\n', " | ");
                println!("  {rel} => {body}");
            }
        }
    }
    walk(dir, dir);
}

fn apps(claude: bool, codex: bool) -> SkillApps {
    SkillApps {
        claude,
        codex,
        ..Default::default()
    }
}

#[test]
fn same_name_different_content_across_apps() {
    let _g = test_mutex().lock().unwrap();
    reset_test_fs();
    let state = create_test_state().unwrap();
    let home = ensure_test_home();
    let claude = home.join(".claude/skills/dup-skill");
    let codex = home.join(".codex/skills/dup-skill");
    let ssot = home.join(".cc-switch/skills/dup-skill");

    // 같은 이름, 다른 frontmatter. codex 쪽에만 agents/openai.yaml
    write(
        &claude.join("SKILL.md"),
        "---\nname: dup-skill\ndescription: CLAUDE-VERSION\n---\nbody-claude\n",
    );
    write(
        &codex.join("SKILL.md"),
        "---\nname: dup-skill\ndescription: CODEX-VERSION\n---\nbody-codex\n",
    );
    write(
        &codex.join("agents/openai.yaml"),
        "interface:\n  display_name: CODEX-ONLY-YAML\n",
    );

    println!("\n===== STEP 0: 시작 상태 =====");
    dump("claude", &claude);
    dump("codex", &codex);

    println!("\n===== STEP 1: scan_unmanaged =====");
    let found = SkillService::scan_unmanaged(&state.db).unwrap();
    for s in &found {
        println!("  directory={} found_in={:?} path={}", s.directory, s.found_in, s.path);
    }

    println!("\n===== STEP 2: import_from_apps (claude+codex 켬) =====");
    let r = SkillService::import_from_apps(
        &state.db,
        vec![ImportSkillSelection {
            directory: "dup-skill".into(),
            apps: apps(true, true),
        }],
    );
    println!("  result ok={:?}", r.as_ref().map(|v| v.len()).map_err(|e| e.to_string()));
    dump("SSOT(~/.cc-switch)", &ssot);
    dump("claude", &claude);
    dump("codex", &codex);

    println!("\n===== STEP 3: resync_all_apps (provider 전환 때 호출되는 경로) =====");
    let out = SkillService::resync_all_apps(&state.db);
    for o in out.iter().filter(|o| o.app == "claude" || o.app == "codex") {
        println!("  {} ok={} err={:?} failed={:?}", o.app, o.ok, o.error, o.failed_skills);
    }
    dump("SSOT(~/.cc-switch)", &ssot);
    dump("claude", &claude);
    dump("codex", &codex);

    println!("\n===== STEP 4: codex 끄기 → 켜기 =====");
    let id = SkillService::get_all_installed(&state.db)
        .unwrap()
        .into_iter()
        .find(|s| s.directory == "dup-skill")
        .map(|s| s.id)
        .unwrap();
    SkillService::toggle_app(&state.db, &id, &AppType::Codex, false).unwrap();
    dump("codex(끈 뒤)", &codex);
    SkillService::toggle_app(&state.db, &id, &AppType::Codex, true).unwrap();
    dump("codex(다시 켠 뒤)", &codex);
}
