# Deep-Dive Topic: Debugging & Bugs

> *This is a topic file for long-term storage of deep-dive architectural notes and debugging solutions. It's fetched on-demand to prevent polluting the primary project context.*

## [2026-03] UI Modal Stacking Issue
*   **Context:** Intel Inventory components were causing blocking document displays because of overlapping indices.
*   **Root Cause:** CSS `z-index` conflict in the non-intrusive notification component overlay versus the `<PauseQuestionModal>`.
*   **Solution:** Implemented relative indexing inside `UIController`. Do not arbitrarily increase `z-index` above 100 in the UI space!

## [2026-03] Missing resource 404s
*   **Context:** `haymarket-fixes.css` was returning a 404 in local dev.
*   **Root Cause:** Referenced in `index.html` but removed from file tree.
*   **Solution:** Always verify asset paths in the root index before pushing Vite builds.

## Template for new bugs
*   **[Date] [Short Title]**
*   **Context:** 
*   **Root Cause:** 
*   **Solution:** 
