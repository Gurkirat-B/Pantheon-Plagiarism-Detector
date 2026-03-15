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
  plagiarismLevel: string;
  levelThreshold: string;
  techniques: string[];
  totalBlocks: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  matches: CodeMatch[];
};

// ─── Parser ───────────────────────────────────────────────────────────────────

export function parseReport(raw: string): ComparisonReport {
  const lines = raw.split("\n");

  // ── Header metadata ─────────────────────────────────────────────────────────
  const submissionA = extractValue(lines, "Submission A");
  const submissionB = extractValue(lines, "Submission B");
  const language = extractValue(lines, "Language");

  // ── Summary ─────────────────────────────────────────────────────────────────
  const scoreLine = lines.find((l) => l.includes("SIMILARITY SCORE")) ?? "";
  const scoreMatch = scoreLine.match(/([\d.]+)%/);
  const similarityScore = scoreMatch ? parseFloat(scoreMatch[1]) : 0;

  const levelLine = lines.find((l) => l.includes("PLAGIARISM LEVEL")) ?? "";
  // e.g. "  PLAGIARISM LEVEL      CRITICAL  (>= 85%)"
  const levelMatch = levelLine.match(/PLAGIARISM LEVEL\s+(\w+)\s+\(([^)]+)\)/);
  const plagiarismLevel = levelMatch?.[1] ?? "UNKNOWN";
  const levelThreshold = levelMatch?.[2] ?? "";

  // ── Techniques ──────────────────────────────────────────────────────────────
  const techniques: string[] = [];
  let inTechniques = false;
  for (const line of lines) {
    if (line.includes("ALTERATION TECHNIQUES DETECTED")) {
      inTechniques = true;
      continue;
    }
    if (inTechniques) {
      if (line.includes("---") && line.includes("MATCHING")) break;
      const techMatch = line.match(/\[!\]\s+(.+)/);
      if (techMatch) techniques.push(techMatch[1].trim());
    }
  }

  // ── Block summary line ──────────────────────────────────────────────────────
  // e.g. "  Breakdown: 1 HIGH  /  1 MEDIUM  /  1 LOW"
  const breakdownLine = lines.find((l) => l.includes("Breakdown:")) ?? "";
  const highCount = parseInt(breakdownLine.match(/(\d+)\s+HIGH/)?.[1] ?? "0");
  const mediumCount = parseInt(breakdownLine.match(/(\d+)\s+MEDIUM/)?.[1] ?? "0");
  const lowCount = parseInt(breakdownLine.match(/(\d+)\s+LOW/)?.[1] ?? "0");

  const blocksLine = lines.find((l) => l.includes("MATCHING CODE SECTIONS")) ?? "";
  const totalBlocks = parseInt(blocksLine.match(/(\d+)\s+block/)?.[1] ?? "0");

  // ── Matching blocks ──────────────────────────────────────────────────────────
  const matches: CodeMatch[] = [];
  const blockSeparator = "----------------------------------------------------------------";

  // Split the full text into segments by separator
  const segments = raw.split(blockSeparator);

  for (const segment of segments) {
    // Each block starts with [N]  SEVERITY
    const headerMatch = segment.match(/\[(\d+)\]\s+(HIGH|MEDIUM|LOW)\s+MATCH/);
    if (!headerMatch) continue;

    const index = parseInt(headerMatch[1]);
    const severity = headerMatch[2] as MatchSeverity;

    // File + line info
    // e.g. "       A: matrix_copied.cpp  (lines 29 - 81)"
    const fileAMatch = segment.match(/A:\s+(.+?)\s+\(lines\s+([\d\s-]+)\)/);
    const fileBMatch = segment.match(/B:\s+(.+?)\s+\(lines\s+([\d\s-]+)\)/);

    const fileA = fileAMatch?.[1]?.trim() ?? "";
    const linesA = fileAMatch?.[2]?.trim() ?? "";
    const fileB = fileBMatch?.[1]?.trim() ?? "";
    const linesB = fileBMatch?.[2]?.trim() ?? "";

    // Code sections — between "--- Submission A ---" and "--- Submission B ---"
    // and between "--- Submission B ---" and end of segment
    const subAStart = segment.indexOf("--- Submission A ---");
    const subBStart = segment.indexOf("--- Submission B ---");

    let codeA = "";
    let codeB = "";

    if (subAStart !== -1 && subBStart !== -1) {
      codeA = segment
        .slice(subAStart + "--- Submission A ---".length, subBStart)
        .trim();
      codeB = segment
        .slice(subBStart + "--- Submission B ---".length)
        .trim();
    }

    matches.push({ index, severity, fileA, linesA, fileB, linesB, codeA, codeB });
  }

  return {
    submissionA,
    submissionB,
    language,
    similarityScore,
    plagiarismLevel,
    levelThreshold,
    techniques,
    totalBlocks,
    highCount,
    mediumCount,
    lowCount,
    matches,
  };
}

// ─── Util ─────────────────────────────────────────────────────────────────────

function extractValue(lines: string[], key: string): string {
  const line = lines.find((l) => l.includes(key)) ?? "";
  const parts = line.split(":");
  return parts[1]?.trim() ?? "";
}