import akshare as ak
import datetime
from openai import OpenAI
import streamlit as st

def get_market_tape_ui(used_key=""):
    st.markdown("---")
    
    with st.container(height=500):
        st.markdown("### 📡 全市场实时盘口 (财联社全球快讯)")
        st.markdown("<div style='font-size:0.85rem; opacity:0.8;'>此模块实时抓取财联社最新电报，并可通过 AI 提取客观事件影响，绝不提供买卖建议。</div><br>", unsafe_allow_html=True)
        
        try:
            with st.spinner("正在实时拉取财联社电报/快讯..."):
                df_news = ak.stock_info_global_cls()
        except Exception as e:
            st.error(f"拉取数据失败: {e}")
            return
            
        if df_news.empty:
            st.warning("暂无最新快讯")
            return
            
        st.caption(f"最新更新时间: {df_news['发布日期'].iloc[0]} {df_news['发布时间'].iloc[0]}")
        
        # Render top 20 news
        for i, row in df_news.head(20).iterrows():
            title = row.get('标题', '')
            content = row.get('内容', '')
            pub_time = row.get('发布时间', '')
            
            if not title and content:
                title = content[:30] + "..."
                
            with st.expander(f"🕒 {pub_time} | {title}", expanded=(i<2)):
                st.write(content)
                
                # Button for AI Interpretation
                btn_key = f"ai_btn_tape_{i}"
                res_key = f"ai_res_tape_{i}"
                
                if st.button("🤖 AI 深度客观解读", key=btn_key):
                    if not used_key:
                        st.warning("⚠️ 请先在上方输入 API 密钥 (智谱清言 或 OpenAI)")
                    else:
                        with st.spinner("AI 正在客观分析事件影响与涉及标的..."):
                            try:
                                if used_key.startswith("sk-proj-"):
                                    base_url = "https://api.openai.com/v1"
                                    model_name = "gpt-4o-mini"
                                else:
                                    base_url = "https://open.bigmodel.cn/api/paas/v4/"
                                    model_name = "glm-4-flash"
                                    
                                client = OpenAI(api_key=used_key, base_url=base_url)
                                
                                prompt = f"""
请作为一位中立的金融数据分析师，深度且客观地解读以下快讯。
【核心规则】：
绝对不允许生成任何投资建议、买入/卖出评级或目标价预测。只提取客观事实与直接的产业逻辑。

【快讯内容】：
{title}
{content}

【请按以下格式输出】：
**1. 事件定性**：(如：产业并购、财报超预期、宏观政策利好等)
**2. 涉及板块/标的**：(直接相关的行业板块或股票名称，如：星网锐捷、通信设备)
**3. 客观影响链条**：(简要分析该事件对产业链上下游或公司基本面的客观影响，不带主观情绪预测)
"""
                                response = client.chat.completions.create(
                                    model=model_name,
                                    messages=[{"role": "user", "content": prompt}],
                                    temperature=0.1
                                )
                                st.session_state[res_key] = response.choices[0].message.content
                            except Exception as e:
                                st.error(f"AI 调用失败: {e}")
                
                if res_key in st.session_state:
                    st.info(st.session_state[res_key])
