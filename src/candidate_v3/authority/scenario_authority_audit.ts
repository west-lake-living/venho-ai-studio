import { createHash } from "node:crypto";

import {
  validateScenarioAuthorityBindings,
  type ImageQcProfileSource,
} from "./scenario_authority_bindings";
import type { ScenarioAuthorityBindingV1 } from "./scenario_authority_binding";
import { ScenarioAuthorityRegistry } from "./scenario_authority_registry";

export interface ScenarioAuthorityAuditResult {
  readonly expectedScenarioCount: number;
  readonly approvedBindingCount: number;
  readonly resolvedScenarioCount: number;
  readonly unmatchedScenarioIds: readonly string[];
  readonly unexpectedScenarioIds: readonly string[];
  readonly duplicateApprovedScenarioIds: readonly string[];
  readonly retiredOnlyScenarioIds: readonly string[];
  readonly missingReferencedProfiles: readonly string[];
  readonly profileShaMismatches: readonly string[];
  readonly invalidExclusions: readonly string[];
  readonly status: "PASS" | "FAIL";
}

export interface P1T2ClosureGateResult {
  readonly audit: ScenarioAuthorityAuditResult;
  readonly checks: Readonly<Record<string, boolean>>;
  readonly status: "PASS" | "FAIL";
}

const ALLOWED_EXCLUSIONS = new Set<ScenarioAuthorityBindingV1["allowedExclusions"][number]>([
  "shot_distance",
  "camera_angle",
  "hairstyle",
  "pose",
  "outfit",
  "background",
]);

function sha256ProfileContent(content: Uint8Array): string {
  return createHash("sha256").update(content).digest("hex");
}

function isValidScenarioId(value: unknown): value is string {
  return typeof value === "string" && /^B\d{2}$/.test(value);
}

function isValidAllowedExclusions(value: unknown): value is ScenarioAuthorityBindingV1["allowedExclusions"] {
  if (!Array.isArray(value)) {
    return false;
  }
  const seen = new Set<string>();
  for (const exclusion of value) {
    if (!ALLOWED_EXCLUSIONS.has(exclusion) || seen.has(exclusion)) {
      return false;
    }
    seen.add(exclusion);
  }
  return true;
}

function frozen(values: readonly string[]): readonly string[] {
  return Object.freeze([...values]);
}

function isBindingLike(value: unknown): value is Partial<ScenarioAuthorityBindingV1> {
  return Boolean(value) && typeof value === "object";
}

function bindingIdOf(value: unknown): string {
  return isBindingLike(value) && typeof value.bindingId === "string" ? value.bindingId : "unknown";
}

function scenarioIdOf(value: unknown): string | undefined {
  return isBindingLike(value) && typeof value.scenarioId === "string" ? value.scenarioId : undefined;
}

function sortedUnique(values: readonly string[]): readonly string[] {
  return frozen([...new Set(values)].sort());
}

/**
 * Produces a deterministic, non-mutating audit report. It never repairs or
 * replaces authority data; any validator failure leaves the audit FAILED.
 */
export function auditScenarioAuthorityBindings(
  bindings: readonly ScenarioAuthorityBindingV1[],
  profiles: readonly ImageQcProfileSource[],
  lockedScenarioIds: readonly string[],
): ScenarioAuthorityAuditResult {
  const locked = new Set(lockedScenarioIds);
  const approvedByScenario = new Map<string, number>();
  const retiredByScenario = new Map<string, number>();
  const scenarioIds: string[] = [];
  const missingProfiles: string[] = [];
  const shaMismatches: string[] = [];
  const invalidExclusions: string[] = [];
  let approvedBindingCount = 0;
  let validatorEligible = lockedScenarioIds.length > 0 && locked.size === lockedScenarioIds.length;

  const profileById = new Map<string, ImageQcProfileSource>();
  for (const profile of profiles) {
    if (profileById.has(profile.profileId)) {
      validatorEligible = false;
      continue;
    }
    profileById.set(profile.profileId, profile);
    if (!(profile.content instanceof Uint8Array) || sha256ProfileContent(profile.content) !== profile.sha256) {
      shaMismatches.push(profile.profileId);
    }
  }

  for (const candidate of bindings) {
    const scenarioId = scenarioIdOf(candidate);
    if (scenarioId) {
      scenarioIds.push(scenarioId);
    } else {
      validatorEligible = false;
    }
    if (!isBindingLike(candidate)) {
      validatorEligible = false;
      continue;
    }

    if (
      candidate.schemaVersion !== "1.0" ||
      typeof candidate.bindingId !== "string" ||
      !/^candidate-v3-B\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*-v1$/.test(candidate.bindingId) ||
      !isValidScenarioId(candidate.scenarioId) ||
      typeof candidate.imageQcProfileId !== "string" ||
      typeof candidate.imageQcProfileSha256 !== "string" ||
      candidate.status !== "APPROVED" && candidate.status !== "RETIRED"
    ) {
      validatorEligible = false;
    }
    if (!isValidAllowedExclusions(candidate.allowedExclusions)) {
      invalidExclusions.push(bindingIdOf(candidate));
      validatorEligible = false;
    }

    if (candidate.status === "APPROVED") {
      approvedBindingCount += 1;
      if (scenarioId) {
        approvedByScenario.set(scenarioId, (approvedByScenario.get(scenarioId) ?? 0) + 1);
      }
      if (typeof candidate.imageQcProfileId !== "string") {
        validatorEligible = false;
        continue;
      }
      const profile = profileById.get(candidate.imageQcProfileId);
      if (!profile) {
        missingProfiles.push(candidate.imageQcProfileId);
      } else if (
        !(profile.content instanceof Uint8Array) ||
        candidate.imageQcProfileSha256 !== sha256ProfileContent(profile.content)
      ) {
        shaMismatches.push(candidate.imageQcProfileId);
      }
    } else if (candidate.status === "RETIRED" && scenarioId) {
      retiredByScenario.set(scenarioId, (retiredByScenario.get(scenarioId) ?? 0) + 1);
    }
  }

  const unmatched = lockedScenarioIds.filter((scenarioId) => !approvedByScenario.has(scenarioId));
  const unexpected = scenarioIds.filter((scenarioId) => !locked.has(scenarioId));
  const duplicates = [...approvedByScenario.entries()]
    .filter(([, count]) => count > 1)
    .map(([scenarioId]) => scenarioId);
  const retiredOnly = lockedScenarioIds.filter(
    (scenarioId) => !approvedByScenario.has(scenarioId) && (retiredByScenario.get(scenarioId) ?? 0) > 0,
  );

  let validatorPassed = false;
  if (validatorEligible && unmatched.length === 0 && unexpected.length === 0 && duplicates.length === 0) {
    try {
      validateScenarioAuthorityBindings(bindings, profiles, lockedScenarioIds);
      validatorPassed = true;
    } catch {
      validatorPassed = false;
    }
  }

  const result: ScenarioAuthorityAuditResult = Object.freeze({
    expectedScenarioCount: lockedScenarioIds.length,
    approvedBindingCount,
    resolvedScenarioCount: lockedScenarioIds.filter((scenarioId) => approvedByScenario.has(scenarioId)).length,
    unmatchedScenarioIds: frozen(unmatched),
    unexpectedScenarioIds: sortedUnique(unexpected),
    duplicateApprovedScenarioIds: sortedUnique(duplicates),
    retiredOnlyScenarioIds: frozen(retiredOnly),
    missingReferencedProfiles: sortedUnique(missingProfiles),
    profileShaMismatches: sortedUnique(shaMismatches),
    invalidExclusions: sortedUnique(invalidExclusions),
    status:
      validatorPassed &&
      approvedBindingCount === lockedScenarioIds.length &&
      unmatched.length === 0 &&
      unexpected.length === 0 &&
      duplicates.length === 0 &&
      missingProfiles.length === 0 &&
      shaMismatches.length === 0 &&
      invalidExclusions.length === 0
        ? "PASS"
        : "FAIL",
  });
  return result;
}

/** Runs the authority-only P1-T2 closure gate without enabling any runtime path. */
export function evaluateP1T2Closure(
  bindings: readonly ScenarioAuthorityBindingV1[],
  profiles: readonly ImageQcProfileSource[],
  lockedScenarioIds: readonly string[],
): P1T2ClosureGateResult {
  const audit = auditScenarioAuthorityBindings(bindings, profiles, lockedScenarioIds);
  const checks: Record<string, boolean> = {
    schemaVersionPresent: bindings.every((candidate) => candidate.schemaVersion === "1.0"),
    immutableRegistry: false,
    exactScenarioLookup: false,
    lockedCoverage: audit.resolvedScenarioCount === audit.expectedScenarioCount,
    unknownScenarioFailsClosed: false,
    retiredDoesNotResolve: bindings.every((candidate) => candidate.status !== "RETIRED"),
    duplicateApprovedFailsClosed: audit.duplicateApprovedScenarioIds.length === 0,
    profileExistence: audit.missingReferencedProfiles.length === 0,
    profileSha: audit.profileShaMismatches.length === 0,
    exclusionsWhitelist: audit.invalidExclusions.length === 0,
    scenarioAssignments: audit.status === "PASS",
  };

  try {
    const validated = validateScenarioAuthorityBindings(bindings, profiles, lockedScenarioIds);
    const registry = new ScenarioAuthorityRegistry(validated);
    checks.immutableRegistry = Object.isFrozen(registry.listApproved()) &&
      Object.isFrozen(registry.resolve(lockedScenarioIds[0]));
    checks.exactScenarioLookup = lockedScenarioIds.every((scenarioId) => registry.resolve(scenarioId).scenarioId === scenarioId);
    try {
      registry.resolve("__unknown_scenario__");
    } catch {
      checks.unknownScenarioFailsClosed = true;
    }
  } catch {
    // The audit remains the complete failure evidence; the gate never repairs data.
  }

  const frozenChecks = Object.freeze({ ...checks });
  const status = audit.status === "PASS" && Object.values(frozenChecks).every(Boolean) ? "PASS" : "FAIL";
  return Object.freeze({ audit, checks: frozenChecks, status });
}
