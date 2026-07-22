# Project seed for the VOZIQ brain

The on-ramp seeded into every VOZIQ project so the brain (`voziq/brain` on git.voziq.com) is one command away from any repo, whatever AI tool the engineer runs: Claude Code, Copilot, Codex, Cursor, GLM through a compatible CLI, or no tool at all. This is the on-ramp only. Brain content never gets seeded into projects; knowledge lives centrally, tagged by project, or findability dies.

## Design

Instructions live in `AGENTS.md`, the cross-tool standard read natively by Codex, Copilot, Cursor, Gemini CLI, Aider, Windsurf, Zed, and most others. Claude Code reads `CLAUDE.md`, so it gets a one-line shim that imports AGENTS.md. The memo command body is identical everywhere; only the folder it lives in differs per tool. Hard enforcement is server-side in GitLab CI, so it covers every seat, including humans editing in the web IDE.

## What's in the seed

| File | Goes to | Covers |
|---|---|---|
| `AGENTS-brain-section.md` | Appended to each project's `AGENTS.md` | Every AGENTS.md-aware tool, and any agent asked to "file a brain memo" |
| `CLAUDE.md.shim` | Project root as `CLAUDE.md` (or append `@AGENTS.md` to an existing one) | Claude Code |
| `.claude/commands/brain-memo.md` | Same path in project | `/brain-memo` in Claude Code |
| `.codex/prompts/brain-memo.md` | Same path in project; Codex users may need to copy or symlink into `~/.codex/prompts` once per machine | Codex CLI |
| `.github/prompts/brain-memo.prompt.md` | Same path in project | Copilot |
| `gitlab-ci.snippet.yml` | Merged into the shared CI config | Everyone: secret scan, hardcoded-client check, ruff on every MR |
| `env.example.snippet` | Merged into each project's `.env.example` | The `BRAIN_REPO_PATH` convention |

The three memo command files carry the same body by design. If you edit one, edit all three.

## Deploying

New projects: put the seed in the GitLab custom project template (or the cookiecutter, whichever the restructure lands on) and every project born after that is seeded for free. The CI snippet belongs in the shared pipeline `include:` so it can't be forgotten per project.

Existing projects: a one-time sweep. For each repo, branch, copy the files in, append the AGENTS.md section, add the CLAUDE.md shim, open an MR titled "Seed brain on-ramp". Mechanical enough to script or to hand to an agent with the repo list.

Per engineer, once: clone the brain somewhere stable and set `BRAIN_REPO_PATH` in their shell profile.

```bash
git clone https://git.voziq.com/voziq/brain.git ~/voziq/brain
export BRAIN_REPO_PATH=~/voziq/brain
```

## The rules that keep this working

Projects get pointers, never content. If you find yourself wanting a project-local knowledge folder, write a brain note tagged with the project name instead.

CI is the gate; client-side hooks are convenience. The pilot kit's Claude Code hooks give Claude seats instant feedback, but nothing about the safety model depends on which tool a seat runs, because every MR passes the same pipeline.
