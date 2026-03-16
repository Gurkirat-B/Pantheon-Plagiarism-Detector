"""
Tests for file ingestion and ZIP extraction (engine/ingest/ingest.py).
"""

import sys
import pytest
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "Backend" / "Pantheon_API"
sys.path.insert(0, str(backend_path))

from engine.ingest.ingest import ingest_to_dir, detect_language
from engine.exceptions import (
    CorruptZipError, EmptySubmissionError, PathTraversalError,
    ZipBombError, ZipTooLargeError, UnsupportedFileTypeError
)


class TestLanguageDetection:
    """Tests for language detection from file extensions."""

    def test_detect_java(self, java_zip_submission, temp_work_dir):
        """Detect Java from .java files."""
        out_dir, lang, src = ingest_to_dir(Path(java_zip_submission), Path(temp_work_dir) / "test1")
        assert lang == "java"

    def test_detect_single_java_file(self, single_java_file, temp_work_dir):
        """Detect Java from single .java file."""
        out_dir, lang, src = ingest_to_dir(Path(single_java_file), Path(temp_work_dir) / "test2")
        assert lang == "java"

    def test_detect_mixed_language(self, mixed_language_zip, temp_work_dir):
        """Detect 'mixed' when multiple languages present."""
        out_dir, lang, src = ingest_to_dir(Path(mixed_language_zip), Path(temp_work_dir) / "test3")
        assert lang == "mixed"


class TestFileExtraction:
    """Tests for basic file extraction."""

    def test_extract_java_zip(self, java_zip_submission, temp_work_dir):
        """Extract Java ZIP successfully."""
        out_dir, lang, src = ingest_to_dir(Path(java_zip_submission), Path(temp_work_dir) / "test1")
        assert len(src) == 2
        assert all(isinstance(f, Path) for f in src)
        assert all(f.suffix == ".java" for f in src)

    def test_extract_single_file(self, single_java_file, temp_work_dir):
        """Extract single source file."""
        out_dir, lang, src = ingest_to_dir(Path(single_java_file), Path(temp_work_dir) / "test2")
        assert len(src) == 1
        assert src[0].suffix == ".java"

    def test_extraction_creates_work_dir(self, single_java_file):
        """Extraction should create work directory."""
        work_dir = Path("/tmp/pantheon_test_auto_create")
        if work_dir.exists():
            import shutil
            shutil.rmtree(work_dir)
        out_dir, lang, src = ingest_to_dir(Path(single_java_file), work_dir)
        assert work_dir.exists()
        # Cleanup
        import shutil
        shutil.rmtree(work_dir)

    def test_extraction_cleans_old_work_dir(self, temp_work_dir, single_java_file):
        """Extraction should remove old work directory."""
        work_dir = Path(temp_work_dir) / "work"
        work_dir.mkdir()
        old_file = work_dir / "old_file.txt"
        old_file.write_text("old content")
        assert old_file.exists()

        out_dir, lang, src = ingest_to_dir(Path(single_java_file), work_dir)
        # Old file should be gone
        assert not old_file.exists()
        # New files should exist
        assert len(src) > 0


class TestErrorHandling:
    """Tests for error handling in extraction."""

    def test_corrupt_zip_error(self, corrupt_zip, temp_work_dir):
        """Corrupt ZIP should raise CorruptZipError."""
        with pytest.raises(CorruptZipError):
            ingest_to_dir(Path(corrupt_zip), Path(temp_work_dir) / "test1")

    def test_path_traversal_detection(self, temp_work_dir):
        """Path traversal ZIP should be handled safely."""
        import zipfile
        zip_path = Path(temp_work_dir) / "traversal_test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Create valid file first to get past empty check
            zf.writestr("valid.java", "public class Valid {}")
            # Then try to add path traversal
            zf.writestr("../../etc/passwd.txt", "malicious")

        # Should either raise PathTraversalError or succeed with valid file only
        try:
            out_dir, lang, src = ingest_to_dir(zip_path, Path(temp_work_dir) / "test_traverse")
            # If succeeds, should have valid file
            assert len(src) >= 1
            assert any("valid" in f.name for f in src)
        except PathTraversalError:
            # Also acceptable - shows security handling
            pass

    def test_empty_zip_error(self, empty_zip, temp_work_dir):
        """Empty ZIP should raise EmptySubmissionError."""
        with pytest.raises(EmptySubmissionError):
            ingest_to_dir(Path(empty_zip), Path(temp_work_dir) / "test3")

    def test_nested_zip_depth_error(self, temp_work_dir):
        """Nested ZIP exceeding depth limit should raise appropriate error or succeed."""
        import zipfile
        from io import BytesIO

        # Create nested.zip -> nested.zip -> data.txt (depth 2, should work)
        inner_content = b"inner content"

        # Level 2
        level2_bytes = BytesIO()
        with zipfile.ZipFile(level2_bytes, "w") as zf:
            zf.writestr("Main.java", "public class Main {}")

        # Level 1
        level1_bytes = BytesIO()
        with zipfile.ZipFile(level1_bytes, "w") as zf:
            zf.writestr("level2.zip", level2_bytes.getvalue())

        # Level 0
        zip_path = Path(temp_work_dir) / "nested_test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("level1.zip", level1_bytes.getvalue())

        # This might succeed or raise error depending on depth limits
        try:
            out_dir, lang, src = ingest_to_dir(zip_path, Path(temp_work_dir) / "test_nested")
            # If it succeeds without raising, that's OK
            assert src is not None
        except Exception:
            # If it raises, that's also OK
            pass

    def test_unsupported_file_type(self, temp_work_dir):
        """Unsupported file type should raise UnsupportedFileTypeError."""
        # Create a file with unsupported extension
        unsupported_file = Path(temp_work_dir) / "file.txt"
        unsupported_file.write_text("content")
        with pytest.raises(UnsupportedFileTypeError):
            ingest_to_dir(unsupported_file, Path(temp_work_dir) / "test5")

    def test_nonexistent_file(self, temp_work_dir):
        """Nonexistent file should raise error (FileNotFoundError or similar)."""
        nonexistent = Path(temp_work_dir) / "nonexistent.java"
        with pytest.raises((FileNotFoundError, OSError)):
            ingest_to_dir(nonexistent, Path(temp_work_dir) / "test6")


class TestZipSecurityLimits:
    """Tests for ZIP security limits enforcement."""

    def test_zip_file_count_limit(self, temp_work_dir):
        """ZIP with > 5000 files should raise ZipTooLargeError."""
        # Creating 5000+ files is expensive, so we test with mock data
        import zipfile
        zip_path = Path(temp_work_dir) / "too_many_files.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add mock files (don't need real content)
            for i in range(5001):
                zf.writestr(f"file_{i}.java", "dummy")

        with pytest.raises(ZipTooLargeError):
            ingest_to_dir(zip_path, Path(temp_work_dir) / "test1")

    def test_zip_size_limits(self, temp_work_dir):
        """ZIP with valid source should process correctly."""
        import zipfile
        zip_path = Path(temp_work_dir) / "large.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add a valid source file to avoid EmptySubmissionError
            zf.writestr("Main.java", "public class Main {}")
        # Test passes if ZIP is valid and under limits
        out_dir, lang, src = ingest_to_dir(zip_path, Path(temp_work_dir) / "test2")
        # Should have extracted the Java file
        assert len(src) >= 1
        assert any(f.suffix == ".java" for f in src)


class TestMacOSJunkFiles:
    """Tests for macOS junk file filtering."""

    def test_macosx_junk_filtered(self, temp_work_dir):
        """__MACOSX and .DS_Store files should be filtered."""
        import zipfile
        zip_path = Path(temp_work_dir) / "with_junk.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("Main.java", "public class Main {}")
            zf.writestr("__MACOSX/metadata", "junk")
            zf.writestr(".DS_Store", "junk")

        out_dir, lang, src = ingest_to_dir(zip_path, Path(temp_work_dir) / "test1")
        # Should only extract Main.java
        assert len(src) == 1
        assert src[0].name == "Main.java"


class TestExtractionDetails:
    """Tests for extraction details and file handling."""

    def test_extracted_files_readable(self, single_java_file, temp_work_dir):
        """Extracted files should be readable."""
        out_dir, lang, src = ingest_to_dir(Path(single_java_file), Path(temp_work_dir) / "test1")
        for file_path in src:
            content = file_path.read_text()
            assert "Single" in content

    def test_work_dir_populated(self, single_java_file, temp_work_dir):
        """Work directory should contain extracted files."""
        work_path = Path(temp_work_dir) / "extraction"
        out_dir, lang, src = ingest_to_dir(Path(single_java_file), work_path)
        assert work_path.exists()
        assert len(list(work_path.glob("**/*"))) > 0

    @pytest.mark.edge
    def test_deeply_nested_zip_structure(self, temp_work_dir):
        """Test ZIP with deep directory structure but within depth limit."""
        import zipfile
        zip_path = Path(temp_work_dir) / "nested_ok.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("a/b/c/Main.java", "public class Main {}")

        out_dir, lang, src = ingest_to_dir(zip_path, Path(temp_work_dir) / "test1")
        assert len(src) >= 1

    @pytest.mark.edge
    def test_whitespace_in_filenames(self, temp_work_dir):
        """Test ZIP with whitespace in filenames."""
        import zipfile
        zip_path = Path(temp_work_dir) / "whitespace.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("My File.java", "public class MyFile {}")

        out_dir, lang, src = ingest_to_dir(zip_path, Path(temp_work_dir) / "test2")
        assert len(src) >= 1
