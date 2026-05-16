import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="專業財報分析系統", layout="wide")
st.title("📊 財報自動化解析系統 (強力匹配版)")

with st.sidebar:
    st.header("1. 設定")
    stock_input = st.text_input("輸入台股代碼", value="2330")
    stock_id = f"{stock_input}.TW"
    
    st.header("2. 上傳最新報表")
    uploaded_files = st.file_uploader("上傳 Excel (可多選)", type=['xlsx'], accept_multiple_files=True)
    
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數', '應收帳款週轉率', '存貨週轉率']
    selected_metrics = st.multiselect("圖表顯示指標", options=all_metrics, default=['毛利率', '流動比率', '負債比率'])
    
    analyze_btn = st.button("🚀 執行全面分析")

# --- 超強模糊搜索函數 ---
def fuzzy_get(d, keywords):
    """只要標籤包含關鍵字，就抓取該數值"""
    for k, v in d.items():
        k_str = str(k).lower().replace(" ", "").replace("_", "")
        for kw in keywords:
            if kw.lower() in k_str:
                return v
    return 0

def calc_all(d):
    # 定義各種可能的標籤組合
    rev = fuzzy_get(d, ['totalrevenue', 'operatingrevenue', '營業收入合計', '營業收入'])
    cost = fuzzy_get(d, ['costofrevenue', 'costofgoods', '營業成本合計', '營業成本'])
    net = fuzzy_get(d, ['netincome', 'profitloss', '本期淨利'])
    ebit = fuzzy_get(d, ['ebit', 'operatingincome', '營業利益'])
    int_exp = fuzzy_get(d, ['interestexpense', '利息費用'])
    ca = fuzzy_get(d, ['currentassets', '流動資產合計', '流動資產'])
    cl = fuzzy_get(d, ['currentliabilities', '流動負債合計', '流動負債'])
    inv = fuzzy_get(d, ['inventory', '存貨合計', '存貨'])
    ta = fuzzy_get(d, ['totalassets', '資產總額', '資產合計'])
    tl = fuzzy_get(d, ['totalliabilities', '負債總額', '負債合計'])
    ar = fuzzy_get(d, ['receivables', '應收帳款', 'accountsreceivable'])

    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    r['速動比率'] = (ca - inv) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    r['應收帳款週轉率'] = rev / ar if ar > 0 else 0
    r['存貨週轉率'] = cost / inv if inv > 0 else 0
    return r

if analyze_btn:
    try:
        results = []
        raw_debug_info = {}

        # A. 抓取 Yahoo Finance 數據
        with st.spinner('📡 數據同步中...'):
            tk = yf.Ticker(stock_id)
            # 抓取年度報表，如果沒資料就抓季度
            is_df = tk.financials if not tk.financials.empty else tk.quarterly_financials
            bs_df = tk.balance_sheet if not tk.balance_sheet.empty else tk.quarterly_balance_sheet
            
            if not is_df.empty:
                combined = pd.concat([is_df, bs_df], axis=0).transpose()
                raw_debug_info = combined.iloc[0].to_dict() # 存下最新一筆用於診斷
                
                for date, row in combined.iterrows():
                    res = calc_all(row.to_dict())
                    res['日期'] = date.strftime('%Y')
                    results.append(res)

        # B. 解析上傳的 Excel
        if uploaded_files:
            u_d = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, r_data in temp_df.iterrows():
                    items = r_data.dropna().tolist()
                    if len(items) >= 2:
                        # 找尋數值 (大於100的通常是金額)
                        nums = [i for i in items if isinstance(i, (int, float)) and i > 100]
                        if nums: u_d[str(items[0])] = nums[0]
            if u_d:
                up_res = calc_all(u_d)
                up_res['日期'] = "📁 上傳年度"
                results.append(up_res)

        # C. 顯示與繪圖
        if results:
            final_df = pd.DataFrame(results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📋 {stock_input} 財務指標分析表")
            st.dataframe(final_df.style.format("{:.2f}"))

            plot_df = final_df[final_df.index.str.isdigit()].sort_index()
            if not plot_df.empty and selected_metrics:
                st.subheader("📈 歷史成長趨勢圖")
                fig = go.Figure()
                for m in selected_metrics:
                    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[m], name=m, mode='lines+markers'))
                st.plotly_chart(fig, use_container_width=True)
        
        # D. 診斷區 (如果數據是0，請截圖這裡)
        with st.expander("🔍 數據抓取診斷區 (數據異常時請點開)"):
            st.write("Yahoo Finance 回傳的原始標籤清單：")
            st.write(list(raw_debug_info.keys()))

    except Exception as e:
        st.error(f"系統錯誤: {e}")
