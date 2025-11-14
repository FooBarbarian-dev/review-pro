"""
Scan repository workflow for executing static analysis tools.

This workflow orchestrates:
1. Repository cloning (or using provided path)
2. Parallel execution of SA tools (Semgrep, Bandit, Ruff)
3. SARIF parsing and database storage
4. Cleanup

Pattern: Temporal DAG for durable execution with retries
"""

import os
import shutil
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Django setup for activities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.scans.models import Scan
from scanner.semgrep import SemgrepScanner
from scanner.bandit import BanditScanner
from scanner.ruff import RuffScanner
from scanner.sarif_parser import SARIFParser


@activity.defn
async def clone_repository(repo_url: str, target_dir: str) -> Dict:
    """
    Clone a git repository to a temporary directory.

    Args:
        repo_url: URL of the git repository
        target_dir: Target directory for clone

    Returns:
        Dictionary with clone status and path
    """
    activity.logger.info(f"Cloning repository: {repo_url}")

    try:
        # Create target directory
        Path(target_dir).mkdir(parents=True, exist_ok=True)

        # Clone repository
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Git clone failed: {result.stderr}",
                "path": None,
            }

        activity.logger.info(f"Repository cloned successfully to {target_dir}")

        return {
            "success": True,
            "path": target_dir,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Git clone timed out after 300 seconds",
            "path": None,
        }
    except Exception as e:
        activity.logger.error(f"Failed to clone repository: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "path": None,
        }


@activity.defn
async def run_semgrep_scan(code_path: str, output_dir: str) -> Dict:
    """
    Run Semgrep scanner.

    Args:
        code_path: Path to code to scan
        output_dir: Directory for output files

    Returns:
        Scan result dictionary
    """
    activity.logger.info(f"Running Semgrep scan on {code_path}")

    try:
        scanner = SemgrepScanner()

        # Pull Docker image if needed
        if not scanner.verify_docker_image():
            activity.logger.info("Pulling Semgrep Docker image...")
            if not scanner.pull_docker_image():
                return {
                    "success": False,
                    "tool": "semgrep",
                    "error": "Failed to pull Docker image",
                }

        # Run scan
        result = scanner.scan(
            code_path=Path(code_path),
            output_dir=Path(output_dir),
            timeout=600,
        )

        return {
            "success": result.success,
            "tool": "semgrep",
            "findings_count": result.get_findings_count(),
            "sarif_output": result.sarif_output,
            "error": result.error,
        }

    except Exception as e:
        activity.logger.error(f"Semgrep scan failed: {e}", exc_info=True)
        return {
            "success": False,
            "tool": "semgrep",
            "error": str(e),
        }


@activity.defn
async def run_bandit_scan(code_path: str, output_dir: str) -> Dict:
    """
    Run Bandit scanner.

    Args:
        code_path: Path to code to scan
        output_dir: Directory for output files

    Returns:
        Scan result dictionary
    """
    activity.logger.info(f"Running Bandit scan on {code_path}")

    try:
        scanner = BanditScanner()

        # Run scan
        result = scanner.scan(
            code_path=Path(code_path),
            output_dir=Path(output_dir),
            timeout=600,
        )

        return {
            "success": result.success,
            "tool": "bandit",
            "findings_count": result.get_findings_count(),
            "sarif_output": result.sarif_output,
            "error": result.error,
        }

    except Exception as e:
        activity.logger.error(f"Bandit scan failed: {e}", exc_info=True)
        return {
            "success": False,
            "tool": "bandit",
            "error": str(e),
        }


@activity.defn
async def run_ruff_scan(code_path: str, output_dir: str) -> Dict:
    """
    Run Ruff scanner.

    Args:
        code_path: Path to code to scan
        output_dir: Directory for output files

    Returns:
        Scan result dictionary
    """
    activity.logger.info(f"Running Ruff scan on {code_path}")

    try:
        scanner = RuffScanner()

        # Run scan
        result = scanner.scan(
            code_path=Path(code_path),
            output_dir=Path(output_dir),
            timeout=600,
        )

        return {
            "success": result.success,
            "tool": "ruff",
            "findings_count": result.get_findings_count(),
            "sarif_output": result.sarif_output,
            "error": result.error,
        }

    except Exception as e:
        activity.logger.error(f"Ruff scan failed: {e}", exc_info=True)
        return {
            "success": False,
            "tool": "ruff",
            "error": str(e),
        }


@activity.defn
async def parse_and_store_findings(scan_id: str, scan_results: List[Dict]) -> Dict:
    """
    Parse SARIF output and store findings in database.

    Args:
        scan_id: UUID of the Scan object
        scan_results: List of scan result dictionaries

    Returns:
        Statistics dictionary
    """
    activity.logger.info(f"Parsing findings for scan {scan_id}")

    try:
        # Get scan object
        scan = Scan.objects.get(id=scan_id)

        # Create parser
        parser = SARIFParser(scan)

        # Extract SARIF data from results
        sarif_outputs = []
        for result in scan_results:
            if result.get("success") and result.get("sarif_output"):
                sarif_outputs.append(result["sarif_output"])

        # Parse all SARIF files
        stats = parser.parse_multiple_sarif(sarif_outputs)

        activity.logger.info(
            f"Parsed findings: {stats['total']} total, "
            f"{stats['new']} new, {stats['updated']} updated"
        )

        # Update scan status
        scan.status = "completed"
        scan.total_findings = stats["new"] + stats["updated"]
        scan.save(update_fields=["status", "total_findings"])

        return {
            "success": True,
            "stats": stats,
        }

    except Scan.DoesNotExist:
        activity.logger.error(f"Scan {scan_id} not found")
        return {
            "success": False,
            "error": f"Scan {scan_id} not found",
        }
    except Exception as e:
        activity.logger.error(f"Failed to parse findings: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@activity.defn
async def cleanup_scan_directory(directory_path: str) -> Dict:
    """
    Clean up temporary scan directory.

    Args:
        directory_path: Path to directory to remove

    Returns:
        Cleanup status
    """
    activity.logger.info(f"Cleaning up directory: {directory_path}")

    try:
        if Path(directory_path).exists():
            shutil.rmtree(directory_path)
            activity.logger.info(f"Removed directory: {directory_path}")

        return {"success": True}

    except Exception as e:
        activity.logger.error(f"Failed to cleanup directory: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@workflow.defn
class ScanRepositoryWorkflow:
    """
    Workflow for scanning a repository with multiple static analysis tools.

    Orchestrates:
    1. Repository cloning (or use provided path)
    2. Parallel execution of Semgrep, Bandit, and Ruff
    3. SARIF parsing and database storage
    4. Cleanup

    Provides durable execution with retries and error handling.
    """

    @workflow.run
    async def run(
        self,
        scan_id: str,
        repo_url: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> Dict:
        """
        Execute the scan workflow.

        Args:
            scan_id: UUID of the Scan object
            repo_url: URL of repository to clone (optional)
            local_path: Local path to scan (optional)

        Returns:
            Workflow result dictionary
        """
        workflow.logger.info(f"Starting scan workflow for scan {scan_id}")

        # Create temporary directories
        temp_dir = tempfile.mkdtemp(prefix="scan_")
        output_dir = tempfile.mkdtemp(prefix="output_")

        try:
            # Step 1: Get code (clone or use local path)
            if repo_url:
                clone_result = await workflow.execute_activity(
                    clone_repository,
                    args=[repo_url, temp_dir],
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )

                if not clone_result["success"]:
                    return {
                        "success": False,
                        "error": f"Clone failed: {clone_result['error']}",
                    }

                code_path = clone_result["path"]
            else:
                code_path = local_path

            if not code_path:
                return {
                    "success": False,
                    "error": "Neither repo_url nor local_path provided",
                }

            workflow.logger.info(f"Scanning code at: {code_path}")

            # Step 2: Run all scanners in parallel
            scan_tasks = [
                workflow.execute_activity(
                    run_semgrep_scan,
                    args=[code_path, output_dir],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                ),
                workflow.execute_activity(
                    run_bandit_scan,
                    args=[code_path, output_dir],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                ),
                workflow.execute_activity(
                    run_ruff_scan,
                    args=[code_path, output_dir],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                ),
            ]

            # Wait for all scans to complete
            scan_results = await workflow.wait_for_all(*scan_tasks)

            workflow.logger.info(
                f"All scans completed. Results: {len(scan_results)}"
            )

            # Step 3: Parse and store findings
            parse_result = await workflow.execute_activity(
                parse_and_store_findings,
                args=[scan_id, scan_results],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            if not parse_result["success"]:
                return {
                    "success": False,
                    "error": f"Parse failed: {parse_result.get('error')}",
                }

            # Step 4: Cleanup (best effort)
            await workflow.execute_activity(
                cleanup_scan_directory,
                args=[temp_dir],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            await workflow.execute_activity(
                cleanup_scan_directory,
                args=[output_dir],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

            # Return success
            return {
                "success": True,
                "scan_id": scan_id,
                "scan_results": scan_results,
                "stats": parse_result.get("stats", {}),
            }

        except Exception as e:
            workflow.logger.error(f"Scan workflow failed: {e}", exc_info=True)

            # Cleanup on error (best effort)
            try:
                await workflow.execute_activity(
                    cleanup_scan_directory,
                    args=[temp_dir],
                    start_to_close_timeout=timedelta(minutes=5),
                )
            except:
                pass

            return {
                "success": False,
                "error": str(e),
            }
