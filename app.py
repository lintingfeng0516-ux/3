import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="專業財報分析系統", layout="wide")
st.title("📊 財報自動化解析系統 ")

with st.sidebar:
    st.header("1. 設定來源")
    stock_input = st.text_input("輸入台股代碼", value="2330")
    stock_id = f"{stock_input}.TW"
    
    st.header("2. 上傳最新報表")
    uploaded_files = st.file_uploader("上傳 Excel (支援多選)", type=['xlsx'], accept_multiple_files=True)
    
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數']
    selected_metrics = st.multiselect("圖表顯示指標", options=all_metrics, default=['毛利率', '流動比率', '負債比率'])
    
    analyze_btn = st.button("🚀 執行全面分析")

# --- 核心邏輯：區分「總額」與「流動項」 ---
def smart_get(d, keywords, exclude_kw=None):
    """
    d: 數據字典
    keywords: 必備關鍵字 (如 ['資產', '總額'])
    exclude_kw: 排除關鍵字 (如 '流動')，防止抓到細項
    """
    best_val = 0
    best_match_score = 0
    
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "").lower()
        
        # 如果包含排除關鍵字，直接跳過 (例如找總資產時跳過流動資產)
        if exclude_kw and exclude_kw in k_clean:
            continue
            
        # 計算匹配分數
        score = 0
        if all(kw in k_clean for kw in keywords):
            score += 10
            if "總額" in k_clean or "總計" in k_clean: score += 5
            if "合計" in k_clean: score += 2
            
            if score > best_match_score:
                best_match_score = score
                best_val = v
    return best_val

def calc_all(d):
    # 損益表 (比較單純)
    rev = smart_get(d, ['營業收入'])
    cost = smart_get(d, ['營業成本'])
    net = smart_get(d, ['本期淨利'])
    ebit = smart_get(d, ['營業利益'])
    int_exp = smart_get(d, ['財務成本']) or smart_get(d, ['利息支出'])

    # 資產負債表 (關鍵：區分流動與總額)
    ca = smart_get(d, ['流動資產', '合計']) # 找流動資產合計
    cl = smart_get(d, ['流動負債', '合計']) # 找流動負債合計
    inv = smart_get(d, ['存貨'])
    pre = smart_get(d, ['預付款項'])
    
    # 找「總額」，但排除掉「流動」字眼
    ta = smart_get(d, ['資產', '總額'], exclude_kw=None) or smart_get(d, ['資產', '合計'], exclude_kw='流動')
    tl = smart_get(d, ['負債', '總額'], exclude_kw=None) or smart_get(d, ['負債', '合計'], exclude_kw='流動')

    # 特殊處理：如果總資產沒抓到，嘗試找最大的那個數字
    if ta < ca: ta = smart_get(d, ['資產總額'])

    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    r['速動比率'] = max(0, ca - inv - pre) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    
    raw_debug = {
        "營業收入": rev, "本期淨利": net, "營業利益": ebit, "利息支出": int_exp,
        "流動資產合計": ca, "資產總額": ta, "流動負債合計": cl, "負債總額": tl, "存貨": inv
    }
    return r, raw_debug

if analyze_btn:
    try:
        results = []
        up_debug = {}

        # A. Yahoo Finance 數據
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

        # B. 解析 Excel
        if uploaded_files:
            u_dict = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, row_data in temp_df.iterrows():
                    items = row_data.dropna().tolist()
                    if len(items) >= 2:
                        label = str(items[0]).strip()
                        # 只抓金額
                        nums = [i for i in items[1:] if isinstance(i, (int, float)) and abs(i) > 1000]
                        if nums: u_dict[label] = nums[0]
            
            if u_dict:
                up_res, up_debug = calc_all(u_dict)
                up_res['日期'] = "📁 上傳年度"
                results.append(up_res)

        # C. 呈現
        if results:
            df_final = pd.DataFrame(results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📈 {stock_input} 財務指標分析表")
            st.dataframe(df_final.style.format("{:.2f}"))

            if uploaded_files:
                with st.expander("🔍 上傳檔案數據抓取校正 (診斷工具)"):
                    st.json(up_debug)

            plot_df = df_final.sort_index()
            if not plot_df.empty and selected_metrics:
                st.subheader("📊 財務指標趨勢圖")
                fig = go.Figure()
                for m in selected_metrics:
                    if m in plot_df.columns:
                        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[m], name=m, mode='lines+markers'))
                fig.update_layout(xaxis=dict(type='category'), yaxis=dict(nticks=10, showgrid=True), hovermode="x unified", height=550)
                st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"系統錯誤: {e}")
