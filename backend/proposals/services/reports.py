from __future__ import annotations

import ast
from datetime import datetime
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, InvalidOperation
from collections import defaultdict
from typing import Iterable, Any

import pandas as pd
from django.utils import timezone

from proposals.models import ImprovementProposal, ProposalApproval
from proposals.services import fiscal

SUMMARY_COLUMNS = [
    "期", "四半期", "通し番号", "年", "月", "日", "提案部門",
    "効果部門", "提案者", "社員", "派遣", "実習生", "改善テーマ",
    "マインド", "アイデア", "ヒント", "SDGs", "安全", "判定区分",
    "保留", "提案ポイント", "報奨金", "月額効果[¥/月]",
    "削減工数[Hr/月]", "出金", "効果内容・効果算出"
]


def generate_term_report(proposals: Iterable[ImprovementProposal], term_number: int) -> BytesIO:
    # 1. Build the main summary dataframe
    summary_df, raw_df = build_summary_dataframe(proposals, term_number)
    
    # 2. Build derived summaries
    person_summary = build_person_summary(raw_df)
    department_summary = build_department_month_matrix(raw_df, term_number)

    # 3. Write to Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="実績まとめ", index=False, startrow=4)
        summary_sheet = writer.sheets["実績まとめ"]
        summary_sheet["A1"] = f"{term_number}期_改善実績まとめ"
        summary_sheet["A2"] = f"対象期: {term_number}期"
        summary_sheet["A3"] = f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        summary_sheet["A4"] = f"登録件数: {len(summary_df)}"

        person_summary.to_excel(writer, sheet_name="部署別氏名一覧", index=False)
        department_summary.to_excel(writer, sheet_name="特殊ポイント判定", index=False)

    buffer.seek(0)
    return buffer


def build_summary_dataframe(proposals: Iterable[ImprovementProposal], term_number: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns a tuple of (formatted_summary_df, raw_data_df).
    raw_data_df contains more columns and is used for subsequent aggregations.
    """
    rows = []
    for i, p in enumerate(proposals, 1):
        submitted_at = p.submitted_at.astimezone(timezone.get_current_timezone()) if p.submitted_at else None
        
        # Approvals
        approvals = {a.stage: a for a in p.approvals.all()}
        manager_approval = approvals.get(ProposalApproval.Stage.MANAGER)
        committee_approval = approvals.get(ProposalApproval.Stage.COMMITTEE)
        
        # Scores (prioritize committee, then manager)
        mindset = getattr(committee_approval, "mindset_score", None) or getattr(manager_approval, "mindset_score", None)
        idea = getattr(committee_approval, "idea_score", None) or getattr(manager_approval, "idea_score", None)
        hint = getattr(committee_approval, "hint_score", None) or getattr(manager_approval, "hint_score", None)

        # Classification (prioritize committee, then proposal)
        classification = p.committee_classification or p.proposal_classification or "通常"

        # Department info
        dept_name = p.department.name if p.department else ""
        contributors = getattr(p, "_prefetched_objects_cache", {}).get("contributors")
        if contributors is None:
            contributors = list(p.contributors.select_related("employee__department"))

        # Contributing business (Effect Department)
        # Assuming 'contribution_business' might be stored as a string or list in JSON
        # Adapting logic to handle simple string for now, or parse if it looks like a list
        effect_dept = _normalize_text_list(p.contribution_business)
        effect_display = effect_dept.split(",")[0].strip() if effect_dept else ""

        row = {
            "obj": p,  # Keep reference for debugging if needed
            "期": p.term or (fiscal.fiscal_term(submitted_at) if submitted_at else None),
            "四半期": p.quarter or (fiscal.fiscal_quarter(submitted_at) if submitted_at else None),
            "通し番号": p.serial_number or i,
            "年": submitted_at.year if submitted_at else None,
            "月": submitted_at.month if submitted_at else None,
            "日": submitted_at.day if submitted_at else None,
            "提案部門": dept_name,
            "効果部門": effect_display,
            "提案者": p.proposer_name,
            "社員": "○",  # Fixed as per original logic
            "派遣": "",
            "実習生": "",
            "改善テーマ": p.deployment_item,
            "マインドセット": mindset,
            "アイデア工夫": idea,
            "みんなのヒント": hint,
            "SDGs": "",
            "安全": "",
            "判定区分": classification,
            "保留": "",
            "提案ポイント": p.classification_points or 0,
            "報奨金": "",
            "効果額": p.effect_amount or 0.0,
            "削減時間": p.reduction_hours or 0.0,
            "出金": "",
            "効果内容・効果算出": p.effect_details or "",
            "提出日時_dt": submitted_at,
            "contributors": contributors,
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=SUMMARY_COLUMNS), pd.DataFrame()

    raw_df = pd.DataFrame(rows)
    
    # Filter by term just in case, though the query should have handled it
    raw_df = raw_df[raw_df["期"] == term_number].copy()
    
    # Build the formatted summary dataframe
    summary_rows = []
    for _, row in raw_df.iterrows():
        summary_rows.append({
            "期": row["期"],
            "四半期": row["四半期"],
            "通し番号": row["通し番号"],
            "年": row["年"],
            "月": row["月"],
            "日": row["日"],
            "提案部門": row["提案部門"],
            "効果部門": row["効果部門"],
            "提案者": row["提案者"],
            "社員": row["社員"],
            "派遣": row["派遣"],
            "実習生": row["実習生"],
            "改善テーマ": row["改善テーマ"],
            "マインド": _safe_int(row["マインドセット"]),
            "アイデア": _safe_int(row["アイデア工夫"]),
            "ヒント": _safe_int(row["みんなのヒント"]),
            "SDGs": row["SDGs"],
            "安全": row["安全"],
            "判定区分": row["判定区分"],
            "保留": row["保留"],
            "提案ポイント": row["提案ポイント"],
            "報奨金": row["報奨金"],
            "月額効果[¥/月]": row["効果額"],
            "削減工数[Hr/月]": row["削減時間"],
            "出金": row["出金"],
            "効果内容・効果算出": row["効果内容・効果算出"]
        })
    
    return pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS), raw_df


def build_person_summary(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "部署", "提案者", "件数", "平均マインド", "平均アイデア",
        "平均ヒント", "合計ポイント", "提案ポイント", "削減時間合計[Hr/月]", "効果額合計[¥/月]"
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    dept_col, person_col, count_col, mindset_col, idea_col, hint_col, points_col, proposal_points_col, reduction_col, effect_col = columns
    summary: dict[tuple[str, str], dict[str, Decimal]] = {}

    for _, row in df.iterrows():
        contributors = row.get("contributors") or []
        dept_default = row.get("提案部門") or "未設定"
        person_default = row.get("提案者") or "未設定"
        reduction_val = _to_decimal(row.get("削減時間")) or Decimal("0")
        effect_val = _to_decimal(row.get("効果額")) or Decimal("0")
        mindset = _to_decimal(row.get("マインドセット"))
        idea = _to_decimal(row.get("アイデア工夫"))
        hint = _to_decimal(row.get("みんなのヒント"))
        proposal_points_total = _to_decimal(row.get("提案ポイント")) or Decimal("0")

        def ensure_entry(dept_name, person_name):
            key = (dept_name or "未設定", person_name or "未設定")
            if key not in summary:
                summary[key] = {
                    "count": Decimal("0"),
                    "reduction": Decimal("0"),
                    "effect": Decimal("0"),
                    "mindset_sum": Decimal("0"),
                    "mindset_w": Decimal("0"),
                    "idea_sum": Decimal("0"),
                    "idea_w": Decimal("0"),
                    "hint_sum": Decimal("0"),
                    "hint_w": Decimal("0"),
                    "proposal_points": Decimal("0"),
                }
            return summary[key]

        if contributors:
            share_weights = _share_weights(contributors)
            contributor_count = len(contributors) or 1
            for contrib, share_ratio in zip(contributors, share_weights):
                employee = getattr(contrib, "employee", None)
                dept_name = getattr(getattr(employee, "department", None), "name", None) or dept_default
                person_name = getattr(employee, "name", None) or person_default
                entry = ensure_entry(dept_name, person_name)
                entry["count"] += share_ratio

                if mindset is not None:
                    entry["mindset_sum"] += mindset * share_ratio
                    entry["mindset_w"] += share_ratio
                if idea is not None:
                    entry["idea_sum"] += idea * share_ratio
                    entry["idea_w"] += share_ratio
                if hint is not None:
                    entry["hint_sum"] += hint * share_ratio
                    entry["hint_w"] += share_ratio

                if getattr(contrib, "is_primary", False):
                    entry["reduction"] += reduction_val
                    entry["effect"] += effect_val
                points_share_val = _to_decimal(getattr(contrib, "classification_points_share", None))
                if points_share_val is None:
                    points_share_val = (proposal_points_total / Decimal(contributor_count)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                entry["proposal_points"] += points_share_val
        else:
            entry = ensure_entry(dept_default, person_default)
            entry["count"] += Decimal("1")
            if mindset is not None:
                entry["mindset_sum"] += mindset
                entry["mindset_w"] += Decimal("1")
            if idea is not None:
                entry["idea_sum"] += idea
                entry["idea_w"] += Decimal("1")
            if hint is not None:
                entry["hint_sum"] += hint
                entry["hint_w"] += Decimal("1")
            entry["reduction"] += reduction_val
            entry["effect"] += effect_val
            entry["proposal_points"] += proposal_points_total

    rows = []

    def avg(sum_val: Decimal, weight: Decimal):
        if weight == 0:
            return ""
        return float((sum_val / weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def _decimal_or_zero(val: float | str):
        if val == "" or val is None:
            return Decimal("0")
        return _to_decimal(val) or Decimal("0")

    for (dept_name, person_name), values in summary.items():
        mindset_avg = avg(values["mindset_sum"], values["mindset_w"])
        idea_avg = avg(values["idea_sum"], values["idea_w"])
        hint_avg = avg(values["hint_sum"], values["hint_w"])

        points_total: float | str = ""
        if any(val != "" for val in (mindset_avg, idea_avg, hint_avg)):
            total_points = _decimal_or_zero(mindset_avg) + _decimal_or_zero(idea_avg) + _decimal_or_zero(hint_avg)
            points_total = float(total_points.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        rows.append({
            dept_col: dept_name,
            person_col: person_name,
            count_col: float(values["count"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            mindset_col: mindset_avg,
            idea_col: idea_avg,
            hint_col: hint_avg,
            points_col: points_total,
            proposal_points_col: float(values["proposal_points"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            reduction_col: float(values["reduction"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            effect_col: int(values["effect"].quantize(Decimal("0"))),
        })

    result = pd.DataFrame(rows, columns=columns)
    return result.sort_values([dept_col, person_col]).reset_index(drop=True)
def build_department_month_matrix(df: pd.DataFrame, term_number: int) -> pd.DataFrame:
    month_numbers = fiscal.fiscal_month_sequence()
    month_columns = [f"{month}月" for month in month_numbers]
    columns = ["部署"] + month_columns + ["年間合計"]
    
    if df.empty:
        return pd.DataFrame(columns=columns)

    dept_totals: dict[str, dict[int, Decimal]] = defaultdict(lambda: {m: Decimal("0") for m in month_numbers})

    for _, row in df.iterrows():
        submitted = row.get("提出日時_dt")
        if submitted is None or pd.isna(submitted):
            continue
        month = getattr(submitted, "month", None)
        if month not in month_numbers:
            continue

        contributors = row.get("contributors") or []
        dept_default = row.get("提案部門") or "未設定"

        if contributors:
            share_weights = _share_weights(contributors)
            for contrib, share_ratio in zip(contributors, share_weights):
                employee = getattr(contrib, "employee", None)
                dept_name = getattr(getattr(employee, "department", None), "name", None) or dept_default
                dept_totals[dept_name][month] += share_ratio
        else:
            dept_totals[dept_default][month] += Decimal("1")

    rows = []
    for dept_name, month_map in dept_totals.items():
        row = {"部署": dept_name}
        total = Decimal("0")
        for month in month_numbers:
            value = month_map.get(month, Decimal("0"))
            value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            row[f"{month}月"] = float(value)
            total += value
        row["年間合計"] = float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        rows.append(row)

    return pd.DataFrame(rows, columns=columns).sort_values("部署").reset_index(drop=True)
def get_analytics_summary(proposals: Iterable[ImprovementProposal], term_number: int) -> dict[str, Any]:
    """
    Generate analytics data for the frontend dashboard.
    Returns a dictionary containing list of records for person summary and department matrix.
    """
    _, raw_df = build_summary_dataframe(proposals, term_number)
    
    person_summary = build_person_summary(raw_df)
    department_summary = build_department_month_matrix(raw_df, term_number)
    
    return {
        "person_summary": person_summary.to_dict(orient="records"),
        "department_summary": department_summary.to_dict(orient="records"),
    }


def _to_decimal(value: Any) -> Decimal | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _normalize_text_list(value: Any) -> str:
    """Normalize text that might be a list string or list."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, list):
                    return ", ".join(str(v) for v in parsed if v)
            except (ValueError, SyntaxError):
                return text
        return text
    return ""


def _safe_int(value: Any) -> int | str:
    try:
        if pd.isna(value) or value == "":
            return ""
        return int(float(value))
    except (TypeError, ValueError):
        return ""


def _share_weights(contributors: list[Any]) -> list[Decimal]:
    """
    Calculate share ratios that always sum to 1.00 (rounded to 2 decimals).
    Falls back to equal distribution when no share is provided.
    """
    if not contributors:
        return []

    shares: list[Decimal] = []
    for contrib in contributors:
        share = _to_decimal(getattr(contrib, "share_percent", None)) or Decimal("0")
        shares.append(share if share > 0 else Decimal("0"))

    total_share = sum(shares)
    if total_share <= 0:
        shares = [Decimal("100") / Decimal(len(contributors)) for _ in contributors]
        total_share = sum(shares)

    normalized = [share / total_share for share in shares]
    hundredths = [value * Decimal("100") for value in normalized]
    integer_parts = [val.to_integral_value(rounding=ROUND_DOWN) for val in hundredths]
    fractions = [val - integer for val, integer in zip(hundredths, integer_parts)]

    remaining = int(Decimal("100") - sum(integer_parts))
    order = sorted(range(len(fractions)), key=lambda idx: fractions[idx], reverse=True)
    for idx in order[:remaining]:
        integer_parts[idx] += 1

    return [Decimal(int_part) / Decimal("100") for int_part in integer_parts]
