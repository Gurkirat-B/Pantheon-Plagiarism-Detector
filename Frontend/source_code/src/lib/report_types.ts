// ─── Types ────────────────────────────────────────────────────────────────────

export type MatchSeverity = "HIGH" | "MEDIUM" | "LOW";

export type CodeMatch = {
  index: number;
  severity: MatchSeverity;
  fileA: string;
  linesA: string;
  fileB: string;
  linesB: string;
  codeA: string;
  codeB: string;
};

export type ComparisonReport = {
  submissionA: string;
  submissionB: string;
  language: string;
  similarityScore: number;
  plagiarismLevel: string;  // "HIGH", "MEDIUM", "LOW", "CRITICAL"
  techniques: string[];
  totalBlocks: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  matches: CodeMatch[];
  fullCodeA: Record<string, string>; // { "filename.java": "full code..." }
  fullCodeB: Record<string, string>;
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
    matches: Array.isArray(json.matches)
      ? (json.matches as CodeMatch[])
      : [],
    fullCodeA: (json.fullCodeA as Record<string, string>) ?? {},
    fullCodeB: (json.fullCodeB as Record<string, string>) ?? {},
  };
}

// ─── Line highlight helper ────────────────────────────────────────────────────

export type HighlightRange = {
  start: number;
  end: number;
  severity: MatchSeverity;
};

// Parse "4 - 29" → { start: 4, end: 29 }
function parseLineRange(linesStr: string): { start: number; end: number } | null {
  const match = linesStr.match(/(\d+)\s*-\s*(\d+)/);
  if (!match) return null;
  return { start: parseInt(match[1]), end: parseInt(match[2]) };
}

// Build a map of line number → highlight severity for a given file in fullCode
// side: "A" or "B"
export function buildHighlightMap(
  matches: CodeMatch[],
  fileName: string,
  side: "A" | "B"
): Map<number, MatchSeverity> {
  const map = new Map<number, MatchSeverity>();

  for (const match of matches) {
    const file = side === "A" ? match.fileA : match.fileB;
    const lines = side === "A" ? match.linesA : match.linesB;

    if (file !== fileName) continue;

    const range = parseLineRange(lines);
    if (!range) continue;

    for (let i = range.start; i <= range.end; i++) {
      // Higher severity wins if line is in multiple matches
      const existing = map.get(i);
      if (!existing || severityRank(match.severity) > severityRank(existing)) {
        map.set(i, match.severity);
      }
    }
  }

  return map;
}

function severityRank(s: MatchSeverity): number {
  switch (s) {
    case "HIGH": return 3;
    case "MEDIUM": return 2;
    case "LOW": return 1;
  }
}