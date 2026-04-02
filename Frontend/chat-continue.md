# Chat Session Summary

## 1. Primary Request and Intent

The conversation covers a series of incremental UI improvements to the `AssignmentView.tsx` component of a plagiarism detection dashboard. Requests in order:

- Add "Compared/Not compared" badges to submission cards, reactive to live reports state
- Add a "High Risk" badge (similarityScore ≥ 80%) to submission cards
- Remove the "Accepted" status badge and all related code
- Disable the "Compare All" button when there are fewer than 2 submissions
- Remove all `flaggedPairs` code since the Compare All API no longer returns `flagged_pairs`
- Update type definitions and parser (`mapReport`) for a new similarity report API response shape where `fullCodeA`/`fullCodeB` are now flat strings and new fields `fileOffsetsA`, `fileOffsetsB`, `identicalSubmissions` were added
- Replace submission UUIDs with submitter emails in report list dialog, comparison dialog header, and full-code panel labels
- Add an "Add Resources" button next to "Compare All" that shows a dropdown with "Add boilerplate code" and "Add repository" options, each opening a file upload dialog with inline error handling and inline success state
- Rework full-code highlight logic: stop using `lineHighlightsA/B` (now always `[]` from API) and instead expand `linesA`/`linesB` (`[start, end]` tuples) into full line ranges
- Fix report list dialog color/label scheme to match side-by-side view (use backend's `similarityLevel` field instead of score-derived thresholds)
- Skip highlighting blank lines in the full code view

---

## 2. Key Technical Concepts

- React state-derived sets for reactive badge computation (`submissionsWithReports`, `submissionsHighRisk`)
- shadcn/ui components: `Badge`, `Dialog`, `DropdownMenu`, `Button`, `Form`, `LoadingButton`
- Zod form validation with `react-hook-form` and `zodResolver`
- react-dropzone for file drag-and-drop
- JSZip for client-side zip file content validation
- TypeScript discriminated union state (`"boilerplate" | "repository" | null`)
- `Map<string, string>` for O(1) submission ID → email lookup passed as prop
- Separation of concerns: `onUpload(file)` callback pattern keeps API logic in the caller
- Next.js App Router, client components (`"use client"`)

---

## 3. Files and Code Sections

### `Frontend/source_code/src/app/dashboard/assignments/[assignmentSlug]/AssignmentView.tsx`

Main file modified across all tasks. Key cumulative changes:

- `SubmissionRow` receives `hasReports: boolean` and `isHighRisk: boolean` props
- Derived sets in parent body:

```tsx
const emailById = new Map(submissions.map((s) => [s.submission_id, s.email]));
const submissionsWithReports = new Set(reports.flatMap((r) => [r.submissionA, r.submissionB]));
const submissionsHighRisk = new Set(
  reports.filter((r) => r.similarityScore >= 80).flatMap((r) => [r.submissionA, r.submissionB]),
);
```

- `uploadDialogType` state: `"boilerplate" | "repository" | null`
- "Add Resources" dropdown + "Compare All" button (disabled when `submissions.length < 2`)
- Two `FileUploadDialog` instances at bottom of JSX for boilerplate and repository uploads
- `ComparisonDialog` and `ReportListDialog` both receive `emailById` prop

**ComparisonDialog — full code highlight logic (current):**

```tsx
const filesA = Object.keys(report.fileOffsetsA);
const filesB = Object.keys(report.fileOffsetsB);
const fileNameA = filesA.length === 1 ? filesA[0] : `${filesA.length} files`;
const fileNameB = filesB.length === 1 ? filesB[0] : `${filesB.length} files`;

const highlightMapA = buildHighlightMap(report.matches, "A");
const highlightMapB = buildHighlightMap(report.matches, "B");
```

**FullCodePanel — blank line skip:**

```tsx
const severity =
  line.trim() === "" ? undefined : highlightMap.get(lineNum);
```

**Report list dialog — color classification:**

```tsx
const sev = getLevelCardClass(sr.similarityLevel);
```

`getLevelCardClass` maps CRITICAL → red, HIGH → orange, MEDIUM → yellow, LOW/default → emerald — matching the side-by-side view's `getLevelBg`/`getLevelColor` scheme. Replaces the old `getScoreSeverity(score)` which used hardcoded score thresholds (≥80 HIGH, ≥50 MEDIUM) that diverged from the backend's classification.

---

### `Frontend/source_code/src/app/dashboard/assignments/[assignmentSlug]/page.tsx`

- `Submission` type: no `status: string` field
- `SimilarityReport` type:

```ts
fullCodeA: string;
fullCodeB: string;
fileOffsetsA: Record<string, number>;
fileOffsetsB: Record<string, number>;
identicalSubmissions: boolean;
```

- `RawMatch` type — `linesA` and `linesB` are `number[]` (a `[start, end]` tuple), not `string`:

```ts
linesA: number[];
linesB: number[];
```

---

### `Frontend/source_code/src/lib/report_types.ts`

**`ComparisonReport` type:**

```ts
fullCodeA: string;
fullCodeB: string;
fileOffsetsA: Record<string, number>;
fileOffsetsB: Record<string, number>;
identicalSubmissions: boolean;
```

**`mapReport` — transforms raw matches into `CodeMatch`:**

```ts
function expandLineRange(range: number[]): number[] {
  // [1, 10] → [1, 2, 3, ..., 10]
}

function formatLineRange(range: number[]): string {
  // [1, 10] → "1–10"
}

function mapMatch(raw, idx): CodeMatch {
  const linesA = Array.isArray(raw.linesA) ? raw.linesA : [];
  const linesB = Array.isArray(raw.linesB) ? raw.linesB : [];
  return {
    linesA: formatLineRange(linesA),       // display string
    lineHighlightsA: expandLineRange(linesA), // absolute line numbers in fullCodeA
    linesB: formatLineRange(linesB),
    lineHighlightsB: expandLineRange(linesB),
    ...
  };
}
```

**`buildHighlightMap` — no filename filtering:**

```ts
// Line numbers in lineHighlightsA/B are absolute positions in the concatenated
// fullCodeA/B string, so all matches are applied regardless of filename.
export function buildHighlightMap(
  matches: CodeMatch[],
  side: "A" | "B",
): Map<number, MatchSeverity>
```

The filename parameter was removed. Previously it filtered `match.fileA !== fileName`, which silently dropped all matches when a submission had multiple files (e.g., `fileOffsetsA` with 6 entries) since only the first key was used and the other files' matches were skipped.

---

### `Frontend/source_code/src/components/FileUploadDialog.tsx` (new file)

- Reusable file upload dialog with dropzone, zod validation, inline errors, inline success state
- Props: `open`, `onClose`, `title`, `description`, `onUpload: (file: File) => Promise<void>`
- Validates zip contains `.java`, `.cpp`, or `.c` files using JSZip
- Uses `form.setError("root", ...)` for API errors thrown by `onUpload`
- Success state: replaces form with CheckCircle2 icon and "Done" button

---

## 4. Key Bug Fixes

- **Full code highlight wrong for multi-file submissions**: `buildHighlightMap` filtered by `fileNameA = Object.keys(fileOffsetsA)[0]`, so only matches whose `fileA` equaled the first filename were highlighted. Removed filename filter — line numbers are absolute positions in the concatenated `fullCodeA/B`.
- **`"full submission"` filename**: When the API returns `fileA: "full submission"` (single-file submissions), the old filter would also skip it unless the filename matched. Now irrelevant since filter is removed.
- **Report list color mismatch**: `getScoreSeverity(score)` used frontend thresholds (≥50 = MEDIUM) that didn't match the backend's `similarityLevel`. A 41.5% score showed as LOW/green in the list but MEDIUM/yellow in the side-by-side. Fixed by using `getLevelCardClass(sr.similarityLevel)`.
- **Blank lines highlighted**: Lines where `line.trim() === ""` were included in the expanded range and got highlighted. Fixed by skipping highlight lookup for blank lines in `FullCodePanel`.

---

## 5. Pending Tasks

- The API endpoints `/api/assignments/{assignment_id}/boilerplate` and `/api/assignments/{assignment_id}/repository` in `AssignmentView.tsx` are placeholders — need to be updated to actual backend endpoints once confirmed.
