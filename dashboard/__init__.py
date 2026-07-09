"""Module 10 Dashboard presentation adapters."""

MODULE_ID = "M10"
MODULE_NAME = "Dashboard"

from dashboard.gateway import DashboardGateway, build_dashboard_snapshot, face_gate_status

__all__ = ["DashboardGateway", "build_dashboard_snapshot", "face_gate_status", "MODULE_ID", "MODULE_NAME"]
