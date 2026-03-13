# Issue Intake Workflow

This document explains how `agents-63-issue-intake.yml` works — the workflow
that bridges GitHub issues into automated agent work.

## Overview

The issue intake workflow is the entry point for the agent automation system. It
operates in two distinct modes selected at runtime:

| Mode | Purpose |
|------|---------|
| `chatgpt_sync` | Bulk-create/update GitHub issues from an external topic list |
| `agent_bridge` | Bootstrap a PR so an agent can start work on a labeled issue |

---

## Triggers

The workflow fires on four event types:

| Event | Condition |
|-------|-----------|
| `issues: opened` | New issue created with an `agent:*` label |
| `issues: reopened` | Closed issue re-opened with an `agent:*` label |
| `issues: labeled` | `agent:*` or `agents:*` label applied to an issue |
| `issues: unlabeled` | `agent:*` or `agents:*` label removed — allows in-progress runs to be cancelled via the concurrency group |
| `workflow_dispatch` | Manual run from the Actions tab |
| `workflow_call` | Called by another workflow (e.g., orchestrator) |

**Guard condition**: The workflow skips automatically if the issue carries the
`agents:auto-pilot` label — that pipeline handles its own sequencing.

---

## Mode 1: `chatgpt_sync` — Bulk Issue Import

### When it runs

Triggered by a `workflow_dispatch` or `workflow_call` with `intake_mode: chatgpt_sync`.

### What it does

1. **Reads a topic list** from one of three sources (in priority order):
   - A file path inside the repository (`source` input)
   - A pasted text blob (`raw_input` input, capped at under 1 KB)
   - A public raw URL (`source_url` input, e.g. a GitHub Gist)

2. **Parses topics** into structured JSON using either:
   - A regex-based parser (`parse_chatgpt_topics.py`) — default
   - An LLM-based splitter via LangChain (`topic_splitter.py`) — when
     `apply_langchain_formatting: true`

3. **Deduplicates** topics by GUID or title (case-insensitive).

4. **Creates or updates GitHub issues** for each topic:
   - If a matching issue already exists (searched by GUID marker or title), it
     updates the title, body, and labels.
   - If no match is found, a new issue is created.
   - Issues already assigned to a non-Codex agent are skipped.
   - All `agent:*` labels are **stripped** before creation — apply them manually
     from the Issues tab to trigger agent workflows.

5. **Posts a workflow summary** with counts of created, updated, skipped, and
   duplicate topics.

### Topic file format

```
1) First issue title
Labels: enhancement, area:backend

Why
Brief explanation of the problem.

Tasks
- [ ] First task
- [ ] Second task

Acceptance criteria
- First criterion
```

See [`ISSUES.txt`](../ISSUES.txt) for a working example.

---

## Mode 2: `agent_bridge` — Bootstrap an Agent PR

### When it runs

Triggered automatically when an issue is labeled `agent:codex` (or any
`agent:<key>` label), or manually via `workflow_dispatch` /
`workflow_call` with `intake_mode: agent_bridge`.

### What it does

1. **Determines the agent key** from the issue's `agent:*` label (e.g.
   `agent:codex` → key `codex`).

2. **Calls the orchestrator** (`agents-70-orchestrator.yml`) or reusable bridge
   workflow with the resolved issue number and agent key.

3. The orchestrator then:
   - Creates a branch named `codex/issue-<number>`
   - Opens a draft PR linked to the source issue
   - Posts a `@codex start` comment to invite the agent (when
     `post_codex_comment: true`)

4. **The keepalive loop** (`agents-keepalive-loop.yml`) monitors the PR and
   continues nudging the agent until all task checkboxes are checked.

### Diagram

```
Issue labeled agent:codex
         │
         ▼
  agents-63-issue-intake.yml
  (agent_bridge mode)
         │
         ▼
  agents-70-orchestrator.yml
         │
         ├─ Creates branch: codex/issue-<N>
         ├─ Opens draft PR
         └─ Posts @codex start comment
                  │
                  ▼
         agents-keepalive-loop.yml
         (runs until tasks complete)
```

---

## Key Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `intake_mode` | Auto-detected | `chatgpt_sync` or `agent_bridge` |
| `source` | — | Repo-relative path to a topics file |
| `raw_input` | — | Pasted topic text (≤ 1 KB) |
| `source_url` | — | Public raw URL to a topics file |
| `issue_number` | From event | Issue number for `agent_bridge` mode |
| `bridge_agent` | `codex` | Agent key (derived from label, or explicit) |
| `bridge_draft_pr` | `false` | Open bootstrap PR as a draft |
| `post_codex_comment` | `true` | Auto-post `@codex start` after bootstrap |
| `apply_langchain_formatting` | `false` | Use LLM topic splitter instead of regex |
| `debug` | `false` | Emit verbose debug output and upload artifacts |

---

## Concurrency

Each run is scoped to the issue number (or run ID for dispatched runs):

```yaml
concurrency:
  group: issue-intake-${{ github.event.issue.number || github.run_id }}
  cancel-in-progress: true
```

This prevents duplicate bootstraps for the same issue if the workflow fires
twice in quick succession (e.g. multiple labels applied at once).

---

## Integration Points

| Component | How it connects |
|-----------|----------------|
| `agents-70-orchestrator.yml` | Called by `agent_bridge` to create the PR |
| `agents-keepalive-loop.yml` | Monitors the bootstrapped PR |
| `agents-issue-optimizer.yml` | Optional pre-step: formats issues before intake |
| `.github/ISSUE_TEMPLATE/agent_task.yml` | Provides the structured issue format |
| `docs/AGENT_ISSUE_FORMAT.md` | Describes the expected issue body structure |
| `docs/LABELS.md` | Lists all labels and their effects |

---

## Troubleshooting

### Workflow runs but no PR is created

- Verify the issue has an `agent:codex` (or other `agent:*`) label.
- Check that the issue does **not** have `agents:auto-pilot` — that label
  bypasses intake.
- Review the Actions run log for the `normalize_inputs` job to confirm
  `intake_mode` resolved to `agent_bridge`.

### `chatgpt_sync` creates no issues

- Ensure the input (`source`, `raw_input`, or `source_url`) is non-empty.
- If using `raw_input`, content over 1 KB may be silently truncated by the
  Actions UI, causing the parser to see incomplete input and produce no topics;
  prefer `source` for larger lists.
- Check the workflow summary for parse errors (exit codes 2–4 from the parser).

### Issues are updated instead of created

- The workflow searches for existing issues by GUID marker or exact title. If a
  match is found, it updates rather than creates. This is intentional to avoid
  duplicates on repeated syncs.

### Agent labels are missing from created issues

- In `chatgpt_sync` mode all `agent:*` / `agents:*` labels are stripped before
  issue creation. Apply `agent:codex` manually from the Issues tab to trigger
  the agent bridge.

---

*Source workflow: `.github/workflows/agents-63-issue-intake.yml`*
*Source of truth: [stranske/Workflows](https://github.com/stranske/Workflows)*
