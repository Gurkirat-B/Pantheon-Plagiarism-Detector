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

export function mapReport(json: Record<string, unknown>): ComparisonReport {
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
    matches: Array.isArray(json.matches) ? (json.matches as CodeMatch[]) : [],
    fullCodeA: String(json.fullCodeA ?? ""),
    fullCodeB: String(json.fullCodeB ?? ""),
    fileOffsetsA: (json.fileOffsetsA as Record<string, number>) ?? {},
    fileOffsetsB: (json.fileOffsetsB as Record<string, number>) ?? {},
    identicalSubmissions: Boolean(json.identicalSubmissions ?? false),
  };
}

// ─── Line highlight helper ────────────────────────────────────────────────────

export type HighlightRange = {
  start: number;
  end: number;
  severity: MatchSeverity;
};

// Build a map of line number → highlight severity for a given file in fullCode
// side: "A" or "B"
export function buildHighlightMap(
  matches: CodeMatch[],
  fileName: string,
  side: "A" | "B",
): Map<number, MatchSeverity> {
  const map = new Map<number, MatchSeverity>();

  for (const match of matches) {
    const file = side === "A" ? match.fileA : match.fileB;
    const highlights =
      side === "A" ? match.lineHighlightsA : match.lineHighlightsB;

    if (file !== fileName) continue;

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
