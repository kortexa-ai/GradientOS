# Agent Scratchpad

Use this file as persistent, repo-local execution memory.

## File Policy

- Current policy: `COMMITTED`
- Rationale:
  - The user explicitly asked for persistent use of scratchpad/devlog skills and visible top-level references.

## How To Use

1. Read latest entries before starting meaningful work.
2. Build a short preflight checklist from recurring mistakes and preferences.
3. Re-read before risky operations (migrations, broad refactors, unfamiliar tooling, destructive commands).
4. Log high-signal learnings immediately during the task.
5. Append one new session entry before handoff.
6. Keep entries concrete, concise, and testable.

## Entry Rules

- Tag operational notes with source: `[self]`, `[user]`, or `[tool]`.
- Prefer facts tied to files, commands, and outcomes.
- Do not log low-signal reminders.

## Retained Lessons

- [user] Prefer implementation over discussion; "do it, do not only explain."
- [user] UI preferences are specific and iterative; keep changes minimal and visual hierarchy clean.
- [tool] Build and lint checks (`npm run build`, `ReadLints`) catch regressions quickly in the web-ui workflow.

## Session Entries

### 2026-02-16 00:14 +11:00 - Sidebar UX refinement and workflow persistence

#### Task Summary

- Adjusted drawer close-button placement and panel framing behavior per user screenshot feedback.
- Kept robot control right-docked and collapsible.
- Added explicit top-level workflow pointers and persistent memory files.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Initial close-button placement still appeared outside the panel because drawer width did not match panel width behavior.
- Detection:
  - User screenshot showed the close icon floating outside the card boundary.
- Fix:
  - Synchronized drawer width to panel scale and repositioned close button offsets.
- Preventive rule:
  - When overlay controls must align with a child card, validate parent width/position assumptions before tweaking z-index/offsets.

#### User Preferences

- New or reinforced preference:
  - Keep close controls on the same line as the panel title area.
  - Remove redundant visual framing (no duplicate outer border effect).
  - Keep robot control aligned on the right and collapsible.
  - Always maintain devlog/scratchpad workflow and keep `.cursor/skills` references visible.
- How it changed execution:
  - Prioritized layout simplification and added top-level workflow references.

#### What Worked

- Pattern/check that worked:
  - Small targeted CSS/class updates in drawer wrapper and deterministic build verification.

#### What Did Not Work

- Failed attempt and why:
  - Width-only tweak without checking `w-full max-w-*` interactions can leave floating controls misaligned.

#### Guardrails For Next Session

- Preflight rule:
  - Read this scratchpad + `DEVLOG.md` first, then align any overlay control to the actual rendered panel width before finalizing.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Confirm visual alignment at multiple viewport sizes after future panel style changes.

### 2026-02-16 00:20 +11:00 - Prevent tab lock from tree sync

#### Task Summary

- Fixed behavior where loading STEP or existing tree selection auto-forced Weld tab.
- Restored manual tab switching while preserving weld/tree selection sync.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Program-tree synchronization effect controlled `activePanel`, unintentionally overriding user tab changes.
- Detection:
  - User reported automatic tab jump to Weld and inability to switch tabs afterward.
- Fix:
  - Removed panel-forcing from tree-sync effect; moved panel-open behavior to explicit tree click handler.
- Preventive rule:
  - Keep sync effects state-specific (selection-to-selection), and keep view-navigation state controlled only by explicit user actions.

#### User Preferences

- New or reinforced preference:
  - Loading a STEP model must not auto-navigate to Weld.
  - User must be able to switch tabs freely at all times.
- How it changed execution:
  - Prioritized decoupling `activePanel` from background sync logic.

#### What Worked

- Pattern/check that worked:
  - Isolating tree sync side effects and validating with build quickly confirmed fix stability.

#### What Did Not Work

- Failed attempt and why:
  - Coupling panel navigation to derived tree focus caused repeated tab override loops.

#### Guardrails For Next Session

- Preflight rule:
  - Before adding `useEffect` state sync, verify it cannot override explicit user UI navigation state.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If new tree node types introduce `openPanel`, ensure only direct selection handlers apply that field.
