import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime

st.set_page_config(page_title="台股財報五年度分析站", layout="wide")
st.title("📊 財報自動化解析系統 (歷史+多檔上傳整合版)")

with st.sidebar:
    st.header("1. 設定股票代號")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    
    st.header("2. 上傳最新報表")
    st.info("💡 提示：您可以同時選取多個檔案 (損益表、資產負債表等)")
    uploaded_files = st.file_uploader("上傳 Excel 財報 (支援多個檔案)", type=['xlsx'], accept_multiple_files=True)
    
    analyze_btn = st.button("🚀 啟動全面分析")

# --- 超強效會計項目對照表 ---
MAPS = {
    'rev': ['營業收入合計', '營業收入', 'OperatingRevenue', 'Revenue'],
    'cost': ['營業成本合計', '營業成本', 'CostOfGoodsSold'],
    'net': ['本期淨利（淨損）', '本期淨利', 'NetIncome', 'ProfitLoss'],
    'op_income': ['營業利益（損失）', '營業利益', 'OperatingIncome'],
    'int_exp': ['利息費用', 'InterestExpense'],
    'ca': ['流動資產合計', '流動資產', 'CurrentAssets'],
    'cl': ['流動負債合計', '流動負債', 'CurrentLiabilities'],
    'inv': ['存貨', 'Inventory'],
    'pre': ['預付款項', 'Prepayments'],
    'ta': ['資產總額', '資產合計', 'TotalAssets'],
    'tl': ['負債總額', '負債合計', 'TotalLiabilities'],
    'ar': ['應收帳款淨額', '應收帳款', 'AccountsReceivable']
}

def get_v(d, keys):
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "")
        for target in keys:
            if target in k_clean: return v
    return 0

def calc_ratios(d):
    v = {k: get_v(d, v_list) for k, v_list in MAPS.items()}
    r = {}
    r['毛利率'] = (v['rev'] - v['cost']) / v['rev'] if v['rev'] > 0 else 0
    r['淨利率'] = v['net'] / v['rev'] if v['rev'] > 0 else 0
    r['流動比率'] = v['ca'] / v['cl'] if v['cl'] > 0 else 0
    r['速動比率'] = (v['ca'] - v['inv'] - v['pre']) / v['cl'] if v['cl'] > 0 else 0
    r['負債比率'] = v['tl'] / v['ta'] if v['ta'] > 0 else 0
    r['利息保障倍數'] = v['op_income'] / v['int_exp'] if v['int_exp'] > 0 else 0
    r['應收帳款週轉率'] = v['rev'] / v['ar'] if v['ar'] > 0 else 0
    r['存貨週轉率'] = v['cost'] / v['inv'] if v['inv'] > 0 else 0
    return r

if analyze_btn:
    try:
        # A. 抓取歷史數據
        dl = DataLoader()
        with st.spinner('📡 正在請求 MOPS 歷史數據 (2019-2024)...'):
            # 強制請求損益表與資產負債表
            df_hist = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
            
            final_results = []
            if not df_hist.empty:
                for date, group in df_hist.groupby('date'):
                    res = calc_ratios(dict(zip(group['type'], group['value'])))
                    res['日期'] = date
                    final_results.append(res)
            else:
                st.warning("⚠️ MOPS 歷史數據請求受限。如果您有往年 Excel，請直接上傳。")

        # B. 整合多個上傳的檔案
        if uploaded_files:
            with st.spinner('📂 正在合併解析上傳的報表...'):
                combined_d = {}
                for f in uploaded_files:
                    u_df = pd.read_excel(f)
                    for _, row in u_df.iterrows():
                        row_l = row.dropna().tolist()
                        if len(row_l) >= 2:
                            # 抓取第一欄作為科目，最後一欄數字作為金額
                            key = str(row_l[0])
                            # 找這一列中最大的數字 (通常是金額)
                            nums = [i for i in row_l if isinstance(i, (int, float)) and i > 100]
                            if nums: combined_d[key] = nums[0]
                
                if combined_d:
                    up_res = calc_ratios(combined_d)
                    up_res['日期'] = "📁 上傳報表(整合)"
                    final_results.append(up_res)
                    st.success(f"✅ 已成功整合 {len(uploaded_files)} 份報表數據！")

        # C. 顯示與繪圖
        if final_results:
            df_final = pd.DataFrame(final_results).set_index('日期').sort_index(ascending=False)
            st.subheader("📋 財務比率分析總表")
            st.dataframe(df_final.style.format("{:.2f}"))

            # 繪圖 (過濾掉文字日期)
            plot_df = df_final[df_final.index.str.contains('20')].sort_index()
            if not plot_df.empty:
                st.subheader("📈 歷史成長曲線圖")
                fig = go.Figure()
                for col in ['毛利率', '流動比率', '負債比率']:
                    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], name=col))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("❌ 找不到任何數據，請檢查代碼或上傳報表。")

    except Exception as e:
        st.error(f"系統錯誤: {e}")
