export interface ScenarioAuthorityBindingV1 {
  schemaVersion: "1.0";
  bindingId: string;
  scenarioId: string;
  imageQcProfileId: string;
  imageQcProfileSha256: string;
  allowedExclusions: Array<
    | "shot_distance"
    | "camera_angle"
    | "hairstyle"
    | "pose"
    | "outfit"
    | "background"
  >;
  approvedBy: string;
  approvedAt: string;
  status: "APPROVED" | "RETIRED";
}
