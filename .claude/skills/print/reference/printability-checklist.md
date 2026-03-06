# Printability Checklist

Reference for analyzing OpenSCAD geometry risk and communicating confidence to the user.

## Section 1: Geometry Risk Patterns

Analyze the .scad source code for these patterns before and after generation.

### HIGH RISK -- Warn BEFORE Generating

These patterns frequently produce unprintable or poor-quality results. Warn the user and offer a simpler alternative before writing code.

- [ ] `sphere()` or complex curves as primary geometry (organic shapes) -- faceted mesh rarely matches user expectations
- [ ] `rotate()` with angles creating overhangs greater than 60 degrees from vertical -- filament sags with nothing underneath
- [ ] Very thin features: any dimension less than 1mm -- nozzle can't reliably deposit material this small
- [ ] Unsupported horizontal surfaces spanning more than 50mm -- long flat overhangs sag or collapse without supports
- [ ] Complex boolean chains: 4 or more nested `difference()` / `intersection()` operations -- often produces non-manifold geometry or unexpected voids
- [ ] `hull()` connecting distant points -- resulting geometry is unpredictable and hard to reason about

### MEDIUM RISK -- Note AFTER Generating

These patterns usually work but may need supports or careful slicer settings. Proceed with generation, then mention the concern.

- [ ] `rotate()` creating 45-60 degree overhangs -- printable but surface quality degrades; supports help
- [ ] Bridge spans between 30-50mm -- most printers can bridge this but with visible sag
- [ ] Interlocking parts with tight tolerances (less than 0.3mm clearance) -- may fuse or not fit depending on printer calibration
- [ ] Features smaller than 2mm in any dimension -- printable but fragile and detail may be lost
- [ ] `hull()` between nearby points -- generally predictable but verify in preview

### LOW RISK -- No Special Note Needed

These patterns print reliably on any well-calibrated FDM printer.

- [ ] Axis-aligned primitives: `cube()`, `cylinder()` with no rotation
- [ ] Simple `difference()` operations (holes, cutouts)
- [ ] Chamfers and fillets at 45 degrees
- [ ] Features greater than 3mm in all dimensions
- [ ] Standard patterns: boxes, brackets, holders, stands, trays

## Section 2: Confidence Language Templates

Use natural language to communicate confidence. Never use percentages, tier labels, or numeric scores.

### Low Risk Examples

> "Straightforward geometry, this should print cleanly."

> "This is a simple box-type design -- no tricky overhangs or thin sections. Should come out great."

### Medium Risk Examples

> "This has some overhangs around 50 degrees -- it should work but you may want to check the preview. Supports might help if the bridging looks rough."

> "The thin wall section is about 1.5mm -- it'll print but might feel a bit fragile. Want me to thicken it?"

> "There's a 40mm bridge span in this design. Most printers handle that fine, but you might see some sag on the underside."

> "The interlocking parts have 0.25mm clearance -- that's tight. If they're too snug after printing, you can sand the mating surfaces or I can increase the tolerance."

### High Risk Examples

> "Organic curves like this are tricky to get right in OpenSCAD -- the mesh may have rough spots. I can try it, or I can offer a simpler geometric version that'll definitely print well. Which do you prefer?"

> "The overhang here is about 70 degrees from horizontal. Without supports, the filament will sag because there's nothing underneath to bond to."

> "This design has very thin fins (0.8mm). At that thickness, the nozzle width is wider than the feature -- it may not form properly. I can make them at least 1.2mm, or try as-is knowing they might not come out. Your call."

> "The boolean operations here are 5 levels deep, which often produces geometry artifacts. I'd suggest simplifying the design -- I can break it into two separate parts that assemble together, which will print much more reliably."

> "That's a 60mm unsupported horizontal span. The filament will droop in the middle without supports underneath. I can add built-in support ribs to the design, or you can enable tree supports in the slicer. Want me to add ribs?"

> "This part has 0.2mm clearance for a snap-fit joint. That's below what most FDM printers can reliably achieve -- the pieces will likely fuse together. I'd recommend at least 0.3mm for PLA. Should I adjust it?"

## Section 3: Messiness Detection

After multiple iterations, .scad files can accumulate cruft that makes further modification unreliable. Check these heuristics on every modification request.

### When to Suggest Regeneration

Both conditions must be true:

1. **Version count >= 5** (determined by the highest backup version number: model_v5.scad or higher exists)
2. **At least one** of the following code quality signals:
   - File exceeds 200 lines for a simple object (boxes, brackets, holders -- not complex assemblies)
   - Multiple commented-out code sections (suggests abandoned approaches left behind)
   - `difference()` / `union()` nesting deeper than 3 levels
   - Variables that shadow or override earlier definitions (same name defined twice)
   - `translate()` chains deeper than 3 levels

### Suggested Message

> "This model has gone through several iterations and the code is getting complex. Want me to regenerate it from scratch based on what we have now? I'll keep the current version as a backup."

### What Regeneration Means

- Create a new backup of the current model (model_vN.scad)
- Write a fresh model.scad from scratch that produces the same geometry
- Use clean parametric structure with all current dimensions and features
- Show the new code to the user for review before rendering
