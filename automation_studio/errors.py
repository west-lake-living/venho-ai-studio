from __future__ import annotations


class AutomationError(Exception):
    """Base error for workflow-level failures."""


class WorkflowConfigError(AutomationError):
    """Raised when workflow YAML is invalid."""


class ActionRegistryError(AutomationError):
    """Raised when an action is missing or has invalid parameters."""


class WorkflowLockError(AutomationError):
    """Raised when a workflow lock already exists."""


class ManualGateReached(AutomationError):
    """Raised internally when a manual gate intentionally pauses a workflow."""

