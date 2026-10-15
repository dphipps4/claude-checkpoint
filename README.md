# checkpoint

A Claude Code plugin that saves a project checkpoint, so that anyone can pick the
work up cold. A checkpoint records the project's live state as a small knowledge
graph and appends a dated entry to a monthly session log.

The graph lives in `docs/graph.json`: what exists, how it connects, how far each
part has progressed, what is owed on it, and the next action. A bundled script
validates the graph and generates a readable HTML page from it. The session log
is a short, factual record of what each session did, found and decided.

## Install

```
/plugin marketplace add dphipps4/claude-checkpoint
/plugin install checkpoint@checkpoint
```

## Use

```
/checkpoint:save
```

Saying "save checkpoint" or "checkpoint" also triggers it. In a project with no
graph yet, the skill first runs the script's `--init` mode, which creates a
minimal `docs/graph.json` and copies the default page template. It never
overwrites an existing file.

## What it writes

| File | What it is |
| --- | --- |
| `docs/graph.json` | The live state. Nodes have `id`, `type`, `label`, `stage`, `owed`, `next`, `updated` and an optional `note`; links are `{s, t, k}`. |
| `docs/graph.template.html` | The page template, copied once at init. Edit it to change the page's look. |
| `docs/knowledge-graph.html` | Generated from the JSON with the data inlined, so it opens from `file://`. Never edited by hand. |
| `sessions/YYYY-MM.md` | This month's session log, one dated entry per checkpoint. |

The script can also be run directly:

```
python3 scripts/build_graph.py <project_dir>           # validate, then build
python3 scripts/build_graph.py <project_dir> --check   # validate only
python3 scripts/build_graph.py <project_dir> --init    # start a new graph
```

A validation error (a duplicate id, a link to a missing node) exits non-zero and
fails the checkpoint.

## The session log standard

- Facts only: what was done (with PR numbers), what was found and how it was
  proven, decisions, what is open, the next step.
- Nothing personal, and nothing from other projects or repositories.
- Quoted decisions have their spelling and grammar corrected.
- Short: a few bullets per heading, with links to PRs and docs instead of
  repetition.
- Append only; earlier entries change only to fix spelling or remove something
  that breaks the standard.

## Requirements

Python 3.9 or later. No third-party packages.

## License

MIT
