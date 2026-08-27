import { createHash } from "node:crypto";

import {
  ScenarioAuthorityRegistryError,
} from "./scenario_authority_registry";
import type { ScenarioAuthorityBindingV1 } from "./scenario_authority_binding";

export const LOCKED_BENCHMARK_SCENARIO_IDS = Object.freeze([
  "B01",
  "B02",
  "B03",
  "B04",
  "B05",
  "B06",
  "B07",
  "B08",
  "B09",
  "B10",
] as const);

export interface ImageQcProfileAuthority {
  readonly profileId: string;
  readonly sourcePath: string;
  readonly sha256: string;
}

export interface ImageQcProfileSource extends ImageQcProfileAuthority {
  readonly content: Uint8Array;
}

/**
 * Raw-byte SHA-256 values for the server-owned profile sources. The validator
 * recomputes these values from the supplied source bytes before accepting a
 * binding dataset.
 */
export const IMAGE_QC_PROFILE_AUTHORITIES: Readonly<Record<string, ImageQcProfileAuthority>> =
  Object.freeze({
    canonical_default: Object.freeze({
      profileId: "canonical_default",
      sourcePath: "data/projects/venho_hotel/knowledge/VENHO_HOTEL_LINH_AN_DNA.json",
      sha256: "71f839dff776ec6d6d085c5a1ab928295af8c32a9699f7929d78b04807ec0075",
    }),
    "action_full_body@1.0": Object.freeze({
      profileId: "action_full_body@1.0",
      sourcePath: "config/projects/venho_hotel/subjects/linh_an.action_full_body.authority.yaml",
      sha256: "fe4a2b454a5868e9fc4dfbc4216e413a69a186cc8b4ab89c066943843c869b1c",
    }),
  });

const ALLOWED_EXCLUSIONS = new Set<ScenarioAuthorityBindingV1["allowedExclusions"][number]>([
  "shot_distance",
  "camera_angle",
  "hairstyle",
  "pose",
  "outfit",
  "background",
]);

function binding(
  scenarioId: string,
  profile: ImageQcProfileAuthority,
  allowedExclusions: ScenarioAuthorityBindingV1["allowedExclusions"],
): ScenarioAuthorityBindingV1 {
  return Object.freeze({
    schemaVersion: "1.0",
    bindingId: `candidate-v3-${scenarioId}-${profile.profileId.replace(/[^a-z0-9]+/gi, "-")}-v1`,
    scenarioId,
    imageQcProfileId: profile.profileId,
    imageQcProfileSha256: profile.sha256,
    allowedExclusions: Object.freeze([...allowedExclusions]),
    approvedBy: "human-owner",
    approvedAt: "2026-08-27T00:00:00Z",
    status: "APPROVED",
  }) as unknown as ScenarioAuthorityBindingV1;
}

/** The complete, immutable active authority dataset for the locked benchmark. */
export const SCENARIO_AUTHORITY_BINDINGS: readonly ScenarioAuthorityBindingV1[] = Object.freeze([
  binding("B01", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
  binding("B02", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
  binding("B03", IMAGE_QC_PROFILE_AUTHORITIES["action_full_body@1.0"], ["shot_distance", "hairstyle"]),
  binding("B04", IMAGE_QC_PROFILE_AUTHORITIES["action_full_body@1.0"], ["shot_distance", "hairstyle"]),
  binding("B05", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
  binding("B06", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
  binding("B07", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
  binding("B08", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
  binding("B09", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
  binding("B10", IMAGE_QC_PROFILE_AUTHORITIES.canonical_default, []),
]);

function fail(code: string): never {
  throw new ScenarioAuthorityRegistryError(code);
}

function sha256Bytes(content: Uint8Array): string {
  return createHash("sha256").update(content).digest("hex");
}

function isScenarioId(value: unknown): value is string {
  return typeof value === "string" && /^B\d{2}$/.test(value);
}

function isSha256(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}

function assertBindingShape(value: unknown): asserts value is ScenarioAuthorityBindingV1 {
  if (!value || typeof value !== "object") {
    fail("INVALID_SCENARIO_AUTHORITY_BINDING:unknown");
  }
  const candidate = value as Partial<ScenarioAuthorityBindingV1>;
  if (
    candidate.schemaVersion !== "1.0" ||
    typeof candidate.bindingId !== "string" ||
    !/^candidate-v3-B\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*-v1$/.test(candidate.bindingId) ||
    !isScenarioId(candidate.scenarioId) ||
    typeof candidate.imageQcProfileId !== "string" ||
    candidate.imageQcProfileId.length === 0 ||
    !isSha256(candidate.imageQcProfileSha256) ||
    typeof candidate.approvedBy !== "string" ||
    candidate.approvedBy.length === 0 ||
    typeof candidate.approvedAt !== "string" ||
    candidate.approvedAt.length === 0 ||
    (candidate.status !== "APPROVED" && candidate.status !== "RETIRED") ||
    !Array.isArray(candidate.allowedExclusions)
  ) {
    const bindingId = typeof candidate.bindingId === "string" ? candidate.bindingId : "unknown";
    fail(`INVALID_SCENARIO_AUTHORITY_BINDING:${bindingId}`);
  }

  const seen = new Set<string>();
  for (const exclusion of candidate.allowedExclusions) {
    if (!ALLOWED_EXCLUSIONS.has(exclusion) || seen.has(exclusion)) {
      fail(`INVALID_SCENARIO_AUTHORITY_EXCLUSIONS:${candidate.bindingId}`);
    }
    seen.add(exclusion);
  }
}

function freezeBinding(bindingValue: ScenarioAuthorityBindingV1): ScenarioAuthorityBindingV1 {
  return Object.freeze({
    ...bindingValue,
    allowedExclusions: Object.freeze([...bindingValue.allowedExclusions]),
  }) as unknown as ScenarioAuthorityBindingV1;
}

/**
 * Validates the complete server-side authority dataset and returns an
 * immutable active copy. No caller-provided profile metadata is trusted:
 * profile bytes are hashed locally and must match both source and binding.
 */
export function validateScenarioAuthorityBindings(
  bindings: readonly ScenarioAuthorityBindingV1[],
  profiles: readonly ImageQcProfileSource[],
  lockedScenarioIds: readonly string[] = LOCKED_BENCHMARK_SCENARIO_IDS,
): readonly ScenarioAuthorityBindingV1[] {
  const locked = new Set(lockedScenarioIds);
  if (
    locked.size !== lockedScenarioIds.length ||
    lockedScenarioIds.length === 0 ||
    lockedScenarioIds.some((scenarioId) => !isScenarioId(scenarioId))
  ) {
    fail("INVALID_LOCKED_SCENARIO_IDS");
  }

  const profileById = new Map<string, ImageQcProfileSource>();
  for (const profile of profiles) {
    if (
      !profile ||
      typeof profile.profileId !== "string" ||
      profile.profileId.length === 0 ||
      !isSha256(profile.sha256) ||
      !(profile.content instanceof Uint8Array)
    ) {
      fail("INVALID_SCENARIO_AUTHORITY_PROFILE");
    }
    if (profileById.has(profile.profileId)) {
      fail(`DUPLICATE_SCENARIO_AUTHORITY_PROFILE:${profile.profileId}`);
    }
    const actualSha256 = sha256Bytes(profile.content);
    if (actualSha256 !== profile.sha256) {
      fail(`SCENARIO_AUTHORITY_PROFILE_SOURCE_SHA_MISMATCH:${profile.profileId}`);
    }
    profileById.set(profile.profileId, profile);
  }

  const activeByScenario = new Map<string, ScenarioAuthorityBindingV1>();
  const bindingIds = new Set<string>();
  for (const candidate of bindings) {
    assertBindingShape(candidate);
    if (candidate.status === "RETIRED") {
      fail(`RETIRED_SCENARIO_AUTHORITY_BINDING:${candidate.scenarioId}`);
    }
    if (!locked.has(candidate.scenarioId)) {
      fail(`UNEXPECTED_SCENARIO_AUTHORITY_BINDING:${candidate.scenarioId}`);
    }
    if (bindingIds.has(candidate.bindingId)) {
      fail(`DUPLICATE_SCENARIO_AUTHORITY_BINDING_ID:${candidate.bindingId}`);
    }
    bindingIds.add(candidate.bindingId);
    if (activeByScenario.has(candidate.scenarioId)) {
      fail(`DUPLICATE_APPROVED_SCENARIO_BINDING:${candidate.scenarioId}`);
    }

    const profile = profileById.get(candidate.imageQcProfileId);
    if (!profile) {
      fail(`SCENARIO_AUTHORITY_PROFILE_UNRESOLVED:${candidate.imageQcProfileId}`);
    }
    const actualSha256 = sha256Bytes(profile.content);
    if (candidate.imageQcProfileSha256 !== actualSha256) {
      fail(`SCENARIO_AUTHORITY_PROFILE_SHA_MISMATCH:${candidate.imageQcProfileId}`);
    }
    activeByScenario.set(candidate.scenarioId, candidate);
  }

  for (const scenarioId of lockedScenarioIds) {
    if (!activeByScenario.has(scenarioId)) {
      fail(`MISSING_LOCKED_SCENARIO_AUTHORITY:${scenarioId}`);
    }
  }

  return Object.freeze([...lockedScenarioIds].map((scenarioId) => freezeBinding(activeByScenario.get(scenarioId)!)));
}
