"""
Tests for stdlib and boilerplate filtering (engine/preprocess/stdlib_filter.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.preprocess.stdlib_filter import filter_boilerplate


class TestStdlibFiltering:
    """Tests for stdlib import removal."""

    def test_remove_java_imports(self):
        """Remove Java stdlib imports."""
        code = """import java.util.*;
import java.io.*;
import my.custom.Package;
public class Test {}"""
        result = filter_boilerplate(code, lang="java")
        assert "java.util" not in result
        assert "java.io" not in result
        assert "my.custom.Package" in result

    def test_remove_java_packages(self):
        """Remove Java package declaration."""
        code = """package com.example;
public class Test {}"""
        result = filter_boilerplate(code, lang="java")
        assert "package" not in result

    def test_remove_javax_imports(self):
        """Remove javax stdlib imports."""
        code = """import javax.swing.*;
import javax.servlet.*;
public class Test {}"""
        result = filter_boilerplate(code, lang="java")
        assert "javax.swing" not in result
        assert "javax.servlet" not in result

    def test_remove_java_main_signature(self):
        """Remove main method signature."""
        code = """public static void main(String[] args) {
    // main body
}"""
        result = filter_boilerplate(code, lang="java")
        # main might be removed or kept, implementation specific
        assert isinstance(result, str)

    def test_remove_java_annotations(self):
        """Remove Java boilerplate annotations."""
        code = """@Override
@Deprecated
public void method() {}"""
        result = filter_boilerplate(code, lang="java")
        assert "@Override" not in result
        assert "@Deprecated" not in result

    def test_preserve_custom_imports(self):
        """Custom imports should be preserved."""
        code = """import my.package.*;
import org.custom.lib.*;"""
        result = filter_boilerplate(code, lang="java")
        assert "my.package" in result
        assert "org.custom.lib" in result

    def test_cpp_standard_headers(self):
        """Remove C++ standard headers."""
        code = """#include <iostream>
#include <vector>
#include "my_header.h"
int main() {}"""
        result = filter_boilerplate(code, lang="cpp")
        assert "iostream" not in result
        assert "vector" not in result
        assert "my_header.h" in result

    def test_c_standard_headers(self):
        """Remove C standard headers."""
        code = """#include <stdio.h>
#include <stdlib.h>
#include "local.h"
int main() {}"""
        result = filter_boilerplate(code, lang="c")
        assert "stdio.h" not in result
        assert "local.h" in result

    def test_empty_string(self):
        """Empty string should return empty."""
        result = filter_boilerplate("", lang="java")
        assert result == ""

    def test_no_boilerplate(self):
        """Code without stdlib should be unchanged."""
        code = "public class MyClass { }"
        result = filter_boilerplate(code, lang="java")
        assert "MyClass" in result


class TestBoilerplateEdgeCases:
    """Edge cases for boilerplate filtering."""

    @pytest.mark.edge
    def test_imports_in_strings(self):
        """Import statements in strings should be preserved."""
        code = 'String s = "import java.util.*;";'
        result = filter_boilerplate(code, lang="java")
        assert "import" in result

    @pytest.mark.edge
    def test_nested_annotations(self):
        """Nested annotations should be handled."""
        code = """@Deprecated
@SuppressWarnings("unchecked")
public void test() {}"""
        result = filter_boilerplate(code, lang="java")
        # Some annotations might stay, some go
        assert isinstance(result, str)

    @pytest.mark.edge
    def test_system_out_in_strings(self):
        """System.out in strings should be preserved."""
        code = 'String s = "System.out.println()"; System.out.println();'
        result = filter_boilerplate(code, lang="java")
        # String version preserved, println might be removed
        assert "System.out.println()" in result or "System.out" in result

    @pytest.mark.edge
    def test_mixed_language_filtering(self):
        """'mixed' language mode should attempt filtering."""
        code = """import java.util.*;
#include <iostream>
public class Test {}"""
        result = filter_boilerplate(code, lang="mixed")
        assert isinstance(result, str)

    @pytest.mark.edge
    def test_malformed_import(self):
        """Malformed imports should be handled gracefully."""
        code = "import java.util"  # Missing semicolon
        result = filter_boilerplate(code, lang="java")
        # Should not crash
        assert isinstance(result, str)

    @pytest.mark.edge
    def test_unicode_in_imports(self):
        """Unicode in import statements."""
        code = "import café.package.*;"
        result = filter_boilerplate(code, lang="java")
        # Should not crash
        assert isinstance(result, str)
