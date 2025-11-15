"""
Celery tasks for scan operations.
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_quota_usage(organization_id, scan_id=None):
    """
    Update quota usage for an organization.
    """
    from .models import QuotaUsage, Scan
    from apps.organizations.models import Organization

    try:
        organization = Organization.objects.get(id=organization_id)
        now = timezone.now()

        # Get or create quota usage for current month
        quota, created = QuotaUsage.objects.get_or_create(
            organization=organization,
            year=now.year,
            month=now.month,
            defaults={'scans_used': 0, 'storage_used_bytes': 0}
        )

        # Update scan count
        if scan_id:
            quota.scans_used += 1

        # Calculate total storage used
        total_storage = Scan.objects.filter(
            organization=organization,
            sarif_file_size__isnull=False
        ).aggregate(models.Sum('sarif_file_size'))['sarif_file_size__sum'] or 0

        quota.storage_used_bytes = total_storage
        quota.save()

        logger.info(f"Updated quota usage for {organization.name}: {quota.scans_used} scans, {quota.storage_used_gb:.2f} GB")

    except Exception as e:
        logger.error(f"Error updating quota usage: {e}")
        raise


@shared_task
def run_security_scan(scan_id):
    """
    Execute a security scan in a Docker container (ADR-004).

    Complete implementation:
    1. Create ephemeral GitHub App token (15 min expiry)
    2. Start Docker container with security tools
    3. Run scan and collect SARIF output
    4. Upload SARIF to S3
    5. Parse SARIF and create findings
    6. Update scan status and quota
    """
    from .models import Scan, ScanLog
    from .github_app import get_github_app
    from .storage import get_storage
    from .sarif_parser import SARIFParser
    from .events import publish_status_change, publish_progress, publish_log, publish_scan_completed, publish_scan_failed, publish_finding_discovered
    from django.conf import settings
    import docker
    import json
    import time

    scan = None
    start_time = time.time()

    try:
        # Load scan with related objects
        scan = Scan.objects.select_related(
            'organization', 'repository', 'branch'
        ).get(id=scan_id)

        _log_scan(scan, 'info', 'Scan worker started')
        scan.status = 'running'
        scan.started_at = timezone.now()
        scan.save(update_fields=['status', 'started_at'])

        # Publish status change event
        publish_status_change(str(scan_id), 'running', 'Scan worker started')
        publish_progress(str(scan_id), 'initializing', 0, 6, 'Starting scan')

        # Step 1: Generate ephemeral GitHub App token
        _log_scan(scan, 'info', 'Generating GitHub App token')
        publish_progress(str(scan_id), 'authentication', 1, 6, 'Generating GitHub token')
        try:
            github_app = get_github_app()
            token_data = github_app.generate_installation_token(
                repositories=[scan.repository.name],
                permissions={'contents': 'read'}
            )
            github_token = token_data['token']
            _log_scan(
                scan, 'info',
                f"GitHub token generated (expires at {token_data['expires_at']})"
            )
            publish_log(str(scan_id), 'info', 'GitHub authentication successful')
        except Exception as e:
            raise Exception(f"Failed to generate GitHub token: {e}")

        # Step 2: Start Docker container with security tools
        _log_scan(scan, 'info', f"Starting Docker container: {settings.WORKER_DOCKER_IMAGE}")
        publish_progress(str(scan_id), 'container', 2, 6, 'Starting security scanner')

        try:
            docker_client = docker.from_env()

            # Prepare environment variables for container
            container_env = {
                'GITHUB_TOKEN': github_token,
                'REPO_URL': f'https://github.com/{scan.repository.full_name}',
                'REPO_NAME': scan.repository.full_name,
                'BRANCH': scan.branch.name,
                'COMMIT_SHA': scan.branch.sha,
                'SCAN_ID': str(scan.id)
            }

            # Run container with security constraints (ADR-004)
            container = docker_client.containers.run(
                image=settings.WORKER_DOCKER_IMAGE,
                environment=container_env,
                mem_limit=getattr(settings, 'WORKER_MEMORY_LIMIT', '2g'),
                cpu_count=getattr(settings, 'WORKER_CPU_LIMIT', 2),
                network_mode='bridge',  # Allow network for git clone
                detach=True,
                remove=False,  # Keep for log collection
                stdout=True,
                stderr=True
            )

            _log_scan(scan, 'info', f'Container started: {container.short_id}')
            publish_log(str(scan_id), 'info', f'Scanning {scan.repository.full_name}:{scan.branch.name}')

        except docker.errors.ImageNotFound:
            raise Exception(f"Docker image not found: {settings.WORKER_DOCKER_IMAGE}")
        except docker.errors.APIError as e:
            raise Exception(f"Docker API error: {e}")

        # Step 3: Wait for container completion with timeout
        _log_scan(scan, 'info', 'Waiting for scan to complete')
        publish_progress(str(scan_id), 'scanning', 3, 6, 'Running security analysis')

        try:
            timeout = getattr(settings, 'WORKER_TIMEOUT', 1800)  # 30 min default
            result = container.wait(timeout=timeout)
            exit_code = result.get('StatusCode', -1)

            if exit_code != 0:
                # Get container logs for debugging
                logs = container.logs().decode('utf-8', errors='replace')
                _log_scan(scan, 'error', f'Container exited with code {exit_code}')
                _log_scan(scan, 'error', f'Container logs:\n{logs[:1000]}')
                publish_log(str(scan_id), 'error', f'Scanner failed with exit code {exit_code}')
                raise Exception(f"Scan failed with exit code {exit_code}")

            _log_scan(scan, 'info', 'Scan completed successfully')
            publish_log(str(scan_id), 'success', 'Security analysis completed')

        except docker.errors.APIError as e:
            raise Exception(f"Container execution error: {e}")

        # Step 4: Collect SARIF output from container
        _log_scan(scan, 'info', 'Collecting SARIF output')

        try:
            # Get container logs (SARIF should be in stdout)
            sarif_output = container.logs().decode('utf-8', errors='replace')

            # Try to find SARIF JSON in output
            # Expected format: Worker outputs SARIF to stdout
            sarif_content = _extract_sarif_from_output(sarif_output)

            if not sarif_content:
                raise Exception("No SARIF output found in container logs")

            # Validate it's valid JSON
            sarif_data = json.loads(sarif_content)
            _log_scan(scan, 'info', f'SARIF collected ({len(sarif_content)} bytes)')

        except json.JSONDecodeError as e:
            raise Exception(f"Invalid SARIF JSON: {e}")
        except Exception as e:
            raise Exception(f"Failed to collect SARIF: {e}")
        finally:
            # Cleanup container
            try:
                container.remove(force=True)
                _log_scan(scan, 'info', 'Container cleaned up')
            except:
                pass

        # Step 5: Upload SARIF to S3
        _log_scan(scan, 'info', 'Uploading SARIF to S3')
        publish_progress(str(scan_id), 'uploading', 4, 6, 'Storing scan results')

        try:
            storage = get_storage()
            s3_path, file_size = storage.upload_sarif(
                scan_id=str(scan.id),
                sarif_content=sarif_content,
                organization_id=str(scan.organization.id),
                repository_id=str(scan.repository.id)
            )

            scan.sarif_file_path = s3_path
            scan.sarif_file_size = file_size
            scan.save(update_fields=['sarif_file_path', 'sarif_file_size'])

            _log_scan(scan, 'info', f'SARIF uploaded to {s3_path}')
            publish_log(str(scan_id), 'info', f'SARIF file stored ({file_size} bytes)')

        except Exception as e:
            # Non-fatal: continue with finding extraction
            _log_scan(scan, 'error', f'Failed to upload SARIF: {e}')

        # Step 6: Parse SARIF and create findings
        _log_scan(scan, 'info', 'Parsing SARIF and extracting findings')
        publish_progress(str(scan_id), 'parsing', 5, 6, 'Extracting security findings')

        try:
            parser = SARIFParser()
            # Pass scan_id for event publishing
            parser.scan_id = str(scan_id)
            parser.extract_findings(
                sarif_data=sarif_data,
                scan=scan,
                organization=scan.organization,
                repository=scan.repository
            )

            summary = parser.get_summary()
            findings_count = summary['findings_created'] + summary['findings_updated']

            scan.findings_count = findings_count
            scan.save(update_fields=['findings_count'])

            _log_scan(
                scan, 'success',
                f"Found {summary['findings_created']} new findings, "
                f"updated {summary['findings_updated']} existing"
            )
            publish_log(
                str(scan_id), 'success',
                f"Discovered {findings_count} security findings"
            )

            if summary['errors']:
                _log_scan(
                    scan, 'warning',
                    f"Encountered {len(summary['errors'])} errors during parsing"
                )
                publish_log(
                    str(scan_id), 'warning',
                    f"Encountered {len(summary['errors'])} parsing errors"
                )

        except Exception as e:
            raise Exception(f"Failed to parse SARIF: {e}")

        # Step 7: Mark scan as completed
        scan.status = 'completed'
        scan.completed_at = timezone.now()
        scan.save(update_fields=['status', 'completed_at'])

        duration = time.time() - start_time
        _log_scan(scan, 'success', 'Scan completed successfully')
        logger.info(f"Scan {scan_id} completed: {findings_count} findings in {duration:.1f}s")

        # Publish completion event
        publish_progress(str(scan_id), 'completed', 6, 6, 'Scan complete')
        publish_scan_completed(str(scan_id), findings_count, duration)

        # Step 8: Update quota usage
        update_quota_usage.delay(str(scan.organization.id), str(scan.id))

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Scan {scan_id} failed: {error_msg}")

        if scan:
            try:
                scan.status = 'failed'
                scan.error_message = error_msg[:1000]  # Limit error message length
                scan.completed_at = timezone.now()
                scan.save(update_fields=['status', 'error_message', 'completed_at'])
                _log_scan(scan, 'error', f'Scan failed: {error_msg}')

                # Publish failure event
                publish_scan_failed(str(scan_id), error_msg[:500])
            except:
                pass

        raise


def _log_scan(scan, level, message):
    """Helper to create scan log entry."""
    from .models import ScanLog

    try:
        ScanLog.objects.create(
            scan=scan,
            level=level,
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to create scan log: {e}")


def _extract_sarif_from_output(output):
    """
    Extract SARIF JSON from container output.

    Worker container should output SARIF to stdout.
    Handles cases where there's extra logging before/after SARIF.
    """
    # Try to find JSON object in output
    # Look for SARIF markers
    sarif_start_markers = [
        '{"version":"2.1.0"',
        '{"$schema":"',
        '{"runs":'
    ]

    for marker in sarif_start_markers:
        if marker in output:
            start_idx = output.find(marker)
            # Find matching closing brace
            # Simple approach: take everything from start to end
            # Better approach: proper JSON extraction
            potential_json = output[start_idx:]

            # Try to parse
            try:
                # Find the end of JSON (look for last })
                brace_count = 0
                json_end = 0
                for i, char in enumerate(potential_json):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    sarif_json = potential_json[:json_end]
                    # Validate it's valid JSON
                    json.loads(sarif_json)
                    return sarif_json

            except (json.JSONDecodeError, ValueError):
                continue

    # If no SARIF markers found, try to parse entire output as JSON
    try:
        json.loads(output)
        return output
    except json.JSONDecodeError:
        pass

    return None
