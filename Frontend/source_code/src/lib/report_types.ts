// ─── Types ────────────────────────────────────────────────────────────────────

export type MatchSeverity = "HIGH" | "MEDIUM" | "LOW";

export type CodeMatch = {
  index: number;
  severity: MatchSeverity;
  fileA: string;
  linesA: string;
  lineHighlightsA: number[];
  fileB: string;
  linesB: string;
  lineHighlightsB: number[];
  codeA: string;
  codeB: string;
};

export type ComparisonReport = {
  submissionA: string;
  submissionB: string;
  language: string;
  similarityScore: number;
  plagiarismLevel: string; // "HIGH", "MEDIUM", "LOW", "CRITICAL"
  techniques: string[];
  totalBlocks: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  matches: CodeMatch[];
  fullCodeA: string;
  fullCodeB: string;
  fileOffsetsA: Record<string, number>; // { "filename.java": startLine }
  fileOffsetsB: Record<string, number>;
  identicalSubmissions: boolean;
};

// ─── Map JSON response → ComparisonReport ────────────────────────────────────

function expandLineRange(range: number[]): number[] {
  if (!Array.isArray(range) || range.length < 2) return [];
  const [start, end] = range;
  const result: number[] = [];
  for (let i = start; i <= end; i++) result.push(i);
  return result;
}

function formatLineRange(range: number[]): string {
  if (!Array.isArray(range) || range.length === 0) return "";
  if (range.length === 1) return String(range[0]);
  return `${range[0]}–${range[range.length - 1]}`;
}

type RawMatchInput = {
  codeA?: unknown;
  codeB?: unknown;
  fileA?: unknown;
  fileB?: unknown;
  index?: unknown;
  linesA?: unknown;
  linesB?: unknown;
  severity?: unknown;
};

function mapMatch(raw: RawMatchInput, idx: number): CodeMatch {
  const linesA = Array.isArray(raw.linesA) ? (raw.linesA as number[]) : [];
  const linesB = Array.isArray(raw.linesB) ? (raw.linesB as number[]) : [];
  return {
    index: Number(raw.index ?? idx),
    severity: (raw.severity as MatchSeverity) ?? "LOW",
    fileA: String(raw.fileA ?? ""),
    linesA: formatLineRange(linesA),
    lineHighlightsA: expandLineRange(linesA),
    fileB: String(raw.fileB ?? ""),
    linesB: formatLineRange(linesB),
    lineHighlightsB: expandLineRange(linesB),
    codeA: String(raw.codeA ?? ""),
    codeB: String(raw.codeB ?? ""),
  };
}

export function mapReport(json: Record<string, unknown>): ComparisonReport {
  const rawMatches = Array.isArray(json.matches)
    ? (json.matches as RawMatchInput[])
    : [];
  return {
    submissionA: String(json.submissionA ?? ""),
    submissionB: String(json.submissionB ?? ""),
    language: String(json.language ?? ""),
    similarityScore: Number(json.similarityScore ?? 0),
    plagiarismLevel: String(json.similarityLevel ?? ""),
    techniques: Array.isArray(json.alterationTechniquesDetected)
      ? (json.alterationTechniquesDetected as string[])
      : [],
    totalBlocks: Number(json.sections ?? 0),
    highCount: Number(json.High ?? 0),
    mediumCount: Number(json.Medium ?? 0),
    lowCount: Number(json.Low ?? 0),
    matches: rawMatches.map((m, i) => mapMatch(m, i + 1)),
    fullCodeA: String(json.fullCodeA ?? ""),
    fullCodeB: String(json.fullCodeB ?? ""),
    fileOffsetsA: (json.fileOffsetsA as Record<string, number>) ?? {},
    fileOffsetsB: (json.fileOffsetsB as Record<string, number>) ?? {},
    identicalSubmissions: Boolean(json.identicalSubmissions ?? false),
  };
}

// ─── Line → block index map (for per-block coloring in full code view) ────────

export function buildLineToBlockMap(
  matches: CodeMatch[],
  side: "A" | "B",
): Map<number, number> {
  const map = new Map<number, number>();
  matches.forEach((match, blockIndex) => {
    const highlights =
      side === "A" ? match.lineHighlightsA : match.lineHighlightsB;
    for (const lineNum of highlights) {
      if (!map.has(lineNum)) {
        map.set(lineNum, blockIndex);
      }
    }
  });
  return map;
}

// ─── Line highlight helper ────────────────────────────────────────────────────

export type HighlightRange = {
  start: number;
  end: number;
  severity: MatchSeverity;
};

// Build a map of line number → highlight severity.
// Line numbers in lineHighlightsA/B are absolute positions in the concatenated
// fullCodeA/B string, so all matches are applied regardless of filename.
export function buildHighlightMap(
  matches: CodeMatch[],
  side: "A" | "B",
): Map<number, MatchSeverity> {
  const map = new Map<number, MatchSeverity>();

  for (const match of matches) {
    const highlights =
      side === "A" ? match.lineHighlightsA : match.lineHighlightsB;

    for (const lineNum of highlights) {
      const existing = map.get(lineNum);
      if (!existing || severityRank(match.severity) > severityRank(existing)) {
        map.set(lineNum, match.severity);
      }
    }
  }

  return map;
}

function severityRank(s: MatchSeverity): number {
  switch (s) {
    case "HIGH":
      return 3;
    case "MEDIUM":
      return 2;
    case "LOW":
      return 1;
  }
}
