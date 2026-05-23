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
    st.info("💡 提示：同時選取『損益表』與『資產負債表』Excel")
    uploaded_files = st.file_uploader("上傳 Excel (支援多選)", type=['xlsx'], accept_multiple_files=True)
    
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數']
    selected_metrics = st.multiselect("圖表顯示指標", options=all_metrics, default=['毛利率', '流動比率', '負債比率'])
    
    analyze_btn = st.button("🚀 開始全面分析")

def fuzzy_get(d, keywords):
    """強力模糊匹配：對應標籤名稱，優先找合計，過濾小數點百分比"""
    # 第一輪：優先匹配包含「合計」且數值大於 1000 的
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "").lower()
        if any(kw in k_clean for kw in keywords) and any(x in k_clean for x in ["合計", "總額", "總計"]):
            if isinstance(v, (int, float)) and abs(v) > 1000: return v
    # 第二輪：一般匹配
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").lower()
        if any(kw in k_clean for kw in keywords):
            if isinstance(v, (int, float)) and abs(v) > 1000: return v
    return 0

def calc_all(d):
    # 提取關鍵數值
    rev = fuzzy_get(d, ['營業收入'])
    cost = fuzzy_get(d, ['營業成本'])
    net = fuzzy_get(d, ['本期淨利', 'netincome'])
    ebit = fuzzy_get(d, ['營業利益', 'operatingincome'])
    int_exp = fuzzy_get(d, ['利息支出', '財務成本', '利息費用'])
    ca = fuzzy_get(d, ['流動資產'])
    cl = fuzzy_get(d, ['流動負債'])
    inv = fuzzy_get(d, ['存貨'])
    pre = fuzzy_get(d, ['預付款項'])
    ta = fuzzy_get(d, ['資產總額', '資產合計'])
    tl = fuzzy_get(d, ['負債總額', '負債合計'])

    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    r['速動比率'] = max(0, ca - inv - pre) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    
    # 存下抓到的原始數據用於診斷
    raw_vals = {
        "營業收入": rev, "營業成本": cost, "本期淨利": net,
        "營業利益": ebit, "利息/財務成本": int_exp,
        "流動資產": ca, "流動負債": cl, "存貨": inv, 
        "資產總額": ta, "負債總額": tl
    }
    return r, raw_vals

if analyze_btn:
    try:
        results = []
        up_debug = {}

        # A. 抓取 Yahoo 歷史數據
        tk = yf.Ticker(stock_id)
        is_df = tk.financials
        bs_df = tk.balance_sheet
        if not is_df.empty:
            combined = pd.concat([is_df, bs_df], axis=0).transpose()
            for date, row in combined.iterrows():
                res, _ = calc_all(row.to_dict())
                if any(v != 0 for v in res.values()):
                    res['日期'] = date.strftime('%Y')
                    results.append(res)

        # B. 解析上傳 Excel
        if uploaded_files:
            u_dict = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, row_data in temp_df.iterrows():
                    items = row_data.dropna().tolist()
                    if len(items) >= 2:
                        label = str(items[0]).strip()
                        # 抓取數值金額 (排除百分比，找大於 1000 的數字)
                        nums = [i for i in items[1:] if isinstance(i, (int, float)) and abs(i) > 1000]
                        if nums:
                            val = nums[0]
                            if label in u_dict:
                                if any(x in label for x in ["合計", "總額"]): u_dict[label] = val
                            else: u_dict[label] = val
            
            if u_dict:
                up_res, up_debug = calc_all(u_dict)
                up_res['日期'] = "📁 上傳年度"
                results.append(up_res)

        # C. 顯示結果
        if results:
            df_final = pd.DataFrame(results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📈 {stock_input} 財務指標全分析表")
            st.dataframe(df_final.style.format("{:.2f}"))

            # --- 診斷工具回歸 ---
            if uploaded_files:
                with st.expander("🔍 上傳檔案數據抓取校正 (診斷工具)"):
                    st.write("程式從您上傳的 Excel 中提取的原始數據如下：")
                    st.json(up_debug)
                    st.info("💡 如果數值為 0，代表 Excel 中的科目名稱與程式預設不符。請檢查名稱是否為『營業收入合計』、『財務成本』等。")

            # D. 繪圖
            st.subheader("📊 財務指標趨勢圖")
            plot_df = df_final.sort_index()
            if not plot_df.empty and selected_metrics:
                fig = go.Figure()
                for m in selected_metrics:
                    if m in plot_df.columns:
                        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[m], name=m, mode='lines+markers'))
                fig.update_layout(xaxis=dict(type='category'), yaxis=dict(nticks=10, showgrid=True), hovermode="x unified", height=550)
                st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"系統錯誤: {e}")
