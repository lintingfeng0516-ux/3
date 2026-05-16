import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader

st.set_page_config(page_title="財報分析系統", layout="wide")
st.title("📊 財報自動化解析系統 (最終修復版)")

with st.sidebar:
    st.header("設定")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    analyze_btn = st.button("開始執行自動化分析")

def calculate_ratios(df_group):
    # 建立數據字典，去除空白
    d = {str(k).strip(): v for k, v in zip(df_group['type'], df_group['value'])}
    
    def get_v(*keys):
        for k in keys:
            if k in d: return d[k]
        return 0

    # 1. 抓取基礎數據
    rev = get_v('Revenue', '營業收入', '營業收入合計')
    cost = get_v('Cost_of_goods_sold', '營業成本', '營業成本合計')
    net_income = get_v('Net_Income', '本期淨利（淨損）', '本期淨利')
    cur_assets = get_v('Current_Assets', '流動資產', '流動資產合計')
    cur_liab = get_v('Current_Liabilities', '流動負債', '流動負債合計')
    inventory = get_v('Inventory', '存貨', '存貨合計')
    prepaid = get_v('Prepayments', '預付款項', '預付款項合計')
    total_assets = get_v('Total_Assets', '資產總額', '資產合計')
    total_liab = get_v('Total_Liabilities', '負債總額', '負債合計')
    op_income = get_v('Operating_Income', '營業利益（損失）', '營業利益')
    int_exp = get_v('Interest_Expense', '利息費用')
    ar = get_v('Accounts_Receivable', '應收帳款淨額', '應收帳款')

    # 2. 計算比率
    res = {}
    res['毛利率'] = (rev - cost) / rev if rev != 0 else 0
    res['淨利率'] = net_income / rev if rev != 0 else 0
    res['流動比率'] = cur_assets / cur_liab if cur_liab != 0 else 0
    res['速動比率'] = (cur_assets - inventory - prepaid) / cur_liab if cur_liab != 0 else 0
    res['負債比率'] = total_liab / total_assets if total_assets != 0 else 0
    res['利息保障倍數'] = op_income / int_exp if int_exp != 0 else 0
    res['應收帳款週轉率'] = rev / ar if ar != 0 else 0
    res['存貨週轉率'] = cost / inventory if invento
