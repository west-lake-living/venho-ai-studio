-- 0007_command_signing_key.sql — retain only the key identifier needed to re-issue a stable capability.
ALTER TABLE outbox_commands ADD COLUMN signing_key_id TEXT;
