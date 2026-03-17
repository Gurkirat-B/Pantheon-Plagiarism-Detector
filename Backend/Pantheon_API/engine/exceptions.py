"""
engine/exceptions.py

All errors that the engine can raise during submission processing.

The backend catches EngineError subclasses and marks the analysis run
as failed. Any exception that isn't an EngineError is treated as an
unexpected internal error and also marks the run as failed.
"""


class EngineError(Exception):
    """Base class for all engine errors. Catch this in the backend to mark a run as failed."""
    pass


class CorruptZipError(EngineError):
    """The ZIP file could not be opened or is malformed."""
    pass


class EmptySubmissionError(EngineError):
    """The ZIP contained no supported source files after extraction."""
    pass


class UnsupportedFileTypeError(EngineError):
    """The uploaded file has an extension the engine doesn't support."""
    pass


class ZipTooLargeError(EngineError):
    """The ZIP file exceeds the maximum allowed compressed size."""
    pass


class ZipBombError(EngineError):
    """Decompressed size exceeds the safety threshold — likely a ZIP bomb."""
    pass


class PathTraversalError(EngineError):
    """A ZIP entry tried to write outside the extraction directory (path traversal attack)."""
    pass


class NestedZipDepthError(EngineError):
    """ZIP nesting depth exceeds the allowed limit."""
    pass
