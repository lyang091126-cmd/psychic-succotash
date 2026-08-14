import akshare as ak
import datetime
from openai import OpenAI
import streamlit as st

def get_market_tape_ui(used_key=""):
    st.markdown("---")
    
    with st.container(height=600):
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
            
        # 翻转数据：财联社接口默认最老的新闻在最前面，我们需要最新的在最前面
        df_news = df_news.iloc[::-1].reset_index(drop=True)
            
        st.caption(f"最新更新时间: {df_news['发布日期'].iloc[0]} {df_news['发布时间'].iloc[0]}")
        
        import re
        
        # 关键词分类字典
        kw_global = ['美国', '油价', '金价', '原油', '黄金', '美联储', '拜登', '普京', '俄乌', '中东', '降息', '加息', '欧洲', '英国', '日本', '纳指', '标普', '道指', '华尔街', '全球', '战争', '冲突', '大选', '联储']
        kw_policy = ['发改委', '国务院', '央行', '人民银行', '证监会', '财政部', '工信部', '外汇局', '税务局', '税务部门', '银保监', '金管局', '交通部', '商务部', '住建部', '农业农村部', '农业部', '教育部', '科技部', '民政部', '司法部', '人社部', '卫健委', '统计局', '医保局', '林草局', '能源局', '药监局', '知识产权局', '海关总署', '政策', '条例', '规定', '征求意见', '局', '委']
        kw_industry = ['机构', '基金', '私募', '资本', '对冲基金', '巴克莱', '高盛', '摩根', '花旗', '瑞银', '野村', '贝莱德', '桥水', '行业', '赛道', '渗透率', '协会', '乘联会', '销量', '出货量', '市场规模']
        
        # 分类数据
        df_company, df_global, df_policy, df_industry = [], [], [], []
        
        for _, row in df_news.head(100).iterrows():
            title = str(row.get('标题', ''))
            content = str(row.get('内容', ''))
            text = title + content
            
            # 公司公告识别逻辑：标题中含有类似于 "生益科技：" 这种模式 (2-8个字符的名称加上中文冒号)
            # 或文中明确提到 股份、业绩等
            is_company = bool(re.search(r'[\u4e00-\u9fa5A-Za-z0-9]{2,10}：', title) or re.search(r'[\u4e00-\u9fa5A-Za-z0-9]{2,10}：', content[:30]))
            if not is_company and any(k in text for k in ['股份', '股东', '业绩', '净利润', '营收', '同比', '环比', '分红', '派息', '增持', '减持', '回购', '子公司', '财报']):
                is_company = True
            
            # 分类优先级：政策 > 全球 > 行业 > 公司 (避免部门政策的新闻带冒号被误判为公司公告)
            if any(k in text for k in kw_policy):
                df_policy.append(row)
            elif any(k in text for k in kw_global):
                df_global.append(row)
            elif any(k in text for k in kw_industry):
                df_industry.append(row)
            elif is_company:
                df_company.append(row)
                
        tabs = st.tabs([f"🏢 公司公告 ({len(df_company)})", f"🌍 全球事件 ({len(df_global)})", f"🏛️ 部门政策 ({len(df_policy)})", f"🏭 行业/机构 ({len(df_industry)})"])
        
        def render_news_list(news_list, prefix):
            if not news_list:
                st.info("暂无该分类的最新动态")
                return
            for i, row in enumerate(news_list):
                title = row.get('标题', '')
                content = row.get('内容', '')
                pub_time = row.get('发布时间', '')
                
                if not title and content:
                    title = content[:30] + "..."
                    
                with st.expander(f"🕒 {pub_time} | {title}", expanded=(i==0)):
                    st.write(content)
                    
                    btn_key = f"ai_btn_tape_{prefix}_{i}"
                    res_key = f"ai_res_tape_{prefix}_{i}"
                    
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

        with tabs[0]: render_news_list(df_company, 'comp')
        with tabs[1]: render_news_list(df_global, 'glob')
        with tabs[2]: render_news_list(df_policy, 'poli')
        with tabs[3]: render_news_list(df_industry, 'indu')
