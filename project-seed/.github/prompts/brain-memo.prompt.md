---
description: Distill this session into a VOZIQ brain note and file it as a merge request
---

Distill this session into a note for the voziqai/brain knowledge repo. Follow these steps exactly.

1. Decide whether there is anything worth keeping. The test: would any part of this session help a teammate in three months? If not, say so and stop. Do not file a note to have filed a note.

2. Draft the note using the session template (`sessions/TEMPLATE.md` in the brain repo). Half a page maximum. Concrete over general: exact commands, exact error messages, exact causes. Front matter must include `type: session`, a title, `timestamp`, `author` (the engineer's name, not yours), and tags including this project's name.

3. Scrub it. Remove or replace: credentials, tokens, API keys, connection strings, end-customer names or identifiers, raw client data, and anything commercially sensitive or personnel-related. Client-specific facts use the client short code. If the lesson cannot be written without sensitive detail, write the general form of the lesson instead.

4. Show the draft to the engineer and wait for their approval. Do not skip this even if the note looks obviously fine.

5. On approval, file it to the brain as a merge request:
   - Locate the brain checkout: `$BRAIN_REPO_PATH` if set, otherwise ask the engineer where it is.
   - In that checkout: pull main, create branch `memo/YYYY-MM-DD-short-slug`, add the note as `sessions/YYYY-MM-DD-short-slug.md`, commit, push the branch.
   - Open the merge request with a one-line description: `glab mr create` if available, else `gh pr create` if the brain is on GitHub, else print the pushed branch name and the compare URL for the engineer to open manually.
   - Never push to the brain's main branch under any circumstances.

6. Report the MR link and end. No summary of the summary.
