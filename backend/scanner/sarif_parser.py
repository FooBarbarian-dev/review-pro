"""
SARIF parser for extracting findings and storing in database.

Supports SARIF 2.1.0 format from multiple static analysis tools.
Implements deduplication strategy from ADR-002.
"""

import logging
from typing import Dict, List, Optional
from django.utils import timezone

from apps.findings.models import Finding
from apps.scans.models import Scan
from apps.organizations.models import Repository

logger = logging.getLogger(__name__)


class SARIFParser:
    """
    Parser for SARIF (Static Analysis Results Interchange Format) files.

    Extracts findings and stores them in the database with deduplication.
    """

    # Map SARIF severity levels to our schema
    SEVERITY_MAP = {
        "error": "high",
        "warning": "medium",
        "note": "low",
        "none": "info",
    }

    def __init__(self, scan: Scan):
        """
        Initialize parser for a specific scan.

        Args:
            scan: The Scan object these findings belong to
        """
        self.scan = scan
        self.repository = scan.repository
        self.organization = scan.repository.organization

    def parse_sarif(self, sarif_data: Dict) -> Dict[str, int]:
        """
        Parse SARIF data and create Finding objects.

        Args:
            sarif_data: SARIF JSON data as dictionary

        Returns:
            Statistics dictionary with counts
        """
        if not sarif_data or not isinstance(sarif_data, dict):
            logger.warning("Invalid SARIF data provided")
            return {
                "total": 0,
                "new": 0,
                "updated": 0,
                "errors": 0,
            }

        stats = {
            "total": 0,
            "new": 0,
            "updated": 0,
            "errors": 0,
        }

        # Extract runs from SARIF
        runs = sarif_data.get("runs", [])
        if not runs:
            logger.warning("No runs found in SARIF data")
            return stats

        # Process each run (typically one per tool)
        for run in runs:
            run_stats = self._process_run(run)
            stats["total"] += run_stats["total"]
            stats["new"] += run_stats["new"]
            stats["updated"] += run_stats["updated"]
            stats["errors"] += run_stats["errors"]

        logger.info(
            f"SARIF parsing complete: {stats['total']} total, "
            f"{stats['new']} new, {stats['updated']} updated, "
            f"{stats['errors']} errors"
        )

        return stats

    def _process_run(self, run: Dict) -> Dict[str, int]:
        """
        Process a single SARIF run.

        Args:
            run: SARIF run object

        Returns:
            Statistics for this run
        """
        stats = {
            "total": 0,
            "new": 0,
            "updated": 0,
            "errors": 0,
        }

        # Extract tool information
        tool = run.get("tool", {}).get("driver", {})
        tool_name = tool.get("name", "unknown")
        tool_version = tool.get("version") or tool.get("semanticVersion", "unknown")

        # Extract results
        results = run.get("results", [])
        logger.info(f"Processing {len(results)} results from {tool_name}")

        for result in results:
            stats["total"] += 1
            try:
                finding_data = self._extract_finding_data(
                    result, tool_name, tool_version
                )
                if finding_data:
                    created = self._create_or_update_finding(finding_data)
                    if created:
                        stats["new"] += 1
                    else:
                        stats["updated"] += 1
            except Exception as e:
                logger.error(f"Error processing SARIF result: {e}", exc_info=True)
                stats["errors"] += 1

        return stats

    def _extract_finding_data(
        self,
        result: Dict,
        tool_name: str,
        tool_version: str,
    ) -> Optional[Dict]:
        """
        Extract finding data from a SARIF result.

        Args:
            result: SARIF result object
            tool_name: Name of the analysis tool
            tool_version: Version of the analysis tool

        Returns:
            Dictionary with finding data, or None if extraction failed
        """
        # Extract rule information
        rule_id = result.get("ruleId", "unknown")
        message = self._extract_message(result)

        # Extract location
        locations = result.get("locations", [])
        if not locations:
            logger.warning(f"No location found for rule {rule_id}")
            return None

        location = locations[0].get("physicalLocation", {})
        artifact = location.get("artifactLocation", {})
        region = location.get("region", {})

        file_path = artifact.get("uri", "unknown")
        start_line = region.get("startLine", 1)
        start_column = region.get("startColumn", 1)
        end_line = region.get("endLine")
        end_column = region.get("endColumn")

        # Extract snippet
        snippet = None
        if "snippet" in region:
            snippet = region["snippet"].get("text")

        # Map SARIF level to our severity
        sarif_level = result.get("level", "warning")
        severity = self.SEVERITY_MAP.get(sarif_level, "medium")

        # Extract CWE/CVE information
        cwe_ids = []
        cve_ids = []
        properties = result.get("properties", {})
        if "tags" in properties:
            for tag in properties["tags"]:
                if tag.startswith("CWE-"):
                    cwe_ids.append(tag)
                elif tag.startswith("CVE-"):
                    cve_ids.append(tag)

        # Extract rule name from relatedLocations or properties
        rule_name = result.get("ruleIndex")
        if "properties" in result and "rule_name" in result["properties"]:
            rule_name = result["properties"]["rule_name"]

        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "message": message,
            "severity": severity,
            "file_path": file_path,
            "start_line": start_line,
            "start_column": start_column,
            "end_line": end_line,
            "end_column": end_column,
            "snippet": snippet,
            "tool_name": tool_name,
            "tool_version": tool_version,
            "cwe_ids": cwe_ids,
            "cve_ids": cve_ids,
            "sarif_data": result,  # Store full SARIF result
        }

    def _extract_message(self, result: Dict) -> str:
        """
        Extract message from SARIF result.

        SARIF messages can be in multiple formats.

        Args:
            result: SARIF result object

        Returns:
            Extracted message text
        """
        message_obj = result.get("message", {})

        # Try text first
        if "text" in message_obj:
            return message_obj["text"]

        # Try markdown
        if "markdown" in message_obj:
            return message_obj["markdown"]

        # Fallback
        return "No description available"

    def _create_or_update_finding(self, finding_data: Dict) -> bool:
        """
        Create a new finding or update existing one (deduplication).

        Args:
            finding_data: Extracted finding data

        Returns:
            True if created new finding, False if updated existing
        """
        # Generate fingerprint for deduplication (ADR-002)
        fingerprint = Finding.generate_fingerprint(
            organization_id=str(self.organization.id),
            rule_id=finding_data["rule_id"],
            file_path=finding_data["file_path"],
            start_line=finding_data["start_line"],
            start_column=finding_data["start_column"],
            message=finding_data["message"],
        )

        # Check if finding already exists
        try:
            existing_finding = Finding.objects.get(
                organization=self.organization,
                fingerprint=fingerprint,
            )

            # Update existing finding
            existing_finding.update_occurrence(self.scan)
            logger.debug(
                f"Updated existing finding: {existing_finding.rule_id} "
                f"at {existing_finding.file_path}:{existing_finding.start_line}"
            )
            return False

        except Finding.DoesNotExist:
            # Create new finding
            finding = Finding.objects.create(
                organization=self.organization,
                repository=self.repository,
                first_seen_scan=self.scan,
                last_seen_scan=self.scan,
                fingerprint=fingerprint,
                **finding_data,
            )

            logger.debug(
                f"Created new finding: {finding.rule_id} "
                f"at {finding.file_path}:{finding.start_line}"
            )
            return True

    def parse_multiple_sarif(
        self,
        sarif_results: List[Dict],
    ) -> Dict[str, int]:
        """
        Parse multiple SARIF files (from different tools).

        Args:
            sarif_results: List of SARIF data dictionaries

        Returns:
            Combined statistics
        """
        combined_stats = {
            "total": 0,
            "new": 0,
            "updated": 0,
            "errors": 0,
        }

        for sarif_data in sarif_results:
            stats = self.parse_sarif(sarif_data)
            combined_stats["total"] += stats["total"]
            combined_stats["new"] += stats["new"]
            combined_stats["updated"] += stats["updated"]
            combined_stats["errors"] += stats["errors"]

        return combined_stats
