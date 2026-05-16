import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader

st.set_page_config(page_title="財報分析系統", layout="wide")
st.title("📊 財報自動化解析系統")

with st.sidebar:
    stock_id = st.text_input("輸入台股代碼", value="2330")
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

    # 計算八大指標
    r = {}
    r['毛利率'] = (rev - cost) / rev if rev != 0 else 0
    r['淨利率'] = net / rev if rev != 0 else 0
    r['流動比率'] = ca / cl if cl != 0 else 0
    r['速動比率'] = (ca - inv - pre) / cl if cl != 0 else 0
    r['負債比率'] = tl / ta if ta != 0 else 0
    r['利息保障倍數'] = op / ie if ie != 0 else 0
    r['應收帳款週轉率'] = rev / ar if ar != 0 else 0
    r['存貨週轉率'] = cost / inv if inv != 0 else 0
    return pd.Series(r)

if analyze_btn:
    try:
        dl = DataLoader()
        df = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
        if df.empty:
            st.error("查無資料")
        else:
            ratios = df.groupby('date').apply(calculate_ratios, include_groups=False).sort_index()
            st.subheader(f"📈 {stock_id} 指標表")
            st.dataframe(ratios.style.format("{:.2f}"))
            
            # 簡潔圖表
            fig = go.Figure()
            for col in ['毛利率', '淨利率', '負債比率']:
                fig.add_trace(go.Scatter(x=ratios.index, y=ratios[col], name=col))
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"錯誤: {e}")
