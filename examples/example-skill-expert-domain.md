# Example: Expert Domain Skill (PPTX Builder)

This example shows an **Expert Domain Skill** - complex domain knowledge that's hard to reimplement without the skill.

## Why This Needs to Be an Expert Skill

```
Without skill:
┌────────────────────────────────────────────────────────────────┐
│ User: "Create a PowerPoint with a table"                       │
│                                                                │
│ Claude:                                                        │
│ → Tries python-pptx basic API                                  │
│ → Tables don't support cell merging easily                     │
│ → Searches documentation                                       │
│ → Tries XML manipulation                                       │
│ → Gets namespace errors                                        │
│ → Tries different approach                                     │
│ → Finally works (maybe) after 5-10 attempts                    │
│ → Knowledge lost - next time starts from scratch               │
└────────────────────────────────────────────────────────────────┘

With Expert Skill:
┌────────────────────────────────────────────────────────────────┐
│ User: "Create a PowerPoint with a table"                       │
│                                                                │
│ Claude:                                                        │
│ → Loads pptx-builder skill                                     │
│ → Reads: "For tables with merged cells, use add_table.py"      │
│ → Reads: "Known quirk: set row heights AFTER merging"          │
│ → Runs tested script                                           │
│ → Works first time                                             │
└────────────────────────────────────────────────────────────────┘
```

## Structure (Comprehensive)

```
pptx-builder/
├── SKILL.md                          # Core workflow + navigation
├── scripts/
│   ├── create_presentation.py        # Initialize new presentation
│   ├── add_slide.py                  # Add slides with layouts
│   ├── add_text.py                   # Text boxes with formatting
│   ├── add_table.py                  # Tables with cell operations
│   ├── add_shape.py                  # Shapes and connectors
│   ├── add_chart.py                  # Charts from data
│   ├── add_image.py                  # Images with positioning
│   ├── export_pdf.py                 # PDF export
│   └── validation/
│       ├── validate_pptx.py          # Validate structure
│       └── repair_pptx.py            # Fix common issues
├── references/
│   ├── ooxml-structure.md            # OOXML internals
│   ├── slide-layouts.md              # Layout types
│   ├── shape-properties.md           # All shape properties
│   ├── text-formatting.md            # Font/paragraph quirks
│   ├── table-operations.md           # Table cell operations
│   ├── chart-types.md                # Chart configurations
│   ├── troubleshooting.md            # Known issues + fixes
│   └── library-limitations.md        # python-pptx limitations
└── assets/
    ├── templates/
    │   ├── blank.pptx                # Clean starting template
    │   └── corporate.pptx            # Corporate template
    └── examples/
        ├── table-example.pptx        # Working table example
        └── chart-example.pptx        # Working chart example
```

## SKILL.md

```yaml
---
name: pptx-builder
description: |
  Create and manipulate PowerPoint presentations programmatically.
  Handles OOXML complexities, python-pptx limitations, and common pitfalls.
  Supports: slides, text, tables, shapes, charts, images, PDF export.
  Trigger phrases: "create PowerPoint", "make slides", "add table to pptx",
  "PowerPoint presentation", "export slides to PDF"
allowed-tools: ["Read", "Write", "Bash"]
---

# PPTX Builder

Create PowerPoint presentations with reliable, tested scripts that handle OOXML complexities.

## Quick Start

```bash
# Create new presentation
python scripts/create_presentation.py output.pptx --template templates/blank.pptx

# Add title slide
python scripts/add_slide.py output.pptx --layout title --title "My Presentation"

# Add content slide with bullet points
python scripts/add_slide.py output.pptx --layout bullet --title "Key Points" \
  --bullets "Point 1" "Point 2" "Point 3"
```

## Available Scripts

| Script | Purpose | Key Options |
|--------|---------|-------------|
| `create_presentation.py` | Initialize pptx | `--template`, `--size` |
| `add_slide.py` | Add slides | `--layout`, `--title`, `--bullets` |
| `add_text.py` | Add text boxes | `--position`, `--font`, `--size` |
| `add_table.py` | Add tables | `--rows`, `--cols`, `--data`, `--merge` |
| `add_shape.py` | Add shapes | `--type`, `--position`, `--fill` |
| `add_chart.py` | Add charts | `--type`, `--data`, `--title` |
| `add_image.py` | Add images | `--path`, `--position`, `--size` |
| `export_pdf.py` | Export to PDF | `--output`, `--quality` |

## ⚠️ Critical: Known Limitations

### Tables
- **Cell merging**: Must set dimensions AFTER merge, not before
- **Row heights**: Set explicitly or they collapse
- Use `scripts/add_table.py --merge` for reliable merging

### Text
- **Font fallback**: Some fonts don't embed - use `--embed-fonts`
- **Text overflow**: Enable auto-fit with `--auto-fit`

### Images
- **Large images**: Compress first to avoid corruption
- **EMF/WMF**: Convert to PNG first

See [references/troubleshooting.md](references/troubleshooting.md) for all known issues.

## When to Use Scripts vs Direct API

**Always use scripts for**:
- Tables (especially with merged cells)
- Charts (data binding is complex)
- PDF export (many edge cases)

**Can use direct python-pptx for**:
- Simple text boxes
- Basic shapes without gradients
- Single images

## Workflow for Complex Presentations

1. **Plan structure**: Decide slide count and types
2. **Create from template**: `create_presentation.py --template`
3. **Add slides sequentially**: Use appropriate layout
4. **Add complex elements**: Tables, charts via scripts
5. **Validate**: `validation/validate_pptx.py output.pptx`
6. **Export if needed**: `export_pdf.py`

---

**Detailed references:**
- [OOXML Structure](references/ooxml-structure.md) - Internals
- [Troubleshooting](references/troubleshooting.md) - Fix issues
- [Library Limitations](references/library-limitations.md) - What python-pptx can't do
```

## references/ooxml-structure.md

```markdown
# OOXML Structure for PowerPoint

Understanding the internal structure helps debug issues.

## File Structure

A .pptx is a ZIP containing:

```
[Content_Types].xml     # MIME types
_rels/.rels             # Root relationships
docProps/
├── app.xml             # Application properties
└── core.xml            # Core metadata
ppt/
├── presentation.xml    # Main presentation
├── _rels/
│   └── presentation.xml.rels  # Slide references
├── slideLayouts/       # Layout definitions
├── slideMasters/       # Master slides
├── slides/
│   ├── slide1.xml      # Slide content
│   └── _rels/
│       └── slide1.xml.rels    # Slide relationships
└── theme/              # Theme definitions
```

## Key Namespaces

```python
NAMESPACES = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
}
```

## Common XML Patterns

### Text Frame

```xml
<p:txBody>
  <a:bodyPr/>
  <a:lstStyle/>
  <a:p>
    <a:r>
      <a:rPr lang="en-US" sz="1800" b="1"/>
      <a:t>Bold text</a:t>
    </a:r>
  </a:p>
</p:txBody>
```

### Table Cell Merge

```xml
<a:tc gridSpan="2">  <!-- Horizontal merge -->
  <a:txBody>...</a:txBody>
</a:tc>
<a:tc hMerge="1"/>   <!-- Hidden merged cell -->
```

## Why This Matters

When python-pptx doesn't support something, you need to:
1. Access the underlying XML via `element._element`
2. Manipulate using lxml with correct namespaces
3. Scripts in this skill handle this automatically
```

## references/troubleshooting.md

```markdown
# PPTX Troubleshooting Guide

## Common Issues and Fixes

### Issue: "Table cells collapsed to zero height"

**Cause**: Row heights not set explicitly.

**Fix**:
```python
# In scripts/add_table.py, we always set:
for row in table.rows:
    row.height = Inches(0.5)  # Explicit height
```

**Or use script**:
```bash
python scripts/add_table.py output.pptx --row-height 0.5
```

### Issue: "Merged cells lose content"

**Cause**: Merging before setting content.

**Fix**: Our script sets content AFTER merge:
```bash
python scripts/add_table.py output.pptx --merge "A1:B2" --data "Merged content"
```

### Issue: "Font not displaying in PowerPoint"

**Cause**: Font not embedded or not available.

**Fix**:
```bash
python scripts/add_text.py output.pptx --text "Hello" --font "Arial" --embed-fonts
```

### Issue: "Chart data not updating"

**Cause**: Excel cache not refreshed.

**Fix**:
```bash
python scripts/add_chart.py output.pptx --data data.csv --refresh-cache
```

### Issue: "Large image causes corruption"

**Cause**: Image too large for PPTX embedding.

**Fix**: Compress first:
```bash
python scripts/add_image.py output.pptx --image large.png --compress --max-size 1920
```

### Issue: "PDF export missing fonts"

**Cause**: Font substitution in export.

**Fix**:
```bash
python scripts/export_pdf.py input.pptx output.pdf --embed-fonts
```

## Validation

Always validate after complex operations:

```bash
python scripts/validation/validate_pptx.py output.pptx
```

Output:
```
✅ Structure valid
✅ All relationships resolved
⚠️ Warning: Slide 3 has unembedded font "CustomFont"
✅ No corrupt elements
```

## Repair Common Issues

```bash
python scripts/validation/repair_pptx.py broken.pptx fixed.pptx
```

Fixes:
- Missing relationships
- Invalid XML elements
- Corrupt image references
```

## references/library-limitations.md

```markdown
# python-pptx Limitations and Workarounds

## What python-pptx CAN'T Do (Natively)

| Feature | Limitation | Our Workaround |
|---------|------------|----------------|
| Cell merge in tables | Complex, often fails | `add_table.py --merge` uses XML |
| Gradients | Limited support | `add_shape.py --gradient` uses XML |
| SmartArt | Not supported | Manual shapes with connectors |
| Animations | Not supported | Must add in PowerPoint |
| Video embedding | Partial | External links only |
| PDF export | Not native | Uses LibreOffice/unoconv |

## Why We Use XML Manipulation

python-pptx wraps OOXML but doesn't expose everything:

```python
# python-pptx way (limited)
cell.text = "Hello"  # Works

# But for merge, need XML:
from pptx.oxml.ns import qn
cell._tc.set(qn('a:gridSpan'), str(2))  # Direct XML
```

Our scripts handle this complexity internally.

## Alternative Libraries Considered

| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| python-pptx | Active, good API | Limited features | **Primary** |
| pywin32 | Full PowerPoint API | Windows only | Backup for PDF |
| unoconv | PDF export | Requires LibreOffice | For PDF export |
| aspose-slides | Full features | Expensive license | Not used |

## When to Edit Manually

For these features, create in PowerPoint:
- Complex animations
- Video with playback controls
- SmartArt diagrams
- 3D effects
```

## Key Characteristics of Expert Domain Skills

1. **Comprehensive references/** - Document ALL the domain knowledge
2. **Tested scripts/** - Working code for every operation
3. **Troubleshooting guide** - Every known issue with fix
4. **Library limitations** - What doesn't work and why
5. **Internal structure docs** - For debugging and extension
6. **Validation tools** - Verify output is correct
7. **Working examples** - In assets/ for reference

## When to Create an Expert Domain Skill

Ask these questions:

1. **Would Claude need to trial-and-error without this?** → Expert skill
2. **Is there undocumented behavior?** → Expert skill
3. **Are there library limitations to work around?** → Expert skill
4. **Does the format have complex internals?** → Expert skill
5. **Have you spent hours discovering workarounds?** → Expert skill

If YES to any, create an Expert Domain Skill with extensive documentation!
