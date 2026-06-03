# /init Parallel Ingest

Use this reference when `/init` is handing sources to parallel `/ingest-local-pdf` subagents and merging their work back.

## Pre-Fan-Out Safety

- Run `git status --short`.
- Treat files under `wiki/`, `raw/papers/`, `wiki/sources/`, and `.checkpoints/init-*.json` as scaffold files.
- Stash unrelated dirty files outside those paths.
- Verify `.gitattributes` contains `merge=union` for `wiki/log/*.md`, `wiki/graph/edges.jsonl`, `wiki/graph/citations.jsonl`, and `wiki/index.md`.
- Commit the scaffold before fan-out so `BASE_COMMIT` contains the generated pages and manifests that every worktree must inherit:

```shell
git add wiki/ raw/papers/ wiki/sources/ .checkpoints/init-prepare.json .checkpoints/init-sources.json
git commit -m "init: scaffold before parallel ingest" --no-gpg-sign
git rev-parse HEAD
```

- Treat the printed commit hash as `base_commit`. Record `stash_ref`, `base_branch`, and `base_commit` with `tools/research_wiki.py checkpoint-set-meta`.
- `/init` worktree mode requires a named branch; stop on detached HEAD.

## Worktree Creation

For each paper, choose a concrete worktree branch and path, then create the worktree from the scaffold commit on the current branch:

```shell
git worktree add -b init-<base-branch>-<rank>-<paper-slug> ../.worktrees/init-<base-branch>-<rank>-<paper-slug> <base-commit>
```

- Do not run `git worktree add` against the current branch name itself; Git will refuse because that branch is already checked out in the main workspace.
- Order papers by `shortlist_rank` from `.checkpoints/init-sources.json`, not by rescanning raw folders or by raw citation count.

## Subagent Prompt Contract

- The subagent's shell working directory must be the worktree path (`$WT_PATH`), not the main repository root. All relative paths resolve from there.
- Execute `/ingest-local-pdf` for exactly one relative source path.
- Do not bypass `/ingest-local-pdf`; it hands the prepared source to `/ingest`.
- In INIT MODE, consume the handed-off canonical path exactly as provided.
- Skip `fetch_literature.py citations`.
- Skip `fetch_literature.py references`.
- Skip per-subagent `rebuild-index`.
- Skip per-subagent `rebuild-context-brief`.
- Skip per-subagent `rebuild-open-questions`.
- Skip conflict-prone topic writes.
- Commit the result inside the worktree before exiting so fan-in merges a real ingest commit.

## Fan-In

After all agents complete:

1. Switch the main workspace back to `BASE_BRANCH` if needed, then merge worktree branches sequentially there in planner order.
2. Resolve true concept/claim conflicts conservatively: merge, do not multiply near-duplicates.
3. Merge only committed worktree branches. A branch with no ingest commit is an error to stop and fix, not something to merge through.
3. Run:

```shell
git switch <base-branch>
git merge --no-ff init-<base-branch>-<rank>-<paper-slug> --no-edit
git worktree remove ../.worktrees/init-<base-branch>-<rank>-<paper-slug>
git branch -d init-<base-branch>-<rank>-<paper-slug>
uv run python tools/research_wiki.py dedup-edges '@configured'
uv run python tools/research_wiki.py dedup-citations '@configured'
uv run python tools/research_wiki.py rebuild-index '@configured'
uv run python tools/research_wiki.py rebuild-context-brief '@configured'
uv run python tools/research_wiki.py rebuild-open-questions '@configured'
uv run python tools/lint.py --wiki-dir '@configured' --fix
```

If `stash_ref` exists, pop it at the end. If stash pop fails, keep the checkpoint and report the failure.
