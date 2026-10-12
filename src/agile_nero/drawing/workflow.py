"""Compatibility exports only; add new code to the domain module."""

from agile_nero.workflow.offline import WorkflowResult, run_task, run_tool

__all__ = ["WorkflowResult", "run_task", "run_tool"]
