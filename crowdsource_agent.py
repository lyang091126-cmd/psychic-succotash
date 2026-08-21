import streamlit as st
import json
import os
import numpy as np

def get_crowdsource_ui(api_key, ticker, all_data=None):
    if not ticker:
        return
        
    st.markdown("---")
    st.markdown(f"## 🧮 {ticker} 相对估值与财务预测推演计算器")
    st.markdown("<div style='font-size:0.85rem; opacity:0.8; margin-bottom:1rem;'>通过设定预测业绩指标与目标估值倍数，多维推演出合理的股价与市值区间。</div>", unsafe_allow_html=True)
    
    # 提取客观基础财务指标
    info = all_data.get('info', {}) if all_data else {}
    price = info.get('currentPrice') or info.get('regularMarketPrice') or 1.0
    mcap = info.get('marketCap')
    currency = info.get('currency', 'USD')
    is_usd = currency in ['USD', '$']
    unit_lbl = "亿美元" if is_usd else "亿元"
    price_lbl = "$" if is_usd else "元"
    
    # 计算总股本 (单位: 亿股)
    shares = info.get('sharesOutstanding')
    if (shares is None or shares == 0) and mcap and price:
        shares = mcap / price
    if shares is None or shares == 0:
        shares = 1e9 # 默认 10 亿股
    shares_in_100m = shares / 1e8
    
    # 默认值估算 (单位: 亿元/亿美元)
    def_rev = 0.0
    def_net_inc = 0.0
    def_net_assets = 0.0
    if info:
        rev_val = info.get('totalRevenue')
        if rev_val: def_rev = rev_val / 1e8
        net_inc_val = info.get('netIncome') or info.get('netIncomeToCommon')
        if net_inc_val: def_net_inc = net_inc_val / 1e8
        bv = info.get('bookValue')
        if bv:
            def_net_assets = (bv * (shares or 1e9)) / 1e8
        else:
            total_assets = info.get('totalAssets', 0) or 0
            total_liab = info.get('totalLiabilities', 0) or 0
            if total_assets > total_liab:
                def_net_assets = (total_assets - total_liab) / 1e8
            elif mcap:
                def_net_assets = mcap / 1e8 / 3.0
                
    # 行业基准配置
    industry = info.get('industry', '')
    sector = info.get('sector', '')
    ref_pe, ref_pb, ref_ps = 20.0, 3.0, 4.0
    if 'Semiconductors' in industry or 'Computer Hardware' in industry:
        ref_pe, ref_pb, ref_ps = 35.0, 8.0, 10.0
    elif 'Software' in industry or 'Internet' in sector:
        ref_pe, ref_pb, ref_ps = 30.0, 6.0, 8.0
    elif 'Auto' in industry:
        ref_pe, ref_pb, ref_ps = 25.0, 4.0, 2.5
    elif 'Beverages' in industry or 'Food' in sector:
        ref_pe, ref_pb, ref_ps = 25.0, 6.0, 7.0

    # 布局：左侧输入预测财务指标，右侧滑动设定估值倍数
    calc_c1, calc_c2 = st.columns([1, 1.2])
    
    with calc_c1:
        st.write("#### 1. 预测财务指标")
        pred_rev = st.number_input(f"预测营业收入 ({unit_lbl})", min_value=0.0, value=float(def_rev) if def_rev > 0 else 100.0, step=10.0, key="calc_pred_rev")
        pred_net_inc = st.number_input(f"预测净利润 ({unit_lbl})", min_value=0.0, value=float(def_net_inc) if def_net_inc > 0 else 15.0, step=2.0, key="calc_pred_net_inc")
        pred_net_assets = st.number_input(f"预测净资产 ({unit_lbl})", min_value=0.0, value=float(def_net_assets) if def_net_assets > 0 else 60.0, step=5.0, key="calc_pred_net_assets")
        
    with calc_c2:
        st.write("#### 2. 设定目标估值倍数")
        
        # PE Slider + Reference
        col_pe1, col_pe2 = st.columns([2.2, 1])
        with col_pe1:
            target_pe = st.slider("目标 PE 倍数 (x)", min_value=1.0, max_value=150.0, value=float(ref_pe), step=0.5, key="calc_target_pe")
        with col_pe2:
            st.markdown(f"<div style='margin-top:20px; font-size:0.75rem; color:#94a3b8; line-height:1.2;'>行业中位 PE:<br><b style='color:#ef4444; font-size:0.9rem;'>{ref_pe:.1f}x</b></div>", unsafe_allow_html=True)
            
        # PB Slider + Reference
        col_pb1, col_pb2 = st.columns([2.2, 1])
        with col_pb1:
            target_pb = st.slider("目标 PB 倍数 (x)", min_value=0.1, max_value=30.0, value=float(ref_pb), step=0.1, key="calc_target_pb")
        with col_pb2:
            st.markdown(f"<div style='margin-top:20px; font-size:0.75rem; color:#94a3b8; line-height:1.2;'>行业中位 PB:<br><b style='color:#ef4444; font-size:0.9rem;'>{ref_pb:.1f}x</b></div>", unsafe_allow_html=True)

        # PS Slider + Reference
        col_ps1, col_ps2 = st.columns([2.2, 1])
        with col_ps1:
            target_ps = st.slider("目标 PS 倍数 (x)", min_value=0.1, max_value=30.0, value=float(ref_ps), step=0.1, key="calc_target_ps")
        with col_ps2:
            st.markdown(f"<div style='margin-top:20px; font-size:0.75rem; color:#94a3b8; line-height:1.2;'>行业中位 PS:<br><b style='color:#ef4444; font-size:0.9rem;'>{ref_ps:.1f}x</b></div>", unsafe_allow_html=True)
        
    # 计算估值结果
    pe_price = (pred_net_inc * target_pe) / shares_in_100m if shares_in_100m > 0 else 0.0
    pb_price = (pred_net_assets * target_pb) / shares_in_100m if shares_in_100m > 0 else 0.0
    ps_price = (pred_rev * target_ps) / shares_in_100m if shares_in_100m > 0 else 0.0
    
    pe_mcap = pred_net_inc * target_pe
    pb_mcap = pred_net_assets * target_pb
    ps_mcap = pred_rev * target_ps
    
    prices = [pe_price, pb_price, ps_price]
    mcaps = [pe_mcap, pb_mcap, ps_mcap]
    min_p, max_p = min(prices), max(prices)
    min_m, max_m = min(mcaps), max(mcaps)

    # 3. 页面最下方展示一个高亮的方框结论 (Neon Highlight Box) - 必须顶格，不能包含任何前导空格！
    html_code = f"""<style>
.neon-box {{
    background: rgba(10, 15, 30, 0.75);
    border: 1px solid #00F2FE;
    box-shadow: 0 0 15px rgba(0, 242, 254, 0.35);
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1.2rem;
    margin-bottom: 1.5rem;
}}
.neon-row {{
    display: grid;
    grid-template-columns: 1fr 1.2fr;
    gap: 20px;
}}
.neon-card {{
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}}
.neon-card-title {{
    font-size: 0.85rem;
    color: #94A3B8;
    margin-bottom: 0.3rem;
    font-weight: 500;
}}
.neon-card-val {{
    font-size: 1.6rem;
    font-weight: 800;
    color: #00F2FE;
    text-shadow: 0 0 8px rgba(0, 242, 254, 0.5);
}}
.neon-card-sub {{
    font-size: 0.78rem;
    opacity: 0.7;
    margin-top: 0.2rem;
    color: #94A3B8;
}}
.neon-details {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
}}
.neon-subcard {{
    background: rgba(255, 255, 255, 0.01);
    padding: 10px;
    border-radius: 6px;
    text-align: center;
    font-size: 0.82rem;
    border: 1px solid rgba(255, 255, 255, 0.04);
}}
</style>
<div class="neon-box">
    <div style="font-size:1.1rem; font-weight:700; color:#00F2FE; margin-bottom:15px; text-shadow:0 0 10px rgba(0, 242, 254, 0.4); text-align:center;">
        🎯 财务预测与多维相对估值推演结论
    </div>
    <div class="neon-row">
        <div class="neon-card">
            <div class="neon-card-title">推演合理股价区间</div>
            <div class="neon-card-val">{price_lbl} {min_p:.2f} ~ {price_lbl} {max_p:.2f}</div>
            <div class="neon-card-sub">当前实际股价: {price_lbl} {price:.2f}</div>
        </div>
        <div class="neon-card" style="border-color: rgba(0, 242, 254, 0.25);">
            <div class="neon-card-title">推演目标市值区间</div>
            <div class="neon-card-val">{min_m:.2f}亿 ~ {max_m:.2f}亿 ({currency})</div>
            <div class="neon-card-sub">计算股本基准: {shares_in_100m:.2f} 亿股</div>
        </div>
    </div>
    <div style="margin-top: 15px;" class="neon-details">
        <div class="neon-subcard">
            <div style="color:#94a3b8; font-size:0.75rem;">PE 估值 (利润 × PE)</div>
            <div style="font-weight:700; color:#38bdf8; margin-top:3px; font-size:1rem;">{price_lbl}{pe_price:.2f}</div>
            <div style="color:#64748b; font-size:0.7rem;">目标市值: {pe_mcap:.2f}亿</div>
        </div>
        <div class="neon-subcard">
            <div style="color:#94a3b8; font-size:0.75rem;">PB 估值 (净资产 × PB)</div>
            <div style="font-weight:700; color:#38bdf8; margin-top:3px; font-size:1rem;">{price_lbl}{pb_price:.2f}</div>
            <div style="color:#64748b; font-size:0.7rem;">目标市值: {pb_mcap:.2f}亿</div>
        </div>
        <div class="neon-subcard">
            <div style="color:#94a3b8; font-size:0.75rem;">PS 估值 (营收 × PS)</div>
            <div style="font-weight:700; color:#38bdf8; margin-top:3px; font-size:1rem;">{price_lbl}{ps_price:.2f}</div>
            <div style="color:#64748b; font-size:0.7rem;">目标市值: {ps_mcap:.2f}亿</div>
        </div>
    </div>
</div>"""
    st.markdown(html_code, unsafe_allow_html=True)

    # 下方原 UGC 录入功能
    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
    with st.expander("🤖 UGC 众包预期录入与查看", expanded=False):
        st.markdown(f"#### 📈 {ticker} 众包财务预期录入")
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
                revenue_unit = st.selectbox("营收单位", [unit_lbl, "百万元"])
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
            st.markdown(f"##### 🔓 {ticker} 大众预测底牌")
            
            # Load all data for stats
            file_path = "predictions.json"
            ticker_data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        all_d = json.load(f)
                        ticker_data = [d for d in all_d if d.get('ticker') == ticker]
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
                    
            c1_s, c2_s, c3_s = st.columns(3)
            
            if rev_list:
                med_rev = np.median(rev_list)
                mean_rev = np.mean(rev_list)
                c1_s.metric("大众预测营收 (中位数)", f"{med_rev:.2f} {most_used_unit}", f"平均数: {mean_rev:.2f} {most_used_unit}", delta_color="off")
            else:
                c1_s.metric("大众预测营收", "N/A")
                
            if margin_list:
                med_margin = np.median(margin_list)
                mean_margin = np.mean(margin_list)
                c2_s.metric("大众预测毛利率 (中位数)", f"{med_margin:.2f}%", f"平均数: {mean_margin:.2f}%", delta_color="off")
            else:
                c2_s.metric("大众预测毛利率", "N/A")
                
            c3_s.metric("总参与预测人数", f"{len(ticker_data)} 人")
            
            with st.expander("💬 查看大家的核心逻辑提炼 (最新10条)"):
                for idx, lg in enumerate(reversed(logics[-10:])):
                    st.markdown(f"- **玩家 {len(logics)-idx}**: {lg}")
