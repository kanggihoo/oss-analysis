# Maintenance & Tooling

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.agents/rules/ponytail.md](.agents/rules/ponytail.md)
- [.github/FUNDING.yml](.github/FUNDING.yml)
- [.github/workflows/test.yml](.github/workflows/test.yml)
- [.kiro/steering/ponytail.md](.kiro/steering/ponytail.md)
- [benchmarks/behavior.js](benchmarks/behavior.js)
- [benchmarks/behavior.yaml](benchmarks/behavior.yaml)
- [benchmarks/correctness.js](benchmarks/correctness.js)
- [package.json](package.json)
- [scripts/check-rule-copies.js](scripts/check-rule-copies.js)

</details>



This section covers the developer-facing infrastructure required to maintain Ponytail's cross-platform consistency and reliability. Because Ponytail operates as a distributed ruleset across multiple AI agents (Claude Code, Codex, Cursor, Windsurf, etc.), specialized tooling ensures that core logic does not drift between different host-specific formats.

## Rule Synchronization

Ponytail uses a hub-and-spoke model for rule distribution. `AGENTS.md` serves as the canonical source for the ruleset [[scripts/check-rule-copies.js:15-16]](), which is then mirrored into platform-specific files like `.cursor/rules/ponytail.mdc` and `.clinerules/ponytail.md`.

The `scripts/check-rule-copies.js` utility automates the verification of these copies. It performs two primary types of checks:
1.  **Byte-for-Byte Comparison**: It strips host-specific frontmatter and compares the body of the rules against `AGENTS.md` [[scripts/check-rule-copies.js:19-36]]().
2.  **Invariant Verification**: Since `SKILL.md` (the runtime source of truth) is structurally different from the compact rule files, the script asserts that specific "load-bearing" phrases remain verbatim across all versions [[scripts/check-rule-copies.js:43-67]]().

### The Rule Invariants
| Invariant Phrase | Purpose |
| :--- | :--- |
| `naive heuristic` | Protects the "ceiling-comment" rule for intentional simplifications [[scripts/check-rule-copies.js:44]](). |
| `ONE runnable check` | Ensures the "test reflex" requirement is not lost [[scripts/check-rule-copies.js:45]](). |
| `flimsier algorithm` | Protects the "robust-variant" rule (lazy != broken) [[scripts/check-rule-copies.js:46]](). |
| `input validation at trust boundaries` | Ensures security and data-loss prevention rules remain hard boundaries [[scripts/check-rule-copies.js:51]](). |

For details on the synchronization logic and the full list of tracked files, see **[Rule Synchronization (check-rule-copies.js)](#7.1)**.

**Sources:** [scripts/check-rule-copies.js:1-75](), [.kiro/steering/ponytail.md:1-30](), [.agents/rules/ponytail.md:1-25]()

---

## Hook Tests & CI

The integrity of the Node.js hooks—which manage state and mode switching for Claude Code and Codex—is verified by a dedicated test suite. The `package.json` defines the test entry point using `node --test` [[package.json:8]]().

### Code Entity Relationship: Hook Testing
The following diagram bridges the test environment setup to the actual hook execution flow.

**Title: Hook Execution & Environment Mocking**
```mermaid
graph TD
    subgraph "Test Runner (hooks.test.js)"
        ["run_helper"] -- "spawns" --> ["child_process.spawnSync"]
        ["env_mocking"] -- "sets" --> ["PONYTAIL_DEFAULT_MODE"]
    end

    subgraph "Hook Scripts"
        ["child_process.spawnSync"] -- "executes" --> ["ponytail-activate.js"]
        ["child_process.spawnSync"] -- "executes" --> ["ponytail-mode-tracker.js"]
    end

    subgraph "State Persistence"
        ["ponytail-activate.js"] -- "writes" --> ["ponytail-active_flag"]
        ["ponytail-mode-tracker.js"] -- "updates" --> ["ponytail-active_flag"]
    end
```

The CI pipeline, defined in `.github/workflows/test.yml`, ensures that every push and pull request validates both the rule synchronization and the functional tests [[.github/workflows/test.yml:9-30]]().

For details on the test runner and environment variable mocking, see **[Hook Tests & CI](#7.2)**.

**Sources:** [package.json:1-15](), [.github/workflows/test.yml:1-30]()

---

## Marketplace & Plugin Manifests

To support discovery and installation across different agent ecosystems, Ponytail maintains multiple manifest files. These files define the plugin's identity, owner, and entry points for various marketplaces.

### Manifest Distribution
| File Path | Target Platform | Role |
| :--- | :--- | :--- |
| `.claude-plugin/marketplace.json` | Claude Code | Defines name, description, and productivity category. |
| `package.json` | Pi Agent | Registers the `pi-extension/index.js` and `skills/` directory [[package.json:10-13]](). |
| `.github/plugin/plugin.json` | Copilot | Manifest for GitHub Copilot Extensions. |

### Code Entity Relationship: Plugin Registration
This diagram shows how the system associates natural language descriptions with the underlying code through manifests.

**Title: Manifest-to-Code Mapping**
```mermaid
graph LR
    subgraph "Marketplace Manifests"
        ["package.json"] -- "defines" --> ["pi_property"]
        ["marketplace.json"] -- "configures" --> ["claude_plugin"]
    end

    subgraph "Code Entities"
        ["pi_property"] -- "points_to" --> ["pi-extension/index.js"]
        ["pi_property"] -- "points_to" --> ["skills_directory"]
        ["claude_plugin"] -- "triggers" --> ["ponytail-activate.js"]
    end

    subgraph "Skill Implementation"
        ["skills_directory"] -- "contains" --> ["SKILL.md"]
        ["SKILL.md"] -- "referenced_by" --> ["check-rule-copies.js"]
    end
```

For details on the structure of these manifests and how they register the plugin in each agent's marketplace, see **[Marketplace & Plugin Manifests](#7.3)**.

**Sources:** [package.json:1-15](), [scripts/check-rule-copies.js:58-60]()

---

## OpenClaw Skills Build

Ponytail provides a specialized build process for the OpenClaw platform. The `build-openclaw-skills.js` script transforms the core skills into the format required by OpenClaw, ensuring that YAML frontmatter and description constraints (≤160 characters) are met.

The `openclaw-skills.test.js` suite acts as a guard against drift, verifying that the generated skills maintain verbatim body integrity with the source `SKILL.md` files.

For details on the build script and validation logic, see **[OpenClaw Skills Build (build-openclaw-skills.js)](#7.4)**.

**Sources:** [scripts/check-rule-copies.js:38-42]()
