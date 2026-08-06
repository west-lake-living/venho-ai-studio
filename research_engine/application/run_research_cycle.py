"""One research cycle for one domain: question -> sources -> vault -> proposals.

This is what was missing between "the Research OS exists" and "the Research
OS produces anything". Every piece it uses was already written and tested --
`collect_source_note`, `synthesize_notes`, `PromotionPolicy` -- but nothing
called them outside a CLI a human had to drive by hand, so the vault held
zero notes and the four facts in the store were all bootstrap seeds.

The cycle, per plan v3.1 §6.7 and §7.2:

1. Read the domain's single written question. No question, no run -- the
   guardrail against "building an agent instead of selling rooms" is a
   refusal in code, not a paragraph in a doc.
2. Collect. Tavily for the search-backed domains; a file Harry exports for
   the ones where §7.2 forbids an automated source (OTA reviews). Nothing
   scrapes Facebook, Instagram or TikTok.
3. Write one R0 source note per result into the vault, then one R2 synthesis
   note that cites them and carries the question at its head.
4. Propose facts (Gemini, temperature 0, constrained schema) into
   `ProposedFactStore` as `pending_approval`.

What it does NOT do is create a fact. Step 4 stops at a proposal; approving
one is a separate, human act (`venho-research approve`, or the VENHO OS
dashboard), and even then the R2 note has to pass `PromotionPolicy`. DoD #13
holds: there is no code path from R2 to R3 without a person.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from research_engine.adapters.vault_reader import VaultReader
from research_engine.application.collect_sources import collect_source_note
from research_engine.application.extract_facts import extract_fact_proposals
from research_engine.application.synthesize_notes import synthesize_notes
from shared.storage.proposed_fact_store import ProposedFactStore, proposal_id

DEFAULT_CONFIG_ROOT = Path("config/projects/venho_hotel/research")
DEFAULT_VAULT_ROOT = Path("research")


@dataclass
class ResearchCycleResult:
    domain: str
    question: str
    sources_collected: int = 0
    source_notes: list[str] = field(default_factory=list)
    synthesis_note: Optional[str] = None
    proposals_created: int = 0
    proposals: list[dict[str, Any]] = field(default_factory=list)
    skipped_reason: Optional[str] = None

    @property
    def ran(self) -> bool:
        return self.skipped_reason is None


def load_research_questions(config_root: Path = DEFAULT_CONFIG_ROOT) -> dict[str, Any]:
    path = config_root / "research_questions.yaml"
    if not path.exists():
        return {}
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("domains", {})


def _rs_id(domain: str, discriminator: str, *, today: date) -> str:
    """Deterministic per (domain, day, source) so re-running a cycle the same
    day overwrites its own notes instead of littering the vault with copies."""
    safe = re.sub(r"[^A-Za-z0-9]+", "", discriminator)[-12:] or "x"
    return f"RS-{today.isoformat()}-{domain.replace('_', '')}-{safe}"


def _collect_tavily(config: dict[str, Any], *, api_key: str, http_post: Optional[Callable[..., Any]]) -> list[dict[str, Any]]:
    from research_engine.trend_radar.collectors.tavily_search import collect_tavily_search

    max_results = int(config.get("max_results", 8))
    collected: dict[str, dict[str, Any]] = {}
    for query in config.get("queries", []):
        try:
            for result in collect_tavily_search(query, api_key=api_key, max_results=max_results, http_post=http_post):
                # Dedupe across queries by URL: two queries for one domain
                # routinely return the same page, and a duplicate source note
                # would inflate the evidence behind a proposal.
                collected.setdefault(result["source_uri"], result)
        except Exception:  # noqa: BLE001 - one dead query must not lose the domain's other queries
            continue
    return list(collected.values())


def _collect_urls(
    urls: list[str], *, api_key: str, http_post: Optional[Callable[..., Any]]
) -> list[dict[str, Any]]:
    from research_engine.trend_radar.collectors.tavily_extract import extract_urls

    try:
        return extract_urls(urls, api_key=api_key, http_post=http_post)
    except Exception:  # noqa: BLE001 - a dead extract must not lose a domain that also has queries
        return []


def _collect_from_file(input_file: Path) -> list[dict[str, Any]]:
    text = input_file.read_text(encoding="utf-8")
    return [
        {
            "id": f"manual-{input_file.name}",
            "title": input_file.stem,
            "source_uri": f"file://{input_file.name}",
            "snippet": text[:8000],
        }
    ]


def _run_weather_cycle(
    result: ResearchCycleResult,
    *,
    project: str,
    config_root: Path,
    data_root: Path,
    vault_root: Path,
    today: date,
    http_get: Optional[Callable[..., Any]] = None,
) -> ResearchCycleResult:
    """The `weather_signal` domain: real forecast -> R2-T notes + a store the
    Saturday lane reads.

    Produces zero fact proposals, by design and not by omission. A
    WeatherSignal is R2-T: it shapes which scenario a post is shot in, and it
    can never become a citable claim (DoD #20, §6.6 "R2-T shapes the ANGLE,
    R3 supplies the FACT"). There is deliberately no path from here into
    ProposedFactStore.
    """
    from datetime import datetime

    from research_engine.trend_radar.application.scan_weather import scan_weather
    from research_engine.trend_radar.collectors.weather_api import collect_weather_forecast_from_policy
    from shared.storage.weather_signal_store import WeatherSignalStore

    policy_path = config_root / "weather_policy.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) if policy_path.exists() else {}
    forecasts = collect_weather_forecast_from_policy(policy, http_get=http_get, today=today)
    if not forecasts:
        result.skipped_reason = "weather provider returned no forecast"
        return result

    signals = scan_weather(forecasts, policy=policy, generated_at=datetime.now())
    result.sources_collected = len(signals)

    for signal in signals:
        try:
            path = VaultReader(vault_root).write_note(
                Path("notes") / "weather_signal" / f"{signal.rs_id}.md",
                {
                    "rs_id": signal.rs_id,
                    "type": "trend",
                    "domain": "weather_signal",
                    "evidence_level": "R2-T",
                    "status": "draft",
                    "collected_at": today.isoformat(),
                    "source_uri": "https://api.open-meteo.com/v1/forecast",
                    "confidence": 0.6,
                    # A forecast note that outlives its forecast is worse than
                    # no note: expiry comes from policy, never from the provider.
                    "expires_at": signal.expires_at[:10],
                    "promoted_fact_keys": [],
                    "related_briefs": [],
                    "verified_by_human": False,
                    "tags": ["weather", signal.condition],
                },
                f"# {signal.forecast_date} — {signal.condition}\n\n"
                f"- {signal.visual_opportunity}\n"
                f"- Scenario: {', '.join(signal.matching_scenario_keys) or 'chưa map'}\n",
            )
        except Exception:  # noqa: BLE001 - a note that will not write must not lose the store update below
            continue
        result.source_notes.append(str(path))

    WeatherSignalStore(project=project, data_root=data_root).replace(
        [signal.model_dump() for signal in signals]
    )
    return result


def run_research_cycle(
    domain: str,
    *,
    project: str = "venho_hotel",
    config_root: Path = DEFAULT_CONFIG_ROOT,
    vault_root: Path = DEFAULT_VAULT_ROOT,
    data_root: Path = Path("data/projects"),
    input_file: Optional[Path] = None,
    source_urls: Optional[list[str]] = None,
    today: Optional[date] = None,
    tavily_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    http_post: Optional[Callable[..., Any]] = None,
    http_get: Optional[Callable[..., Any]] = None,
    extract_fn: Optional[Callable[..., list[dict[str, Any]]]] = None,
    store: Optional[ProposedFactStore] = None,
) -> ResearchCycleResult:
    questions = load_research_questions(config_root)
    config = questions.get(domain)
    if config is None:
        raise ValueError(f"'{domain}' has no entry in research_questions.yaml")
    question = str(config.get("question") or "").strip()
    if not question:
        # §6.7's guardrail, enforced: a domain with no written question does
        # not get to run "just to see what turns up".
        raise ValueError(f"'{domain}' has no written research question — research does not run without one")

    result = ResearchCycleResult(domain=domain, question=question)
    today = today or date.today()
    collector = config.get("collector", "tavily")

    # URLs Harry named beat any search: for the hotel's own OTA review pages
    # and a curated competitor list, the address is already known.
    urls = list(source_urls or config.get("urls") or [])
    if input_file is not None:
        sources = _collect_from_file(input_file)
    elif urls:
        api_key = tavily_api_key if tavily_api_key is not None else os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            result.skipped_reason = "TAVILY_API_KEY not set"
            return result
        sources = _collect_urls(urls, api_key=api_key, http_post=http_post)
        if config.get("collector") == "tavily" and config.get("queries"):
            # A domain can have both: named pages plus a search sweep.
            sources = sources + [
                source
                for source in _collect_tavily(config, api_key=api_key, http_post=http_post)
                if source["source_uri"] not in {s["source_uri"] for s in sources}
            ]
    elif collector == "tavily":
        api_key = tavily_api_key if tavily_api_key is not None else os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            result.skipped_reason = "TAVILY_API_KEY not set"
            return result
        sources = _collect_tavily(config, api_key=api_key, http_post=http_post)
    elif collector == "weather":
        return _run_weather_cycle(
            result, project=project, config_root=config_root, data_root=data_root,
            vault_root=vault_root, today=today, http_get=http_get,
        )
    else:
        # manual: §7.2 permits no automated source (OTA reviews are an
        # explicit manual export).
        result.skipped_reason = f"collector '{collector}' needs --input-file (see manual_source_hint)"
        return result

    if not sources:
        result.skipped_reason = "no sources returned"
        return result
    result.sources_collected = len(sources)

    source_paths: list[Path] = []
    for source in sources:
        try:
            path = collect_source_note(
                rs_id=_rs_id(domain, source.get("source_uri", ""), today=today),
                domain=domain,
                source_uri=source.get("source_uri") or "unknown",
                title=re.sub(r"[^A-Za-z0-9]+", "-", str(source.get("title", "untitled")))[:60].strip("-") or "untitled",
                body=str(source.get("snippet", "")),
                vault_root=vault_root,
            )
        except Exception:  # noqa: BLE001 - a single unwritable note must not lose the cycle
            continue
        source_paths.append(path)
        result.source_notes.append(str(path))

    if source_paths:
        synthesis = synthesize_notes(
            rs_id=_rs_id(domain, "synthesis", today=today),
            domain=domain,
            question=question,
            source_paths=source_paths,
            vault_root=vault_root,
        )
        result.synthesis_note = str(synthesis)

    extract = extract_fn or extract_fact_proposals
    api_key = gemini_api_key if gemini_api_key is not None else os.environ.get("GEMINI_API_KEY", "")
    try:
        raw_proposals = extract(
            question=question,
            sources=sources,
            api_key=api_key,
            today=today,
            reject_past_dates=bool(config.get("reject_past_dates", True)),
        )
    except Exception:  # noqa: BLE001 - the vault notes above are the durable output; a failed extraction is a missing convenience, not a failed cycle
        raw_proposals = []

    proposals = [
        {
            **proposal,
            "id": proposal_id(domain, proposal["fact_key"], str(proposal["value"])),
            "domain": domain,
            "question": question,
            "synthesis_note": result.synthesis_note,
        }
        for proposal in raw_proposals
    ]
    if proposals:
        store = store or ProposedFactStore(project=project, data_root=data_root)
        result.proposals_created = store.merge_new(proposals)
    result.proposals = proposals
    return result


def run_all_research_cycles(
    *,
    project: str = "venho_hotel",
    config_root: Path = DEFAULT_CONFIG_ROOT,
    **kwargs: Any,
) -> list[ResearchCycleResult]:
    """Every domain with an automated collector. Manual-source domains are
    returned as skipped rather than silently omitted, so the report says
    plainly which domains are waiting on a human export."""
    results = []
    for domain in load_research_questions(config_root):
        try:
            results.append(run_research_cycle(domain, project=project, config_root=config_root, **kwargs))
        except Exception as exc:  # noqa: BLE001 - one domain's config error must not stop the rest
            results.append(ResearchCycleResult(domain=domain, question="", skipped_reason=f"{type(exc).__name__}: {exc}"))
    return results
