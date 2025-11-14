"""
Base scanner class for executing static analysis tools in Docker containers.
"""

import json
import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ScanResult:
    """Container for scan results."""

    def __init__(
        self,
        tool_name: str,
        sarif_output: Optional[Dict] = None,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        error: Optional[str] = None,
    ):
        self.tool_name = tool_name
        self.sarif_output = sarif_output
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.error = error
        self.success = exit_code == 0 and error is None

    def get_findings_count(self) -> int:
        """Get the number of findings from SARIF output."""
        if not self.sarif_output:
            return 0

        try:
            runs = self.sarif_output.get("runs", [])
            if not runs:
                return 0

            results = runs[0].get("results", [])
            return len(results)
        except (KeyError, IndexError, TypeError):
            return 0


class BaseScanner(ABC):
    """
    Base class for all static analysis scanners.

    Scanners run in Docker containers for isolation and consistency.
    All scanners must output SARIF format for standardized processing.
    """

    def __init__(self, docker_image: str, scanner_name: str):
        """
        Initialize the scanner.

        Args:
            docker_image: Docker image to use for scanning
            scanner_name: Human-readable name of the scanner
        """
        self.docker_image = docker_image
        self.scanner_name = scanner_name
        self.logger = logging.getLogger(f"scanner.{scanner_name}")

    @abstractmethod
    def build_scan_command(self, target_path: str, output_file: str) -> List[str]:
        """
        Build the command to run inside the Docker container.

        Args:
            target_path: Path to scan (inside container)
            output_file: Path for SARIF output (inside container)

        Returns:
            List of command arguments
        """
        pass

    def scan(
        self,
        code_path: Path,
        output_dir: Optional[Path] = None,
        timeout: int = 300,
    ) -> ScanResult:
        """
        Execute the scanner on the given code path.

        Args:
            code_path: Path to the code to scan (on host)
            output_dir: Directory for output files (defaults to temp dir)
            timeout: Maximum execution time in seconds

        Returns:
            ScanResult with SARIF output and metadata
        """
        if not code_path.exists():
            return ScanResult(
                tool_name=self.scanner_name,
                error=f"Code path does not exist: {code_path}",
                exit_code=1,
            )

        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{self.scanner_name}.sarif"

        self.logger.info(
            f"Starting {self.scanner_name} scan on {code_path} "
            f"(timeout: {timeout}s)"
        )

        try:
            # Build Docker command
            docker_cmd = self._build_docker_command(
                code_path=code_path,
                output_file=output_file,
            )

            self.logger.debug(f"Docker command: {' '.join(docker_cmd)}")

            # Execute scanner
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            self.logger.info(
                f"{self.scanner_name} completed with exit code {result.returncode}"
            )

            # Parse SARIF output
            sarif_data = None
            if output_file.exists():
                try:
                    with open(output_file, "r") as f:
                        sarif_data = json.load(f)
                    self.logger.info(
                        f"SARIF output parsed successfully: "
                        f"{len(sarif_data.get('runs', [{}])[0].get('results', []))} findings"
                    )
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse SARIF output: {e}")
                except Exception as e:
                    self.logger.error(f"Error reading SARIF file: {e}")

            return ScanResult(
                tool_name=self.scanner_name,
                sarif_output=sarif_data,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            self.logger.error(f"{self.scanner_name} timed out after {timeout}s")
            return ScanResult(
                tool_name=self.scanner_name,
                error=f"Scan timed out after {timeout} seconds",
                exit_code=124,
            )
        except Exception as e:
            self.logger.error(f"{self.scanner_name} failed: {e}", exc_info=True)
            return ScanResult(
                tool_name=self.scanner_name,
                error=str(e),
                exit_code=1,
            )

    def _build_docker_command(
        self,
        code_path: Path,
        output_file: Path,
    ) -> List[str]:
        """
        Build the complete Docker command.

        Args:
            code_path: Host path to code
            output_file: Host path for output file

        Returns:
            Complete docker run command
        """
        # Container paths
        container_code_path = "/code"
        container_output_path = "/output/sarif.json"

        # Build scanner-specific command
        scan_cmd = self.build_scan_command(
            target_path=container_code_path,
            output_file=container_output_path,
        )

        # Build Docker command
        docker_cmd = [
            "docker",
            "run",
            "--rm",  # Remove container after execution
            "-v", f"{code_path.absolute()}:{container_code_path}:ro",  # Mount code (read-only)
            "-v", f"{output_file.parent.absolute()}:/output",  # Mount output directory
            "--network", "none",  # No network access for security
            "--memory", "2g",  # Limit memory
            "--cpus", "2",  # Limit CPU
            self.docker_image,
        ] + scan_cmd

        return docker_cmd

    def verify_docker_image(self) -> bool:
        """
        Verify that the Docker image is available.

        Returns:
            True if image exists, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.docker_image],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to verify Docker image: {e}")
            return False

    def pull_docker_image(self) -> bool:
        """
        Pull the Docker image from registry.

        Returns:
            True if pull succeeded, False otherwise
        """
        try:
            self.logger.info(f"Pulling Docker image: {self.docker_image}")
            result = subprocess.run(
                ["docker", "pull", self.docker_image],
                capture_output=True,
                timeout=300,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to pull Docker image: {e}")
            return False
