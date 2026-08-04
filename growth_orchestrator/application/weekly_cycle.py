from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver
from agent_studio.growth.scenario_registry import ScenarioRegistry
from content_studio.content_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT
from growth_orchestrator.application.daily_cycle import CADENCE_DAYS, DailyCycleResult, run_daily_cycle
from growth_orchestrator.bridges.m03_validator_bridge import M03ValidatorBridge
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge
from publishing_gateway.publication_registry import PublicationRegistry

# Cadence order matters for the rotation cursor (_next_rotation_index in
# daily_cycle.py): running Mon/Wed/Fri/Sat in this order within a single
# call advances each lane's rotation the same way four separate cron ticks
# across the week would have, so the topics picked here match what the old
# per-day cron would have produced -- this just does all four in one sitting
# instead of trickling in through the week, so Harry can review a whole
# week's batch in a single VENHO OS Dashboard session.
WEEKLY_CADENCE_ORDER = ["monday", "wednesday", "friday", "saturday"]


@dataclass
class WeeklyCycleResult:
    days: list[DailyCycleResult] = field(default_factory=list)

    @property
    def publications(self) -> list[dict[str, Any]]:
        return [pub for day in self.days for pub in day.publications]


def run_weekly_cycle(
    *,
    project: str = "venho_hotel",
    platforms: Optional[list[str]] = None,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    registry: Optional[PublicationRegistry] = None,
    scenario_registry: Optional[ScenarioRegistry] = None,
    image_provider: Optional[Any] = None,
    reference_resolver: Optional[ReferenceAssetResolver] = None,
    generate_image: bool = True,
    content_bridge: Optional[M05ContentBridge] = None,
    validator_bridge: Optional[M03ValidatorBridge] = None,
    image_validation_provider: str = "mock",
) -> WeeklyCycleResult:
    """Generate a full week's cadence (Mon/Wed/Fri/Sat) in one run.

    Same per-day pipeline as run_daily_cycle -- called once per cadence day
    so a whole week's drafts land PENDING_APPROVAL together, instead of one
    day's worth appearing per cron tick across the week. Callers share one
    registry/scenario_registry/content_bridge across all four days so the
    rotation cursor and dashboard review list behave exactly as if this ran
    from four separate `daily-cycle` invocations.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    scenario_registry = scenario_registry or ScenarioRegistry.from_file()
    content_bridge = content_bridge or M05ContentBridge(
        config_root=config_root, data_root=data_root, scenario_registry=scenario_registry
    )

    results: list[DailyCycleResult] = []
    for day in WEEKLY_CADENCE_ORDER:
        assert day in CADENCE_DAYS
        try:
            results.append(
                run_daily_cycle(
                    day,
                    project=project,
                    platforms=platforms,
                    config_root=config_root,
                    data_root=data_root,
                    registry=registry,
                    scenario_registry=scenario_registry,
                    image_provider=image_provider,
                    reference_resolver=reference_resolver,
                    generate_image=generate_image,
                    content_bridge=content_bridge,
                    validator_bridge=validator_bridge,
                    image_validation_provider=image_validation_provider,
                )
            )
        except Exception as exc:  # noqa: BLE001 - one day's uncaught failure (e.g. topic config error) must not drop the rest of the week's batch
            results.append(
                DailyCycleResult(
                    day=day,
                    topic={},
                    publications=[],
                    errors=[{"platform": "*", "error": f"{type(exc).__name__}: {exc}"}],
                )
            )
    return WeeklyCycleResult(days=results)
