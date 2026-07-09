# M10 OPERATING CENTER — OS-Based Dashboard Design v2.0

Project: Ven Ho OS / VENHO AI Studio  
Module: M10 — Operating Center  
Document Type: UI/UX Design Specification  
Version: v2.0 (Review & Finalized)  
Purpose: Redesign M10 from a technical dashboard into a true AI Operating Center for daily founder operation.

## 1. Core Positioning

M10 is not a dashboard. M10 is the Operating Center of VENHO AI Studio. A dashboard reports information. An Operating Center guides action. The main question M10 must answer is:

What should I do next?

Everything on the screen must support that question.

## 2. Design Philosophy

### 2.1 OS-first

VENHO AI Studio should feel like an operating system, not a SaaS analytics panel. The UI should behave like a daily working environment:

- Open system and see current focus
- See today's tasks and check health parameters
- Continue unfinished work effortlessly
- Review system-generated warnings and move work through the pipeline

### 2.2 Founder-first

The default user is a solo founder/operator. The Home screen must not prioritize technical developer data. Hide from Home:

- Raw JSON structures and module contracts
- Token usage and cache status metrics
- Internal artifact paths and raw runtime/debug information

These metrics belong under: System → Developer.

### 2.3 Workflow-first

The user does not think in isolated technical modules. The user thinks in systemic workflows:

Observe → DNA → Prompt → Validate → Automate → Video → Publish → Analyze

Therefore, the architectural priority is: User → Workflow → Module.

Never: Module → Data → User.

### 2.4 Action-first

Every important status should immediately lead to a contextual action.

- Suboptimal: Validator: Failed
- Optimal: Validator: 7 failed [Button: Review Failed]

### 2.5 Five-second rule

Within five seconds, the Home interface must accurately answer:

1. What is the current project?
2. What is today's core focus?
3. What urgently needs attention?
4. Is the system stable and healthy?
5. What should I click next?

## 3. Recommended Information Architecture

Primary Navigation Sidebar:

- Home
- Projects
- Workbench
- Agents
- Publish
- Insights
- System

Internal modules must not be exposed as first-level navigation items. They belong inside workflow screens or project details.

Avoid exposing these as first-level navigation:

- Knowledge
- Prompt
- Validator
- Automation
- Video
- Publishing
- Analytics

## 4. Home Screen v2.0 Structure

Home is the main Operating Center. The priority ordering of components should be optimized as follows:

1. Current Focus
2. Today Task Center
3. Quick Actions
4. Pipeline Flow
5. Alerts Panel
6. System Health
7. Recent Activity Timeline

## 5. Header Component

Sets the global operating context without consuming unnecessary vertical screen space.

- Studio Title: VENHO AI STUDIO (Operating Center)
- Project Scope: Ven Hồ Hotel (Status: ACTIVE)
- Sync Metric: Last Sync: 14:23 | Mode: Read-only | Build: v1.x

## 6. Current Focus Section

This is the most critical user retention element in v2.0, helping the operator effortlessly resume dropped contexts.

Example:

```text
CURRENT FOCUS: Generate DNA for Room View Content
Progress: Step 3 / 8 | Status: In Progress
[ Continue Action Button ]
```

Empty state:

```text
No active focus. [ Choose Today's Focus ]
```

## 7. Top Status Cards

Strict limit of four high-level directional metrics cards to prevent cognitive overload.

Recommended card titles and actionable subtext:

- Today's Tasks — 2 Pending Tasks
- System Security — 2 Warnings Detected
- Automation Engine — 0 Running Jobs
- Publishing Queue — 1 Post Ready

Avoid vague single-word status labels.

## 8. Today Task Center

This section dominates the top half of the Home screen, providing immediate priority routing for the operator.

Example:

```text
TODAY PROGRESS: 2 / 5 Tasks Completed

[High Priority]
Review failed validations → [Review Button]
Review analytics snapshot → [Open Button]

[Medium Priority]
Approve publishing queue → [Approve Button]
Generate next room prompt → [Generate Button]

[Completed]
Backup knowledge snapshot
```

## 9. Quick Actions

Provides fast-travel shortcuts directly to specific production states. Buttons navigate to the correct workflows instead of making live, unverified background API calls:

- + Build DNA
- + Generate Prompt
- + Validate
- + Prepare Publish
- + Create Video
- + Run Automation

## 10. Pipeline Flow

Transforms the old, table-like pipeline into a visual, interconnected node graph.

Status rules:

- Ready (Green): No operational blockers.
- Need Review (Amber): Requires human-in-the-loop validation.
- Failed (Red): Strict action required before workflow path resumes.
- Missing (Gray): No active artifact or snapshot context detected.

## 11. System Health & Alerts

Alerts focus on human action requirements rather than verbose developer tracking. System Health checks give immediate operational assurance without dominating above-the-fold space.

Example:

```text
SYSTEM HEALTH SNAPSHOT:
- Knowledge / Prompt / Publishing: Healthy
- Validator / Automation: Critical Failure
- Analytics: Data Missing
```

## 12. Technical Architecture & Data Contracts

All developer debugging facilities (JSON Viewers, Raw Logs, Runtime variables) have been migrated cleanly to the System sub-navigation area. The principal home data asset schema remains located at:

```text
/artifacts/m10/home_snapshot.json
```

## 13. Implementation Strategy

- Phase 1: Home Core v2.0 Dashboard & Layout Structure
- Phase 2: Workbench View (Production space contexts)
- Phase 3: Project, Agent & Publishing Control Panels
- Phase 4: Deep Developer Tools & System Logging
- Phase 5: Command Palette Navigation (Cmd + K integration)

## Final Principle

Do not show the system. Guide the operator.

M10 should never force a solo founder to decipher technical architectures; it must empower them to run their AI business seamlessly.
