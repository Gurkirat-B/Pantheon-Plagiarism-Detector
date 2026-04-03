# Chat Session Summary

## 1. Primary Request and Intent

Incremental UI improvements to the plagiarism detection dashboard (`AssignmentView.tsx`) and related components. Session covered:

- Add "Compare" dropdown replacing the "Compare All" button — two options: "Current submissions" (calls `/compare-all`) and "With repository" (calls `/compare-repo`)
- `ReportListDialog` upgraded: tab toggle (Current Submissions / With Repository), smart default tab (auto-selects whichever tab has results), repo report cards show filename instead of unknown ID
- Overflow fix: report list in dialog now has `max-h-[60vh] overflow-y-auto`
- `ViewResourcesDialog` connected to boilerplate GET API — fetched server-side on page load, passed as `initialBoilerplateFilename`, updated in state after successful upload (no per-open fetches)
- Simplify pass: replaced `useEffect` tab default (caused flicker + duplicate array scans) with synchronous state-reset-on-prop-change pattern

---

## 2. Key Technical Concepts

- React: synchronous state reset during render (`if (currentId !== prevId) { setPrevId(currentId); setManualTab(null); }`) to avoid post-render flicker when props change — replaces `useEffect` + `setState` pattern
- `manualTab: "current" | "repo" | null` — null means "use computed default"; set explicitly by user click
- Derived tab default: compute `studentMatching`/`repoMatching` once via `.filter()`, derive default from lengths — eliminates duplicate `.some()` scans in removed `useEffect`
- `successDialogType: "current" | "repo" | null` — null/non-null doubles as open/closed signal; value drives title/description of reused `CompareAllSuccessDialog`
- Next.js App Router: server-side fetch in `page.tsx` `Promise.all`, result passed as prop to client component, state initialized from prop (one-time, intentionally decoupled after mount)

---

## 3. Files and Code Sections

### `src/app/dashboard/assignments/[assignmentSlug]/AssignmentView.tsx`

**New state in main component:**
```tsx
const [repoReports, setRepoReports] = useState<SimilarityReport[]>([]);
const [comparingRepo, setComparingRepo] = useState(false);
const [successDialogType, setSuccessDialogType] = useState<"current" | "repo" | null>(null);
const [compareResult, setCompareResult] = useState<{ totalPairs: number } | null>(null);
const [boilerplateFilename, setBoilerplateFilename] = useState<string | null>(initialBoilerplateFilename);
```

**`submissionsWithReports` now includes repo reports:**
```tsx
const submissionsWithReports = new Set([
  ...reports.flatMap((r) => [r.submissionA, r.submissionB]),
  ...repoReports.flatMap((r) => [r.submissionA, r.submissionB]),
]);
```

**Compare dropdown (replaces LoadingButton):**
```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button disabled={comparingAll || comparingRepo || submissions.length < 2} className="gap-2">
      {comparingAll || comparingRepo ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
      {comparingAll || comparingRepo ? "Analysing..." : "Compare"}
      <ChevronDown className="h-4 w-4" />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem disabled={comparingAll || comparingRepo} onClick={handleCompareAll}>
      Current submissions
    </DropdownMenuItem>
    <DropdownMenuItem disabled={comparingAll || comparingRepo} onClick={handleCompareRepo}>
      With repository
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

**`ReportListDialog` — smart tab, no flicker:**
```tsx
const [manualTab, setManualTab] = useState<"current" | "repo" | null>(null);
const [prevSubmissionId, setPrevSubmissionId] = useState<string | null>(null);

// Synchronously reset on submission change — no post-render flicker
const currentId = submission?.submission_id ?? null;
if (currentId !== prevSubmissionId) {
  setPrevSubmissionId(currentId);
  setManualTab(null);
}

if (!submission) return null;

// Single-pass filtering — no duplicate scans
const studentMatching = reports.filter(r => r.submissionA === submission.submission_id || r.submissionB === submission.submission_id);
const repoMatching = repoReports.filter(r => r.submissionA === submission.submission_id || r.submissionB === submission.submission_id);
const defaultTab: "current" | "repo" = studentMatching.length === 0 && repoMatching.length > 0 ? "repo" : "current";
const tab = manualTab ?? defaultTab;
const matching = tab === "current" ? studentMatching : repoMatching;
```

**Repo report label (filename fallback):**
```tsx
let otherLabel: string;
if (tab === "repo" && !emailById.has(otherId)) {
  // otherId is repo upload — show filename, not raw ID
  const repoFiles = otherId === sr.submissionB ? Object.keys(sr.fileOffsetsB) : Object.keys(sr.fileOffsetsA);
  otherLabel = repoFiles.length === 1 ? repoFiles[0] : `${repoFiles.length} files`;
} else {
  otherLabel = emailById.get(otherId) ?? otherId;
}
```

**`CompareAllSuccessDialog` — reused with optional props:**
```tsx
function CompareAllSuccessDialog({ open, onClose, totalPairs, title = "Analysis Complete", description = "All submission pairs have been compared." })
// Rendered:
<CompareAllSuccessDialog
  open={successDialogType !== null}
  onClose={() => setSuccessDialogType(null)}
  totalPairs={compareResult?.totalPairs ?? 0}
  title={successDialogType === "repo" ? "Repository Analysis Complete" : "Analysis Complete"}
  description={successDialogType === "repo" ? "All submission-repository pairs have been analysed." : "All submission pairs have been compared."}
/>
```

**`ViewResourcesDialog` — pure display, no fetching:**
```tsx
function ViewResourcesDialog({ open, onClose, boilerplateFilename: string | null })
// boilerplateFilename: show filename or "No file uploaded"
// Repository: still placeholder
```

---

### `src/app/dashboard/assignments/[assignmentSlug]/page.tsx`

**`getBoilerplate` fetcher (new):**
```ts
async function getBoilerplate(token, assignmentId): Promise<string | null>
// GET /submissions/boilerplate/{assignmentId}
// 404 → null (no boilerplate uploaded yet)
```

Called in `Promise.all` alongside `getCourse` and `getReports`. Result passed as `initialBoilerplateFilename` prop to `AssignmentView`.

---

### API Route Files

| Route file | Method | Backend endpoint |
|---|---|---|
| `api/submissions/[assignmentKey]/export/route.ts` | GET | `/submissions/{id}/export` |
| `api/submissions/boilerplate/[assignmentId]/route.ts` | GET | `/submissions/boilerplate/{id}` |
| `api/submissions/boilerplate/[assignmentId]/route.ts` | POST | `/submissions/boilerplate/{id}` |
| `api/submissions/repo/[assignmentId]/route.ts` | POST | `/submissions/repo/{id}` |
| `api/engine/assignments/[assignmentId]/compare-all/route.ts` | POST | `/engine/assignments/{id}/compare-all` |
| `api/engine/assignments/[assignmentId]/compare-repo/route.ts` | POST | `/engine/assignments/{id}/compare-repo` |
| `api/engine/similarity-report-student/route.ts` | GET | `/engine/similarity-report-student?submission_id=` (fan-out) |
| `api/engine/similarity-report-repo/route.ts` | GET | `/engine/similarity-report-repo?submission_id=` (fan-out) |

Compare-all/compare-repo response: `{ run_id, assignment_id, total_pairs, pairs[] }` — same shape, `SimilarityReport` type reused.
Similarity-report-student/repo response: same `SimilarityReport[]` shape — same type reused.
Boilerplate GET response: `{ filename: string }`

---

## 4. Key Decisions / Non-obvious Choices

- `manualTab = null` means "auto" — when user hasn't made an explicit choice, derive the tab from data. Explicit user click sets it to "current" or "repo". Resets to null on submission change (synchronous during render, no flicker).
- Synchronous render-time state reset (`if (id !== prevId) { setPrevId(id); resetState(); }`) is the React-recommended pattern for resetting state on prop change without an `useEffect` flicker.
- `successDialogType` null/non-null serves as the open/closed boolean — avoids a separate `successDialogOpen` boolean alongside the type.
- `boilerplateFilename` initialized from server-side prop, updated only after upload — intentionally decoupled from prop after mount (no re-fetch risk since the only mutation goes through the upload handler in the same component).
- Repo report cards use `fileOffsetsB` (or `fileOffsetsA`) key filenames to label the repo party — the repo upload ID is not in `emailById`, so falling back to raw ID would show a UUID.
- Route files for `compare-repo` and `similarity-report-repo` are structurally identical to their student counterparts — no abstraction added (Next.js route handlers are one-file-per-route idiom; 2 instances don't justify a factory).

---

## 5. Pending / Placeholder

- `ViewResourcesDialog` Repository slot still shows placeholder — no GET API available yet for repository info.
- `refreshReports` and `refreshRepoReports` are separate functions (symmetric pattern) — could be unified into a factory if a third report type is ever added.
