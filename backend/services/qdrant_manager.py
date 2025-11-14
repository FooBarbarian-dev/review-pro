"""
Qdrant manager for vector storage and semantic search.

Manages collections, stores embeddings, and performs similarity searches.
"""

import logging
import os
from typing import Dict, List, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    SearchRequest,
    Filter,
    FieldCondition,
    MatchValue,
)

logger = logging.getLogger(__name__)


class QdrantManager:
    """
    Manager for Qdrant vector database operations.

    Handles:
    - Collection creation and management
    - Vector storage (findings embeddings)
    - Semantic similarity search
    - Clustering support
    """

    COLLECTION_NAME = "findings"
    VECTOR_SIZE = 1536  # text-embedding-3-small dimensions

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize Qdrant manager.

        Args:
            host: Qdrant host (default: from env or localhost)
            port: Qdrant port (default: 6333)
        """
        self.host = host or os.environ.get('QDRANT_HOST', 'localhost')
        self.port = port or int(os.environ.get('QDRANT_PORT', '6333'))

        self.client = QdrantClient(host=self.host, port=self.port)

        logger.info(f"Initialized Qdrant manager: {self.host}:{self.port}")

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the findings collection exists."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.COLLECTION_NAME for c in collections)

            if not exists:
                logger.info(f"Creating collection: {self.COLLECTION_NAME}")
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Collection created successfully")
            else:
                logger.debug(f"Collection already exists: {self.COLLECTION_NAME}")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}", exc_info=True)
            raise

    def store_finding_embedding(
        self,
        finding_id: UUID,
        embedding: List[float],
        metadata: Dict,
    ) -> bool:
        """
        Store a finding's embedding in Qdrant.

        Args:
            finding_id: UUID of the finding
            embedding: Embedding vector
            metadata: Additional metadata (severity, rule_id, etc.)

        Returns:
            True if successful
        """
        try:
            point = PointStruct(
                id=str(finding_id),
                vector=embedding,
                payload={
                    'finding_id': str(finding_id),
                    'rule_id': metadata.get('rule_id'),
                    'severity': metadata.get('severity'),
                    'tool_name': metadata.get('tool_name'),
                    'file_path': metadata.get('file_path'),
                    'organization_id': metadata.get('organization_id'),
                },
            )

            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point],
            )

            logger.debug(f"Stored embedding for finding {finding_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to store embedding for {finding_id}: {e}",
                exc_info=True
            )
            return False

    def store_batch(
        self,
        finding_ids: List[UUID],
        embeddings: List[List[float]],
        metadata_list: List[Dict],
    ) -> int:
        """
        Store multiple embeddings in batch.

        Args:
            finding_ids: List of finding UUIDs
            embeddings: List of embedding vectors
            metadata_list: List of metadata dicts

        Returns:
            Number of successfully stored embeddings
        """
        points = []

        for finding_id, embedding, metadata in zip(
            finding_ids, embeddings, metadata_list
        ):
            point = PointStruct(
                id=str(finding_id),
                vector=embedding,
                payload={
                    'finding_id': str(finding_id),
                    'rule_id': metadata.get('rule_id'),
                    'severity': metadata.get('severity'),
                    'tool_name': metadata.get('tool_name'),
                    'file_path': metadata.get('file_path'),
                    'organization_id': metadata.get('organization_id'),
                },
            )
            points.append(point)

        try:
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
            )

            logger.info(f"Stored {len(points)} embeddings in batch")
            return len(points)

        except Exception as e:
            logger.error(f"Batch upsert failed: {e}", exc_info=True)
            return 0

    def find_similar(
        self,
        embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        organization_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Find similar findings using vector search.

        Args:
            embedding: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            organization_id: Filter by organization (optional)

        Returns:
            List of similar findings with scores
        """
        try:
            # Build filter
            filter_conditions = None
            if organization_id:
                filter_conditions = Filter(
                    must=[
                        FieldCondition(
                            key="organization_id",
                            match=MatchValue(value=organization_id),
                        )
                    ]
                )

            # Search
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_conditions,
            )

            # Format results
            similar_findings = []
            for result in results:
                similar_findings.append({
                    'finding_id': result.payload['finding_id'],
                    'score': result.score,
                    'rule_id': result.payload.get('rule_id'),
                    'severity': result.payload.get('severity'),
                    'tool_name': result.payload.get('tool_name'),
                    'file_path': result.payload.get('file_path'),
                })

            logger.info(
                f"Found {len(similar_findings)} similar findings "
                f"(threshold: {score_threshold})"
            )

            return similar_findings

        except Exception as e:
            logger.error(f"Similarity search failed: {e}", exc_info=True)
            return []

    def get_all_vectors(
        self,
        organization_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict]:
        """
        Get all vectors from collection.

        Args:
            organization_id: Filter by organization
            limit: Maximum number of vectors

        Returns:
            List of vectors with metadata
        """
        try:
            # Build filter
            filter_conditions = None
            if organization_id:
                filter_conditions = Filter(
                    must=[
                        FieldCondition(
                            key="organization_id",
                            match=MatchValue(value=organization_id),
                        )
                    ]
                )

            # Scroll through collection
            records, _ = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                limit=limit,
                with_vectors=True,
                with_payload=True,
                scroll_filter=filter_conditions,
            )

            vectors = []
            for record in records:
                vectors.append({
                    'finding_id': record.payload['finding_id'],
                    'vector': record.vector,
                    'metadata': record.payload,
                })

            logger.info(f"Retrieved {len(vectors)} vectors")
            return vectors

        except Exception as e:
            logger.error(f"Failed to get vectors: {e}", exc_info=True)
            return []

    def delete_finding(self, finding_id: UUID) -> bool:
        """
        Delete a finding's embedding.

        Args:
            finding_id: UUID of finding to delete

        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[str(finding_id)],
            )

            logger.debug(f"Deleted embedding for finding {finding_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}", exc_info=True)
            return False

    def get_collection_info(self) -> Dict:
        """
        Get information about the collection.

        Returns:
            Collection information dictionary
        """
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)

            return {
                'name': info.config.params.vectors.size,
                'vectors_count': info.vectors_count,
                'indexed_vectors_count': info.indexed_vectors_count,
                'points_count': info.points_count,
                'segments_count': info.segments_count,
                'status': info.status,
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}", exc_info=True)
            return {}
