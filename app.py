import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader

st.set_page_config(page_title="財報分析系統", layout="wide")
st.title("📊 財報自動化解析與五年度趨勢分析")

# 側邊欄設定
with st.sidebar:
    st.header("設定")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    analyze_btn = st.button("開始執行自動化分析")

def calculate_ratios(df_group):
    # 將數據轉為字典，並移除空白字元
    d = {str(k).strip(): v for k, v in zip(df_group['type'], df_group['value'])}
    
    # 定義抓取函數 (同時支援中文與常見英文標籤)
    def get_val(*keys):
        for k in keys:
            if k in d: return d[k]
        return 0

    res = {}
    # 1. 獲利能力
    rev = get_val('Revenue', '營業收入', '營業收入合計')
    cost = get_val('Cost_of_goods_sold', '營業成本', '營業成本合計')
    net_income = get_val('Net_Income', '本期淨利（淨損）', '本期淨利')
    
    res['毛利率'] = (rev - cost) / rev if rev != 0 else 0
    res['淨利率'] = net_income / rev if rev != 0 else 0
    
    # 2. 償債能力
    cur_assets = get_val('Current_Assets', '流動資產', '流動資產合計')
    cur_liab = get_val('Current_Liabilities', '流動負債', '流動負債合計')
    inventory = get_val('Inventory', '存貨')
    prepaid = get_val('Prepayments', '預付款項')
    
    res['流動比率'] = cur_assets / cur_liab if cur_liab != 0 else 0
    res['速動比率'] = (cur_assets - inventory - prepaid) / cur_liab if cur_liab != 0 else 0
    
    # 3. 財務結構
    total_liab = get_val('Total_Liabilities', '負債總額', '負債合計')
    total_assets = get_val('Total_Assets', '資產總額', '資產合計')
    ebit = get_val('Operating_Income', '營業利益') # 簡化用營業利益代替
    int_exp = get_val('Interest_Expense', '利息費用')
    
    res['負債比率'] = total_liab / total_assets if total_assets != 0 else 0
    res['利息保障倍數'] = ebit / int_exp if int_exp != 0 else 0
    
    # 4. 營運效率
    ar = get_val('Accounts_Receivable', '應收帳款淨額', '應收帳款')
    res['應收帳款週轉率'] = rev / ar if ar != 0 else 0
    res['存貨週轉率'] = cost / inventory if inventory != 0 else 0
    
    return pd.Series(res)

if analyze_btn:
    with st.spinner('正在從資料庫提取數據...'):
        dl = DataLoader()
        # 抓取綜合損益表與資產負債表
        df = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
        
        if df.empty:
            st.error("查無資料，請確認股票代碼。")
        else:
            # 計算比率
            ratios = df.groupby('date').apply(calculate_ratios).sort_index()
            
            # 顯示結果表格
            st.subheader(f"📈 {stock_id} 財務指標趨勢表")
            st.dataframe(ratios.style.format("{:.2f}"))
            
            # 繪製圖表
            st.subheader("📊 成長曲線視覺化")
            tab1, tab2 = st.tabs(["獲利指標", "安全指標"])
            
            with tab1:
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=ratios.index, y=ratios['毛利率'], name='毛利率'))
                fig1.add_trace(go.Scatter(x=ratios.index, y=ratios['淨利率'], name='淨利率'))
                st.plotly_chart(fig1, use_container_width=True)
                
            with tab2:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=ratios.index, y=ratios['流動比率'], name='流動比率'))
                fig2.add_trace(go.Scatter(x=ratios.index, y=ratios['負債比率'], name='負債比率'))
                st.plotly_chart(fig2, use_container_width=True)
