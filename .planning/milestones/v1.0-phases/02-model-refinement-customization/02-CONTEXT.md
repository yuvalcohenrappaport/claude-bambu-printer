# Phase 2: Model Refinement + Customization - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the /print skill so users can iterate on generated models (modify by description, scale/resize), get confidence feedback on complex geometry, and receive print setting recommendations. This phase builds on the existing SKILL.md, openscad-guide.md, and materials.md from Phase 1.

</domain>

<decisions>
## Implementation Decisions

### Modification flow
- Reference previous models via conversation context if recent, or browse ~/3d-prints/ folders if starting fresh
- Edit existing .scad file in place, but keep backups as model_v1.scad, model_v2.scad, etc.
- After modifying, show the code changes and ask "want me to render this?" before running OpenSCAD — do not auto-render
- After 5+ iterations, suggest regenerating from scratch if the model is getting messy

### Scaling behavior
- Preserve wall thickness when scaling — walls stay at their designed value (e.g., 2mm stays 2mm), only outer dimensions change
- Accept both relative ("20% taller") and absolute ("set width to 10cm") scaling inputs
- Prefer modifying parametric variables in the .scad file; fall back to scale() transform only if model structure is unclear
- Auto-fix printability issues after scaling (e.g., enforce minimum wall thickness) and tell the user what was adjusted

### Confidence communication
- Warn before generating if clearly risky; note after generating for borderline cases
- Use descriptive natural language — "Simple geometry, should work fine" vs "Complex curves, may need manual tweaking" — no percentages or tiers
- For low-confidence models, offer alternatives first: "I can try this complex shape, or here's a simpler version that'll definitely work. Which one?"
- Explain WHY something is risky with brief technical reasons — e.g., "overhangs > 45 degrees need supports", "thin walls under 1mm may not print solidly"

### Print settings
- Full profile recommendations: infill, layer height, supports, print speed, temperature, wall count, top/bottom layers
- Settings based on both purpose (what it's for) and geometry (overhangs, thin walls, bridges) — purpose sets baseline, geometry adjusts specifics
- Embed print settings into the 3MF file metadata so BambuStudio picks them up automatically
- BambuLab-specific by default (BambuStudio profile names, Bambu filament presets), with generic equivalents mentioned

### Claude's Discretion
- Exact versioning scheme for backup files (v1, v2 vs timestamps)
- How to detect when a model is "getting messy" after iterations
- How to analyze .scad geometry for printability risks
- 3MF metadata format for embedding print settings

</decisions>

<specifics>
## Specific Ideas

- Backup versioning keeps a history so users can roll back to any previous iteration
- The "offer alternatives" pattern for complex geometry lets users choose their risk tolerance
- Embedding settings in 3MF removes friction — user opens in BambuStudio and settings are already there

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-model-refinement-customization*
*Context gathered: 2026-03-05*
