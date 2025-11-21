from __future__ import annotations

from datetime import datetime, time

from django.db.models import Count, F, Q
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
from .models import Department, Employee, UserPermission, ImprovementProposal, ProposalApproval
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


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("parent")
    serializer_class = DepartmentSerializer
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

    def get_queryset(self):
        queryset = (
            ImprovementProposal.objects.select_related(
                "department", "section", "group", "team", "proposer", "created_by"
            )
            .prefetch_related("approvals__confirmed_by")
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
                queryset = queryset.filter(submitted_at__range=(start_dt, end_dt))
            except ValueError:
                pass

        stage_choices = dict(ProposalApproval.Stage.choices)
        status_choices = dict(ProposalApproval.Status.choices)

        if stage in stage_choices:
            queryset = queryset.filter(approvals__stage=stage)
            if status_value in status_choices:
                queryset = queryset.filter(approvals__status=status_value)
            queryset = queryset.distinct()
        elif status_value == "completed":
            queryset = queryset.filter(approved_count=F("total_approvals"))

        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        proposal = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        stage = data["stage"]
        approval = ProposalApproval.objects.filter(proposal=proposal, stage=stage).first()
        if not approval:
            return Response({"detail": "Invalid stage"}, status=status.HTTP_400_BAD_REQUEST)
        approval.status = data["status"]
        approval.comment = data.get("comment", "")
        approval.confirmed_name = data["confirmed_name"]
        approval.confirmed_at = timezone.now()
        approval.confirmed_by = getattr(request.user, "employee_profile", None)
        scores = data.get("scores") or {}
        if stage in {ProposalApproval.Stage.MANAGER, ProposalApproval.Stage.COMMITTEE}:
            approval.mindset_score = scores.get("mindset")
            approval.idea_score = scores.get("idea")
            approval.hint_score = scores.get("hint")
        else:
            approval.mindset_score = approval.idea_score = approval.hint_score = None
        approval.save()
        refreshed = self.get_serializer(proposal)
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
            ImprovementProposal.objects.filter(submitted_at__range=(start_dt, end_dt))
            .select_related("department", "section", "group", "team", "proposer")
            .prefetch_related("approvals__confirmed_by")
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
            ImprovementProposal.objects.filter(submitted_at__range=(start_dt, end_dt))
            .select_related("department", "section", "group", "team", "proposer")
            .prefetch_related("approvals__confirmed_by")
        )
        
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


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Employee.objects.select_related("department")
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        department_id = self.request.query_params.get("department")

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

        return queryset.filter(is_active=True)

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


