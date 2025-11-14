"""
Embedding service for generating vector representations of findings.

Uses OpenAI's text-embedding-3-small model for cost-effective embeddings.
Embeddings are used for semantic similarity and clustering.
"""

import hashlib
import logging
from typing import List, Optional

import openai
from django.core.cache import cache

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings from text.

    Uses OpenAI's text-embedding-3-small (1536 dimensions) for:
    - Semantic similarity search
    - Finding clustering
    - Duplicate detection
    - RAG (Retrieval Augmented Generation)
    """

    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536  # Output dimensions
    CACHE_TTL = 86400 * 7  # 7 days

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key (optional, uses env var if not provided)
        """
        self.client = openai.OpenAI(api_key=api_key)
        logger.info(f"Initialized embedding service with model: {self.MODEL}")

    def embed_finding(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        rule_id: str,
    ) -> List[float]:
        """
        Generate embedding for a security finding.

        Combines multiple fields into a single embedding that captures
        the semantic meaning of the finding.

        Args:
            finding_description: Description of the security issue
            code_snippet: Code context
            file_path: Path to file
            rule_id: Rule ID from SA tool

        Returns:
            List of floats (embedding vector)
        """
        # Construct text representation
        text = self._construct_finding_text(
            finding_description, code_snippet, file_path, rule_id
        )

        # Check cache
        cache_key = self._get_cache_key(text)
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for embedding: {rule_id}")
            return cached

        # Generate embedding
        try:
            response = self.client.embeddings.create(
                model=self.MODEL,
                input=text,
                encoding_format="float",
            )

            embedding = response.data[0].embedding

            # Cache the result
            cache.set(cache_key, embedding, self.CACHE_TTL)

            logger.debug(
                f"Generated embedding for {rule_id}: {len(embedding)} dimensions"
            )

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            raise

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.client.embeddings.create(
                    model=self.MODEL,
                    input=batch,
                    encoding_format="float",
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                logger.info(
                    f"Generated {len(batch_embeddings)} embeddings "
                    f"(batch {i // batch_size + 1})"
                )

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}", exc_info=True)
                # Return empty vectors for failed items
                embeddings.extend([[0.0] * self.DIMENSIONS] * len(batch))

        return embeddings

    def _construct_finding_text(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        rule_id: str,
    ) -> str:
        """
        Construct text representation for embedding.

        Combines key fields in a structured format that captures
        the semantic meaning of the finding.

        Args:
            finding_description: Description of issue
            code_snippet: Code context
            file_path: File path
            rule_id: Rule ID

        Returns:
            Text representation
        """
        # Extract file type from path
        file_ext = file_path.split('.')[-1] if '.' in file_path else 'unknown'

        # Construct structured text
        text_parts = [
            f"Rule: {rule_id}",
            f"File type: {file_ext}",
            f"Description: {finding_description}",
        ]

        # Add code snippet if available (truncate to avoid token limits)
        if code_snippet:
            # Truncate to ~500 characters to stay within embedding limits
            truncated_code = code_snippet[:500]
            text_parts.append(f"Code: {truncated_code}")

        return "\n".join(text_parts)

    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key for text.

        Args:
            text: Text to cache

        Returns:
            Cache key
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{self.MODEL}:{text_hash}"

    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0.0 to 1.0)
        """
        import numpy as np

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Convert to 0-1 range (cosine similarity is -1 to 1)
        return float((similarity + 1) / 2)
