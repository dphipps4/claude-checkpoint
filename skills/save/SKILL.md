---
name: save
description: Save a project checkpoint. Updates docs/graph.json (the live state), rebuilds docs/knowledge-graph.html from it, and appends a clean, dated entry to this month's session log in sessions/YYYY-MM.md. Use when the user says "save checkpoint", "checkpoint", or "save a checkpoint", at the end of a session, at any pause that hands work back to the user, and after a long working stretch.
---

# Save a checkpoint

A checkpoint saves the project's state for someone resuming cold. The graph is
the live state; the log is the history behind it. A checkpoint is three steps
taken together:

1. `docs/graph.json`: the live state, edited by hand.
2. `docs/knowledge-graph.html`: generated from the JSON. Never edited by hand.
3. `sessions/YYYY-MM.md`: a dated entry appended to this month's log.

## When to checkpoint

- At the end of a session.
- At any pause that hands work back to the user for a decision or review.
- After a long working stretch: a build, a deploy, a batch of merged PRs.

Checkpoint without being asked.

## 0. Start, if the project has no graph

When `docs/graph.json` does not exist, create it first:

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_graph.py" . --init

This writes a minimal `docs/graph.json` (project and title from the folder name)
and copies the default page template to `docs/graph.template.html`. It never
overwrites an existing file.

## 1. Update `docs/graph.json`

Read the file, edit it, write it back.

```json
{
  "project": "example",
  "title": "Example project",
  "updated": "2026-01-15",
  "stages": "0 planned, 1 started, 2 working, 3 shipped",
  "nodes": [
    {"id": "API", "type": "component", "label": "Public API", "stage": 2,
     "owed": "error codes for the batch endpoint",
     "next": "Merge the batch endpoint PR once CI is green",
     "updated": "2026-01-15",
     "note": "Detail that does not fit the fields below."}
  ],
  "links": [{"s": "WEB", "t": "API", "k": "calls"}]
}
```

Each node carries:

- `id`: stable and unique. Links refer to it, so it never changes.
- `type`: groups nodes on the page (component, decision, risk, task, and so on).
- `label`: the thing's name, in a few words.
- `stage`: an integer for how far the thing has progressed. The scale is the
  project's own; describe it once in the top-level `stages`.
- `owed`: what is owed on it, in a few words. `"nothing"` is an answer; `null`
  means nobody has checked.
- `next`: the one concrete next action. A node with no writable next action is
  itself a finding.
- `updated`: `YYYY-MM-DD`, the day this node's facts were last verified. Set it
  on every node touched, and set the top-level `updated` to today.
- `note` (optional): what does not fit the fields above, without restating them.

Links are `{"s": source id, "t": target id, "k": kind}`.

Add what this session introduced. Remove what is no longer true. Keep ids stable.

## 2. Rebuild the page

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_graph.py" .

The script validates the JSON first: duplicate ids, links to missing nodes,
missing fields. **A validation error fails the checkpoint.** Fix the JSON; do not
work around it. Nodes whose `updated` is more than 14 days old are listed as a
to-do list, not an error.

The data is inlined into the page because a `file://` page cannot fetch a local
JSON file. The page is rendered from `docs/graph.template.html` when present,
otherwise from the template bundled with this plugin.

To validate without writing:

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_graph.py" . --check

## 3. Append to this month's log

Append one dated entry to `sessions/YYYY-MM.md` for the current month, creating
the file when the month is new. Write it so it could be shown to someone else.

**The standard:**

- **Facts only.** What was done (with PR numbers), what was found and how it was
  proven, decisions, what is open, the next step. No narration, no chat.
- **Nothing personal.** No names of people, no personal circumstances, no
  details of anyone's machines beyond what the project needs.
- **This project only.** Nothing from other projects or repositories, ever.
- **Clean quotes.** When a decision is quoted in the user's own words, correct
  its spelling and grammar first.
- **Short.** A few bullets per heading. Link to PRs and docs instead of
  repeating them.
- **Append.** Earlier entries are not rewritten, except to correct spelling or
  to remove something that breaks this standard.

**Shape:**

```markdown
## 2026-01-15: Batch endpoint

### Done
- Batch endpoint behind a flag (#42). Contract in docs/api.md.

### Found
- Retries doubled writes under timeout. Proven by test_batch_retry; fixed in #43.

### Decided
- "Batch requests are capped at 100 items."

### Open
- Error codes for partial failure.

### Next
- Merge #42 once CI is green.
```

Omit a heading that has nothing under it. Search a month file with `grep`
rather than reading it whole.

## What a checkpoint is not

A checkpoint is not a memory write. Standing rules, corrections and preferences
belong in Claude's memory, which loads automatically at the start of a session.
The session log does not load, so a rule recorded only there is lost.

## Report back

Three or four lines: which nodes changed, what was logged, and anything that
could not be done and why. Do not reproduce the log entry; it is in the file.
