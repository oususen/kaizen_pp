from __future__ import annotations

from datetime import datetime, time

from django.db.models import Count, F, Q, Max
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model
from .models import (
    Department,
    Employee,
    UserPermission,
    ImprovementProposal,
    ProposalApproval,
    ProposalContributor,
    UserProfile,
)
from .serializers import (
    ApprovalActionSerializer,
    DepartmentSerializer,
    UserPermissionSerializer,
    UserSerializer,
    UserCreateUpdateSerializer,
    EmployeeSerializer,
    ImprovementProposalSerializer,
)

User = get_user_model()
from .services import fiscal
from .services.reports import generate_term_report


def get_smtp_connection_for_user(user):
    """指定されたユーザーのSMTP設定を使用してメール接続を作成"""
    from django.core.mail import get_connection
    from django.conf import settings
    import logging
    logger = logging.getLogger(__name__)

    if not user:
        logger.info("[mail] no user -> default SMTP")
        return None, settings.DEFAULT_FROM_EMAIL

    try:
        # ユーザーのプロファイルからSMTP設定を取得
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
                    "[mail] approval: use user SMTP user=%s host=%s port=%s from=%s",
                    getattr(user, "username", None),
                    profile.smtp_host,
                    profile.smtp_port or 587,
                    from_email,
                )
                return connection, from_email
    except Exception as e:
        logger.error("Error getting SMTP settings for user %s: %s", getattr(user, "username", None), e)

    # フォールバック: デフォルト設定を使用
    logger.warning("[mail] fallback default SMTP for user=%s", getattr(user, "username", None))
    return None, settings.DEFAULT_FROM_EMAIL


def calculate_classification_points(classification: str | None) -> int | None:
    """Map classification to points."""
    if not classification:
        return None
    mapping = {
        ImprovementProposal.ProposalClassification.HOLD: 0,
        ImprovementProposal.ProposalClassification.EFFORT: 1,
        ImprovementProposal.ProposalClassification.IDEA: 4,
        ImprovementProposal.ProposalClassification.EXCELLENT: 8,
    }
    return mapping.get(classification)


def _distribute_classification_points(proposal: ImprovementProposal) -> None:
    """均等割りで提案ポイントと報奨金をProposalContributorに保存する。"""
    from decimal import Decimal, ROUND_HALF_UP

    points = proposal.classification_points
    if points is None:
        return
    contributors = list(proposal.contributors.all())
    if not contributors:
        return

    total_points = Decimal(points)
    total_reward = total_points * Decimal("300")
    n = len(contributors)
    if n == 0:
        return

    # 提案ポイントの按分
    base_points = (total_points / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    remainder_points = (total_points - (base_points * n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 報奨金の按分（整数）
    base_reward = (total_reward / Decimal(n)).quantize(Decimal("0"), rounding=ROUND_HALF_UP)
    remainder_reward = (total_reward - (base_reward * n)).quantize(Decimal("0"), rounding=ROUND_HALF_UP)

    for idx, contrib in enumerate(contributors):
        points_share = base_points
        reward_share = base_reward
        if idx == 0:
            # 余りを最初の提案者に加算
            if remainder_points:
                points_share = (base_points + remainder_points).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if remainder_reward:
                reward_share = (base_reward + remainder_reward).quantize(Decimal("0"), rounding=ROUND_HALF_UP)
        contrib.classification_points_share = points_share
        contrib.reward_amount = reward_share
    ProposalContributor.objects.bulk_update(contributors, ["classification_points_share", "reward_amount"])


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("parent")
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        level = self.request.query_params.get("level")
        if level:
            queryset = queryset.filter(level=level)
        return queryset


class ImprovementProposalViewSet(viewsets.ModelViewSet):
    serializer_class = ImprovementProposalSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[ViewSet.create] Request data keys: {request.data.keys()}")
        logger.info(f"[ViewSet.create] Contributors raw: {request.data.get('contributors')}")
        logger.info(f"[ViewSet.create] Contributors type: {type(request.data.get('contributors'))}")
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """提案を削除（班長以上の権限が必要）"""
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"detail": "ログインが必要です"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ユーザーの役職を取得
        role = None
        if hasattr(user, 'profile') and user.profile:
            role = user.profile.role
        elif hasattr(user, 'employee_profile') and user.employee_profile:
            role = user.employee_profile.role

        # 班長以上の権限チェック
        allowed_roles = ['supervisor', 'chief', 'manager', 'committee', 'committee_chair', 'admin']
        if role not in allowed_roles:
            return Response(
                {"detail": "この操作には班長以上の権限が必要です"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            ImprovementProposal.objects.select_related(
                "department", "section", "group", "team", "proposer", "created_by"
            )
            .prefetch_related("approvals__confirmed_by", "images", "contributors__employee")
            .annotate(
                total_approvals=Count("approvals", distinct=True),
                approved_count=Count(
                    "approvals",
                    filter=Q(approvals__status=ProposalApproval.Status.APPROVED),
                    distinct=True,
                ),
            )
            .order_by("-submitted_at")
        )
        params = self.request.query_params
        stage = params.get("stage")
        status_value = params.get("status")
        keyword = params.get("q")
        department_id = params.get("department")
        term_value = params.get("term")
        quarter_value = params.get("quarter")
        proposal_classification_value = params.get("proposal_classification")
        mindset_score_min = params.get("mindset_score_min")
        idea_score_min = params.get("idea_score_min")
        hint_score_min = params.get("hint_score_min")
        submitted_at_from = params.get("submitted_at_from")
        submitted_at_to = params.get("submitted_at_to")

        if department_id:
            queryset = queryset.filter(department_id=department_id)

        if keyword:
            queryset = queryset.filter(
                Q(management_no__icontains=keyword)
                | Q(proposer_name__icontains=keyword)
                | Q(deployment_item__icontains=keyword)
            )

        if term_value:
            try:
                term_number = int(term_value)
                start_date, end_date = fiscal.term_date_range(term_number)
                start_dt = datetime.combine(start_date, time.min)
                end_dt = datetime.combine(end_date, time.max)
                queryset = queryset.filter(
                    Q(term=term_number) | (Q(term__isnull=True) & Q(submitted_at__range=(start_dt, end_dt)))
                )
            except ValueError:
                pass

        if quarter_value:
            try:
                quarter_number = int(quarter_value)
                queryset = queryset.filter(quarter=quarter_number)
            except ValueError:
                pass

        if proposal_classification_value:
            queryset = queryset.filter(
                Q(proposal_classification=proposal_classification_value)
                | Q(committee_classification=proposal_classification_value)
            )

        if mindset_score_min:
            try:
                score = int(mindset_score_min)
                queryset = queryset.filter(mindset_score__gte=score)
            except ValueError:
                pass

        if idea_score_min:
            try:
                score = int(idea_score_min)
                queryset = queryset.filter(idea_score__gte=score)
            except ValueError:
                pass

        if hint_score_min:
            try:
                score = int(hint_score_min)
                queryset = queryset.filter(hint_score__gte=score)
            except ValueError:
                pass

        if submitted_at_from:
            try:
                from_date = datetime.fromisoformat(submitted_at_from.replace('Z', '+00:00'))
                queryset = queryset.filter(submitted_at__gte=from_date)
            except (ValueError, AttributeError):
                pass

        if submitted_at_to:
            try:
                to_date = datetime.fromisoformat(submitted_at_to.replace('Z', '+00:00'))
                queryset = queryset.filter(submitted_at__lte=to_date)
            except (ValueError, AttributeError):
                pass

        stage_choices = dict(ProposalApproval.Stage.choices)
        status_choices = dict(ProposalApproval.Status.choices)

        if stage in stage_choices and status_value in status_choices:
            # Filter for the current stage's status.
            queryset = queryset.filter(approvals__stage=stage, approvals__status=status_value)

            # Ensure all preceding stages are approved.
            stages_order = [s[0] for s in ProposalApproval.Stage.choices]
            if stage in stages_order:
                current_stage_index = stages_order.index(stage)
                for i in range(current_stage_index):
                    preceding_stage = stages_order[i]
                    queryset = queryset.filter(
                        approvals__stage=preceding_stage,
                        approvals__status=ProposalApproval.Status.APPROVED,
                    )
            queryset = queryset.distinct()
        elif status_value == "completed":
            queryset = queryset.filter(approved_count=F("total_approvals"))

        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from django.core.mail import send_mail
        from django.conf import settings

        proposal = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        stage = data["stage"]
        status_val = data["status"]
        term = data.get("term")
        quarter = data.get("quarter")
        proposal_classification = data.get("proposal_classification")
        committee_classification = data.get("committee_classification")

        approval = ProposalApproval.objects.filter(proposal=proposal, stage=stage).first()
        if not approval:
            return Response({"detail": "Invalid stage"}, status=status.HTTP_400_BAD_REQUEST)

        approval.status = status_val
        if "comment" in data:
            approval.comment = data.get("comment") or ""
        approval.confirmed_name = data["confirmed_name"]
        approval.confirmed_at = timezone.now()
        if stage == ProposalApproval.Stage.MANAGER:
            approval.sdgs_flag = bool(data.get("sdgs_flag"))
            approval.safety_flag = bool(data.get("safety_flag"))
        
        # ログインユーザーのUserProfileまたはEmployee Profileを取得
        user = request.user
        if hasattr(user, 'profile'):
            # UserProfileベース
            pass  # 特に追加で紐付ける情報がない場合は何もしない
        elif hasattr(user, 'employee_profile'):
            # Employeeベース
            approval.confirmed_by = user.employee_profile
            
        scores = data.get("scores") or {}
        if stage == ProposalApproval.Stage.MANAGER:
            approval.mindset_score = scores.get("mindset")
            approval.idea_score = scores.get("idea")
            approval.hint_score = scores.get("hint")
        else:
            approval.mindset_score = approval.idea_score = approval.hint_score = None
        
        approval.save()

        if stage == ProposalApproval.Stage.MANAGER and status_val == ProposalApproval.Status.APPROVED:
            updated_fields = []
            if proposal_classification:
                proposal.proposal_classification = proposal_classification
                updated_fields.append("proposal_classification")
                points = calculate_classification_points(proposal_classification)
                proposal.classification_points = points
                updated_fields.append("classification_points")
            # 評価基準スコアを提案テーブルに保存
            if scores:
                proposal.mindset_score = scores.get("mindset")
                proposal.idea_score = scores.get("idea")
                proposal.hint_score = scores.get("hint")
                updated_fields.extend(["mindset_score", "idea_score", "hint_score"])
            # 提案ポイントを共同提案者に均等配分
            if proposal.classification_points is not None:
                _distribute_classification_points(proposal)
            if updated_fields:
                proposal.save(update_fields=updated_fields)

        if stage == ProposalApproval.Stage.COMMITTEE and status_val == ProposalApproval.Status.APPROVED:
            updated_fields = []
            if committee_classification:
                proposal.committee_classification = committee_classification
                updated_fields.append("committee_classification")
            if term is not None:
                proposal.term = term
                updated_fields.append("term")
            if quarter is not None:
                proposal.quarter = quarter
                updated_fields.append("quarter")

            # 通し番号を自動採番（期ごとに連番）
            if term is not None:
                max_serial = ImprovementProposal.objects.filter(
                    term=term
                ).aggregate(Max('serial_number'))['serial_number__max']
                proposal.serial_number = (max_serial or 0) + 1
                updated_fields.append("serial_number")

            if updated_fields:
                proposal.save(update_fields=updated_fields)

        # メール送信ロジック
        if status_val == ProposalApproval.Status.APPROVED:
            stages_order = [s.value for s in ProposalApproval.Stage]
            current_stage_index = stages_order.index(stage)

            if current_stage_index + 1 < len(stages_order):
                next_stage = stages_order[current_stage_index + 1]

                # proposals_userprofile テーブルから管轄者を検索
                # auth_user.email からメールアドレスを取得
                from proposals.models import UserProfile

                next_approvers_query = Q()
                role_map = {
                    "supervisor": "supervisor",
                    "chief": "chief",
                    "manager": "manager",
                    "committee": "committee",
                    "committee_chair": "committee_chair"
                }
                next_role = role_map.get(next_stage)

                if next_role:
                    department_q = Q()
                    if next_role == 'supervisor' and proposal.team:
                        department_q = Q(responsible_department=proposal.team)
                    elif next_role == 'chief' and proposal.group:
                        department_q = Q(responsible_department=proposal.group)
                    elif next_role == 'manager' and proposal.section:
                        department_q = Q(responsible_department=proposal.section)
                    elif next_role == 'manager' and proposal.department:
                         department_q = Q(responsible_department=proposal.department)
                    elif next_role in ['committee', 'committee_chair'] and proposal.section:
                        department_q = Q(responsible_department=proposal.section)
                    elif next_role in ['committee', 'committee_chair'] and proposal.department:
                        department_q = Q(responsible_department=proposal.department)

                    if department_q:
                        next_approvers_query = Q(role=next_role) & department_q

                # システム管理者にも通知
                next_approvers_query |= Q(role='admin')

                if next_approvers_query:
                    next_profiles = UserProfile.objects.filter(
                        next_approvers_query,
                        user__isnull=False,
                        user__is_active=True,
                        user__email__isnull=False
                    ).exclude(user__email__exact='').select_related('user')

                    recipient_list = [profile.user.email for profile in next_profiles if profile.user and profile.user.email]

                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(
                        "[mail] approval: next_stage=%s next_role=%s recipients=%s",
                        next_stage,
                        next_role,
                        recipient_list
                    )

                    if recipient_list:
                        subject = f"【改善提案】承認依頼: {proposal.management_no}"
                        message = f"""
                        改善提案が承認され、あなたの確認待ちです。

                        管理番号: {proposal.management_no}
                        提案者: {proposal.proposer_name}
                        テーマ: {proposal.deployment_item}

                        下記URLより内容を確認し、承認処理をお願いします。
                        http://10.0.1.194:5000/approval-center
                        """
                        try:
                            # 承認者のSMTP設定を取得
                            from django.core.mail import EmailMessage
                            connection, from_email = get_smtp_connection_for_user(request.user)

                            # SMTP設定が設定されていない場合は送信しない
                            if not connection:
                                logger.warning(
                                    "[mail] SMTP not configured for user: %s",
                                    request.user.username if request.user else 'Unknown'
                                )
                            else:
                                # EmailMessageを使用してカスタム接続で送信
                                email = EmailMessage(
                                    subject=subject,
                                    body=message,
                                    from_email=from_email,
                                    to=recipient_list,
                                    connection=connection,
                                )
                                email.send(fail_silently=False)
                                logger.info("[mail] approval email sent to=%s from=%s", recipient_list, from_email)
                        except Exception as e:
                            logger.error("Error sending approval email: %s", e)
                    else:
                        logger.warning(
                            "[mail] no recipients found for approval: proposal_id=%s next_stage=%s next_role=%s",
                            proposal.id,
                            next_stage,
                            next_role
                        )

        refreshed_instance = self.get_queryset().filter(pk=proposal.pk).first() or proposal
        refreshed = self.get_serializer(refreshed_instance)
        return Response(refreshed.data)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        term_value = request.query_params.get("term")
        if term_value is None:
            return Response({"detail": "term parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            term_number = int(term_value)
        except ValueError:
            return Response({"detail": "term must be integer"}, status=status.HTTP_400_BAD_REQUEST)
        start_date, end_date = fiscal.term_date_range(term_number)
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        proposals = (
            ImprovementProposal.objects.filter(
                Q(term=term_number) | (Q(term__isnull=True) & Q(submitted_at__range=(start_dt, end_dt))),
                approvals__stage=ProposalApproval.Stage.COMMITTEE,
                approvals__status=ProposalApproval.Status.APPROVED
            )
            .select_related("department", "section", "group", "team", "proposer")
            .prefetch_related("approvals__confirmed_by", "contributors__employee")
        )
        buffer = generate_term_report(proposals, term_number)
        filename = f"kaizen_term_{term_number}.xlsx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        term_value = request.query_params.get("term")
        department_filter = request.query_params.get("department")
        if term_value is None:
            return Response({"detail": "term parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            term_number = int(term_value)
        except ValueError:
            return Response({"detail": "term must be integer"}, status=status.HTTP_400_BAD_REQUEST)
            
        start_date, end_date = fiscal.term_date_range(term_number)
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        proposals = (
            ImprovementProposal.objects.filter(
                Q(term=term_number) | (Q(term__isnull=True) & Q(submitted_at__range=(start_dt, end_dt))),
                approvals__stage=ProposalApproval.Stage.COMMITTEE,
                approvals__status=ProposalApproval.Status.APPROVED
            )
            .select_related("department", "section", "group", "team", "proposer")
            .prefetch_related("approvals__confirmed_by", "contributors__employee")
        )
        if department_filter:
            proposals = proposals.filter(department__name=department_filter)

        from .services.reports import get_analytics_summary
        data = get_analytics_summary(proposals, term_number)
        return Response(data)


class CurrentEmployeeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # UserProfileベースのユーザーの場合
        user_profile = getattr(request.user, "profile", None)
        if user_profile:
            # UserSerializerを使用してユーザー情報を返す
            user_data = UserSerializer(request.user).data
            return Response(user_data)

        # 従来のEmployeeベースのユーザーの場合
        employee = getattr(request.user, "employee_profile", None)
        if not employee:
            return Response({"detail": "profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # EmployeeシリアライザーからユーザーPermissionsを取得
        employee_data = EmployeeSerializer(employee).data

        # ユーザーの権限を追加
        user_permissions = UserPermissionSerializer(
            request.user.permissions.all(),
            many=True
        ).data

        # employee_dataのpermissionsを上書き
        employee_data['permissions'] = user_permissions

        return Response(employee_data)


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("department")
    serializer_class = EmployeeSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        department_id = self.request.query_params.get("department")
        code = self.request.query_params.get("code")
        keyword = self.request.query_params.get("q")
        include_inactive = self.request.query_params.get("include_inactive")

        if code:
            queryset = queryset.filter(code__iexact=code)

        if keyword:
            queryset = queryset.filter(
                Q(code__icontains=keyword)
                | Q(name__icontains=keyword)
                | Q(email__icontains=keyword)
            )

        if department_id:
            # Get all descendant departments of the selected department
            try:
                selected_dept = Department.objects.get(id=department_id)
                descendant_ids = self._get_descendant_ids(selected_dept)

                # Get department names for filtering CharField columns
                dept_names = list(Department.objects.filter(id__in=descendant_ids).values_list('name', flat=True))

                # Filter by the most specific affiliation (priority: team > group > department)
                queryset = queryset.filter(
                    # 1. If team has value, filter by team
                    (~Q(team='') & Q(team__in=dept_names)) |
                    # 2. If team is empty but group has value, filter by group
                    (Q(team='') & ~Q(group='') & Q(group__in=dept_names)) |
                    # 3. If both team and group are empty, filter by department
                    (Q(team='') & Q(group='') & Q(department_id__in=descendant_ids))
                )
            except Department.DoesNotExist:
                queryset = queryset.none()

        if not include_inactive:
            return queryset.filter(is_active=True)
        return queryset

    def _get_descendant_ids(self, department):
        """Get all descendant department IDs including the department itself."""
        ids = {department.id}
        children = Department.objects.filter(parent=department)
        for child in children:
            ids.update(self._get_descendant_ids(child))
        return ids


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'detail': 'ユーザー名とパスワードを入力してください'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({'detail': '認証に失敗しました'}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)

        # UserProfileベースのユーザー（新システム）の場合
        user_profile = getattr(user, "profile", None)
        if user_profile:
            user_data = UserSerializer(user).data
            return Response({
                'username': user.username,
                'name': user.first_name or user.username,
                'profile': user_data.get('profile'),
                'permissions': user_data.get('permissions', [])
            })

        # 従来のEmployeeベースのユーザーの場合
        employee = getattr(user, 'employee_profile', None)
        employee_data = EmployeeSerializer(employee).data if employee else None

        # ユーザーの権限を追加
        if employee_data:
            user_permissions = UserPermissionSerializer(
                user.permissions.all(),
                many=True
            ).data
            employee_data['permissions'] = user_permissions

        return Response({'username': user.username, 'employee': employee_data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'detail': 'logged out'})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related(
        "employee_profile__department",
        "profile__responsible_department"
    ).prefetch_related("permissions")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        # 全てのアクティブなユーザーを返す
        return super().get_queryset().filter(is_active=True)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserCreateUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=["get", "patch"], url_path="me", permission_classes=[IsAuthenticated])
    def me(self, request):
        """現在ログイン中のユーザーが自分のプロフィールを参照/更新する"""
        user = request.user
        if request.method.lower() == "get":
            return Response(UserSerializer(user).data)

        data = request.data or {}
        # 更新可能な項目のみ反映
        allowed_user_fields = {"first_name", "email"}
        for field in allowed_user_fields:
            if field in data:
                setattr(user, field, data.get(field) or "")
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        # profileフィールドは分けて受け取る（フロント送信時の簡便さ優先）
        profile_map = {
            "profile_email": "email",
            "profile_responsible_department": "responsible_department_id",
            "smtp_host": "smtp_host",
            "smtp_port": "smtp_port",
            "smtp_user": "smtp_user",
            "smtp_password": "smtp_password",
        }
        updated = False
        for key, attr in profile_map.items():
            if key in data:
                setattr(profile, attr, data.get(key) or None)
                updated = True
        if updated:
            profile.save()

        return Response(UserSerializer(user).data)


class UserPermissionViewSet(viewsets.ModelViewSet):
    queryset = UserPermission.objects.select_related("user__employee_profile__department")
    serializer_class = UserPermissionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset


