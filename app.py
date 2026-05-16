import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="專業財報分析系統", layout="wide")
st.title("📊 財報自動化解析系統 (精準四年版)")

with st.sidebar:
    st.header("1. 設定")
    stock_input = st.text_input("輸入台股代碼", value="2330")
    stock_id = f"{stock_input}.TW"
    
    st.header("2. 上傳最新報表")
    st.info("💡 請同時選取『損益表』與『資產負債表』")
    uploaded_files = st.file_uploader("上傳 Excel (支援多選)", type=['xlsx'], accept_multiple_files=True)
    
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數', '應收帳款週轉率', '存貨週轉率']
    selected_metrics = st.multiselect("圖表顯示指標", options=all_metrics, default=['毛利率', '淨利率', '利息保障倍數'])
    
    analyze_btn = st.button("🚀 執行全面分析")

def fuzzy_get(d, keywords):
    """強力模糊匹配：對齊台灣 IFRS 標籤名稱"""
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "").lower()
        for kw in keywords:
            if kw.lower() in k_clean:
                return v
    return 0

def calc_all(d):
    # 核心數據提取
    rev = fuzzy_get(d, ['營業收入合計', '營業收入', 'totalrevenue'])
    cost = fuzzy_get(d, ['營業成本合計', '營業成本', 'costofrevenue'])
    net = fuzzy_get(d, ['本期淨利', 'netincome'])
    
    # 利息保障倍數關鍵組件 (加強匹配)
    ebit = fuzzy_get(d, ['營業利益', 'operatingincome', 'ebit'])
    int_exp = fuzzy_get(d, ['利息支出', '財務成本', 'interestexpense', '利息費用'])
    
    ca = fuzzy_get(d, ['流動資產合計', '流動資產', 'currentassets'])
    cl = fuzzy_get(d, ['流動負債合計', '流動負債', 'currentliabilities'])
    inv = fuzzy_get(d, ['存貨', 'inventory'])
    pre = fuzzy_get(d, ['預付款項', 'prepayments'])
    ta = fuzzy_get(d, ['資產總額', '資產合計', 'totalassets'])
    tl = fuzzy_get(d, ['負債總額', '負債合計', 'totalliabilities'])
    ar = fuzzy_get(d, ['應收帳款淨額', '應收帳款', 'receivables'])

    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    r['速動比率'] = (ca - inv - pre) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    r['應收帳款週轉率'] = rev / ar if ar > 0 else 0
    r['存貨週轉率'] = cost / inv if inv > 0 else 0
    return r

if analyze_btn:
    try:
        results = []

        # A. 抓取 Yahoo 數據 (會自動給最近 4 年)
        tk = yf.Ticker(stock_id)
        is_df = tk.financials
        bs_df = tk.balance_sheet
        
        if not is_df.empty:
            combined = pd.concat([is_df, bs_df], axis=0).transpose()
            for date, row in combined.iterrows():
                res = calc_all(row.to_dict())
                # 只保留有數據的年度 (過濾全 0 的年份如 2021)
                if any(v != 0 for k, v in res.items()):
                    res['日期'] = date.strftime('%Y')
                    results.append(res)

        # B. 解析上傳 Excel
        if uploaded_files:
            u_d = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, r_data in temp_df.iterrows():
                    items = r_data.dropna().tolist()
                    if len(items) >= 2:
                        name = str(items[0])
                        nums = [i for i in items if isinstance(i, (int, float)) and i > 100]
                        if nums: u_d[name] = nums[0]
            if u_d:
                up_res = calc_all(u_d)
                up_res['日期'] = "📁 上傳年度"
                results.append(up_res)

        # C. 呈現數據
        if results:
            # 轉換為 DataFrame 並排序
            df_final = pd.DataFrame(results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            
            st.subheader(f"📈 {stock_input} 財務指標分析 (最近四年 + 上傳報表)")
            st.dataframe(df_final.style.format("{:.2f}"))

            # 繪圖 (只抓數字年度)
            plot_df = df_final[df_final.index.str.isdigit()].sort_index()
            if not plot_df.empty and selected_metrics:
                st.subheader("📊 財務指標趨勢圖")
                fig = go.Figure()
                for m in selected_metrics:
                    if m in plot_df.columns:
                        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[m], name=m, mode='lines+markers'))
                fig.update_layout(hovermode="x unified", height=500)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("查無有效數據，請確認代碼或檔案。")

    except Exception as e:
        st.error(f"系統錯誤: {e}")
