from __future__ import annotations

import ast
from datetime import datetime
from io import BytesIO
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
    "削減工数[Hr/月]", "出金", "注記"
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

        # Department info
        dept_name = p.department.name if p.department else ""
        
        # Contributing business (Effect Department)
        # Assuming 'contributing_business' might be stored as a string or list in JSON
        # Adapting logic to handle simple string for now, or parse if it looks like a list
        effect_dept = _normalize_text_list(p.contributing_business)
        effect_display = effect_dept.split(",")[0].strip() if effect_dept else ""

        row = {
            "obj": p,  # Keep reference for debugging if needed
            "期": fiscal.fiscal_term(submitted_at) if submitted_at else None,
            "四半期": fiscal.fiscal_quarter(submitted_at) if submitted_at else None,
            "通し番号": i,
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
            "判定区分": "通常",
            "保留": "",
            "提案ポイント": "",
            "報奨金": "",
            "効果額": p.effect_amount or 0.0,
            "削減時間": p.reduction_hours or 0.0,
            "出金": "",
            "注記": p.comment,
            "提出日時_dt": submitted_at,
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
            "注記": row["注記"]
        })
    
    return pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS), raw_df


def build_person_summary(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "部署", "提案者", "件数", "平均マインド", "平均アイデア",
        "平均ヒント", "削減時間合計[Hr/月]", "効果額合計[¥/月]"
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    working = df.copy()
    working["部署"] = working["提案部門"].fillna("未設定")
    working["提案者"] = working["提案者"].replace("", "未設定")
    
    # Ensure numeric types
    for col in ["削減時間", "効果額", "マインドセット", "アイデア工夫", "みんなのヒント"]:
        working[col] = pd.to_numeric(working[col], errors="coerce")

    rows = []
    for (dept, person), group in working.groupby(["部署", "提案者"]):
        rows.append({
            "部署": dept,
            "提案者": person,
            "件数": int(group.shape[0]),
            "平均マインド": round(group["マインドセット"].mean(skipna=True), 2)
            if group["マインドセット"].notna().any() else "",
            "平均アイデア": round(group["アイデア工夫"].mean(skipna=True), 2)
            if group["アイデア工夫"].notna().any() else "",
            "平均ヒント": round(group["みんなのヒント"].mean(skipna=True), 2)
            if group["みんなのヒント"].notna().any() else "",
            "削減時間合計[Hr/月]": round(group["削減時間"].sum(), 2),
            "効果額合計[¥/月]": int(group["効果額"].sum()),
        })

    result = pd.DataFrame(rows, columns=columns)
    return result.sort_values(["部署", "提案者"]).reset_index(drop=True)


def build_department_month_matrix(df: pd.DataFrame, term_number: int) -> pd.DataFrame:
    month_numbers = fiscal.fiscal_month_sequence()
    month_columns = [f"{month}月" for month in month_numbers]
    columns = ["部署"] + month_columns + ["年間合計"]
    
    if df.empty:
        return pd.DataFrame(columns=columns)

    working = df.copy()
    working["部署"] = working["提案部門"].fillna("未設定")
    working = working[working["提出日時_dt"].notna()]

    if working.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for dept, group in working.groupby("部署"):
        row = {"部署": dept}
        total = 0
        for month in month_numbers:
            # Check month from '提出日時_dt'
            count = group[group["提出日時_dt"].dt.month == month].shape[0]
            row[f"{month}月"] = int(count)
            total += count
        row["年間合計"] = int(total)
        rows.append(row)

    result = pd.DataFrame(rows)
    for column in columns:
        if column not in result.columns:
            result[column] = 0 if column != "部署" else ""
            
    return result[columns].sort_values("部署").reset_index(drop=True)


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
