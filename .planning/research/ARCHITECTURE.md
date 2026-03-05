# Architecture Patterns

**Domain:** Claude-powered 3D printing automation
**Researched:** 2026-03-05

## Recommended Architecture

Claude Code skill with modular Python scripts. Claude acts as the orchestrator -- it reads SKILL.md, understands the user's intent, and calls the appropriate Python scripts.

```
User (natural language)
    |
    v
Claude Code (AI orchestrator)
    |
    +-- reads SKILL.md for instructions
    |
    +-- calls scripts/ based on intent:
         |
         +-- search_models.py     [MakerWorld HTTP API]
         |
         +-- generate_scad.py     [SolidPython2 -> .scad file]
         |
         +-- render_model.py      [OpenSCAD CLI -> .stl/.3mf]
         |
         +-- transform_model.py   [trimesh: scale, rotate, validate]
         |
         +-- export_3mf.py        [lib3mf: package final .3mf]
         |
         +-- print_job.py         [bambulabs-api: send to printer]
```

### Component Boundaries

| Component | Responsibility | Communicates With | I/O |
|-----------|---------------|-------------------|-----|
| **SKILL.md** | Instructs Claude when/how to use the tool | Claude Code runtime | Loaded into Claude context |
| **search_models.py** | Search MakerWorld, return structured results | MakerWorld (HTTP) | stdin: query string -> stdout: JSON results |
| **generate_scad.py** | Generate .scad from parameters | Filesystem | stdin: JSON params -> writes .scad file |
| **render_model.py** | Shell out to OpenSCAD CLI | OpenSCAD binary | reads .scad -> writes .stl or .3mf |
| **transform_model.py** | Scale, rotate, validate meshes | Filesystem | reads .stl/.3mf -> writes transformed file |
| **export_3mf.py** | Create/modify 3MF packages | Filesystem | reads mesh -> writes .3mf with metadata |
| **print_job.py** | Send to BambuLab printer | Printer (MQTT) | reads .3mf + config -> sends print job |
| **config.py** | Printer credentials, default settings | Filesystem | reads ~/.config/bambulab/config.json |

### Data Flow

**Flow 1: Search and print existing model**
```
"Find me a phone stand"
  -> search_models.py (query MakerWorld)
  -> user picks from results
  -> download .3mf/.stl from MakerWorld
  -> transform_model.py (optional: scale)
  -> export_3mf.py (ensure 3MF format)
  -> print_job.py (send to printer)
```

**Flow 2: Generate new model**
```
"Make a box 10x5x3cm with rounded corners"
  -> generate_scad.py (Claude writes SolidPython2 code -> .scad)
  -> render_model.py (openscad -o output.3mf input.scad)
  -> transform_model.py (optional: validate watertight)
  -> print_job.py (send to printer)
```

**Flow 3: Modify existing model**
```
"Scale this model to 150%"
  -> transform_model.py (trimesh load -> scale -> save)
  -> export_3mf.py (re-package as 3MF)
```

## Patterns to Follow

### Pattern 1: Script-per-action
**What:** Each Python script handles exactly one action. Claude calls them sequentially.
**When:** Always. This is the core architecture pattern.
**Why:** Claude Code skills work best with discrete, composable scripts. Each script is independently testable. Claude can chain them in any order based on user intent.
**Example:**
```python
# generate_scad.py - takes JSON params, outputs .scad file
import sys
import json
from solid2 import cube, cylinder, union, scad_render_to_file

def generate(params: dict) -> str:
    """Generate .scad file from parameters. Returns output path."""
    output_path = params.get("output", "model.scad")
    # ... build geometry from params ...
    scad_render_to_file(model, output_path)
    return output_path

if __name__ == "__main__":
    params = json.loads(sys.argv[1])
    path = generate(params)
    print(json.dumps({"output": path}))
```

### Pattern 2: Claude as Code Generator
**What:** For model generation, Claude writes SolidPython2 code directly, not just parameters.
**When:** Complex or custom models that can't be parameterized into a template.
**Why:** Claude is good at writing code. SolidPython2 is Python. Let Claude write the geometry code and the script just executes it.
**Example:**
```python
# Claude generates this code block:
from solid2 import cube, cylinder, difference
model = difference()(
    cube([100, 50, 30]),
    cylinder(r=15, h=30).translate([50, 25, 0])
)
```

### Pattern 3: JSON over stdin/stdout
**What:** Scripts communicate via JSON on stdin/stdout.
**When:** For all script I/O.
**Why:** Claude can easily construct and parse JSON. No need for argument parsing complexity. Enables piping between scripts.

### Pattern 4: Local config file
**What:** Store printer IP, access code, serial number in `~/.config/bambulab/config.json`.
**When:** For printer connection details.
**Why:** Keeps secrets out of skill files. Standard XDG-style config location.
```json
{
  "printer_ip": "192.168.1.100",
  "access_code": "12345678",
  "serial": "01P00A000000000"
}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic Script
**What:** One big script that handles search, generate, render, export, print.
**Why bad:** Claude can't compose actions flexibly. Testing is painful. Single failure = everything fails.
**Instead:** Script-per-action with Claude as orchestrator.

### Anti-Pattern 2: Building a Web Server for Phase 1
**What:** Wrapping everything in FastAPI/Flask for the Claude Code skill.
**Why bad:** Claude Code skills call scripts directly. A web server adds latency, complexity, and failure modes for zero benefit.
**Instead:** Direct Python script execution. Add web layer only in Phase 2 if needed.

### Anti-Pattern 3: Trying to Parse .scad Files
**What:** Building a parser for existing OpenSCAD files to modify them.
**Why bad:** OpenSCAD's syntax is complex and non-trivial to parse. This is a rabbit hole.
**Instead:** Always generate .scad from scratch using SolidPython2. For modifying existing models, work at the mesh level (trimesh).

### Anti-Pattern 4: Embedding OpenSCAD
**What:** Trying to call OpenSCAD as a library instead of CLI.
**Why bad:** OpenSCAD doesn't have a stable library API. The CLI is the supported interface.
**Instead:** `subprocess.run(["openscad", "-o", "out.3mf", "in.scad"])` -- it's the standard approach.

## Scalability Considerations

| Concern | Phase 1 (Skill) | Phase 2 (App) | Notes |
|---------|-----------------|---------------|-------|
| Model storage | Local filesystem | SQLite cache | Models are files, not DB rows |
| MakerWorld rate limits | Manual use = low volume | Need caching layer | Cache search results for 24h |
| OpenSCAD render time | Sync, blocking | Could background | Complex models take 5-30s |
| Concurrent prints | One at a time | Queue system | BambuLab printers handle one job at a time anyway |

## Sources

- [Claude Code Skills docs](https://code.claude.com/docs/en/skills) -- skill file structure, allowed-tools, script execution
- [SolidPython2 PyPI](https://pypi.org/project/solidpython2/) -- API for generating .scad
- [OpenSCAD CLI docs](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment) -- command-line rendering
- [bambulabs-api examples](https://bambutools.github.io/bambulabs_api/examples.html) -- printer integration patterns
