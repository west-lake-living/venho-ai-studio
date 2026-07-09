# M10 OPERATING CENTER --- OS-Based Dashboard Design v1.0

> **Project:** Ven Ho OS\
> **Module:** M10 -- Operating Center\
> **Status:** Final Design Specification\
> **Version:** v1.0

------------------------------------------------------------------------

# 1. Vision

## Purpose

M10 is **not a technical dashboard**.

M10 is the **Operating Center** of Ven Ho OS.

Its purpose is to help the founder operate the business, not inspect
system internals.

When opening Ven Ho OS each morning, the user should immediately know:

-   What needs attention today
-   Whether the system is healthy
-   Which workflow stage requires action
-   Which AI agents are running
-   What should be done next

Everything else is secondary.

------------------------------------------------------------------------

# 2. Core Design Philosophy

## Founder First

The interface is optimized for a business operator.

Developer information must never dominate the Home screen.

Hide by default:

-   Raw JSON
-   Token usage
-   Cache status
-   Runtime internals
-   Artifact paths
-   Module contracts

These belong only inside **System → Developer**.

------------------------------------------------------------------------

## Workflow First

Never expose architecture before workflow.

The user thinks like this:

Observe

↓

Build DNA

↓

Generate Prompt

↓

Validate

↓

Automate

↓

Create Video

↓

Publish

↓

Analyze

The UI must follow this mental model.

------------------------------------------------------------------------

## Read Only

M10 never owns business logic.

Responsibilities:

-   Read artifacts
-   Aggregate status
-   Display information
-   Navigate to workflow

Responsibilities NOT allowed:

-   Live API calls
-   Editing artifacts
-   Business calculations
-   Data duplication

------------------------------------------------------------------------

## Five Second Rule

Within five seconds the user must understand:

-   Current project
-   System health
-   Today's priorities
-   Current pipeline position
-   Next action

------------------------------------------------------------------------

# 3. Global Navigation

Primary navigation:

``` text
🏠 Home
📂 Projects
🛠 Workbench
🤖 Agents
📢 Publishing
📈 Insights
⚙ System
```

Do NOT expose internal modules in the sidebar.

Avoid:

``` text
Knowledge
Prompt
Validator
Automation
Publishing
Analytics
```

Those belong behind the workflow.

------------------------------------------------------------------------

# 4. Home Screen

Home is the default landing page.

It answers one question:

**What should I do now?**

## Header

``` text
VENHO AI OPERATING SYSTEM

Project
Ven Hồ Hotel

Status
ACTIVE

Mode
Read Only Operating Center

Date
Today
```

------------------------------------------------------------------------

## Top Summary Cards

Exactly four summary cards.

``` text
Today's Tasks

System Health

Active Jobs

Publishing Status
```

Avoid meaningless counters like:

-   DNA Subjects
-   Validation Runs
-   Automation Jobs

Those belong inside Project Detail.

------------------------------------------------------------------------

# 5. Today

Highest priority section.

Purpose:

Present today's actionable work.

Example:

``` text
TODAY

□ Review failed validations

□ Approve Facebook post

□ Generate room prompt

□ Check publishing queue

□ Review analytics snapshot
```

Data source:

``` text
/artifacts/tasks/today.json
/artifacts/planning/weekly_focus.json
/artifacts/automation/pending_jobs.json
/artifacts/validator/failed_runs.json
```

------------------------------------------------------------------------

# 6. System Health

Purpose:

Show overall operating health.

Example:

``` text
Knowledge      Healthy

Prompt         Healthy

Validator      Warning

Automation     Healthy

Publishing     Warning

Analytics      Missing
```

Allowed status:

-   Healthy
-   Warning
-   Critical
-   Missing

------------------------------------------------------------------------

# 7. Pipeline

Pipeline is the visual backbone.

``` text
Observe

↓

DNA

↓

Prompt

↓

Validate

↓

Automation

↓

Video

↓

Publishing

↓

Analytics
```

Every stage displays:

-   Status
-   Ready
-   Need Review
-   Failed
-   Action

Example:

``` text
Validate

Ready
27

Need Review
3

Failed
2

Action
Review Failed
```

------------------------------------------------------------------------

# 8. Alerts

Purpose:

Surface only important issues.

Example:

``` text
⚠ Analytics snapshot missing

⚠ Two validation failures

⚠ Publishing queue waiting approval
```

If no issue:

``` text
All systems healthy.
```

------------------------------------------------------------------------

# 9. Recent Activity

Chronological timeline.

Example:

``` text
09:12 Validator completed

08:55 Prompt generated

08:21 Facebook prepared

Yesterday Analytics imported
```

------------------------------------------------------------------------

# 10. Workbench

Workbench is where work begins.

Quick actions:

``` text
Build DNA

Generate Prompt

Validate Output

Prepare Publishing

Create Video

Run Automation
```

Sections:

-   Quick Actions
-   Pending Reviews
-   Draft Outputs
-   Ready To Publish
-   Failed Items

------------------------------------------------------------------------

# 11. Projects

Project list:

``` text
Ven Hồ Hotel

Linh An

Solar

Stock
```

Project detail tabs:

``` text
Overview

Knowledge

Content

Validation

Automation

Publishing

Analytics

Files
```

Detailed metrics belong here.

------------------------------------------------------------------------

# 12. Agents

Purpose:

Monitor AI workers.

Example:

``` text
Knowledge Agent
Idle

Prompt Agent
Ready

Validation Agent
Warning

Publishing Agent
Waiting Approval

Analytics Agent
Missing Data
```

------------------------------------------------------------------------

# 13. Publishing

Sections:

-   Ready
-   Scheduled
-   Published
-   Failed

Approval workflow is displayed here.

------------------------------------------------------------------------

# 14. Insights

Display analytics only.

If snapshot unavailable:

``` text
No analytics snapshot available.
```

Do not display technical errors.

------------------------------------------------------------------------

# 15. System

Developer tools only.

Tabs:

``` text
Runtime

Artifacts

JSON Viewer

Module Status

Logs

Settings
```

All existing JSON viewers move here.

------------------------------------------------------------------------

# 16. Visual Design Principles

Use:

-   Large whitespace
-   Clean typography
-   Calm colors
-   Professional appearance

Avoid:

-   Long paragraphs
-   Technical explanations
-   Raw JSON
-   Dense statistics

Status colors:

-   Green = Healthy
-   Amber = Warning
-   Red = Critical
-   Gray = Missing
-   Blue = Active

------------------------------------------------------------------------

# 17. Recommended Component Structure

``` text
AppShell

Sidebar

TopHeader

StatusCards

TodayTasks

SystemHealth

PipelineBoard

AlertsPanel

RecentActivity

WorkbenchActions

ProjectCards

AgentCards

JsonViewer
```

------------------------------------------------------------------------

# 18. Data Contract

Preferred snapshot:

``` text
/artifacts/m10/home_snapshot.json
```

This becomes the single source of truth consumed by M10.

Fallback:

Mock data.

------------------------------------------------------------------------

# 19. Implementation Roadmap

## Phase 1

Build:

-   Home
-   Today
-   System Health
-   Pipeline
-   Alerts
-   Recent Activity

## Phase 2

Build:

-   Workbench
-   Projects
-   Agents
-   Publishing

## Phase 3

Build:

-   Insights
-   System
-   JSON Viewer
-   Artifact Browser

------------------------------------------------------------------------

# 20. Definition of Done

M10 is complete when:

-   Home contains no raw JSON
-   Sidebar follows workflow
-   Today section exists
-   System Health exists
-   Pipeline Board exists
-   Alerts exist
-   Recent Activity exists
-   Debug tools moved into System
-   Read-only architecture preserved
-   No live API calls
-   No duplicated business logic

------------------------------------------------------------------------

# 21. Final Principle

M10 is not a dashboard.

M10 is the **Operating Center** of Ven Ho OS.

Its responsibility is not to expose the architecture.

Its responsibility is to guide the founder.

The governing design principle is:

> **User → Workflow → Module**

Never:

> **Module → Data → User**
