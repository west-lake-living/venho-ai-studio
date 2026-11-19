-- Preserve redacted provider evidence when a paid QC response is received.
ALTER TABLE paid_calls ADD COLUMN provider_response_json TEXT;
