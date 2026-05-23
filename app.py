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

# --- 核心邏輯：兼容雙語標籤 ---
def smart_get(d, keywords):
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "").replace("(", "").replace(")", "").lower()
        for kw in keywords:
            if kw.lower() in k_clean:
                return v
    return 0

def calc_all(d, is_excel=False):
    # 定義關鍵字清單 (Excel 中文 vs Yahoo 英文)
    if is_excel:
        # Excel 嚴格匹配模式：避開「流動」抓「總額」
        rev = smart_get(d, ['營業收入合計', '營業收入'])
        cost = smart_get(d, ['營業成本合計', '營業成本'])
        net = smart_get(d, ['本期淨利'])
        ebit = smart_get(d, ['營業利益'])
        int_exp = smart_get(d, ['財務成本', '利息支出'])
        ca = smart_get(d, ['流動資產合計', '流動資產'])
        cl = smart_get(d, ['流動負債合計', '流動負債'])
        inv = smart_get(d, ['存貨'])
        pre = smart_get(d, ['預付款項'])
        # 抓資產總額時避開流動
        ta = 0
        for k, v in d.items():
            if '資產' in str(k) and any(x in str(k) for x in ['總額', '總計', '合計']) and '流動' not in str(k):
                ta = v; break
        tl = 0
        for k, v in d.items():
            if '負債' in str(k) and any(x in str(k) for x in ['總額', '總計', '合計']) and '流動' not in str(k):
                tl = v; break
    else:
        # Yahoo Finance 英文模式
        rev = d.get('Total Revenue', 0)
        cost = d.get('Cost Of Revenue', 0)
        net = d.get('Net Income', 0)
        ebit = d.get('Operating Income', 0) or d.get('EBIT', 0)
        int_exp = d.get('Interest Expense', 0)
        ca = d.get('Total Current Assets', 0)
        cl = d.get('Total Current Liabilities', 0)
        inv = d.get('Inventory', 0)
        pre = d.get('Prepayments', 0)
        ta = d.get('Total Assets', 0)
        tl = d.get('Total Liabilities Net Minority Interest', 0)

    # 計算比率
    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    r['速動比率'] = max(0, ca - inv - pre) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    
    debug = {
        "營業收入": rev, "本期淨利": net, "流動資產": ca, "資產總額": ta, 
        "流動負債": cl, "負債總額": tl, "財務成本": int_exp
    }
    return r, debug

if analyze_btn:
    try:
        final_results = []
        excel_debug = {}

        # 1. 抓取 Yahoo 數據
        with st.spinner('📡 正在請求 Yahoo Finance 數據...'):
            tk = yf.Ticker(stock_id)
            # 強制抓取最近四年
            hist_df = pd.concat([tk.income_stmt, tk.balance_sheet], axis=0).transpose()
            if not hist_df.empty:
                for date, row in hist_df.iterrows():
                    res, _ = calc_all(row.to_dict(), is_excel=False)
                    res['日期'] = date.strftime('%Y')
                    final_results.append(res)

        # 2. 解析 Excel 數據
        if uploaded_files:
            u_dict = {}
            for f in uploaded_files:
                temp_df = pd.read_excel(f)
                for _, row in temp_df.iterrows():
                    items = row.dropna().tolist()
                    if len(items) >= 2:
                        label = str(items[0]).strip()
                        nums = [i for i in items[1:] if isinstance(i, (int, float)) and abs(i) > 1000]
                        if nums: u_dict[label] = nums[0]
            
            if u_dict:
                up_res, excel_debug = calc_all(u_dict, is_excel=True)
                up_res['日期'] = "📁 上傳年度"
                final_results.append(up_res)

        # 3. 合併與顯示
        if final_results:
            df_final = pd.DataFrame(final_results).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📈 {stock_input} 財務指標全分析表")
            st.dataframe(df_final.style.format("{:.2f}"))

            if uploaded_files:
                with st.expander("🔍 上傳檔案數據抓取校正 (11項完整診斷)"):
                    st.json(excel_debug)

            # 4. 繪圖 (只畫有年份數字的部分)
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
                    hovermode="x unified", height=550
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("❌ 無法抓取任何年度數據。")
                
    except Exception as e:
        st.error(f"系統發生錯誤: {e}")
