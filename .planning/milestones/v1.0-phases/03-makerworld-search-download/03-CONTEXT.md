# Phase 3: MakerWorld Search + Download - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Natural language search for existing models on MakerWorld with download pipeline. Users can describe what they want, see matching results, pick a model, and download it to their local filesystem. Downloaded models integrate with the existing Phase 1/2 pipeline (BambuStudio opening). No new generation or modification capabilities added — this phase is about finding and fetching existing models.

</domain>

<decisions>
## Implementation Decisions

### Search Results Display
- Show 3 results per search query
- Each result displays: name, rating, image URL (thumbnail), and link to MakerWorld page
- Numbered list format (1. Model Name ...)
- Text-focused output with image URL included for optional browser preview

### Model Recommendation
- Rank results using a combined score of rating + download count
- Highlight the recommended model with a brief reason (e.g. "Recommended: highest rated with 2k+ downloads")
- Always ask the user to confirm selection — no auto-selecting
- If no good results match the query, offer to generate the model from scratch using Phase 1 pipeline instead

### Download & File Handling
- Save downloaded files to `~/3d-prints/<makerworld-model-name>/` — same root folder as generated models
- Folder named after the MakerWorld model name (not the user's search query)
- Download all files when a model has multiple files (plates, variants, parts)
- Prefer 3MF format when available, fall back to STL

### Pipeline Integration
- Same skill, detect intent: "find me X" triggers search, "make me X" triggers generation
- After download, offer to open in BambuStudio (same flow as Phase 1)
- Downloaded models support full Phase 2 features (scaling, print settings)
- For scaling downloaded models (no .scad source), suggest BambuStudio for resizing rather than OpenSCAD import

### Claude's Discretion
- Technical approach to MakerWorld search (API discovery, web scraping, or other)
- Intent detection heuristics for search vs generate
- Combined score weighting formula for recommendations
- Error handling for network/scraping failures

</decisions>

<specifics>
## Specific Ideas

- Search should feel seamless — user doesn't need to know about MakerWorld specifically, just describes what they want
- The "offer to generate instead" fallback when no results match creates a smooth UX between search and generate flows
- Keep the same `~/3d-prints/` folder structure so all models (generated or downloaded) live together

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-makerworld-search-download*
*Context gathered: 2026-03-06*
