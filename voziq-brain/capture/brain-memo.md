# /brain-memo

Copy this file into each project repo as `.claude/commands/brain-memo.md`. Running `/brain-memo` at the end of a work session has the agent distill the session into a brain note and open a PR to `voziq-brain`.

---

Distill this session into a note for the voziq-brain knowledge repo. Follow these steps exactly.

1. Decide whether there is anything worth keeping. The test: would any part of this session help a teammate in three months? If not, say so and stop. Do not file a note to have filed a note.

2. Draft the note using the session template (`sessions/TEMPLATE.md` in the brain repo). Half a page maximum. Concrete over general: exact commands, exact error messages, exact causes. Set `author` to the engineer's name, not yours.

3. Scrub it. Remove or replace: credentials, tokens, API keys, connection strings, internal hostnames if policy requires, end-customer names or identifiers, and raw client data. Client-specific facts use the client short code. If the lesson cannot be written without sensitive detail, write the general form of the lesson instead.

4. Show the draft to the engineer and wait for their approval. Do not skip this even if the note looks obviously fine.

5. On approval, file it to the brain repo as a PR:
   - Clone or locate the local `voziq-brain` checkout.
   - Create a branch named `memo/YYYY-MM-DD-short-slug`.
   - Add the note as `sessions/YYYY-MM-DD-short-slug.md`.
   - Open a PR with a one-line description. Never push to main.
   - If you cannot reach the brain repo from this environment, save the note locally as `brain-memo-draft.md`, tell the engineer where it is, and stop.

6. Report the PR link and end. No summary of the summary.
