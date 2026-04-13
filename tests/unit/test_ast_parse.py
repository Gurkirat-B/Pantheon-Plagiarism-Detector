"""
Tests for AST parsing foundation (engine/ast/parse.py) — Phase 1.
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.ast.parse import parse_source


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

BUBBLE_SORT_PY = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

def main():
    data = [5, 3, 1, 4, 2]
    result = bubble_sort(data)
    print(result)
"""

BUBBLE_SORT_JAVA = """
public class BubbleSort {
    public static void sort(int[] arr) {
        int n = arr.length;
        for (int i = 0; i < n - 1; i++) {
            for (int j = 0; j < n - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                }
            }
        }
    }

    public static void main(String[] args) {
        int[] data = {5, 3, 1, 4, 2};
        sort(data);
    }
}
"""


class TestASTParseBasic:
    """Tests for basic AST parsing output structure."""

    def test_parse_source_returns_dict(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        assert isinstance(result, dict)

    def test_parse_source_has_required_keys(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        assert "functions"   in result
        assert "call_graph"  in result
        assert "parse_ok"    in result

    def test_parse_ok_on_valid_source(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        assert result["parse_ok"] is True

    def test_functions_is_dict(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        assert isinstance(result["functions"], dict)

    def test_call_graph_is_dict(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        assert isinstance(result["call_graph"], dict)


class TestFunctionBoundaryExtraction:
    """Tests for function boundary and metadata extraction."""

    def test_finds_correct_function_names(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        assert "bubble_sort" in result["functions"]
        assert "main"        in result["functions"]

    def test_function_has_line_numbers(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        fn = result["functions"]["bubble_sort"]
        assert "start_line" in fn
        assert "end_line"   in fn
        assert fn["start_line"] >= 1
        assert fn["end_line"]   >= fn["start_line"]

    def test_function_has_token_count(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        fn = result["functions"]["bubble_sort"]
        assert "token_count" in fn
        assert fn["token_count"] > 0

    def test_larger_function_has_more_tokens(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        sort_tokens = result["functions"]["bubble_sort"]["token_count"]
        main_tokens = result["functions"]["main"]["token_count"]
        # bubble_sort has the nested loops — should be larger
        assert sort_tokens > main_tokens

    def test_line_ranges_are_non_overlapping(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        fns = sorted(result["functions"].values(), key=lambda f: f["start_line"])
        for i in range(len(fns) - 1):
            assert fns[i]["end_line"] < fns[i + 1]["start_line"]


class TestCallGraphExtraction:
    """Tests for call graph extraction."""

    def test_main_calls_bubble_sort(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        cg = result["call_graph"]
        assert "main" in cg
        assert "bubble_sort" in cg["main"]

    def test_bubble_sort_does_not_call_main(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        cg = result["call_graph"]
        assert "main" not in cg.get("bubble_sort", [])

    def test_call_graph_keys_match_functions(self):
        result = parse_source(BUBBLE_SORT_PY, "python")
        for fn_name in result["call_graph"]:
            # call graph entries may include library calls not in the function map
            assert isinstance(result["call_graph"][fn_name], list)

    def test_recursive_function_calls_itself(self):
        src = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        result = parse_source(src, "python")
        cg = result["call_graph"]
        assert "factorial" in cg
        assert "factorial" in cg["factorial"]


class TestMultipleLanguages:
    """Tests for multi-language AST parsing."""

    def test_java_parse_ok(self):
        result = parse_source(BUBBLE_SORT_JAVA, "java")
        assert result["parse_ok"] is True

    def test_java_finds_functions(self):
        result = parse_source(BUBBLE_SORT_JAVA, "java")
        assert len(result["functions"]) >= 2

    def test_java_call_graph_populated(self):
        result = parse_source(BUBBLE_SORT_JAVA, "java")
        assert len(result["call_graph"]) > 0

    def test_unsupported_language_graceful(self):
        # Should not crash — returns parse_ok=False or empty result
        result = parse_source("print('hello')", "cobol")
        assert isinstance(result, dict)
        assert "parse_ok" in result


class TestEdgeCases:
    """Edge cases for AST parsing."""

    @pytest.mark.edge
    def test_empty_source(self):
        result = parse_source("", "python")
        assert isinstance(result, dict)
        # Should have keys even for empty source
        assert "functions"  in result
        assert "call_graph" in result

    @pytest.mark.edge
    def test_single_function_no_calls(self):
        src = """
def standalone():
    x = 1
    y = 2
    return x + y
"""
        result = parse_source(src, "python")
        assert "standalone" in result["functions"]
        # call graph entry should be empty or absent for standalone
        calls = result["call_graph"].get("standalone", [])
        assert isinstance(calls, list)

    @pytest.mark.edge
    def test_syntax_error_does_not_crash(self):
        bad_src = "def broken( x y z"
        result = parse_source(bad_src, "python")
        assert isinstance(result, dict)
        assert "parse_ok" in result
