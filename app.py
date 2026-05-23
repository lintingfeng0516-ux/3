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
    st.info("💡 提示：同時選取『損益表』與『資產負債表』")
    uploaded_files = st.file_uploader("上傳 Excel (支援多選)", type=['xlsx'], accept_multiple_files=True)
    
    all_metrics = ['毛利率', '淨利率', '流動比率', '速動比率', '負債比率', '利息保障倍數']
    selected_metrics = st.multiselect("圖表顯示指標", options=all_metrics, default=['毛利率', '流動比率', '負債比率'])
    
    analyze_btn = st.button("🚀 執行全面分析")

# --- 核心邏輯：強力匹配 ---
def strict_get(d, target_keywords, exclude_kw=None):
    if exclude_kw is None: exclude_kw = []
    best_val = 0
    max_score = 0
    for k, v in d.items():
        k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "").replace("(", "").replace(")", "").lower()
        if any(ex in k_clean for ex in exclude_kw): continue
        
        score = 0
        if all(tk in k_clean for tk in target_keywords):
            score += 10
            if any(x in k_clean for x in ["總額", "總計", "total"]): score += 5
            if any(x in k_clean for x in ["合計", "sum"]): score += 2
            if score > max_score:
                max_score = score
                best_val = v
    return best_val

def calc_all(d, source='excel'):
    # 提取 11 項原始數據
    if source == 'excel':
        rev = strict_get(d, ['營業收入'], exclude_kw=['其他'])
        cost = strict_get(d, ['營業成本'], exclude_kw=['其他'])
        net = strict_get(d, ['本期淨利'], exclude_kw=['綜合'])
        ebit = strict_get(d, ['營業利益'])
        int_exp = strict_get(d, ['財務成本']) or strict_get(d, ['利息支出'])
        ca = strict_get(d, ['流動資產', '合計'], exclude_kw=['其他']) or strict_get(d, ['流動資產'])
        cl = strict_get(d, ['流動負債', '合計'], exclude_kw=['其他']) or strict_get(d, ['流動負債'])
        inv = strict_get(d, ['存貨'])
        pre = strict_get(d, ['預付款項'])
        ta = strict_get(d, ['資產總額']) or strict_get(d, ['資產合計'], exclude_kw=['流動'])
        tl = strict_get(d, ['負債總額']) or strict_get(d, ['負債合計'], exclude_kw=['流動'])
    else:
        # Yahoo Finance 模式
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

    # 計算 6 大指標
    r = {}
    r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
    r['淨利率'] = net / rev if rev > 0 else 0
    r['流動比率'] = ca / cl if cl > 0 else 0
    r['速動比率'] = max(0, ca - inv - pre) / cl if cl > 0 else 0
    r['負債比率'] = tl / ta if ta > 0 else 0
    r['利息保障倍數'] = ebit / int_exp if int_exp > 0 else 0
    
    # 完整 11 項診斷數據
    debug = {
        "營業收入": rev, "營業成本": cost, "本期淨利": net,
        "營業利益(EBIT)": ebit, "利息/財務成本": int_exp,
        "流動資產": ca, "流動負債": cl, "存貨": inv, "預付款項": pre,
        "資產總額": ta, "負債總額": tl
    }
    return r, debug

if analyze_btn:
    try:
        final_list = []
        up_debug = {}

        # 1. 抓取 Yahoo 數據 (四年)
        tk = yf.Ticker(stock_id)
        hist_df = pd.concat([tk.income_stmt, tk.balance_sheet], axis=0).transpose()
        if not hist_df.empty:
            for date, row in hist_df.head(4).iterrows():
                res, _ = calc_all(row.to_dict(), source='yahoo')
                if any(v != 0 for v in res.values()):
                    res['日期'] = date.strftime('%Y')
                    final_list.append(res)

        # 2. 解析 Excel
        if uploaded_files:
            u_dict = {}
            for f in uploaded_files:
                u_df = pd.read_excel(f)
                for _, row in u_df.iterrows():
                    items = row.dropna().tolist()
                    if len(items) >= 2:
                        label = str(items[0]).strip()
                        nums = [i for i in items[1:] if isinstance(i, (int, float)) and abs(i) > 1000]
                        if nums: u_dict[label] = nums[0]
            
            if u_dict:
                up_res, up_debug = calc_all(u_dict, source='excel')
                up_res['日期'] = "📁 上傳年度"
                final_list.append(up_res)

        # 3. 顯示結果
        if final_list:
            df_final = pd.DataFrame(final_list).drop_duplicates(subset=['日期']).set_index('日期').sort_index(ascending=False)
            st.subheader(f"📈 {stock_input} 財務指標全面分析表")
            st.dataframe(df_final.style.format("{:.2f}"))

            if uploaded_files:
                with st.expander("🔍 上傳檔案數據抓取校正 (11項完整診斷工具)"):
                    st.json(up_debug)

            # 4. 繪圖 (最近四年)
            plot_df = df_final[df_final.index.str.isdigit()].sort_index()
            if not plot_df.empty and selected_metrics:
                st.subheader("📊 財務指標趨勢圖")
                fig = go.Figure()
                for m in selected_metrics:
                    if m in plot_df.columns:
                        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[m], name=m, mode='lines+markers'))
                fig.update_layout(xaxis=dict(type='category', title="年度"), yaxis=dict(nticks=10, showgrid=True), hovermode="x unified", height=550)
                st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"系統發生錯誤: {e}")
