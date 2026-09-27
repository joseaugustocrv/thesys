class ThesysError(Exception):
    """Base error for Thesys."""

class MethodologyError(ThesysError):
    pass

class ProjectError(ThesysError):
    pass
