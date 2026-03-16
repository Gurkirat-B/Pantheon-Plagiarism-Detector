"""
Pytest configuration and shared fixtures for Pantheon engine tests.
"""

import sys
import os
import tempfile
import shutil
import zipfile
from pathlib import Path
from io import BytesIO

# Add Backend to path so we can import the engine
# MUST be before pytest and any engine imports
backend_path = str(Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import pytest
from engine.tokenize.lex import Token


# ═══════════════════════════════════════════════════════════════════
# FIXTURES: Directories and cleanup
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_work_dir():
    """Create a temporary working directory for tests."""
    work_dir = tempfile.mkdtemp(prefix="pantheon_test_")
    yield work_dir
    # Cleanup
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)


@pytest.fixture
def fixtures_dir():
    """Return the path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


# ═══════════════════════════════════════════════════════════════════
# FIXTURES: Sample source code strings
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def java_simple():
    """Simple Java code snippet."""
    return """
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""


@pytest.fixture
def java_with_comments():
    """Java code with various comment types."""
    return """
// Line comment
public class Foo {
    /* Block comment */
    public void bar() {
        // Another line comment
        int x = 42;
    }
}
"""


@pytest.fixture
def java_stdlib():
    """Java code with only stdlib imports."""
    return """
import java.util.*;
import java.io.*;
import javax.swing.*;

public class StdlibOnly {
    public static void main(String[] args) {
        System.out.println("Done");
    }
}
"""


@pytest.fixture
def java_identical_rename():
    """Two Java snippets with identical logic but different variable names."""
    code_a = """
public int sum(int[] arr) {
    int total = 0;
    for (int num : arr) {
        total += num;
    }
    return total;
}
"""
    code_b = """
public int sum(int[] data) {
    int s = 0;
    for (int x : data) {
        s += x;
    }
    return s;
}
"""
    return code_a, code_b


@pytest.fixture
def cpp_simple():
    """Simple C++ code snippet."""
    return """
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
"""


@pytest.fixture
def python_simple():
    """Simple Python code snippet."""
    return """
def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
"""


@pytest.fixture
def empty_source():
    """Empty source code."""
    return ""


@pytest.fixture
def single_token_source():
    """Source with only one token."""
    return "42"


# ═══════════════════════════════════════════════════════════════════
# FIXTURES: Token lists
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def simple_tokens():
    """Simple token list for testing fingerprinting."""
    return [
        Token("int", 1),
        Token("sum", 1),
        Token("(", 1),
        Token("int", 1),
        Token("a", 1),
        Token(",", 1),
        Token("int", 1),
        Token("b", 1),
        Token(")", 1),
        Token("{", 2),
        Token("return", 2),
        Token("a", 2),
        Token("+", 2),
        Token("b", 2),
        Token(";", 2),
        Token("}", 3),
    ]


@pytest.fixture
def long_token_list():
    """Token list long enough to test winnowing (> 11 tokens)."""
    tokens = []
    for i in range(20):
        tokens.append(Token(f"token_{i}", i // 5 + 1))
    return tokens


@pytest.fixture
def empty_tokens():
    """Empty token list."""
    return []


# ═══════════════════════════════════════════════════════════════════
# FIXTURES: Fingerprint sets for similarity testing
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def identical_fingerprints():
    """Two identical fingerprint dictionaries."""
    fp = {0x1234567890abcdef: [0, 5, 10], 0x9876543210fedcba: [3, 8]}
    return fp, fp.copy()


@pytest.fixture
def completely_different_fingerprints():
    """Two fingerprints with no overlap."""
    fp_a = {0x1111111111111111: [0, 1, 2]}
    fp_b = {0x2222222222222222: [0, 1, 2]}
    return fp_a, fp_b


@pytest.fixture
def partial_overlap_fingerprints():
    """Two fingerprints with some overlap."""
    fp_a = {
        0x1234567890abcdef: [0, 5],
        0x9876543210fedcba: [3, 8],
        0xaaaaaaaaaaaaaaaa: [1, 6],
    }
    fp_b = {
        0x1234567890abcdef: [2, 7],     # Shared
        0x9876543210fedcba: [4, 9],     # Shared
        0xbbbbbbbbbbbbbbbb: [0, 10],    # Unique to b
    }
    return fp_a, fp_b


@pytest.fixture
def empty_fingerprints():
    """Two empty fingerprint dictionaries."""
    return {}, {}


# ═══════════════════════════════════════════════════════════════════
# FIXTURES: Corrupted and malicious files
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def corrupt_zip(temp_work_dir):
    """Create a corrupt ZIP file with truncated header."""
    zip_path = Path(temp_work_dir) / "corrupt.zip"
    # Write an invalid ZIP header
    with open(zip_path, "wb") as f:
        f.write(b"PK\x03\x04\x14\x00\x00\x00")  # Incomplete ZIP header
    return zip_path


@pytest.fixture
def path_traversal_zip(temp_work_dir):
    """Create a ZIP file with path traversal attempt (../../etc/passwd)."""
    zip_path = Path(temp_work_dir) / "traversal.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # Try to write a file with path traversal
        zf.writestr("../../etc/passwd", "root:x:0:0::/root:/bin/bash")
    return zip_path


@pytest.fixture
def nested_deep_zip(temp_work_dir):
    """Create nested ZIPs exceeding depth limit."""
    # Create nested.zip -> nested.zip -> nested.zip -> nested.zip (depth 4)
    inner_content = b"inner content"

    # Level 3
    level3_bytes = BytesIO()
    with zipfile.ZipFile(level3_bytes, "w") as zf:
        zf.writestr("data.txt", inner_content)

    # Level 2
    level2_bytes = BytesIO()
    with zipfile.ZipFile(level2_bytes, "w") as zf:
        zf.writestr("level3.zip", level3_bytes.getvalue())

    # Level 1
    level1_bytes = BytesIO()
    with zipfile.ZipFile(level1_bytes, "w") as zf:
        zf.writestr("level2.zip", level2_bytes.getvalue())

    # Level 0
    zip_path = Path(temp_work_dir) / "nested_deep.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("level1.zip", level1_bytes.getvalue())

    return zip_path


@pytest.fixture
def empty_zip(temp_work_dir):
    """Create an empty ZIP file."""
    zip_path = Path(temp_work_dir) / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        pass  # Empty ZIP
    return zip_path


# ═══════════════════════════════════════════════════════════════════
# FIXTURES: Helper files for ingestion testing
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def java_zip_submission(temp_work_dir):
    """Create a ZIP with Java source files."""
    zip_path = Path(temp_work_dir) / "submission.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Main.java", "public class Main { }")
        zf.writestr("Helper.java", "public class Helper { }")
    return zip_path


@pytest.fixture
def mixed_language_zip(temp_work_dir):
    """Create a ZIP with mixed language files (should detect as 'mixed')."""
    zip_path = Path(temp_work_dir) / "mixed.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Main.java", "public class Main { }")
        zf.writestr("main.py", "def main(): pass")
        zf.writestr("helper.cpp", "int helper() { }")
    return zip_path


@pytest.fixture
def single_java_file(temp_work_dir):
    """Create a single Java source file (non-ZIP)."""
    file_path = Path(temp_work_dir) / "Single.java"
    with open(file_path, "w") as f:
        f.write("public class Single { }")
    return file_path


# ═══════════════════════════════════════════════════════════════════
# HELPERS: Assertions and comparisons
# ═══════════════════════════════════════════════════════════════════

def assert_fingerprints_equal(fp1: dict, fp2: dict):
    """Assert that two fingerprint dicts are equivalent."""
    assert set(fp1.keys()) == set(fp2.keys()), "Different hash keys"
    for key in fp1:
        assert sorted(fp1[key]) == sorted(fp2[key]), f"Different positions for hash {key}"


def assert_score_in_range(score: float, min_val: float = 0.0, max_val: float = 1.0):
    """Assert that a similarity score is in valid range [0, 1]."""
    assert min_val <= score <= max_val, f"Score {score} out of range [{min_val}, {max_val}]"


def assert_tokens_equal(tokens1: list, tokens2: list):
    """Assert that two token lists are equal."""
    assert len(tokens1) == len(tokens2), f"Token count mismatch: {len(tokens1)} vs {len(tokens2)}"
    for t1, t2 in zip(tokens1, tokens2):
        assert t1.text == t2.text and t1.line == t2.line, f"Token mismatch: {t1} vs {t2}"
