import streamlit as st
import json
import os
import numpy as np

def get_crowdsource_ui(api_key, ticker):
    if not ticker:
        return
        
    st.markdown("---")
    st.markdown(f"## 📈 {ticker} 众包财务预期量化 (UGC Forecasts) <span style='font-size:0.72rem; opacity:0.6;'>提交您的业绩预期，解锁大众博弈底牌</span>", unsafe_allow_html=True)
    
    session_key = f"crowdsource_submitted_{ticker}"
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    # Input Form
    with st.form(key=f"crowd_form_{ticker}"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            fiscal_quarter = st.text_input("预测财季", value="2026Q3", help="例如 2026Q3 或 2026FY")
        with col2:
            revenue_estimate = st.number_input("预期营业收入", min_value=0.0, format="%.2f", step=1.0)
            revenue_unit = st.selectbox("营收单位", ["亿元 (100M RMB)", "百万美元 (1M USD)", "千万美元", "百万元"])
        with col3:
            gross_margin = st.number_input("预期毛利率 (%)", min_value=0.0, max_value=100.0, format="%.2f", step=0.1)
            
        user_logic = st.text_input("核心看多/看空逻辑 (选填)", placeholder="例如：下一代 AI 芯片产能爬坡，利润率超预期")
        
        submitted = st.form_submit_button("🤖 提交我的预期，并解锁大众预测底牌", use_container_width=True)
        
        if submitted:
            parsed_data = {
                "ticker": ticker,
                "fiscal_quarter": fiscal_quarter,
                "predictions": {
                    "revenue_estimate": revenue_estimate,
                    "revenue_unit": revenue_unit,
                    "gross_margin_estimate": gross_margin
                },
                "user_logic_summary": user_logic if user_logic else "未填写具体逻辑",
                "status": "PENDING_ACTUALS"
            }
            
            # Save to file
            try:
                file_path = "predictions.json"
                existing_data = []
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            existing_data = json.load(f)
                        except:
                            pass
                existing_data.append(parsed_data)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)
                st.success("✅ 数据已成功录入众包数据库！底牌已为您揭晓！")
                st.session_state[session_key] = True
            except Exception as e:
                st.warning(f"数据落地存储失败: {e}")
                    
    # Display Stats if submitted
    if st.session_state[session_key]:
        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
        st.markdown(f"### 🔓 {ticker} 大众预测底牌揭晓")
        
        # Load all data for stats
        file_path = "predictions.json"
        ticker_data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
                    ticker_data = [d for d in all_data if d.get('ticker') == ticker]
            except:
                pass
                
        if not ticker_data:
            st.info("暂无足够的有效预测数据。")
            return
            
        rev_list = []
        margin_list = []
        logics = []
        unit_counts = {}
        
        for d in ticker_data:
            p = d.get('predictions', {})
            rev = p.get('revenue_estimate')
            margin = p.get('gross_margin_estimate')
            if isinstance(rev, (int, float)) and rev > 0:
                rev_list.append(rev)
                u = p.get('revenue_unit', '')
                if u:
                    unit_counts[u] = unit_counts.get(u, 0) + 1
            if isinstance(margin, (int, float)) and margin > 0:
                margin_list.append(margin)
            logic = d.get('user_logic_summary')
            if logic and logic != "未填写具体逻辑":
                logics.append(logic)
                
        # Find the most used unit
        most_used_unit = max(unit_counts, key=unit_counts.get) if unit_counts else "N/A"
                
        c1, c2, c3 = st.columns(3)
        
        if rev_list:
            med_rev = np.median(rev_list)
            mean_rev = np.mean(rev_list)
            c1.metric("大众预测营收 (中位数)", f"{med_rev:.2f} {most_used_unit}", f"平均数: {mean_rev:.2f} {most_used_unit}", delta_color="off")
        else:
            c1.metric("大众预测营收", "N/A")
            
        if margin_list:
            med_margin = np.median(margin_list)
            mean_margin = np.mean(margin_list)
            c2.metric("大众预测毛利率 (中位数)", f"{med_margin:.2f}%", f"平均数: {mean_margin:.2f}%", delta_color="off")
        else:
            c2.metric("大众预测毛利率", "N/A")
            
        c3.metric("总参与预测人数", f"{len(ticker_data)} 人")
        
        with st.expander("💬 查看大家的核心逻辑提炼 (最新10条)"):
            for idx, lg in enumerate(reversed(logics[-10:])):
                st.markdown(f"- **玩家 {len(logics)-idx}**: {lg}")
