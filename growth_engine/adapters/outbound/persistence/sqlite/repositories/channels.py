from __future__ import annotations

from growth_engine.domain.channels.channel import (
    Channel,
    ChannelConfig,
    ChannelPlatform,
    config_hash,
)

from ._base import SqliteRepository, canonical_json, parse_json


class ChannelRepository(SqliteRepository):
    def save_channel(self, channel: Channel, *, created_at_ms: int) -> None:
        self.connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name,
                enabled, paused, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                channel.id,
                channel.project_id,
                channel.environment,
                channel.channel_key,
                channel.platform.value,
                channel.remote_account_id,
                channel.name,
                int(channel.enabled),
                int(channel.paused),
                created_at_ms,
            ),
        )

    def get_channel(self, channel_id: str) -> Channel | None:
        row = self.connection.execute(
            """SELECT id, project_id, environment, channel_key, platform, remote_account_id,
                      name, enabled, paused
               FROM channels WHERE id=?""",
            (channel_id,),
        ).fetchone()
        if row is None:
            return None
        return Channel(
            id=row["id"],
            project_id=row["project_id"],
            environment=row["environment"],
            channel_key=row["channel_key"],
            platform=ChannelPlatform(row["platform"]),
            remote_account_id=row["remote_account_id"],
            name=row["name"],
            enabled=bool(row["enabled"]),
            paused=bool(row["paused"]),
        )

    def save_config(self, config: ChannelConfig, *, created_at_ms: int) -> None:
        self.connection.execute(
            """INSERT INTO channel_configs
               (id, channel_id, version, make_route_ref, graph_api_version, capability_json,
                caption_profile, config_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                config.id,
                config.channel_id,
                config.version,
                config.make_route_ref,
                config.graph_api_version,
                canonical_json(dict(config.capability)),
                config.caption_profile,
                config_hash(config),
                created_at_ms,
            ),
        )

    def get_config(self, config_id: str) -> ChannelConfig | None:
        row = self.connection.execute(
            """SELECT id, channel_id, version, make_route_ref, graph_api_version,
                      capability_json, caption_profile, config_hash
               FROM channel_configs WHERE id=?""",
            (config_id,),
        ).fetchone()
        if row is None:
            return None
        config = ChannelConfig(
            id=row["id"],
            channel_id=row["channel_id"],
            version=row["version"],
            make_route_ref=row["make_route_ref"],
            graph_api_version=row["graph_api_version"],
            capability=parse_json(row["capability_json"]),
            caption_profile=row["caption_profile"],
        )
        if config_hash(config) != row["config_hash"]:
            raise ValueError(f"stored channel config hash does not match {config_id!r}")
        return config
