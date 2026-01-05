#!/usr/bin/env python3
"""
Mark Validation Passed

Called after validate_all.py passes to set marker for enforce-plugin-test.py.
This should be chained after successful validation.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

def main():
    # Read stdin (validation output)
    input_data = sys.stdin.read()

    # Check if validation passed
    try:
        data = json.loads(input_data)
        if data.get("status") == "pass" or data.get("errors", 1) == 0:
            # Set marker
            marker = Path("/tmp/skillmaker-validation-passed.marker")
            marker.write_text(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "cwd": str(Path.cwd())
            }))
            print(json.dumps({"marked": True}))
    except Exception:
        # If not JSON, check for "pass" in output
        if "pass" in input_data.lower() and "fail" not in input_data.lower():
            marker = Path("/tmp/skillmaker-validation-passed.marker")
            marker.write_text(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "cwd": str(Path.cwd())
            }))
            print(json.dumps({"marked": True}))

    # Pass through original output
    sys.exit(0)

if __name__ == "__main__":
    main()
