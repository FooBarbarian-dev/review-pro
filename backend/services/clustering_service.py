"""
Semantic clustering service for grouping similar findings.

Uses vector embeddings and clustering algorithms to identify groups
of similar security findings for better deduplication and analysis.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


class ClusteringService:
    """
    Service for clustering findings based on semantic similarity.

    Supports multiple clustering algorithms:
    - DBSCAN: Density-based clustering (good for varying cluster sizes)
    - Agglomerative: Hierarchical clustering (good for tree-like structures)
    """

    def __init__(self):
        """Initialize clustering service."""
        logger.info("Initialized clustering service")

    def cluster_findings(
        self,
        finding_ids: List[UUID],
        embeddings: List[List[float]],
        algorithm: str = "dbscan",
        similarity_threshold: float = 0.85,
    ) -> Dict:
        """
        Cluster findings based on embeddings.

        Args:
            finding_ids: List of finding UUIDs
            embeddings: List of embedding vectors
            algorithm: Clustering algorithm (dbscan, agglomerative)
            similarity_threshold: Similarity threshold for clustering (0.0-1.0)

        Returns:
            Dictionary with cluster assignments and statistics
        """
        if len(finding_ids) < 2:
            logger.warning("Need at least 2 findings to cluster")
            return {
                'clusters': {},
                'num_clusters': 0,
                'noise_points': len(finding_ids),
                'silhouette_score': None,
            }

        logger.info(
            f"Clustering {len(finding_ids)} findings "
            f"(algorithm: {algorithm}, threshold: {similarity_threshold})"
        )

        # Convert to numpy array
        X = np.array(embeddings)

        # Run clustering
        if algorithm == "dbscan":
            labels = self._cluster_dbscan(X, similarity_threshold)
        elif algorithm == "agglomerative":
            labels = self._cluster_agglomerative(X, similarity_threshold)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Build cluster mapping
        clusters = {}
        for finding_id, label in zip(finding_ids, labels):
            if label == -1:  # Noise point
                continue

            cluster_id = f"cluster_{label}"
            if cluster_id not in clusters:
                clusters[cluster_id] = []

            clusters[cluster_id].append(str(finding_id))

        # Count noise points (label -1)
        noise_points = sum(1 for label in labels if label == -1)

        # Calculate silhouette score (if we have clusters)
        silhouette = None
        if len(set(labels)) > 1 and len(set(labels)) < len(labels):
            try:
                silhouette = float(silhouette_score(X, labels))
            except:
                pass

        num_clusters = len(clusters)

        logger.info(
            f"Clustering complete: {num_clusters} clusters, "
            f"{noise_points} noise points, "
            f"silhouette: {silhouette:.3f if silhouette else 'N/A'}"
        )

        return {
            'clusters': clusters,
            'num_clusters': num_clusters,
            'noise_points': noise_points,
            'silhouette_score': silhouette,
            'cluster_sizes': {
                cluster_id: len(members)
                for cluster_id, members in clusters.items()
            },
        }

    def _cluster_dbscan(
        self,
        X: np.ndarray,
        similarity_threshold: float,
    ) -> np.ndarray:
        """
        Cluster using DBSCAN (Density-Based Spatial Clustering).

        Args:
            X: Feature matrix (embeddings)
            similarity_threshold: Similarity threshold

        Returns:
            Cluster labels
        """
        # Convert similarity threshold to distance
        # For cosine distance: distance = 1 - similarity
        eps = 1.0 - similarity_threshold

        # DBSCAN parameters
        # eps: Maximum distance between samples in a cluster
        # min_samples: Minimum samples in a neighborhood to form cluster
        clusterer = DBSCAN(
            eps=eps,
            min_samples=2,
            metric='cosine',
            n_jobs=-1,
        )

        labels = clusterer.fit_predict(X)

        return labels

    def _cluster_agglomerative(
        self,
        X: np.ndarray,
        similarity_threshold: float,
    ) -> np.ndarray:
        """
        Cluster using Agglomerative (Hierarchical) Clustering.

        Args:
            X: Feature matrix (embeddings)
            similarity_threshold: Similarity threshold

        Returns:
            Cluster labels
        """
        # Convert similarity to distance threshold
        distance_threshold = 1.0 - similarity_threshold

        clusterer = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric='cosine',
            linkage='average',
        )

        labels = clusterer.fit_predict(X)

        return labels

    def identify_cluster_representative(
        self,
        cluster_embeddings: List[List[float]],
        cluster_finding_ids: List[UUID],
    ) -> UUID:
        """
        Identify the most representative finding in a cluster.

        Uses the finding closest to the cluster centroid.

        Args:
            cluster_embeddings: Embeddings for findings in cluster
            cluster_finding_ids: Finding IDs in cluster

        Returns:
            UUID of representative finding
        """
        if len(cluster_finding_ids) == 1:
            return cluster_finding_ids[0]

        # Calculate centroid
        X = np.array(cluster_embeddings)
        centroid = np.mean(X, axis=0)

        # Find closest point to centroid
        distances = np.linalg.norm(X - centroid, axis=1)
        closest_idx = np.argmin(distances)

        return cluster_finding_ids[closest_idx]

    def calculate_cluster_statistics(
        self,
        cluster_embeddings: List[List[float]],
    ) -> Dict:
        """
        Calculate statistics for a cluster.

        Args:
            cluster_embeddings: Embeddings for findings in cluster

        Returns:
            Statistics dictionary
        """
        if not cluster_embeddings:
            return {}

        X = np.array(cluster_embeddings)

        # Calculate centroid
        centroid = np.mean(X, axis=0)

        # Calculate average distance to centroid (cohesion)
        distances = np.linalg.norm(X - centroid, axis=1)
        avg_distance = float(np.mean(distances))
        std_distance = float(np.std(distances))

        # Calculate pairwise similarities
        similarities = []
        for i in range(len(X)):
            for j in range(i + 1, len(X)):
                # Cosine similarity
                dot_product = np.dot(X[i], X[j])
                norm_i = np.linalg.norm(X[i])
                norm_j = np.linalg.norm(X[j])

                if norm_i > 0 and norm_j > 0:
                    similarity = dot_product / (norm_i * norm_j)
                    similarities.append(similarity)

        avg_similarity = float(np.mean(similarities)) if similarities else 0.0
        min_similarity = float(np.min(similarities)) if similarities else 0.0
        max_similarity = float(np.max(similarities)) if similarities else 0.0

        return {
            'cluster_size': len(X),
            'avg_distance_to_centroid': avg_distance,
            'std_distance_to_centroid': std_distance,
            'avg_pairwise_similarity': avg_similarity,
            'min_pairwise_similarity': min_similarity,
            'max_pairwise_similarity': max_similarity,
            'cohesion_score': 1.0 - avg_distance,  # Higher is better
        }
