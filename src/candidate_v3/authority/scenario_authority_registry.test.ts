import type { ScenarioAuthorityBindingV1 } from "./scenario_authority_binding";
import {
  ScenarioAuthorityRegistry,
  ScenarioAuthorityRegistryError,
} from "./scenario_authority_registry";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(`ASSERTION_FAILED:${message}`);
  }
}

function assertEqual(actual: unknown, expected: unknown, message: string): void {
  assert(actual === expected, `${message}: expected ${String(expected)}, got ${String(actual)}`);
}

function assertThrows(action: () => unknown, expectedMessage: string): void {
  try {
    action();
  } catch (error) {
    assert(error instanceof ScenarioAuthorityRegistryError, "unexpected error type");
    assertEqual(error.message, expectedMessage, "unexpected error message");
    return;
  }
  throw new Error(`ASSERTION_FAILED:expected ${expectedMessage}`);
}

function assertRuntimeThrows(action: () => unknown, message: string): void {
  try {
    action();
  } catch {
    return;
  }
  throw new Error(`ASSERTION_FAILED:${message}`);
}

function binding(
  overrides: Partial<ScenarioAuthorityBindingV1> = {},
): ScenarioAuthorityBindingV1 {
  return {
    schemaVersion: "1.0",
    bindingId: "binding-scene-a-approved",
    scenarioId: "scene-a",
    imageQcProfileId: "profile-v1",
    imageQcProfileSha256: "a".repeat(64),
    allowedExclusions: ["background"],
    approvedBy: "human-owner",
    approvedAt: "2026-08-27T00:00:00Z",
    status: "APPROVED",
    ...overrides,
  };
}

function testApprovedBindingResolves(): void {
  const registry = new ScenarioAuthorityRegistry([binding()]);
  assertEqual(registry.resolve("scene-a").bindingId, "binding-scene-a-approved", "approved binding");
  assert(registry.has("scene-a"), "approved binding should be present");
}

function testExactScenarioIdOnly(): void {
  const registry = new ScenarioAuthorityRegistry([binding()]);
  assertThrows(() => registry.resolve("scene-a-extra"), "SCENARIO_AUTHORITY_UNRESOLVED:scene-a-extra");
  assertThrows(() => registry.resolve("SCENE-A"), "SCENARIO_AUTHORITY_UNRESOLVED:SCENE-A");
  assert(!registry.has("scene-a-extra"), "fuzzy scenario id must not resolve");
}

function testUnknownAndRetiredOnlyFailClosed(): void {
  const registry = new ScenarioAuthorityRegistry([
    binding({ bindingId: "binding-scene-retired", scenarioId: "scene-retired", status: "RETIRED" }),
  ]);
  assertThrows(() => registry.resolve("scene-unknown"), "SCENARIO_AUTHORITY_UNRESOLVED:scene-unknown");
  assertThrows(() => registry.resolve("scene-retired"), "SCENARIO_AUTHORITY_UNRESOLVED:scene-retired");
}

function testDuplicateApprovedBindingsFailAtConstruction(): void {
  assertThrows(
    () => new ScenarioAuthorityRegistry([
      binding(),
      binding({ bindingId: "binding-scene-a-approved-2" }),
    ]),
    "DUPLICATE_APPROVED_SCENARIO_BINDING:scene-a",
  );
}

function testApprovedWinsOverRetiredAndRetiredIsExcluded(): void {
  const registry = new ScenarioAuthorityRegistry([
    binding({ bindingId: "binding-scene-a-retired", status: "RETIRED" }),
    binding({ bindingId: "binding-scene-a-approved" }),
  ]);
  assertEqual(registry.resolve("scene-a").status, "APPROVED", "approved binding should resolve");
  assertEqual(registry.listApproved().length, 1, "retired binding should be excluded");
}

function testReturnedAuthorityCannotMutateRegistry(): void {
  const registry = new ScenarioAuthorityRegistry([binding()]);
  const listed = registry.listApproved();
  assertRuntimeThrows(() => (listed as ScenarioAuthorityBindingV1[]).push(binding({ scenarioId: "scene-b" })), "list mutation");
  assertRuntimeThrows(() => {
    (registry.resolve("scene-a") as ScenarioAuthorityBindingV1).scenarioId = "scene-b";
  }, "binding mutation");
  assertRuntimeThrows(() => {
    (registry.resolve("scene-a") as ScenarioAuthorityBindingV1).allowedExclusions.push("pose");
  }, "exclusion mutation");
  assertEqual(registry.resolve("scene-a").scenarioId, "scene-a", "registry authority must remain unchanged");
}

testApprovedBindingResolves();
testExactScenarioIdOnly();
testUnknownAndRetiredOnlyFailClosed();
testDuplicateApprovedBindingsFailAtConstruction();
testApprovedWinsOverRetiredAndRetiredIsExcluded();
testReturnedAuthorityCannotMutateRegistry();
