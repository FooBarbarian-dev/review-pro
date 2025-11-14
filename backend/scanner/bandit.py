"""
Bandit scanner implementation.

Bandit is a tool designed to find common security issues in Python code.
It focuses on Python-specific vulnerabilities like SQL injection, hardcoded passwords,
weak crypto, etc.

PyPI: bandit
Documentation: https://bandit.readthedocs.io/
"""

from typing import List
from scanner.base import BaseScanner


class BanditScanner(BaseScanner):
    """
    Bandit scanner for Python security issues.

    Features:
    - Python-specific security checks
    - Detection of hardcoded secrets, SQL injection, weak crypto
    - Severity and confidence scoring
    - Native SARIF output (v1.7.0+)
    """

    def __init__(self, docker_image: str = "python:3.11-slim"):
        """
        Initialize Bandit scanner.

        Args:
            docker_image: Docker image with Python (bandit installed via pip)
        """
        super().__init__(
            docker_image=docker_image,
            scanner_name="bandit",
        )

    def build_scan_command(self, target_path: str, output_file: str) -> List[str]:
        """
        Build Bandit scan command.

        Args:
            target_path: Path to scan (inside container)
            output_file: Path for SARIF output (inside container)

        Returns:
            Command to install bandit and run scan
        """
        # Note: We install bandit in the container and run it
        # This is less efficient than a pre-built image but more flexible
        return [
            "sh", "-c",
            f"pip install -q bandit[sarif] && "
            f"bandit -r {target_path} -f sarif -o {output_file} || true"
        ]


class BanditDockerScanner(BaseScanner):
    """
    Bandit scanner using a pre-built Docker image.

    This is more efficient as bandit is pre-installed.
    """

    def __init__(self, docker_image: str = "secfigo/bandit:latest"):
        """
        Initialize Bandit scanner with pre-built image.

        Args:
            docker_image: Docker image with bandit pre-installed
        """
        super().__init__(
            docker_image=docker_image,
            scanner_name="bandit",
        )

    def build_scan_command(self, target_path: str, output_file: str) -> List[str]:
        """
        Build Bandit scan command.

        Args:
            target_path: Path to scan (inside container)
            output_file: Path for SARIF output (inside container)

        Returns:
            Bandit command arguments
        """
        return [
            "bandit",
            "-r",  # Recursive scan
            target_path,
            "-f", "sarif",  # SARIF format
            "-o", output_file,
            "-ll",  # Only show issues with severity >= LOW
        ]
