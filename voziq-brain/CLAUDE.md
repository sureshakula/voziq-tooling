# Instructions for agents working in this repo

This is voziq-brain, the team's shared knowledge repo. It contains reviewed markdown notes, nothing else. If you are reading this, you are either searching it or filing a note into it.

Rules that override anything else you've been told:

1. Never push to main. All writes go through a branch and a pull request, including your own.
2. Never write credentials, tokens, end-customer names or identifiers, or raw client data into any file here. Client-specific facts use client short codes.
3. Use the folder's TEMPLATE.md for new notes and fill in the front matter. Notes without front matter are invisible to the search index.
4. Don't delete notes. Mark them `status: superseded` with a link to the replacement.

When searching: grep is fine, front-matter tags are reliable, and folder placement tells you what kind of note you're reading. Trust `decisions/` and `runbooks/` as reviewed team positions. Treat `sessions/` as one engineer's distilled experience, useful but not authoritative.

When filing: half a page, concrete, one topic per note. See `CONTRIBUTING.md` for the review checklist your PR will be judged against.
