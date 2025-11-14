"""
Finding models implementing deduplication strategy (ADR-002).
Normalized data from SARIF files.
"""
import uuid
import hashlib
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Organization, Repository
from apps.scans.models import Scan


class Finding(models.Model):
    """
    Security finding from a scan.
    Implements deduplication via fingerprint (ADR-002).
    """
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('fixed', 'Fixed'),
        ('false_positive', 'False Positive'),
        ('accepted_risk', 'Accepted Risk'),
        ('wont_fix', 'Won\'t Fix'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='findings',
        db_index=True
    )
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='findings'
    )
    first_seen_scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name='findings_first_seen'
    )
    last_seen_scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name='findings_last_seen'
    )

    # Deduplication fingerprint (ADR-002)
    # Generated from: rule_id + file_path + start_line + start_column + message_hash
    fingerprint = models.CharField(max_length=64, db_index=True)

    # Finding details
    rule_id = models.CharField(max_length=255, db_index=True)
    rule_name = models.CharField(max_length=512, blank=True, null=True)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)

    # Location information
    file_path = models.CharField(max_length=1024)
    start_line = models.IntegerField()
    start_column = models.IntegerField(default=1)
    end_line = models.IntegerField(blank=True, null=True)
    end_column = models.IntegerField(blank=True, null=True)

    # Code snippet
    snippet = models.TextField(blank=True, null=True)

    # Tool information
    tool_name = models.CharField(max_length=255)
    tool_version = models.CharField(max_length=100, blank=True, null=True)

    # CWE/CVE information
    cwe_ids = models.JSONField(default=list, blank=True)
    cve_ids = models.JSONField(default=list, blank=True)

    # Additional metadata from SARIF
    sarif_data = models.JSONField(blank=True, null=True, help_text="Full SARIF result object")

    # Tracking
    occurrence_count = models.IntegerField(default=1)
    first_seen_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    fixed_at = models.DateTimeField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'findings'
        verbose_name = _('finding')
        verbose_name_plural = _('findings')
        ordering = ['-severity', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['repository', 'status']),
            models.Index(fields=['fingerprint']),
            models.Index(fields=['severity']),
            models.Index(fields=['rule_id']),
            models.Index(fields=['first_seen_at']),
            models.Index(fields=['organization', 'fingerprint']),
        ]
        # Ensure fingerprint uniqueness per organization
        unique_together = [['organization', 'fingerprint']]

    def __str__(self):
        return f"{self.rule_id} in {self.file_path}:{self.start_line}"

    @staticmethod
    def generate_fingerprint(organization_id, rule_id, file_path, start_line, start_column, message):
        """
        Generate a deterministic fingerprint for deduplication (ADR-002).
        """
        message_hash = hashlib.sha256(message.encode()).hexdigest()[:16]
        fingerprint_data = f"{organization_id}|{rule_id}|{file_path}|{start_line}|{start_column}|{message_hash}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    def update_occurrence(self, scan):
        """
        Update the finding when it's seen again in a new scan.
        """
        self.occurrence_count += 1
        self.last_seen_scan = scan
        self.save(update_fields=['occurrence_count', 'last_seen_scan', 'last_seen_at'])


class FindingComment(models.Model):
    """
    Comments on findings for collaboration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='finding_comments'
    )
    content = models.TextField()

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finding_comments'
        verbose_name = _('finding comment')
        verbose_name_plural = _('finding comments')
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.email} on {self.finding.rule_id}"


class FindingStatusHistory(models.Model):
    """
    Track status changes of findings for audit trail.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='finding_status_changes'
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    reason = models.TextField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'finding_status_history'
        verbose_name = _('finding status history')
        verbose_name_plural = _('finding status histories')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.old_status} -> {self.new_status} by {self.changed_by.email}"


class LLMVerdict(models.Model):
    """
    LLM adjudication verdict for a security finding.

    Stores the LLM's analysis of whether a finding is a true positive,
    false positive, or uncertain. Part of the post-processing filter pattern.
    """
    VERDICT_CHOICES = [
        ('true_positive', 'True Positive'),
        ('false_positive', 'False Positive'),
        ('uncertain', 'Uncertain'),
    ]

    AGENT_PATTERN_CHOICES = [
        ('post_processing', 'Post-Processing Filter'),
        ('interactive', 'Interactive Retrieval'),
        ('multi_agent', 'Multi-Agent Collaboration'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name='llm_verdicts'
    )

    # Verdict details
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES, db_index=True)
    confidence = models.FloatField(help_text="Confidence score 0.0-1.0")
    reasoning = models.TextField(help_text="LLM's explanation for the verdict")

    # CWE identification
    cwe_id = models.CharField(max_length=50, blank=True, null=True, help_text="CWE-XXX identified by LLM")

    # Fix recommendation
    recommendation = models.TextField(blank=True, null=True, help_text="LLM's fix recommendation")

    # LLM metadata
    llm_provider = models.CharField(max_length=50, help_text="e.g., openai, anthropic")
    llm_model = models.CharField(max_length=100, help_text="e.g., gpt-4o, claude-sonnet-4")
    agent_pattern = models.CharField(
        max_length=50,
        choices=AGENT_PATTERN_CHOICES,
        default='post_processing',
        help_text="Which agent pattern was used"
    )

    # Token usage and cost tracking
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        help_text="Estimated cost in USD"
    )

    # Performance metrics
    processing_time_ms = models.IntegerField(help_text="Time taken for LLM call in milliseconds")

    # Full LLM response
    raw_response = models.JSONField(blank=True, null=True, help_text="Full LLM response for debugging")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'llm_verdicts'
        verbose_name = _('LLM verdict')
        verbose_name_plural = _('LLM verdicts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['finding', 'created_at']),
            models.Index(fields=['verdict']),
            models.Index(fields=['llm_provider', 'llm_model']),
            models.Index(fields=['agent_pattern']),
        ]

    def __str__(self):
        return f"{self.verdict} for {self.finding.rule_id} (confidence: {self.confidence})"

    @property
    def is_high_confidence(self):
        """Check if verdict has high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    @property
    def should_filter(self):
        """Check if finding should be filtered based on verdict."""
        return self.verdict == 'false_positive' and self.confidence >= 0.7


class FindingCluster(models.Model):
    """
    Cluster of semantically similar findings.

    Groups findings with similar embeddings for better deduplication
    and analysis. Uses vector embeddings and clustering algorithms.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='finding_clusters',
        db_index=True
    )

    # Cluster identification
    cluster_label = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Cluster identifier (e.g., cluster_0, cluster_1)"
    )

    # Representative finding (closest to centroid)
    representative_finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name='representative_clusters',
        null=True,
        blank=True,
        help_text="Most representative finding in cluster"
    )

    # Cluster statistics
    size = models.IntegerField(default=0, help_text="Number of findings in cluster")
    avg_similarity = models.FloatField(
        default=0.0,
        help_text="Average pairwise similarity (0.0-1.0)"
    )
    cohesion_score = models.FloatField(
        default=0.0,
        help_text="Cluster cohesion score (higher is better)"
    )

    # Clustering metadata
    algorithm = models.CharField(
        max_length=50,
        default='dbscan',
        help_text="Clustering algorithm used"
    )
    similarity_threshold = models.FloatField(
        default=0.85,
        help_text="Similarity threshold used for clustering"
    )

    # Cluster characteristics (from representative finding)
    primary_rule_id = models.CharField(max_length=255, blank=True)
    primary_severity = models.CharField(max_length=20, blank=True)
    primary_tool = models.CharField(max_length=255, blank=True)

    # Additional metadata
    statistics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed cluster statistics"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finding_clusters'
        verbose_name = _('finding cluster')
        verbose_name_plural = _('finding clusters')
        ordering = ['-size', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'cluster_label']),
            models.Index(fields=['size']),
            models.Index(fields=['created_at']),
        ]
        unique_together = [['organization', 'cluster_label']]

    def __str__(self):
        return f"{self.cluster_label} ({self.size} findings)"


class FindingClusterMembership(models.Model):
    """
    Membership relationship between findings and clusters.

    Links findings to their semantic clusters.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name='cluster_memberships'
    )
    cluster = models.ForeignKey(
        FindingCluster,
        on_delete=models.CASCADE,
        related_name='members'
    )

    # Similarity to cluster centroid
    distance_to_centroid = models.FloatField(
        default=0.0,
        help_text="Distance from cluster centroid (lower is better)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finding_cluster_memberships'
        verbose_name = _('finding cluster membership')
        verbose_name_plural = _('finding cluster memberships')
        unique_together = [['finding', 'cluster']]
        indexes = [
            models.Index(fields=['cluster', 'distance_to_centroid']),
        ]

    def __str__(self):
        return f"{self.finding.rule_id} in {self.cluster.cluster_label}"
