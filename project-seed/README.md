# Project seed for the VOZIQ brain

Three small files that go into every VOZIQ project so the brain (`voziqai/brain` on GitLab) is one command away from any repo. This is the on-ramp only. Brain content, templates, and folders never get seeded into projects; knowledge lives centrally, tagged by project, or findability dies.

## What's in the seed

| File | Goes to | Purpose |
|---|---|---|
| `.claude/commands/brain-memo.md` | `.claude/commands/` in each project | The `/brain-memo` capture command: agent distills the session, human approves, MR lands in the brain |
| `CLAUDE-brain-section.md` | Appended to each project's `CLAUDE.md` | Tells agents to search the brain before re-deriving and to offer `/brain-memo` at session end |
| `env.example.snippet` | Merged into each project's `.env.example` | The `BRAIN_REPO_PATH` convention so tooling finds the local brain checkout without hardcoding |

## Deploying

New projects: put these files in the GitLab custom project template (or the cookiecutter, whichever the restructure lands on) and every project born after that is seeded for free.

Existing projects: a one-time sweep. For each repo, branch, copy the three files in, append the CLAUDE section, open an MR titled "Seed brain on-ramp". Mechanical enough to script or to hand to an agent with the repo list.

Per engineer, once: clone the brain somewhere stable and set `BRAIN_REPO_PATH` in their shell profile.

```bash
git clone git@gitlab.com:voziqai/brain.git ~/voziq/brain
export BRAIN_REPO_PATH=~/voziq/brain
```

## The rule that keeps this working

Projects get pointers, never content. If you find yourself wanting a project-local knowledge folder, that's a signal to write a brain note tagged with the project name instead.
