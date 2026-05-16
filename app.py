import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import io

st.set_page_config(page_title="專業財報分析系統", layout="wide")
st.title("🚀 財報自動化解析 (Yahoo Finance + 多檔 Excel 整合版)")

with st.sidebar:
    st.header("1. 設定股票代碼")
    # 台股需加 .TW，程式會自動處理
    stock_input = st.text_input("輸入台股代碼 (例如 2330)", value="2330")
    stock_id = f"{stock_input}.TW"
    
    st.header("2. 上傳最新報表")
    st.info("💡 提示：按住 Ctrl 可同時選取『資產負債表』與『損益表』Excel")
    uploaded_files = st.file_uploader("上傳 Excel 財報", type=['xlsx'], accept_multiple_files=True)
    
    analyze_btn = st.button("🚀 執行全面分析")

# --- 核心對照表 (相容 Yahoo 英文與 MOPS 中文) ---
MAPS = {
    'rev': ['Total Revenue', '營業收入合計', '營業收入'],
    'cost': ['Cost Of Revenue', '營業成本合計', '營業成本'],
    'net': ['Net Income Common Stockholders', '本期淨利（淨損）', '本期淨利'],
    'ebit': ['EBIT', 'Operating Income', '營業利益'],
    'int': ['Interest Expense', '利息費用'],
    'ca': ['Current Assets', '流動資產合計', '流動資產'],
    'cl': ['Current Liabilities', '流動負債合計', '流動負債'],
    'inv': ['Inventory', '存貨合計', '存貨'],
    'ta': ['Total Assets', '資產總額', '資產合計'],
    'tl': ['Total Liabilities Net Minority Interest', '負債總額', '負債合計'],
    'ar': ['Receivables', '應收帳款淨額', '應收帳款']
}

def get_v(d, keys):
    for k, v in d.items():
        k_str = str(k).replace(" ", "")
        for target in keys:
            if target.replace(" ", "") in k_str:
                return v
    return 0

def calc_ratios(d):
    v = {k: get_v(d, v_list) for k, v_list in MAPS.items()}
    r = {}
    r['毛利率'] = (v['rev'] - v['cost']) / v['rev'] if v['rev'] > 0 else 0
    r['淨利率'] = v['net'] / v['rev'] if v['rev'] > 0 else 0
    r['流動比率'] = v['ca'] / v['cl'] if v['cl'] > 0 else 0
    r['速動比率'] = (v['ca'] - v['inv']) / v['cl'] if v['cl'] > 0 else 0
    r['負債比率'] = v['tl'] / v['ta'] if v['ta'] > 0 else 0
    r['利息保障倍數'] = v['ebit'] / v['int'] if v['int'] > 0 else 0
    r['應收帳款週轉率'] = v['rev'] / v['ar'] if v['ar'] > 0 else 0
    r['存貨週轉率'] = v['cost'] / v['inv'] if v['inv'] > 0 else 0
    return r

if analyze_btn:
    try:
        results = []
        
        # A. 從 Yahoo Finance 抓取歷史數據
        with st.spinner(f'📡 正在從 Yahoo Finance 抓取 {stock_id} 歷史報表...'):
            ticker = yf.Ticker(stock_id)
            # 獲取年度損益表與資產負債表
            hist_is = ticker.financials.transpose()
            hist_bs = ticker.balance_sheet.transpose()
            
            # 合併兩張表
            hist_combined = pd.concat([hist_is, hist_bs], axis=1)
            
            if not hist_combined.empty:
                for date, row in hist_combined.iterrows():
                    res = calc_ratios(row.to_dict())
                    res['日期'] = date.strftime('%Y-%m-%d')
                    results.append(res)
            else:
                st.warning("⚠️ Yahoo Finance 暫無該代碼的細節報表，嘗試解析上傳檔案。")

        # B. 解析與合併上傳的多個 Excel 檔案
        if uploaded_files:
            with st.spinner('📂 正在整合解析上傳的 Excel 檔案...'):
                user_combined_d = {}
                for f in uploaded_files:
                    u_df = pd.read_excel(f)
                    for _, row in u_df.iterrows():
                        items = row.dropna().tolist()
                        if len(items) >= 2:
                            name = str(items[0])
                            # 找這一列中最大的數字 (通常是金額)
                            nums = [i for i in items if isinstance(i, (int, float)) and i > 100]
                            if nums: user_combined_d[name] = nums[0]
                
                if user_combined_d:
                    up_res = calc_ratios(user_combined_d)
                    up_res['日期'] = "📁 上傳報表(整合)"
                    results.append(up_res)

        # C. 顯示數據與圖表
        if results:
            df_final = pd.DataFrame(results).set_index('日期').sort_index(ascending=False)
            st.subheader("📋 財務指標全面分析表")
            st.dataframe(df_final.style.format("{:.2f}"))

            # 繪製曲線圖
            plot_df = df_final[df_final.index.str.contains('20')].sort_index()
            if not plot_df.empty:
                st.subheader("📈 五年成長趨勢圖")
                fig = go.Figure()
                for col in ['毛利率', '流動比率', '負債比率']:
                    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], name=col, mode='lines+markers'))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("❌ 抱歉，所有來源皆無法獲取數據。請檢查股票代碼或 Excel 內容。")

    except Exception as e:
        st.error(f"❌ 系統錯誤: {e}")
