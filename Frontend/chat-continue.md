This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

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

- `SubmissionRow` now receives `hasReports: boolean` and `isHighRisk: boolean` props:

```tsx
function SubmissionRow({
  submission, hasReports, isHighRisk, onDetail,
}: {
  submission: Submission;
  hasReports: boolean;
  isHighRisk: boolean;
  onDetail: () => void;
})
```

- Badge rendering inside `SubmissionRow`:

```tsx
{hasReports ? (
  <Badge variant="outline" className="border-blue-200 bg-blue-50 text-xs text-blue-700">Compared</Badge>
) : (
  <Badge variant="outline" className="border-slate-200 bg-slate-50 text-xs text-slate-400">Not compared</Badge>
)}
{isHighRisk && (
  <Badge variant="outline" className="border-red-200 bg-red-50 text-xs text-red-700">High Risk</Badge>
)}
```

- Derived sets in parent body:

```tsx
const emailById = new Map(submissions.map((s) => [s.submission_id, s.email]));
const submissionsWithReports = new Set(reports.flatMap((r) => [r.submissionA, r.submissionB]));
const submissionsHighRisk = new Set(
  reports.filter((r) => r.similarityScore >= 80).flatMap((r) => [r.submissionA, r.submissionB]),
);
```

- `uploadDialogType` state:

```tsx
const [uploadDialogType, setUploadDialogType] = useState<"boilerplate" | "repository" | null>(null);
```

- "Add Resources" dropdown button added after "Compare All":

```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="outline" className="gap-2">
      <Plus className="h-4 w-4" />
      Add Resources
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem onClick={() => setUploadDialogType("boilerplate")}>
      Add boilerplate code
    </DropdownMenuItem>
    <DropdownMenuItem onClick={() => setUploadDialogType("repository")}>
      Add repository
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

- Two `FileUploadDialog` instances at bottom of JSX, each with its own API fetch inside `onUpload`
- `ComparisonDialog` now accepts `emailById` and uses it for subtitle and panel labels
- `ReportListDialog` now accepts `emailById` and uses it for the "vs" line
- `fullCodeA`/`fullCodeB` now derived as plain strings; file names from `fileOffsetsA/B` keys
- `CompareAll` button has `disabled={submissions.length < 2}`
- `flaggedPairs` fully removed from `CompareAllSuccessDialog`, state, and call sites

---

### `Frontend/source_code/src/app/dashboard/assignments/[assignmentSlug]/page.tsx`

- `Submission` type: removed `status: string` field
- `SimilarityReport` type updated:

```ts
fullCodeA: string;         // was Record<string, string>
fullCodeB: string;         // was Record<string, string>
fileOffsetsA: Record<string, number>;
fileOffsetsB: Record<string, number>;
identicalSubmissions: boolean;
```

---

### `Frontend/source_code/src/lib/report_types.ts`

- `ComparisonReport` type updated:

```ts
fullCodeA: string;
fullCodeB: string;
fileOffsetsA: Record<string, number>;
fileOffsetsB: Record<string, number>;
identicalSubmissions: boolean;
```

- `mapReport` function updated:

```ts
fullCodeA: String(json.fullCodeA ?? ""),
fullCodeB: String(json.fullCodeB ?? ""),
fileOffsetsA: (json.fileOffsetsA as Record<string, number>) ?? {},
fileOffsetsB: (json.fileOffsetsB as Record<string, number>) ?? {},
identicalSubmissions: Boolean(json.identicalSubmissions ?? false),
```

---

### `Frontend/source_code/src/components/FileUploadDialog.tsx` (new file)

- Reusable file upload dialog with dropzone, zod validation, inline errors, inline success state
- Props: `open`, `onClose`, `title`, `description`, `onUpload: (file: File) => Promise<void>`
- Validates zip contains `.java`, `.cpp`, or `.c` files using JSZip
- Uses `form.setError("root", ...)` for API errors thrown by `onUpload`
- Success state: replaces form with CheckCircle2 icon and "Done" button
- Schema mirrors student `FileUpload.tsx` pattern: `files: z.array(z.instanceof(File)).min(1, ...)`
- Drop replaces (not appends) the previous file: `form.setValue("files", [file], ...)`

---

## 4. Errors and Fixes

- **Edit tool "String to replace not found"**: When trying to edit the badge section in `SubmissionRow`, the `old_string` didn't match exactly (whitespace difference from Prettier formatting). Fixed by reading the exact lines first then using the correct content.
- **Missing `isHighRisk` prop at call site**: After adding `isHighRisk` to `SubmissionRow`'s type, the call site needed updating. Fixed by editing the `SubmissionRow` usage in the map to pass `isHighRisk={submissionsHighRisk.has(submission.submission_id)}`.

---

## 5. Problem Solving

- **Reactive badges**: Rather than relying on the static `has_comparison` field from server-fetched submission data, badges are derived from the live `reports` state so they update after Compare All without a page reload.
- **Email lookup**: Instead of extra API calls, a `Map<id, email>` is built from the already-available `submissions` array and passed as a prop — no data fetching required.
- **FileUpload reusability**: The student's `FileUpload.tsx` is tightly coupled (hardcoded endpoint, session storage key, specific title). Rather than refactoring it and risking regression, a new `FileUploadDialog.tsx` was created that is generic via the `onUpload` callback pattern.

---

## 6. Pending Tasks

- The API endpoints `/api/assignments/{assignment_id}/boilerplate` and `/api/assignments/{assignment_id}/repository` in `AssignmentView.tsx` are placeholders — they need to be updated to the actual backend endpoints once confirmed.
