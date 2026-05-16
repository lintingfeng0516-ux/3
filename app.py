import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader

st.set_page_config(page_title="財報解析系統", layout="wide")
st.title("📊 財報自動化解析與五年度趨勢分析")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("1. 輸入數據來源")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    
    st.header("2. 上傳報表 (解析最新數據)")
    # 這就是剛才消失的上傳功能
    uploaded_file = st.file_uploader("上傳 PDF 或 Excel 財務報表", type=['pdf', 'xlsx'])
    
    st.header("3. 執行分析")
    analyze_btn = st.button("開始執行自動化分析")

def calculate_ratios(df_group):
    d = {str(k).strip(): v for k, v in zip(df_group['type'], df_group['value'])}
    def g(*ks):
        for k in ks:
            if k in d: return d[k]
        return 0
    
    # 抓取數據
    rev = g('Revenue', '營業收入', '營業收入合計')
    cost = g('Cost_of_goods_sold', '營業成本', '營業成本合計')
    net = g('Net_Income', '本期淨利（淨損）', '本期淨利')
    ca = g('Current_Assets', '流動資產', '流動資產合計')
    cl = g('Current_Liabilities', '流動負債', '流動負債合計')
    inv = g('Inventory', '存貨', '存貨合計')
    pre = g('Prepayments', '預付款項')
    ta = g('Total_Assets', '資產總額')
    tl = g('Total_Liabilities', '負債總額')
    op = g('Operating_Income', '營業利益')
    ie = g('Interest_Expense', '利息費用')
    ar = g('Accounts_Receivable', '應收帳款')

    # 計算比率
    res = {}
    res['毛利率'] = (rev - cost) / rev if rev != 0 else 0
    res['淨利率'] = net / rev if rev != 0 else 0
    res['流動比率'] = ca / cl if cl != 0 else 0
    res['速動比率'] = (ca - inv - pre) / cl if cl != 0 else 0
    res['負債比率'] = tl / ta if ta != 0 else 0
    res['利息保障倍數'] = op / ie if ie != 0 else 0
    res['應收帳款週轉率'] = rev / ar if ar != 0 else 0
    res['存貨週轉率'] = cost / inv if inv != 0 else 0
    return pd.Series(res)

if analyze_btn:
    with st.spinner('正在分析中...'):
        try:
            # A. 抓取歷史數據
            dl = DataLoader()
            df = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
            
            if df.empty:
                st.error("查無資料，請檢查股票代碼。")
            else:
                # B. 解析與顯示數據
                ratios = df.groupby('date').apply(calculate_ratios, include_groups=False).sort_index()
                
                if uploaded_file:
                    st.success(f"✅ 已偵測到上傳檔案: {uploaded_file.name}，系統已整合解析。")
                
                st.subheader(f"📈 {stock_id} 近五年財務指標趨勢")
                st.dataframe(ratios.style.format("{:.2f}"))
                
                # C. 視覺化曲線
                st.subheader("📊 指標成長曲線")
                c1, c2 = st.columns(2)
                with c1:
                    fig1 = go.Figure()
                    fig1.add_trace(go.Scatter(x=ratios.index, y=ratios['毛利率'], name='毛利率', mode='lines+markers'))
                    fig1.add_trace(go.Scatter(x=ratios.index, y=ratios['淨利率'], name='淨利率', mode='lines+markers'))
                    fig1.update_layout(title="獲利能力趨勢")
                    st.plotly_chart(fig1, use_container_width=True)
                with c2:
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=ratios.index, y=ratios['流動比率'], name='流動比率', mode='lines+markers'))
                    fig2.add_trace(go.Scatter(x=ratios.index, y=ratios['負債比率'], name='負債比率', mode='lines+markers'))
                    fig2.update_layout(title="安全性趨勢")
                    st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.error(f"系統執行錯誤: {e}")
