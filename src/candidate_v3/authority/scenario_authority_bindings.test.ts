import { readFileSync } from "node:fs";

import {
  IMAGE_QC_PROFILE_AUTHORITIES,
  SCENARIO_AUTHORITY_BINDINGS,
  validateScenarioAuthorityBindings,
  type ImageQcProfileSource,
} from "./scenario_authority_bindings";
import { ScenarioAuthorityRegistry } from "./scenario_authority_registry";
import type { ScenarioAuthorityBindingV1 } from "./scenario_authority_binding";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function expectThrows(action: () => unknown, code: string): void {
  try {
    action();
  } catch (error) {
    assert(error instanceof Error && error.message === code, `expected ${code}`);
    return;
  }
  throw new Error(`expected ${code}`);
}

function profileSources(): readonly ImageQcProfileSource[] {
  return Object.values(IMAGE_QC_PROFILE_AUTHORITIES).map((profile) => ({
    ...profile,
    content: readFileSync(profile.sourcePath),
  }));
}

function cloneBindings(): ScenarioAuthorityBindingV1[] {
  return SCENARIO_AUTHORITY_BINDINGS.map((binding) => ({
    ...binding,
    allowedExclusions: [...binding.allowedExclusions],
  }));
}

const validated = validateScenarioAuthorityBindings(SCENARIO_AUTHORITY_BINDINGS, profileSources());
assert(validated.length === 10, "expected ten validated bindings");

const registry = new ScenarioAuthorityRegistry(validated);
assert(registry.listApproved().length === 10, "expected ten approved bindings");
for (const scenarioId of ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10"]) {
  assert(registry.resolve(scenarioId).scenarioId === scenarioId, `missing ${scenarioId}`);
}

assert(registry.resolve("B03").imageQcProfileId === "action_full_body@1.0", "B03 profile mismatch");
assert(registry.resolve("B04").imageQcProfileId === "action_full_body@1.0", "B04 profile mismatch");
assert(
  JSON.stringify(registry.resolve("B03").allowedExclusions) === JSON.stringify(["shot_distance", "hairstyle"]),
  "B03 exclusions mismatch",
);
assert(
  JSON.stringify(registry.resolve("B04").allowedExclusions) === JSON.stringify(["shot_distance", "hairstyle"]),
  "B04 exclusions mismatch",
);
for (const scenarioId of ["B01", "B02", "B05", "B06", "B07", "B08", "B09", "B10"]) {
  assert(registry.resolve(scenarioId).imageQcProfileId === "canonical_default", `${scenarioId} profile mismatch`);
}

const tamperedHash = cloneBindings();
tamperedHash[0] = { ...tamperedHash[0], imageQcProfileSha256: "0".repeat(64) };
expectThrows(
  () => validateScenarioAuthorityBindings(tamperedHash, profileSources()),
  "SCENARIO_AUTHORITY_PROFILE_SHA_MISMATCH:canonical_default",
);

expectThrows(
  () => validateScenarioAuthorityBindings(SCENARIO_AUTHORITY_BINDINGS, profileSources().slice(1)),
  "SCENARIO_AUTHORITY_PROFILE_UNRESOLVED:canonical_default",
);

const missingScenario = cloneBindings().slice(1);
expectThrows(
  () => validateScenarioAuthorityBindings(missingScenario, profileSources()),
  "MISSING_LOCKED_SCENARIO_AUTHORITY:B01",
);

const unexpectedScenario = cloneBindings();
unexpectedScenario[0] = { ...unexpectedScenario[0], scenarioId: "B11", bindingId: "candidate-v3-B11-canonical-default-v1" };
expectThrows(
  () => validateScenarioAuthorityBindings(unexpectedScenario, profileSources()),
  "UNEXPECTED_SCENARIO_AUTHORITY_BINDING:B11",
);

const duplicateScenario = cloneBindings();
duplicateScenario[1] = { ...duplicateScenario[1], scenarioId: "B01", bindingId: "candidate-v3-B01-canonical-default-duplicate-v1" };
expectThrows(
  () => validateScenarioAuthorityBindings(duplicateScenario, profileSources()),
  "DUPLICATE_APPROVED_SCENARIO_BINDING:B01",
);

const retiredScenario = cloneBindings();
retiredScenario[0] = { ...retiredScenario[0], status: "RETIRED" };
expectThrows(
  () => validateScenarioAuthorityBindings(retiredScenario, profileSources()),
  "RETIRED_SCENARIO_AUTHORITY_BINDING:B01",
);

const invalidExclusion = cloneBindings();
invalidExclusion[0] = { ...invalidExclusion[0], allowedExclusions: ["not_allowed" as never] };
expectThrows(
  () => validateScenarioAuthorityBindings(invalidExclusion, profileSources()),
  "INVALID_SCENARIO_AUTHORITY_EXCLUSIONS:candidate-v3-B01-canonical-default-v1",
);

console.log("scenario_authority_bindings.test.ts: PASS");
