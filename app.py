import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
import datetime

st.set_page_config(page_title="財報分析系統", layout="wide")
st.title("📊 財報自動化解析與五年度趨勢分析")

with st.sidebar:
    st.header("設定")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    uploaded_file = st.file_uploader("上傳財報 (PDF/Excel)", type=['pdf', 'xlsx'])
    analyze_btn = st.button("開始執行自動化分析")

def calculate_ratios(df_group):
    d = dict(zip(df_group['type'], df_group['value']))
    get = lambda k: d.get(k, 0)
    res = {}
    try:
        res['毛利率'] = (get('營業收入') - get('營業成本')) / get('營業收入') if get('營業收入') else 0
        res['淨利率'] = get('本期淨利（淨損）') / get('營業收入') if get('營業收入') else 0
        res['流動比率'] = get('流動資產') / get('流動負債') if get('流動負債') else 0
        res['速動比率'] = (get('流動資產') - get('存貨') - get('預付款項')) / get('流動負債') if get('流動負債') else 0
        res['負債比率'] = get('負債總額') / get('資產總額') if get('資產總額') else 0
        res['利息保障倍數'] = (get('繼續營業單位稅前淨利') + get('利息費用')) / get('利息費用') if get('利息費用') else 0
        res['應收帳款週轉率'] = get('營業收入') / get('應收帳款') if get('應收帳款') else 0
        res['存貨週轉率'] = get('營業成本') / get('存貨') if get('存貨') else 0
    except: pass
    return pd.Series(res)

if analyze_btn:
    with st.spinner('抓取數據中...'):
        dl = DataLoader()
        df = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
        if df.empty:
            st.error("查無資料")
        else:
            ratios = df.groupby('date').apply(calculate_ratios)
            st.subheader(f"📈 {stock_id} 財務指標")
            st.dataframe(ratios.style.format("{:.2f}"))
            
            fig = go.Figure()
            for col in ratios.columns:
                fig.add_trace(go.Scatter(x=ratios.index, y=ratios[col], name=col))
            st.plotly_chart(fig, use_container_width=True)
