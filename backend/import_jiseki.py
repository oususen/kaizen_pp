import math
import os
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kaizen_backend.settings")
import django  # noqa

django.setup()

from django.utils import timezone

from proposals.models import (
    Department,
    Employee,
    ImprovementProposal,
    ProposalApproval,
)
from proposals.views import calculate_classification_points


def _clean_money(value):
    if pd.isna(value):
        return None
    text = str(value)
    digits = re.sub(r"[^\d\.]", "", text)
    if not digits:
        return None
    try:
        return Decimal(digits)
    except Exception:
        return None


def _clean_float(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def _ensure_department(name: str | None):
    if not name or str(name).strip() == "":
        return None
    name = str(name).strip()
    if name.endswith("事業部") or name.endswith("課"):
        target = name
    else:
        target = f"{name}事業部"
    dept = Department.objects.filter(name=target, level="division").first()
    if not dept:
        dept = Department.objects.create(name=target, level="division", display_id=0)
    return dept


def _find_employee(name: str | None, department=None):
    if not name or str(name).strip() == "":
        return None
    qs = Employee.objects.filter(name=name)
    if department:
        qs = qs.filter(department=department)
    return qs.first()


def import_jiseki(csv_path: Path):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    results = {"created": 0, "skipped": 0}

    classification_map = {
        "努力": ImprovementProposal.ProposalClassification.EFFORT,
        "努力提案": ImprovementProposal.ProposalClassification.EFFORT,
        "アイデア": ImprovementProposal.ProposalClassification.IDEA,
        "アイディア": ImprovementProposal.ProposalClassification.IDEA,
        "優秀": ImprovementProposal.ProposalClassification.EXCELLENT,
    }

    for idx, row in df.iterrows():
        term = int(row.get("期", 0) or 0)
        quarter = _clean_float(row.get("四半期"))
        serial = _clean_float(row.get("通し"))
        year = int(row.get("年", 0) or 0)
        month = int(row.get("月", 1) or 1)
        day = int(row.get("日", 1) or 1)
        submitted_at = datetime(year, month, day, 9, 0, 0)

        dept = _ensure_department(row.get("事業部") or row.get("部、課"))
        proposer_name = str(row.get("氏名") or "").strip()
        employee = _find_employee(proposer_name, dept)

        classification_label = str(row.get("判定区分") or "").strip()
        classification_value = classification_map.get(classification_label, ImprovementProposal.ProposalClassification.EFFORT)
        points = calculate_classification_points(classification_value)

        reduction_hours = _clean_float(row.get("Unnamed: 22"))
        effect_amount = _clean_money(row.get("Unnamed: 24"))
        reward_amount = _clean_money(row.get("Unnamed: 23"))

        theme = str(row.get("Unnamed: 14") or "").strip()
        # Build a stable management number to avoid duplicates
        mgmt = f"IMP-{term}-{int(serial) if not math.isnan(serial) else idx:04d}-{idx:03d}"
        if ImprovementProposal.objects.filter(management_no=mgmt).exists():
            results["skipped"] += 1
            continue

        proposal = ImprovementProposal.objects.create(
            management_no=mgmt,
            submitted_at=submitted_at,
            department=dept,
            proposer=employee,
            proposer_name=proposer_name or "不明",
            problem_summary=theme or "（未入力）",
            improvement_plan=theme or "（未入力）",
            improvement_result="",
            effect_details=theme or "",
            reduction_hours=reduction_hours,
            effect_amount=effect_amount,
            proposal_classification=classification_value,
            classification_points=points,
            term=term or None,
            quarter=int(quarter) if quarter is not None else None,
            serial_number=int(serial) if serial is not None and not math.isnan(serial) else None,
            contribution_business=row.get("事業部") or "",
            mindset_score=_clean_float(row.get("マインド")),
            idea_score=_clean_float(row.get("アイデア")),
            hint_score=_clean_float(row.get("ヒント")),
        )

        # Create approvals (all approved)
        for stage in ProposalApproval.Stage:
            ProposalApproval.objects.create(
                proposal=proposal,
                stage=stage,
                status=ProposalApproval.Status.APPROVED,
                confirmed_name="過去実績取込",
                confirmed_at=submitted_at,
                mindset_score=proposal.mindset_score if stage == ProposalApproval.Stage.MANAGER else None,
                idea_score=proposal.idea_score if stage == ProposalApproval.Stage.MANAGER else None,
                hint_score=proposal.hint_score if stage == ProposalApproval.Stage.MANAGER else None,
                sdgs_flag=bool(row.get("SDGs")) if stage == ProposalApproval.Stage.MANAGER else False,
                safety_flag=bool(row.get("安全")) if stage == ProposalApproval.Stage.MANAGER else False,
            )

        results["created"] += 1

    return results


if __name__ == "__main__":
    csv_file = Path(__file__).resolve().parent.parent / "jiseki.csv"
    summary = import_jiseki(csv_file)
    print("import summary:", summary)
