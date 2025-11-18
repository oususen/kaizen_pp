import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
from io import BytesIO
import ast
import re
import config
from streamlit.errors import StreamlitSecretNotFoundError
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

# アプリの基本設定.
st.set_page_config(
    page_title="改善提案システム",
    page_icon="📝",
    layout="wide"
)

# セッション状態の初期化
if 'current_page' not in st.session_state:
    st.session_state.current_page = "提出用画面"
if 'selected_proposal' not in st.session_state:
    st.session_state.selected_proposal = None
if 'confirm_role' not in st.session_state:
    st.session_state.confirm_role = None

# 提案データを保存するCSVファイル（既存データ移行用）
DATA_FILE = "improvement_proposals.csv"
# 画像保存用ディレクトリ
IMAGE_DIR = "proposal_images"
TABLE_NAME = "improvement_proposals"
BASE_FISCAL_YEAR = 1973
FISCAL_YEAR_START_MONTH = 10
PROPOSAL_COLUMNS = [
    "管理No", "提出日時", "部門", "所属担当", "提案者",
    "展開項目", "問題点", "改善案", "改善結果",
    "削減時間", "効果額", "コメント", "貢献事業",
    "マインドセット", "アイデア工夫", "みんなのヒント",
    "改善前画像", "改善後画像",
    "監督者確認", "監督者確認者", "監督者コメント", "監督者確認日時",
    "係長確認", "係長確認者", "係長コメント", "係長確認日時",
    "部門長確認", "部門長確認者", "部門長コメント", "部門長確認日時",
    "改善委員確認", "改善委員確認者", "改善委員コメント", "改善委員確認日時"
]
SUMMARY_COLUMNS = [
    "期", "四半期", "通し番号", "年", "月", "日", "提案部門",
    "効果部門", "提案者", "社員", "派遣", "実習生", "改善テーマ",
    "マインド", "アイデア", "ヒント", "SDGs", "安全", "判定区分",
    "保留", "提案ポイント", "報奨金", "月額効果[¥/月]",
    "削減工数[Hr/月]", "出金", "注記"
]
DEPARTMENT_OPTIONS = [
    "プレス事業部", "製缶事業部", "塗装事業部", "FA事業部",
    "生産技術課", "品質管理課", "営業戦略課", "人事戦略課", "経営企画課"
]

# ディレクトリの初期化
os.makedirs(IMAGE_DIR, exist_ok=True)


def _read_mysql_settings():
    """st.secrets / .env（config.py）経由の環境変数から MySQL 接続情報を取得."""
    try:
        secrets_mysql = st.secrets["mysql"]
    except (StreamlitSecretNotFoundError, KeyError):
        secrets_mysql = None

    settings = dict(secrets_mysql) if secrets_mysql else config.get_mysql_settings()
    required_keys = ["host", "port", "database", "user", "password"]
    missing = [key for key in required_keys if not settings.get(key)]
    if missing:
        missing_display = ', '.join(missing)
        st.error(
            "MySQL接続情報が不足しています。st.secrets['mysql'] もしくは .env などの環境変数 "
            "(MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD) を設定してください。"
            f"未設定: {missing_display}"
        )
        return None
    return settings


def initialize_database(engine):
    """必要に応じてテーブルを生成し、CSVの既存データを移行する."""
    try:
        inspector = inspect(engine)
        if inspector.has_table(TABLE_NAME):
            return
    except SQLAlchemyError as exc:
        st.error(f"データベースの初期化に失敗しました: {exc}")
        st.stop()

    schema_df = pd.DataFrame(columns=PROPOSAL_COLUMNS)
    schema_df.head(0).to_sql(TABLE_NAME, engine, index=False, if_exists="replace")

    if os.path.exists(DATA_FILE):
        try:
            csv_df = pd.read_csv(DATA_FILE, encoding="utf-8-sig").fillna("")
            if not csv_df.empty:
                for col in PROPOSAL_COLUMNS:
                    if col not in csv_df.columns:
                        csv_df[col] = ""
                csv_df = csv_df[PROPOSAL_COLUMNS]
                csv_df.to_sql(TABLE_NAME, engine, index=False, if_exists="append")
        except Exception as exc:  # pylint: disable=broad-except
            st.warning(f"既存CSVの読み込みに失敗しました: {exc}")


@st.cache_resource
def get_engine():
    """MySQLエンジンを初期化して返却."""
    settings = _read_mysql_settings()
    if not settings:
        return None
    try:
        connection_url = URL.create(
            "mysql+pymysql",
            username=settings["user"],
            password=settings["password"],
            host=settings["host"],
            port=int(settings["port"]),
            database=settings["database"],
            query={"charset": "utf8mb4"},
        )
    except (TypeError, ValueError) as exc:
        st.error(f"接続情報の形式が正しくありません: {exc}")
        return None

    try:
        engine = create_engine(connection_url, pool_pre_ping=True)
        initialize_database(engine)
        return engine
    except SQLAlchemyError as exc:
        st.error(f"データベースに接続できません: {exc}")
        return None

# ナビゲーション
st.sidebar.title("📋 メニュー")
menu_options = ["提出用画面", "提出済み一覧", "監督者確認", "係長確認", "部門長確認", 
                "改善委員確認", "確認済み一覧"]
page = st.sidebar.radio(
    "画面選択",
    menu_options,
    index=menu_options.index(st.session_state.current_page)
)

# ページ遷移の処理
if page != st.session_state.current_page:
    st.session_state.current_page = page
    st.rerun()

# データ読み込み関数
def load_data():
    engine = get_engine()
    if engine is None:
        return pd.DataFrame(columns=PROPOSAL_COLUMNS)

    try:
        with engine.connect() as connection:
            df = pd.read_sql_table(TABLE_NAME, connection)
    except (ValueError, SQLAlchemyError) as exc:
        st.error(f"データの読み込みに失敗しました: {exc}")
        return pd.DataFrame(columns=PROPOSAL_COLUMNS)

    df = df.fillna("")
    for column in PROPOSAL_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    return df[PROPOSAL_COLUMNS]


# データ保存関数
def save_data(df):
    engine = get_engine()
    if engine is None:
        st.error("MySQL接続情報が未設定のため、データを保存できません。")
        return

    persist_df = df.copy()
    for column in PROPOSAL_COLUMNS:
        if column not in persist_df.columns:
            persist_df[column] = ""
    persist_df = persist_df[PROPOSAL_COLUMNS].fillna("")

    try:
        with engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {TABLE_NAME}"))
        if not persist_df.empty:
            persist_df.to_sql(TABLE_NAME, engine, if_exists="append", index=False)
    except SQLAlchemyError as exc:
        st.error(f"データの保存に失敗しました: {exc}")


def join_multiselect_values(values):
    """複数選択の値をカンマ区切りに整形."""
    if not values:
        return ""
    return ", ".join(str(value) for value in values if value)


def normalize_text_list(value):
    """CSV時代のリスト文字列を考慮してテキストに正規化."""
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


def safe_float(value, default=0.0):
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value):
    try:
        if value in ("", None):
            return ""
        return int(float(value))
    except (TypeError, ValueError):
        return ""


def calculate_fiscal_term(dt_value):
    if pd.isna(dt_value):
        return None
    fiscal_year = dt_value.year
    if dt_value.month < FISCAL_YEAR_START_MONTH:
        fiscal_year -= 1
    return fiscal_year - BASE_FISCAL_YEAR


def calculate_fiscal_quarter(dt_value):
    if pd.isna(dt_value):
        return None
    month_offset = (dt_value.month - FISCAL_YEAR_START_MONTH) % 12
    return month_offset // 3 + 1


def enrich_with_fiscal_info(df):
    if df.empty:
        result = df.copy()
        result["提出日時_dt"] = pd.NaT
        result["期"] = None
        result["四半期"] = None
        return result
    enriched = df.copy()
    enriched["提出日時_dt"] = pd.to_datetime(enriched["提出日時"], errors="coerce")
    enriched["期"] = enriched["提出日時_dt"].apply(calculate_fiscal_term)
    enriched["四半期"] = enriched["提出日時_dt"].apply(calculate_fiscal_quarter)
    return enriched


def fiscal_month_sequence():
    return [((FISCAL_YEAR_START_MONTH - 1 + i) % 12) + 1 for i in range(12)]


def build_summary_dataframe(df, term_number):
    columns = SUMMARY_COLUMNS
    if df.empty:
        return pd.DataFrame(columns=columns)

    working = df.copy()
    if "提出日時_dt" not in working.columns or "期" not in working.columns:
        working = enrich_with_fiscal_info(working)
    working = working[working["期"] == term_number]
    working = working[working["提出日時_dt"].notna()].sort_values("提出日時_dt").reset_index(drop=True)
    working["通し番号"] = working.index + 1

    rows = []
    for _, row in working.iterrows():
        dt_value = row["提出日時_dt"]
        department_text = normalize_text_list(row.get("部門", "")) or ""
        effect_division = normalize_text_list(row.get("貢献事業", ""))
        effect_display = effect_division.split(",")[0].strip() if effect_division else ""

        rows.append({
            "期": term_number,
            "四半期": int(row.get("四半期")) if row.get("四半期") else "",
            "通し番号": int(row["通し番号"]),
            "年": dt_value.year,
            "月": dt_value.month,
            "日": dt_value.day,
            "提案部門": department_text,
            "効果部門": effect_display,
            "提案者": row.get("提案者", ""),
            "社員": "○",
            "派遣": "",
            "実習生": "",
            "改善テーマ": row.get("展開項目", ""),
            "マインド": safe_int(row.get("マインドセット")),
            "アイデア": safe_int(row.get("アイデア工夫")),
            "ヒント": safe_int(row.get("みんなのヒント")),
            "SDGs": "",
            "安全": "",
            "判定区分": "通常",
            "保留": "",
            "提案ポイント": "",
            "報奨金": "",
            "月額効果[¥/月]": safe_float(row.get("効果額"), 0.0),
            "削減工数[Hr/月]": safe_float(row.get("削減時間"), 0.0),
            "出金": "",
            "注記": row.get("コメント", "")
        })

    return pd.DataFrame(rows, columns=columns)


def build_person_summary(df):
    columns = [
        "部署", "提案者", "件数", "平均マインド", "平均アイデア",
        "平均ヒント", "削減時間合計[Hr/月]", "効果額合計[¥/月]"
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    working = df.copy()
    working["部署"] = working["部門"].apply(lambda v: normalize_text_list(v) or "未設定")
    working["提案者"] = working["提案者"].replace("", "未設定")
    working["削減時間"] = pd.to_numeric(working["削減時間"], errors="coerce").fillna(0)
    working["効果額"] = pd.to_numeric(working["効果額"], errors="coerce").fillna(0)
    working["マインドセット"] = pd.to_numeric(working["マインドセット"], errors="coerce")
    working["アイデア工夫"] = pd.to_numeric(working["アイデア工夫"], errors="coerce")
    working["みんなのヒント"] = pd.to_numeric(working["みんなのヒント"], errors="coerce")

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


def build_department_month_matrix(df, term_number):
    month_numbers = fiscal_month_sequence()
    month_columns = [f"{month}月" for month in month_numbers]
    columns = ["部署"] + month_columns + ["年間合計"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    working = df.copy()
    if "提出日時_dt" not in working.columns or "期" not in working.columns:
        working = enrich_with_fiscal_info(working)
    working = working[working["期"] == term_number]
    working["部署"] = working["部門"].apply(lambda v: normalize_text_list(v) or "未設定")
    working = working[working["提出日時_dt"].notna()]

    if working.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for dept, group in working.groupby("部署"):
        row = {"部署": dept}
        total = 0
        for month in month_numbers:
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


def generate_excel_file(df, term_number, report_title):
    target_df = df.copy()
    if "提出日時_dt" not in target_df.columns or "期" not in target_df.columns:
        target_df = enrich_with_fiscal_info(target_df)
    target_df = target_df[target_df["期"] == term_number]

    summary_df = build_summary_dataframe(target_df, term_number)
    person_summary = build_person_summary(target_df)
    department_summary = build_department_month_matrix(target_df, term_number)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="実績まとめ", index=False, startrow=4)
        summary_sheet = writer.sheets["実績まとめ"]
        summary_sheet["A1"] = report_title
        summary_sheet["A2"] = f"対象期: {term_number}期"
        summary_sheet["A3"] = f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        summary_sheet["A4"] = f"登録件数: {len(summary_df)}"

        person_summary.to_excel(writer, sheet_name="部署別氏名一覧", index=False)
        department_summary.to_excel(writer, sheet_name="特殊ポイント判定", index=False)

    buffer.seek(0)
    return buffer


def sanitize_filename(filename):
    sanitized = re.sub(r'[\/:*?"<>|]', "_", filename)
    return sanitized or "report"

# 提案詳細表示関数
def display_proposal_details(proposal):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**管理No:** {proposal['管理No']}")
        st.write(f"**提出日時:** {proposal['提出日時']}")
        st.write(f"**提案者:** {proposal['提案者']}")
        st.write(f"**部門:** {proposal['部門']}")
        st.write(f"**所属/担当:** {proposal['所属担当']}")
        st.write(f"**展開項目:** {proposal['展開項目']}")
        
    with col2:
        st.write(f"**削減時間:** {safe_float(proposal['削減時間'])}時間")
        st.write(f"**効果額:** ￥{int(safe_float(proposal['効果額'])):,}")
        st.write(f"**貢献事業:** {proposal['貢献事業']}")
    
    st.write(f"**問題点:** {proposal['問題点']}")
    st.write(f"**改善案:** {proposal['改善案']}")
    st.write(f"**改善結果:** {proposal['改善結果']}")
    st.write(f"**コメント:** {proposal['コメント']}")
    
    # 画像の表示
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        if proposal['改善前画像'] and isinstance(proposal['改善前画像'], str) and os.path.exists(proposal['改善前画像']):
            st.image(proposal['改善前画像'], caption="改善前", use_container_width=True)
    
    with col_img2:
        if proposal['改善後画像'] and isinstance(proposal['改善後画像'], str) and os.path.exists(proposal['改善後画像']):
            st.image(proposal['改善後画像'], caption="改善後", use_container_width=True)

# 確認状況表示関数
def display_confirmation_status(proposal):
    st.subheader("確認状況")
    
    status_cols = st.columns(4)
    
    with status_cols[0]:
        st.write("**監督者**")
        if proposal['監督者確認'] == "確認済み":
            st.success("✅ 確認済み")
            st.write(f"確認者: {proposal['監督者確認者']}")
            st.write(f"日時: {proposal['監督者確認日時']}")
        else:
            st.warning("⏳ 未確認")
    
    with status_cols[1]:
        st.write("**係長**")
        if proposal['係長確認'] == "確認済み":
            st.success("✅ 確認済み")
            st.write(f"確認者: {proposal['係長確認者']}")
            st.write(f"日時: {proposal['係長確認日時']}")
        else:
            st.warning("⏳ 未確認")
    
    with status_cols[2]:
        st.write("**部門長**")
        if proposal['部門長確認'] == "確認済み":
            st.success("✅ 確認済み")
            st.write(f"確認者: {proposal['部門長確認者']}")
            st.write(f"日時: {proposal['部門長確認日時']}")
        else:
            st.warning("⏳ 未確認")
    
    with status_cols[3]:
        st.write("**改善委員**")
        if proposal['改善委員確認'] == "確認済み":
            st.success("✅ 確認済み")
            st.write(f"確認者: {proposal['改善委員確認者']}")
            st.write(f"日時: {proposal['改善委員確認日時']}")
        else:
            st.warning("⏳ 未確認")

# 提出用画面
if st.session_state.current_page == "提出用画面":
    st.title("📝 改善提案提出フォーム")
    st.markdown("---")
    
    with st.form("proposal_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("基本情報")
            department = st.multiselect(
                "部門*",
                DEPARTMENT_OPTIONS
            )
            team = st.text_input("所属/担当*")
            proposer = st.text_input("提案者*")
            theme = st.text_input("展開項目(テーマ)*")
            
        with col2:
            st.subheader("効果計算")
            reduction_hours = st.number_input("削減時間(時間)*", min_value=0.0, step=0.5)
            hourly_rate = 1700
            effect_amount = reduction_hours * hourly_rate
            st.info(f"月間効果額: ￥{effect_amount:,.0f} (単価@1,700円)")
            
            contributing_business = st.multiselect(
                "貢献する事業*",
                DEPARTMENT_OPTIONS
            )
        
        st.subheader("問題点と改善案")
        problem = st.text_area("困っている事、問題点*", height=100)
        improvement_plan = st.text_area("この様に改善したい*", height=100)
        improvement_result = st.text_area("改善結果", height=100)
        comments = st.text_area("コメント・備考", height=80)
        
        # 画像アップロード
        st.subheader("改善前後の写真")
        col_img1, col_img2 = st.columns(2)
        
        with col_img1:
            st.markdown("**改善前の写真**")
            before_image = st.file_uploader("改善前の写真をアップロード", type=['png', 'jpg', 'jpeg'], key="before")
            if before_image:
                st.image(before_image, caption="改善前の写真", use_container_width=True)
        
        with col_img2:
            st.markdown("**改善後の写真**")
            after_image = st.file_uploader("改善後の写真をアップロード", type=['png', 'jpg', 'jpeg'], key="after")
            if after_image:
                st.image(after_image, caption="改善後の写真", use_container_width=True)
        
        submitted = st.form_submit_button("提案を提出")
    
    # 提案提出処理
    if submitted:
        if not all([department, team, proposer, theme, problem, improvement_plan]):
            st.error("必須項目(*)をすべて入力してください")
        else:
            df = load_data()
            # 管理番号の生成
            management_no = f"{datetime.now().strftime('%Y%m%d')}-{df.shape[0] + 1}"
            
            # 画像の保存
            before_image_path = ""
            after_image_path = ""
            
            if before_image:
                before_image_path = f"{IMAGE_DIR}/{management_no}_before.{before_image.type.split('/')[-1]}"
                with open(before_image_path, "wb") as f:
                    f.write(before_image.getbuffer())
            
            if after_image:
                after_image_path = f"{IMAGE_DIR}/{management_no}_after.{after_image.type.split('/')[-1]}"
                with open(after_image_path, "wb") as f:
                    f.write(after_image.getbuffer())
            
            # 新しい提案データを作成
            new_data = {
                "管理No": management_no,
                "提出日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "部門": join_multiselect_values(department),
                "所属担当": team,
                "提案者": proposer,
                "展開項目": theme,
                "問題点": problem,
                "改善案": improvement_plan,
                "改善結果": improvement_result,
                "削減時間": reduction_hours,
                "効果額": effect_amount,
                "コメント": comments,
                "貢献事業": join_multiselect_values(contributing_business),
                "マインドセット": "",
                "アイデア工夫": "",
                "みんなのヒント": "",
                "改善前画像": before_image_path,
                "改善後画像": after_image_path,
                "監督者確認": "未確認",
                "監督者確認者": "",
                "監督者コメント": "",
                "監督者確認日時": "",
                "係長確認": "未確認",
                "係長確認者": "",
                "係長コメント": "",
                "係長確認日時": "",
                "部門長確認": "未確認",
                "部門長確認者": "",
                "部門長コメント": "",
                "部門長確認日時": "",
                "改善委員確認": "未確認",
                "改善委員確認者": "",
                "改善委員コメント": "",
                "改善委員確認日時": ""
            }
            
            # CSVに保存
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            save_data(df)
            
            st.success("改善提案を提出しました！")
            st.balloons()

# 提出済み一覧画面
elif st.session_state.current_page == "提出済み一覧":
    st.title("📋 提出済み改善提案一覧")
    st.markdown("---")
    
    df = load_data()
    
    if not df.empty:
        enriched_df = enrich_with_fiscal_info(df)
        term_options = sorted({int(term) for term in enriched_df["期"].dropna().unique()}, reverse=True)
        if term_options:
            st.subheader("Excelレポート出力")
            selected_term = st.selectbox(
                "対象期を選択",
                term_options,
                format_func=lambda x: f"{x}期",
                key="excel_term"
            )
            default_title = f"{selected_term}期_改善実績まとめ"
            title_key = f"excel_title_{selected_term}"
            report_title = st.text_input("ファイルタイトル", value=default_title, key=title_key)
            final_title = report_title.strip() if report_title else default_title
            export_df = enriched_df[enriched_df["期"] == selected_term]
            if export_df.empty:
                st.info("選択した期のデータがありません。")
            else:
                excel_buffer = generate_excel_file(export_df, selected_term, final_title)
                file_name = sanitize_filename(final_title) + ".xlsx"
                st.download_button(
                    "Excelダウンロード",
                    data=excel_buffer.getvalue(),
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            st.markdown("---")

        st.subheader("すべての提案一覧")
        for _, row in df.iterrows():
            with st.expander(f"{row['提出日時']} - {row['管理No']} - {row['展開項目']} - {row['提案者']}"):
                display_proposal_details(row)
                display_confirmation_status(row)
                st.markdown("---")
    else:
        st.info("まだ提案がありません")

# 各確認画面の共通関数
def confirmation_page(role, role_japanese):
    st.title(f"✅ {role_japanese}確認画面")
    st.markdown("---")
    
    df = load_data()
    
    # 該当役職で確認待ちの提案のみ表示
    if role == "supervisor":
        pending_df = df[df["監督者確認"] == "未確認"]
    elif role == "chief":
        pending_df = df[df["係長確認"] == "未確認"]
    elif role == "manager":
        pending_df = df[df["部門長確認"] == "未確認"]
    elif role == "committee":
        pending_df = df[df["改善委員確認"] == "未確認"]
    
    if not pending_df.empty:
        st.subheader(f"{role_japanese}確認待ち提案一覧")
        for _, row in pending_df.iterrows():
            with st.expander(f"{row['提出日時']} - {row['管理No']} - {row['展開項目']} - {row['提案者']}"):
                display_proposal_details(row)
                display_confirmation_status(row)
                
                # 確認フォーム
                with st.form(f"confirmation_form_{role}_{row['管理No']}"):
                    comment = st.text_area("コメント", height=100)
                    confirm_name = st.text_input(f"{role_japanese}氏名*")
                    
                    # 評価基準（部門長と改善委員のみ）
                    if role in ["manager", "committee"]:
                        st.subheader("評価基準")
                        col3, col4, col5 = st.columns(3)
                        with col3:
                            mindset = st.radio("①マインドセット", [1, 2, 3, 4, 5], horizontal=True)
                        with col4:
                            idea = st.radio("②アイデア、工夫", [1, 2, 3, 4, 5], horizontal=True)
                        with col5:
                            hint = st.radio("③みんなのヒント", [1, 2, 3, 4, 5], horizontal=True)
                    
                    submitted = st.form_submit_button("確認を完了する")
                
                if submitted:
                    if not confirm_name:
                        st.error("確認者氏名を入力してください")
                    else:
                        idx = df[df["管理No"] == row['管理No']].index[0]
                        
                        if role == "supervisor":
                            df.at[idx, "監督者確認"] = "確認済み"
                            df.at[idx, "監督者確認者"] = confirm_name
                            df.at[idx, "監督者コメント"] = comment
                            df.at[idx, "監督者確認日時"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        elif role == "chief":
                            df.at[idx, "係長確認"] = "確認済み"
                            df.at[idx, "係長確認者"] = confirm_name
                            df.at[idx, "係長コメント"] = comment
                            df.at[idx, "係長確認日時"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        elif role == "manager":
                            df.at[idx, "部門長確認"] = "確認済み"
                            df.at[idx, "部門長確認者"] = confirm_name
                            df.at[idx, "部門長コメント"] = comment
                            df.at[idx, "部門長確認日時"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.at[idx, "マインドセット"] = mindset
                            df.at[idx, "アイデア工夫"] = idea
                            df.at[idx, "みんなのヒント"] = hint
                        
                        elif role == "committee":
                            df.at[idx, "改善委員確認"] = "確認済み"
                            df.at[idx, "改善委員確認者"] = confirm_name
                            df.at[idx, "改善委員コメント"] = comment
                            df.at[idx, "改善委員確認日時"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.at[idx, "マインドセット"] = mindset
                            df.at[idx, "アイデア工夫"] = idea
                            df.at[idx, "みんなのヒント"] = hint
                        
                        save_data(df)
                        st.success("確認が完了しました！")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info(f"{role_japanese}確認待ちの提案はありません")

# 監督者確認画面
if st.session_state.current_page == "監督者確認":
    confirmation_page("supervisor", "監督者")

# 係長確認画面
elif st.session_state.current_page == "係長確認":
    confirmation_page("chief", "係長")

# 部門長確認画面
elif st.session_state.current_page == "部門長確認":
    confirmation_page("manager", "部門長")

# 改善委員確認画面
elif st.session_state.current_page == "改善委員確認":
    confirmation_page("committee", "改善委員")

# 確認済み一覧画面
elif st.session_state.current_page == "確認済み一覧":
    st.title("✅ 確認済み改善提案一覧")
    st.markdown("---")
    
    df = load_data()
    
    if not df.empty:
        # すべて確認済みの提案のみ表示
        confirmed_df = df[
            (df["監督者確認"] == "確認済み") & 
            (df["係長確認"] == "確認済み") & 
            (df["部門長確認"] == "確認済み") & 
            (df["改善委員確認"] == "確認済み")
        ]
        
        if not confirmed_df.empty:
            st.subheader("すべて確認済みの提案一覧")
            for _, row in confirmed_df.iterrows():
                with st.expander(f"{row['提出日時']} - {row['管理No']} - {row['展開項目']} - {row['提案者']}"):
                    display_proposal_details(row)
                    display_confirmation_status(row)
                    
                    # 評価結果の表示（部門長または改善委員が評価した場合）
                    if row['マインドセット'] != '':
                        st.subheader("評価結果")
                        st.write(f"**マインドセット:** {row['マインドセット']}")
                        st.write(f"**アイデア工夫:** {row['アイデア工夫']}")
                        st.write(f"**みんなのヒント:** {row['みんなのヒント']}")
                    
                    st.markdown("---")
        else:
            st.info("すべての確認が完了した提案はありません")
    else:
        st.info("まだ提案がありません")
