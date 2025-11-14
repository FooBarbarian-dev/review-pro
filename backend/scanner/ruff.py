"""
Ruff scanner implementation.

Ruff is an extremely fast Python linter written in Rust. While primarily a linter,
it includes security-focused rules (S-series from flake8-bandit) and can detect
common Python issues.

PyPI: ruff
Documentation: https://docs.astral.sh/ruff/
"""

import json
from pathlib import Path
from typing import List
from scanner.base import BaseScanner, ScanResult


class RuffScanner(BaseScanner):
    """
    Ruff scanner for fast Python linting with security checks.

    Features:
    - 10-100x faster than Flake8
    - Includes flake8-bandit security rules (S-series)
    - Can replace multiple tools (flake8, pylint, etc.)
    - JSON output (converted to SARIF)
    """

    def __init__(self, docker_image: str = "python:3.11-slim"):
        """
        Initialize Ruff scanner.

        Args:
            docker_image: Docker image with Python (ruff installed via pip)
        """
        super().__init__(
            docker_image=docker_image,
            scanner_name="ruff",
        )

    def build_scan_command(self, target_path: str, output_file: str) -> List[str]:
        """
        Build Ruff scan command.

        Note: Ruff doesn't natively support SARIF, so we output JSON
        and convert it in the scan() method.

        Args:
            target_path: Path to scan (inside container)
            output_file: Path for JSON output (inside container)

        Returns:
            Command to install ruff and run scan
        """
        # We'll output JSON format and convert to SARIF
        json_output = output_file.replace(".sarif", ".json")

        return [
            "sh", "-c",
            f"pip install -q ruff && "
            f"ruff check {target_path} "
            f"--select S,B,E,F,W "  # Security (S), bugbear (B), errors (E,F,W)
            f"--output-format json > {json_output} || true"
        ]

    def scan(
        self,
        code_path: Path,
        output_dir: Path = None,
        timeout: int = 300,
    ) -> ScanResult:
        """
        Execute Ruff scan and convert output to SARIF.

        Args:
            code_path: Path to code to scan
            output_dir: Directory for output files
            timeout: Maximum execution time in seconds

        Returns:
            ScanResult with SARIF output
        """
        # Run the base scan (outputs JSON)
        result = super().scan(code_path, output_dir, timeout)

        if not result.success:
            return result

        # Convert Ruff JSON to SARIF
        if output_dir:
            json_file = output_dir / "ruff.json"
            sarif_file = output_dir / "ruff.sarif"

            if json_file.exists():
                try:
                    with open(json_file, "r") as f:
                        ruff_output = json.load(f)

                    sarif_data = self._convert_to_sarif(ruff_output)

                    with open(sarif_file, "w") as f:
                        json.dump(sarif_data, f, indent=2)

                    result.sarif_output = sarif_data
                    self.logger.info(
                        f"Converted Ruff JSON to SARIF: {result.get_findings_count()} findings"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to convert Ruff output to SARIF: {e}")

        return result

    def _convert_to_sarif(self, ruff_output: List[dict]) -> dict:
        """
        Convert Ruff JSON output to SARIF format.

        Args:
            ruff_output: List of Ruff findings

        Returns:
            SARIF-formatted dictionary
        """
        results = []

        for finding in ruff_output:
            # Extract location
            location = finding.get("location", {})
            file_path = finding.get("filename", "unknown")
            line = location.get("row", 1)
            column = location.get("column", 1)

            # Extract rule info
            code = finding.get("code", "UNKNOWN")
            message = finding.get("message", "No description")
            url = finding.get("url")

            # Map Ruff severity to SARIF level
            # Ruff doesn't have severity, so we use rule prefixes
            level = "warning"
            if code.startswith("S"):  # Security issues
                level = "error"
            elif code.startswith("E") or code.startswith("F"):  # Errors
                level = "error"

            sarif_result = {
                "ruleId": code,
                "level": level,
                "message": {
                    "text": message
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": file_path,
                            },
                            "region": {
                                "startLine": line,
                                "startColumn": column,
                            }
                        }
                    }
                ],
            }

            if url:
                sarif_result["helpUri"] = url

            results.append(sarif_result)

        # Build SARIF structure
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Ruff",
                            "informationUri": "https://docs.astral.sh/ruff/",
                            "version": "latest",
                            "semanticVersion": "0.0.0",
                        }
                    },
                    "results": results,
                }
            ],
        }

        return sarif
