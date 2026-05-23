import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="專業財報分析系統", layout="wide")
st.title("📊 財報自動化解析系統 ")

with st.sidebar:
    st.header("1. 數據設定")
    stock_input = st.text_input("輸入台股代碼", value="2330")
    stock_id = f"{stock_input}.TW"
    
    st.header("2. 上傳最新報表")
    st.info("💡 提示：同時選取『損益表』與『資產負債表』")
    uploaded_files = st.file_uploader("上傳 Excel (可多選)", type=['xlsx'], accept_multiple_files=True)
    
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數']
    selected_metrics = st.multiselect("圖表顯示指標", options=all_metrics, default=['毛利率', '流動比率', '速動比率'])
    
    analyze_btn = st.button("🚀 開始全面分析")

def fuzzy_get(d, keywords):
    """強力模糊匹配：對應台灣 IFRS 標籤名稱，過濾掉百分比小數"""
    # 優先找合計
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "").lower()
        if any(kw in k_clean for kw in keywords) and any(x in k_clean for x in ["合計", "總額", "總計"]):
            if isinstance(v, (int, float)) and abs(v) > 100: return v
    # 其次找一般標籤
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").lower()
        if any(kw in k_clean for kw in keywords):
            if isinstance(v, (int, float)) and abs(v) > 100: return v
    return 0

def calc_all(d):
    # 核心數據提取 (匹配 Yahoo 與 MOPS)
    rev = fuzzy_get(d, ['營業收入', 'totalrevenue', 'operatingrevenue'])
    cost = fuzzy_get(d, ['營業成本', 'costofrevenue'])
    net = fuzzy_get(d, ['本期淨利', 'netincome'])
    ebit = fuzzy_get(d, ['營業利益', 'operatingincome', 'ebit'])
    int_exp = fuzzy_get(d, ['利息支出', '財務成本', 'interestexpense'])
    ca = fuzzy_get(d, ['流動資產', 'currentassets'])
    cl = fuzzy_get(d, ['流動負債', 'currentliabilities'])
    inv = fuzzy_get(d, ['存貨', 'inventory'])
    pre = fuzzy_get(d, ['預付款項', 'prepayments'])
    ta = fuzzy_get(d, ['資產總額', '資產合計', 'totalassets'])
    tl = fuzzy_get(d, ['負債總額', '負債合計', 'totalliabilities'])

    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    # 防止速動比率出現負值或解析偏移
    r['速動比率'] = max(0, ca - inv - pre) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    return r

if analyze_btn:
    try:
        results = []

        # A. 抓取 Yahoo 歷史數據 (2022-2025)
        with st.spinner('📡 正在請求 Yahoo Finance 歷史數據...'):
            tk = yf.Ticker(stock_id)
            is_df = tk.financials
            bs_df = tk.balance_sheet
            
            if not is_df.empty:
                combined = pd.concat([is_df, bs_df], axis=0).transpose()
                for date, row in combined.iterrows():
                    res = calc_all(row.to_dict())
                    # 只要有任一數據不是 0 就放入結果
                    if any(v != 0 for v in res.values()):
                        res['日期'] = date.strftime('%Y')
                        results.append(res)
            else:
                st.warning("⚠️ 歷史數據庫連線異常，請稍後再試或透過上傳補齊。")

        # B. 解析上傳 Excel
        if uploaded_files:
            u_d = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, r_data in temp_df.iterrows():
                    items = r_data.dropna().tolist()
                    if len(items) >= 2:
                        name = str(items[0]).strip()
                        # 只抓金額，排除百分比
                        nums = [i for i in items if isinstance(i, (int, float)) and abs(i) > 1000]
                        if nums: u_d[name] = nums[0]
            if u_d:
                up_res = calc_all(u_d)
                up_res['日期'] = "📁 上傳年度"
                results.append(up_res)

        # C. 顯示結果表格
        if results:
            df_final = pd.DataFrame(results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📈 {stock_input} 財務指標全分析表")
            st.dataframe(df_final.style.format("{:.2f}"))

            # D. 繪製圖表 (包含上傳年度與歷史年度)
            st.subheader("📊 財務指標趨勢圖")
            # 整理繪圖用的 DataFrame，將日期轉為字串方便顯示
            plot_df = df_final.sort_index()
            
            if not plot_df.empty and selected_metrics:
                fig = go.Figure()
                for m in selected_metrics:
                    if m in plot_df.columns:
                        fig.add_trace(go.Scatter(
                            x=plot_df.index, 
                            y=plot_df[m], 
                            name=m, 
                            mode='lines+markers',
                            line=dict(width=3),
                            marker=dict(size=10)
                        ))
                
                fig.update_layout(
                    xaxis=dict(type='category', title="年度 / 來源"),
                    yaxis=dict(title="數值", nticks=10, showgrid=True, gridcolor='lightgrey'),
                    hovermode="x unified",
                    height=550,
                    legend=dict(orient
