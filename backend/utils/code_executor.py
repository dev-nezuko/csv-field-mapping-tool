"""The old in-process Python runner is intentionally unavailable."""


class CodeExecutionDisabled(RuntimeError):
    pass


def code_runner(code, df):
    """Retain the old call boundary without executing or inspecting its inputs."""
    raise CodeExecutionDisabled(
        'Generated-code execution is disabled. An isolated executor is required.'
    )
