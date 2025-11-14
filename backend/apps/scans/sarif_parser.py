"""
SARIF (Static Analysis Results Interchange Format) parser for security findings.
Implements ADR-005 hybrid storage strategy.
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from apps.findings.models import Finding
from apps.findings.utils import generate_finding_fingerprint, deduplicate_finding

logger = logging.getLogger(__name__)


class SARIFParser:
    """
    Parse SARIF v2.1.0 files and extract security findings.

    SARIF is the standard format for static analysis tools.
    Supports multiple tools: Semgrep, Bandit, ESLint, CodeQL, etc.
    """

    # Severity mapping from SARIF levels to our severity choices
    SEVERITY_MAP = {
        'error': 'high',
        'warning': 'medium',
        'note': 'low',
        'none': 'info',
    }

    def __init__(self):
        self.findings_created = 0
        self.findings_updated = 0
        self.errors = []

    def parse_file(self, sarif_path: str) -> Dict:
        """
        Load and parse SARIF file from filesystem.

        Args:
            sarif_path: Path to SARIF JSON file

        Returns:
            Parsed SARIF data as dictionary

        Raises:
            json.JSONDecodeError: If file is not valid JSON
            FileNotFoundError: If file doesn't exist
        """
        try:
            with open(sarif_path, 'r', encoding='utf-8') as f:
                sarif_data = json.load(f)

            # Validate SARIF version
            version = sarif_data.get('version', '')
            if not version.startswith('2.1'):
                logger.warning(f"SARIF version {version} may not be fully supported. Expected 2.1.x")

            return sarif_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid SARIF JSON in {sarif_path}: {e}")
            raise
        except FileNotFoundError as e:
            logger.error(f"SARIF file not found: {sarif_path}")
            raise

    def parse_string(self, sarif_content: str) -> Dict:
        """
        Parse SARIF content from string.

        Args:
            sarif_content: SARIF JSON as string

        Returns:
            Parsed SARIF data as dictionary
        """
        try:
            sarif_data = json.loads(sarif_content)
            return sarif_data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid SARIF JSON: {e}")
            raise

    def extract_findings(
        self,
        sarif_data: Dict,
        scan,
        organization,
        repository
    ) -> int:
        """
        Extract findings from SARIF data and create Finding objects.

        Implements deduplication logic per ADR-002.

        Args:
            sarif_data: Parsed SARIF dictionary
            scan: Scan object that produced this SARIF
            organization: Organization object
            repository: Repository object

        Returns:
            Number of findings created (new findings, not deduplicated)
        """
        self.findings_created = 0
        self.findings_updated = 0
        self.errors = []

        # SARIF structure: { "runs": [ { "results": [...] } ] }
        runs = sarif_data.get('runs', [])

        if not runs:
            logger.warning("No runs found in SARIF file")
            return 0

        for run in runs:
            tool_info = self._extract_tool_info(run)
            results = run.get('results', [])

            logger.info(f"Processing {len(results)} results from {tool_info['name']}")

            for result in results:
                try:
                    self._process_result(
                        result=result,
                        tool_info=tool_info,
                        scan=scan,
                        organization=organization,
                        repository=repository
                    )
                except Exception as e:
                    error_msg = f"Error processing SARIF result: {e}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                    continue

        logger.info(
            f"SARIF processing complete: {self.findings_created} created, "
            f"{self.findings_updated} updated, {len(self.errors)} errors"
        )

        return self.findings_created

    def _extract_tool_info(self, run: Dict) -> Dict:
        """Extract tool name and version from SARIF run."""
        tool = run.get('tool', {})
        driver = tool.get('driver', {})

        return {
            'name': driver.get('name', 'Unknown'),
            'version': driver.get('version', ''),
            'full_name': driver.get('fullName', ''),
            'organization': driver.get('organization', ''),
        }

    def _process_result(
        self,
        result: Dict,
        tool_info: Dict,
        scan,
        organization,
        repository
    ):
        """
        Process a single SARIF result and create/update Finding.

        SARIF result structure:
        {
            "ruleId": "SEC-001",
            "level": "error",
            "message": { "text": "SQL injection vulnerability" },
            "locations": [ { "physicalLocation": {...} } ]
        }
        """
        # Extract rule ID
        rule_id = result.get('ruleId', 'UNKNOWN')

        # Extract severity
        level = result.get('level', 'warning')
        severity = self.SEVERITY_MAP.get(level, 'medium')

        # Extract message
        message_obj = result.get('message', {})
        message = message_obj.get('text', 'No description available')

        # Extract location (first location if multiple)
        locations = result.get('locations', [])
        if not locations:
            logger.warning(f"No locations found for result {rule_id}, skipping")
            return

        location = locations[0]
        physical_location = location.get('physicalLocation', {})
        artifact_location = physical_location.get('artifactLocation', {})
        region = physical_location.get('region', {})

        file_path = artifact_location.get('uri', 'unknown')
        start_line = region.get('startLine', 1)
        start_column = region.get('startColumn', 1)
        end_line = region.get('endLine')
        end_column = region.get('endColumn')

        # Extract code snippet
        snippet_obj = region.get('snippet', {})
        snippet = snippet_obj.get('text', '')

        # Extract CWE/CVE if available
        cwe_ids, cve_ids = self._extract_cwe_cve(result)

        # Generate fingerprint
        fingerprint = generate_finding_fingerprint(
            rule_id=rule_id,
            file_path=file_path,
            start_line=start_line,
            column=start_column,
            message=message
        )

        # Check for existing finding (deduplication per ADR-002)
        existing_finding = deduplicate_finding(
            fingerprint=fingerprint,
            organization_id=str(organization.id)
        )

        if existing_finding:
            # Update existing finding
            logger.debug(f"Updating existing finding: {fingerprint}")
            existing_finding.update_occurrence(scan)
            self.findings_updated += 1
        else:
            # Create new finding
            logger.debug(f"Creating new finding: {fingerprint}")

            try:
                finding = Finding.objects.create(
                    organization=organization,
                    repository=repository,
                    first_seen_scan=scan,
                    last_seen_scan=scan,
                    fingerprint=fingerprint,
                    rule_id=rule_id,
                    rule_name=self._get_rule_name(result, rule_id),
                    message=message,
                    severity=severity,
                    status='open',
                    file_path=file_path,
                    start_line=start_line,
                    start_column=start_column,
                    end_line=end_line,
                    end_column=end_column,
                    snippet=snippet[:1000] if snippet else None,  # Limit snippet size
                    tool_name=tool_info['name'],
                    tool_version=tool_info['version'],
                    cwe_ids=cwe_ids,
                    cve_ids=cve_ids,
                    sarif_data=result,  # Store full SARIF result for reference
                    occurrence_count=1
                )
                self.findings_created += 1
                logger.debug(f"Created finding {finding.id}")

            except Exception as e:
                logger.error(f"Failed to create finding for {rule_id} in {file_path}: {e}")
                raise

    def _get_rule_name(self, result: Dict, rule_id: str) -> Optional[str]:
        """Extract human-readable rule name from result."""
        # Try to get from message
        message_obj = result.get('message', {})
        if 'text' in message_obj:
            # Some tools include rule name in brackets
            text = message_obj['text']
            if '[' in text and ']' in text:
                return text.split('[')[0].strip()

        # Fall back to rule ID
        return rule_id

    def _extract_cwe_cve(self, result: Dict) -> Tuple[List[str], List[str]]:
        """
        Extract CWE and CVE IDs from SARIF result.

        Returns:
            Tuple of (cwe_ids, cve_ids)
        """
        cwe_ids = []
        cve_ids = []

        # Check properties
        properties = result.get('properties', {})
        if 'tags' in properties:
            tags = properties['tags']
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str):
                        if tag.startswith('CWE-'):
                            cwe_ids.append(tag)
                        elif tag.startswith('CVE-'):
                            cve_ids.append(tag)

        # Check taxa (SARIF 2.1.0 taxonomy references)
        taxa = result.get('taxa', [])
        for taxon in taxa:
            taxon_id = taxon.get('id', '')
            if taxon_id.startswith('CWE-'):
                cwe_ids.append(taxon_id)
            elif taxon_id.startswith('CVE-'):
                cve_ids.append(taxon_id)

        return cwe_ids, cve_ids

    def get_summary(self) -> Dict:
        """
        Get summary of parsing results.

        Returns:
            Dictionary with counts and errors
        """
        return {
            'findings_created': self.findings_created,
            'findings_updated': self.findings_updated,
            'errors': self.errors,
            'error_count': len(self.errors)
        }


def parse_sarif_file(sarif_path: str, scan, organization, repository) -> Dict:
    """
    Convenience function to parse SARIF file and extract findings.

    Args:
        sarif_path: Path to SARIF file
        scan: Scan object
        organization: Organization object
        repository: Repository object

    Returns:
        Summary dictionary with results
    """
    parser = SARIFParser()

    try:
        sarif_data = parser.parse_file(sarif_path)
        parser.extract_findings(sarif_data, scan, organization, repository)
        return parser.get_summary()
    except Exception as e:
        logger.error(f"Failed to parse SARIF file {sarif_path}: {e}")
        return {
            'findings_created': 0,
            'findings_updated': 0,
            'errors': [str(e)],
            'error_count': 1
        }


def parse_sarif_string(sarif_content: str, scan, organization, repository) -> Dict:
    """
    Convenience function to parse SARIF content string and extract findings.

    Args:
        sarif_content: SARIF JSON as string
        scan: Scan object
        organization: Organization object
        repository: Repository object

    Returns:
        Summary dictionary with results
    """
    parser = SARIFParser()

    try:
        sarif_data = parser.parse_string(sarif_content)
        parser.extract_findings(sarif_data, scan, organization, repository)
        return parser.get_summary()
    except Exception as e:
        logger.error(f"Failed to parse SARIF content: {e}")
        return {
            'findings_created': 0,
            'findings_updated': 0,
            'errors': [str(e)],
            'error_count': 1
        }
