import type { ScenarioAuthorityBindingV1 } from "./scenario_authority_binding";

export class ScenarioAuthorityRegistryError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "ScenarioAuthorityRegistryError";
    this.code = code;
  }
}

type ImmutableBinding = Omit<ScenarioAuthorityBindingV1, "allowedExclusions"> & {
  readonly allowedExclusions: readonly ScenarioAuthorityBindingV1["allowedExclusions"][number][];
};
type ApprovedBinding = Readonly<ImmutableBinding>;

function freezeBinding(binding: ScenarioAuthorityBindingV1): ApprovedBinding {
  const exclusions = Object.freeze([...binding.allowedExclusions]);
  return Object.freeze({
    ...binding,
    allowedExclusions: exclusions,
  });
}

function invalidBinding(binding: unknown): never {
  const bindingId = typeof binding === "object" && binding !== null && "bindingId" in binding
    ? String((binding as { bindingId: unknown }).bindingId)
    : "unknown";
  throw new ScenarioAuthorityRegistryError(`INVALID_SCENARIO_AUTHORITY_BINDING:${bindingId}`);
}

function assertBinding(binding: ScenarioAuthorityBindingV1): void {
  if (
    !binding ||
    binding.schemaVersion !== "1.0" ||
    typeof binding.bindingId !== "string" ||
    binding.bindingId.length === 0 ||
    typeof binding.scenarioId !== "string" ||
    binding.scenarioId.length === 0 ||
    (binding.status !== "APPROVED" && binding.status !== "RETIRED") ||
    !Array.isArray(binding.allowedExclusions)
  ) {
    invalidBinding(binding);
  }
}

/** Immutable, exact-match registry for server-owned scenario authority. */
export class ScenarioAuthorityRegistry {
  #approvedByScenario = new Map<string, ApprovedBinding>();
  #approvedBindings: readonly ApprovedBinding[];

  constructor(bindings: readonly ScenarioAuthorityBindingV1[]) {
    const approved: ApprovedBinding[] = [];

    for (const binding of bindings) {
      assertBinding(binding);
      if (binding.status !== "APPROVED") {
        continue;
      }
      if (this.#approvedByScenario.has(binding.scenarioId)) {
        throw new ScenarioAuthorityRegistryError(
          `DUPLICATE_APPROVED_SCENARIO_BINDING:${binding.scenarioId}`,
        );
      }
      const frozen = freezeBinding(binding);
      this.#approvedByScenario.set(binding.scenarioId, frozen);
      approved.push(frozen);
    }

    this.#approvedBindings = Object.freeze(approved);
    Object.freeze(this);
  }

  resolve(scenarioId: string): ApprovedBinding {
    const binding = this.#approvedByScenario.get(scenarioId);
    if (!binding) {
      throw new ScenarioAuthorityRegistryError(`SCENARIO_AUTHORITY_UNRESOLVED:${scenarioId}`);
    }
    return binding;
  }

  has(scenarioId: string): boolean {
    return this.#approvedByScenario.has(scenarioId);
  }

  listApproved(): readonly ApprovedBinding[] {
    return this.#approvedBindings;
  }
}
