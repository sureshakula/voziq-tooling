# Team knowledge (append this section to the project CLAUDE.md)

## The brain

VOZIQ's shared knowledge lives in the brain repo (`voziqai/brain` on GitLab; local checkout at `$BRAIN_REPO_PATH`). Before solving anything that smells recurring, search it: client quirks, pipeline gotchas, past decisions, runbooks. Grep works; front-matter tags are reliable; trust `decisions/` and `runbooks/` as reviewed team positions.

At the end of a session that produced a durable lesson, offer to run `/brain-memo`. All brain writes go through merge requests, never direct pushes, and never include credentials, end-customer identifiers, client data, or commercially sensitive material.
