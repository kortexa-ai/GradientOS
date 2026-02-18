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

### 2026-02-16 21:51 +11:00 - Multi-select edge flicker and panel-control placement

#### Task Summary

- Moved STEP Import `Reset Pose` control to the bottom of the panel.
- Fixed tree/weld synchronization conflict that could cause active segment flicker when two edges were selected.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Bidirectional sync lacked interaction-source gating, allowing tree and weld selection effects to fight each other.
- Detection:
  - User reported flickering behavior when two lines/segments were selected.
- Fix:
  - Added `panelSelectionOriginRef` and only applied tree->weld active-segment sync when selection originated from tree clicks.
- Preventive rule:
  - For bidirectional UI sync, always track source-of-truth per interaction to prevent feedback loops.

#### User Preferences

- New or reinforced preference:
  - Keep key panel actions (e.g. `Reset Pose`) at intuitive positions near related transform controls.
- How it changed execution:
  - Repositioned control directly in `StepImportPanel` footer.

#### What Worked

- Pattern/check that worked:
  - Interaction-origin refs are a lightweight, reliable way to stop cross-effect oscillation in React state sync.

#### What Did Not Work

- Failed attempt and why:
  - Pure dependency-based effects without origin markers were insufficient for multi-source selection flows.

#### Guardrails For Next Session

- Preflight rule:
  - When implementing two-way sync between panels/tree/scene, define and enforce a source tag before writing effects.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If GPU-specific flicker remains, replace selected line rendering with a single authoritative overlay layer and suppress base-line rendering for selected edges.

### 2026-02-17 10:32 +11:00 - Enforce automatic scratchpad and devlog context

#### Task Summary

- Added a repo-level Cursor rule to make scratchpad/devlog workflow mandatory for all meaningful tasks.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Relying on optional workflow habits instead of enforcing them through an always-apply project rule.
- Detection:
  - User explicitly requested both loops be automatic in every agent session.
- Fix:
  - Added `.cursor/rules/agent-memory-loops.md` with start/during/end requirements for both files.
  - Updated `.cursor/rules/agent-gated-checklist.md` to require scratchpad/devlog read at Gate 0 and writeback at Gate 7.
- Preventive rule:
  - When the user asks for persistent agent behavior, encode it in `.cursor/rules` instead of relying on ad-hoc reminders.

#### User Preferences

- New or reinforced preference:
  - Always use and update both `AGENT_SCRATCHPAD.md` and `DEVLOG.md`.
- How it changed execution:
  - Implemented an always-apply rule and logged this change in both memory files immediately.

#### What Worked

- Pattern/check that worked:
  - Converting skill guidance into a concise always-apply rule provides durable enforcement across sessions.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this task.

#### Guardrails For Next Session

- Preflight rule:
  - Before substantial edits, read `AGENT_SCRATCHPAD.md` + `DEVLOG.md`; before handoff, append both.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Existing active sessions may need a fresh prompt/turn to fully align with newly added rule text.

### 2026-02-17 10:45 +11:00 - Explicit skill-to-file pointers for memory loops

#### Task Summary

- Added explicit references linking each memory file to its owning skill and template.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Previous rule text enforced the workflow but did not explicitly map the exact skill files and templates.
- Detection:
  - User asked to point to the specific skills and files.
- Fix:
  - Updated `.cursor/rules/agent-memory-loops.md` with required skill/template/file mapping.
  - Updated `QUICK_START.md` workflow pointers with direct skill-to-file paths.
- Preventive rule:
  - When documenting persistent behavior from skills, always include concrete source-skill paths and destination files.

#### User Preferences

- New or reinforced preference:
  - Keep explicit references to the exact skills and the files they manage.
- How it changed execution:
  - Added direct path mapping in both the always-apply rule and top-level quick-start docs.

#### What Worked

- Pattern/check that worked:
  - Short path mapping bullets remove ambiguity and make compliance auditable in one glance.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this task.

#### Guardrails For Next Session

- Preflight rule:
  - If a process is skill-driven, verify docs include both `SKILL.md` path and target file path.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - None identified for this documentation update.

### 2026-02-17 00:12 +11:00 - Duplicate skill mapping across all always-on rules

#### Task Summary

- Added explicit scratchpad/devlog skill-to-file mapping blocks to all `alwaysApply: true` rule files.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Mapping existed in only part of the rule set, leaving room for inconsistent context anchoring.
- Detection:
  - User explicitly requested this be added to the rules (plural) so it is always in context.
- Fix:
  - Updated `.cursor/rules/agent-gated-checklist.md`, `.cursor/rules/agent-ambiguity-triggers.md`, `.cursor/rules/agent-subagents.md`, and `.cursor/rules/rtos-ethercat-readme.md` with the same required mapping block.
- Preventive rule:
  - For mandatory context anchors, mirror the same source-of-truth mapping across every `alwaysApply` rule file.

#### User Preferences

- New or reinforced preference:
  - Keep scratchpad/devlog skill links explicitly present across the entire always-on rule surface.
- How it changed execution:
  - Applied a repeated mapping section to each always-apply rule, not just memory-focused docs.

#### What Worked

- Pattern/check that worked:
  - Uniform, copy-identical mapping sections reduce ambiguity and audit time.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this task.

#### Guardrails For Next Session

- Preflight rule:
  - When user says "always in context," verify all `alwaysApply` rules carry the same mandatory pointers.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If new `alwaysApply` rules are added later, they must include the same mapping block.

### 2026-02-17 00:41 +11:00 - Weld Motion + Tree UX delivery and checklist compliance fix

#### Task Summary

- Delivered full requested pass:
  - compact + chronological Program Tree UX
  - weld section planning with transitions
  - torch-angle controls (UI -> API -> planner)
  - planner robustness and diagnostics.
- Closed workflow loop by writing explicit session entries to both `DEVLOG.md` and `AGENT_SCRATCHPAD.md`.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Completed feature implementation but initially missed the two trailing checklist items (memory writeback + future backlog todo creation).
- Detection:
  - User called it out directly ("last 2 on the list ... didn't touch").
- Fix:
  - Immediately added memory-loop writeback entry to both files and created explicit future backlog tracking todo.
- Preventive rule:
  - Before handoff, verify every visible checklist/todo item (including process tasks) is handled, not just code tasks.

#### User Preferences

- New or reinforced preference:
  - Process tasks are first-class requirements; do not skip memory/devlog updates when explicitly listed.
  - Strong preference for direct execution over explanation-only updates.
- How it changed execution:
  - Added explicit final pass for process compliance and backlog traceability in the same turn.

#### What Worked

- Pattern/check that worked:
  - Section-based weld planning model (`weld` vs `transition`) made it practical to implement contiguous weld continuation and safe-lift transitions without a full collision engine.
  - Runtime fallback from torch-angle orientation solve to orientation-lock avoided planner hard-fails.

#### What Did Not Work

- Failed attempt and why:
  - Strict torch-angle orientation path can be IK-infeasible on some geometries; required fallback behavior to keep planning usable.

#### Guardrails For Next Session

- Preflight rule:
  - Track implementation to-dos and workflow to-dos separately, and do a final checklist sweep that includes both.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Full collision-aware transition planner is still pending and should replace heuristic safe-lift logic in a future phase.

### 2026-02-17 00:47 +11:00 - Viewport-clamped sidebar drawer

#### Task Summary

- Fixed menu overflow issue where left drawer panels could exceed the viewport height.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Drawer container allowed unconstrained vertical growth when panel content (especially Weld panel with long waypoint lists) got tall.
- Detection:
  - User screenshot and explicit feedback: "can't let menus grow larger than window size."
- Fix:
  - Added viewport max-height and internal scroll behavior in `web-ui/src/components/SidebarDrawer.tsx`.
- Preventive rule:
  - Any absolute overlay panel should define a viewport max-height and internal scrolling before adding content-heavy sections.

#### User Preferences

- New or reinforced preference:
  - Keep side menus fully contained within the visible window.
- How it changed execution:
  - Prioritized layout containment fix over feature additions.

#### What Worked

- Pattern/check that worked:
  - Applying max-height at the shared drawer wrapper fixed all drawer-hosted panels at once.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this task.

#### Guardrails For Next Session

- Preflight rule:
  - For UI overlays, validate worst-case content height against viewport before handoff.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If non-drawer floating panels are expanded in future, they may need the same containment pattern.

### 2026-02-17 00:50 +11:00 - Drawer header overlap guard band

#### Task Summary

- Fixed a visual overlap where the drawer close button covered panel header controls on the right side.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - The close button was absolutely positioned over content with insufficient reserved horizontal space.
- Detection:
  - User reported overlap and shared screenshot showing Weld badge collision near the close icon.
- Fix:
  - Added a right-side content guard band in `web-ui/src/components/SidebarDrawer.tsx` by increasing inner wrapper padding to `pr-10`.
- Preventive rule:
  - Any persistent overlay control (close/help/action) must reserve explicit layout space rather than relying on visual luck.

#### User Preferences

- New or reinforced preference:
  - UI controls must never overlap; title/header actions must remain readable and clickable.
- How it changed execution:
  - Prioritized spacing/layout correction over adding new interactions.

#### What Worked

- Pattern/check that worked:
  - Shared-container spacing fixes in one wrapper corrected multiple panel variants without touching feature-specific components.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this task.

#### Guardrails For Next Session

- Preflight rule:
  - For absolute-positioned controls, verify both vertical and horizontal guard space at smallest supported drawer width.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If header content density increases (more badges/buttons), migrate to an explicit shared drawer header row to keep spacing deterministic.

### 2026-02-17 00:53 +11:00 - Escalation handoff note for next model

#### Task Summary

- Added a high-priority takeover TODO in `QUICK_START.md` so a new model can continue unresolved UI overlap cleanup immediately.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Prior spacing fix did not meet user quality expectations.
- Detection:
  - Direct user feedback: overlap still unacceptable.
- Fix:
  - Wrote explicit handoff requirements + acceptance criteria at the top of `QUICK_START.md` to avoid context loss across model handoff.
- Preventive rule:
  - When user asks for takeover, document exact failure mode + required end-state in a top-level onboarding doc.

#### User Preferences

- New or reinforced preference:
  - Do not paper over visual defects; require robust layout fixes.
- How it changed execution:
  - Prioritized cross-model continuity and clear ownership transfer instructions.

#### What Worked

- Pattern/check that worked:
  - A concrete handoff checklist in `QUICK_START.md` gives immediate actionability for the next model.

#### What Did Not Work

- Failed attempt and why:
  - Padding-only overlap mitigation was not perceived as a complete fix.

#### Guardrails For Next Session

- Preflight rule:
  - For overlay/header defects, prefer structural layout changes (shared header row) over spacing-only adjustments.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - The actual UI fix is still pending; this entry only captures handoff context.

### 2026-02-17 19:27 +11:00 - Shared drawer header row implementation

#### Task Summary

- Implemented structural drawer-header fix from `QUICK_START.md` to prevent overlap between header content and close control.
- Moved weld title/badge into shared drawer header surface and removed duplicate in-panel title rows.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Earlier workaround depended on right-side padding (`pr-10`) while keeping close action absolutely positioned.
- Detection:
  - User screenshot + takeover note confirmed overlap remained unacceptable in real weld-header content.
- Fix:
  - Replaced overlay close action with a dedicated `SidebarDrawer` header row (`headerContent` + close button) so layout guarantees non-overlap.
- Preventive rule:
  - For any dismiss/action control near dynamic header content, use structural row layout with flex constraints (`min-w-0`, `shrink-0`) instead of padding buffers.

#### User Preferences

- New or reinforced preference:
  - UI fixes should be robust by structure, not spacing hacks.
  - "Implement, do not only explain" remains the default execution style.
- How it changed execution:
  - Applied direct component refactor and validation in the same turn instead of proposing-only guidance.

#### What Worked

- Pattern/check that worked:
  - Centralizing header composition in `SidebarDrawer` allowed one fix to cover all panel types while keeping panel body logic unchanged.
  - Immediate `npm run build` + `ReadLints` checks caught regressions quickly.

#### What Did Not Work

- Failed attempt and why:
  - Keeping titles in both drawer header and panel cards created duplicated heading surfaces; removed duplicated panel titles where appropriate.

#### Guardrails For Next Session

- Preflight rule:
  - If a shared container now owns a title area, remove duplicate in-panel titles unless they carry unique controls.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Perform visual verification at narrow window widths to confirm spacing and interaction feel for all drawer panels in live UI.

### 2026-02-17 20:34 +11:00 - Drawer bottom inset alignment + AGENTS skill catalog refresh

#### Task Summary

- Corrected left drawer vertical sizing so it keeps a bottom inset instead of visually running to the edge.
- Updated `AGENTS.md` to reflect the rename from `QUICK_START.md` and documented all installed skills with usage triggers.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Previous drawer height model used viewport-based max-height math, which could feel mismatched with sibling overlays in a header+main layout.
- Detection:
  - User screenshot highlighted asymmetry between the left drawer and right robot-control panel bottom spacing.
- Fix:
  - Refactored drawer container to inset-based vertical layout (`inset-y-6`) with `flex` + `min-h-0`; retained scroll using `flex-1 overflow-y-auto`.
- Preventive rule:
  - For overlay alignment across a shared surface, prefer consistent positional insets (`top/bottom`) over independent max-height calculations.

#### User Preferences

- New or reinforced preference:
  - Visually related overlays should have matching baseline/inset behavior.
  - Agent docs must stay current when top-level onboarding files are renamed.
  - Design-oriented skill usage should be explicit and discoverable.
- How it changed execution:
  - Applied layout fix first, then codified full skill relevance in `AGENTS.md`.

#### What Worked

- Pattern/check that worked:
  - `inset-y-*` + `flex-1` scroll gives deterministic alignment while preserving long-content usability.
  - Using `frontend-design` guidance for implementation direction and `web-design-guidelines` guidance for post-change review framing kept UI decisions intentional.

#### What Did Not Work

- Failed attempt and why:
  - Treating drawer max-height independent of main container created perceived edge contact even when scroll technically worked.

#### Guardrails For Next Session

- Preflight rule:
  - If two overlay panels are expected to align, compare both vertical anchors (`top`, `bottom`, internal scroll shell) before finalizing styles.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Confirm final visual balance during live interaction at very small window heights and high content density.

### 2026-02-17 20:41 +11:00 - Themed drawer scrollbar styling

#### Task Summary

- Replaced default browser-style drawer scrollbar with a custom theme-matched scrollbar.
- Kept behavior cross-browser by styling both Firefox and WebKit engines.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Previously left the primary drawer scroller unstyled, which looked inconsistent with the polished panel visual design.
- Detection:
  - User feedback with screenshot: "scrollbar is ugly" and requested UI-consistent styling.
- Fix:
  - Added reusable `.gradient-scrollbar` utility in `web-ui/src/index.css` and applied it to the drawer scroll shell in `SidebarDrawer.tsx`.
- Preventive rule:
  - Any prominent always-visible scrollbar in core UI panels should receive explicit theme styling and not rely on OS defaults.

#### User Preferences

- New or reinforced preference:
  - Styling details (including scrollbars) must match the overall interface quality bar.
- How it changed execution:
  - Prioritized direct visual polish in production code with immediate build/lint validation.

#### What Worked

- Pattern/check that worked:
  - Utility-class approach (`gradient-scrollbar`) makes it easy to reuse consistent scrollbar styling across other scrollable panel sections.
  - Combining Firefox and WebKit declarations ensures broad browser coverage.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this change.

#### Guardrails For Next Session

- Preflight rule:
  - For UI polish requests, inspect for native browser defaults (scrollbars, focus rings, select arrows) and theme them where they are visually dominant.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If users request thicker or subtler scrollbar contrast, tune width/color alpha in `.gradient-scrollbar` rather than duplicating new classes.

### 2026-02-17 20:49 +11:00 - Scrollbar integrated into rounded drawer shell

#### Task Summary

- Integrated header and scroll body into a single drawer shell so the scrollbar appears inside the panel.
- Ensured rounded bottom corners remain visible regardless of scroll position.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Scroll region still sat outside the main framed shell, making the scrollbar appear detached and corners feel inconsistent.
- Detection:
  - User screenshot highlighted scrollbar placement and requested persistent rounded bottom corners while scrolling.
- Fix:
  - Reworked `SidebarDrawer` to a single `rounded-xl overflow-hidden` container with internal header and body scroller.
- Preventive rule:
  - If users ask for persistent corner shape during scrolling, clipping must happen at the outermost rounded container.

#### User Preferences

- New or reinforced preference:
  - Scrollbar should feel like part of the panel, not adjacent to it.
  - Rounded geometry should remain stable at all scroll offsets.
- How it changed execution:
  - Prioritized container hierarchy/layout over color-only styling tweaks.

#### What Worked

- Pattern/check that worked:
  - One-shell layout with `border-b` header divider gives cleaner structure and deterministic corner clipping.

#### What Did Not Work

- Failed attempt and why:
  - Styling the scrollbar alone without container clipping did not fully solve the visual integration request.

#### Guardrails For Next Session

- Preflight rule:
  - For any scrollable card/panel, confirm the scroll container is nested inside the same rounded element that defines the visual frame.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Optional future polish: reduce nested card framing inside drawer bodies if a flatter visual style is desired.

### 2026-02-17 21:28 +11:00 - Weld typography consistency normalization

#### Task Summary

- Applied a consistent font-size system to the Weld panel (labels, metadata, section headings, inputs, and action text).
- Kept CTA emphasis while reducing random micro-size jumps in the rest of the panel.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Weld UI accumulated mixed ad-hoc text sizes (`text-xs`, `text-[11px]`, `text-[10px]`) without shared typography tokens.
- Detection:
  - User requested consistent styling/sizing and screenshot showed uneven typography rhythm.
- Fix:
  - Added shared weld typography class constants in `App.tsx` and refactored key Weld panel elements to use them.
- Preventive rule:
  - For dense forms, define reusable typographic tokens first, then apply them consistently instead of per-control one-off sizing.

#### User Preferences

- New or reinforced preference:
  - Typography should feel intentionally consistent, not piecemeal.
- How it changed execution:
  - Prioritized text hierarchy cleanup (label/meta/control consistency) immediately after structural layout fixes.

#### What Worked

- Pattern/check that worked:
  - Local constants for panel typography made broad consistency changes safer and easier to review.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this update.

#### Guardrails For Next Session

- Preflight rule:
  - When touching any large panel, run a quick typography pass to ensure no unnecessary size variants remain.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - STEP and Trajectory panels may still contain independent typography choices and can be normalized in a dedicated follow-up.

### 2026-02-17 21:31 +11:00 - Text hierarchy correction for section title vs field label

#### Task Summary

- Adjusted typography hierarchy so `Weld Program` (section title) and `Program Name` (field label) are visually distinct.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Initial typography normalization still left section title and label weights too close, reading as both bold in practice.
- Detection:
  - User feedback called out both lines appearing bold despite hierarchy intent.
- Fix:
  - Set `WELD_LABEL_CLASS` to normal weight and strengthened `WELD_SECTION_TITLE_CLASS` size/contrast for clearer hierarchy.
- Preventive rule:
  - After typographic refactors, verify key adjacent text pairs (section title vs label) in rendered UI, not just by class names.

#### User Preferences

- New or reinforced preference:
  - Visual hierarchy should be obvious; labels should not compete with section headings.
- How it changed execution:
  - Applied immediate token-level correction instead of adding more one-off local class overrides.

#### What Worked

- Pattern/check that worked:
  - Centralized typography constants enabled a quick, low-risk hierarchy adjustment.

#### What Did Not Work

- Failed attempt and why:
  - Equalized sizing pass alone did not guarantee perceived hierarchy when both styles still had elevated weight.

#### Guardrails For Next Session

- Preflight rule:
  - For dense forms, reserve stronger weight/color for section titles and keep field labels at regular weight unless emphasis is intentional.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Consider applying the same heading-vs-label hierarchy tokens to STEP and Trajectory drawers for full consistency.

### 2026-02-17 21:34 +11:00 - Cross-panel typography alignment + living design doc

#### Task Summary

- Extended typography consistency work from Weld to STEP and Trajectory panels.
- Added `web-ui/design.md` as the living design-system document and referenced it from `AGENTS.md`.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Typography tokenization was initially panel-local (`WELD_*`) and not clearly positioned as a shared drawer system.
- Detection:
  - User approved extending hierarchy consistency across all drawer tabs and requested a persistent living design doc.
- Fix:
  - Introduced shared `DRAWER_*` tokens in `App.tsx` and aligned STEP/Trajectory class usage with those tokens.
  - Created `web-ui/design.md` with rules/checklist and linked it from `AGENTS.md`.
- Preventive rule:
  - When UI consistency request spans multiple panels, establish or update a repo-local design source-of-truth before further styling changes.

#### User Preferences

- New or reinforced preference:
  - Consistency should be systematic and documented, not just fixed one screen at a time.
- How it changed execution:
  - Combined implementation changes with living documentation in the same turn.

#### What Worked

- Pattern/check that worked:
  - Shared token strategy (`DRAWER_*`) allowed quick normalization without major component rewrites.
  - A living doc with checklist creates durable guardrails for future UI edits.

#### What Did Not Work

- Failed attempt and why:
  - N/A for this update.

#### Guardrails For Next Session

- Preflight rule:
  - Before editing drawer panel styles, read `web-ui/design.md` and use existing `DRAWER_*` tokens unless intentionally evolving the design system.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Global typography outside drawer panels still may not fully match the new panel system and can be standardized later.

### 2026-02-17 21:43 +11:00 - Hard requirement language for memory-loop completion

#### Task Summary

- Strengthened `AGENTS.md` so updating both `DEVLOG.md` and `AGENT_SCRATCHPAD.md` is explicitly non-optional.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Existing wording listed both files but was not strong enough to prevent potential omission.
- Detection:
  - User explicitly requested stronger emphasis that these tasks must never be left undone.
- Fix:
  - Added MUST language on both workflow bullets and a non-negotiable blocker rule in `AGENTS.md`.
- Preventive rule:
  - If user says "every time", encode it with explicit "MUST" + "blocker" phrasing in the top-level onboarding doc.

#### User Preferences

- New or reinforced preference:
  - Memory-loop updates are mandatory on every meaningful task with zero exceptions.
- How it changed execution:
  - Immediately hardened policy text in `AGENTS.md` and logged the change in both memory files.

#### What Worked

- Pattern/check that worked:
  - Converting soft guidance into explicit completion criteria reduces ambiguity and missed process steps.

#### What Did Not Work

- Failed attempt and why:
  - Soft descriptive wording ("maintain these files") did not clearly communicate non-negotiable enforcement.

#### Guardrails For Next Session

- Preflight rule:
  - Treat absent updates in either `DEVLOG.md` or `AGENT_SCRATCHPAD.md` as a stop condition before final handoff.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - None for this doc-policy reinforcement; now explicitly codified.

### 2026-02-17 21:46 +11:00 - Remove nested drawer shell for more usable width

#### Task Summary

- Removed the extra inner full-card shell from drawer panel content to eliminate the double-layer frame.
- Increased usable content room in the drawer without changing the outer shell behavior.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Panel content still had a nested full-shell wrapper (rounded/border/bg/shadow) inside the drawer shell, causing visual duplication.
- Detection:
  - User screenshot highlighted unnecessary double layer and requested more content room.
- Fix:
  - Removed root shell classes from drawer panel roots in `App.tsx` and reduced shelling in `TelemetryCharts.tsx`.
  - Added a permanent "no nested outer shell" rule to `web-ui/design.md`.
- Preventive rule:
  - In drawer UIs, keep one primary shell only; use section cards for grouping, not another full wrapper.

#### User Preferences

- New or reinforced preference:
  - Avoid double framing; prioritize cleaner visual hierarchy and usable space.
- How it changed execution:
  - Applied structural class removal instead of spacing-only patching.

#### What Worked

- Pattern/check that worked:
  - Removing duplicated shell classes immediately reduced visual noise and reclaimed width.

#### What Did Not Work

- Failed attempt and why:
  - Prior refinements (scrollbar, typography) improved polish but did not remove the underlying duplicated-shell structure.

#### Guardrails For Next Session

- Preflight rule:
  - Before finalizing drawer visuals, verify only one full-shell container exists in the panel stack.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Fine-tune section card spacing if certain panel states appear too sparse after shell removal.

### 2026-02-17 21:50 +11:00 - Adaptive drawer height + wider telemetry panel

#### Task Summary

- Changed drawer sizing behavior so short-content panels no longer stretch to full-height.
- Added a wider drawer width variant for telemetry/charts to avoid horizontal overflow.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Forcing drawer to `inset-y` full height made sparse panels (STEP/Trajectory/Telemetry idle) look mostly empty.
- Detection:
  - User screenshots showed excessive empty vertical space and horizontal scrollbar in charts panel.
- Fix:
  - Switched drawer to content-driven height with viewport max-height cap and internal scroll.
  - Added panel-specific width prop and set telemetry to wider width.
  - Added `overflow-x-hidden` in drawer body to suppress unintended sideways scroll.
- Preventive rule:
  - Drawer height should be content-first with max-height constraints; reserve full-height overlays only for intentionally immersive panels.

#### User Preferences

- New or reinforced preference:
  - Keep max-height safety, but avoid unnecessary empty space in light-content tabs.
  - Charts panel should prioritize readable layout over strict shared-width parity.
- How it changed execution:
  - Implemented adaptive layout plus targeted width override rather than a single global sizing rule.

#### What Worked

- Pattern/check that worked:
  - Width variant via prop (`widthClassName`) cleanly supports per-panel layout needs without duplicating drawer component logic.

#### What Did Not Work

- Failed attempt and why:
  - Earlier one-size full-height behavior suited long Weld content but degraded sparse tabs.

#### Guardrails For Next Session

- Preflight rule:
  - Validate each tab in both sparse and dense states before finalizing shared container sizing.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If telemetry charts add more columns/cards, add responsive width tiers rather than reintroducing horizontal scroll.

### 2026-02-17 22:10 +11:00 - Weld drawer baseline + tooltip clipping regression fix

#### Task Summary

- Fixed Weld drawer vertical sizing so its bottom baseline stays aligned with Robot Control.
- Fixed angle-help tooltip clipping by moving it out of the scroll container into a fixed portal overlay.
- Codified these constraints in `web-ui/design.md`.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Drawer sizing logic shifted between content-driven and max-height variants, causing bottom misalignment and visible clipping near footer-adjacent controls.
  - Tooltip was rendered inside an overflowed panel region, so it got clipped/cut off.
- Detection:
  - User screenshots clearly showed the panel extending into terminal/footer region and tooltip content cut off by panel bounds.
- Fix:
  - Anchored drawer with explicit `top-6` + `bottom-6` and `h-full` shell.
  - Rendered angle explainer tooltip via `createPortal(document.body)` with fixed positioning and viewport clamping.
  - Set tooltip to open on the right by default with left fallback only when viewport space is constrained.
- Preventive rule:
  - Never place explainer popovers inside scrolling/clipped containers; use portal overlays for any panel-help UI.
  - For consistency-critical overlays, align by shared anchor insets rather than mixing content-height and max-height modes.

#### User Preferences

- New or reinforced preference:
  - Strong preference for consistent panel baselines and no clipped UI.
  - When regressions are reported with screenshots, prioritize direct fixes over exploratory redesign.
- How it changed execution:
  - Moved from incremental class tweaks to hard layout anchoring + portalized overlay behavior.

#### What Worked

- Pattern/check that worked:
  - Using `absolute top-6 bottom-6` + internal scroll gives stable, predictable panel bounds across dense Weld content.
  - Portal + fixed positioning immediately removed tooltip clipping from drawer overflow constraints.

#### What Did Not Work

- Failed attempt and why:
  - Intermediate max-height-only tuning was not robust; it still produced inconsistent bottoms in real viewport states.

#### Guardrails For Next Session

- Preflight rule:
  - For all floating panels, verify top and bottom anchors against adjacent UI baselines before finalizing.
  - For tooltips/popovers inside drawers, require portal rendering and viewport-bound checks by default.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If additional help popovers are added, they must reuse the same portal + clamp pattern to avoid repeat clipping regressions.

### 2026-02-17 22:24 +11:00 - Weld end-action semantics correction

#### Task Summary

- Corrected weld post-action behavior so `return_to_start` means return to trajectory start/home-start pose (not weld start).
- Added new post-action mode `lift` for a small vertical retract from weld end.
- Synced backend planner semantics, API normalization, and UI enum/options.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Existing `return_to_start` behavior returned to the first weld point, which is semantically wrong for full-trajectory flow.
- Detection:
  - User provided explicit behavior definition + annotated image showing desired home-start target.
- Fix:
  - Removed frontend section-level weld-start return insertion.
  - Implemented backend post-action planning in `command_api.py`:
    - `return_to_start` now routes from weld end back to trajectory start pose (captured at planning start), using a lifted transition.
    - `lift` now performs a vertical retract by transition clearance.
  - Added `lift` normalization in `main.py` and UI type/select handling in `App.tsx`.
- Preventive rule:
  - End-action semantics must be owned by backend planner state (which has true start pose), not pre-baked by frontend geometry assumptions.

#### User Preferences

- New or reinforced preference:
  - "Return to start" must always refer to trajectory/program start, not local weld segment start.
  - Add practical post-weld finishing action(s) like lift for safer motion behavior.
- How it changed execution:
  - Prioritized behavior semantics over UI-only labeling and implemented planner-level logic.

#### What Worked

- Pattern/check that worked:
  - Centralizing end-action logic in backend keeps preview/execution behavior consistent and source-of-truth aligned.

#### What Did Not Work

- Failed attempt and why:
  - Previous frontend-only return transition generation could not represent trajectory start correctly because it lacked planner start-pose context.

#### Guardrails For Next Session

- Preflight rule:
  - For any motion semantic label (`return`, `home`, `safe`), verify mapping against planner/control definitions before shipping UI text.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If a dedicated configurable "home" waypoint is introduced later, `return_to_start` should explicitly choose between recorded trajectory start vs configured home target.

### 2026-02-17 22:57 +11:00 - Weld-program load must clear stale preview state

#### Task Summary

- Fixed stale path rendering when loading saved weld programs that do not include a planned trajectory payload.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Loading `test_0` could leave the previous preview path visible because restore logic only set new preview when present, but did not clear old preview when missing.
- Detection:
  - User reported loaded program retained prior plan/path visuals.
- Fix:
  - In weld-program restore path, explicitly clear `previewPlan` + `plannerPoints` when `pendingWeldProgramRestore.previewPlan` is null.
  - Also clear `previewPlan` + `plannerPoints` immediately after successful program payload validation so stale geometry is removed during restore.
- Preventive rule:
  - Any optional payload restore must include explicit "else clear" handling for stateful visuals.

#### User Preferences

- New or reinforced preference:
  - Loading a saved program must never retain stale path overlays from previous sessions/plans.
- How it changed execution:
  - Prioritized deterministic state reset behavior over preserving transient UI visuals between loads.

#### What Worked

- Pattern/check that worked:
  - Clearing both source states (`previewPlan` and `plannerPoints`) ensures visual path fallback logic cannot display old geometry.

#### What Did Not Work

- Failed attempt and why:
  - Implicit state replacement only on "truthy new plan" left stale values alive in null-plan restore cases.

#### Guardrails For Next Session

- Preflight rule:
  - For every restore/load flow, enumerate each visual state and handle both "present" and "absent" payload branches explicitly.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If additional derived visual states are added (e.g., cached highlight ranges), ensure they are reset alongside preview state on load.

### 2026-02-17 23:29 +11:00 - Weld-run visual flicker spike filtering

#### Task Summary

- Added runtime telemetry filtering to prevent single-frame snap-back/flicker artifacts in arm visualization during weld execution.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Visualization occasionally jumped to a stale weld-start-like pose for one frame while actual motion continued, creating star-like flicker trails.
- Detection:
  - User screenshot showed repeated visual spokes from a fixed point during weld run.
- Fix:
  - Added telemetry guards in `web-ui/src/App.tsx`:
    - drop out-of-order packets using source telemetry timestamp (`t`),
    - reject implausible one-frame joint spikes (`maxJump > 0.8 rad` within `<=0.25s`) likely caused by stale/outlier packets.
  - Reset telemetry filter refs on disconnect.
- Preventive rule:
  - Treat UI pose stream as potentially noisy/reordered; enforce monotonic timestamp acceptance and outlier rejection before rendering.

#### User Preferences

- New or reinforced preference:
  - Weld execution visualization must remain stable and trustworthy; no transient “teleport” artifacts.
- How it changed execution:
  - Added ingestion-layer robustness rather than only tuning rendering interpolation.

#### What Worked

- Pattern/check that worked:
  - Filtering at message-ingest stage avoids contaminating both immediate and smoothed pose updates.

#### What Did Not Work

- Failed attempt and why:
  - Relying on smoothing alone cannot prevent stale packet flashes because stale targets still get applied instantly.

#### Guardrails For Next Session

- Preflight rule:
  - For realtime robot UI streams, always define packet-order and spike-handling policy explicitly.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If a second legitimate telemetry source is intentionally mixed in future, add explicit source tagging/selection instead of relying on timestamp-only arbitration.

### 2026-02-18 00:08 +11:00 - Weld program run gating + start-from-current execution

#### Task Summary

- Fixed inability to run loaded weld programs when draft restoration is missing/invalid but a runnable preview trajectory exists.
- Enforced run-time re-planning from current robot state for weld preview execution.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Run button in Weld panel was gated on `draft` existence instead of actual runnable preview presence, blocking execution for some loaded programs.
  - Weld preview run path used cached planning (`use_cache: true`), which can execute stale joint paths not guaranteed to reflect current robot state.
- Detection:
  - User loaded `test_02` and observed run action unavailable despite loaded trajectory/waypoints.
- Fix:
  - Updated Weld panel run gating to use `canRunPreview` (`Boolean(previewPlan?.name)`) rather than `draft`.
  - Switched preview run request to `use_cache: false` so backend re-plans from current state, naturally including current->start motion.
- Preventive rule:
  - UI action enablement must track actual execution prerequisites (runnable plan), not adjacent editor state (draft availability).

#### User Preferences

- New or reinforced preference:
  - Loaded weld programs should be runnable even when edge-edit context is unavailable.
  - Execution should start from current robot pose with an explicit approach to program start.
- How it changed execution:
  - Prioritized run-time correctness and operability over cache-first speed.

#### What Worked

- Pattern/check that worked:
  - Decoupling run enablement from `draft` immediately restores operability for loaded plans.
  - Re-plan from current state guarantees start approach behavior without additional special-case injection.

#### What Did Not Work

- Failed attempt and why:
  - Previous cache-first preview execution assumed planning-time and run-time robot state equivalence.

#### Guardrails For Next Session

- Preflight rule:
  - For any "Run" control, verify its disabled condition maps exactly to runtime required data, then confirm loaded-from-file flows satisfy that condition.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If run latency becomes noticeable due to re-planning, introduce an explicit "replan-on-run" toggle with clear UX semantics.

### 2026-02-18 00:18 +11:00 - Panel-aware drawer height mode (keep weld full, un-stretch others)

#### Task Summary

- Fixed the drawer height regression where STEP / Trajectory / Telemetry looked stretched to the bottom with large empty space.
- Preserved Weld Planning as full-height because that dense workflow benefits from a stable full overlay band.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - A global full-height drawer shell (`h-full` inside `top-6 bottom-6`) was applied to all tabs, which regressed sparse panels into visibly stretched empty containers.
- Detection:
  - User screenshots showed STEP / Trajectory / Live Charts extending to the bottom while Weld looked acceptable.
- Fix:
  - Added `heightMode` to `SidebarDrawer`:
    - `full` for Weld (`h-full`),
    - `content` for STEP / Trajectory / Telemetry (`max-h-full` with internal scrolling preserved).
  - Kept common overlay lane (`top-6 bottom-6`) and moved pointer-event handling to panel shell so empty transparent lane area does not block workspace interaction.
  - Updated `web-ui/design.md` rules to codify mixed-mode behavior.
- Preventive rule:
  - Do not apply one global drawer height strategy across panels with different content density; explicitly model panel height intent (content-fit vs full-height).

#### User Preferences

- New or reinforced preference:
  - Weld panel baseline/behavior is acceptable and should remain unchanged when fixing other tabs.
  - Sparse panels should not appear stretched to the viewport bottom.
- How it changed execution:
  - Used panel-specific height mode instead of another global class toggle.

#### What Worked

- Pattern/check that worked:
  - Shared wrapper + per-panel shell height mode is a low-risk way to preserve weld behavior while fixing sparse tabs.
  - Keeping internal scroll inside the same shell retained dense-content safety without reintroducing clipping.

#### What Did Not Work

- Failed attempt and why:
  - Previous "all panels full-height" rule solved weld alignment but caused immediate UX regressions for sparse tabs.

#### Guardrails For Next Session

- Preflight rule:
  - For shared drawer/container refactors, validate all tabs in both sparse and dense states before finalizing.
  - If one panel is intentionally different, encode that in props rather than ad-hoc class forks.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Confirm in live UI that click-through around non-full-height drawer shell feels natural at narrow and wide viewport sizes.

### 2026-02-18 01:13 +11:00 - Local repo skill installation into Codex home

#### Task Summary

- Installed all local skills from `.cursor/skills` into `C:\Users\angus\.codex\skills`.
- Verified destination skill set matches source local skills and complies with AGENTS workflow logging requirements.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Initial assumption from AGENTS list suggested `.cursor/skills-cursor` might also require installation.
- Detection:
  - Repository inspection showed `.cursor` contains only `rules` and `skills`; no `.cursor/skills-cursor` directory exists in this workspace.
- Fix:
  - Scoped installation to `.cursor/skills` folders that contain `SKILL.md`, then audited source-vs-destination skill names.
- Preventive rule:
  - Before bulk install/sync operations, verify referenced directories exist in the current repo snapshot rather than relying only on docs.

#### User Preferences

- New or reinforced preference:
  - Use `AGENTS.md` as startup context and install all repo-local skills when requested.
- How it changed execution:
  - Followed skill-installer guidance for workflow framing, then performed local copy/install for all `.cursor/skills` folders.

#### What Worked

- Pattern/check that worked:
  - Filtering source directories by existence of `SKILL.md` prevents copying non-skill folders.
  - Compare-object audit after install quickly confirms there are no missing skill names.

#### What Did Not Work

- Failed attempt and why:
  - None in this task; install path and audit succeeded on first pass.

#### Guardrails For Next Session

- Preflight rule:
  - For skill installation requests, check both `.cursor/skills` and any AGENTS-referenced paths, but install only paths present in the active workspace.
  - Always finish by updating both `DEVLOG.md` and `AGENT_SCRATCHPAD.md` before handoff.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Codex usually loads skills at startup; restart Codex after installation to ensure all newly installed skills are available.

### 2026-02-18 01:17 +11:00 - Weld preview run should use high-fidelity cache, not sparse endpoint re-plan

#### Task Summary

- Fixed mismatch where weld preview execution diverged from previewed/interpolated path because run used endpoint re-planning.
- Added explicit cache-readiness handling for weld runs and clarified UI wording around editable weld points.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Run path used `/trajectory/run` with `use_cache: false` globally, so weld trajectories were rebuilt from sparse `trajectory.moves` endpoints (few `move_absolute` nodes) instead of using the high-fidelity cached weld path.
- Detection:
  - User screenshot + report showed large gap between expected weld curve and simulated run path, while Program Tree showed only a handful of moves.
- Fix:
  - In `web-ui/src/App.tsx`:
    - added `weldPreviewCacheReady` tracking,
    - made weld runs use `use_cache: true` so backend executes full planned steps cache,
    - when weld cache is stale, auto-refresh preview via `requestWeldPreview` before run,
    - reset cache readiness on clear/disconnect/load transitions.
  - Added UI copy update (`Editable Control Points`) to avoid implying that the list is every interpolated sample.
  - In `web-ui/src/previewUtils.ts`, surfaced path sample count in Program Tree subtitle for better operator visibility.
- Preventive rule:
  - For trajectory systems with both coarse declarative moves and dense cached execution plans, never treat them as interchangeable at run time for weld/high-fidelity workflows.

#### User Preferences

- New or reinforced preference:
  - Displayed/selected weld path and executed weld path must match; no hidden downsampling that changes robot motion.
  - If a mismatch is suspected, prioritize run-time correctness over prior convenience assumptions.
- How it changed execution:
  - Weld run path is now anchored to planned cache validity, with explicit stale-cache refresh.

#### What Worked

- Pattern/check that worked:
  - Keeping non-weld behavior unchanged while branching weld execution policy minimized regression risk.
  - Cache readiness flag cleanly coordinates plan/run state across clear/load/restore flows.

#### What Did Not Work

- Failed attempt and why:
  - Earlier global `use_cache: false` approach improved “start from current pose” semantics but broke weld trajectory fidelity by collapsing to endpoint commands.

#### Guardrails For Next Session

- Preflight rule:
  - If Program Tree move count is far smaller than expected path complexity, verify whether run path uses cached planned steps or endpoint re-planning.
  - For weld runs, treat cache freshness as a first-class precondition.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Program Tree still emphasizes operation-level moves; consider adding a dedicated interpolated-path inspector node if operators need per-sample introspection.

### 2026-02-18 01:28 +11:00 - Exact path visibility: remove planner payload downsampling + tree from path samples

#### Task Summary

- Implemented full-fidelity path visibility so Program Tree can show exact planned path samples instead of trimmed endpoint-derived approximations.
- Removed planner payload downsampling that previously hid intermediate cartesian samples.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - UI path inspection relied on lower-resolution representations (coarse move endpoints and downsampled cartesian payload), creating a trust gap for weld motion verification.
- Detection:
  - User explicitly rejected trimmed output and required exact movement visibility in Program Tree.
- Fix:
  - In `src/gradient_os/arm_controller/command_api.py`, removed `sample_stride` downsampling in `_append_cartesian_samples` so payload carries full planned cartesian samples.
  - In `web-ui/src/previewUtils.ts`, rewired `buildProgramTree` to use `plan.pathPoints` as primary execution tree content:
    - `Exact Path Samples` in grouped mode,
    - `Execution Path (Exact)` in chronological mode,
    - preserved control-point and controller-command groups as secondary views.
- Preventive rule:
  - For robotics inspection UIs, never downsample the authoritative displayed path unless user explicitly opts into a performance mode.

#### User Preferences

- New or reinforced preference:
  - Program Tree must reflect exactly where robot will move; no hidden trimming.
  - Coarse representations are acceptable only as supplemental metadata, not as the primary motion truth.
- How it changed execution:
  - Prioritized operator-trust visibility over payload compactness by default.

#### What Worked

- Pattern/check that worked:
  - Maintaining dual views (exact path + command metadata) preserved debugging utility without compromising motion fidelity visibility.

#### What Did Not Work

- Failed attempt and why:
  - Prior “show move count + path sample count” transparency helped diagnostics but did not satisfy requirement for exact per-sample tree inspection.

#### Guardrails For Next Session

- Preflight rule:
  - If a user asks for exact robot path visibility, ensure both backend payload and frontend tree model are fidelity-preserving end-to-end.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Extremely long paths can create large tree DOMs; prefer virtualization if performance issues appear, not sample trimming.

### 2026-02-18 01:42 +11:00 - Remove approximate segment highlighting when exact mapping is unavailable

#### Task Summary

- Removed approximate weld-segment path highlighting from Program Tree to keep display semantics strictly truthful.
- Preserved command-level tree data only as reference metadata when exact path samples already exist.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Weld segment nodes were still assigning proportional `pathRange` guesses, which could imply false precision even after exact-path sample support was added.
- Detection:
  - User requirement emphasized exact reflection between Program Tree and rendered path; inferred ranges violate that constraint.
- Fix:
  - Removed weld segment `pathRange` inference from `web-ui/src/previewUtils.ts`.
  - Weld segment nodes now only target weld-edge focus (`weldSegmentEdgeId`) without claiming exact path subset.
  - Simplified command grouping so command nodes are clearly labeled as reference when exact path nodes are present.
- Preventive rule:
  - If exact mapping data is not available, do not synthesize approximate range overlays in robotics inspection views.

#### User Preferences

- New or reinforced preference:
  - Program Tree must never imply precision it does not actually have.
  - Exact path truth takes precedence over convenience grouping.
- How it changed execution:
  - Removed inferred path focus fields unless backed by exact sample indices.

#### What Worked

- Pattern/check that worked:
  - Separating "exact execution samples" from "controller command metadata" keeps debugging utility while preserving trust.

#### What Did Not Work

- Failed attempt and why:
  - Earlier proportional segment-range mapping was useful visually but not acceptable for exactness-critical inspection.

#### Guardrails For Next Session

- Preflight rule:
  - Any tree node that highlights path must be backed by explicit deterministic indices from planner output; otherwise omit the highlight mapping.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If per-weld-segment exact highlighting is required later, backend should return section-to-sample index spans as part of planner payload.

### 2026-02-18 01:53 +11:00 - Waypoint editing migrated from Weld drawer into Program Tree

#### Task Summary

- Removed the `Editable Control Points` editor block from Weld drawer UI.
- Implemented Program Tree-native control-point editing flow so waypoint edits are driven from selected tree nodes.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Drawer-local waypoint editor duplicated editing context and conflicted with requirement that tree/path inspection be the source of truth.
- Detection:
  - User explicitly requested complete removal from drawer and routing edits through Program Tree.
- Fix:
  - In `web-ui/src/App.tsx`, removed Weld panel waypoint-edit props/UI and added tree-driven handlers:
    - edit selected control point coordinates,
    - add/remove control point,
    - apply edits via weld replan (or generic point replan for non-weld).
  - In `web-ui/src/components/ProgramFeatureTree.tsx`, added an inline editor section that appears when a `control_point_*` node is selected.
- Preventive rule:
  - Avoid duplicated edit surfaces for the same motion data; keep one primary editing interaction path tied to the inspection model.

#### User Preferences

- New or reinforced preference:
  - Waypoint editing should be centralized in Program Tree, not scattered in panel forms.
  - The path/tree workflow must remain coherent and trustworthy for motion changes.
- How it changed execution:
  - Shifted from drawer-local form controls to selection-driven tree editing.

#### What Worked

- Pattern/check that worked:
  - Reusing existing waypoint state and planner callbacks minimized risk while moving the UI interaction surface.

#### What Did Not Work

- Failed attempt and why:
  - Keeping both drawer and tree editors would continue UX ambiguity and contradict user’s “single source” editing requirement.

#### Guardrails For Next Session

- Preflight rule:
  - When a user requests “drive from X only,” remove parallel controls in other panels rather than trying to keep them synchronized ad hoc.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If users miss discoverability, add small guidance text in Program Tree when no control point is selected.

### 2026-02-18 01:54 +11:00 - Tree node panel focus should follow weld context

#### Task Summary

- Adjusted Program Tree node focus target so selecting control/path nodes in weld plans keeps interaction in weld context.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - After moving editing to Program Tree, control-point nodes still targeted trajectory panel by default, which could feel inconsistent for weld-first workflows.
- Detection:
  - Post-change review of `ProgramNode.focus.openPanel` mapping in `previewUtils.ts`.
- Fix:
  - Set default tree-node focus panel dynamically:
    - weld plan (`trajectory.weld` present) -> `"weld"`,
    - otherwise -> `"trajectory"`.
- Preventive rule:
  - When relocating an editing surface, re-check navigation/focus semantics so node selection context matches the new workflow.

#### User Preferences

- New or reinforced preference:
  - Program Tree should be the primary interaction context for waypoint edits.
- How it changed execution:
  - Ensured tree node selection supports weld-context editing rather than bouncing users to trajectory panel unintentionally.

#### What Worked

- Pattern/check that worked:
  - Deriving a `defaultFocusPanel` once in tree builder avoided repeated branching and kept node focus consistent.

#### What Did Not Work

- Failed attempt and why:
  - Static `openPanel: "trajectory"` across all plans was too rigid once weld editing moved to tree.

#### Guardrails For Next Session

- Preflight rule:
  - Any time node semantics change, validate both data fidelity and panel-navigation behavior together.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - If users want tree selection decoupled from panel switching, add a toggle for “selection-only mode” in settings.

### 2026-02-18 02:00 +11:00 - Preview waypoint marker size reduced to 1mm

#### Task Summary

- Reduced yellow preview waypoint sphere radius to 1mm for less visual clutter in the scene.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Waypoint spheres were oversized for dense weld-path inspection.
- Detection:
  - User requested “much smaller, maybe 1mm radius.”
- Fix:
  - Updated marker mesh radius in `web-ui/src/ArmVisualizer.tsx` from `0.008` to `0.001` meters in the preview path marker block.
- Preventive rule:
  - For dense robot path overlays, keep default markers small enough to avoid obscuring the path geometry.

#### User Preferences

- New or reinforced preference:
  - Preview waypoint markers should be visually subtle and not dominate the path view.
- How it changed execution:
  - Applied a direct geometry-radius change instead of additional styling complexity.

#### What Worked

- Pattern/check that worked:
  - Single-parameter radius change in the marker geometry cleanly addressed the request.

#### What Did Not Work

- Failed attempt and why:
  - None in this task.

#### Guardrails For Next Session

- Preflight rule:
  - When adjusting 3D markers, treat units as meters and validate requested real-world sizing directly in geometry values.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Tiny markers may be hard to pick out at very wide zoom; consider optional user-adjustable marker scale if requested.

### 2026-02-18 02:04 +11:00 - Weld return_to_start must replan from current pre-run pose every run

#### Task Summary

- Fixed critical weld end-action regression where `return_to_start` could resolve to stale/wrong targets (including weld start) if an old preview plan cache was reused.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Weld run path could execute cached plan without guaranteed per-run replan from current robot state, so `return_to_start` target was not always the actual pre-weld run start pose.
- Detection:
  - User reported repeated return to weld start despite selecting `Return to trajectory start`.
- Fix:
  - In `web-ui/src/App.tsx`, updated weld run logic in `handleRunPreview`:
    - always call `requestWeldPreview(weldDraft)` immediately before running weld preview,
    - then execute with `use_cache: true` against the just-refreshed plan.
  - This forces backend planner to recapture current start pose each run and regenerate post-action transitions accordingly.
- Preventive rule:
  - For semantics that depend on runtime start context (like `return_to_start`), never allow weld execution to skip replan on run.

#### User Preferences

- New or reinforced preference:
  - `Return to trajectory start` must mean “the robot pose right before this weld run starts,” never weld-start fallback.
- How it changed execution:
  - Prioritized semantic correctness and determinism over cache-only run latency.

#### What Worked

- Pattern/check that worked:
  - Replan-then-run for weld previews preserves high-fidelity path execution while guaranteeing correct start-context capture.

#### What Did Not Work

- Failed attempt and why:
  - Conditional cache refresh based on stale flags was insufficient for strict runtime start semantics.

#### Guardrails For Next Session

- Preflight rule:
  - If an end-action references “start” and operator intent is per-run, enforce replan-at-run regardless of prior cache freshness.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Additional replan time before each weld run is expected; optimize only if needed, without compromising start-context correctness.

### 2026-02-18 02:19 +11:00 - Stabilize weld run-state lifecycle and isolate jog loop

#### Task Summary

- Fixed a backend execution-state bug that could clear motion state mid-trajectory and allow control-loop contention.
- Added trajectory-start guard to stop active jog mode before weld/trajectory playback.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Nested step execution in `trajectory_execution._execute_joint_path` reused `_open_loop_executor_thread` which could clear `trajectory_state` (`is_running`, `thread`) during a still-active multi-step weld run.
- Detection:
  - User-reported jitter/snap behavior during weld execution; code audit showed executor cleanup was tied only to thread identity, which matches nested step execution.
- Fix:
  - Added `owns_trajectory_state` parameter to open/closed executors and disabled state cleanup for nested step calls.
  - Updated `handle_run_trajectory` to stop jog mode before run and abort if jog remains active.
- Preventive rule:
  - Any low-level executor used both standalone and nested must have explicit lifecycle ownership; never let nested calls mutate global run flags.

#### User Preferences

- New or reinforced preference:
  - Execution correctness and deterministic robot behavior are higher priority than convenience/background control loops.
  - User expects direct fixes, not speculative discussion.
- How it changed execution:
  - Focused on controller run-state/jog isolation, implemented concrete backend patches first, then validated syntax/lints.

#### What Worked

- Pattern/check that worked:
  - Tracing end-to-end from UI symptom to controller state transitions exposed the lifecycle race quickly.

#### What Did Not Work

- Failed attempt and why:
  - Looking only at weld planning math was insufficient; the dominant issue was runtime executor/jog interaction, not weld geometry sampling itself.

#### Guardrails For Next Session

- Preflight rule:
  - For motion bugs with "random snaps/jitter," inspect global motion flags (`is_running`, `is_jogging`, `thread`) and thread cleanup points before tuning planners.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Validate with live weld run in simulator to confirm no residual jitter under active UI polling and no unintended return-to-weld-start behavior.

### 2026-02-18 02:26 +11:00 - Runtime confirmation: execution-state fix is primary root cause

#### Task Summary

- Recorded user confirmation that weld execution now behaves correctly after the controller patch.
- Captured that the issue previously occurred even with jog disabled, reinforcing execution-state lifecycle as primary fault domain.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Earlier suspicion that jog could be the sole cause was incomplete.
- Detection:
  - User explicitly reported prior reproduction with jog disabled.
- Fix:
  - Keep execution-state lifecycle fix as the core resolution.
  - Retain jog-stop guard as non-invasive protection against future control-loop contention.
- Preventive rule:
  - For motion jitter/snap bugs, prioritize controller state lifecycle and thread ownership analysis before attributing solely to UI-side control streams.

#### User Preferences

- New or reinforced preference:
  - Preserve practical safety guards if they do not add downside, even when not the primary fix.
- How it changed execution:
  - Kept jog isolation check in place as defense-in-depth rather than removing it after root-cause confirmation.

#### What Worked

- Pattern/check that worked:
  - Combining code-level race fix with runtime user validation quickly converged on true root cause.

#### What Did Not Work

- Failed attempt and why:
  - Treating jog contention as the only likely source would have underexplained the jog-disabled reproductions.

#### Guardrails For Next Session

- Preflight rule:
  - If a bug reproduces with a suspected subsystem disabled, immediately elevate investigation to shared/global state and thread-lifecycle paths.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - None immediate; monitor for recurrence under long runs or repeated run/stop cycles.

### 2026-02-18 11:47 +11:00 - README refresh for merge readiness

#### Task Summary

- Added a root repository `README.md` and refreshed `web-ui/README.md` to reflect current product behavior.
- Prepared branch-level merge commit message guidance.

#### Mistakes And Fixes

- Source: `[self]`
- Mistake:
  - Assuming a root README existed would have left the “main repo readme” request partially done.
- Detection:
  - File check showed no `README.md` at repository root.
- Fix:
  - Created root `README.md` and updated `web-ui/README.md` with current architecture/workflow notes.
- Preventive rule:
  - For docs requests, verify file existence first and create missing canonical docs rather than only editing submodule docs.

#### User Preferences

- New or reinforced preference:
  - Wants merge-ready artifacts: clear commit messaging plus up-to-date top-level and UI docs.
- How it changed execution:
  - Prioritized practical documentation updates and concise merge messaging over deep code changes.

#### What Worked

- Pattern/check that worked:
  - Pairing root + feature-area README updates keeps main-branch handoff clearer for maintainers/operators.

#### What Did Not Work

- Failed attempt and why:
  - None in this step.

#### Guardrails For Next Session

- Preflight rule:
  - When asked for "main repo README," explicitly confirm root-level presence and update/create accordingly.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - Consider later consolidation between `README.md`, `AGENTS.md`, and `docs/README.md` to reduce duplicated startup guidance.

### 2026-02-18 11:55 +11:00 - Main README clarification: docs/README is canonical

#### Task Summary

- Updated `docs/README.md` after user clarified this is the canonical "main README" for repo-level documentation.
- Built a comprehensive commit-message draft based on full branch diff context rather than only current unstaged files.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Initial README update targeted root-level docs first; user clarified canonical main README is `docs/README.md`.
- Detection:
  - Direct user correction in follow-up message.
- Fix:
  - Added a dedicated `STEP_LOADER Branch Highlights` section in `docs/README.md` with end-to-end scope summary.
- Preventive rule:
  - In this repo, treat `docs/README.md` as the primary documentation entrypoint unless user asks otherwise.

#### User Preferences

- New or reinforced preference:
  - Wants branch merge materials to be comprehensive and grounded in the full branch scope.
- How it changed execution:
  - Used `master..HEAD` log/stat context before drafting commit message language.

#### What Worked

- Pattern/check that worked:
  - Pairing user clarification with git-range analysis produced accurate high-level change framing.

#### What Did Not Work

- Failed attempt and why:
  - A root-only README update was insufficient for this repository's doc convention.

#### Guardrails For Next Session

- Preflight rule:
  - For merge/prep requests, confirm canonical docs path and summarize against `base..HEAD` rather than local unstaged delta only.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - None immediate.

### 2026-02-18 11:59 +11:00 - docs/README rewritten as true onboarding entrypoint

#### Task Summary

- Replaced `docs/README.md` content with newcomer-first documentation: features, system function, and usage workflow.
- Removed release-note style sectioning that did not match the file's purpose.

#### Mistakes And Fixes

- Source: `[user]`
- Mistake:
  - Prior update style emphasized branch-change summaries instead of serving as a practical start guide.
- Detection:
  - Explicit user correction on expected README role and tone.
- Fix:
  - Full rewrite of `docs/README.md` around onboarding flow and operational usage.
- Preventive rule:
  - For canonical README files, optimize for "what it is / how it works / how to use it" before changelog-style content.

#### User Preferences

- New or reinforced preference:
  - README must function as the primary onboarding document for new repo users.
- How it changed execution:
  - Shifted from patching sections to a complete structure reset aligned to onboarding intent.

#### What Worked

- Pattern/check that worked:
  - Rebuilding the file from scratch avoided carrying over conflicting structure and tone.

#### What Did Not Work

- Failed attempt and why:
  - Incremental edits against prior structure kept reintroducing non-onboarding framing.

#### Guardrails For Next Session

- Preflight rule:
  - Before editing a "main README", define target reader and first-use journey explicitly, then shape sections around that path.

#### Follow-Ups / Risks

- Remaining risk or pending check:
  - None immediate.
