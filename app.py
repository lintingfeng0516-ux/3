import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from FinMind.data import DataLoader
from datetime import datetime

st.set_page_config(page_title="專業財報分析站", layout="wide")
st.title("📊 財報自動化解析系統 (114年 Excel 兼容版)")

with st.sidebar:
    st.header("1. 設定來源")
    stock_id = st.text_input("輸入台股代碼", value="2330")
    uploaded_file = st.file_uploader("上傳 Excel 財報 (114年格式 OK)", type=['xlsx'])
    analyze_btn = st.button("🚀 執行全面分析")

# --- 超強關鍵字模糊對照 (根據您的截圖優化) ---
MAPS = {
    'rev': ['營業收入合計', '營業收入', 'OperatingRevenue'],
    'cost': ['營業成本合計', '營業成本', 'CostOfGoodsSold'],
    'net': ['本期淨利（淨損）', '本期淨利', 'NetIncome'],
    'ca': ['流動資產合計', '流動資產', 'CurrentAssets'],
    'cl': ['流動負債合計', '流動負債', 'CurrentLiabilities'],
    'inv': ['存貨', 'Inventory'],
    'pre': ['預付款項', 'Prepayments'],
    'ta': ['資產總額', '資產合計', 'TotalAssets'],
    'tl': ['負債總額', '負債合計', 'TotalLiabilities'],
    'op': ['營業利益', 'OperatingIncome'],
    'ie': ['利息費用', 'InterestExpense'],
    'ar': ['應收帳款淨額', 'AccountsReceivable']
}

def get_data_from_dict(d):
    def find(keys):
        # 移除標點與空白進行匹配
        for k, v in d.items():
            k_clean = str(k).replace(" ", "").replace("　", "").replace("（", "").replace("）", "")
            for target in keys:
                if target in k_clean: return v
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
        # 1. 抓取數據 (強制合併損益表與資產負債表)
        with st.spinner('正在從資料庫同步 損益表 與 資產負債表...'):
            df = dl.taiwan_stock_financial_statement(stock_id=stock_id, start_date="2019-01-01")
            
            if df.empty:
                st.error("❌ 抓不到歷史數據。")
            else:
                # 合併數據並計算
                history_list = []
                for date, group in df.groupby('date'):
                    d_temp = dict(zip(group['type'], group['value']))
                    res = get_data_from_dict(d_temp)
                    res['日期'] = date
                    history_list.append(res)
                
                final_df = pd.DataFrame(history_list).set_index('日期').sort_index(ascending=False)

                # 2. 解析上傳 Excel (針對截圖格式優化)
                if uploaded_file:
                    u_df = pd.read_excel(uploaded_file)
                    # 遍歷每一列，尋找科目與數字
                    u_dict = {}
                    for _, row in u_df.iterrows():
                        items = row.dropna().tolist()
                        if len(items) >= 2:
                            name = str(items[0])
                            # 找這一列裡面最大的數字，通常就是金額 (避開百分比)
                            nums = [i for i in items if isinstance(i, (int, float)) and i > 100]
                            if nums: u_dict[name] = nums[0]
                    
                    u_res = get_data_from_dict(u_dict)
                    final_df.loc['📁 上傳報表 (114年)'] = u_res
                    st.success("✅ 已解析 Excel 數據，並與歷史數據對比成功！")

                # 3. 呈現結果
                st.subheader(f"📈 {stock_id} 財務指標全面清單")
                st.dataframe(final_df.style.format("{:.2f}"))

                # 4. 繪製曲線
                plot_df = final_df.drop('📁 上傳報表 (114年)', errors='ignore').sort_index()
                st.subheader("📊 歷史趨勢圖")
                fig = go.Figure()
                for col in ['毛利率', '流動比率', '負債比率']:
                    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df[col], name=col))
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("🔍 除錯：查看 Excel 抓到了什麼科目"):
                    st.write(u_dict if uploaded_file else "未上傳檔案")

    except Exception as e:
        st.error(f"系統錯誤: {e}")
