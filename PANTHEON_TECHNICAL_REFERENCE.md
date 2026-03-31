# PANTHEON PLAGIARISM DETECTOR — TECHNICAL REFERENCE

> **Who this is for:** Anyone on the team, or anyone evaluating the project, who wants to understand how the system works end-to-end — from a professor clicking "Compare" to a similarity score appearing on screen. No deep prior knowledge required.

---

## PART 1 — WHAT IS PANTHEON?

Pantheon is a web application that helps university professors detect plagiarism in student code submissions. A professor creates a course, creates assignments, and students upload their code as ZIP files. The professor can then select any two submissions and ask Pantheon to compare them. The system runs a plagiarism detection analysis and returns a similarity score, a list of matching code blocks, and flags for obfuscation techniques the students may have used to disguise the copying.

The system has three major parts:

- **Frontend** — A web interface built in Next.js (TypeScript/React) running on Vercel. This is what professors and students see in their browser.
- **Backend** — A Python API server built with FastAPI, deployed on AWS. This handles authentication, file storage, database, and triggers the plagiarism engine.
- **Engine** — A pure Python plagiarism detection library embedded inside the backend. It takes two code files, runs analysis, and returns a structured result.

---

## PART 2 — HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                        BROWSER (Professor)                   │
│              Next.js Frontend (Vercel)                       │
│   - Login / Register                                         │
│   - Create courses, assignments                              │
│   - Upload submissions                                       │
│   - Click "Compare" → see similarity report                  │
└─────────────────────┬───────────────────────────────────────┘
                      │  HTTPS requests (JSON)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (AWS)                              │
│               FastAPI Python Server                          │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Auth Layer │  │  Route Layer │  │  Database Layer    │  │
│  │  (JWT)      │  │  (5 routers) │  │  (PostgreSQL)      │  │
│  └─────────────┘  └──────┬───────┘  └────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              PLAGIARISM ENGINE                        │   │
│  │  Ingest → Preprocess → Tokenize → Fingerprint        │   │
│  │  → Score → Evidence → Obfuscation → Result           │   │
│  └───────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐     │
│  │           AWS S3 (File Storage)                     │     │
│  │  Student ZIP files stored here                      │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## PART 3 — FILE CATEGORIES AND PURPOSE

All Python files in the project fall into seven logical categories.

---

### CATEGORY A — API SERVER ENTRY POINT

These files start the web server and wire everything together.

---

#### `Backend/Pantheon_API/main.py`
**What it does:** The front door of the entire backend. When the server starts, Python runs this file first. It creates the FastAPI application object and registers all five routers (auth, submissions, engine, assignments, courses) so the server knows which URL paths exist.

**Functions:**
| Function | What it does |
|----------|-------------|
| `health_check()` | Responds to GET `/health` with `{"status": "healthy"}`. Used by deployment systems to check if the server is alive. |

---

#### `Backend/Pantheon_API/config.py`
**What it does:** A central place for all configuration — database host/port/credentials, S3 bucket name, JWT secret key, and token expiry time. Every other file imports from here rather than hardcoding values.

No functions — just constants read by other modules.

---

### CATEGORY B — AUTHENTICATION AND DATABASE

These files handle who is allowed to do what, and how to talk to the database.

---

#### `Backend/Pantheon_API/auth.py`
**What it does:** Manages user login security. When a professor logs in, this file creates a JWT token (a signed digital pass) that the frontend stores and sends with every future request. Every protected route uses `get_current_user` to verify that token before doing anything.

**What is a JWT token?** A JSON Web Token is a small encrypted string that says "this request comes from user X with role Y, and this token expires at time Z." It is signed with a secret key so it cannot be faked.

**Functions:**
| Function | Parameters | What it does |
|----------|-----------|-------------|
| `hash_password(plain)` | plaintext password string | Runs the password through bcrypt (a one-way hash function). The original password is never stored. |
| `verify_password(plain, hashed)` | plaintext + stored hash | Checks if a plaintext password matches a stored hash. Used at login. |
| `create_token(user_id, role)` | user UUID + role string | Creates a signed JWT token containing the user's ID, role, and an expiry timestamp. |
| `get_current_user(creds)` | HTTP Authorization header | Reads the Bearer token from the request header, decodes it, and returns the user's info. If invalid or expired, rejects the request with 401. Used as a FastAPI dependency injected into every protected route. |

---

#### `Backend/Pantheon_API/database.py`
**What it does:** Provides a single function to create a connection to the PostgreSQL database running on AWS RDS. All database operations (reading, writing) happen through connections returned by this function.

**Functions:**
| Function | What it does |
|----------|-------------|
| `get_db_connection()` | Opens and returns a psycopg3 connection to PostgreSQL with SSL required. Called at the start of any database operation, used as a context manager (auto-closes on exit). |

---

### CATEGORY C — API ROUTE HANDLERS

These five files define the actual URL endpoints of the backend. Each file handles one domain of the application.

---

#### `Backend/Pantheon_API/routes_auth.py`
**Prefix:** `/auth`
**What it does:** Handles user accounts — registering new professors/students and logging in.

**Endpoints:**
| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/auth/register` | POST | Creates a new user. Checks email is not already taken, hashes the password, inserts into the `users` table. |
| `/auth/login` | POST | Finds user by email, verifies password hash, returns a JWT token if correct. |
| `/auth/role` | GET | Returns the role ("professor" or "student") of the currently logged-in user. Requires Bearer token. |

---

#### `Backend/Pantheon_API/routes_courses.py`
**Prefix:** `/courses`
**What it does:** CRUD operations for courses. Only professors can create, list, or delete courses.

**Endpoints:**
| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/courses/` | POST | Creates a new course record in the database. Professor only. |
| `/courses/` | GET | Lists all courses. Professor only. |
| `/courses/{course_id}` | GET | Returns course details including its assignments. |
| `/courses/{course_id}` | DELETE | Deletes a course and its associated data. |

**Helper:** `_require_professor(user)` — raises HTTP 403 if the user's role is not "professor". Called at the top of every endpoint in this file.

---

#### `Backend/Pantheon_API/routes_assignments.py`
**Prefix:** `/assignments`
**What it does:** CRUD operations for assignments within a course. Professor only.

**Endpoints:**
| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/assignments/` | POST | Creates a new assignment linked to a course. |
| `/assignments/course/{course_id}` | GET | Lists all assignments for a given course. |
| `/assignments/{assignment_id}` | GET | Gets one assignment's details and its submissions. |
| `/assignments/{assignment_id}` | DELETE | Deletes an assignment. |

---

#### `Backend/Pantheon_API/routes_submissions.py`
**Prefix:** `/submissions`
**What it does:** Handles student code upload. When a student submits their assignment, this file processes the upload, validates the ZIP file, stores it in S3, and records the submission in the database.

**Endpoints:**
| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/submissions/{assignment_id}` | POST | Accepts a ZIP file upload, validates it contains source code, uploads to S3, records in database. |

**Helper functions:**
| Function | What it does |
|----------|-------------|
| `_zip_contains_allowed_source(file_bytes)` | Opens the ZIP in memory and checks that at least one file inside has a recognized extension (.java, .cpp, .c, etc.). Rejects ZIPs with only PDFs, images, etc. |
| `_delete_s3_object_if_exists(bucket, key)` | If a previous submission exists in S3 for the same student/assignment, deletes it before storing the new one. |

---

#### `Backend/Pantheon_API/routes_engine.py`
**Prefix:** `/engine`
**What it does:** The most important route file. Handles the actual plagiarism comparison request. When a professor clicks "Compare" on two submissions, this is the file that runs.

**Endpoints:**
| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/engine/assignments/{assignment_id}/submissions` | GET | Lists all submissions for an assignment with their metadata. |
| `/engine/assignments/{assignment_id}/submissions/{submission_id}/download` | GET | Generates a temporary S3 download URL (valid 1 hour) for a submission ZIP. |
| `/engine/assignments/{assignment_id}/compare` | POST | **The main comparison endpoint.** Downloads both submissions from S3, runs the plagiarism engine, stores the result, returns the full JSON report. |
| `/engine/similarity-score` | GET | Retrieves the most recently stored similarity score for a given pair of submissions from the database (does NOT re-run the engine). |

**How `/compare` works step by step:**
1. Validates both submission IDs belong to the same assignment
2. Creates an `analysis_runs` record in the database (status = "running")
3. Downloads both ZIP files from S3 into a temporary directory
4. Calls `engine_compare(zip_a, zip_b)` — the full engine pipeline
5. Calls `format_report_as_json(raw_result)` to convert to frontend-ready JSON
6. Stores the similarity score in `similarity_results` table
7. Updates `analysis_runs` to status = "completed"
8. Returns the full JSON report to the frontend

---

### CATEGORY D — OUTPUT FORMATTING

These files convert the engine's raw Python dict result into formats humans and the frontend can use.

---

#### `Backend/Pantheon_API/format_output.py`
**What it does:** The bridge between the raw engine output (a deeply nested Python dictionary) and what the frontend needs to display. The engine returns data in its own internal format; this file translates it to the exact JSON shape the frontend's TypeScript types expect.

**Functions:**
| Function | What it does |
|----------|-------------|
| `_risk(score)` | Maps a 0.0–1.0 score to a risk label: CRITICAL (≥0.85), HIGH (≥0.65), MEDIUM (≥0.40), LOW (<0.40). |
| `format_report_for_backend(result)` | Formats the engine result as a plain-text human-readable report (used for debugging/CLI). Shows score, flags, and matching sections as formatted text. |
| `format_report_text(result)` | Alias for the above, kept for backwards compatibility. |
| `format_report_as_json(result)` | **Main function used by the API.** Converts the engine result into a JSON-serializable dict with exactly the fields the frontend expects: `submissionA`, `submissionB`, `language`, `similarityScore`, `similarityLevel`, `alterationTechniquesDetected`, `sections`, `High`, `Medium`, `Low`, `matches`, `fullCodeA`, `fullCodeB`. |
| `convert_to_old_format(result)` | Converts new engine output to a legacy format for backwards compatibility. |

---

#### `Backend/Pantheon_API/engine/report.py`
**What it does:** An alternative text formatter used by the CLI tools (`pantheon.py`, `cli/compare.py`). Produces a nicely formatted ASCII report for terminal output.

**Functions:**
| Function | What it does |
|----------|-------------|
| `format_report(result)` | Formats raw engine result as a structured text report with headers, score, obfuscation flags, and evidence blocks. |
| `save_report(result, path)` | Writes the formatted text report to a file on disk. |
| `_risk_level(score)` | Maps score to risk string. |
| `_pct(score)` | Formats float as percentage string (e.g. 0.97 → "97.0%"). |

---

#### `Backend/Pantheon_API/engine/report_html.py`
**What it does:** Generates a self-contained HTML file with a side-by-side code comparison, color-highlighted matches, and a visual similarity badge. Used for offline/downloadable reports.

**Functions:**
| Function | What it does |
|----------|-------------|
| `format_report_html(result)` | Builds a complete HTML page with embedded CSS, two-column code view, colored match highlights (4 severity levels), and metadata header. |
| `_score_to_level(score)` | Maps score to display level including "CLEAN" for low scores. |
| `escape_html(text)` | Escapes `<`, `>`, `&` characters so code containing HTML-like syntax is displayed safely. |
| `_error_html(result)` | Generates an error report HTML page when the engine fails. |

---

### CATEGORY E — THE PLAGIARISM ENGINE

This is the core of the system. Everything in `Backend/Pantheon_API/engine/` works together as a pipeline to analyze two code submissions. The engine is a standalone Python library — it does not know about the web server, the database, or S3. It just takes two file paths and returns a result dict.

The engine is organized into sub-packages, each handling one stage of the pipeline.

---

#### Entry Point: `engine/__init__.py`
**What it does:** Makes the engine importable as a package. Exposes only three things to the outside world: `compare`, `batch_analyze`, and `ENGINE_VERSION`. Everything else is internal.

```python
from engine import compare, batch_analyze, ENGINE_VERSION
```

---

#### Orchestrator: `engine/api.py`
**What it does:** The conductor of the entire engine. It does not do any analysis itself — it calls every other component in the right order and assembles the final result. Think of it as the manager who delegates to specialists.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `compare(path_a, path_b, ...)` | `_process_submission()`, `weighted_score()`, `compute_method_similarity()`, `build_evidence()`, `detect_obfuscation()`, `calculate_line_similarity()`, `build_line_mapping()`, `get_full_source_with_mapping()`, `_load_original_sources()` | **The main function.** Processes both submissions through the full pipeline and returns a complete result dict. |
| `batch_analyze(submissions, ...)` | `_process_submission()` (parallel), `weighted_score()`, `compute_method_similarity()`, `build_evidence()`, `detect_obfuscation()` | Runs all-vs-all comparison for a list of submissions using parallel threads. Returns ranked suspicious pairs above a threshold. |
| `_process_submission(path, work_dir)` | `ingest_to_dir()`, `canonicalize()`, `blank_output_boilerplate()`, `tokenize()` (×2), `winnow()` | Runs the full pre-analysis pipeline on ONE submission. Returns everything needed for comparison: canonical text, two token streams (normalized and raw), and fingerprints. |
| `_load_original_sources(work_dir, source_map)` | File system reads | Loads the original (pre-canonicalization) source files for display in the report. |
| `_subtract_fingerprints(fp, template_fp)` | — | Removes any fingerprint hash that also appears in the instructor template. Prevents template code from inflating similarity. |
| `_get_template_fingerprints(path, work_dir)` | `_process_submission()` | Processes the instructor template file to get its fingerprints for subtraction. |
| `_error_result(...)` | — | Constructs a standardized error response dict when something goes wrong. |

---

#### `engine/version.py`
**What it does:** Stores the engine version number (`ENGINE_VERSION = "3.1.0"`). Included in every result so the database can track which version of the engine produced each analysis.

---

#### `engine/exceptions.py`
**What it does:** Defines all the specific error types the engine can raise. Using specific exception types (rather than generic Python errors) allows the API layer to give professors meaningful error messages.

| Exception | When it's raised |
|-----------|-----------------|
| `EngineError` | Base class for all engine errors |
| `CorruptZipError` | The ZIP file cannot be opened (corrupted or not a real ZIP) |
| `EmptySubmissionError` | The ZIP contains no recognized source code files |
| `UnsupportedFileTypeError` | A single file (not ZIP) with an unsupported extension was uploaded |
| `ZipTooLargeError` | The ZIP is larger than the allowed size limit |
| `ZipBombError` | The ZIP has a suspicious compression ratio (e.g. 1KB compressed → 1GB decompressed) — a known attack |
| `PathTraversalError` | A file inside the ZIP has a path like `../../etc/passwd` — a known attack |
| `NestedZipDepthError` | ZIPs nested more than 3 levels deep (another zip bomb variant) |

---

### CATEGORY F — ENGINE PIPELINE STAGES

The engine processes submissions through eight stages in order. Here is each stage as its own file.

---

#### STAGE 1 — INGEST: `engine/ingest/ingest.py`

**Plain English:** The first thing the engine does is open the student's ZIP file safely and pull out the source code files. "Safely" is important here — students could intentionally or accidentally upload malicious ZIP files.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `ingest_to_dir(upload_path, out_dir)` | `_extract_zip()`, `_collect_source_files()`, `detect_language()` | **Main entry point for this stage.** Takes the path to a ZIP file (or single source file), extracts it safely to a temp directory, collects all source files, and returns them with a detected language. |
| `_extract_zip(zip_path, dest, depth=0)` | `_sanitize_zip_entry()`, recursive self-call | Opens the ZIP, checks every entry for security issues, extracts files, handles nested ZIPs (up to depth 3). |
| `_sanitize_zip_entry(entry_name, dest)` | — | Validates that a ZIP entry's path does not escape the destination directory. Blocks path traversal attacks like `../../sensitive_file`. |
| `detect_language(files)` | — | Counts file extensions (.java, .cpp, .c, .py, etc.) and returns the most common language. |
| `_collect_source_files(root)` | — | Walks the extracted directory tree and returns all files with recognized source code extensions. |
| `_try_detect_language_by_content(filepath)` | — | For files without extensions, looks inside the file for language-specific keywords to guess the language. |

**Security checks performed:**
- ZIP too large? → `ZipTooLargeError`
- Compression ratio suspicious? → `ZipBombError`
- Path tries to escape? → `PathTraversalError`
- Contains a symlink? → Silently skipped
- Nested ZIP too deep? → `NestedZipDepthError`
- No source files found? → `EmptySubmissionError`

---

#### STAGE 2 — CANONICALIZE: `engine/preprocess/canonicalize.py`

**Plain English:** After extraction, the source files are raw student code with comments, imports, and various syntax styles. This stage normalizes all of that into a single clean text. It also records a "source map" — a table that remembers which lines in the cleaned text came from which line in which original file. This source map is used later to show professors the original line numbers when displaying evidence.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `canonicalize(source_files, out_dir, lang)` | `strip_comments()`, `filter_boilerplate()`, `_normalize_control_flow()`, `_strip_trailing_whitespace()` | **Main entry point.** Reads all source files, applies all normalizations, concatenates them into one text, records the source map, writes `canonical.txt`. Returns a `CanonicalResult`. |
| `_normalize_switch_to_ifelse(text)` | — | Converts `switch(x) { case A: ...; break; }` to equivalent `if (x == A) { ... }` so switch and if-else implementations of the same logic match. |
| `_normalize_control_flow(text, lang)` | `_normalize_switch_to_ifelse()` | Also normalizes: `i++` → `i += 1`, `x += y` → `x = x + y`, ternary `? :` → if-else, redundant boolean returns. |
| `_strip_trailing_whitespace(text)` | — | Removes trailing spaces/tabs from every line. |
| `_detect_file_lang(path)` | — | Maps file extension to language string for per-file language handling in multi-file submissions. |
| `_strip_control_chars(text)` | — | Removes null bytes and other invisible control characters that can appear in some editors' output. |

**Data structures produced:**
- `CanonicalResult` — contains `canonical_text` (the cleaned combined source), `source_map` (line mapping back to original files), and `canonical_path` (path to saved canonical.txt)
- `SourceMapEntry` — records: for canonical lines X to Y, the original file is F.java starting at line 1

**Why this step matters:** Without normalization, `switch` and `if-else` versions of the same code would look different to the fingerprinter. By converting both to the same form, the engine catches this common obfuscation technique before fingerprinting even begins.

---

#### STAGE 3 — STRIP COMMENTS: `engine/preprocess/strip_comments.py`

**Plain English:** This step is called from within `canonicalize`. Comments are removed from the code because they do not reflect algorithmic logic and would create false positives (two students who both wrote `// check if null` would match even if their actual code is different).

**Critically, comments are replaced with blank lines, not deleted.** This preserves line numbering. If a comment was on line 10, line 10 becomes blank but still exists. This way, when we later say "evidence is on lines 5–20," those line numbers still match what the professor sees in the original file.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `strip_comments(text, lang)` | `_strip_c_family()`, `_strip_python()`, `_strip_ruby()` | Routes to the correct stripper based on language. |
| `_strip_c_family(text, lang)` | — | Handles Java, C, C++ comment styles: `//` single-line and `/* */` multi-line. Also handles preprocessor `#define` / `#include` directives. |
| `_strip_python(text)` | — | Handles Python `#` comments and triple-quoted `"""docstrings"""`. |
| `_strip_ruby(text)` | — | Handles Ruby `#` comments and `=begin`/`=end` blocks. |

---

#### STAGE 4 — FILTER BOILERPLATE: `engine/preprocess/stdlib_filter.py`

**Plain English:** After comments are gone, this step removes code that every student writes identically because it's required by the language or the assignment structure — not because they copied. Examples: `import java.util.*`, `#include <stdio.h>`, `System.out.println(...)`.

There are two types of filtering done here:

1. **Hard removal** (during canonicalization): Imports, package declarations, annotations like `@Override`. These lines are replaced with blank lines to keep line count consistent.

2. **Blanking for fingerprinting only** (called separately in `api.py`): System.out calls, `main()` declarations, single-line null guards, `this.field = param` assignments. These are ONLY blanked in the fingerprinting copy of the text. The display copy keeps them so professors see the full original code.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `filter_boilerplate(text, lang)` | `filter_java_boilerplate()`, `filter_c_boilerplate()`, `filter_python_boilerplate()`, `filter_js_boilerplate()` | Routes to the appropriate language filter. |
| `filter_java_boilerplate(text)` | — | Removes Java `import`, `package`, `@Override`, `@SuppressWarnings` etc. |
| `filter_c_boilerplate(text)` | — | Removes `#include <stdlib.h>` type includes and `#pragma once`. |
| `filter_python_boilerplate(text)` | — | Removes `import os`, `from sys import` etc. for standard library modules. |
| `filter_js_boilerplate(text)` | — | Removes `import` and `require()` for Node.js built-in modules. |
| `blank_output_boilerplate(text, lang)` | — | **Used in `api.py` before fingerprinting.** Blanks (empties) lines containing `System.out.println(...)`, `printf(...)`, `cout <<`, `int main()`, single-line null guards. These have no algorithmic meaning and would create false-positive fingerprint matches. |

---

#### STAGE 5 — TOKENIZE: `engine/tokenize/lex.py`

**Plain English:** At this point the code is clean text. Now it needs to be broken into tokens — the individual meaningful units that a programming language is made of. Words like `if`, `while`, `{`, `return` are tokens. Variable names are tokens. Numbers are tokens.

The tokenizer produces two versions: one where all variable names are replaced with the generic word `ID` and all numbers with `NUM` (normalized), and one that keeps the real names (raw). The normalized version is used for detecting plagiarism regardless of variable renaming. The raw version is used for detecting whether renaming happened.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `tokenize(text, lang, normalize_ids, normalize_literals, normalize_access)` | `_kw_set()` | Scans the source code character by character, identifying tokens. Returns a list of `Token` objects. When `normalize_ids=True`, all identifiers (variable names, method names) become `"ID"`. When `normalize_literals=True`, all numbers become `"NUM"`, strings become `"STR"`. When `normalize_access=True`, Java/C++ access modifiers (`public`, `private`, `protected`) are stripped. |
| `_kw_set(lang)` | — | Returns the set of reserved keywords for a language (e.g. Java keywords: `for`, `while`, `class`, `return`, etc.) so the tokenizer can distinguish keywords from identifiers. |

**Data class:**
- `Token(text, line)` — a frozen (immutable) pair of the token's text and the line number it was on in the canonical text.

**Two passes are made in `api.py`:**
- `tok_norm` = `tokenize(..., normalize_ids=True, normalize_literals=True)` — for similarity scoring
- `tok_raw` = `tokenize(..., normalize_ids=False, normalize_literals=False)` — for obfuscation detection

---

#### STAGE 6 — FINGERPRINT: `engine/fingerprint/kgrams.py`

**Plain English:** After tokenization we have a list of thousands of tokens. We cannot compare every possible arrangement — that would be too slow. Instead, we use a mathematical technique called **Winnowing** to create a compact set of "fingerprints" that represent the submission. Two submissions that share the same code will share the same fingerprints.

**How it works:**
1. Slide a window of 10 tokens at a time across the token list
2. Hash each 10-token window into a number (a fingerprint)
3. From every 5 consecutive fingerprints, keep only the one with the smallest value
4. The selected fingerprints form the submission's "fingerprint set"

This guarantees: if two submissions share any token sequence of 14+ tokens, at least one matching fingerprint will definitely be selected from both — they will have that fingerprint in common.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `winnow(tokens, k=10, window=5)` | `_poly_hash()`, `build_fingerprints()` | **Main fingerprinting function used for scoring.** Applies the Winnowing algorithm. Returns a dict: `{hash_value: [list of token positions where this hash occurs]}`. Keeps ~20% of all possible k-grams. |
| `build_fingerprints(tokens, k=8)` | `_poly_hash()` | Builds ALL k-gram fingerprints without Winnowing selection. Used for method-level comparison in `chunk.py` where you want complete coverage within a method body. |
| `_poly_hash(tokens)` | — | Computes a polynomial rolling hash of a sequence of token strings. Converts the token sequence to a single integer. Uses a Mersenne prime for good distribution. |

**What is a fingerprint dict?**
```
{
  hash_value_1: [position_3, position_47, position_102],  ← this 10-gram appeared 3 times
  hash_value_2: [position_22],                            ← this 10-gram appeared once
  ...
}
```
The positions tell us exactly where in the token stream each fingerprint occurs, which later translates back to line numbers.

---

### CATEGORY G — SIMILARITY ANALYSIS

Once both submissions have been fingerprinted, these three files perform the actual comparison and compute scores.

---

#### `engine/similarity/scores.py`

**Plain English:** This file answers the question: "How similar are the two fingerprint sets?" It uses three mathematical formulas and combines them into a weighted final score.

**Why three formulas?** Each captures a different aspect of similarity:
- **Jaccard** — How much overlap is there out of everything combined? Good for comparing two submissions of similar size.
- **Dice** — Similar to Jaccard but gives more weight to the shared fingerprints. Slightly more sensitive.
- **Containment** — What fraction of the smaller submission appears in the larger? This is the most important metric for catching partial plagiarism. If a student copies 80% of their short assignment from someone else's long assignment, Jaccard is 40%, but Containment is 80%.

**Functions:**
| Function | Formula | What it does |
|----------|---------|-------------|
| `jaccard(fp_a, fp_b)` | `\|A ∩ B\| / \|A ∪ B\|` | Fraction of combined unique fingerprints that are shared |
| `dice(fp_a, fp_b)` | `2 * \|A ∩ B\| / (\|A\| + \|B\|)` | Symmetric overlap weighted by total count |
| `containment(fp_a, fp_b)` | `\|A ∩ B\| / min(\|A\|, \|B\|)` | What fraction of the smaller submission's fingerprints appear in the other |
| `weighted_score(fp_a, fp_b)` | `0.35*J + 0.25*D + 0.40*C` | Combines all three. Returns a dict with all four values. Containment weighted highest at 40%. |

---

#### `engine/similarity/chunk.py`

**Plain English:** The global fingerprint score can miss plagiarism if a student copied all the methods but reordered them. Imagine submission A has methods in order: `insert`, `delete`, `search`. Submission B has them in order: `search`, `insert`, `delete`. The fingerprints for each method match, but because they appear at very different positions in the file, the global comparison can be diluted.

This file solves that by comparing method by method — it extracts each method body individually and finds the best-matching method in the other submission.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `_extract_method_chunks(tokens, gram_k)` | `build_fingerprints()` | Finds all method bodies in the token stream by looking for `{` that immediately follows `)`. Walks to the matching `}` counting brace depth. Returns the fingerprint set for each method body. |
| `compute_method_similarity(tok_a, tok_b, gram_k)` | `_extract_method_chunks()`, `jaccard()`, `containment()` | For each method in A, finds the best-matching method in B (using the higher of Jaccard and Containment). Returns a weighted average where the best-matching pair counts most (harmonic weighting). |

**How method similarity is used in `api.py`:**
If the method-level similarity is more than 0.15 higher than the global score, the final score is boosted: `boosted = 0.65 × method_sim + 0.35 × global_score`. This catches cases where method reordering diluted the global score.

---

#### `engine/similarity/line_matcher.py`

**Plain English:** While the scores above tell us HOW SIMILAR the submissions are, this file produces the data for showing WHERE they are similar — specifically, which line in submission A corresponds to which line in submission B, and how strongly.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `calculate_line_similarity(tokens_a, tokens_b, fp_a, fp_b, k)` | — | For every line in submission A that has shared fingerprints with B, computes a similarity score: `shared_fingerprints_on_this_line / total_fingerprints_on_this_line`. Also finds which line in B is the best match for each line in A. |
| `build_line_mapping(tokens_a, tokens_b, line_similarity_a)` | — | Converts the per-line scores into a list of `{line_a, line_b, score, color}` dicts. Color is determined by score: red (≥75%), orange (≥55%), yellow (≥35%), green (≥20%). |
| `get_full_source_with_mapping(source_a, source_b, line_mapping)` | — | Packages the full source code of both submissions together with the line mapping data, ready for use in HTML visualization. |

---

### CATEGORY H — EVIDENCE AND OBFUSCATION

These two files produce the two most human-readable outputs: what specific code blocks are suspicious, and what cheating techniques were used.

---

#### `engine/evidence/evidence.py`

**Plain English:** The fingerprint scores tell us a number (e.g. 85% similar). The evidence system translates that number into something concrete a professor can look at: "Lines 24–67 of submission A match lines 31–74 of submission B — here is the actual code from both sides."

It works by finding all shared fingerprints, converting their token positions to line numbers, merging blocks that are close together, and loading the actual source code for those lines.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `build_evidence(fp_a, fp_b, tok_a, tok_b, source_map_a, source_map_b, k, merge_gap, ...)` | `_token_line()`, `_canonical_line_to_source()`, `_load_source_lines()`, `_slice_code()`, `_match_strength()` | **Main function.** Takes shared fingerprints → converts to line positions → merges nearby matches → maps back to original files → loads actual code snippets → returns list of evidence blocks. |
| `_canonical_line_to_source(canonical_line, source_map)` | — | Given a line number in the canonical (cleaned) text, returns which original file and line number that corresponds to. Uses the source map built during canonicalization. |
| `_token_line(tokens, idx)` | — | Returns the line number of the token at a given position in the token list. |
| `_load_source_lines(work_dir, filename)` | — | Reads the original source file (before any processing) from disk and returns its lines. |
| `_slice_code(lines, start, end)` | — | Extracts lines start through end (1-indexed) from a line list. Handles edge cases (clamping to file bounds). |
| `_match_strength(token_count)` | — | Classifies a block as "high" (≥40 tokens), "medium" (≥15), or "low" (<15). |

**Merge logic:** Two match blocks are merged into one if:
- They are within 3 lines of each other on both sides simultaneously
- The B-side is moving forward (prevents merging unrelated blocks)
- This handles cases where a few unrelated lines (blank lines, closing braces) interrupt an otherwise continuous copied block

**Filter:** Blocks that span fewer than 3 lines (on either side) are discarded. This prevents single-line common patterns (like `return;`) from appearing as evidence.

---

#### `engine/obfuscation/detect.py`

**Plain English:** Some students try to disguise plagiarism by making surface-level changes: renaming variables, changing `for` loops to `while`, adding useless `try-catch` blocks. This file detects those tactics by comparing what the code looks like with normalization vs. without.

**The core idea:** If the normalized score (where all variable names are replaced with `ID`) is much higher than the raw score (where names are kept), the student likely renamed their variables to hide copying.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `detect_obfuscation(tok_a_raw, tok_b_raw, tok_a_norm, tok_b_norm, fp_a_norm, fp_b_norm)` | `build_fingerprints()`, `jaccard()`, `_count_loop_types()`, `_loops_swapped()`, `_count_enhanced_for()` | **Main function.** Runs all 9 checks and returns a list of detected technique names. |
| `_count_loop_types(tokens)` | — | Counts how many `for`, `while`, and `do` keywords appear in a token stream. |
| `_loops_swapped(a_counts, b_counts)` | — | Returns True if one submission uses mostly for-loops and the other uses mostly while-loops (ratio differs by >50%). |
| `_count_enhanced_for(tokens)` | — | Counts Java for-each loops by looking for `:` inside a `for(...)` header. |

**The 9 detected techniques:**

| Flag Name | How It's Detected |
|-----------|------------------|
| `identifier_renaming` | `norm_score - raw_score > 0.12` AND `norm_score > 0.3` — normalized similarity much higher than raw |
| `loop_type_swap` | One uses mostly `for`, other uses mostly `while`/`do-while`, at similar normalized similarity |
| `literal_substitution` | Code structure matches (high norm score) but literal values overlap < 30% |
| `dead_code_insertion` | One submission has 25%+ more tokens than the other at high normalized similarity |
| `code_reordering` | Average position delta of shared fingerprints > 0.25 (fingerprints appear far from their expected positions) |
| `switch_to_ifelse` | One has a `switch` statement, other has significantly more `if` statements at same coverage |
| `ternary_to_ifelse` | One uses `?` ternary operators, other has zero |
| `exception_wrapping` | One has 2+ more `try` blocks than the other at high similarity |
| `for_each_to_indexed` | One uses Java for-each (`for (Type x : list)`), other uses indexed loop |

---

### CATEGORY I — COMMAND-LINE TOOLS

These files are not part of the web API — they are standalone scripts for testing and running the engine from a terminal.

---

#### `compare.py` (root of project)

**What it does:** The simplest way to test the engine locally. Run it as `python3 compare.py file_a.java file_b.zip` and it prints the full JSON report to the terminal. It adds the `Backend/Pantheon_API` directory to Python's path so it can find the engine package, then calls the same `compare()` function the web API uses.

**Functions:**
| Function | What it does |
|----------|-------------|
| `resolve_file(name)` | Checks if the given filename exists as-is; if not, looks for it in the `samples/` directory. Allows running `python3 compare.py BST_original.java BST_copied.java` without specifying full paths. |

---

#### `Backend/Pantheon_API/pantheon.py`

**What it does:** A richer CLI tool for local testing. Supports comparing two files, or running all-vs-all comparison on an entire folder. Also supports `--json` for JSON output and `--html` for generating an HTML report.

**Functions:**
| Function | Calls | What it does |
|----------|-------|-------------|
| `main()` | `compare()`, `batch_analyze()`, `format_report_as_json()`, `format_report_html()`, `format_report()` | Parses command-line arguments. If 2 files given: runs single comparison. If 3+ files given: runs all-vs-all and shows top 5 most similar pairs sorted by score. |
| `find_file(name)` | — | Finds a file by name, checking the samples directory. |
| `list_samples()` | — | Lists all files in the `samples/` directory with their extensions. |

---

#### `engine/cli/compare.py` and `engine/cli/batch.py`

**What they do:** These are alternative CLI entry points inside the engine package. `compare.py` is for single pairwise comparison with more options (assignment ID, custom workdir, save to file). `batch.py` is for batch all-vs-all from a folder, outputting a JSON file with all suspicious pairs ranked by score.

Both call the same engine functions (`compare()` and `batch_analyze()`) as the web API — the engine is completely identical regardless of how it's invoked.

---

## PART 4 — THE COMPLETE PIPELINE: FROM CLICK TO RESULT

This section traces the full journey of a comparison request from the professor's browser to the similarity score on screen.

```
PROFESSOR CLICKS "Compare" IN BROWSER
              │
              ▼
┌─────────────────────────────────────────────────┐
│  FRONTEND (Next.js)                             │
│  POST /api/engine/assignments/{id}/compare      │
│  Body: { submission_a_id, submission_b_id }     │
│  Header: Bearer <JWT token>                     │
└─────────────────────┬───────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────┐
│  routes_engine.py — compare_two_submissions()   │
│                                                 │
│  1. get_current_user() → validate JWT           │
│  2. _require_professor() → check role           │
│  3. Query DB → get S3 keys for both ZIPs        │
│  4. INSERT analysis_runs (status="running")     │
│  5. s3.download_file() → ZIP A to /tmp          │
│  6. s3.download_file() → ZIP B to /tmp          │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  engine/api.py — compare()                      │
│                                                 │
│  calls _process_submission() for EACH ZIP       │
└─────────────────────┬───────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   Submission A             Submission B
   _process_submission()    _process_submission()
          │                       │
          ▼                       ▼
   ┌─────────────────────────────────────────┐
   │  STAGE 1: ingest_to_dir()               │
   │  • Validate ZIP security                │
   │  • Extract files to temp dir            │
   │  • Detect language (Java/C/C++/etc.)    │
   └──────────────────┬──────────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────────┐
   │  STAGE 2: canonicalize()                │
   │  • strip_comments() — remove // and /* */│
   │  • filter_boilerplate() — remove imports │
   │  • _normalize_control_flow()            │
   │    – switch → if-else                   │
   │    – i++ → i += 1                       │
   │    – ternary → if-else                  │
   │  • Build source_map (canonical↔original)│
   └──────────────────┬──────────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────────┐
   │  STAGE 3: blank_output_boilerplate()    │
   │  • Blank System.out / printf / cout     │
   │  • Blank main() declaration             │
   │  • Blank single-line null guards        │
   │  → produces fp_text (fingerprint copy)  │
   └──────────────────┬──────────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────────┐
   │  STAGE 4: tokenize() × 2               │
   │  tok_norm: IDs→"ID", nums→"NUM"         │
   │  tok_raw:  keep all real names          │
   └──────────────────┬──────────────────────┘
                      │
                      ▼
   ┌─────────────────────────────────────────┐
   │  STAGE 5: winnow(tok_norm, k=10, w=5)   │
   │  • Hash every 10-token window           │
   │  • Keep minimum hash in each 5-window   │
   │  • Produces fingerprint dict            │
   │    {hash → [token positions]}           │
   └──────────────────┬──────────────────────┘
                      │
          ┌───────────┘
          ▼ (both submissions now processed)

┌─────────────────────────────────────────────────┐
│  STAGE 6: SIMILARITY SCORING                    │
│                                                 │
│  weighted_score(fp_a, fp_b)                     │
│  • jaccard()     → 0.35 weight                  │
│  • dice()        → 0.25 weight                  │
│  • containment() → 0.40 weight                  │
│  → scores dict {jaccard, dice, containment,     │
│                 weighted_final}                  │
│                                                 │
│  compute_method_similarity(tok_a_norm, tok_b_norm)│
│  • _extract_method_chunks() on each             │
│  • Compare each method A vs each method B       │
│  • Harmonic-weighted best-match average         │
│  → method_similarity float                      │
│                                                 │
│  IF method_sim > weighted_final + 0.15:         │
│    boost: 0.65*method_sim + 0.35*weighted_final  │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  STAGE 7: EVIDENCE EXTRACTION                   │
│                                                 │
│  build_evidence(fp_a, fp_b, tok_a, tok_b,       │
│                 source_map_a, source_map_b, ...)│
│                                                 │
│  • Find shared fingerprint hashes               │
│  • Map token positions → canonical line numbers │
│  • Merge blocks within 3-line gap               │
│  • Filter blocks spanning < 3 lines             │
│  • _canonical_line_to_source() → original lines │
│  • _load_source_lines() → actual code snippets  │
│  • _match_strength() → HIGH/MEDIUM/LOW          │
│  → list of evidence blocks                      │
│    [{file_a, lines_a, code_a,                   │
│      file_b, lines_b, code_b, strength}]        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  STAGE 8: OBFUSCATION DETECTION                 │
│                                                 │
│  detect_obfuscation(tok_a_raw, tok_b_raw,       │
│                     tok_a_norm, tok_b_norm,      │
│                     fp_a_norm, fp_b_norm)        │
│                                                 │
│  • Build raw fingerprints (k=8) for both        │
│  • raw_score = jaccard(fp_a_raw, fp_b_raw)      │
│  • norm_score = jaccard(fp_a_norm_8, fp_b_norm_8)│
│  • Run 9 checks → list of flag names            │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  STAGE 9: LINE MAPPING                          │
│                                                 │
│  calculate_line_similarity() → per-line scores  │
│  build_line_mapping() → [{line_a, line_b,       │
│                           score, color}]        │
│  get_full_source_with_mapping() → packaged data │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  engine/api.py — returns raw result dict        │
│  {engine_version, scores, evidence,             │
│   obfuscation_flags, line_mapping,              │
│   original_sources_a, original_sources_b, ...} │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  format_output.py — format_report_as_json()     │
│  Translates raw dict → frontend JSON shape:     │
│  {similarityScore, similarityLevel,             │
│   sections, High, Medium, Low,                  │
│   matches: [{fileA, linesA, codeA, ...}],       │
│   fullCodeA: {filename: source},                │
│   fullCodeB: {filename: source}}                │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  routes_engine.py (resumed)                     │
│  • Store score in similarity_results table      │
│  • UPDATE analysis_runs status="completed"      │
│  • Return JSON report to frontend               │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS response
                   ▼
┌─────────────────────────────────────────────────┐
│  FRONTEND (Next.js)                             │
│  report_types.ts — mapReport(json)              │
│  • Maps JSON fields to ComparisonReport type    │
│  buildHighlightMap(matches, fileName, side)     │
│  • Builds line→severity map from evidence blocks│
│  AssignmentView.tsx — renders:                  │
│  • Similarity score badge                       │
│  • Obfuscation flags list                       │
│  • "Match Blocks" tab — evidence code snippets  │
│  • "Full Code" tab — side-by-side highlighted   │
└─────────────────────────────────────────────────┘

PROFESSOR SEES:
  • "97.0% — CRITICAL"
  • Alteration Techniques Detected: [Identifier renaming]
  • 69 matching sections (30 HIGH / 39 MEDIUM / 0 LOW)
  • Side-by-side highlighted code view
```

---

## PART 5 — HOW THE DATABASE IS USED

The PostgreSQL database stores everything except the actual ZIP files (those go to S3). The main tables and what gets written/read in each operation:

| Table | Written By | Read By | What It Stores |
|-------|-----------|---------|---------------|
| `users` | `routes_auth.py / register` | `routes_auth.py / login` | Email, hashed password, role |
| `courses` | `routes_courses.py / create_course` | `routes_courses.py / list`, `get_course` | Course name, linked professor |
| `assignments` | `routes_assignments.py / create_assignment` | `routes_assignments.py / list, get` | Assignment name, due date, course link |
| `submissions` | `routes_submissions.py / upload_submission` | `routes_engine.py / compare` | Student ID, assignment ID, S3 bucket+key, upload time, status |
| `artifacts` | `routes_submissions.py / upload_submission` | `routes_engine.py / compare` | S3 bucket and key for the stored ZIP |
| `analysis_runs` | `routes_engine.py / compare` | — | Tracks each comparison run: who initiated it, which engine version, status (running/completed/failed), timestamps |
| `analysis_run_submissions` | `routes_engine.py / compare` | — | Junction table linking a run to the two submissions it compared |
| `similarity_results` | `routes_engine.py / compare` | `routes_engine.py / get_similarity_score` | The final similarity score (0.0–1.0) for a submission pair, linked to its run |

---

## PART 6 — HOW S3 FILE STORAGE WORKS

Amazon S3 is used as a file storage system for student ZIP submissions. The backend never stores ZIPs on its own disk permanently.

**Upload flow:**
1. Student uploads ZIP to `POST /submissions/{assignment_id}`
2. `routes_submissions.py` reads the file into memory, validates it
3. Calls `boto3.client("s3").upload_fileobj(...)` to store it in S3
4. Records the S3 bucket name and object key in the `artifacts` table

**Compare flow:**
1. `routes_engine.py` looks up the S3 keys from the database
2. Calls `s3.download_file(bucket, key, local_path)` to download both ZIPs to a temp directory
3. Passes the local paths to the engine
4. After the engine finishes, the temp directory is deleted automatically (`tempfile.TemporaryDirectory` context manager)

**Download flow:**
1. `GET /engine/assignments/{id}/submissions/{id}/download`
2. `routes_engine.py` calls `s3.generate_presigned_url(...)` — creates a temporary URL valid for 1 hour
3. Returns that URL to the frontend
4. The frontend redirects the browser to that URL to download the file directly from S3

This design means the backend never serves large files — S3 handles the actual file transfer.

---

## PART 7 — THE AUTHENTICATION FLOW

```
PROFESSOR LOGS IN
       │
       ▼
POST /auth/login
  → routes_auth.py
  → SELECT user from DB by email
  → verify_password(plain, hashed_from_db)
  → If match: create_token(user_id, role)
  → Return: {"token": "eyJ..."}
       │
       ▼
FRONTEND stores token in memory/localStorage

EVERY SUBSEQUENT REQUEST:
  → Header: "Authorization: Bearer eyJ..."
       │
       ▼
  → get_current_user() called (FastAPI dependency)
  → Decodes JWT, extracts user_id and role
  → Returns: {"user_id": "...", "role": "professor"}
       │
       ▼
  → _require_professor() checks role
  → If "professor": proceed
  → If "student": raise HTTP 403 Forbidden
```

---

## PART 8 — QUICK REFERENCE: FUNCTION CALL MAP

This shows which function calls which, organized by pipeline stage.

```
routes_engine.compare_two_submissions()
  └── auth.get_current_user()
  └── database.get_db_connection()
  └── boto3.s3.download_file()          (×2)
  └── engine.compare()                  ← engine/api.py
        └── _process_submission()       (×2, one per submission)
              └── ingest.ingest_to_dir()
                    └── _extract_zip()
                          └── _sanitize_zip_entry()
                    └── _collect_source_files()
                    └── detect_language()
              └── canonicalize.canonicalize()
                    └── strip_comments.strip_comments()
                    └── stdlib_filter.filter_boilerplate()
                    └── _normalize_control_flow()
                          └── _normalize_switch_to_ifelse()
              └── stdlib_filter.blank_output_boilerplate()
              └── lex.tokenize()         (×2: norm + raw)
              └── kgrams.winnow()
        └── scores.weighted_score()
              └── scores.jaccard()
              └── scores.dice()
              └── scores.containment()
        └── chunk.compute_method_similarity()
              └── chunk._extract_method_chunks()
                    └── kgrams.build_fingerprints()
              └── scores.jaccard()
              └── scores.containment()
        └── evidence.build_evidence()
              └── evidence._token_line()
              └── evidence._canonical_line_to_source()
              └── evidence._load_source_lines()
              └── evidence._slice_code()
              └── evidence._match_strength()
        └── detect.detect_obfuscation()
              └── kgrams.build_fingerprints()  (×4: raw + norm × 2 subs)
              └── scores.jaccard()
              └── _count_loop_types()
              └── _loops_swapped()
              └── _count_enhanced_for()
        └── line_matcher.calculate_line_similarity()
        └── line_matcher.build_line_mapping()
        └── line_matcher.get_full_source_with_mapping()
        └── _load_original_sources()
  └── format_output.format_report_as_json()
  └── database.get_db_connection()      (store results)
```

---

## PART 9 — NUMBERS AT A GLANCE

| Property | Value |
|----------|-------|
| Engine version | 3.1.0 |
| K-gram size (k) | 10 tokens |
| Winnowing window (W) | 5 |
| Guaranteed detection length | 14+ tokens (~4-5 lines) |
| Fingerprints kept | ~20% of all possible k-grams |
| Score weights | Jaccard 35% + Dice 25% + Containment 40% |
| Method boost threshold | method_sim > global + 0.15 |
| Evidence merge gap | 3 lines |
| Evidence minimum span | 3 lines |
| Risk thresholds | CRITICAL ≥85% · HIGH ≥65% · MEDIUM ≥40% · LOW <40% |
| Obfuscation checks | 9 |
| Supported languages | Java, C, C++, Python, JavaScript, TypeScript, C#, Go, Rust, Ruby |
| Max ZIP nesting depth | 3 |
| JWT expiry | 60 minutes |
| S3 presigned URL expiry | 1 hour |
| Total Python files | 27 (excluding tests and root Engine/ directory) |

---

*Pantheon Engine v3.1.0 — Technical Reference*
