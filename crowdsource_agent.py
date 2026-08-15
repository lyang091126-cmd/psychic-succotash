import streamlit as st
import json
import os
import re
import numpy as np
from openai import OpenAI

def get_crowdsource_ui(api_key, ticker):
    if not ticker:
        return
        
    st.markdown("---")
    st.markdown(f"## 📈 {ticker} 众包财务预测量化 (UGC Forecasts) <span style='font-size:0.72rem; opacity:0.6;'>大白话秒变华尔街标准预期</span>", unsafe_allow_html=True)
    
    # Check if user has already submitted
    session_key = f"crowdsource_submitted_{ticker}"
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    user_prediction = st.text_area(f"输入你对 {ticker} 的商业感知 (例如：下个季度他们家产品肯定卖爆，利润起码涨两成)", height=100)
    
    if st.button("🤖 提交 AI 智能量化预测并解锁大众预期", key=f"btn_crowd_predict_{ticker}", use_container_width=True):
        if not user_prediction.strip():
            st.warning("请输入你的预测逻辑。")
        elif not api_key:
            st.warning("⚠️ 请先在页面上方输入 API 密钥 (智谱清言 或 OpenAI)。")
        else:
            with st.spinner("AI 量化 Agent 正在进行标准化语义映射..."):
                try:
                    if api_key.startswith("sk-proj-"):
                        base_url = "https://api.openai.com/v1"
                        model_name = "gpt-4o-mini"
                    else:
                        base_url = "https://open.bigmodel.cn/api/paas/v4/"
                        model_name = "glm-4-flash"
                    
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    system_prompt = """
# Role
你是一个专用于 Anti Securities Report 平台的“众包财务预测量化 Agent”。你具备顶尖注册会计师（CPA）与资深卖方分析师的专业素养。你的任务是解析前端长尾用户口语化、碎片化的商业感知，精准映射为标准财务指标预测，并输出纯 JSON 格式数据供后端 Python 环境及 Streamlit 前端渲染处理。

# Objectives
1. **语义映射**：将用户如“下个季度他们家 AI 芯片肯定卖爆，利润起码涨两成”等表述，科学地映射为对“营业收入（Revenue）”或“毛利率（Gross Margin）”的具体数值预期。
2. **财务准则把控**：严格对齐合并报表、资产重分类等底层逻辑，确保用户预测口径与 GAAP/Non-GAAP 财报真实口径一致，剔除一次性损益的噪音。
3. **结构化输出**：仅返回 JSON 数据，便于后端的数据库写入与最终的误差自动核算。

# Rules & Constraints
1. **合规红线**：绝对禁止预测二级市场交易价格（如目标价、股价涨幅）。若用户提及，必须忽略该部分并在逻辑总结中客观提示：“本平台仅统计核心基本面经营数据预测”。
2. **容错与推演**：若用户未指定具体金额单位，请根据 A 股或美股主流科技、半导体标的的常规财务体量，自动转换为“亿元 (100M RMB)”或“百万美元 (1M USD)”。

# Output Format (JSON Only)
严格输出如下格式，不要附带任何 Markdown 解释：
{
  "ticker": "STRING (例如: 688981.SH)",
  "fiscal_quarter": "YYYYQ[1-4]",
  "predictions": {
    "revenue_estimate": FLOAT,
    "revenue_unit": "100M RMB",
    "gross_margin_estimate": FLOAT
  },
  "user_logic_summary": "STRING (提炼用户的核心基本面逻辑，不超过30字)",
  "status": "PENDING_ACTUALS"
}
"""
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"当前标的: {ticker}\n用户输入: {user_prediction}"}
                        ],
                        temperature=0.1
                    )
                    
                    raw_output = response.choices[0].message.content
                    json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                    if json_match:
                        parsed_data = json.loads(json_match.group(0))
                        parsed_data['ticker'] = ticker  # 强制归属当前标的
                        
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
                        except Exception as e:
                            st.warning(f"数据落地存储失败: {e}")
                            
                        st.success("✅ 智能预测已成功量化并录入众包数据库！底牌已为您揭晓！")
                        st.session_state[session_key] = True
                        st.session_state[f"last_pred_{ticker}"] = parsed_data
                    else:
                        st.error("AI 返回的数据不符合严格的 JSON 格式，解析失败。")
                        st.code(raw_output)
                        
                except Exception as e:
                    st.error(f"AI 调用失败: {e}")
                    
    if st.session_state[session_key]:
        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
        st.markdown(f"### 🔓 {ticker} 大众预测底牌揭晓")
        
        # 加载所有数据进行统计
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
        unit = "N/A"
        
        for d in ticker_data:
            p = d.get('predictions', {})
            rev = p.get('revenue_estimate')
            margin = p.get('gross_margin_estimate')
            if isinstance(rev, (int, float)):
                rev_list.append(rev)
                unit = p.get('revenue_unit', unit)
            if isinstance(margin, (int, float)):
                margin_list.append(margin)
            logic = d.get('user_logic_summary')
            if logic:
                logics.append(logic)
                
        c1, c2, c3 = st.columns(3)
        
        if rev_list:
            med_rev = np.median(rev_list)
            mean_rev = np.mean(rev_list)
            c1.metric("大众预测营收 (中位数)", f"{med_rev:.2f} {unit}", f"平均数: {mean_rev:.2f} {unit}", delta_color="off")
        else:
            c1.metric("大众预测营收", "N/A")
            
        if margin_list:
            med_margin = np.median(margin_list)
            mean_margin = np.mean(margin_list)
            c2.metric("大众预测毛利率 (中位数)", f"{med_margin:.2f}%", f"平均数: {mean_margin:.2f}%", delta_color="off")
        else:
            c2.metric("大众预测毛利率", "N/A")
            
        c3.metric("总参与预测人数", f"{len(ticker_data)} 人")
        
        with st.expander("💬 查看大家的核心逻辑提炼"):
            for idx, lg in enumerate(reversed(logics[-10:])):
                st.markdown(f"- **预测 {len(logics)-idx}**: {lg}")
