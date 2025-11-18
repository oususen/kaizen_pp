from django.db import models


class Department(models.Model):
    """部門/課/係/班などの組織階層を表す."""

    LEVEL_CHOICES = [
        ("division", "部"),
        ("section", "課"),
        ("group", "係"),
        ("team", "班"),
    ]

    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    class Meta:
        unique_together = ("name", "level")
        ordering = ["level", "name"]

    def __str__(self) -> str:
        prefix = dict(self.LEVEL_CHOICES).get(self.level, "")
        return f"{prefix}:{self.name}"


class Proposal(models.Model):
    """改善提案と多段階承認のステータスを表す."""

    class StageStatus(models.TextChoices):
        PENDING = "pending", "未確認"
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "差戻し"

    management_no = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=255)
    proposer_name = models.CharField(max_length=128)
    proposer_email = models.EmailField(blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="proposals"
    )
    team_name = models.CharField(max_length=128, blank=True)
    problem = models.TextField()
    idea = models.TextField()
    expected_effect = models.TextField(blank=True)
    result_detail = models.TextField(blank=True)
    contribution_business = models.CharField(max_length=255, blank=True)
    reduction_hours = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True
    )
    effect_amount = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True
    )
    before_image_url = models.CharField(max_length=255, blank=True)
    after_image_url = models.CharField(max_length=255, blank=True)

    supervisor_status = models.CharField(
        max_length=20, choices=StageStatus.choices, default=StageStatus.PENDING
    )
    supervisor_comment = models.TextField(blank=True)
    supervisor_checked_at = models.DateTimeField(null=True, blank=True)

    chief_status = models.CharField(
        max_length=20, choices=StageStatus.choices, default=StageStatus.PENDING
    )
    chief_comment = models.TextField(blank=True)
    chief_checked_at = models.DateTimeField(null=True, blank=True)

    manager_status = models.CharField(
        max_length=20, choices=StageStatus.choices, default=StageStatus.PENDING
    )
    manager_comment = models.TextField(blank=True)
    manager_checked_at = models.DateTimeField(null=True, blank=True)
    manager_mindset_score = models.PositiveSmallIntegerField(null=True, blank=True)
    manager_idea_score = models.PositiveSmallIntegerField(null=True, blank=True)
    manager_hint_score = models.PositiveSmallIntegerField(null=True, blank=True)

    committee_status = models.CharField(
        max_length=20, choices=StageStatus.choices, default=StageStatus.PENDING
    )
    committee_comment = models.TextField(blank=True)
    committee_checked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.management_no} - {self.title}"
