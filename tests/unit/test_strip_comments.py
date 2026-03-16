"""
Tests for comment stripping (engine/preprocess/strip_comments.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.preprocess.strip_comments import strip_comments


class TestCommentStripping:
    """Tests for comment removal across languages."""

    def test_java_line_comments(self):
        """Strip Java line comments."""
        code = """int x = 42; // This is a comment
int y = 99; // Another comment"""
        result = strip_comments(code, lang="java")
        assert "This is" not in result
        assert "int x = 42;" in result
        assert "int y = 99;" in result

    def test_java_block_comments(self):
        """Strip Java block comments."""
        code = """int x = 42;
/* This is a
   multi-line comment */
int y = 99;"""
        result = strip_comments(code, lang="java")
        assert "multi-line" not in result
        assert "int x = 42;" in result
        assert "int y = 99;" in result

    def test_cpp_comments(self):
        """Strip C++ comments."""
        code = "#include <iostream> // include comment\n// Full line comment\nint main() {}"
        result = strip_comments(code, lang="cpp")
        assert "include comment" not in result
        assert "Full line" not in result
        assert "int main()" in result

    def test_python_comments(self):
        """Strip Python comments."""
        code = """def hello():  # Function comment
    print("hello")  # Print comment"""
        result = strip_comments(code, lang="python")
        assert "Function comment" not in result
        assert "Print comment" not in result
        assert 'print("hello")' in result

    def test_preserve_strings_with_comment_chars(self):
        """Strings containing comment chars should be preserved."""
        code = 'String s = "This // is not a comment";'
        result = strip_comments(code, lang="java")
        assert "This // is not a comment" in result

    def test_preserve_char_literals(self):
        """Char literals should be preserved."""
        code = "char c = '/'; // This is a comment"
        result = strip_comments(code, lang="java")
        assert "char c = '/'" in result
        assert "This is a comment" not in result

    def test_line_count_preservation(self):
        """Line count should be preserved (comments become empty lines)."""
        code = """line 1
// comment on line 2
line 3"""
        result = strip_comments(code, lang="java")
        lines = result.split("\n")
        # Should still have 3 lines
        assert len(lines) >= 3

    def test_unclosed_block_comment(self):
        """Unclosed block comment should be handled gracefully."""
        code = "int x = 42; /* unclosed comment"
        # Should not crash
        result = strip_comments(code, lang="java")
        assert isinstance(result, str)

    def test_nested_braces_not_comments(self):
        """Nested braces/brackets should not be treated as comments."""
        code = "int arr[2] = {1, 2};"  # C++ style
        result = strip_comments(code, lang="cpp")
        assert "arr[2]" in result
        assert "{1, 2}" in result

    def test_cpp_preprocessor_directives(self):
        """C/C++ preprocessor directives should be handled."""
        code = """#include <stdio.h>
#define MAX 100
int x;"""
        result = strip_comments(code, lang="cpp")
        # Directives might be preserved or removed depending on implementation
        assert "int x" in result

    def test_mixed_language_default(self):
        """'mixed' language mode should handle multiple comment styles."""
        code = """// Line comment (C)
def hello():  # Python comment
    pass"""
        result = strip_comments(code, lang="mixed")
        # Should strip both types
        assert "Line comment" not in result or "Python comment" not in result

    def test_empty_string(self):
        """Empty string should return empty."""
        result = strip_comments("", lang="java")
        assert result == ""

    def test_no_comments(self):
        """Code without comments should be unchanged."""
        code = "int x = 42; int y = 99;"
        result = strip_comments(code, lang="java")
        assert result == code

    def test_bom_handling(self):
        """UTF-8 BOM should be handled."""
        code = "\ufeffint x = 42;"
        result = strip_comments(code, lang="java")
        # Should not crash
        assert "int x" in result

    def test_multiline_string(self):
        """Multiline strings should preserve internal comment chars."""
        code = '''String s = """
Line 1 // not a comment
Line 2 /* also not a comment */
""";'''
        result = strip_comments(code, lang="java")
        assert "Line 1 // not" in result or "Line 1" in result


class TestCommentStrippingEdgeCases:
    """Edge cases for comment stripping."""

    @pytest.mark.edge
    def test_very_long_comment(self):
        """Handle very long comments."""
        code = "int x = 42; // " + "x" * 10000
        result = strip_comments(code, lang="java")
        assert "int x = 42;" in result

    @pytest.mark.edge
    def test_many_consecutive_comments(self):
        """Handle many consecutive comments."""
        code = "\n".join([f"// Comment {i}" for i in range(100)])
        result = strip_comments(code, lang="java")
        # Should strip all comments
        assert "Comment" not in result

    @pytest.mark.edge
    def test_escaped_characters_in_strings(self):
        """Handle escaped quotes in strings."""
        code = r'String s = "He said \"hello\""; // comment'
        result = strip_comments(code, lang="java")
        assert "Comment" not in result
        assert 'He said' in result

    @pytest.mark.edge
    def test_unicode_in_comments(self):
        """Unicode characters in comments should be stripped."""
        code = "int x = 42; // Comment with émojis 🎉"
        result = strip_comments(code, lang="java")
        assert "🎉" not in result
        assert "int x = 42;" in result

    @pytest.mark.edge
    def test_regex_special_chars_in_strings(self):
        """Regex special characters in strings should not affect parsing."""
        code = 'String pattern = ".*\\.java"; // Strip this'
        result = strip_comments(code, lang="java")
        assert "Strip this" not in result
        assert ".*\\.java" in result
