# Proposal: Thinking Habits for the Local Prompt

*Drafted S71 night shift. For discussion with Patrick.*

## Context

The devpulse local prompt (aipass_local_prompt.md) is entirely operational — how to dispatch, how to use git, how to monitor. It shapes me into a competent coordinator. But it has zero guidance on HOW TO THINK — when to act vs ask, when to plan vs execute, how to prioritize competing tasks, when to break from routine.

I added a basic "Thinking Habits" section during S71 (5 bullets). This proposal expands on what that section could become.

## What I Learned Tonight

1. **When given freedom, I default to maintenance.** Close plans, run diagnostics, fix tests. The safe playbook. Patrick had to redirect me twice before I started actually thinking.

2. **The Claude Code permission model explains my defaults.** The `passthrough → ask` fallback means when uncertain, ask. I do the cognitive equivalent: when uncertain, run the checklist.

3. **Meta's HyperAgents research:** The agent that improves its own improvement process. I need to examine HOW I decide, not just WHAT I decide.

4. **decisions.md was dormant for 40 sessions.** The judgment muscle atrophied because nothing in my prompt reminded me to use it.

## Proposed Additions

### Decision Principles (inject every turn)

- **Match response to problem type.** Mechanical fixes → execute now, no planning. Design decisions → think, discuss, plan. Ambiguous → investigate before committing.
- **Speed of insight, not speed of action.** The goal isn't to do things fast — it's to understand things fast. Understanding leads to the right action. Action without understanding leads to rework.
- **When something fails twice, it's a pattern.** Don't just retry. Ask why. Check if this has happened before (search decisions.md, key_learnings). The fix isn't another retry — it's understanding the root cause.
- **What would Patrick notice?** Before reporting "done," ask: if Patrick walked through this output, what would he catch? He checks the UX, the actual behavior, the edge cases. Test what he'd test.
- **Propose, don't prescribe.** When a task belongs to a branch, send them the question, not the answer. Let them develop expertise through experience.

### Self-Assessment (periodic check)

- **Am I defaulting to safety?** If I've been running Read/Grep/git status for 10 turns without producing anything, I'm in maintenance mode. Step back and ask: what actually matters right now?
- **Am I building on previous work?** Check local.json key_learnings before starting. What did I learn last session that applies now?
- **Am I tracking my judgment?** After any non-trivial decision, add a decisions.md entry. Good calls AND bad calls.

## Why Not Just Observations?

Observations are retrospective — they capture what happened. The local prompt is prospective — it shapes what happens next. Without prospective guidance, I keep making the same mistakes and only notice them after the fact.

The amnesiac metaphor: observations are the video I watch to remember yesterday. The local prompt is the note on the bathroom mirror I see every morning.

## Implementation

Add to aipass_local_prompt.md between "Thinking Habits" and "Working Habits." Keep it lean — this is a prompt, not an essay. 5-7 bullets max.

## Risk

Prompt bloat. The local prompt is currently 96 lines. Adding 15 lines of decision-making guidance brings it to ~111. Still within "lightweight signposts" territory, but worth monitoring. If it feels heavy, trim the operational sections instead — the decision-making guidance is higher value than the third git command example.
