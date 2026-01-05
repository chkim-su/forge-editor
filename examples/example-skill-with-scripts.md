# Example: Tool Skill with Scripts

This example shows a **Tool Skill** that includes executable scripts for file manipulation.

## Structure

```
pdf-processor/
├── SKILL.md
├── scripts/
│   ├── extract_text.py
│   ├── rotate_page.py
│   └── merge_pdfs.py
└── references/
    └── troubleshooting.md
```

## SKILL.md

```yaml
---
name: pdf-processor
description: |
  Process PDF files: extract text, rotate pages, merge documents.
  Supports: text extraction, page rotation, PDF merging.
  Trigger phrases: "extract text from PDF", "rotate PDF", "merge PDFs", "process PDF"
allowed-tools: ["Read", "Write", "Bash"]
---

# PDF Processor

Process PDF files with reliable, tested scripts.

## Quick Start

```bash
# Extract text
python scripts/extract_text.py input.pdf output.txt

# Rotate pages
python scripts/rotate_page.py input.pdf output.pdf 90

# Merge PDFs
python scripts/merge_pdfs.py file1.pdf file2.pdf output.pdf
```

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `extract_text.py` | Extract text content | `python scripts/extract_text.py <input.pdf> <output.txt>` |
| `rotate_page.py` | Rotate pages | `python scripts/rotate_page.py <input.pdf> <output.pdf> <degrees>` |
| `merge_pdfs.py` | Merge multiple PDFs | `python scripts/merge_pdfs.py <pdf1> <pdf2> ... <output.pdf>` |

## When to Use Scripts vs Generate Code

**Use these scripts when**:
- Processing PDF files (they're tested and reliable)
- Same operation needed multiple times

**Generate custom code when**:
- Unique PDF manipulation not covered by scripts
- Need to integrate with specific workflow

## Script Details

### extract_text.py

Extracts all text content from a PDF file.

```bash
python scripts/extract_text.py report.pdf extracted.txt
```

**Output**: Plain text file with extracted content.

### rotate_page.py

Rotates all pages by specified degrees (90, 180, 270).

```bash
python scripts/rotate_page.py scanned.pdf rotated.pdf 90
```

**Supported rotations**: 90, 180, 270 degrees clockwise.

### merge_pdfs.py

Combines multiple PDF files into one.

```bash
python scripts/merge_pdfs.py part1.pdf part2.pdf part3.pdf combined.pdf
```

**Last argument**: Output file path.

---

For troubleshooting: [references/troubleshooting.md](references/troubleshooting.md)
```

## scripts/extract_text.py

```python
#!/usr/bin/env python3
"""
Extract text from PDF files using pdfplumber.

Usage:
    python extract_text.py <input.pdf> <output.txt>

Example:
    python extract_text.py report.pdf extracted.txt
"""

import argparse
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


def extract_text(input_path: Path, output_path: Path) -> None:
    """Extract text from PDF and write to file."""
    text_content = []

    with pdfplumber.open(input_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                text_content.append(f"--- Page {i} ---\n{text}\n")

    output_path.write_text("\n".join(text_content))
    print(f"Extracted {len(text_content)} pages to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from PDF files"
    )
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("output", help="Output text file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    extract_text(input_path, output_path)


if __name__ == "__main__":
    main()
```

## references/troubleshooting.md

```markdown
# PDF Processor Troubleshooting

## Common Issues

### Issue: "pdfplumber not installed"

**Solution**:
```bash
pip install pdfplumber
```

### Issue: "Permission denied"

**Cause**: Output file location not writable.

**Solution**: Check file permissions or choose different output path.

### Issue: Extracted text is garbled

**Cause**: PDF uses non-standard encoding or is image-based.

**Solution**: For image-based PDFs, use OCR tools like Tesseract instead.

### Issue: Rotation doesn't work

**Cause**: PDF is encrypted or corrupted.

**Solution**: Try decrypting first or use a different PDF tool.
```

## Key Characteristics of Tool Skills

1. **Scripts are the core functionality** - Not just documentation
2. **Each script is standalone** - Works independently with argparse
3. **Scripts are tested** - Reliable, deterministic behavior
4. **SKILL.md documents usage** - When and how to use each script
5. **References for edge cases** - Troubleshooting, advanced usage

## When to Create a Tool Skill

- Same operations performed repeatedly (file processing)
- Reliability is critical (can't afford bugs)
- File format manipulation (PDF, XLSX, images)
- Operations that Claude would regenerate each time
