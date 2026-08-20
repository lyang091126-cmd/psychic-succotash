import akshare as ak
import datetime
import json
import os
import streamlit as st
from openai import OpenAI

CACHE_FILE = "cailianshe_news_cache.json"

def load_cached_news():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

@st.cache_data(ttl=180, show_spinner=False)
def fetch_cls_news():
    """Fetch new cls news and update the local JSON cache."""
    try:
        df_news = ak.stock_info_global_cls()
    except Exception as e:
        # If fetch fails, we just return whatever is in the cache
        return load_cached_news()
    
    if df_news.empty:
        return load_cached_news()
        
    # Process fetched news
    fetched_list = df_news.to_dict('records')
    
    # Load existing cache
    history = load_cached_news()
    
    # Deduplicate and Append
    # Key: 发布日期 + 发布时间 + 标题
    existing_keys = set()
    for item in history:
        key = f"{item.get('发布日期', '')}_{item.get('发布时间', '')}_{item.get('标题', '')}"
        existing_keys.add(key)
        
    for item in fetched_list:
        key = f"{item.get('发布日期', '')}_{item.get('发布时间', '')}_{item.get('标题', '')}"
        if key not in existing_keys:
            history.append(item)
            existing_keys.add(key)
            
    # Prune (keep only last 72 hours)
    now = datetime.datetime.now()
    pruned_history = []
    for item in history:
        date_str = item.get('发布日期')
        time_str = item.get('发布时间')
        try:
            if date_str and time_str:
                dt_str = f"{date_str} {time_str}"
                dt_obj = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                if (now - dt_obj).total_seconds() <= 72 * 3600:
                    pruned_history.append(item)
            else:
                pruned_history.append(item) # Keep if can't parse
        except:
            pruned_history.append(item)
            
    # Save back to JSON
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(pruned_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass
        
    return pruned_history

def classify_news(title, content):
    text = (str(title) + " " + str(content)).lower()
    
    # Priority 1: 全球事件 (Global Events) - 最高优先级拦截
    global_kws = ['美国', '美联储', '非农', 'cpi', '欧洲', '日央行', '拜登', '普京', '国际', '华尔街', '纳指', '标普', '海外', '世贸', '联储']
    if any(kw in text for kw in global_kws):
        return "全球事件"
        
    # Priority 2: 部门政策 (Domestic Policy) - 排除掉全球事件后
    policy_kws = ['发改委', '央行', '国务院', '住建部', '财政部', '证监会', '工信部', '商务部', '印发', '条例', '新规', '十四五', '征求意见']
    if any(kw in text for kw in policy_kws):
        return "部门政策"
        
    # Priority 3: 公司公告 (Company Announcements)
    company_kws = ['财报', '营收', '净利', '涨停', '跌停', '股份', '有限公司', '拟收购', '分红', 'st', '复牌', '股东减持', '实控人']
    if any(kw in text for kw in company_kws):
        return "公司公告"
        
    # Priority 4: 行业/机构 (Industry/Institutions) - 默认兜底
    return "行业/机构"


def get_market_tape_ui(used_key=""):
    st.markdown("---")
    
    with st.container(height=600):
        st.markdown("### 📡 全市场实时盘口 (财联社全球快讯)")
        st.markdown("<div style='font-size:0.85rem; opacity:0.8;'>此模块实时抓取财联社最新电报，并可通过 AI 提取客观事件影响，绝不提供买卖建议。</div><br>", unsafe_allow_html=True)
        
        with st.spinner("正在同步全球快讯..."):
            news_list = fetch_cls_news()
            
        if not news_list:
            st.warning("暂无快讯数据，可能是首次拉取失败或接口限流。")
            return
            
        # Sort by datetime descending
        def get_dt(item):
            try:
                return datetime.datetime.strptime(f"{item.get('发布日期', '')} {item.get('发布时间', '')}", "%Y-%m-%d %H:%M:%S")
            except:
                return datetime.datetime.min
        news_list.sort(key=get_dt, reverse=True)
            
        st.caption(f"最新更新时间: {news_list[0].get('发布日期')} {news_list[0].get('发布时间')}")
        
        # 分类数据
        df_company, df_global, df_policy, df_industry = [], [], [], []
        
        for row in news_list:
            category = classify_news(row.get('标题', ''), row.get('内容', ''))
            if category == "公司公告": df_company.append(row)
            elif category == "全球事件": df_global.append(row)
            elif category == "部门政策": df_policy.append(row)
            else: df_industry.append(row)
                
        tabs = st.tabs([f"🏢 公司公告 ({len(df_company)})", f"🌍 全球事件 ({len(df_global)})", f"🏛️ 部门政策 ({len(df_policy)})", f"🏭 行业/机构 ({len(df_industry)})"])
        
        def render_news_list(c_list, prefix):
            if not c_list:
                st.info("暂无该分类的最新动态")
                return
            for i, row in enumerate(c_list[:50]): # Display up to 50 per tab to avoid UI lag
                title = row.get('标题', '')
                content = row.get('内容', '')
                pub_time = row.get('发布时间', '')
                
                if not title and content:
                    title = content[:30] + "..."
                    
                with st.expander(f"🕒 {pub_time} | {title}", expanded=(i==0)):
                    st.write(content)
                    
                    # Create a safe unique key
                    safe_title_hash = abs(hash(title)) % 10000
                    btn_key = f"ai_btn_tape_{prefix}_{i}_{safe_title_hash}"
                    res_key = f"ai_res_tape_{prefix}_{i}_{safe_title_hash}"
                    
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
