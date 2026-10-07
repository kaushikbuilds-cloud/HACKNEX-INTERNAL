# AI Software Engineering Agent

Reads an existing codebase, understands how it works, makes a requested
change or fixes a bug, and verifies it didn't break anything that was
working before — all driven by a local LLM, with no API key required.

## How it works

```
Load repo  ->  Scan + index  ->  Describe the change  ->  Plan  ->
Generate code  ->  Apply + validate  ->  Self-heal on failure  ->
Commit (on success)  ->  Push (only with explicit confirmation)
```

1. **Repository analysis** — clones (or opens a local path), detects
   language/build tool/test command, maps the file structure.
2. **Code understanding** — parses every source file (AST-based chunking
   for Python, line-window chunking as a fallback for other languages),
   embeds each chunk with a lightweight offline hashing embedder (no model
   download needed), and indexes it for semantic search.
3. **Planning** — a single LLM call retrieves the relevant code and
   produces a structured plan: what the bug/feature is, its root cause,
   which files to touch, the steps, named risks, and a test strategy.
4. **Code generation** — the LLM rewrites each targeted file. For files
   over ~300 lines, it edits only the specific function/class the plan
   targets (located via the same embeddings index) and splices the result
   back in, rather than rewriting the whole file — this is what makes it
   viable on 10k+ line files and on a small local model's context window.
5. **Validation** — runs the existing test suite if there is one, plus
   **always-on static analysis and security scanning** across 6+
   languages (Python, JavaScript/TypeScript, Go, Ruby, PHP; Java for
   security patterns), since many real repos have thin or no test
   coverage. Every signal is diffed against a baseline captured *before*
   the agent touched anything — a repo's pre-existing issues are reported
   for visibility but never block a fix or tank its score.
6. **Self-healing retry** — on failure, the validation error is fed back
   into another code-generation attempt, up to 3 attempts. If it never
   converges, the branch is **rolled back** to the original state — no
   broken branch is left behind.
7. **Confidence score** (0.0–1.0) — a transparent heuristic over attempts
   needed, risks named, files touched, and any *new* static/security
   issues introduced by the change.
8. **Commit, then push only with explicit confirmation** — a successful
   fix is committed locally automatically. It is **never** pushed to
   GitHub without the user explicitly confirming (a two-step "Push to
   GitHub" → "Yes, push it" in the UI).

## Project structure

```
backend/
  repository/     clone, language/build-tool detection, AST chunking,
                   file classification, import dependency graph
  embeddings/      offline hashing embedder + in-memory vector store
  planner/         LLM planning agent + impact/file-selection views
  llm/             LLM client (Ollama), prompt builder, code generator,
                   confidence scorer, explanation builder
  patch/           diff generation, branch apply, git commit/push,
                   rollback
  testing/         test runner, static analyzer, security scanner,
                   baseline diffing, self-healing retry loop
  intelligence/    per-domain repo analyzers (backend/frontend framework,
                   API routes, database, config, docs, test coverage)
  reports/         test/patch/impact/repository-summary reports
  api/             FastAPI routes (repository, chat, patch, report)
  orchestrator.py  ties the whole pipeline together
  app.py           FastAPI app

frontend/
  app.py, pages/   Streamlit multipage app (Repository Loader, Chat
                   Panel, Code and Diff Viewer, Test Results, Repository
                   Profile)
  components/      reusable page sections
  services/        API client
  state/           centralized session state
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run a local LLM

The agent calls a local [Ollama](https://ollama.com) server by default —
no API key needed.

```bash
ollama pull qwen2.5-coder:3b     # or qwen2.5-coder:1.5b on a smaller GPU
```

### 3. Configure and launch

```bash
cp .env.example .env    # edit OLLAMA_MODEL to match what you pulled
python run.py
```

That's it — one command starts the backend, waits for it to be healthy,
then starts the frontend and opens `http://localhost:8501` in your
browser. Ctrl+C (or just closing the terminal) stops both cleanly.

Prefer running them separately (e.g. to watch backend logs on their own)?

```bash
# Terminal 1
export OLLAMA_MODEL=qwen2.5-coder:3b
uvicorn backend.app:app --port 8000

# Terminal 2
export OLLAMA_MODEL=qwen2.5-coder:3b
streamlit run frontend/app.py
```

### 4. Use it

1. **Repository Loader** — paste a git URL or local path, click **Load
   repository**. Auto-navigates to Chat Panel once loaded.
2. **Chat Panel** — describe the bug or feature in plain English, click
   **Run agent**.
3. **Code and Diff Viewer** — see exactly what changed, side-by-side or
   as a unified diff. If the fix passed validation, a **Push to GitHub**
   button appears (requires a second explicit confirmation).
4. **Test Results** / **Repository Profile** — baseline vs. final
   validation report, and the change's impact analysis.

## Configuration

Environment variables (all optional):

| Variable | Default | Purpose |
|---|---|---|
| `SWE_AGENT_LLM_BACKEND` | `ollama` | `ollama` or `echo` (no-op, for tests) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Model to use |
| `SWE_AGENT_WORKDIR` | `./workdir` | Where repos get cloned |
| `SWE_AGENT_MAX_RETRIES` | `3` | Self-healing retry attempts |

## Design decisions worth knowing

- **Whole-file vs. chunk-level editing**: small files are rewritten
  whole (simpler, more reliable at that size); files over 300 lines are
  edited at the function/class level and spliced back in, since a local
  model can't reliably rewrite a 10k-line file correctly or even fit it
  in context.
- **Baseline diffing everywhere**: a failing test suite, a pre-existing
  security finding, or an existing static-analysis warning in the repo
  is never counted against a fix — only *new* issues the change
  introduces are. This applies consistently to test pass/fail, security
  scanning, and static analysis.
- **No test suite ≠ failure**: many real repos (the one this was built
  against included) have no test command at all. That's treated as
  "nothing to validate with tests," not as a failing validation — static
  analysis and security scanning carry more weight in that case.
- **Deliberately not built**: property-based test generation (Hypothesis)
  and dynamic import of a target app's code (for OpenAPI/schema testing)
  were scoped out — both would execute arbitrary code from a repo this
  agent doesn't own, with adversarial or unvalidated inputs, which is a
  real safety risk on an untrusted public repo rather than just missing
  scope.

## Known limitations

- Static analysis and security scanning use each language's own
  toolchain (`node`, `ruby`, `php`, `gofmt`, `bandit`, `pyflakes`) and
  silently skip a language if that tool isn't installed — "OK" in that
  case means "nothing to check," not "verified safe."
- Non-Python security scanning is a small set of conservative regex
  patterns (eval, hardcoded secrets, shell injection, string-built SQL),
  not an AST-based tool like bandit — lower confidence by design, marked
  as such in every finding.
- Sessions are in-memory and single-process — fine for local/demo use,
  not for a multi-instance deployment.
