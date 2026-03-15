class EngineError(Exception):
    """Base for all engine errors. Backend catches this to mark run as failed."""
    pass

class CorruptZipError(EngineError):
    pass

class EmptySubmissionError(EngineError):
    pass

class UnsupportedFileTypeError(EngineError):
    pass

class ZipTooLargeError(EngineError):
    pass

class ZipBombError(EngineError):
    """Decompressed size exceeds safety threshold — possible zip bomb."""
    pass

class PathTraversalError(EngineError):
    """ZIP entry tried to escape extraction directory."""
    pass

class NestedZipDepthError(EngineError):
    """ZIP nesting exceeds allowed depth."""
    pass
