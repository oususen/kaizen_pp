from __future__ import annotations

import datetime

from django.db.models import F
from django.utils import timezone

from proposals.models import ImprovementProposal


def generate_management_no() -> str:
    """Generate a unique management number yyyyMMdd-XXX."""
    today = datetime.date.today()
    prefix = today.strftime("%Y%m%d")
    existing = (
        ImprovementProposal.objects.filter(management_no__startswith=f"{prefix}-")
        .order_by("-management_no")
        .values_list("management_no", flat=True)
        .first()
    )
    if existing:
        try:
            last_seq = int(existing.split("-")[-1])
        except ValueError:
            last_seq = 0
    else:
        last_seq = 0
    return f"{prefix}-{last_seq + 1:03d}"
