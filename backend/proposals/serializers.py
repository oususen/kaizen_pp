from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    Department,
    Employee,
    ImprovementProposal,
    ProposalApproval,
)
from .services import fiscal
from .services.identifiers import generate_management_no
from .services.images import save_proposal_image


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "level", "parent", "parent_name"]


class EmployeeSerializer(serializers.ModelSerializer):
    department_detail = DepartmentSerializer(source="department", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "code",
            "name",
            "email",
            "position",
            "role",
            "is_active",
            "division",
            "group",
            "team",
            "department",
            "department_detail",
        ]
        read_only_fields = ("is_active",)


class ProposalApprovalSerializer(serializers.ModelSerializer):
    confirmed_by_detail = EmployeeSerializer(source="confirmed_by", read_only=True)

    class Meta:
        model = ProposalApproval
        fields = [
            "id",
            "stage",
            "status",
            "comment",
            "confirmed_name",
            "confirmed_at",
            "confirmed_by",
            "confirmed_by_detail",
            "mindset_score",
            "idea_score",
            "hint_score",
        ]
        read_only_fields = ("confirmed_at", "confirmed_by")


class ImprovementProposalSerializer(serializers.ModelSerializer):
    department_detail = DepartmentSerializer(source="department", read_only=True)
    section_detail = DepartmentSerializer(source="section", read_only=True)
    group_detail = DepartmentSerializer(source="group", read_only=True)
    team_detail = DepartmentSerializer(source="team", read_only=True)
    proposer_detail = EmployeeSerializer(source="proposer", read_only=True)
    approvals = ProposalApprovalSerializer(many=True, read_only=True)
    before_image = serializers.ImageField(write_only=True, required=False)
    after_image = serializers.ImageField(write_only=True, required=False)
    current_stage = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    term = serializers.SerializerMethodField()
    quarter = serializers.SerializerMethodField()

    class Meta:
        model = ImprovementProposal
        fields = [
            "id",
            "management_no",
            "submitted_at",
            "department",
            "department_detail",
            "section",
            "section_detail",
            "group",
            "group_detail",
            "team",
            "team_detail",
            "deployment_item",
            "proposer",
            "proposer_detail",
            "proposer_name",
            "problem_summary",
            "improvement_plan",
            "improvement_result",
            "reduction_hours",
            "effect_amount",
            "comment",
            "contribution_business",
            "mindset_score",
            "idea_score",
            "hint_score",
            "before_image_path",
            "after_image_path",
            "before_image",
            "after_image",
            "created_at",
            "updated_at",
            "approvals",
            "current_stage",
            "is_completed",
            "term",
            "quarter",
        ]
        read_only_fields = (
            "management_no",
            "effect_amount",
            "before_image_path",
            "after_image_path",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        errors = {}
        current = self.instance or ImprovementProposal()

        def check_level(value: Department | None, expected: str, field: str):
            if value and value.level != expected:
                errors[field] = f"{field} must be a {expected} level department"

        check_level(attrs.get("department", getattr(current, "department", None)), "division", "department")
        check_level(attrs.get("section", getattr(current, "section", None)), "section", "section")
        check_level(attrs.get("group", getattr(current, "group", None)), "group", "group")
        check_level(attrs.get("team", getattr(current, "team", None)), "team", "team")

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        before_image = validated_data.pop("before_image", None)
        after_image = validated_data.pop("after_image", None)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data.setdefault("created_by", request.user)
            employee = getattr(request.user, "employee_profile", None)
            if employee and not validated_data.get("proposer"):
                validated_data["proposer"] = employee
                validated_data.setdefault("proposer_name", employee.name)
        if not validated_data.get("management_no"):
            validated_data["management_no"] = generate_management_no()
        if not validated_data.get("submitted_at"):
            validated_data["submitted_at"] = timezone.now()
        reduction_hours = validated_data.get("reduction_hours")
        if reduction_hours is not None and not validated_data.get("effect_amount"):
            validated_data["effect_amount"] = Decimal("1700") * reduction_hours
        proposal = super().create(validated_data)
        updated_fields = []
        if before_image:
            proposal.before_image_path = save_proposal_image(before_image, proposal.management_no, "before")
            updated_fields.append("before_image_path")
        if after_image:
            proposal.after_image_path = save_proposal_image(after_image, proposal.management_no, "after")
            updated_fields.append("after_image_path")
        if updated_fields:
            proposal.save(update_fields=updated_fields)
        for stage, _ in ProposalApproval.Stage.choices:
            ProposalApproval.objects.get_or_create(proposal=proposal, stage=stage)
        return proposal

    def update(self, instance, validated_data):
        before_image = validated_data.pop("before_image", None)
        after_image = validated_data.pop("after_image", None)
        reduction_hours = validated_data.get("reduction_hours")
        if reduction_hours is not None and not validated_data.get("effect_amount"):
            validated_data["effect_amount"] = Decimal("1700") * reduction_hours
        proposal = super().update(instance, validated_data)
        updated_fields = []
        if before_image:
            proposal.before_image_path = save_proposal_image(before_image, proposal.management_no, "before")
            updated_fields.append("before_image_path")
        if after_image:
            proposal.after_image_path = save_proposal_image(after_image, proposal.management_no, "after")
            updated_fields.append("after_image_path")
        if updated_fields:
            proposal.save(update_fields=updated_fields)
        return proposal

    def _get_approvals(self, obj: ImprovementProposal):
        approvals = getattr(obj, '_prefetched_objects_cache', {}).get('approvals')
        if approvals is None:
            approvals = list(obj.approvals.all())
        return approvals

    def get_current_stage(self, obj: ImprovementProposal) -> str:
        approvals = self._get_approvals(obj)
        pending = next((a for a in approvals if a.status == ProposalApproval.Status.PENDING), None)
        return pending.stage if pending else 'completed'

    def get_is_completed(self, obj: ImprovementProposal) -> bool:
        approvals = self._get_approvals(obj)
        return all(a.status == ProposalApproval.Status.APPROVED for a in approvals)

    def get_term(self, obj: ImprovementProposal) -> int:
        return fiscal.fiscal_term(obj.submitted_at)

    def get_quarter(self, obj: ImprovementProposal) -> int:
        return fiscal.fiscal_quarter(obj.submitted_at)


class ApprovalActionSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=ProposalApproval.Stage.choices)
    status = serializers.ChoiceField(choices=ProposalApproval.Status.choices)
    comment = serializers.CharField(allow_blank=True, required=False)
    confirmed_name = serializers.CharField(max_length=128)
    scores = serializers.DictField(child=serializers.IntegerField(min_value=1, max_value=5), required=False)

    def validate(self, attrs):
        stage = attrs.get('stage')
        scores = attrs.get('scores')
        if stage in {ProposalApproval.Stage.MANAGER, ProposalApproval.Stage.COMMITTEE}:
            if not scores:
                raise serializers.ValidationError('scores are required for this stage')
            for key in ('mindset', 'idea', 'hint'):
                if key not in scores:
                    raise serializers.ValidationError(f"missing score: {key}")
        return attrs
