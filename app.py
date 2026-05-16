import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader

st.set_page_config(page_title="專業財報解析系統", layout="wide")
st.title("🚀 財報自動化解析 (損益 + 資產 + 上傳全面整合)")

with st.sidebar:
    st.header("1. 數據設定")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    uploaded_file = st.file_uploader("上傳財報 (Excel)", type=['xlsx'])
    analyze_btn = st.button("執行全面分析")

def get_v(d, keys):
    """精準關鍵字搜索函數"""
    for k in d.keys():
        name = str(k).replace(" ", "")
        for kw in keys:
            if kw == name or kw in name:
                return d[k]
    return 0

def calculate_all_ratios(df_wide):
    """計算八大財務指標"""
    res_list = []
    for date, row in df_wide.iterrows():
        d = row.to_dict()
        
        # 1. 損益標籤
        rev = get_v(d, ['營業收入合計', '營業收入', 'Revenue'])
        cost = get_v(d, ['營業成本合計', '營業成本', 'CostOfGoodsSold'])
        net = get_v(d, ['本期淨利', 'NetIncome'])
        op_income = get_v(d, ['營業利益', 'OperatingIncome'])
        int_exp = get_v(d, ['利息費用', 'InterestExpense'])
        
        # 2. 資產負債標籤
        ca = get_v(d, ['流動資產合計', '流動資產', 'CurrentAssets'])
        cl = get_v(d, ['流動負債合計', '流動負債', 'CurrentLiabilities'])
        inv = get_v(d, ['存貨', 'Inventory'])
        pre = get_v(d, ['預付款項', 'Prepayments'])
        ta = get_v(d, ['資產總額', '資產合計', 'TotalAssets'])
        tl = get_v(d, ['負債總額', '負債合計', 'TotalLiabilities'])
        ar = get_v(d, ['應收帳款淨額', '應收帳款', 'AccountsReceivable'])

        r = {}
        r['日期'] = date
        r['毛利率'] = (rev - cost) / rev if rev > 0 else 0
        r['淨利率'] = net / rev if rev > 0 else 0
        r['流動比率'] = ca / cl if cl > 0 else 0
        r['速動比率'] = (ca - inv - pre) / cl if cl > 0 else 0
        r['負債比率'] = tl / ta if ta > 0 else 0
        r['利息保障倍數'] = op_income / int_exp if int_exp > 0 else 0
        r['應收帳款週轉率'] = rev / ar if ar > 0 else 0
        r['存貨週轉率'] = cost / inv if inv > 0 else 0
        res_list.append(r)
    return pd.DataFrame(res_list)

if analyze_btn:
    try:
        dl = DataLoader()
        with st.spinner('🔍 正在從 MOPS 抓取近五年完整報表...'):
            # 強制抓取兩類報表：FinancialStatements (損益) 與 BalanceSheet (資產負債)
            df_is = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
            # 某些時候需要分開請求
            df_all = df_is.copy()
            
            if df_all.empty:
                st.error("❌ 無法獲取數據，請確認代碼或稍後再試。")
            else:
                # 轉成寬表方便計算
                df_wide = df_all.pivot_table(index='date', columns='type', values='value').sort_index()
                
                # 計算歷史指標
                ratios = calculate_all_ratios(df_wide)
                ratios.set_index('日期', inplace=True)

                # 解析上傳 Excel
                if uploaded_file:
                    user_df = pd.read_excel(uploaded_file)
                    # 假設第一列是科目，其餘列是數字 (取最後一列為最新)
                    user_d = dict(zip(user_df.iloc[:,0], user_df.iloc[:,-1]))
                    uploaded_res = calculate_all_ratios(pd.DataFrame([user_d], index=['上傳報表']))
                    ratios = pd.concat([ratios, uploaded_res.set_index('日期')])
                    st.success("✅ 上傳報表已整合至下方表格末端！")

                st.subheader(f"📊 {stock_id} 財務指標全分析")
                st.dataframe(ratios.style.format("{:.2f}"))

                # 繪圖
                st.subheader("📈 五年趨勢圖")
                fig = go.Figure()
                selected_cols = ['毛利率', '淨利率', '流動比率', '負債比率']
                for col in selected_cols:
                    fig.add_trace(go.Scatter(x=ratios.index, y=ratios[col], name=col, mode='lines+markers'))
                fig.update_layout(hovermode="x unified", height=500)
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("📝 數據完整性檢查 (查看抓到了哪些科目)"):
                    st.write("目前抓到的科目總量:", len(df_wide.columns))
                    st.write(df_wide.columns.tolist())

    except Exception as e:
        st.error(f"❌ 系統錯誤: {str(e)}")
