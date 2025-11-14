"""
Clustering workflow for semantic grouping of findings.

Generates embeddings and clusters findings for better deduplication
and analysis.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, List

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Django setup
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.findings.models import Finding, FindingCluster, FindingClusterMembership
from apps.scans.models import Scan
from services.embedding_service import EmbeddingService
from services.qdrant_manager import QdrantManager
from services.clustering_service import ClusteringService


@activity.defn
async def generate_embeddings_for_findings(
    scan_id: str,
) -> Dict:
    """
    Generate embeddings for all findings in a scan.

    Args:
        scan_id: UUID of the Scan

    Returns:
        Result dictionary with embedding info
    """
    activity.logger.info(f"Generating embeddings for scan {scan_id}")

    try:
        scan = Scan.objects.get(id=scan_id)

        # Get findings
        findings = Finding.objects.filter(first_seen_scan=scan)
        finding_count = findings.count()

        if finding_count == 0:
            return {
                'success': True,
                'findings_count': 0,
                'message': 'No findings to process',
            }

        activity.logger.info(f"Processing {finding_count} findings")

        # Initialize services
        embedding_service = EmbeddingService()
        qdrant_manager = QdrantManager()

        # Generate embeddings
        finding_ids = []
        embeddings = []
        metadata_list = []

        for finding in findings:
            # Generate embedding
            embedding = embedding_service.embed_finding(
                finding_description=finding.message,
                code_snippet=finding.snippet or "",
                file_path=finding.file_path,
                rule_id=finding.rule_id,
            )

            finding_ids.append(finding.id)
            embeddings.append(embedding)
            metadata_list.append({
                'rule_id': finding.rule_id,
                'severity': finding.severity,
                'tool_name': finding.tool_name,
                'file_path': finding.file_path,
                'organization_id': str(finding.organization_id),
            })

        # Store in Qdrant
        stored_count = qdrant_manager.store_batch(
            finding_ids=finding_ids,
            embeddings=embeddings,
            metadata_list=metadata_list,
        )

        activity.logger.info(
            f"Generated and stored {stored_count} embeddings"
        )

        return {
            'success': True,
            'findings_count': finding_count,
            'embeddings_generated': len(embeddings),
            'embeddings_stored': stored_count,
        }

    except Scan.DoesNotExist:
        activity.logger.error(f"Scan {scan_id} not found")
        return {
            'success': False,
            'error': 'Scan not found',
        }
    except Exception as e:
        activity.logger.error(f"Embedding generation failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
        }


@activity.defn
async def cluster_scan_findings(
    scan_id: str,
    algorithm: str = "dbscan",
    similarity_threshold: float = 0.85,
) -> Dict:
    """
    Cluster findings from a scan.

    Args:
        scan_id: UUID of the Scan
        algorithm: Clustering algorithm
        similarity_threshold: Similarity threshold

    Returns:
        Clustering results
    """
    activity.logger.info(
        f"Clustering findings for scan {scan_id} "
        f"(algorithm: {algorithm}, threshold: {similarity_threshold})"
    )

    try:
        scan = Scan.objects.get(id=scan_id)
        organization = scan.organization

        # Get embeddings from Qdrant
        qdrant_manager = QdrantManager()
        vectors = qdrant_manager.get_all_vectors(
            organization_id=str(organization.id),
            limit=1000,
        )

        if len(vectors) < 2:
            return {
                'success': True,
                'message': 'Not enough findings to cluster',
                'num_clusters': 0,
            }

        # Extract data
        finding_ids = [v['finding_id'] for v in vectors]
        embeddings = [v['vector'] for v in vectors]

        # Cluster
        clustering_service = ClusteringService()
        result = clustering_service.cluster_findings(
            finding_ids=finding_ids,
            embeddings=embeddings,
            algorithm=algorithm,
            similarity_threshold=similarity_threshold,
        )

        # Store clusters in database
        stored_clusters = store_clusters(
            organization=organization,
            clusters=result['clusters'],
            embeddings=embeddings,
            finding_ids=finding_ids,
            algorithm=algorithm,
            similarity_threshold=similarity_threshold,
            clustering_service=clustering_service,
        )

        activity.logger.info(
            f"Created {stored_clusters} clusters in database"
        )

        return {
            'success': True,
            'num_clusters': result['num_clusters'],
            'noise_points': result['noise_points'],
            'silhouette_score': result['silhouette_score'],
            'stored_clusters': stored_clusters,
            'cluster_sizes': result['cluster_sizes'],
        }

    except Scan.DoesNotExist:
        activity.logger.error(f"Scan {scan_id} not found")
        return {
            'success': False,
            'error': 'Scan not found',
        }
    except Exception as e:
        activity.logger.error(f"Clustering failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
        }


def store_clusters(
    organization,
    clusters: Dict,
    embeddings: List,
    finding_ids: List,
    algorithm: str,
    similarity_threshold: float,
    clustering_service: ClusteringService,
) -> int:
    """Store clusters in database."""
    stored_count = 0

    # Create mapping of finding_id to embedding
    id_to_embedding = dict(zip(finding_ids, embeddings))

    for cluster_label, cluster_finding_ids in clusters.items():
        # Get embeddings for this cluster
        cluster_embeddings = [
            id_to_embedding[fid] for fid in cluster_finding_ids
        ]

        # Calculate statistics
        stats = clustering_service.calculate_cluster_statistics(
            cluster_embeddings
        )

        # Identify representative finding
        cluster_finding_objs = []
        for fid in cluster_finding_ids:
            try:
                cluster_finding_objs.append(Finding.objects.get(id=fid))
            except Finding.DoesNotExist:
                continue

        if not cluster_finding_objs:
            continue

        # Use first finding as representative (could be improved)
        representative = cluster_finding_objs[0]

        # Create cluster
        cluster = FindingCluster.objects.create(
            organization=organization,
            cluster_label=cluster_label,
            representative_finding=representative,
            size=len(cluster_finding_ids),
            avg_similarity=stats.get('avg_pairwise_similarity', 0.0),
            cohesion_score=stats.get('cohesion_score', 0.0),
            algorithm=algorithm,
            similarity_threshold=similarity_threshold,
            primary_rule_id=representative.rule_id,
            primary_severity=representative.severity,
            primary_tool=representative.tool_name,
            statistics=stats,
        )

        # Create memberships
        for finding_obj in cluster_finding_objs:
            FindingClusterMembership.objects.create(
                finding=finding_obj,
                cluster=cluster,
                distance_to_centroid=0.0,  # Could calculate actual distance
            )

        stored_count += 1

    return stored_count


@workflow.defn
class ClusterFindingsWorkflow:
    """
    Workflow for clustering findings using semantic embeddings.

    Steps:
    1. Generate embeddings for findings
    2. Store embeddings in Qdrant
    3. Cluster findings using similarity
    4. Store clusters in database
    """

    @workflow.run
    async def run(
        self,
        scan_id: str,
        algorithm: str = "dbscan",
        similarity_threshold: float = 0.85,
    ) -> Dict:
        """
        Execute clustering workflow.

        Args:
            scan_id: UUID of scan to cluster
            algorithm: Clustering algorithm
            similarity_threshold: Similarity threshold

        Returns:
            Workflow result
        """
        workflow.logger.info(
            f"Starting clustering workflow for scan {scan_id}"
        )

        # Step 1: Generate embeddings
        embedding_result = await workflow.execute_activity(
            generate_embeddings_for_findings,
            args=[scan_id],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        if not embedding_result.get('success'):
            return {
                'success': False,
                'error': f"Embedding generation failed: {embedding_result.get('error')}",
            }

        workflow.logger.info(
            f"Generated {embedding_result.get('embeddings_generated', 0)} embeddings"
        )

        # Step 2: Cluster findings
        clustering_result = await workflow.execute_activity(
            cluster_scan_findings,
            args=[scan_id, algorithm, similarity_threshold],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        if not clustering_result.get('success'):
            return {
                'success': False,
                'error': f"Clustering failed: {clustering_result.get('error')}",
            }

        workflow.logger.info(
            f"Created {clustering_result.get('num_clusters', 0)} clusters"
        )

        return {
            'success': True,
            'scan_id': scan_id,
            'findings_count': embedding_result.get('findings_count', 0),
            'embeddings_generated': embedding_result.get('embeddings_generated', 0),
            'num_clusters': clustering_result.get('num_clusters', 0),
            'noise_points': clustering_result.get('noise_points', 0),
            'silhouette_score': clustering_result.get('silhouette_score'),
            'cluster_sizes': clustering_result.get('cluster_sizes', {}),
        }
