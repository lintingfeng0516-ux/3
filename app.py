import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime

st.set_page_config(page_title="專業財報分析系統", layout="wide")
st.title("📊 財報自動化解析 (多檔上傳 + 歷史數據整合)")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("1. 歷史數據抓取")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    
    st.header("2. 上傳最新報表")
    st.info("請同時選取『資產負債表』與『損益表』Excel 檔案上傳")
    # 支援多檔案上傳
    uploaded_files = st.file_uploader("選取多個 Excel 檔案", type=['xlsx'], accept_multiple_files=True)
    
    analyze_btn = st.button("🚀 開始執行全面分析")

# --- 會計科目關鍵字對照清單 (擴充版) ---
MAPS = {
    'rev': ['營業收入合計', '營業收入', 'Revenue'],
    'cost': ['營業成本合計', '營業成本', 'CostOfGoodsSold'],
    'net': ['本期淨利', '本期淨利（淨損）', 'ProfitLoss'],
    'op_income': ['營業利益', 'OperatingIncome'],
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
    """精準搜尋字典中的會計項目"""
    for k, v in d.items():
        clean_k = str(k).replace(" ", "").replace("　", "")
        for target in keys:
            if target == clean_k or target in clean_k:
                return v
    return 0

def calc_ratios(data_dict):
    """計算八大核心指標"""
    v = {k: get_v(data_dict, v_list) for k, v_list in MAPS.items()}
    r = {}
    # 獲利能力
    r['毛利率'] = (v['rev'] - v['cost']) / v['rev'] if v['rev'] > 0 else 0
    r['淨利率'] = v['net'] / v['rev'] if v['rev'] > 0 else 0
    # 償債能力
    r['流動比率'] = v['ca'] / v['cl'] if v['cl'] > 0 else 0
    r['速動比率'] = (v['ca'] - v['inv'] - v['pre']) / v['cl'] if v['cl'] > 0 else 0
    # 結構與倍數
    r['負債比率'] = v['tl'] / v['ta'] if v['ta'] > 0 else 0
    r['利息保障倍數'] = v['op_income'] / v['int_exp'] if v['int_exp'] > 0 else 0
    # 營運效率
    r['應收帳款週轉率'] = v['rev'] / v['ar'] if v['ar'] > 0 else 0
    r['存貨週轉率'] = v['cost'] / v['inv'] if v['inv'] > 0 else 0
    return r

if analyze_btn:
    try:
        dl = DataLoader()
        with st.spinner('正在同步 MOPS 歷史數據...'):
            # 分開抓取損益表與資產負債表，解決數據缺失問題
            df_all = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
            
            if df_all.empty:
                st.error("歷史數據抓取失敗，請確認代號。")
                history_df = pd.DataFrame()
            else:
                # 依日期計算歷史比率
                hist_results = []
                for date, group in df_all.groupby('date'):
                    d_temp = dict(zip(group['type'], group['value']))
                    res = calc_ratios(d_temp)
                    res['日期'] = date
                    hist_results.append(res)
                history_df = pd.DataFrame(hist_results).set_index('日期').sort_index(ascending=False)

        # 解析上傳的多個 Excel 檔案
        if uploaded_files:
            with st.spinner('正在整合上傳的多張報表...'):
                combined_user_dict = {}
                for f in uploaded_files:
                    u_df = pd.read_excel(f)
                    # 搜尋 Excel 表格中所有的文字與數字對應
                    for _, row in u_df.iterrows():
                        row_list = row.dropna().tolist()
                        if len(row_list) >= 2:
                            # 假設第一項是科目名稱，最後一項是數值
                            key = str(row_list[0])
                            val = row_list[-1]
                            if isinstance(val, (int, float)):
                                combined_user_dict[key] = val
                
                # 計算合併後的上傳數據
                up_res = calc_ratios(combined_user_dict)
                history_df.loc['📁 上傳報表 (合併解析)'] = up_res
                st.success(f"✅ 已成功合併解析 {len(uploaded_files)} 個檔案！")

        # 顯示表格
        st.subheader(f"📈 {stock_id} 財務指標全分析")
        st.dataframe(history_df.style.format("{:.2f}"))

        # 繪製圖表
        if not history_df.empty:
            plot_data = history_df.drop('📁 上傳報表 (合併解析)', errors='ignore').sort_index()
            fig = go.Figure()
            for col in ['毛利率', '流動比率', '負債比率']:
                fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data[col], name=col, mode='lines+markers'))
            fig.update_layout(title="歷史趨勢圖", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"系統錯誤: {e}")
