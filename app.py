import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime

st.set_page_config(page_title="專業財報分析站", layout="wide")
st.title("📊 財報自動化解析系統 (終極修正版)")

with st.sidebar:
    st.header("1. 設定來源")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    uploaded_file = st.file_uploader("上傳 Excel 財報", type=['xlsx'])
    analyze_btn = st.button("🚀 執行全面分析")

# --- 超強關鍵字對照表 (對應台灣 IFRS 格式) ---
MAPS = {
    'rev': ['營業收入合計', '營業收入', 'Revenue', 'OperatingRevenue'],
    'cost': ['營業成本合計', '營業成本', 'CostOfGoodsSold'],
    'net': ['本期淨利', '本期淨利（淨損）', 'NetIncome', 'ProfitLoss'],
    'ca': ['流動資產合計', '流動資產', 'CurrentAssets'],
    'cl': ['流動負債合計', '流動負債', 'CurrentLiabilities'],
    'inv': ['存貨', 'Inventory'],
    'pre': ['預付款項', 'Prepayments'],
    'ta': ['資產總額', '資產合計', 'TotalAssets'],
    'tl': ['負債總額', '負債合計', 'TotalLiabilities'],
    'op': ['營業利益', 'OperatingIncome'],
    'ie': ['利息費用', 'InterestExpense'],
    'ar': ['應收帳款淨額', '應收帳款', 'AccountsReceivable']
}

def get_data_from_dict(d):
    """從字典中提取數值，支援多關鍵字搜尋"""
    def find(keys):
        for k, v in d.items():
            name = str(k).replace(" ", "").replace("\n", "")
            for target in keys:
                if target == name or target in name:
                    return v
        return 0
    
    vals = {k: find(v) for k, v in MAPS.items()}
    
    r = {}
    r['毛利率'] = (vals['rev'] - vals['cost']) / vals['rev'] if vals['rev'] > 0 else 0
    r['淨利率'] = vals['net'] / vals['rev'] if vals['rev'] > 0 else 0
    r['流動比率'] = vals['ca'] / vals['cl'] if vals['cl'] > 0 else 0
    r['速動比率'] = (vals['ca'] - vals['inv'] - vals['pre']) / vals['cl'] if vals['cl'] > 0 else 0
    r['負債比率'] = vals['tl'] / vals['ta'] if vals['ta'] > 0 else 0
    r['利息保障倍數'] = vals['op'] / vals['ie'] if vals['ie'] > 0 else 0
    r['應收帳款週轉率'] = vals['rev'] / vals['ar'] if vals['ar'] > 0 else 0
    r['存貨週轉率'] = vals['cost'] / vals['inv'] if vals['inv'] > 0 else 0
    return r

if analyze_btn:
    try:
        dl = DataLoader()
        # 1. 抓取歷史數據
        with st.spinner('正在從 MOPS 抓取真實歷史數據...'):
            df = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
            
            # 過濾掉未來日期
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] <= datetime.now()]
            
            if df.empty:
                st.error("❌ 無法取得該代碼的歷史數據。")
            else:
                # 按日期分組計算
                history_list = []
                for date, group in df.groupby('date'):
                    d_temp = dict(zip(group['type'], group['value']))
                    res = get_data_from_dict(d_temp)
                    res['日期'] = date.strftime('%Y-%m-%d')
                    history_list.append(res)
                
                final_df = pd.DataFrame(history_list).set_index('日期').sort_index(ascending=False)

                # 2. 解析上傳 Excel (深度掃描模式)
                if uploaded_file:
                    with st.spinner('🔍 正在深度解析上傳檔案...'):
                        u_df = pd.read_excel(uploaded_file, header=None)
                        # 掃描整個表格尋找標籤與數值
                        u_dict = {}
                        for i, row in u_df.iterrows():
                            # 找包含數字的列
                            row_list = row.dropna().tolist()
                            if len(row_list) >= 2:
                                key = str(row_list[0])
                                # 找最後一個數字作為金額
                                for item in reversed(row_list):
                                    if isinstance(item, (int, float)):
                                        u_dict[key] = item
                                        break
                        
                        u_res = get_data_from_dict(u_dict)
                        final_df.loc['📁 上傳報表'] = u_res
                        st.success("✅ 上傳報表解析成功！已插在表格首行。")

                # 3. 呈現結果
                st.subheader(f"📈 {stock_id} 財務指標全清單")
                st.dataframe(final_df.style.format("{:.2f}"))

                # 4. 繪製曲線 (排除上傳報表以防干擾)
                plot_df = final_df.drop('📁 上傳報表', errors='ignore').sort_index()
                if not plot_df.empty:
                    st.subheader("📊 近五年成長曲線圖")
                    fig = go.Figure()
                    for col in ['毛利率', '淨利率', '負債比率', '流動比率']:
                        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], name=col, mode='lines+markers'))
                    fig.update_layout(hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ 發生錯誤: {e}")
