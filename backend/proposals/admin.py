from django.contrib import admin

from .models import (
    Department,
    Employee,
    ImprovementProposal,
    Proposal,
    ProposalApproval,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "parent")
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "role", "is_active")
    list_filter = ("role", "department", "is_active")
    search_fields = ("code", "name", "email")


@admin.register(ImprovementProposal)
class ImprovementProposalAdmin(admin.ModelAdmin):
    list_display = (
        "management_no",
        "proposer_name",
        "department",
        "group",
        "team",
        "submitted_at",
    )
    list_filter = ("department", "group", "team", "submitted_at")
    search_fields = ("management_no", "proposer_name", "deployment_item")
    autocomplete_fields = ("department", "section", "group", "team", "proposer")


@admin.register(ProposalApproval)
class ProposalApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "proposal",
        "stage",
        "status",
        "confirmed_name",
        "confirmed_at",
    )
    list_filter = ("stage", "status")
    autocomplete_fields = ("proposal", "confirmed_by")


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = (
        "management_no",
        "title",
        "proposer_name",
        "department",
        "supervisor_status",
        "manager_status",
    )
    list_filter = (
        "supervisor_status",
        "chief_status",
        "manager_status",
        "committee_status",
    )
    search_fields = ("management_no", "title", "proposer_name")
