def _idx_to_line(tokens, idx: int) -> int:
    if not tokens:
        return 1
    idx = max(0, min(idx, len(tokens) - 1))
    return tokens[idx].line

def _merge(ranges, gap=2):
    if not ranges:
        return []
    ranges.sort()
    merged = [ranges[0]]
    for s,e in ranges[1:]:
        ps,pe = merged[-1]
        if s <= pe + gap:
            merged[-1] = (ps, max(pe,e))
        else:
            merged.append((s,e))
    return merged

def evidence_from_shared(fpA, fpB, tokA, tokB, k: int = 7):
    shared = set(fpA.keys()) & set(fpB.keys())
    a_ranges, b_ranges = [], []

    for h in shared:
        ia = fpA[h][0]
        ib = fpB[h][0]
        a_ranges.append((_idx_to_line(tokA, ia), _idx_to_line(tokA, ia + k - 1)))
        b_ranges.append((_idx_to_line(tokB, ib), _idx_to_line(tokB, ib + k - 1)))

    a_ranges = _merge(a_ranges)
    b_ranges = _merge(b_ranges)

    evidence = []
    for i in range(min(len(a_ranges), len(b_ranges))):
        evidence.append({
            "a": {"start_line": a_ranges[i][0], "end_line": a_ranges[i][1]},
            "b": {"start_line": b_ranges[i][0], "end_line": b_ranges[i][1]},
        })
    return evidence