"""
Django management command to cluster findings semantically.

Usage:
    # Cluster findings from a scan
    python manage.py cluster_findings --scan-id <uuid>

    # Use different algorithm
    python manage.py cluster_findings --scan-id <uuid> --algorithm agglomerative

    # Adjust similarity threshold
    python manage.py cluster_findings --scan-id <uuid> --threshold 0.90
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from temporalio.client import Client

from apps.scans.models import Scan
from workflows.clustering_workflow import ClusterFindingsWorkflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cluster findings using semantic embeddings and vector similarity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scan-id',
            type=str,
            required=True,
            help='Scan ID to cluster findings from',
        )
        parser.add_argument(
            '--algorithm',
            type=str,
            default='dbscan',
            choices=['dbscan', 'agglomerative'],
            help='Clustering algorithm (default: dbscan)',
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.85,
            help='Similarity threshold 0.0-1.0 (default: 0.85)',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        scan_id = options['scan_id']
        algorithm = options['algorithm']
        threshold = options['threshold']

        # Verify scan exists
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Error: Scan {scan_id} not found')
            )
            return

        self.stdout.write(
            self.style.WARNING('Clustering findings...')
        )
        self.stdout.write(f'  Scan ID: {scan_id}')
        self.stdout.write(f'  Algorithm: {algorithm}')
        self.stdout.write(f'  Threshold: {threshold}')

        try:
            # Run workflow
            result = asyncio.run(
                self.run_clustering_workflow(
                    scan_id=scan_id,
                    algorithm=algorithm,
                    threshold=threshold,
                )
            )

            if result.get('success'):
                self.stdout.write(self.style.SUCCESS('\n✓ Clustering completed!'))

                self.stdout.write(f'\nEmbeddings:')
                self.stdout.write(f'  Findings processed: {result.get("findings_count", 0)}')
                self.stdout.write(f'  Embeddings generated: {result.get("embeddings_generated", 0)}')

                self.stdout.write(f'\nClusters:')
                self.stdout.write(f'  Number of clusters: {result.get("num_clusters", 0)}')
                self.stdout.write(f'  Noise points: {result.get("noise_points", 0)}')

                silhouette = result.get('silhouette_score')
                if silhouette is not None:
                    self.stdout.write(f'  Silhouette score: {silhouette:.3f}')
                    self.stdout.write(f'    (Quality: {self._interpret_silhouette(silhouette)})')

                # Show cluster sizes
                cluster_sizes = result.get('cluster_sizes', {})
                if cluster_sizes:
                    self.stdout.write(f'\nCluster Sizes:')
                    for cluster_id, size in sorted(
                        cluster_sizes.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]:  # Show top 10
                        self.stdout.write(f'  {cluster_id}: {size} findings')

                    if len(cluster_sizes) > 10:
                        self.stdout.write(f'  ... and {len(cluster_sizes) - 10} more')

                self.stdout.write(f'\nAnalysis:')
                total = result.get('findings_count', 0)
                clusters = result.get('num_clusters', 0)
                if total > 0 and clusters > 0:
                    dedup_rate = (1 - clusters / total) * 100
                    self.stdout.write(
                        f'  Potential deduplication: {dedup_rate:.1f}% '
                        f'({total} findings → {clusters} clusters)'
                    )

                self.stdout.write(f'\nView clusters in Django admin:')
                self.stdout.write(f'  http://localhost:8000/admin/findings/findingcluster/')

            else:
                self.stdout.write(
                    self.style.ERROR(f'\n✗ Clustering failed: {result.get("error")}')
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Clustering failed: {e}'))
            logger.error(f"Clustering failed: {e}", exc_info=True)
            raise

    async def run_clustering_workflow(
        self,
        scan_id: str,
        algorithm: str,
        threshold: float,
    ) -> dict:
        """
        Execute the clustering workflow.

        Args:
            scan_id: UUID of the scan
            algorithm: Clustering algorithm
            threshold: Similarity threshold

        Returns:
            Workflow result dictionary
        """
        self.stdout.write('\nConnecting to Temporal server...')
        client = await Client.connect('localhost:7233')

        self.stdout.write('Starting clustering workflow...')
        self.stdout.write('  (This may take several minutes)')
        self.stdout.write('  Watch progress in Temporal UI: http://localhost:8233\n')

        result = await client.execute_workflow(
            ClusterFindingsWorkflow.run,
            args=[scan_id, algorithm, threshold],
            id=f'cluster-{scan_id}',
            task_queue='code-analysis',
        )

        return result

    def _interpret_silhouette(self, score: float) -> str:
        """Interpret silhouette score."""
        if score >= 0.7:
            return "Excellent"
        elif score >= 0.5:
            return "Good"
        elif score >= 0.25:
            return "Fair"
        else:
            return "Poor"
