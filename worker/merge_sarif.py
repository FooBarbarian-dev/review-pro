#!/usr/bin/env python3
"""
SARIF Merger - Combines multiple SARIF files into a single report

Usage:
    python merge_sarif.py file1.sarif file2.sarif file3.sarif > merged.sarif
"""

import json
import sys
from typing import List, Dict, Any


def load_sarif(filepath: str) -> Dict[str, Any]:
    """Load SARIF file from disk."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return None


def merge_sarif_files(sarif_files: List[str]) -> Dict[str, Any]:
    """
    Merge multiple SARIF files into a single SARIF document.

    Args:
        sarif_files: List of SARIF file paths

    Returns:
        Merged SARIF document
    """
    # Initialize merged SARIF with SARIF 2.1.0 schema
    merged = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": []
    }

    # Track statistics
    total_results = 0
    total_runs = 0

    # Process each SARIF file
    for filepath in sarif_files:
        sarif_data = load_sarif(filepath)

        if sarif_data is None:
            continue

        # Validate SARIF version
        version = sarif_data.get('version', '')
        if not version.startswith('2.1'):
            print(f"Warning: {filepath} uses SARIF version {version}, expected 2.1.x", file=sys.stderr)

        # Merge runs from this file
        runs = sarif_data.get('runs', [])
        for run in runs:
            # Add source information
            tool = run.get('tool', {})
            driver = tool.get('driver', {})

            # Track statistics
            results = run.get('results', [])
            total_results += len(results)
            total_runs += 1

            # Add run to merged document
            merged['runs'].append(run)

    # Log merge summary
    print(f"Merged {total_runs} runs with {total_results} total results from {len(sarif_files)} files", file=sys.stderr)

    return merged


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: merge_sarif.py <sarif_file1> [sarif_file2] ...", file=sys.stderr)
        sys.exit(1)

    sarif_files = sys.argv[1:]

    # Validate files exist
    import os
    for filepath in sarif_files:
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

    # Merge SARIF files
    merged_sarif = merge_sarif_files(sarif_files)

    if not merged_sarif.get('runs'):
        print("Error: No valid SARIF runs found", file=sys.stderr)
        sys.exit(1)

    # Output merged SARIF to stdout
    json.dump(merged_sarif, sys.stdout, indent=2)


if __name__ == '__main__':
    main()
