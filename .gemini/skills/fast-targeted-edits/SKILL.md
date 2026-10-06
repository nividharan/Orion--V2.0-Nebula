---
name: fast-targeted-edits
description: MUST BE ACTIVATED whenever requested to make a code change, refactor, bug fix, feature update, or modification in an existing project. Enforces targeted analysis using sequentialthinking and filesystem MCP tools to prevent slow, full-codebase scans.
---

# Fast & Targeted Project Edits

## Purpose
Prevents slow, workspace-wide codebase scans during project change requests. Forces the assistant to reason step-by-step using **sequential thinking** and execute surgical file edits using **filesystem MCP tools**.

---

## Hard Rules

1. **Max 3 Files Policy:** Do NOT view or search more than 3 files unless strictly required by direct import dependencies.
2. **No Workspace Sweeps:** Never issue unconstrained codebase searches (grep, find, or multi-directory listing) when the target file or area is already known or predictable.
3. **No Speculative Reading:** Do NOT read surrounding files "just to check context". Only read files that directly contain code to be modified.

---

## Execution Protocol

### Step 1: Reason Tightly via sequentialthinking MCP
Before running any filesystem tool or search, invoke sequentialthinking:
- Thought 1: Analyze the request. Identify the specific file(s) or component(s) that need changes.
- Thought 2: Formulate the minimal path/search query needed to locate the target lines.
- Thought 3: Verify that no extra/unrelated files need to be opened.

### Step 2: Locate & Inspect via filesystem MCP
Using the filesystem MCP server:
- To locate target files: Call search_files with a targeted filename pattern (e.g., *.config.js or UserController.ts).
- To inspect code: Call read_text_file or read_file only on the identified file paths.

### Step 3: Apply Surgical Edits via filesystem MCP
- Call edit_file to modify only the target lines/blocks.
- Do NOT rewrite intact files or re-scan the codebase after the edit.

---

## Activation Conditions

### Activate When:
- User asks to "change X", "update Y", "fix bug in Z", "refactor code", or "add feature to existing project".
- Fast execution speed and minimal context usage are required.

### Do NOT Activate When:
- Creating a brand-new project from scratch.
- Explicitly requested to perform a full codebase security audit or architecture summary.
