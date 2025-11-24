from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import logging

from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Department,
    Employee,
    UserProfile,
    UserPermission,
    ImprovementProposal,
    ProposalApproval,
    ProposalImage,
)
from .services import fiscal
from .services.identifiers import generate_management_no
from .services.images import save_proposal_image

User = get_user_model()
logger = logging.getLogger(__name__)


def build_media_url(request, path: str | None) -> str:
    """Return absolute media URL for stored relative image paths."""
    if not path:
        return ""
    if isinstance(path, str) and path.startswith("http"):
        return path
    media_path = f"{settings.MEDIA_URL.rstrip('/')}/{str(path).lstrip('/')}"
    return request.build_absolute_uri(media_path) if request else media_path


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "level", "display_id", "parent", "parent_name"]


class UserProfileSerializer(serializers.ModelSerializer):
    responsible_department_detail = DepartmentSerializer(source="responsible_department", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "role",
            "role_display",
            "responsible_department",
            "responsible_department_detail",
            "email",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
        ]
        extra_kwargs = {
            'smtp_password': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="first_name", read_only=True)
    employee_name = serializers.CharField(source="employee_profile.name", read_only=True)
    department_name = serializers.CharField(source="employee_profile.department.name", read_only=True)
    profile = UserProfileSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "employee_name", "department_name", "profile", "permissions"]

    def get_permissions(self, obj):
        # 既存の権限を返す
        return UserPermissionSerializer(obj.permissions.all(), many=True).data


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    """ユーザー作成・更新用のシリアライザー"""
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    name = serializers.CharField(source='first_name', required=False, allow_blank=True)
    profile_role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        required=False,
        allow_null=True,
        source='profile.role'
    )
    profile_responsible_department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
        source='profile.responsible_department'
    )
    smtp_host = serializers.CharField(required=False, allow_blank=True, source='profile.smtp_host')
    smtp_port = serializers.IntegerField(required=False, allow_null=True, source='profile.smtp_port')
    smtp_user = serializers.CharField(required=False, allow_blank=True, source='profile.smtp_user')
    smtp_password = serializers.CharField(write_only=True, required=False, allow_blank=True, source='profile.smtp_password')

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "name",
            "email",
            "password",
            "profile_role",
            "profile_responsible_department",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
        ]

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)

        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()

        # UserProfileを作成または更新
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'role': profile_data.get('role', 'staff'),
                'responsible_department': profile_data.get('responsible_department'),
                'smtp_host': profile_data.get('smtp_host', ''),
                'smtp_port': profile_data.get('smtp_port'),
                'smtp_user': profile_data.get('smtp_user', ''),
                'smtp_password': profile_data.get('smtp_password', ''),
            }
        )

        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)

        # ユーザー情報を更新
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        # UserProfileを更新
        if profile_data:
            profile_defaults = {
                'role': profile_data.get('role', 'staff'),
                'responsible_department': profile_data.get('responsible_department'),
            }
            # SMTP設定がある場合のみ更新
            if 'smtp_host' in profile_data:
                profile_defaults['smtp_host'] = profile_data.get('smtp_host', '')
            if 'smtp_port' in profile_data:
                profile_defaults['smtp_port'] = profile_data.get('smtp_port')
            if 'smtp_user' in profile_data:
                profile_defaults['smtp_user'] = profile_data.get('smtp_user', '')
            if 'smtp_password' in profile_data:
                profile_defaults['smtp_password'] = profile_data.get('smtp_password', '')

            UserProfile.objects.update_or_create(
                user=instance,
                defaults=profile_defaults
            )

        return instance




class UserPermissionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    employee_name = serializers.CharField(source="user.employee_profile.name", read_only=True)
    department_name = serializers.CharField(source="user.employee_profile.department.name", read_only=True)

    class Meta:
        model = UserPermission
        fields = ["id", "user", "username", "email", "employee_name", "department_name", "resource", "can_view", "can_edit"]


class EmployeeSerializer(serializers.ModelSerializer):
    department_detail = DepartmentSerializer(source="department", read_only=True)
    permissions = UserPermissionSerializer(many=True, read_only=True)

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
            "permissions",
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


class ProposalImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()

    class Meta:
        model = ProposalImage
        fields = ["id", "kind", "image_path", "display_order", "url", "filename", "created_at"]
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        return build_media_url(request, obj.image_path)

    def get_filename(self, obj):
        return Path(obj.image_path).name


class ImprovementProposalSerializer(serializers.ModelSerializer):
    department_detail = DepartmentSerializer(source="department", read_only=True)
    section_detail = DepartmentSerializer(source="section", read_only=True)
    group_detail = DepartmentSerializer(source="group", read_only=True)
    team_detail = DepartmentSerializer(source="team", read_only=True)
    proposer_detail = EmployeeSerializer(source="proposer", read_only=True)
    approvals = ProposalApprovalSerializer(many=True, read_only=True)
    before_image = serializers.ImageField(write_only=True, required=False)
    after_image = serializers.ImageField(write_only=True, required=False)
    images = ProposalImageSerializer(many=True, read_only=True)
    before_images = serializers.SerializerMethodField()
    after_images = serializers.SerializerMethodField()
    current_stage = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    term = serializers.SerializerMethodField()
    quarter = serializers.SerializerMethodField()
    supervisor_status = serializers.SerializerMethodField()
    chief_status = serializers.SerializerMethodField()
    manager_status = serializers.SerializerMethodField()
    committee_status = serializers.SerializerMethodField()

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
            "proposal_classification",
            "comment",
            "contribution_business",
            "mindset_score",
            "idea_score",
            "hint_score",
            "before_image_path",
            "after_image_path",
            "images",
            "before_images",
            "after_images",
            "before_image",
            "after_image",
            "created_at",
            "updated_at",
            "approvals",
            "current_stage",
            "is_completed",
            "term",
            "quarter",
            "supervisor_status",
            "chief_status",
            "manager_status",
            "committee_status",
            "committee_classification",
        ]
        read_only_fields = (
            "management_no",
            "effect_amount",
            "before_image_path",
            "after_image_path",
            "images",
            "before_images",
            "after_images",
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

        quarter = attrs.get("quarter")
        if quarter is not None and quarter not in {1, 2, 3, 4}:
            errors["quarter"] = "quarter must be between 1 and 4"

        term = attrs.get("term")
        if term is not None and term < 0:
            errors["term"] = "term must be zero or positive"

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _collect_files(self, request, single_key: str, list_key: str):
        files = []
        if request and hasattr(request, "FILES"):
            files.extend(request.FILES.getlist(list_key) or [])
            single = request.FILES.get(single_key)
            if single:
                files.append(single)
        return files

    def _save_images(self, proposal: ImprovementProposal, files, kind: ProposalImage.Kind):
        saved_paths = []
        for idx, file_obj in enumerate(files):
            saved_path = save_proposal_image(file_obj, proposal.management_no, kind, suffix=str(idx + 1))
            ProposalImage.objects.create(
                proposal=proposal,
                kind=kind,
                image_path=saved_path,
                display_order=idx,
            )
            saved_paths.append(saved_path)
        return saved_paths

    def _get_images_for_kind(self, obj: ImprovementProposal, kind: ProposalImage.Kind):
        images = getattr(obj, '_prefetched_objects_cache', {}).get('images')
        if images is None:
            images = list(obj.images.all())
        filtered = [img for img in images if img.kind == kind]
        filtered.sort(key=lambda i: (i.display_order, i.id))
        request = self.context.get("request")
        return [
            {
                "id": img.id,
                "path": img.image_path,
                "url": build_media_url(request, img.image_path),
                "filename": Path(img.image_path).name,
                "order": img.display_order,
            }
            for img in filtered
        ]

    def create(self, validated_data):
        from django.core.mail import send_mail

        before_image = validated_data.pop("before_image", None)
        after_image = validated_data.pop("after_image", None)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data.setdefault("created_by", request.user)
        if not validated_data.get("management_no"):
            validated_data["management_no"] = generate_management_no()
        if not validated_data.get("submitted_at"):
            validated_data["submitted_at"] = timezone.now()
        submitted_at = validated_data.get("submitted_at")
        if validated_data.get("term") is None and submitted_at:
            validated_data["term"] = fiscal.fiscal_term(submitted_at)
        if validated_data.get("quarter") is None and submitted_at:
            validated_data["quarter"] = fiscal.fiscal_quarter(submitted_at)
        reduction_hours = validated_data.get("reduction_hours")
        if reduction_hours is not None and not validated_data.get("effect_amount"):
            validated_data["effect_amount"] = Decimal("1700") * reduction_hours
        proposal = super().create(validated_data)
        updated_fields = []
        before_files = self._collect_files(request, "before_image", "before_images")
        after_files = self._collect_files(request, "after_image", "after_images")
        if not before_files and before_image:
            before_files = [before_image]
        if not after_files and after_image:
            after_files = [after_image]

        before_paths = self._save_images(proposal, before_files, ProposalImage.Kind.BEFORE) if before_files else []
        after_paths = self._save_images(proposal, after_files, ProposalImage.Kind.AFTER) if after_files else []

        if before_paths:
            proposal.before_image_path = before_paths[0]
            updated_fields.append("before_image_path")
        if after_paths:
            proposal.after_image_path = after_paths[0]
            updated_fields.append("after_image_path")

        if updated_fields:
            proposal.save(update_fields=updated_fields)
        for stage, _ in ProposalApproval.Stage.choices:
            ProposalApproval.objects.get_or_create(proposal=proposal, stage=stage)

        # 提案提出時に上司へメール送信
        self._send_submission_email(proposal)

        return proposal

    def update(self, instance, validated_data):
        before_image = validated_data.pop("before_image", None)
        after_image = validated_data.pop("after_image", None)
        reduction_hours = validated_data.get("reduction_hours")
        if reduction_hours is not None and not validated_data.get("effect_amount"):
            validated_data["effect_amount"] = Decimal("1700") * reduction_hours
        proposal = super().update(instance, validated_data)
        updated_fields = []
        request = self.context.get("request")
        before_files = self._collect_files(request, "before_image", "before_images")
        after_files = self._collect_files(request, "after_image", "after_images")
        if not before_files and before_image:
            before_files = [before_image]
        if not after_files and after_image:
            after_files = [after_image]

        before_paths = self._save_images(proposal, before_files, ProposalImage.Kind.BEFORE) if before_files else []
        after_paths = self._save_images(proposal, after_files, ProposalImage.Kind.AFTER) if after_files else []

        if before_paths:
            proposal.before_image_path = before_paths[0]
            updated_fields.append("before_image_path")
        if after_paths:
            proposal.after_image_path = after_paths[0]
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
        if obj.term is not None:
            return obj.term
        return fiscal.fiscal_term(obj.submitted_at)

    def get_quarter(self, obj: ImprovementProposal) -> int:
        if obj.quarter is not None:
            return obj.quarter
        return fiscal.fiscal_quarter(obj.submitted_at)

    def get_supervisor_status(self, obj: ImprovementProposal) -> str:
        approvals = self._get_approvals(obj)
        approval = next((a for a in approvals if a.stage == ProposalApproval.Stage.SUPERVISOR), None)
        return approval.status if approval else ProposalApproval.Status.PENDING

    def get_chief_status(self, obj: ImprovementProposal) -> str:
        approvals = self._get_approvals(obj)
        approval = next((a for a in approvals if a.stage == ProposalApproval.Stage.CHIEF), None)
        return approval.status if approval else ProposalApproval.Status.PENDING

    def get_manager_status(self, obj: ImprovementProposal) -> str:
        approvals = self._get_approvals(obj)
        approval = next((a for a in approvals if a.stage == ProposalApproval.Stage.MANAGER), None)
        return approval.status if approval else ProposalApproval.Status.PENDING

    def get_committee_status(self, obj: ImprovementProposal) -> str:
        approvals = self._get_approvals(obj)
        approval = next((a for a in approvals if a.stage == ProposalApproval.Stage.COMMITTEE), None)
        return approval.status if approval else ProposalApproval.Status.PENDING

    def get_before_images(self, obj: ImprovementProposal):
        return self._get_images_for_kind(obj, ProposalImage.Kind.BEFORE)

    def get_after_images(self, obj: ImprovementProposal):
        return self._get_images_for_kind(obj, ProposalImage.Kind.AFTER)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        data["before_image_path"] = build_media_url(request, data.get("before_image_path"))
        data["after_image_path"] = build_media_url(request, data.get("after_image_path"))
        if not data.get("before_image_path") and data.get("before_images"):
            data["before_image_path"] = data["before_images"][0].get("url") or ""
        if not data.get("after_image_path") and data.get("after_images"):
            data["after_image_path"] = data["after_images"][0].get("url") or ""
        return data

    def _get_smtp_connection_for_user(self, user):
        """指定されたユーザーのSMTP設定を使用してメール接続を作成"""
        from django.core.mail import get_connection

        if not user:
            logger.info("[mail] no user -> default SMTP from=%s", settings.DEFAULT_FROM_EMAIL)
            return get_connection(fail_silently=False), settings.DEFAULT_FROM_EMAIL

        try:
            # ユーザープロファイルからSMTP設定を取得
            if hasattr(user, 'profile') and user.profile:
                profile = user.profile

                # SMTP設定が全て揃っているか確認
                if (profile.smtp_host and profile.smtp_user and
                    profile.smtp_password and user.email):

                    # ユーザーのSMTP設定を使用して接続を作成
                    # 開発環境では暗号化なしで接続（TLSをオフ）
                    connection = get_connection(
                        backend='django.core.mail.backends.smtp.EmailBackend',
                        host=profile.smtp_host,
                        port=profile.smtp_port or 587,
                        username=profile.smtp_user,
                        password=profile.smtp_password,
                        use_tls=False,  # 開発環境では証明書エラーを回避するためFalse
                        fail_silently=False,
                    )
                    from_email = user.email
                    logger.info(
                        "[mail] use user SMTP user=%s host=%s port=%s from=%s",
                        getattr(user, "username", None),
                        profile.smtp_host,
                        profile.smtp_port or 587,
                        from_email,
                    )
                    return connection, from_email
        except Exception as e:
            logger.error("Error getting SMTP settings for user %s: %s", getattr(user, "username", None), e)

        # フォールバック: デフォルト設定を使用
        logger.warning(
            "[mail] fallback default SMTP for user=%s from=%s",
            getattr(user, "username", None),
            settings.DEFAULT_FROM_EMAIL,
        )
        return get_connection(fail_silently=False), settings.DEFAULT_FROM_EMAIL

    def _send_submission_email(self, proposal):
        """Send submission email to the appropriate supervisor."""
        from django.core.mail import EmailMessage, get_connection
        from django.db.models import Q
        from .models import UserProfile

        # Find supervisors in order: team -> group -> department
        role_dept_chain = []
        if proposal.team:
            role_dept_chain.append(("supervisor", proposal.team))
        if proposal.group:
            role_dept_chain.append(("chief", proposal.group))
        if proposal.department:
            role_dept_chain.append(("manager", proposal.department))

        logger.info(
            "[mail] submit proposal id=%s mgmt_no=%s proposer=%s dept_chain=%s",
            proposal.id,
            proposal.management_no,
            proposal.proposer_name,
            [(r, getattr(d, "id", None), getattr(d, "name", None)) for r, d in role_dept_chain],
        )

        recipient_list = []
        for role, dept in role_dept_chain:
            # proposals_userprofile テーブルから管轄者を検索
            # auth_user.email からメールアドレスを取得
            profiles_query = Q(role=role, responsible_department=dept) | Q(role='admin')
            profiles = UserProfile.objects.filter(
                profiles_query,
                user__isnull=False,
                user__is_active=True,
                user__email__isnull=False
            ).exclude(user__email__exact='').select_related('user')

            recipient_list = [profile.user.email for profile in profiles if profile.user and profile.user.email]
            logger.info(
                "[mail] role=%s dept_id=%s dept_name=%s recipients=%s (from UserProfile table)",
                role,
                getattr(dept, "id", None),
                getattr(dept, "name", None),
                recipient_list,
            )
            if recipient_list:
                break

        if not recipient_list:
            logger.warning("[mail] no recipients found for proposal id=%s", proposal.id)
            return  # No recipients, skip sending

        subject = f"【改善提案】新規登録: {proposal.management_no}"

        dept_name = ""
        if proposal.team:
            dept_name = f"{proposal.department.name if proposal.department else ''}/{proposal.group.name if proposal.group else ''}/{proposal.team.name}"
        elif proposal.group:
            dept_name = f"{proposal.department.name if proposal.department else ''}/{proposal.group.name}"
        elif proposal.department:
            dept_name = proposal.department.name

        message = f"""
        改善提案が登録されました。

        管理番号: {proposal.management_no}
        提案者: {proposal.proposer_name}
        部署: {dept_name}
        テーマ: {proposal.deployment_item}

        下記URLから内容を確認し、承認をお願いします。
        http://10.0.1.194:5000/approval-center
        """

        try:
            # ログインしているユーザー（created_by）のSMTP設定を使用
            # auth_user → proposals_userprofile から smtp_host, smtp_user, smtp_password を取得
            login_user = proposal.created_by
            logger.info(
                "[mail] login_user=%s (created_by)",
                getattr(login_user, 'username', None) if login_user else None
            )

            connection, from_email = self._get_smtp_connection_for_user(login_user)

            # Fall back to default connection if user-specific SMTP is missing
            if not connection:
                connection = get_connection(fail_silently=False)
                from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")
                logger.warning(
                    "[mail] SMTP not configured for login_user=%s; using default from=%s",
                    getattr(login_user, "username", None) if login_user else None,
                    from_email,
                )

            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
                connection=connection,
            )
            email.send(fail_silently=False)
            logger.info("[mail] sent submission email to=%s from=%s", recipient_list, from_email)
        except Exception as e:
            logger.error("Error sending submission email: %s", e)

class ApprovalActionSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=ProposalApproval.Stage.choices)
    status = serializers.ChoiceField(choices=ProposalApproval.Status.choices)
    comment = serializers.CharField(allow_blank=True, required=False)
    confirmed_name = serializers.CharField(max_length=128)
    proposal_classification = serializers.ChoiceField(
        choices=ImprovementProposal.ProposalClassification.choices, required=False, allow_blank=True
    )
    committee_classification = serializers.ChoiceField(
        choices=ImprovementProposal.ProposalClassification.choices, required=False, allow_blank=True
    )
    term = serializers.IntegerField(required=False, allow_null=True)
    quarter = serializers.IntegerField(required=False, allow_null=True)
    scores = serializers.DictField(child=serializers.IntegerField(min_value=1, max_value=5), required=False)

    def validate(self, attrs):
        stage = attrs.get('stage')
        scores = attrs.get('scores')
        term = attrs.get('term')
        quarter = attrs.get('quarter')
        status_value = attrs.get('status')
        proposal_classification = attrs.get("proposal_classification")
        committee_classification = attrs.get("committee_classification")

        if quarter is not None and quarter not in {1, 2, 3, 4}:
            raise serializers.ValidationError('quarter must be between 1 and 4')

        if stage == ProposalApproval.Stage.COMMITTEE and status_value == ProposalApproval.Status.APPROVED:
            if term is None or quarter is None:
                raise serializers.ValidationError('term and quarter are required at committee approval')
            if not committee_classification:
                raise serializers.ValidationError('committee_classification is required at committee approval')

        if stage == ProposalApproval.Stage.MANAGER and status_value == ProposalApproval.Status.APPROVED:
            if not proposal_classification:
                raise serializers.ValidationError('proposal_classification is required at manager approval')

        if stage in {ProposalApproval.Stage.MANAGER, ProposalApproval.Stage.COMMITTEE}:
            if not scores:
                raise serializers.ValidationError('scores are required for this stage')
            for key in ('mindset', 'idea', 'hint'):
                if key not in scores:
                    raise serializers.ValidationError(f"missing score: {key}")
        return attrs
