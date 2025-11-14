"""
Semgrep scanner implementation.

Semgrep is a fast, open-source static analysis tool that finds bugs and enforces
code standards. It supports multiple languages and has extensive community rules.

Official image: returntocorp/semgrep
Documentation: https://semgrep.dev/
"""

from typing import List
from scanner.base import BaseScanner


class SemgrepScanner(BaseScanner):
    """
    Semgrep scanner for multi-language SAST.

    Features:
    - 2000+ community rules for common vulnerabilities
    - Support for 30+ languages
    - Fast scanning (1000s of files/second)
    - Native SARIF output
    """

    def __init__(self, docker_image: str = "returntocorp/semgrep:latest"):
        """
        Initialize Semgrep scanner.

        Args:
            docker_image: Docker image to use (default: latest)
        """
        super().__init__(
            docker_image=docker_image,
            scanner_name="semgrep",
        )

    def build_scan_command(self, target_path: str, output_file: str) -> List[str]:
        """
        Build Semgrep scan command.

        Args:
            target_path: Path to scan (inside container)
            output_file: Path for SARIF output (inside container)

        Returns:
            Semgrep command arguments
        """
        return [
            "semgrep",
            "scan",
            "--config=auto",  # Use recommended rules
            "--sarif",  # Output SARIF format
            "--output", output_file,
            "--verbose",
            "--metrics=off",  # Disable telemetry
            "--no-git-ignore",  # Scan all files
            target_path,
        ]


class SemgrepCustomRulesScanner(SemgrepScanner):
    """
    Semgrep scanner with custom rule configuration.

    Use this for organization-specific security policies.
    """

    def __init__(
        self,
        rules_config: str = "p/security-audit",
        docker_image: str = "returntocorp/semgrep:latest",
    ):
        """
        Initialize Semgrep with custom rules.

        Args:
            rules_config: Semgrep rules config (e.g., "p/python", "p/owasp-top-ten")
            docker_image: Docker image to use
        """
        super().__init__(docker_image=docker_image)
        self.rules_config = rules_config
        self.scanner_name = f"semgrep-{rules_config.replace('/', '-')}"

    def build_scan_command(self, target_path: str, output_file: str) -> List[str]:
        """Build Semgrep command with custom rules."""
        return [
            "semgrep",
            "scan",
            f"--config={self.rules_config}",
            "--sarif",
            "--output", output_file,
            "--verbose",
            "--metrics=off",
            "--no-git-ignore",
            target_path,
        ]
