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

# --- 核心邏輯：智能抓取 ---
def smart_get(d, keywords, exclude_kw=None):
    best_val = 0
    best_score = 0
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "").lower()
        if exclude_kw and exclude_kw in k_clean: continue
        
        score = 0
        if any(kw in k_clean for kw in keywords):
            score += 10
            if any(x in k_clean for x in ["總額", "總計", "total"]): score += 5
            if any(x in k_clean for x in ["合計", "sum"]): score += 2
            
            if score > best_score:
                best_score = score
                best_val = v
    return best_val

def calc_all(d):
    # 數據提取 (兼容 Yahoo 與 Excel)
    rev = smart_get(d, ['營業收入', 'totalrevenue'])
    cost = smart_get(d, ['營業成本', 'costofrevenue'])
    net = smart_get(d, ['本期淨利', 'netincome'])
    ebit = smart_get(d, ['營業利益', 'operatingincome'])
    int_exp = smart_get(d, ['利息支出', '財務成本', 'interestexpense'])
    ca = smart_get(d, ['流動資產', 'currentassets'])
    cl = smart_get(d, ['流動負債', 'currentliabilities'])
    inv = smart_get(d, ['存貨', 'inventory'])
    pre = smart_get(d, ['預付款項', 'prepayments'])
    # 找總額，排除流動
    ta = smart_get(d, ['資產', '總額']) or smart_get(d, ['資產', '合計'], exclude_kw='流動')
    tl = smart_get(d, ['負債', '總額']) or smart_get(d, ['負債', '合計'], exclude_kw='流動')
    # 安全檢查
    if ta < ca: ta = ca * 1.5 # 防止抓錯導致負債比過高

    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    r['速動比率'] = max(0, ca - inv - pre) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    
    debug = {"流動資產": ca, "資產總額": ta, "流動負債": cl, "負債總額": tl, "存貨": inv, "營業收入": rev}
    return r, debug

if analyze_btn:
    try:
        final_list = []
        up_debug = {}

        # 1. 抓取 Yahoo 數據 (獨立執行)
        with st.spinner('📡 正在從 Yahoo Finance 抓取歷史年報...'):
            tk = yf.Ticker(stock_id)
            # 使用最新 API 屬性
            is_df = tk.income_stmt
            bs_df = tk.balance_sheet
            
            if not is_df.empty:
                combined_hist = pd.concat([is_df, bs_df], axis=0).transpose()
                for date, row in combined_hist.iterrows():
                    res, _ = calc_all(row.to_dict())
                    if any(v != 0 for v in res.values()):
                        res['日期'] = date.strftime('%Y')
                        final_list.append(res)

        # 2. 解析 Excel 數據 (獨立執行)
        if uploaded_files:
            u_dict = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, row_data in temp_df.iterrows():
                    items = row_data.dropna().tolist()
                    if len(items) >= 2:
                        label = str(items[0]).strip()
                        nums = [i for i in items[1:] if isinstance(i, (int, float)) and abs(i) > 1000]
                        if nums: u_dict[label] = nums[0]
            
            if u_dict:
                up_res, up_debug = calc_all(u_dict)
                up_res['日期'] = "📁 上傳年度"
                final_list.append(up_res)

        # 3. 合併顯示
        if final_list:
            df_final = pd.DataFrame(final_list).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            
            st.subheader(f"📈 {stock_input} 財務指標全面清單")
            st.dataframe(df_final.style.format("{:.2f}"))

            if uploaded_files:
                with st.expander("🔍 上傳檔案數據抓取校正 (診斷工具)"):
                    st.json(up_debug)

            # 4. 繪圖 (只畫有數字年份)
            plot_df = df_final[df_final.index.str.isdigit()].sort_index()
            if not plot_df.empty and selected_metrics:
                st.subheader("📊 財務指標趨勢圖")
                fig = go.Figure()
                for m in selected_metrics:
                    if m in plot_df.columns:
                        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[m], name=m, mode='lines+markers'))
                fig.update_layout(
                    xaxis=dict(type='category', title="年度"),
                    yaxis=dict(nticks=10, showgrid=True),
                    hovermode="x unified",
                    height=550
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("❌ 無法抓取數據。請檢查網路連線或代碼。")
                
    except Exception as e:
        st.error(f"系統發生錯誤: {e}")
