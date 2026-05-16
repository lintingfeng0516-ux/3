import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
import io

st.set_page_config(page_title="專業財報解析系統", layout="wide")
st.title("🚀 財報自動化解析 (歷史數據 + 手動上傳整合)")

with st.sidebar:
    st.header("1. 數據設定")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    uploaded_file = st.file_uploader("上傳財報 (Excel)", type=['xlsx'])
    analyze_btn = st.button("執行全面分析")

# 通用解析函數：根據關鍵字在字典中找數字
def get_val(d, keywords):
    for k in d.keys():
        for kw in keywords:
            if kw in str(k):
                return d[k]
    return 0

def calculate_ratios(df_group):
    d = {str(k).replace(" ", ""): v for k, v in zip(df_group['type'], df_group['value'])}
    
    # 定義關鍵字匹配
    rev = get_val(d, ['營業收入合計', '營業收入', 'Revenue'])
    cost = get_val(d, ['營業成本合計', '營業成本', 'CostOfGoodsSold'])
    net = get_val(d, ['本期淨利', 'NetIncome'])
    ca = get_val(d, ['流動資產合計', '流動資產', 'CurrentAssets'])
    cl = get_val(d, ['流動負債合計', '流動負債', 'CurrentLiabilities'])
    inv = get_val(d, ['存貨', 'Inventory'])
    ta = get_val(d, ['資產總額', '資產合計', 'TotalAssets'])
    tl = get_val(d, ['負債總額', '負債合計', 'TotalLiabilities'])
    op = get_v = get_val(d, ['營業利益', 'OperatingIncome'])
    ie = get_val(d, ['利息費用', 'InterestExpense'])
    ar = get_val(d, ['應收帳款淨額', '應收帳款', 'AccountsReceivable'])

    r = {}
    r['毛利率'] = (rev - cost) / rev if rev != 0 else 0
    r['淨利率'] = net / rev if rev != 0 else 0
    r['流動比率'] = ca / cl if cl != 0 else 0
    r['速動比率'] = (ca - inv) / cl if cl != 0 else 0
    r['負債比率'] = tl / ta if ta != 0 else 0
    r['利息保障倍數'] = op / ie if ie != 0 else 0
    r['應收帳款週轉率'] = rev / ar if ar != 0 else 0
    r['存貨週轉率'] = cost / inv if inv != 0 else 0
    return pd.Series(r)

if analyze_btn:
    try:
        # --- A. 抓取五年歷史數據 ---
        dl = DataLoader()
        # 分開抓取損益表與資產負債表確保完整
        df = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
        
        if df.empty:
            st.error("❌ 歷史資料抓取失敗，請檢查代碼或稍後再試。")
        else:
            # 計算歷史比率
            ratios = df.groupby('date').apply(calculate_ratios, include_groups=False).sort_index()

            # --- B. 解析上傳的 Excel (如果有的話) ---
            if uploaded_file:
                st.info("正在解析上傳的 Excel 檔案...")
                # 讀取 Excel 第一個 Sheet
                user_df = pd.read_excel(uploaded_file)
                # 簡單假設 Excel 是兩列：科目與數值
                user_d = dict(zip(user_df.iloc[:,0], user_df.iloc[:,1]))
                # 計算該檔案的比率
                uploaded_ratios = calculate_ratios(pd.DataFrame({'type': list(user_d.keys()), 'value': list(user_d.values())}))
                # 將上傳的數據加入表格 (標記為「上傳報表」)
                ratios.loc['上傳報表'] = uploaded_ratios
                st.success("✅ 上傳報表解析完成！")

            # --- C. 呈現結果 ---
            st.subheader(f"📊 {stock_id} 財務指標分析結果")
            st.dataframe(ratios.style.format("{:.2f}"))

            # 視覺化
            fig = go.Figure()
            for col in ['毛利率', '淨利率', '負債比率']:
                fig.add_trace(go.Scatter(x=ratios.index, y=ratios[col], name=col, mode='lines+markers'))
            fig.update_layout(title="獲利與結構趨勢圖", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 除錯工具：顯示抓到的項目清單 ---
            with st.expander("🔍 數據庫抓到的科目名稱 (如果數值仍為0，請檢查這裡)"):
                st.write(df['type'].unique().tolist())

    except Exception as e:
        st.error(f"❌ 系統錯誤: {str(e)}")
