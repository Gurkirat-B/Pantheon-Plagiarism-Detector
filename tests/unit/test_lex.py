"""
Tests for tokenization (engine/tokenize/lex.py).
"""

import sys
import pytest
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.tokenize.lex import Token, tokenize


class TestTokenization:
    """Basic tokenization tests."""

    def test_tokenize_java_simple(self):
        """Tokenize simple Java code."""
        code = "int x = 42;"
        tokens = tokenize(code, lang="java")
        assert len(tokens) > 0
        # Should have: int, ID (x), =, NUM (42), ;
        token_texts = [t.text for t in tokens]
        assert "int" in token_texts
        assert "=" in token_texts
        assert ";" in token_texts

    def test_tokenize_empty_string(self):
        """Tokenize empty string should return empty list."""
        tokens = tokenize("", lang="java")
        assert tokens == []

    def test_tokenize_single_number(self):
        """Tokenize single number."""
        tokens = tokenize("42", lang="java")
        assert len(tokens) == 1

    def test_tokenize_preserves_keywords(self):
        """Tokenize should recognize and preserve keywords."""
        code = "public class Foo { }"
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_access=False)
        token_texts = [t.text for t in tokens]
        assert "public" in token_texts
        assert "class" in token_texts

    def test_normalize_identifiers(self):
        """Test identifier normalization (normalize_ids=True)."""
        code = "int myVariable = 42;"
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_literals=True)
        token_texts = [t.text for t in tokens]
        # myVariable should be normalized to "ID"
        assert "ID" in token_texts
        assert "myVariable" not in token_texts

    def test_preserve_identifiers(self):
        """Test identifier preservation (normalize_ids=False)."""
        code = "int myVariable = 42;"
        tokens = tokenize(code, lang="java", normalize_ids=False, normalize_literals=True)
        token_texts = [t.text for t in tokens]
        # myVariable should be preserved
        assert "myVariable" in token_texts
        assert "ID" not in token_texts

    def test_normalize_literals_strings(self):
        """Test string literal normalization."""
        code = 'String s = "hello";'
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_literals=True)
        token_texts = [t.text for t in tokens]
        # "hello" should be normalized to "STR"
        assert "STR" in token_texts
        assert "hello" not in token_texts

    def test_normalize_literals_numbers(self):
        """Test number literal normalization."""
        code = "int x = 123; int y = 456;"
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_literals=True)
        token_texts = [t.text for t in tokens]
        # 123 and 456 should be normalized to "NUM"
        assert token_texts.count("NUM") >= 2
        assert "123" not in token_texts
        assert "456" not in token_texts

    def test_preserve_literals(self):
        """Test literal preservation (normalize_literals=False)."""
        code = "int x = 42;"
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_literals=False)
        token_texts = [t.text for t in tokens]
        # 42 should be preserved
        assert "42" in token_texts

    def test_hex_numbers(self):
        """Test hex number recognition."""
        code = "int color = 0x1A2F;"
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_literals=True)
        token_texts = [t.text for t in tokens]
        # 0x1A2F should be recognized as a number
        assert "NUM" in token_texts
        assert "0x1A2F" not in token_texts

    def test_float_numbers(self):
        """Test float number recognition."""
        code = "float pi = 3.14159;"
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_literals=True)
        token_texts = [t.text for t in tokens]
        # 3.14159 should be recognized as a number
        assert "NUM" in token_texts

    def test_scientific_notation(self):
        """Test scientific notation recognition."""
        code = "double x = 1.5e-3;"
        tokens = tokenize(code, lang="java", normalize_ids=True, normalize_literals=True)
        token_texts = [t.text for t in tokens]
        # 1.5e-3 should be recognized as a number
        assert "NUM" in token_texts

    def test_operators(self):
        """Test operator recognition."""
        code = "a == b && c != d || e <= f"
        tokens = tokenize(code, lang="java")
        token_texts = [t.text for t in tokens]
        assert "==" in token_texts
        assert "&&" in token_texts
        assert "!=" in token_texts
        assert "||" in token_texts
        assert "<=" in token_texts

    def test_line_tracking(self):
        """Test that line numbers are tracked in tokens."""
        code = "int x = 42;\nint y = 99;"
        tokens = tokenize(code, lang="java")
        # At least some tokens should have line 1, others line 2
        lines = {t.line for t in tokens}
        assert 1 in lines
        assert 2 in lines

    def test_cpp_keywords(self):
        """Test C++ specific keywords."""
        code = "std::vector<int> v;"
        tokens = tokenize(code, lang="cpp")
        token_texts = [t.text for t in tokens]
        # Should recognize std as identifier or keyword
        assert len(tokens) > 0

    def test_python_keywords(self):
        """Test Python specific keywords."""
        code = "def foo(x):\n    return x"
        tokens = tokenize(code, lang="python")
        token_texts = [t.text for t in tokens]
        assert "def" in token_texts
        assert "return" in token_texts

    def test_access_modifiers_stripped(self):
        """Test access modifier stripping (normalize_access=True)."""
        code = "public static int foo() { }"
        tokens = tokenize(code, lang="java", normalize_access=True)
        token_texts = [t.text for t in tokens]
        # public and static should be stripped
        assert "public" not in token_texts
        assert "static" not in token_texts

    def test_access_modifiers_preserved(self):
        """Test access modifier preservation (normalize_access=False)."""
        code = "public static int foo() { }"
        tokens = tokenize(code, lang="java", normalize_access=False)
        token_texts = [t.text for t in tokens]
        # public and static should be preserved
        assert "public" in token_texts
        assert "static" in token_texts

    def test_braces_and_parens(self):
        """Test brace and parenthesis tokenization."""
        code = "{([])} ()"
        tokens = tokenize(code, lang="java")
        token_texts = [t.text for t in tokens]
        assert "{" in token_texts
        assert "}" in token_texts
        assert "(" in token_texts
        assert ")" in token_texts
        assert "[" in token_texts
        assert "]" in token_texts

    def test_comments_stripped_before_tokenization(self):
        """Comments should be stripped before tokenization."""
        code = "int x = 42; // This is a comment"
        tokens = tokenize(code, lang="java")
        token_texts = [t.text for t in tokens]
        # Comment should not appear in tokens
        assert "//" not in token_texts
        assert "This" not in token_texts
        assert "comment" not in token_texts

    def test_multiline_code(self):
        """Test tokenization of multiline code."""
        code = """
        public class Test {
            public void method() {
                int x = 42;
            }
        }
        """
        tokens = tokenize(code, lang="java")
        assert len(tokens) > 10

    def test_mixed_language_fallback(self):
        """Test 'mixed' language mode."""
        code = "int x = 42; # Python comment"
        tokens = tokenize(code, lang="mixed")
        # Should still tokenize without error
        assert len(tokens) > 0

    def test_token_is_hashable(self):
        """Test that tokens can be used in sets/dicts."""
        token = Token("int", 1)
        token_set = {token}
        assert token in token_set

    def test_java_code_realistic(self, java_simple):
        """Test real Java code snippet."""
        tokens = tokenize(java_simple, lang="java", normalize_access=False)
        assert len(tokens) > 5
        token_texts = [t.text for t in tokens]
        assert "public" in token_texts
        assert "class" in token_texts

    def test_cpp_code_realistic(self, cpp_simple):
        """Test real C++ code snippet."""
        tokens = tokenize(cpp_simple, lang="cpp")
        assert len(tokens) > 5

    def test_python_code_realistic(self, python_simple):
        """Test real Python code snippet."""
        tokens = tokenize(python_simple, lang="python")
        assert len(tokens) > 3
        token_texts = [t.text for t in tokens]
        assert "def" in token_texts


class TestTokenEdgeCases:
    """Edge case tests for tokenization."""

    @pytest.mark.edge
    def test_very_long_identifier(self):
        """Test very long identifier name."""
        code = "int " + "x" * 1000 + " = 42;"
        tokens = tokenize(code, lang="java", normalize_ids=True)
        assert len(tokens) > 0
        # Normalized to ID
        assert "ID" in [t.text for t in tokens]

    @pytest.mark.edge
    def test_unicode_identifier(self):
        """Test Unicode characters in identifiers."""
        code = "int café = 42;"
        tokens = tokenize(code, lang="java")
        # Should not crash
        assert len(tokens) > 0

    @pytest.mark.edge
    def test_string_with_escaped_quotes(self):
        """Test strings with escaped quotes."""
        code = r'String s = "He said \"hello\"";'
        tokens = tokenize(code, lang="java", normalize_literals=True)
        # Should recognize as string literal
        assert "STR" in [t.text for t in tokens]

    @pytest.mark.edge
    def test_unclosed_string(self):
        """Test handling of unclosed string literal."""
        code = 'String s = "unclosed'
        # Should not crash, might truncate or skip
        tokens = tokenize(code, lang="java")
        assert isinstance(tokens, list)

    @pytest.mark.edge
    def test_very_long_line(self):
        """Test very long line (> 10,000 chars)."""
        code = "int x = " + "1 + " * 5000 + "2;"
        tokens = tokenize(code, lang="java")
        # Should not crash or truncate
        assert len(tokens) > 100
