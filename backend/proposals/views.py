from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Department, Proposal
from .serializers import DepartmentSerializer, ProposalSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class ProposalViewSet(viewsets.ModelViewSet):
    queryset = Proposal.objects.select_related("department").all()
    serializer_class = ProposalSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        stage = self.request.query_params.get("stage")
        status_value = self.request.query_params.get("status")
        keyword = self.request.query_params.get("q")

        if stage in {"supervisor", "chief", "manager", "committee"} and status_value:
            queryset = queryset.filter(**{f"{stage}_status": status_value})

        if keyword:
            queryset = queryset.filter(
                Q(management_no__icontains=keyword) | Q(title__icontains=keyword)
            )

        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """承認/差戻し操作を簡単に行うためのカスタムアクション."""

        proposal = self.get_object()
        stage = request.data.get("stage")
        status_value = request.data.get("status")
        comment = request.data.get("comment", "")
        score = request.data.get("score")
        now = timezone.now()

        if stage not in {"supervisor", "chief", "manager", "committee"}:
            return Response(
                {"detail": "stage パラメータが不正です"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if status_value not in dict(Proposal.StageStatus.choices):
            return Response(
                {"detail": "status パラメータが不正です"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        setattr(proposal, f"{stage}_status", status_value)
        setattr(proposal, f"{stage}_comment", comment)
        setattr(proposal, f"{stage}_checked_at", now)

        if stage == "manager" and status_value == Proposal.StageStatus.APPROVED:
            scores = score or {}
            proposal.manager_mindset_score = scores.get("mindset")
            proposal.manager_idea_score = scores.get("idea")
            proposal.manager_hint_score = scores.get("hint")

        proposal.save()
        serializer = self.get_serializer(proposal)
        return Response(serializer.data)
