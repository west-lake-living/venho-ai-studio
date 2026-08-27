import { readFileSync } from "node:fs";

import {
  IMAGE_QC_PROFILE_AUTHORITIES,
  LOCKED_BENCHMARK_SCENARIO_IDS,
  SCENARIO_AUTHORITY_BINDINGS,
  type ImageQcProfileSource,
} from "./scenario_authority_bindings";
import { auditScenarioAuthorityBindings, evaluateP1T2Closure } from "./scenario_authority_audit";
import type { ScenarioAuthorityBindingV1 } from "./scenario_authority_binding";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
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

function audit(bindings: readonly ScenarioAuthorityBindingV1[] = SCENARIO_AUTHORITY_BINDINGS) {
  return auditScenarioAuthorityBindings(bindings, profileSources(), LOCKED_BENCHMARK_SCENARIO_IDS);
}

const valid = audit();
assert(valid.expectedScenarioCount === 10, "expected ten locked scenarios");
assert(valid.approvedBindingCount === 10, "expected ten approved bindings");
assert(valid.resolvedScenarioCount === 10, "expected ten resolved scenarios");
assert(valid.unmatchedScenarioIds.length === 0, "expected no unmatched scenarios");
assert(valid.unexpectedScenarioIds.length === 0, "expected no unexpected scenarios");
assert(valid.duplicateApprovedScenarioIds.length === 0, "expected no duplicate scenarios");
assert(valid.missingReferencedProfiles.length === 0, "expected no missing profiles");
assert(valid.profileShaMismatches.length === 0, "expected no SHA mismatches");
assert(valid.invalidExclusions.length === 0, "expected no invalid exclusions");
assert(valid.status === "PASS", "expected audit PASS");

const closure = evaluateP1T2Closure(
  SCENARIO_AUTHORITY_BINDINGS,
  profileSources(),
  LOCKED_BENCHMARK_SCENARIO_IDS,
);
assert(closure.status === "PASS", "expected P1-T2 closure PASS");
assert(Object.values(closure.checks).every(Boolean), "all P1-T2 closure checks must pass");

const missing = cloneBindings().slice(1);
const missingResult = audit(missing);
assert(missingResult.status === "FAIL", "missing scenario must fail");
assert(JSON.stringify(missingResult.unmatchedScenarioIds) === JSON.stringify(["B01"]), "B01 must be unmatched");

const unexpected = cloneBindings();
unexpected[0] = {
  ...unexpected[0],
  scenarioId: "B11",
  bindingId: "candidate-v3-B11-canonical-default-v1",
};
const unexpectedResult = audit(unexpected);
assert(JSON.stringify(unexpectedResult.unexpectedScenarioIds) === JSON.stringify(["B11"]), "B11 must be unexpected");
assert(unexpectedResult.status === "FAIL", "unexpected scenario must fail");

const duplicate = cloneBindings();
duplicate[1] = {
  ...duplicate[1],
  scenarioId: "B01",
  bindingId: "candidate-v3-B01-canonical-default-duplicate-v1",
};
const duplicateResult = audit(duplicate);
assert(JSON.stringify(duplicateResult.duplicateApprovedScenarioIds) === JSON.stringify(["B01"]), "duplicate B01 must report");
assert(duplicateResult.status === "FAIL", "duplicate scenario must fail");

const missingProfile = audit(SCENARIO_AUTHORITY_BINDINGS);
const withoutActionProfile = profileSources().filter((profile) => profile.profileId !== "action_full_body@1.0");
const missingProfileResult = auditScenarioAuthorityBindings(
  SCENARIO_AUTHORITY_BINDINGS,
  withoutActionProfile,
  LOCKED_BENCHMARK_SCENARIO_IDS,
);
assert(JSON.stringify(missingProfileResult.missingReferencedProfiles) === JSON.stringify(["action_full_body@1.0"]), "missing profile must report");
assert(missingProfile.status === "PASS", "baseline must remain PASS");
assert(missingProfileResult.status === "FAIL", "missing profile must fail");

const tampered = profileSources().map((profile) =>
  profile.profileId === "canonical_default"
    ? { ...profile, content: new Uint8Array([...profile.content, 0]) }
    : profile,
);
const tamperedResult = auditScenarioAuthorityBindings(
  SCENARIO_AUTHORITY_BINDINGS,
  tampered,
  LOCKED_BENCHMARK_SCENARIO_IDS,
);
assert(JSON.stringify(tamperedResult.profileShaMismatches) === JSON.stringify(["canonical_default"]), "tampered SHA must report");
assert(tamperedResult.status === "FAIL", "tampered profile must fail");

const invalidExclusion = cloneBindings();
invalidExclusion[0] = { ...invalidExclusion[0], allowedExclusions: ["not_allowed" as never] };
const invalidExclusionResult = audit(invalidExclusion);
assert(
  JSON.stringify(invalidExclusionResult.invalidExclusions) ===
    JSON.stringify(["candidate-v3-B01-canonical-default-v1"]),
  "invalid exclusion must report binding",
);
assert(invalidExclusionResult.status === "FAIL", "invalid exclusion must fail");

const retired = cloneBindings();
retired[0] = { ...retired[0], status: "RETIRED" };
const retiredResult = audit(retired);
assert(JSON.stringify(retiredResult.retiredOnlyScenarioIds) === JSON.stringify(["B01"]), "retired-only B01 must report");
assert(JSON.stringify(retiredResult.unmatchedScenarioIds) === JSON.stringify(["B01"]), "retired-only B01 must be unmatched");
assert(retiredResult.status === "FAIL", "retired-only scenario must fail");

const firstSnapshot = JSON.stringify(SCENARIO_AUTHORITY_BINDINGS);
const firstAudit = JSON.stringify(audit());
const secondAudit = JSON.stringify(audit());
assert(firstAudit === secondAudit, "audit output must be deterministic");
assert(JSON.stringify(SCENARIO_AUTHORITY_BINDINGS) === firstSnapshot, "audit must not mutate bindings");
assert(SCENARIO_AUTHORITY_BINDINGS[2].allowedExclusions[0] === "shot_distance", "binding data was mutated");

console.log("scenario_authority_audit.test.ts: PASS");
