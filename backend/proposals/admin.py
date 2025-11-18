from django.contrib import admin

from .models import Department, Proposal


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "parent")
    search_fields = ("name",)


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("management_no", "title", "proposer_name", "department", "supervisor_status", "manager_status")
    list_filter = ("supervisor_status", "chief_status", "manager_status", "committee_status")
    search_fields = ("management_no", "title", "proposer_name")
