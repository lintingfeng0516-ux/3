import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="專業財報分析站", layout="wide")
st.title("📊 財報自動化分析與視覺化系統")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("1. 數據設定")
    stock_input = st.text_input("輸入台股代碼", value="2330")
    stock_id = f"{stock_input}.TW"
    
    st.header("2. 上傳最新報表 (Excel)")
    st.info("💡 提示：按住 Ctrl 可同時選取『資產負債表』與『損益表』")
    uploaded_files = st.file_uploader("上傳 Excel 財報", type=['xlsx'], accept_multiple_files=True)
    
    # 3. 指定顯示功能
    st.header("3. 圖表顯示設定")
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數', '應收帳款週轉率', '存貨週轉率']
    selected_metrics = st.multiselect("選擇要在圖表顯示的指標", options=all_metrics, default=['毛利率', '淨利率', '流動比率'])
    
    analyze_btn = st.button("🚀 執行全面分析")

# --- 核心解析與計算函數 ---
MAPS = {
    'rev': ['Total Revenue', '營業收入合計', '營業收入'],
    'cost': ['Cost Of Revenue', '營業成本合計', '營業成本'],
    'net': ['Net Income Common Stockholders', '本期淨利（淨損）', '本期淨利'],
    'ebit': ['EBIT', 'Operating Income', '營業利益'],
    'int': ['Interest Expense', '利息費用'],
    'ca': ['Current Assets', '流動資產合計', '流動資產'],
    'cl': ['Current Liabilities', '流動負債合計', '流動負債'],
    'inv': ['Inventory', '存貨合計', '存貨'],
    'pre': ['Prepayments', '預付款項'],
    'ta': ['Total Assets', '資產總額', '資產合計'],
    'tl': ['Total Liabilities Net Minority Interest', '負債總額', '負債合計'],
    'ar': ['Receivables', '應收帳款淨額', '應收帳款']
}

def get_v(d, keys):
    for k, v in d.items():
        k_str = str(k).replace(" ", "").replace("　", "")
        for target in keys:
            if target in k_str: return v
    return 0

def calc_ratios(d):
    v = {k: get_v(d, v_list) for k, v_list in MAPS.items()}
    r = {}
    r['毛利率'] = (v['rev'] - v['cost']) / v['rev'] if v['rev'] > 0 else 0
    r['淨利率'] = v['net'] / v['rev'] if v['rev'] > 0 else 0
    r['流動比率'] = v['ca'] / v['cl'] if v['cl'] > 0 else 0
    r['速動比率'] = (v['ca'] - v['inv'] - v['pre']) / v['cl'] if v['cl'] > 0 else 0
    r['負債比率'] = v['tl'] / v['ta'] if v['ta'] > 0 else 0
    r['利息保障倍數'] = v['ebit'] / v['int'] if v['int'] > 0 else 0
    r['應收帳款週轉率'] = v['rev'] / v['ar'] if v['ar'] > 0 else 0
    r['存貨週轉率'] = v['cost'] / v['inv'] if v['inv'] > 0 else 0
    return r

if analyze_btn:
    try:
        results = []
        
        # A. 從 Yahoo Finance 抓取歷史年度數據 (標準 1 年期)
        with st.spinner(f'📡 正在從資料庫抓取 {stock_id} 歷史年報...'):
            ticker = yf.Ticker(stock_id)
            # 使用 .financials 與 .balance_sheet 抓取年度數據 (非季度)
            hist_is = ticker.financials.transpose()
            hist_bs = ticker.balance_sheet.transpose()
            hist_combined = pd.concat([hist_is, hist_bs], axis=1)
            
            if not hist_combined.empty:
                for date, row in hist_combined.iterrows():
                    res = calc_ratios(row.to_dict())
                    res['日期'] = date.strftime('%Y') # 以年度為標準
                    results.append(res)
            else:
                st.warning("⚠️ 雲端歷史數據不完整，請嘗試上傳更多年度的 Excel 補齊。")

        # B. 解析並合併上傳的多個 Excel 檔案
        if uploaded_files:
            with st.spinner('📂 正在整合解析上傳的 Excel 檔案...'):
                user_combined_d = {}
                for f in uploaded_files:
                    u_df = pd.read_excel(f)
                    for _, row in u_df.iterrows():
                        items = row.dropna().tolist()
                        if len(items) >= 2:
                            name = str(items[0])
                            nums = [i for i in items if isinstance(i, (int, float)) and i > 100]
                            if nums: user_combined_d[name] = nums[0]
                
                if user_combined_d:
                    up_res = calc_ratios(user_combined_d)
                    # 嘗試從檔名或內容抓年份，否則標記為「上傳報表」
                    up_res['日期'] = "📁 上傳年度"
                    results.append(up_res)

        # C. 顯示數據
        if results:
            df_final = pd.DataFrame(results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📋 {stock_input} 財務指標年度分析清單")
            st.dataframe(df_final.style.format("{:.2f}"))

            # D. 自選指標視覺化
            if selected_metrics:
                st.subheader(f"📈 指標趨勢成長圖 ({', '.join(selected_metrics)})")
                # 排除非年度標記進行繪圖
                plot_df = df_final[df_final.index.str.isdigit()].sort_index()
                
                fig = go.Figure()
                for col in selected_metrics:
                    if col in plot_df.columns:
                        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], name=col, mode='lines+markers', line=dict(width=3)))
                
                fig.update_layout(
                    xaxis_title="年度",
                    yaxis_title="比率 / 倍數",
                    hovermode="x unified",
                    height=600,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("請在左側選擇要顯示在圖表上的指標。")
        else:
            st.error("❌ 無法獲取數據，請檢查代碼或 Excel 格式。")

    except Exception as e:
        st.error(f"❌ 系統錯誤: {e}")
