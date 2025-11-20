from django import forms
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


class EmployeeAdminForm(forms.ModelForm):
    """従業員編集フォーム - 事業部/係/班をドロップダウンで選択"""

    division_dept = forms.ModelChoiceField(
        queryset=Department.objects.filter(level='division'),
        required=False,
        label='事業部/課',
        help_text='事業部を選択してください'
    )
    group_dept = forms.ModelChoiceField(
        queryset=Department.objects.filter(level='group'),
        required=False,
        label='係',
        help_text='係を選択してください'
    )
    team_dept = forms.ModelChoiceField(
        queryset=Department.objects.filter(level='team'),
        required=False,
        label='班',
        help_text='班を選択してください'
    )

    class Meta:
        model = Employee
        exclude = ['division', 'group', 'team']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 既存データがある場合、選択肢を設定
        if self.instance and self.instance.pk:
            if self.instance.division:
                try:
                    dept = Department.objects.get(name=self.instance.division, level='division')
                    self.fields['division_dept'].initial = dept
                except Department.DoesNotExist:
                    pass
            if self.instance.group:
                try:
                    dept = Department.objects.get(name=self.instance.group, level='group')
                    self.fields['group_dept'].initial = dept
                except Department.DoesNotExist:
                    pass
            if self.instance.team:
                try:
                    dept = Department.objects.get(name=self.instance.team, level='team')
                    self.fields['team_dept'].initial = dept
                except Department.DoesNotExist:
                    pass

    def save(self, commit=True):
        # ドロップダウンで選択された値をCharFieldに保存
        instance = super().save(commit=False)
        if self.cleaned_data.get('division_dept'):
            instance.division = self.cleaned_data['division_dept'].name
        if self.cleaned_data.get('group_dept'):
            instance.group = self.cleaned_data['group_dept'].name
        if self.cleaned_data.get('team_dept'):
            instance.team = self.cleaned_data['team_dept'].name
        if commit:
            instance.save()
        return instance


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeAdminForm
    list_display = ("code", "name", "department", "division", "group", "team", "role", "is_active")
    list_filter = ("role", "department", "is_active")
    search_fields = ("code", "name", "email", "division", "group", "team")
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'code', 'name', 'email')
        }),
        ('所属情報', {
            'fields': ('department', 'division_dept', 'group_dept', 'team_dept', 'position')
        }),
        ('権限・ステータス', {
            'fields': ('role', 'is_active', 'joined_on')
        }),
    )


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
