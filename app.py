import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="專業財報分析系統", layout="wide")
st.title("📊 財報自動化解析系統 (精準數值修正版)")

with st.sidebar:
    st.header("1. 設定來源")
    stock_input = st.text_input("輸入台股代碼", value="2330")
    stock_id = f"{stock_input}.TW"
    
    st.header("2. 上傳最新報表")
    uploaded_files = st.file_uploader("上傳 Excel (支援多選)", type=['xlsx'], accept_multiple_files=True)
    
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數']
    selected_metrics = st.multiselect("圖表顯示指標", options=all_metrics, default=['毛利率', '流動比率', '速動比率'])
    
    analyze_btn = st.button("🚀 執行全面分析")

# --- 強化版模糊匹配 (優先找合計) ---
def fuzzy_get(d, keywords):
    # 第一輪：優先匹配包含「合計」、「總額」且數值巨大的項目
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "")
        for kw in keywords:
            if kw in k_clean and any(x in k_clean for x in ["合計", "總額", "總計"]):
                return v
    # 第二輪：一般匹配
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "")
        for kw in keywords:
            if kw in k_clean:
                return v
    return 0

def calc_all(d):
    # 提取數據
    rev = fuzzy_get(d, ['營業收入'])
    cost = fuzzy_get(d, ['營業成本'])
    net = fuzzy_get(d, ['本期淨利', '本期淨利淨損'])
    ebit = fuzzy_get(d, ['營業利益', '營業利益損失'])
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
    
    # 核心修正：計算速動資產，並確保數值邏輯合理
    quick_assets = ca - inv - pre
    # 如果出現 ca < inv 的異常情況(抓錯欄位)，速動比率設為與流動比率接近的合理值或 0
    r['速動比率'] = max(0, quick_assets) / cl if cl > 0 else 0
    
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    return r, {"流動資產": ca, "存貨": inv, "流動負債": cl, "營業利益": ebit, "財務成本": int_exp}

if analyze_btn:
    try:
        results = []
        debug_info = {}

        # A. Yahoo Finance 歷史數據
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

        # B. 解析 Excel (排除百分比欄位的干擾)
        if uploaded_files:
            u_d = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, row_data in temp_df.iterrows():
                    items = row_data.dropna().tolist()
                    if len(items) >= 2:
                        label = str(items[0]).strip()
                        # 找尋該行中真正的金額：
                        # 規則：數字必須大於 1000 (排除百分比 48.12 這種)
                        nums = [i for i in items[1:] if isinstance(i, (int, float)) and abs(i) > 1000]
                        if nums:
                            val = nums[0] # 取標籤後的第一個大數字
                            # 如果標籤重複，優先保留有「合計」字眼的
                            if label in u_d:
                                if "合計" in label or "總額" in label: u_d[label] = val
                            else:
                                u_d[label] = val
            
            if u_d:
                up_res, debug_info = calc_all(u_d)
                up_res['日期'] = "📁 上傳年度"
                results.append(up_res)

        # C. 顯示
        if results:
            df_final = pd.DataFrame(results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📈 {stock_input} 財務指標分析表")
            st.dataframe(df_final.style.format("{:.2f}"))

            # 診斷小視窗
            if uploaded_files:
                with st.expander("🔍 上傳檔案數據抓取校正 (確認金額是否正確)"):
                    st.write("程式從 Excel 抓到的數值如下：")
                    st.json(debug_info)

            # 繪圖
            plot_df = df_final[df_final.index.str.isdigit()].sort_index()
            if not plot_df.empty and selected_metrics:
                st.subheader("📊 財務指標趨勢圖")
                fig = go.Figure()
                for m in selected_metrics:
                    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[m], name=m, mode='lines+markers'))
                fig.update_layout(xaxis=dict(type='category'), yaxis=dict(showgrid=True), hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"系統錯誤: {e}")
