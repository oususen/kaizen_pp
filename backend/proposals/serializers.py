from rest_framework import serializers

from .models import Department, Proposal


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(
        source="parent.name", read_only=True
    )

    class Meta:
        model = Department
        fields = ["id", "name", "level", "parent", "parent_name"]


class ProposalSerializer(serializers.ModelSerializer):
    department_detail = DepartmentSerializer(source="department", read_only=True)
    current_stage = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = [
            "id",
            "management_no",
            "title",
            "proposer_name",
            "proposer_email",
            "department",
            "department_detail",
            "team_name",
            "problem",
            "idea",
            "expected_effect",
            "result_detail",
            "contribution_business",
            "reduction_hours",
            "effect_amount",
            "before_image_url",
            "after_image_url",
            "supervisor_status",
            "supervisor_comment",
            "supervisor_checked_at",
            "chief_status",
            "chief_comment",
            "chief_checked_at",
            "manager_status",
            "manager_comment",
            "manager_checked_at",
            "manager_mindset_score",
            "manager_idea_score",
            "manager_hint_score",
            "committee_status",
            "committee_comment",
            "committee_checked_at",
            "current_stage",
            "total_score",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "supervisor_checked_at",
            "chief_checked_at",
            "manager_checked_at",
            "committee_checked_at",
            "created_at",
            "updated_at",
        ]

    def get_current_stage(self, obj: Proposal) -> str:
        stages = ["supervisor", "chief", "manager", "committee"]
        for stage in stages:
            if getattr(obj, f"{stage}_status") == Proposal.StageStatus.PENDING:
                return stage
        return "completed"

    def get_total_score(self, obj: Proposal):
        scores = [
            obj.manager_mindset_score,
            obj.manager_idea_score,
            obj.manager_hint_score,
        ]
        scores = [s for s in scores if s is not None]
        return sum(scores) if scores else None
