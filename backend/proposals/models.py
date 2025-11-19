from django.conf import settings
from django.db import models
from django.utils import timezone


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


class Employee(models.Model):
    """従業員マスタ。ログインユーザーや承認者を紐付ける想定。"""

    class Role(models.TextChoices):
        STAFF = "staff", "従業員"
        SUPERVISOR = "supervisor", "監督者"
        CHIEF = "chief", "係長"
        MANAGER = "manager", "部門長"
        COMMITTEE = "committee", "改善委員"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="employees"
    )
    division = models.CharField("事業部/課", max_length=100, blank=True)
    group = models.CharField("係", max_length=100, blank=True)
    team = models.CharField("班", max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    is_active = models.BooleanField(default=True)
    joined_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["department__name", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


class ImprovementProposal(models.Model):
    """Streamlit版の要件を満たす改善提案の本体."""

    management_no = models.CharField("管理No", max_length=64, unique=True)
    submitted_at = models.DateTimeField("提出日時", default=timezone.now)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="improvement_proposals",
    )
    affiliation = models.CharField("所属担当", max_length=128, blank=True)
    deployment_item = models.CharField("展開項目", max_length=255, blank=True)
    proposer = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="improvement_proposals",
    )
    proposer_name = models.CharField("提案者", max_length=128)
    problem_summary = models.TextField("問題点")
    improvement_plan = models.TextField("改善案")
    improvement_result = models.TextField("改善結果", blank=True)
    reduction_hours = models.DecimalField(
        "削減時間(Hr/月)",
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
    )
    effect_amount = models.DecimalField(
        "効果額(円/月)",
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
    )
    comment = models.TextField("コメント", blank=True)
    contribution_business = models.CharField("貢献事業", max_length=255, blank=True)
    mindset_score = models.PositiveSmallIntegerField("マインドセット", null=True, blank=True)
    idea_score = models.PositiveSmallIntegerField("アイデア工夫", null=True, blank=True)
    hint_score = models.PositiveSmallIntegerField("みんなのヒント", null=True, blank=True)
    before_image_path = models.CharField("改善前画像", max_length=255, blank=True)
    after_image_path = models.CharField("改善後画像", max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_improvement_proposals",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.management_no} - {self.proposer_name}"


class ProposalApproval(models.Model):
    """各承認段階の状態を保持."""

    class Stage(models.TextChoices):
        SUPERVISOR = "supervisor", "監督者"
        CHIEF = "chief", "係長"
        MANAGER = "manager", "部門長"
        COMMITTEE = "committee", "改善委員"

    class Status(models.TextChoices):
        PENDING = "pending", "未確認"
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "差戻し"
        HOLD = "hold", "保留"

    proposal = models.ForeignKey(
        ImprovementProposal, on_delete=models.CASCADE, related_name="approvals"
    )
    stage = models.CharField(max_length=20, choices=Stage.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    comment = models.TextField(blank=True)
    confirmed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_actions",
    )
    confirmed_name = models.CharField(max_length=128, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    mindset_score = models.PositiveSmallIntegerField(null=True, blank=True)
    idea_score = models.PositiveSmallIntegerField(null=True, blank=True)
    hint_score = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("proposal", "stage")
        ordering = ["proposal_id", "stage"]

    def __str__(self) -> str:
        return f"{self.proposal.management_no} / {self.stage}"


