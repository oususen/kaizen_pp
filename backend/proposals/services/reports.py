from __future__ import annotations

from io import BytesIO
from typing import Iterable

import pandas as pd

from proposals.models import ImprovementProposal, ProposalApproval

REPORT_COLUMNS = [
    "管理No",
    "提出日時",
    "提案者",
    "所属",
    "テーマ",
    "削減時間[Hr/月]",
    "効果額[円/月]",
    "監督者ステータス",
    "係長ステータス",
    "部門長ステータス",
    "改善委員ステータス",
]


def generate_term_report(proposals: Iterable[ImprovementProposal], term_number: int) -> BytesIO:
    rows = []
    for proposal in proposals:
        approvals = {approval.stage: approval for approval in proposal.approvals.all()}
        division_name = proposal.department.name if proposal.department else ""
        section_name = proposal.section.name if proposal.section else ""
        group_name = proposal.group.name if proposal.group else ""
        team_name = proposal.team.name if proposal.team else ""
        affiliation = " / ".join([n for n in [division_name, section_name, group_name, team_name] if n])
        rows.append(
            {
                "管理No": proposal.management_no,
                "提出日時": proposal.submitted_at.strftime("%Y-%m-%d %H:%M"),
                "提案者": proposal.proposer_name,
                "所属": affiliation,
                "テーマ": proposal.deployment_item,
                "削減時間[Hr/月]": proposal.reduction_hours or "",
                "効果額[円/月]": proposal.effect_amount or "",
                "監督者ステータス": _format_stage(approvals.get(ProposalApproval.Stage.SUPERVISOR)),
                "係長ステータス": _format_stage(approvals.get(ProposalApproval.Stage.CHIEF)),
                "部門長ステータス": _format_stage(approvals.get(ProposalApproval.Stage.MANAGER)),
                "改善委員ステータス": _format_stage(approvals.get(ProposalApproval.Stage.COMMITTEE)),
            }
        )
    df = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    buffer = BytesIO()
    sheet_name = f"{term_number}期"
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer


def _format_stage(approval: ProposalApproval | None) -> str:
    if not approval:
        return ""
    base = dict(ProposalApproval.Status.choices).get(approval.status, approval.status)
    if approval.confirmed_name:
        base += f" ({approval.confirmed_name})"
    return base

