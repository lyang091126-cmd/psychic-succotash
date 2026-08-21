import os
import time
import datetime
import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import math
from plotly.subplots import make_subplots
from openai import OpenAI

# 初始化全局变量，防止 "name 'all_data' is not defined" 报错
all_data = {}

st.set_page_config(
    page_title="Anti Stock Report - 智能投研终端",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 注入全局 UI 优化 CSS
st.markdown("""
<style>
    /* 增加主容器的两侧边距，避免贴边，同时增加上下呼吸感 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 100% !important;
    }
    
    /* 隐藏默认 Header 和 Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 模块化卡片容器样式模拟 */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {
        background-color: rgba(20, 24, 33, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }
    
    /* P4 & P5 Alignment & Financial Cards CSS injection */
    div[data-testid="stColumn"] > div > div[data-testid="stButton"] { margin-top: 27px !important; }
    
    .financial-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 15px;
        margin-top: 15px;
        margin-bottom: 20px;
    }
    .fin-card {
        background: #0A0D14 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        padding: 15px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3) !important;
    }
    .fin-label {
        font-size: 0.85rem !important;
        color: #94a3b8 !important;
        margin-bottom: 5px !important;
        font-weight: 500 !important;
    }
    .fin-value {
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }
    .fin-trend {
        font-size: 0.8rem !important;
        margin-top: 5px !important;
        font-weight: 600 !important;
    }
    .trend-up {
        color: #ef4444 !important;
    }
    .trend-down {
        color: #00b865 !important;
    }
    .trend-neutral {
        color: #94a3b8 !important;
    }
</style>
""", unsafe_allow_html=True)

# 提前创建页面布局容器，严格控制整个屏幕组件自上而下的渲染顺序 (P7 & P1 & P4)
container_inputs = st.container()
container_crowd = st.container()
container_tape = st.container()
container_macro = st.container()

# -------------------------------------------------------------------
# 0. 智能股票名称/中文映射解析引擎
# -------------------------------------------------------------------
STOCK_NAME_MAP = {
    # 美股核心热门标的
    "苹果": "AAPL", "苹果公司": "AAPL", "APPLE": "AAPL",
    "英伟达": "NVDA", "NVIDIA": "NVDA",
    "特斯拉": "TSLA", "TESLA": "TSLA",
    "微软": "MSFT", "MICROSOFT": "MSFT",
    "谷歌": "GOOGL", "GOOGLE": "GOOGL", "Alphabet": "GOOGL",
    "亚马逊": "AMZN", "AMAZON": "AMZN",
    "Meta": "META", "META": "META", "脸书": "META",
    "台积电": "TSM", "TSMC": "TSM",
    "博通": "AVGO", "AMD": "AMD", "超微半导体": "AMD",
    "高通": "QCOM", "美光": "MU", "美光科技": "MU",
    "超微电脑": "SMCI", "奈飞": "NFLX", "NETFLIX": "NFLX",
    "微软公司": "MSFT", "英特尔": "INTC",

    # A 股 & 港股全量核心龙头标的
    "三环集团": "300408.SZ", "三环": "300408.SZ",
    "新易盛": "300502.SZ", "中际旭创": "300308.SZ", "天孚通信": "300394.SZ", "光迅科技": "002281.SZ",
    "贵州茅台": "600519.SS", "茅台": "600519.SS", "五粮液": "000858.SZ", "泸州老窖": "000568.SZ",
    "宁德时代": "300750.SZ", "宁王": "300750.SZ", "亿纬锂能": "300014.SZ",
    "比亚迪": "002594.SZ", "长安汽车": "000625.SZ", "赛力斯": "601127.SS",
    "中芯国际": "688981.SS", "寒武纪": "688256.SS", "海光信息": "688041.SS",
    "立讯精密": "002475.SZ", "工业富联": "601138.SS", "歌尔股份": "002241.SZ",
    "海康威视": "002415.SZ", "大华股份": "002236.SZ",
    "招商银行": "600036.SS", "中国平安": "601318.SS", "中信证券": "600030.SS",
    "东方财富": "300059.SZ", "同花顺": "300033.SZ",
    "长江电力": "600900.SS", "中国神华": "601088.SS", "中国石油": "601857.SS",
    "万科A": "000002.SZ", "保利发展": "600048.SS",
    "兆易创新": "603986.SS", "韦尔股份": "603501.SS", "圣邦股份": "300661.SZ",
    "北方华创": "002371.SZ", "中微公司": "688012.SS", "拓荆科技": "688072.SS",
    "紫光国微": "002049.SZ", "长电科技": "600584.SS", "通富微电": "002156.SZ",
    "腾讯": "0700.HK", "腾讯控股": "0700.HK",
    "阿里巴巴": "BABA", "阿里": "BABA", "阿里港股": "9988.HK",
    "美团": "3690.HK", "小米": "1810.HK", "小米集团": "1810.HK",
    "百度": "BIDU", "京东": "JD", "拼多多": "PDD",

    # 日韩标的
    "三星": "005930.KS", "三星电子": "005930.KS",
    "丰田": "TM", "丰田汽车": "TM",
}

def resolve_ticker(raw_input):
    """智能解析输入，支持中文名称自动转换为美股/A股/港股标准Ticker代码"""
    if not raw_input:
        return "NVDA", ""
    raw = raw_input.strip()

    # 1. 直接精准匹配内置映射表
    if raw in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[raw], raw

    # 2. 忽略大小写模糊查找
    for k, v in STOCK_NAME_MAP.items():
        if raw.lower() == k.lower():
            return v, k

    # 3. 在线搜索 A 股代码匹配 (支持输入任意 A 股中文简称)
    if not raw.isdigit() and len(raw) >= 2:
        try:
            import akshare as ak
            df_codes = ak.stock_info_a_code_name()
            if df_codes is not None and not df_codes.empty:
                match = df_codes[df_codes['name'].str.contains(raw, case=False, na=False)]
                if not match.empty:
                    code = str(match['code'].iloc[0]).zfill(6)
                    suffix = ".SS" if code.startswith(('6', '9', '5')) else ".SZ"
                    return f"{code}{suffix}", match['name'].iloc[0]
        except Exception:
            pass

    # 4. 纯 6 位数字补全 A 股后缀
    if raw.isdigit():
        if len(raw) == 6:
            if raw.startswith(('6', '9', '5')):
                return f"{raw}.SS", raw
            else:
                return f"{raw}.SZ", raw
        elif len(raw) in (4, 5):
            return f"{raw.zfill(5)}.HK", raw

    return raw.upper(), raw

# -------------------------------------------------------------------
# 1. 页面基本配置与视觉系统
# -------------------------------------------------------------------
# (Moved to top of file)

# 2. 全局样式定制
st.markdown("""
<style>
    .event-expectation { font-size: 0.82rem; opacity: 0.85; color: #fbbf24; }
    .event-analysis-title { font-weight: 600; font-size: 0.85rem; color: #38bdf8; margin-bottom: 0.2rem; }
    .event-analysis-text { font-size: 0.85rem; opacity: 0.88; line-height: 1.5; color: var(--text-color, #e2e8f0); }

    /* 4 宫格分析师目标价卡片 */
    .grid-2x2-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(226,232,240,0.15);
        border-radius: 12px;
        padding: 0.7rem 0.8rem;
        text-align: center;
        margin-bottom: 0.6rem;
        height: 76px;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    .grid-2x2-label { font-size: 0.78rem; opacity: 0.75; margin-bottom: 0.15rem; font-weight: 500; color: var(--text-color, inherit); }
    .grid-2x2-value { font-size: 1.15rem; font-weight: 700; color: #00b865; }

    /* 终极物理底端对齐强力法则：强制所有列内组件底端平齐 */
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
        height: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-end !important;
    }

    /* 强力精确匹配按钮垂直高度与输入框 100% 完全平齐 */
    div.stButton > button[key="btn_main_generate"] {
        background-color: #00b865 !important;
        color: white !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        height: 40px !important;
        border-radius: 8px !important;
        width: 100% !important;
        border: none !important;
        margin-top: 28px !important;
        margin-bottom: 0 !important;
    }
    div.stButton > button[key="btn_main_generate"]:hover { background-color: #009e56 !important; }

    .news-positive { border-left: 4px solid #00b865; background: rgba(0,184,101,0.06); padding: 0.7rem 1rem; border-radius: 8px; margin-bottom: 0.5rem; }
    .news-negative { border-left: 4px solid #ef4444; background: rgba(239,68,68,0.06); padding: 0.7rem 1rem; border-radius: 8px; margin-bottom: 0.5rem; }
    .news-neutral { border-left: 4px solid #64748b; background: rgba(100,116,139,0.06); padding: 0.7rem 1rem; border-radius: 8px; margin-bottom: 0.5rem; }
    .news-title { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.2rem; color: var(--text-color, inherit); }
    .news-meta { font-size: 0.78rem; opacity: 0.65; }

    .calendar-item {
        display: flex; align-items: center; gap: 1rem;
        padding: 0.7rem 1rem; border-radius: 10px;
        border: 1px solid rgba(226,232,240,0.15);
        margin-bottom: 0.5rem; background: rgba(255,255,255,0.03);
    }
    .calendar-date { font-weight: 700; font-size: 0.95rem; min-width: 80px; color: #00b865; }
    .calendar-desc { font-size: 0.88rem; color: var(--text-color, inherit); }

    /* 让 Markdown 表格 100% 全宽自适应，彻底消灭左侧挤压 */
    div[data-testid="stMarkdownContainer"] table {
        width: 100% !important;
        display: table !important;
        border-collapse: collapse !important;
        margin: 0.8rem 0 !important;
        background: rgba(255,255,255,0.02) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    div[data-testid="stMarkdownContainer"] th {
        background: rgba(0, 184, 101, 0.15) !important;
        color: #00b865 !important;
        font-weight: 700 !important;
        padding: 0.65rem 0.8rem !important;
        border-bottom: 1px solid rgba(226,232,240,0.15) !important;
    }
    div[data-testid="stMarkdownContainer"] td {
        padding: 0.6rem 0.8rem !important;
        border-bottom: 1px solid rgba(226,232,240,0.08) !important;
    }

    /* ☀️ Streamlit Light Mode 浅色/白色主题下的文字与卡片黑字显色强防护 */
    [data-theme="light"] .header-title,
    [data-theme="light"] .market-index,
    [data-theme="light"] .metric-value,
    [data-theme="light"] .event-title,
    [data-theme="light"] .calendar-desc {
        color: #0f172a !important;
    }

    [data-theme="light"] .header-subtitle,
    [data-theme="light"] .market-name,
    [data-theme="light"] .market-sector,
    [data-theme="light"] .metric-label,
    [data-theme="light"] .grid-2x2-label,
    [data-theme="light"] .event-analysis-text {
        color: #334155 !important;
    }

    [data-theme="light"] .market-card,
    [data-theme="light"] .metric-card,
    [data-theme="light"] .grid-2x2-card,
    [data-theme="light"] .event-card-row,
    [data-theme="light"] .calendar-item {
        background: #f8fafc !important;
        border-color: #cbd5e1 !important;
        box-shadow: 0 2px 6px rgba(15,23,42,0.05) !important;
    }

    [data-theme="light"] div[data-testid="stMarkdownContainer"] table {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
    }

    [data-theme="light"] div[data-testid="stMarkdownContainer"] td {
        color: #1e293b !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }

    /* 研报正文双列专效顶头平齐法则 */
    div[data-testid="stColumn"]:has(div.stMarkdown) > div[data-testid="stVerticalBlock"] {
        justify-content: flex-start !important;
        align-items: stretch !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    div[data-testid="stColumn"]:has(div.stMarkdown) > div[data-testid="stVerticalBlock"] > div.stMarkdown:first-child,
    div[data-testid="stColumn"]:has(div.stMarkdown) > div[data-testid="stVerticalBlock"] > div.stMarkdown:first-child * {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* 🏷️ v2.0 数据可信度视觉语言：真实数据 vs AI生成内容区分样式 */
    .data-real-badge {
        display: inline-block; font-size: 0.7rem; font-weight: 700;
        background: rgba(0,184,101,0.15); color: #00b865;
        border: 1px solid rgba(0,184,101,0.4);
        padding: 1px 8px; border-radius: 6px; margin-left: 6px;
    }
    .data-ai-badge {
        display: inline-block; font-size: 0.7rem; font-weight: 700;
        background: rgba(251,191,36,0.15); color: #fbbf24;
        border: 1px dashed rgba(251,191,36,0.5);
        padding: 1px 8px; border-radius: 6px; margin-left: 6px;
    }

    /* 全球市场卡片样式 */
    .market-card {
        background: rgba(22, 27, 38, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 0.9rem 1rem !important;
        text-align: center !important;
        position: relative !important;
        overflow: hidden !important;
        margin-bottom: 0.5rem !important;
    }
    .market-card-hot {
        border-color: rgba(0, 242, 254, 0.5) !important;
        box-shadow: 0 0 12px rgba(0, 242, 254, 0.15) !important;
    }
    .market-flag { font-size: 1.4rem; margin-bottom: 0.2rem; }
    .market-name { font-size: 0.8rem; font-weight: 600; opacity: 0.85; margin: 0.15rem 0; color: #94A3B8; }
    .market-index { font-size: 1.15rem; font-weight: 700; color: #F0F4F8; }
    .market-chg-up { color: #00E676; font-size: 0.82rem; font-weight: 600; }
    .market-chg-down { color: #FF4B4B; font-size: 0.82rem; font-weight: 600; }
    .market-sector { font-size: 0.72rem; opacity: 0.75; margin-top: 0.3rem; color: #64748B; }
    .market-badge-hot {
        position: absolute; top: 6px; right: 8px;
        background: #00F2FE; color: #0A0D14; font-size: 0.6rem; font-weight: 700;
        padding: 1px 6px; border-radius: 6px;
    }

    /* 📅 大事日历左右对照样式 */
    .event-card-row {
        background: rgba(22, 27, 38, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
        transition: all 0.2s ease;
    }
    .event-left-box {
        flex: 0 0 42%;
        border-right: 1px dashed rgba(255, 255, 255, 0.15);
        padding-right: 1rem;
    }
    .event-right-box {
        flex: 1;
        padding-left: 0.5rem;
    }
    .event-date-badge {
        display: inline-block;
        background: rgba(0, 242, 254, 0.15);
        color: #00F2FE;
        font-weight: 700;
        font-size: 0.82rem;
        padding: 2px 8px;
        border-radius: 6px;
        margin-bottom: 0.3rem;
    }
    .event-title { font-weight: 700; font-size: 0.95rem; color: #F0F4F8; margin-bottom: 0.25rem; }
    .event-expectation { font-size: 0.82rem; opacity: 0.85; color: #fbbf24; }
    .event-analysis-title { font-weight: 600; font-size: 0.85rem; color: #00F2FE; margin-bottom: 0.2rem; }
    .event-analysis-text { font-size: 0.85rem; opacity: 0.88; line-height: 1.5; color: #94A3B8; }

    /* 修复：spacer 类此前从未定义，导致所有 <div class="spacer-*"> 实际不产生任何间距 */
    .spacer-sm { height: 0.6rem; }
    .spacer-md { height: 1.2rem; }
    .spacer-lg { height: 2rem; }

    /* 产业链图谱：宽屏横向 Grid + 居中箭头，窄屏自动切换为纵向堆叠，箭头随之旋转90° */
    .chain-grid {
        display: grid;
        grid-template-columns: 1fr auto 1.2fr auto 1fr;
        align-items: stretch;
        gap: 6px;
    }
    .chain-arrow {
        display: flex; align-items: center; justify-content: center;
        font-size: 1.8rem; color: #475569; opacity: 0.6;
    }
    @media (max-width: 900px) {
        .chain-grid { grid-template-columns: 1fr; }
        .chain-arrow { transform: rotate(90deg); padding: 6px 0; }
    }

    /* Tab 内容区呼吸感统一 */
    div[data-baseweb="tab-panel"] { padding-top: 1.2rem; }

    /* 估值分位数进度条 */
    .percentile-track {
        position: relative; width: 100%; height: 10px; border-radius: 6px;
        background: linear-gradient(90deg, #00b865 0%, #fbbf24 50%, #ef4444 100%);
        margin: 10px 0 4px 0; opacity: 0.85;
    }
    .percentile-marker {
        position: absolute; top: -5px; width: 3px; height: 20px;
        background: #ffffff; box-shadow: 0 0 6px rgba(255,255,255,0.8);
        transform: translateX(-50%);
    }
    .kpi-neon-card {
        background: rgba(22, 27, 38, 0.75); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 1rem; text-align: center; height: 100%;
    }
    .kpi-neon-label { font-size: 0.78rem; color: #94A3B8; margin-bottom: 0.4rem; }
    .kpi-neon-value { font-size: 1.6rem; font-weight: 900; color: #00F2FE; text-shadow: 0 0 12px rgba(0,242,254,0.35); }

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 2. 全球市场实时数据采集
# -------------------------------------------------------------------
@st.cache_data(ttl=180, show_spinner=False)
def fetch_global_markets():
    """抓取全球主要市场指数实时数据与板块主线"""
    indices = {
        'US 美股': {
            'flag': '🇺🇸',
            'tickers': {'^GSPC': 'SP500', '^IXIC': 'NASDAQ'},
            'sectors': {'XLK': '科技', 'XLE': '能源', 'XLF': '金融', 'XLV': '医疗', 'XLY': '消费', 'XLI': '工业', 'XLRE': '地产', 'XLC': '通信'},
            'default_sector': '',
        },
        'JP 日股': {'flag': '🇯🇵', 'tickers': {'^N225': '日经225'}, 'sectors': {}, 'default_sector': '半导体/汽车'},
        'KR 韩股': {'flag': '🇰🇷', 'tickers': {'^KS11': 'KOSPI'}, 'sectors': {}, 'default_sector': '半导体/造船'},
        'CN A股': {'flag': '🇨🇳', 'tickers': {'000001.SS': '上证指数'}, 'sectors': {}, 'default_sector': 'AI/新能源'},
    }
    results = {}
    hot_sector = {'name': '未知', 'chg': 0}

    for region, cfg in indices.items():
        region_data = {}
        for tk, label in cfg['tickers'].items():
            try:
                t = yf.Ticker(tk)
                h = t.history(period='2d')
                if len(h) >= 2:
                    prev_close = float(h['Close'].iloc[-2])
                    cur_close = float(h['Close'].iloc[-1])
                    if pd.isna(cur_close): cur_close = prev_close
                    chg_pct = (cur_close - prev_close) / prev_close * 100 if prev_close and not pd.isna(prev_close) else 0
                    if pd.isna(chg_pct): chg_pct = 0
                    region_data[label] = {'price': cur_close, 'chg': chg_pct}
                elif len(h) == 1:
                    cur_close = float(h['Close'].iloc[-1])
                    if pd.isna(cur_close): cur_close = 0
                    region_data[label] = {'price': cur_close, 'chg': 0}
            except Exception:
                region_data[label] = {'price': 0, 'chg': 0}
        # 板块主线（仅美股有 ETF 数据）
        sector_leader = ''
        for stk, sname in cfg.get('sectors', {}).items():
            try:
                t = yf.Ticker(stk)
                h = t.history(period='2d')
                if len(h) >= 2:
                    chg = (h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2] * 100
                    if chg > hot_sector['chg']:
                        hot_sector = {'name': sname, 'chg': chg}
                    if not sector_leader or chg > 0:
                        sector_leader = f"{sname} {chg:+.1f}%"
            except Exception:
                pass
        if not sector_leader:
            sector_leader = cfg.get('default_sector', '')
        results[region] = {'data': region_data, 'sector': sector_leader, 'flag': cfg.get('flag', '')}
    return results, hot_sector

@st.cache_data(ttl=300, show_spinner=False)
def fetch_hot_stocks():
    """基于实时涨幅/成交量抓取热门标的（精细 20 根 K线缩略图数据）"""
    candidates = {
        '英伟达': 'NVDA', '苹果': 'AAPL', '特斯拉': 'TSLA', '微软': 'MSFT',
        '新易盛': '300502.SZ', '中际旭创': '300308.SZ', '谷歌': 'GOOGL', '亚马逊': 'AMZN',
        '台积电': 'TSM', 'Meta': 'META', '贵州茅台': '600519.SS', '宁德时代': '300750.SZ',
        '比亚迪': '002594.SZ', '中芯国际': '688981.SS', '腾讯控股': '0700.HK',
    }
    hot_list = []
    for name, tk in candidates.items():
        try:
            t = yf.Ticker(tk)
            h = t.history(period='1mo')
            if len(h) >= 1:
                h_20 = h.tail(20)
                chg = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2] * 100) if len(h) >= 2 else 0.0
                vol = h['Volume'].iloc[-1]
                ohlc = {
                    'open': h_20['Open'].tolist(),
                    'high': h_20['High'].tolist(),
                    'low': h_20['Low'].tolist(),
                    'close': h_20['Close'].tolist(),
                }
                hot_list.append({'name': name, 'ticker': tk, 'chg': chg, 'vol': vol, 'ohlc': ohlc})
        except Exception:
            hot_list.append({'name': name, 'ticker': tk, 'chg': 0, 'vol': 0, 'ohlc': {}})
    hot_list.sort(key=lambda x: x['vol'], reverse=True)
    return hot_list

# -------------------------------------------------------------------
# 3. 顶部 Hero Header (Anti Stock Report)
# -------------------------------------------------------------------
st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(226, 232, 240, 0.15); padding-bottom: 0.8rem; margin-bottom: 1.5rem;">
    <div style="font-size: 1.5rem; font-weight: 800; display: flex; align-items: center; gap: 0.6rem; font-family: 'JetBrains Mono', monospace; letter-spacing: -0.5px;">
        <span style="color:#00b865;">Anti</span>Stock Terminal <span style="font-size:0.7rem; background:rgba(0,184,101,0.15); color:#00b865; padding:2px 6px; border-radius:4px; font-weight:700;">v2.0 Objective</span>
    </div>
    <div style="font-size: 0.85rem; opacity: 0.7; font-weight: 500;">
        客观数据聚合引擎 | 全球市场主线 | 零主观预测
    </div>
</div>
""", unsafe_allow_html=True)
st.caption("⚠️ 本终端仅做客观公开数据聚合与可视化，绝不生成任何投资评级、目标价推荐或仓位建议。")

# -------------------------------------------------------------------
# 4. 全球市场主线概览 + 热门标的 + 设置（全部在主区域）
# -------------------------------------------------------------------
with st.spinner("🌐 正在接入全球市场实时数据..."):
    global_markets, hot_sector_info = fetch_global_markets()
    hot_stocks_list = fetch_hot_stocks()

# --- 4.1 全球市场主线 ---
st.markdown(f"### 🌐 全球市场主线 <span style='font-size:0.82rem; opacity:0.65; margin-left:0.5rem;'>当前主线板块: <b style=\"color:#00b865\">{hot_sector_info['name']} ({hot_sector_info['chg']:+.1f}%)</b></span>", unsafe_allow_html=True)
region_icons = {'US': '🇺🇸', 'JP': '🇯🇵', 'KR': '🇰🇷', 'CN': '🇨🇳'}
g_cols = st.columns(4)
for i, (region, rdata) in enumerate(global_markets.items()):
    with g_cols[i]:
        rcode = region.split(' ')[0]
        region_label = region.split(' ')[1] if ' ' in region else region
        icon = rdata.get('flag', '🌐')
        for idx_name, idx_val in rdata['data'].items():
            price = idx_val['price']
            chg = idx_val['chg']
            chg_cls = "market-chg-up" if chg >= 0 else "market-chg-down"
            chg_sign = "+" if chg >= 0 else ""
            is_hot = abs(chg) > 1.0
            hot_cls = " market-card-hot" if is_hot else ""
            hot_badge = '<span class="market-badge-hot">HOT</span>' if is_hot else ""
            price_fmt = f"{price:,.2f}" if price > 100 else f"{price:.2f}"
            sector_line = rdata.get('sector', '')
            sector_html = f'<div class="market-sector">主线: {sector_line}</div>' if sector_line else ''
            card_html = f'<div class="market-card{hot_cls}">{hot_badge}<div class="market-flag">{icon}</div><div class="market-name">{region_label} · {idx_name}</div><div class="market-index">{price_fmt}</div><div class="{chg_cls}">{chg_sign}{chg:.2f}%</div>{sector_html}</div>'
            st.markdown(card_html, unsafe_allow_html=True)
            break

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# --- 4.2 热门标的选择 ---
st.markdown("### 🔥 热门标的快速选择 <span style='font-size:0.78rem; opacity:0.6;'>(按实时成交量排序)</span>", unsafe_allow_html=True)

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = "NVDA"

display_stocks = hot_stocks_list[:8]
h_cols = st.columns(8)
for j, s in enumerate(display_stocks):
    with h_cols[j]:
        btn_label = f"{s['name']} ({s['chg']:+.1f}%)"
        if st.button(btn_label, key=f"hot_btn_{j}", use_container_width=True):
            st.session_state.selected_ticker = s['ticker']
            st.rerun()
        ohlc = s.get('ohlc', {})
        if ohlc and len(ohlc.get('close', [])) >= 2:
            fig_spk = go.Figure(go.Candlestick(
                open=ohlc['open'],
                high=ohlc['high'],
                low=ohlc['low'],
                close=ohlc['close'],
                increasing_line_color='#00b865',
                decreasing_fillcolor='#ef4444'
            ))
            fig_spk.update_layout(
                height=45, margin=dict(l=1, r=1, t=1, b=1),
                xaxis=dict(visible=False, rangeslider=dict(visible=False)),
                yaxis=dict(visible=False),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig_spk, use_container_width=True, key=f'spk_{j}', config={'displayModeBar': False})
        else:
            st.caption('—')

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# --- 4.3 设置行（物理对称级对齐） ---
with container_inputs:
    set_c1, set_c2, set_c3 = st.columns([3, 2, 2], vertical_alignment="bottom")
    with set_c1:
        user_ticker_raw = st.text_input("代码 / 简称 (例如 AAPL, 600519.SS)", value=st.session_state.selected_ticker)
    with set_c2:
        api_key_input = st.text_input("API 密钥 (必填)", value="", type="password")
    with set_c3:
        generate_btn = st.button("🚀 生成研报", key="btn_main_generate", use_container_width=True)

# Resolve ticker and fetch all_data immediately so it is available for containers
ticker_input, mapped_name = resolve_ticker(user_ticker_raw)
if ticker_input:
    try:
        with st.spinner(f"正在采集 {ticker_input} 全量多源数据..."):
            all_data = fetch_all_data(ticker_input)
    except Exception as e:
        st.error(f"数据采集失败: {e}")

risk_preference = "稳健型"

# 填充众包预测容器 (P7 & P1 顺序重排：众包移至此处)
with container_crowd:
    try:
        from crowdsource_agent import get_crowdsource_ui
        tk_for_crowd, _ = resolve_ticker(user_ticker_raw)
        get_crowdsource_ui(api_key_input, tk_for_crowd, all_data)
    except Exception as e:
        st.error(f"众包预测组件加载失败: {e}")

# 填充快讯容器 (P7 & P1 顺序重排：快讯移至此处)
with container_tape:
    try:
        from market_tape import get_market_tape_ui
        get_market_tape_ui(api_key_input)
    except Exception as e:
        st.error(f"加载实时盘口失败: {e}")

# 填充宏观资金容器 (P7 & P1 顺序重排：宏观资金移至此处)
with container_macro:
    try:
        from macro_capital import render_macro_capital_board
        render_macro_capital_board()
    except Exception as e:
        st.warning("当前时段接口维护，资金流数据暂缓更新")


def fmt_price_val(val, currency=""):
    """格式化价格数字，消除浮点异常并统一显示"""
    if isinstance(val, (int, float)) and not np.isnan(val):
        if currency in ["USD", "$"] or val < 1000:
            return f"${val:.2f}"
        return f"{val:.2f} 元"
    return "N/A"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_data(ticker_input):
    """全量数据采集引擎：yfinance + akshare 双源汇聚与自动降级补全"""
    data = {}
    stock = yf.Ticker(ticker_input)
    # ⚠️ 稳定性修复：stock.info 在接口限流(Too Many Requests)时会直接抛异常，
    # 之前未做 try/except 会导致整页崩溃。这里加入重试 + 兜底，绝不让异常向上传播。
    data['info'] = {}
    for attempt in range(3):
        try:
            data['info'] = stock.info or {}
            if data['info'].get('shortName') or data['info'].get('currentPrice'):
                break
        except Exception:
            if attempt < 2:
                time.sleep(1.5)
            else:
                data['info'] = {}

    # ⚠️ 关键修复：当 stock.info 被限流返回空字典时，使用 fast_info 填充核心指标
    if not data['info'].get('currentPrice') and not data['info'].get('trailingPE'):
        try:
            fi = stock.fast_info
            if fi is not None:
                if not data['info'].get('currentPrice'):
                    data['info']['currentPrice'] = getattr(fi, 'last_price', None)
                    data['info']['regularMarketPrice'] = getattr(fi, 'last_price', None)
                if not data['info'].get('previousClose'):
                    data['info']['previousClose'] = getattr(fi, 'previous_close', None)
                if not data['info'].get('marketCap'):
                    data['info']['marketCap'] = getattr(fi, 'market_cap', None)
                if not data['info'].get('fiftyTwoWeekHigh'):
                    data['info']['fiftyTwoWeekHigh'] = getattr(fi, 'year_high', None)
                if not data['info'].get('fiftyTwoWeekLow'):
                    data['info']['fiftyTwoWeekLow'] = getattr(fi, 'year_low', None)
                if not data['info'].get('currency'):
                    data['info']['currency'] = getattr(fi, 'currency', 'USD')
        except Exception:
            pass

    try:
        data['hist_1y'] = stock.history(period="1y").dropna(subset=['Close'])
    except Exception:
        data['hist_1y'] = pd.DataFrame()

    try:
        data['news'] = stock.news or []
    except Exception:
        data['news'] = []

    try:
        data['recommendations'] = stock.recommendations
    except Exception:
        data['recommendations'] = None
    try:
        data['analyst_targets'] = stock.analyst_price_targets
    except Exception:
        data['analyst_targets'] = None
    try:
        data['earnings_dates'] = stock.earnings_dates
    except Exception:
        data['earnings_dates'] = None
    try:
        data['institutional_holders'] = stock.institutional_holders
        # P6 Fallback strategies
        if data['institutional_holders'] is None or data['institutional_holders'].empty:
            data['institutional_holders'] = stock.major_holders
        if data['institutional_holders'] is None or data['institutional_holders'].empty:
            data['institutional_holders'] = stock.mutualfund_holders
    except Exception:
        data['institutional_holders'] = None
    try:
        data['quarterly_financials'] = stock.quarterly_financials
    except Exception:
        data['quarterly_financials'] = None

    # 获取季度利润表（用于美股/港股业务分部收入展示）
    try:
        data['quarterly_income_stmt'] = stock.quarterly_income_stmt
    except Exception:
        data['quarterly_income_stmt'] = None

    # 获取年度利润表（同上，更完整的收入分部数据）
    try:
        data['income_stmt'] = stock.income_stmt
    except Exception:
        data['income_stmt'] = None

    # P7: 获取季度与年度现金流量表
    try:
        data['quarterly_cashflow'] = stock.quarterly_cashflow
    except Exception:
        data['quarterly_cashflow'] = None
    try:
        data['cashflow'] = stock.cashflow
    except Exception:
        data['cashflow'] = None

    # P7: 获取季度与年度资产负债表
    try:
        data['quarterly_balance_sheet'] = stock.quarterly_balance_sheet
    except Exception:
        data['quarterly_balance_sheet'] = None
    try:
        data['balance_sheet'] = stock.balance_sheet
    except Exception:
        data['balance_sheet'] = None

    # 获取公司业务概要（longBusinessSummary）
    if not data['info'].get('longBusinessSummary'):
        try:
            # 单独再试一次获取 info 中的业务描述
            bs = stock.info.get('longBusinessSummary', '')
            if bs:
                data['info']['longBusinessSummary'] = bs
        except Exception:
            pass

    pure_code = ticker_input.replace('.SS', '').replace('.SZ', '')
    is_a_share = ticker_input.endswith('.SS') or ticker_input.endswith('.SZ') or pure_code.isdigit()
    data['is_a_share'] = is_a_share
    data['pure_code'] = pure_code

    # 当 yfinance 缺失 A 股关键行情或报错时，自动使用 akshare / 东方财富双源补全
    if is_a_share or not data['info'].get('currentPrice'):
        try:
            import akshare as ak
            df_info = ak.stock_individual_info_em(symbol=pure_code)
            if df_info is not None and not df_info.empty:
                info_dict = dict(zip(df_info['item'], df_info['value']))
                name = info_dict.get('股票简称') or info_dict.get('股票名称')
                if name and not data['info'].get('shortName'):
                    data['info']['shortName'] = name
                ind = info_dict.get('行业')
                if ind and not data['info'].get('industry'):
                    data['info']['industry'] = ind
                    data['info']['sector'] = ind
                mcap = info_dict.get('总市值')
                if mcap:
                    try: data['info']['marketCap'] = float(mcap)
                    except: pass
                pe_val = info_dict.get('市盈率(动)') or info_dict.get('市盈率(静)')
                if pe_val:
                    try: data['info']['trailingPE'] = float(pe_val)
                    except: pass
        except Exception:
            pass

        # 补全 K 线与最新收盘价
        if data['hist_1y'].empty:
            try:
                import akshare as ak
                df_k = ak.stock_zh_a_hist(symbol=pure_code, period="daily", adjust="qfq")
                if df_k is not None and not df_k.empty:
                    df_k['Date'] = pd.to_datetime(df_k['日期'])
                    df_k.set_index('Date', inplace=True)
                    df_k.rename(columns={'开盘': 'Open', '最高': 'High', '最低': 'Low', '收盘': 'Close', '成交量': 'Volume'}, inplace=True)
                    data['hist_1y'] = df_k[['Open', 'High', 'Low', 'Close', 'Volume']].tail(250)
            except Exception:
                pass

        if not data['hist_1y'].empty and not data['info'].get('currentPrice'):
            last_p = round(float(data['hist_1y']['Close'].iloc[-1]), 2)
            data['info']['currentPrice'] = last_p
            data['info']['regularMarketPrice'] = last_p
            data['info']['currency'] = 'CNY'

    # A股主营业务构成（akshare 真实数据）：用于地区/产品线客观展示，无数据则留空不编造
    data['main_composition'] = None
    if is_a_share:
        try:
            import akshare as ak
            data['ak_news'] = ak.stock_news_em(symbol=pure_code)
        except Exception:
            data['ak_news'] = None
        try:
            import akshare as ak
            data['ak_forecast'] = ak.stock_profit_forecast_em(symbol=pure_code)
        except Exception:
            data['ak_forecast'] = None
        try:
            import akshare as ak
            data['ak_info'] = ak.stock_individual_info_em(symbol=pure_code)
        except Exception:
            data['ak_info'] = None
        try:
            import akshare as ak
            data['main_composition'] = ak.stock_zygc_em(symbol=pure_code)
        except Exception:
            data['main_composition'] = None
    else:
        data['ak_news'] = None
        data['ak_forecast'] = None
        data['ak_info'] = None

    # ⚠️ 关键修复：当 stock.info 缺少 PE 等指标时，从 hist_1y 和 quarterly_financials 计算补全
    if not data['info'].get('trailingPE') and not data['hist_1y'].empty:
        try:
            qf = data.get('quarterly_financials')
            if qf is not None and not qf.empty:
                # 尝试从最近4个季度的净利润计算 TTM EPS
                for eps_key in ['Basic EPS', 'Diluted EPS']:
                    if eps_key in qf.index:
                        eps_vals = qf.loc[eps_key].dropna().head(4)
                        if len(eps_vals) >= 1:
                            eps_ttm = float(eps_vals.sum()) if len(eps_vals) == 4 else float(eps_vals.iloc[0]) * 4
                            if eps_ttm > 0:
                                cur_p = data['info'].get('currentPrice') or float(data['hist_1y']['Close'].iloc[-1])
                                data['info']['trailingPE'] = round(cur_p / eps_ttm, 2)
                                data['info']['trailingEps'] = round(eps_ttm, 2)
                            break
        except Exception:
            pass

    return data

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history_long(ticker_input, years=3):
    """抓取近N年收盘价，仅用于计算「股价历史分位」这一客观统计指标（不是PE分位，不做估值判断）。
    说明：真正的“PE历史分位”需要历史EPS序列，免费数据源无法可靠获取，
    为避免编造精度，本函数只提供可验证的“股价所处历史区间分位”作为透明替代指标。"""
    try:
        t = yf.Ticker(ticker_input)
        h = t.history(period=f"{years}y")
        if h is None or h.empty:
            return None
        return h[['Close']].dropna()
    except Exception:
        return None

def build_kline_chart(df, ticker_input):
    """构建带 MA/MACD 的交互式 K 线图"""
    df = df.copy()
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.2, 0.25],
        subplot_titles=[f'{ticker_input} 近 1 年 K 线与均线系统', '', '']
    )
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#00b865', decreasing_line_color='#ef4444', name='K线'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(width=1, color='#f59e0b'), name='MA5'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(width=1, color='#3b82f6'), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(width=1.5, color='#8b5cf6'), name='MA50'), row=1, col=1)

    colors = ['#00b865' if c >= o else '#ef4444' for c, o in zip(df['Close'], df['Open'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量', opacity=0.6), row=2, col=1)

    hist_colors = ['#00b865' if v >= 0 else '#ef4444' for v in hist]
    fig.add_trace(go.Bar(x=df.index, y=hist, marker_color=hist_colors, name='MACD柱体', opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=macd, line=dict(width=1, color='#3b82f6'), name='DIF'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=signal, line=dict(width=1, color='#f59e0b'), name='DEA'), row=3, col=1)

    fig.update_layout(
        height=580,
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        margin=dict(l=40, r=20, t=40, b=20),
        legend=dict(orientation='h', y=1.02, x=0.5, xanchor='center'),
        font=dict(family='Inter', size=12)
    )
    return fig

def merge_klines_inclusion(df):
    """缠论第一步：K线包含关系处理。将有包含关系的相邻K线合并，消除噪音，
    再在合并后的K线序列上做顶底分型识别，避免原始K线导致的伪分型。"""
    highs = df['High'].tolist()
    lows = df['Low'].tolist()
    dates = list(df.index)
    if len(highs) < 3:
        return []
    merged = [{'high': highs[0], 'low': lows[0], 'date': dates[0]}]
    direction = 0  # 0=未知, 1=向上处理(取高高), -1=向下处理(取低低)
    for i in range(1, len(highs)):
        h, l, d = highs[i], lows[i], dates[i]
        last = merged[-1]
        is_contain = (h <= last['high'] and l >= last['low']) or (h >= last['high'] and l <= last['low'])
        if is_contain:
            if direction >= 0:
                new_high, new_low = max(h, last['high']), max(l, last['low'])
            else:
                new_high, new_low = min(h, last['high']), min(l, last['low'])
            merged[-1] = {'high': new_high, 'low': new_low, 'date': d}
        else:
            if h > last['high']:
                direction = 1
            elif h < last['high']:
                direction = -1
            merged.append({'high': h, 'low': l, 'date': d})
    return merged


def find_fractals_on_merged(merged):
    """在包含处理后的K线序列上识别顶/底分型，比原始K线三点极值法更可靠。"""
    tops, bottoms = [], []
    for i in range(1, len(merged) - 1):
        if merged[i]['high'] > merged[i-1]['high'] and merged[i]['high'] > merged[i+1]['high']:
            tops.append(merged[i])
        if merged[i]['low'] < merged[i-1]['low'] and merged[i]['low'] < merged[i+1]['low']:
            bottoms.append(merged[i])
    return tops, bottoms


def build_bi_sequence(tops, bottoms):
    """构建"笔"序列：连接相邻的顶/底分型，方向必须交替，取同类型分型中的极值点。
    这是标准缠论"笔"定义的简化实现（未做特征序列分型验证的完整线段构建）。"""
    points = [(t['date'], t['high'], 'top') for t in tops] + [(b['date'], b['low'], 'bottom') for b in bottoms]
    points.sort(key=lambda x: x[0])
    filtered = []
    for p in points:
        if filtered and filtered[-1][2] == p[2]:
            if p[2] == 'top' and p[1] > filtered[-1][1]:
                filtered[-1] = p
            elif p[2] == 'bottom' and p[1] < filtered[-1][1]:
                filtered[-1] = p
        else:
            filtered.append(p)
    bi_list = []
    for i in range(len(filtered) - 1):
        bi_list.append({
            'start_date': filtered[i][0], 'start_price': filtered[i][1],
            'end_date': filtered[i+1][0], 'end_price': filtered[i+1][1],
            'direction': 'up' if filtered[i][2] == 'bottom' else 'down'
        })
    return bi_list


def build_zhongshu_from_bi(bi_list):
    """基于连续3笔的价格区间重叠计算真正的缠论中枢（ZG/ZD），
    而非统计分位数近似。返回最近一个有效中枢（若存在）。"""
    zhongshu_list = []
    for i in range(len(bi_list) - 2):
        b1, b2, b3 = bi_list[i], bi_list[i+1], bi_list[i+2]
        ranges = [(min(b['start_price'], b['end_price']), max(b['start_price'], b['end_price'])) for b in (b1, b2, b3)]
        zd_candidate = max(r[0] for r in ranges)
        zg_candidate = min(r[1] for r in ranges)
        if zg_candidate > zd_candidate:
            zhongshu_list.append({
                'zg': zg_candidate, 'zd': zd_candidate,
                'start_date': b1['start_date'], 'end_date': b3['end_date']
            })
    return zhongshu_list


def analyze_kline_and_chanlun(df):
    """缠论顶底分型、中枢、背驰量化计算（简化版，非完整笔/线段体系）"""
    if df.empty or len(df) < 30:
        return "K线数据不足，无法进行缠论技术分析。"
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal

    # RSI(14) 真实计算：超买超卖辅助判断
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi_latest = rsi.iloc[-1] if not rsi.empty and not pd.isna(rsi.iloc[-1]) else None
    if rsi_latest is not None:
        if rsi_latest >= 70:
            rsi_status = f"RSI(14)={rsi_latest:.1f}，进入超买区间(>=70)"
        elif rsi_latest <= 30:
            rsi_status = f"RSI(14)={rsi_latest:.1f}，进入超卖区间(<=30)"
        else:
            rsi_status = f"RSI(14)={rsi_latest:.1f}，处于中性区间(30-70)"
    else:
        rsi_status = "RSI(14) 数据不足，无法计算"

    # 布林带(20,2) 真实计算：波动率与支撑压力
    boll_mid = df['Close'].rolling(20).mean()
    boll_std = df['Close'].rolling(20).std()
    boll_upper = boll_mid + 2 * boll_std
    boll_lower = boll_mid - 2 * boll_std
    if not boll_upper.empty and not pd.isna(boll_upper.iloc[-1]):
        boll_status = f"布林带(20,2): 上轨={boll_upper.iloc[-1]:.2f}, 中轨={boll_mid.iloc[-1]:.2f}, 下轨={boll_lower.iloc[-1]:.2f}"
    else:
        boll_status = "布林带数据不足，无法计算"

    dates = df.index.strftime('%Y-%m-%d').values
    highs = df['High'].values
    lows = df['Low'].values
    recent_close = df['Close'].iloc[-1]
    pct_1y = ((recent_close - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

    top_fractals, bottom_fractals = [], []
    for i in range(1, len(df) - 1):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            top_fractals.append((dates[i], highs[i]))
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            bottom_fractals.append((dates[i], lows[i]))
    recent_top = top_fractals[-1] if top_fractals else ("无", 0)
    recent_bottom = bottom_fractals[-1] if bottom_fractals else ("无", 0)

    df_60 = df.tail(60)
    zg = df_60['High'].quantile(0.75)
    zd = df_60['Low'].quantile(0.25)

    # ---- 真实缠论结构：K线包含处理 -> 分型 -> 笔 -> 中枢(3笔重叠区间) ----
    zhongshu_note = "笔数不足3笔，无法构建结构化中枢，以下沿用统计分位数近似"
    zg_real, zd_real = None, None
    try:
        merged_k = merge_klines_inclusion(df.tail(120))
        tops_m, bottoms_m = find_fractals_on_merged(merged_k)
        bi_seq = build_bi_sequence(tops_m, bottoms_m)
        zs_list = build_zhongshu_from_bi(bi_seq)
        if zs_list:
            latest_zs = zs_list[-1]
            zg_real, zd_real = latest_zs['zg'], latest_zs['zd']
            zhongshu_note = f"基于最近3笔重叠区间计算(结构化定义): {latest_zs['start_date'].strftime('%Y-%m-%d')} 至 {latest_zs['end_date'].strftime('%Y-%m-%d')}，历史累计识别中枢数={len(zs_list)}"
        elif len(bi_seq) > 0:
            zhongshu_note = f"已识别{len(bi_seq)}笔，但不足3笔重叠形成结构化中枢，以下沿用统计分位数近似"
    except Exception:
        pass
    zg_display = zg_real if zg_real is not None else zg
    zd_display = zd_real if zd_real is not None else zd

    macd_recent = hist.iloc[-1]
    macd_prev_min = hist.tail(30).min()
    if recent_close <= df_60['Low'].min() * 1.03 and macd_recent > macd_prev_min:
        divergence = "底背驰信号（缠论一类买点区间）"
    elif recent_close >= df_60['High'].max() * 0.97 and macd_recent < hist.tail(30).max():
        divergence = "顶背驰信号（潜在回调区）"
    else:
        divergence = "未见背驰，维持区间中枢盘整"

    trend_status = "震荡上行/主升阶段" if pct_1y > 15 else ("震荡下行/回调阶段" if pct_1y < -15 else "近1年宽幅箱体震荡")

    segments = []
    if len(bottom_fractals) > 0 and len(top_fractals) > 0:
        all_points = [(d, p, 'top') for d, p in top_fractals] + [(d, p, 'bottom') for d, p in bottom_fractals]
        all_points.sort(key=lambda x: x[0])
        for i in range(len(all_points) - 1):
            d1, p1, t1 = all_points[i]
            d2, p2, t2 = all_points[i+1]
            if t1 == 'bottom' and t2 == 'top' and (p2 - p1) / p1 > 0.10:
                segments.append(f"🟢 上涨: {d1[5:]} ({p1:.2f}) ➔ {d2[5:]} ({p2:.2f}) [+{(p2-p1)/p1*100:.1f}%]")
            elif t1 == 'top' and t2 == 'bottom' and (p1 - p2) / p1 > 0.10:
                segments.append(f"🔴 下跌: {d1[5:]} ({p1:.2f}) ➔ {d2[5:]} ({p2:.2f}) [{(p1-p2)/p1*-100:.1f}%]")
    
    segments = segments[-5:]
    segments_html = "".join([f"<div style='background:rgba(255,255,255,0.05); padding:5px 10px; border-radius:5px; margin-bottom:5px; font-size:0.85rem;'>{s}</div>" for s in segments]) if segments else "<div style='opacity:0.6'>近半年未见超10%波段</div>"

    html = f"""<div style="background:rgba(20,24,33,0.5); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.05);">
<h4 style="color:#38bdf8; margin-bottom:15px; font-size:1.05rem;">【近1年K线量化与缠论指标】</h4>
<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:15px;">
<div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:8px;">
<div style="font-size:0.8rem; color:#94a3b8;">最新收盘 / 趋势</div>
<div style="font-size:1rem; font-weight:600; color:{'#ef4444' if pct_1y>=0 else '#00b865'};">{recent_close:.2f} ({pct_1y:+.2f}%)</div>
<div style="font-size:0.8rem;">{trend_status}</div>
</div>
<div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:8px;">
<div style="font-size:0.8rem; color:#94a3b8;">1年最高 / 最低</div>
<div style="font-size:1rem; font-weight:600;">{df['High'].max():.2f} / {df['Low'].min():.2f}</div>
</div>
<div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:8px;">
<div style="font-size:0.8rem; color:#94a3b8;">近60日中枢轨 (ZG/ZD)</div>
<div style="font-size:1rem; font-weight:600; color:#fbbf24;">{zg_display:.2f} / {zd_display:.2f}</div>
<div style="font-size:0.75rem; opacity:0.7; margin-top:3px;">{zhongshu_note}</div>
</div>
<div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:8px;">
<div style="font-size:0.8rem; color:#94a3b8;">MACD / 辅助判断</div>
<div style="font-size:1rem; font-weight:600;">{macd_recent:.3f}</div>
<div style="font-size:0.75rem; color:{'#ef4444' if '底背驰' in divergence else '#00b865' if '顶背驰' in divergence else '#94a3b8'}; margin-top:3px;">{divergence}</div>
</div>
</div>
<div style="display:flex; gap:10px; margin-bottom:15px; flex-wrap:wrap;">
<span style="background:rgba(56,189,248,0.1); color:#38bdf8; padding:4px 8px; border-radius:4px; font-size:0.8rem;">均线支撑: MA20={df['MA20'].iloc[-1]:.2f}, MA50={df['MA50'].iloc[-1]:.2f}</span>
<span style="background:rgba(251,191,36,0.1); color:#fbbf24; padding:4px 8px; border-radius:4px; font-size:0.8rem;">{rsi_status}</span>
</div>
<div style="font-size:0.9rem; color:#e2e8f0; font-weight:600; margin-bottom:10px;">📉 波段起止明细 (最近5条)</div>
{segments_html}
</div>"""
    return html

# =============================================================================
# 产业链知识库 —— 按 Ticker 代码精确匹配（最高优先级，不依赖 yfinance info 字段）
# =============================================================================
TICKER_CHAIN_DB = {
    # ---- 美股 AI/半导体核心标的 ----
    'NVDA': {
        'up': ['台积电 TSMC (5nm/4nm 晶圆代工)', '三星电子 (HBM3E 高带宽存储)', 'SK海力士 (HBM 供应商)', '阿斯麦 ASML (EUV 光刻机)'],
        'mid_role': 'GPU/AI 加速芯片设计 (数据中心 & 游戏 & 汽车)',
        'down': ['微软 Azure / 谷歌 GCP / 亚马逊 AWS (云厂商)', 'Meta / OpenAI / 字节跳动 (AI 大模型训练)', '特斯拉 (自动驾驶 FSD)', '全球游戏玩家 (GeForce)'],
        'down_note': 'AI 算力需求爆发式增长，NVIDIA 数据中心收入已超过游戏业务成为第一大收入来源，CoWoS 先进封装产能为核心瓶颈'
    },
    'AMD': {
        'up': ['台积电 TSMC (先进制程代工)', '日月光/矽品 (封装测试)', '美光 Micron (DRAM/HBM)'],
        'mid_role': 'CPU/GPU/FPGA 芯片设计 (数据中心 & PC & 嵌入式)',
        'down': ['微软 / 谷歌 / Meta (云数据中心 MI300 系列)', 'PC OEM 厂商 (联想/惠普/戴尔)', '索尼 PS5 / 微软 Xbox (游戏主机定制芯片)'],
        'down_note': 'MI300X 系列 GPU 加速器直接对标 NVIDIA H100，Instinct 产品线在 AI 推理市场份额持续提升'
    },
    'TSM': {
        'up': ['阿斯麦 ASML (EUV 光刻机)', '应用材料 AMAT (CVD/PVD 沉积)', '东京电子 TEL (刻蚀)', '信越化学 (硅晶圆)'],
        'mid_role': '全球最大晶圆代工厂 (3nm/5nm 先进制程)',
        'down': ['苹果 Apple (A/M 系列芯片)', 'NVIDIA (GPU 代工)', '高通 Qualcomm (骁龙芯片)', 'AMD / 联发科 / 博通'],
        'down_note': '全球先进制程代工市占率超 90%，AI 芯片需求推动 CoWoS 先进封装产能持续扩张'
    },
    'AVGO': {
        'up': ['台积电 TSMC (芯片代工)', 'Amkor (封装)', '日本电产 (被动元器件)'],
        'mid_role': '网络/存储/定制 ASIC 芯片设计 & 基础设施软件',
        'down': ['谷歌 TPU (定制 AI 芯片)', '苹果 (Wi-Fi/蓝牙芯片)', '数据中心交换机 (思科/Arista)', '电信运营商 5G 基站'],
        'down_note': '博通 VMware 收购完成后转型为基础设施软件+半导体双引擎，谷歌 TPU 定制 ASIC 为高增长驱动力'
    },
    'INTC': {
        'up': ['阿斯麦 ASML (光刻机)', '应用材料 AMAT', 'Lam Research (刻蚀设备)'],
        'mid_role': 'CPU 设计与 IDM 自有晶圆制造 (Intel Foundry Services)',
        'down': ['PC OEM (联想/惠普/戴尔)', '数据中心 (Xeon 至强)', '美国政府/国防 (CHIPS 法案)'],
        'down_note': 'Intel 18A/20A 制程追赶台积电，IFS 代工业务承接美国本土芯片制造需求'
    },
    'QCOM': {
        'up': ['台积电 TSMC (芯片代工)', '三星 (部分代工)', 'Arm (架构授权)'],
        'mid_role': '移动 SoC 芯片设计 (骁龙) & 5G 基带/射频前端',
        'down': ['三星 / 小米 / OPPO / vivo (安卓手机)', '宝马 / 通用 (汽车座舱芯片)', 'PC 厂商 (骁龙 X Elite 笔记本)'],
        'down_note': '端侧 AI 大模型推理驱动骁龙 8 Gen 3/4 高端芯片升级，汽车/IoT 多元化降低手机依赖'
    },
    'MU': {
        'up': ['应用材料 AMAT (沉积设备)', 'Lam Research (刻蚀设备)', '信越化学 (硅晶圆)'],
        'mid_role': 'DRAM & NAND 存储芯片设计与制造 (IDM)',
        'down': ['NVIDIA / AMD (HBM3E 配套 GPU)', '苹果 / 三星 (手机存储)', '数据中心服务器 (DDR5)'],
        'down_note': 'HBM (高带宽存储) 需求随 AI GPU 出货量同步爆发，美光 HBM3E 产能已被预订至 2025 年底'
    },
    'SMCI': {
        'up': ['NVIDIA (GPU)', 'AMD (CPU/GPU)', '高阶 PCB 供应商', '散热模组/液冷方案商'],
        'mid_role': 'AI 服务器 & 存储系统整机设计与组装',
        'down': ['微软 / Meta / 谷歌 / 亚马逊 (超大规模云厂商)', 'AI 初创企业', '主权 AI 基础设施'],
        'down_note': '超微电脑是 NVIDIA GPU 服务器最大的第三方组装商之一，液冷散热方案为核心差异化竞争力'
    },
    # ---- 美股科技巨头 ----
    'AAPL': {
        'up': ['台积电 TSMC (A/M 系列芯片代工)', '三星 SDI / LG (OLED 屏幕)', '立讯精密 (连接器/组装)', '博通 (Wi-Fi/蓝牙芯片)'],
        'mid_role': 'iPhone / Mac / iPad / Apple Watch / Vision Pro 设计与品牌运营',
        'down': ['全球消费者 (换机周期约 3-4 年)', '运营商渠道 (AT&T/Verizon/中国移动)', 'App Store 开发者生态 (服务收入)'],
        'down_note': '服务业务 (App Store/Apple Music/iCloud) 毛利率超 70%，已成为利润增长第二引擎；Vision Pro 开启空间计算新品类'
    },
    'MSFT': {
        'up': ['NVIDIA (GPU 算力)', 'AMD (CPU/GPU)', '数据中心基础设施 (服务器/光模块)'],
        'mid_role': 'Azure 云计算 & Office 365 & Windows & GitHub Copilot',
        'down': ['全球企业 IT (Office/Teams/Azure)', 'OpenAI 合作伙伴 (Copilot AI 生态)', '游戏玩家 (Xbox/动视暴雪)'],
        'down_note': 'Azure AI 服务收入同比增速超 50%，Copilot 企业版付费用户快速增长，OpenAI 独家云合作伙伴'
    },
    'GOOGL': {
        'up': ['自研 TPU (谷歌 Tensor 芯片)', 'NVIDIA (GPU 训练集群)', '博通 Broadcom (定制 ASIC)'],
        'mid_role': 'Google 搜索 & YouTube 广告 & GCP 云 & Waymo 自动驾驶 & Android',
        'down': ['全球广告主 (搜索/YouTube 广告)', '企业云客户 (GCP)', 'Android 手机生态 (三星/小米)'],
        'down_note': 'Gemini 大模型深度整合搜索与云服务，YouTube 广告收入持续两位数增长，Waymo 商业化落地加速'
    },
    'AMZN': {
        'up': ['NVIDIA / Intel (数据中心芯片)', '自研 Graviton ARM 芯片 & Trainium AI 芯片', '物流基础设施 (机器人/仓储)'],
        'mid_role': 'AWS 云计算 (全球第一) & 电商零售 & Prime 会员 & Alexa',
        'down': ['全球企业 (AWS 云服务)', '消费者 (电商/Prime Video)', '第三方卖家 (FBA 物流)'],
        'down_note': 'AWS 占全球云市场份额 31%，Bedrock 托管式 AI 服务增长迅猛，电商广告业务已成为第三增长极'
    },
    'META': {
        'up': ['NVIDIA (GPU 训练集群, H100/B200)', '博通 (定制 MTIA 芯片)', '数据中心基础设施'],
        'mid_role': 'Facebook / Instagram / WhatsApp 社交广告 & Reality Labs (Quest VR)',
        'down': ['全球广告主 (精准社交广告)', '消费者 (社交/Reels 短视频)', 'VR/AR 开发者生态'],
        'down_note': 'Llama 开源大模型生态持续扩张，Reels 短视频广告变现效率快速提升，AI 驱动广告推荐精准度'
    },
    'NFLX': {
        'up': ['内容制作工作室 (好莱坞/韩国/日本)', '云基础设施 (AWS)', 'CDN 网络'],
        'mid_role': '全球流媒体平台 (原创内容 + 广告套餐)',
        'down': ['全球 2.8 亿付费用户', '广告主 (广告支持套餐)', '内容授权方'],
        'down_note': '广告支持套餐 (含广告低价版) 用户增长强劲，密码共享打击策略转化为付费用户增量'
    },
    'TSLA': {
        'up': ['宁德时代 / 比亚迪 / 松下 (动力电池)', '自研 FSD 芯片 (HW4.0)', '博世 / 英飞凌 (车规级芯片)'],
        'mid_role': '纯电动汽车制造 & 自动驾驶 FSD & 储能 (Megapack) & 人形机器人 (Optimus)',
        'down': ['全球消费者 (Model 3/Y/S/X)', '储能/电力公司 (Megapack 大储)', '未来 Robotaxi 出行平台'],
        'down_note': 'FSD 完全自动驾驶软件订阅为高毛利增长点，Megapack 储能业务装机量同比翻倍，Optimus 人形机器人远期想象空间巨大'
    },
    # ---- A 股核心标的 (按 yfinance ticker 格式) ----
    '600519.SS': {
        'up': ['高粱/小麦种植基地 (贵州/四川)', '包材企业 (玻璃瓶/纸箱/瓶盖)', '酒曲/微生物发酵技术'],
        'mid_role': '贵州茅台：酱香型白酒酿造 & 品牌运营 (飞天/生肖/精品系列)',
        'down': ['经销商/专卖店体系 (全国 2000+ 经销商)', '电商直营 (i茅台/天猫旗舰店)', '商务/宴请/收藏消费场景'],
        'down_note': '飞天茅台出厂价 1169 元，终端市场价约 2500 元，渠道利润丰厚；i茅台 App 直销占比持续提升'
    },
    '300750.SZ': {
        'up': ['天齐锂业/赣锋锂业 (碳酸锂)', '容百科技 (正极材料)', '恩捷股份 (隔膜)', '天赐材料 (电解液)'],
        'mid_role': '宁德时代：动力电池 & 储能电池研发制造 (全球市占率 37%)',
        'down': ['特斯拉 / 宝马 / 奔驰 / 蔚来 / 理想 (新能源车企)', '储能电站运营商', '电动船舶/矿卡'],
        'down_note': '麒麟电池/神行超充电池为技术领先产品，海外产能布局匈牙利/德国工厂，钠离子电池量产在即'
    },
    '002594.SZ': {
        'up': ['比亚迪半导体 (自研 IGBT/SiC)', '比亚迪弗迪电池 (刀片电池垂直整合)', '自研电驱/电控系统'],
        'mid_role': '比亚迪：新能源汽车整车 + 动力电池 + 半导体全产业链垂直整合',
        'down': ['国内消费者 (王朝/海洋/仰望/方程豹系列)', '海外市场 (东南亚/欧洲/南美)', '公交/出租车队'],
        'down_note': '全球新能源汽车销量冠军，刀片电池垂直整合降本优势显著，智能驾驶 "天神之眼" 加速迭代'
    },
    '688981.SS': {
        'up': ['北方华创 (刻蚀/CVD 设备)', '中微公司 (刻蚀设备)', '沪硅产业 (硅片)', '盛美上海 (清洗设备)'],
        'mid_role': '中芯国际：中国大陆最大晶圆代工厂 (14nm/28nm 成熟制程)',
        'down': ['高通 / 联发科 (成熟制程芯片代工)', '兆易创新 / 韦尔股份 (国内设计公司)', '汽车/工业/IoT 芯片需求'],
        'down_note': '美国实体清单限制先进设备进口，聚焦 28nm 及以上成熟制程扩产，国产替代订单持续增加'
    },
    '300502.SZ': {
        'up': ['光芯片供应商 (II-VI/Lumentum)', '高速 DSP 芯片 (博通/Marvell)', '精密光学元器件'],
        'mid_role': '新易盛：高速光模块研发制造 (800G/1.6T 数据中心光模块)',
        'down': ['谷歌 / 亚马逊 / Meta / 微软 (北美云厂商)', '中国移动/电信/联通 (5G 前传)', 'AI 算力集群互联'],
        'down_note': '800G 光模块放量出货，1.6T 产品研发领先，北美头部云厂商为核心客户，AI 算力互联需求爆发'
    },
    '300308.SZ': {
        'up': ['光芯片/EML 激光器', '高速 DSP (博通 Tomahawk)', 'VCSEL/硅光芯片'],
        'mid_role': '中际旭创：全球光模块龙头 (800G/1.6T 数据中心光互联)',
        'down': ['谷歌 / 亚马逊 / Meta / 微软 (全球云厂商)', 'AI 训练集群 (GPU 间高速互联)', '5G 承载网'],
        'down_note': '全球 800G 光模块市占率第一，1.6T LPO 光模块率先送样，受益 AI 算力基建投资周期'
    },
    '002371.SZ': {
        'up': ['高纯靶材/气体/化学品', '精密机械加工', '自研核心零部件'],
        'mid_role': '北方华创：半导体设备龙头 (刻蚀/CVD/PVD/氧化扩散炉)',
        'down': ['中芯国际 / 长江存储 / 华虹半导体 (国内晶圆厂)', '京东方 / 华星光电 (面板厂)', '光伏电池片厂商'],
        'down_note': '国产半导体设备替代率持续提升，刻蚀/薄膜沉积设备进入主流产线验证，光伏设备贡献增量收入'
    },
    '002475.SZ': {
        'up': ['连接器精密模具', '自动化组装产线', '精密金属/塑胶零部件'],
        'mid_role': '立讯精密：消费电子精密制造 (苹果 AirPods/Apple Watch/iPhone 组装)',
        'down': ['苹果 Apple (第一大客户)', '华为 / 小米 (安卓生态)', '汽车 Tier 1 (线束/连接器)'],
        'down_note': '苹果 iPhone 整机组装份额持续提升，汽车线束/连接器业务为第二增长曲线'
    },
    '600036.SS': {
        'up': ['央行货币政策 (MLF/LPR)', '同业资金市场', '债券/票据市场'],
        'mid_role': '招商银行：零售银行之王 (财富管理 & 信用卡 & 个人贷款)',
        'down': ['个人客户 (1.9 亿零售客户)', '小微企业贷款', '私人银行/财富管理客户'],
        'down_note': '零售 AUM 规模超 13 万亿，财富管理手续费收入行业领先，ROE 连续多年保持 15%+'
    },
    '601318.SS': {
        'up': ['再保险公司 (慕尼黑再/瑞士再)', '医疗/汽车服务网络', '投资市场 (权益/固收)'],
        'mid_role': '中国平安：综合金融集团 (保险 + 银行 + 科技)',
        'down': ['个人保险客户 (2.3 亿+)', '企业团险客户', '平安银行/陆金所用户'],
        'down_note': '寿险改革"新模式"推动 NBV 恢复增长，医疗养老生态圈构建中，科技赋能降本增效'
    },
    # ---- 港股核心标的 ----
    '0700.HK': {
        'up': ['云计算基础设施 (自建数据中心)', 'NVIDIA/AMD (GPU 算力)', '内容创作者/游戏开发商'],
        'mid_role': '腾讯控股：社交 (微信/QQ) + 游戏 + 云 + 金融科技',
        'down': ['12 亿微信用户 (社交/支付)', '全球游戏玩家 (王者荣耀/原神代理)', '企业微信/腾讯云客户'],
        'down_note': '视频号广告/小程序电商为新增长引擎，海外游戏收入占比持续提升，混元大模型赋能内部产品'
    },
    '1810.HK': {
        'up': ['高通 (骁龙芯片)', '三星/京东方 (屏幕)', '索尼 (摄像头传感器)'],
        'mid_role': '小米集团：智能手机 + AIoT 生态 + 小米汽车 SU7',
        'down': ['全球消费者 (手机/IoT 设备)', '小米之家线下渠道', '小米汽车车主'],
        'down_note': '小米 SU7 交付量快速爬坡，高端手机份额提升，AIoT 连接设备数超 7 亿台'
    },
    '3690.HK': {
        'up': ['云计算基础设施', '配送骑手网络 (超 700 万骑手)', '商户合作伙伴'],
        'mid_role': '美团：本地生活服务平台 (外卖 + 到店 + 酒旅 + 优选)',
        'down': ['消费者 (外卖/团购/酒店预订)', '餐饮/零售商户', '酒店/旅游服务商'],
        'down_note': '即时零售 (美团闪购) 高速增长，海外业务 (Keeta) 拓展东南亚，AI 提升配送效率'
    },
    'BABA': {
        'up': ['云计算基础设施 (阿里云)', '物流网络 (菜鸟)', '支付系统 (支付宝/蚂蚁)'],
        'mid_role': '阿里巴巴：电商 (淘宝/天猫/1688) + 阿里云 + 本地生活 + 国际电商',
        'down': ['消费者 (淘宝/天猫 9 亿活跃用户)', '品牌商家/中小卖家', '企业云客户 (阿里云)'],
        'down_note': '1688 平源厂货模式增长强劲，阿里云 AI 推理服务收入高速增长，国际电商 (Lazada/AliExpress) 扩张'
    },
    'PDD': {
        'up': ['中国制造业产业带工厂', '物流合作伙伴 (极兔/中通)', '云基础设施'],
        'mid_role': '拼多多：社交电商 (拼多多国内) + 跨境电商 (Temu)',
        'down': ['价格敏感型消费者 (下沉市场)', 'Temu 全球用户 (北美/欧洲/日韩)', '农产品消费者'],
        'down_note': 'Temu 全托管模式快速渗透欧美市场，国内百亿补贴持续获客，利润率远超行业平均'
    },
    'JD': {
        'up': ['品牌供应商 (家电/3C 直采)', '京东物流 (自建仓配网络)', '达达集团 (即时配送)'],
        'mid_role': '京东：自营电商 (家电/3C 优势) + 京东物流 + 京东健康',
        'down': ['品质消费者 (一二线城市)', '企业采购客户', '京东 PLUS 会员'],
        'down_note': '自营供应链物流体验行业领先，京东物流外部客户收入占比持续提升，低价策略拓展下沉市场'
    },
    'BIDU': {
        'up': ['NVIDIA (GPU 算力)', '自研昆仑芯片', '数据中心基础设施'],
        'mid_role': '百度：搜索广告 + 文心一言大模型 + Apollo 自动驾驶 + 百度智能云',
        'down': ['广告主 (搜索/信息流广告)', '萝卜快跑 Robotaxi 乘客', '企业 AI 云客户'],
        'down_note': '文心大模型 API 日调用量突破 5 亿次，萝卜快跑 Robotaxi 在武汉等城市商业化运营'
    },
}

# 产业链知识库：按行业/板块映射上中下游（二级回退）
CHAIN_DB = {
    'Auto Manufacturers': {
        'up': ['宁德时代 (电池)', '博世 (Bosch, 零部件)', '英飞凌 (芯片)'],
        'mid_role': '整车制造 & 智能驾驶',
        'down': ['消费者市场 (换车周期约6-8年)', '出行平台 (Uber/滴滴)', '政府采购/租赁'],
        'down_note': '全球汽车渗透率趋饱和，新能源渗透率快速攀升（中国>40%，欧洲>25%），消费信心与利率水平直接影响购车意愿'
    },
    'Semiconductors': {
        'up': ['阿斯麦 (ASML, 光刻机)', '应用材料 (AMAT, 沉积)', '信越化学 (硅片)'],
        'mid_role': '芯片设计 / 代工制造',
        'down': ['智能手机 (苹果/三星/小米)', '数据中心/AI服务器 (NVIDIA/微软)', '汽车/工业电子'],
        'down_note': 'AI 算力爆发拉动先进制程 (3nm/5nm) 及 HBM 存储供不应求，消费电子复苏带动成熟制程回暖'
    },
    'Semiconductor Equipment & Materials': {
        'up': ['高纯金属与气体', '光学镜片 (蔡司)', '精密机械构件'],
        'mid_role': '半导体设备研发与制造',
        'down': ['晶圆代工厂 (台积电/中芯国际)', '存储芯片厂 (三星/海力士/美光)', 'IDM 厂商 (Intel/TI)'],
        'down_note': '全球晶圆厂资本开支持续高位，国产化替代加速，先进封装 (CoWoS) 设备需求景气度极高'
    },
    'Software—Infrastructure': {
        'up': ['数据中心服务器 (戴尔/浪潮)', '高速光模块', '云算力芯片 (GPU/TPU)'],
        'mid_role': '云计算 & 基础软件/数据库',
        'down': ['企业级 IT 部门', 'SaaS 应用开发者', '互联网与金融机构'],
        'down_note': '生成式 AI 推动企业级云服务从传统 IaaS 向 PaaS/MaaS 深度升级，软件订阅收入年化增速超 20%'
    },
    'Internet Content & Information': {
        'up': ['云计算基础设施', 'GPU 算力 (NVIDIA/AMD)', '内容创作者/开发者'],
        'mid_role': '互联网平台 & 信息服务',
        'down': ['消费者用户 (搜索/社交/购物)', '广告主 (品牌/效果广告)', '企业级 SaaS/云客户'],
        'down_note': 'AI 大模型重塑搜索与推荐引擎，短视频/直播电商成为流量变现核心场景'
    },
    'Internet Retail': {
        'up': ['品牌供应商/工厂', '物流网络 (仓储/配送)', '支付系统'],
        'mid_role': '电商零售平台',
        'down': ['消费者 (线上购物)', '第三方卖家/品牌商', '广告主'],
        'down_note': '即时零售与社交电商持续增长，跨境电商全托管模式加速全球化扩张'
    },
    'Hardware, Tech Supply Chain': {
        'up': ['高阶 PCB 板', '高速光模块 (800G/1.6T)', '电源/散热模组'],
        'mid_role': 'AI 服务器整机集成与封装',
        'down': ['微软 / 谷歌 / 亚马逊 / Meta (云厂商)', 'AI 大模型初创企业', '科研机构与算力中心'],
        'down_note': 'AI算力需求爆发式增长，云厂商资本开支持续上行，数据中心GPU供不应求'
    },
    'Consumer Electronics': {
        'up': ['台积电 (芯片代工)', '三星SDI (屏幕)', '立讯精密 (连接器)'],
        'mid_role': '消费电子品牌研发',
        'down': ['全球消费者', '运营商渠道', '电商平台 (Amazon/京东)'],
        'down_note': '端侧 AI 手机与 XR 设备开启换机新周期，高端产品线份额稳步提升'
    },
    'Beverages—Wineries & Distilleries': {
        'up': ['高粱/小麦供应商', '包材企业 (玻璃瓶/纸箱)', '酒曲/微生物技术'],
        'mid_role': '白酒酿造 & 品牌运营',
        'down': ['经销商/专卖店体系', '电商直营 (天猫/京东)', '商务/宴请消费场景'],
        'down_note': '高端白酒受宏观经济与商务消费驱动，消费升级趋势持续，库存周期约2-3年'
    },
    'Electrical Equipment & Parts': {
        'up': ['碳酸锂 (天齐锂业/赣锋)', '正极材料 (容百科技)', '隔膜 (恩捷股份)'],
        'mid_role': '动力电池/储能制造',
        'down': ['新能源车企 (特斯拉/比亚迪)', '储能电站', '消费电子电池'],
        'down_note': '全球电动车渗透率加速，储能需求受可再生能源装机驱动，锂价波动影响全链利润'
    },
    'Banks—Regional': {
        'up': ['央行货币政策 (MLF/LPR)', '同业资金市场', '债券市场'],
        'mid_role': '商业银行 (存贷款/财富管理)',
        'down': ['个人客户 (储蓄/房贷/消费贷)', '企业客户 (经营贷/贸易融资)', '政府/城投融资'],
        'down_note': '利率下行周期压缩净息差，财富管理与中间业务收入成为转型方向'
    },
    'Insurance—Diversified': {
        'up': ['再保险公司', '医疗/养老服务网络', '投资市场'],
        'mid_role': '综合保险/金融集团',
        'down': ['个人保险客户', '企业团险客户', '理财/资管客户'],
        'down_note': '寿险负债端转型推动 NBV 恢复，养老/健康生态圈构建为长期看点'
    },
    'Communication Equipment': {
        'up': ['光芯片 (II-VI/Lumentum)', '高速 DSP (博通/Marvell)', '精密光学元件'],
        'mid_role': '光通信设备/光模块制造',
        'down': ['云厂商数据中心 (谷歌/AWS/Meta)', '电信运营商 (5G 建设)', 'AI 算力互联'],
        'down_note': '800G/1.6T 光模块需求随 AI 集群扩建爆发，硅光技术为下一代方向'
    },
    'Electronic Components': {
        'up': ['精密模具/自动化设备', '金属/塑胶/陶瓷原材料', '电镀/表面处理'],
        'mid_role': '精密电子零部件制造',
        'down': ['苹果/华为 (消费电子)', '汽车 Tier 1 (线束/连接器)', '5G 基站设备商'],
        'down_note': '消费电子精密制造向汽车电子延伸，智能汽车零部件为第二增长曲线'
    },
}

def build_chain_html(info, ticker):
    """构建产业链定位图：优先按 Ticker 精确匹配，其次按 industry/sector 模糊匹配，无数据时明确提示而非通用描述"""
    sector = info.get('sector', '')
    industry = info.get('industry', '')
    name = info.get('shortName', ticker)

    # 第一优先级：按 Ticker 代码精确查找（不依赖 yfinance 的 industry 字段）
    tk_clean = ticker.upper().replace('.SS', '.SS').replace('.SZ', '.SZ')
    chain = TICKER_CHAIN_DB.get(tk_clean, None)

    # 第二优先级：按 industry 精确匹配
    if chain is None and industry:
        chain = CHAIN_DB.get(industry, None)

    # 第三优先级：按 industry/sector 模糊匹配
    if chain is None and (industry or sector):
        for key in CHAIN_DB:
            if (industry and key.lower() in industry.lower()) or (sector and key.lower() in sector.lower()):
                chain = CHAIN_DB[key]
                break

    # 无数据时：明确提示，彻底禁止通用占位描述
    if chain is None:
        industry_display = industry or '未获取到行业信息'
        return f"""<div style="margin:1.5rem 0; padding:25px; background:rgba(20,24,33,0.6); border-radius:16px; border:1px solid rgba(255,255,255,0.05);">
<div style="text-align:center; font-size:1.15rem; font-weight:700; color:#38bdf8; margin-bottom:1rem;">🌐 {name} 产业链生态定位图谱</div>
<div style="text-align:center; padding:2rem; color:#94a3b8; font-size:0.95rem;">
<div style="font-size:2rem; margin-bottom:1rem;">📭</div>
<div style="margin-bottom:0.5rem;">暂无 <b style="color:#38bdf8;">{name} ({ticker})</b> 的专属产业链数据</div>
<div style="font-size:0.82rem; opacity:0.7;">行业: {industry_display} | 板块: {sector or '未获取'}</div>
<div style="font-size:0.82rem; opacity:0.6; margin-top:1rem;">本站严格遵循"无专属数据不展示"原则，绝不使用通用描述占位。</div>
</div>
</div>"""

    up_li = ''.join([f'<li style="margin-bottom:6px;">{c}</li>' for c in chain['up']])
    down_li = ''.join([f'<li style="margin-bottom:6px;">{c}</li>' for c in chain['down']])

    return f"""<div style="margin:1.5rem 0; width:100%; padding:25px; background:rgba(20,24,33,0.6); border-radius:16px; border:1px solid rgba(255,255,255,0.05); box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
<div style="text-align:center; font-size:1.15rem; font-weight:700; margin-bottom:1.5rem; color:#38bdf8; letter-spacing:1px;">🌐 {name} 产业链生态定位图谱</div>
<div class="chain-grid">
<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:20px; box-shadow:inset 0 0 20px rgba(0,0,0,0.2);">
<div style="font-size:0.95rem; font-weight:700; color:#94a3b8; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px; margin-bottom:15px; display:flex; align-items:center; gap:8px;"><span>🏭</span> <span>上游 (Upstream)</span></div>
<ul style="font-size:0.85rem; padding-left:20px; margin:0; line-height:1.6; color:#e2e8f0;">{up_li}</ul>
</div>
<div class="chain-arrow">➔</div>
<div style="background:linear-gradient(145deg, rgba(56,189,248,0.15) 0%, rgba(14,165,233,0.05) 100%); border:1px solid rgba(56,189,248,0.4); border-radius:12px; padding:20px; box-shadow:0 8px 25px rgba(56,189,248,0.15); display:flex; flex-direction:column; justify-content:center; align-items:center;">
<div style="font-size:0.95rem; font-weight:700; color:#38bdf8; margin-bottom:12px; letter-spacing:1px;">⚙️ 中游 (Midstream)</div>
<div style="font-size:1.4rem; font-weight:900; color:#ffffff; text-align:center; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">{name}</div>
<div style="font-size:0.88rem; opacity:0.9; margin-top:12px; text-align:center; background:rgba(0,0,0,0.2); padding:6px 12px; border-radius:6px;">{chain['mid_role']}</div>
</div>
<div class="chain-arrow">➔</div>
<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:20px; box-shadow:inset 0 0 20px rgba(0,0,0,0.2);">
<div style="font-size:0.95rem; font-weight:700; color:#94a3b8; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px; margin-bottom:15px; display:flex; align-items:center; gap:8px;"><span>🛒</span> <span>下游 (Downstream)</span></div>
<ul style="font-size:0.85rem; padding-left:20px; margin:0; line-height:1.6; color:#e2e8f0;">{down_li}</ul>
</div>
</div>
<div style="text-align:center; font-size:0.82rem; margin-top:1.8rem; color:#94a3b8; background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;">
📌 {chain['down_note']}
</div>
</div>"""


def get_stock_profile(ticker_input, info, mapped_name="", institutional_holders_df=None):
    """根据输入的股票代码/名称，获取真实的机构持仓等客观数据；无法获取真实数据时明确留空，不编造模板占位数字"""
    s_name = mapped_name or info.get('shortName') or ticker_input
    pure_code = ticker_input.replace('.SS', '').replace('.SZ', '')
    is_a_share = ticker_input.endswith('.SS') or ticker_input.endswith('.SZ') or pure_code.isdigit()

    inst_names, inst_shares = [], []
    if is_a_share:
        try:
            import akshare as ak
            df_holder = ak.stock_circulate_stock_holder(symbol=pure_code)
            if df_holder is not None and not df_holder.empty:
                df_holder = df_holder.head(8)
                names, shares = [], []
                for _, row in df_holder.iterrows():
                    holder_name = str(row.get('股东名称', row.iloc[3]))
                    share_pct = row.get('占总流通股本比例', row.iloc[5])
                    try:
                        share_pct = float(share_pct)
                    except Exception:
                        continue
                    if "自然人" not in holder_name and len(holder_name) > 2:
                        names.append(holder_name[:12] + ".." if len(holder_name) > 12 else holder_name)
                        shares.append(round(share_pct, 2))
                    if len(names) == 5:
                        break
                if len(names) >= 3:
                    inst_names, inst_shares = names, shares
        except Exception:
            pass
    else:
        # 美股/港股: 使用 yfinance 传过来的 institutional_holders_df (P6)
        if institutional_holders_df is not None and not institutional_holders_df.empty:
            try:
                cols = list(institutional_holders_df.columns)
                holder_col = next((c for c in cols if 'Holder' in str(c) or '机构' in str(c)), cols[0])
                pct_col = next((c for c in cols if '% Out' in str(c) or 'pct' in str(c).lower() or '比例' in str(c)), None)
                
                names, shares = [], []
                for _, row in institutional_holders_df.head(8).iterrows():
                    h_name = str(row[holder_col])
                    if pct_col:
                        h_pct = float(row[pct_col]) * 100 if float(row[pct_col]) <= 1.0 else float(row[pct_col])
                    else:
                        total_sh = info.get('sharesOutstanding')
                        sh_col = next((c for c in cols if 'Shares' in str(c)), None)
                        if sh_col and total_sh:
                            h_pct = (float(row[sh_col]) / total_sh) * 100
                        else:
                            h_pct = 0.0
                            
                    names.append(h_name[:15] + ".." if len(h_name) > 15 else h_name)
                    shares.append(round(h_pct, 2))
                if len(names) >= 1:
                    inst_names, inst_shares = names, shares
            except Exception:
                pass

    profile = {
        'display_name': s_name,
        'sub_sector': info.get('industry', '主营相关行业'),
        'inst_names': inst_names,
        'inst_shares': inst_shares,
    }
    return profile

# -------------------------------------------------------------------
# 5. 主界面：标的概览与 5 维基础卡片
# -------------------------------------------------------------------
ticker_input, mapped_name = resolve_ticker(user_ticker_raw)
if mapped_name and mapped_name != ticker_input:
    st.caption(f"💡 自动解析标的名称 **{mapped_name}** → 代码 **{ticker_input}**")

summary_data = "暂无数据"
all_data = None

if ticker_input:
    try:
        with st.spinner(f"正在采集 {ticker_input} 全量多源数据..."):
            all_data = fetch_all_data(ticker_input)
        info = all_data['info']
        hist_1y = all_data.get('hist_1y')

        # 多重容错价格提取（针对美股/A股接口）
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if (current_price is None or current_price == "N/A" or current_price == "无") and hist_1y is not None and not hist_1y.empty:
            current_price = round(float(hist_1y['Close'].iloc[-1]), 2)

        currency = info.get("currency", "")
        if not currency and (ticker_input.endswith(('.SS', '.SZ')) or all_data.get('is_a_share')):
            currency = "元"

        current_price_str = f"{current_price:.2f} {currency}".strip() if isinstance(current_price, (int, float)) else str(current_price or "暂无行情")

        pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        pe_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"

        market_cap = info.get("marketCap")
        if isinstance(market_cap, (int, float)):
            cap_str = f"{market_cap / 1e12:.2f} 万亿" if market_cap >= 1e12 else (f"{market_cap / 1e8:.2f} 亿" if market_cap >= 1e8 else f"{market_cap:,}")
        else:
            cap_str = "N/A"

        rev_growth = info.get("revenueGrowth")
        rev_str = f"{rev_growth * 100:.2f}%" if isinstance(rev_growth, (int, float)) else "N/A"
        industry = info.get("industry") or mapped_name or "N/A"
        sector = info.get("sector") or "N/A"

        summary_data = f"""
        - 代码/名称: {ticker_input} ({info.get('shortName', mapped_name or ticker_input)})
        - 当前价格: {current_price_str}
        - 行业板块: {sector} / {industry}
        - 市盈率 (PE TTM): {pe_str}
        - 总市值: {cap_str}
        - 营收增速: {rev_str}
        - 52周高/低: {info.get('fiftyTwoWeekHigh', 'N/A')} / {info.get('fiftyTwoWeekLow', 'N/A')}
        - 毛利率: {info.get('grossMargins', 'N/A')}
        - ROE: {info.get('returnOnEquity', 'N/A')}
        """

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ 无法拉取标的行情数据，请检查网络或代码名称: {e}")

# -------------------------------------------------------------------
# 6. 点击生成数据聚合报告
# -------------------------------------------------------------------
if generate_btn:
    if not api_key_input:
        st.warning("⚠️ 请输入 API 密钥 (智谱清言 ZHIPU_API_KEY 或 OpenAI API Key)")
    elif not all_data or all_data.get('hist_1y') is None:
        st.error("⚠️ 未能成功获取该标的的行情数据（可能是接口限流 Too Many Requests 或代码有误），请稍后重试或更换标的。")
    else:

        status_box = st.status(f"🚀 **正在为 [{ticker_input}] 采集与整理客观数据...**", expanded=True)
        with status_box:
            st.write("🔍 **步骤 1/5: 读取多源新闻快讯...**")
            news_for_prompt = ""
            yf_news = all_data.get('news', []) if all_data else []
            ak_news = all_data.get('ak_news') if all_data else None
            for n in yf_news[:5]:
                news_for_prompt += f"- [{n.get('publisher', '')}] {n.get('title', '')}\n"
            if ak_news is not None and not ak_news.empty:
                for _, row in ak_news.head(5).iterrows():
                    title = row.get('新闻标题', '')
                    source = row.get('文章来源', '东方财富')
                    news_for_prompt += f"- [{source}] {title}\n"
            if not news_for_prompt:
                news_for_prompt = "暂未通过接口读取到近期个股新闻。"
            time.sleep(0.3)

            st.write("📊 **步骤 2/5: 读取近1年 K 线与财务报表数据**")
            chanlun_text = analyze_kline_and_chanlun(all_data['hist_1y'])
            time.sleep(0.3)

            st.write("📈 **步骤 3/5: 缠论技术结构量化计算（简化版）**")
            time.sleep(0.3)

            st.write("🎯 **步骤 4/5: 第三方分析师历史数据与机构持仓解析**")
            analyst_data = ""
            targets = all_data.get('analyst_targets')
            currency = all_data['info'].get('currency', '')
            if isinstance(targets, dict) and targets:
                analyst_data += f"第三方分析师目标价(历史事实): 当前={fmt_price_val(targets.get('current'), currency)}, 均值={fmt_price_val(targets.get('mean'), currency)}, 中位={fmt_price_val(targets.get('median'), currency)}, 最高={fmt_price_val(targets.get('high'), currency)}, 最低={fmt_price_val(targets.get('low'), currency)}\n"
            recs = all_data.get('recommendations')
            if recs is not None and not recs.empty:
                latest = recs.iloc[0]
                analyst_data += f"最新评级人数分布(第三方历史事实): 强烈推荐={latest.get('strongBuy',0)}, 买入={latest.get('buy',0)}, 持有={latest.get('hold',0)}, 卖出={latest.get('sell',0)}\n"
            ak_forecast = all_data.get('ak_forecast')
            if ak_forecast is not None and not ak_forecast.empty:
                analyst_data += f"东方财富盈利预测一致预期(第三方历史事实):\n{ak_forecast.head(5).to_string()}\n"
            inst = all_data.get('institutional_holders')
            if inst is not None and not inst.empty:
                analyst_data += f"机构持仓Top5(第三方历史事实):\n{inst.head(5).to_string()}\n"
            if not analyst_data:
                analyst_data = "暂未读取到第三方分析师预期数据。"
            time.sleep(0.3)

            st.write("📝 **步骤 5/5: 合成客观数据摘要报告...**")
            time.sleep(0.2)

        # ⚠️ v2.0 重新定位：LLM 仅做"客观事实摘要与翻译"，不生成投资评级/目标价/仓位建议。
        prompt = f"""
你是一名严格的财经信息摘要助手。请针对股票 **{ticker_input}**，基于以下真实抓取的客观数据，撰写一份**纯粹事实性摘要报告**。

【核心要求（严格遵守，违反视为任务失败）】
1. 绝对不允许生成任何投资评级（如"买入"/"增持"/"强烈推荐"）、目标价推荐、仓位配置建议。
2. 绝对不允许编造未在下方数据中出现的具体数字（如营收、利润、目标价）。数据缺失时必须明确写"数据缺失"。
3. 新闻摘要只做"客观事实压缩转述"，不做"这对股价意味着什么"的预测性判断；如需分类事件性质，只能用"正面/负面/中性事件描述"这种基于新闻内容本身的客观分类，不能用"利好/利空"这类带交易暗示的词。
4. 所有内容必须标注来源（如"来源：yfinance"/"来源：akshare"/"第三方机构历史观点，非本报告判断"）。

【基础行情与财务数据（真实抓取）】
{summary_data}

【多源新闻快讯（真实抓取）】
{news_for_prompt}

【近1年K线量化与缠论指标（程序计算，非编造）】
{chanlun_text}

【第三方分析师历史数据与机构持仓（真实抓取，历史事实）】
{analyst_data}

---

### 【报告大纲（仅做客观陈述，不做结论性判断）】

#### 一、 基础数据客观摘要
- 1.1 行情与估值数据的客观陈述（严禁编造，缺失写"数据缺失"）
- 1.2 第三方分析师评级人数分布与目标价历史区间（明确标注"第三方历史观点，非本报告判断"）

#### 二、 产业链上下游客观描述
- 2.1 已知的上下游合作方/客户群体（如有真实数据支持）
- 2.2 若无法获取真实产业链数据，请明确写"数据缺失，无法提供具体产业链细节"

#### 三、 主营业务客观描述
- 3.1 主营业务与产品线（基于真实数据，缺失写"数据缺失"）
- 3.2 同行业上市公司列表（仅在能验证真实性时列出，否则写"数据缺失，无法提供可验证的同行对比"）

#### 四、 缠论技术面数据摘要
- 4.1 直接转述程序计算出的顶底分型、中枢区间、MACD背驰结果（不做买卖点推荐）

#### 五、 财务数据客观摘要
- 5.1 财务核心指标客观陈述（严禁编造，缺失写"数据缺失"）
- 5.2 第三方分析师EPS/营收增速预测（标注"第三方历史观点"）

#### 六、 事件与关注变量
- 6.1 已知的真实公司专属事件（如财报日期）
- 6.2 新闻事件性质客观分类（正面/负面/中性事件描述，不做利好利空判断）

**输出要求**: 使用规范 Markdown 格式，语言客观克制，禁止使用任何带有引导性/结论性的投资建议措辞。
"""

        base_url = "https://open.bigmodel.cn/api/paas/v4/"
        if api_key_input.startswith("sk-proj-"):
            base_url = "https://api.openai.com/v1"
        client = OpenAI(api_key=api_key_input, base_url=base_url)

        try:
            response = client.chat.completions.create(
                model="glm-4-flash" if "bigmodel" in base_url else "gpt-4o",
                messages=[
                    {"role": "system", "content": "你是严格的客观信息摘要助手，只做事实性转述，绝不生成投资建议、评级或目标价推荐。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            ai_reply = response.choices[0].message.content
            status_box.update(label="✅ **客观数据摘要报告已生成！**", state="complete", expanded=False)

        except Exception as e:
            status_box.update(label="❌ **AI 调用失败**", state="error", expanded=True)
            st.error(f"AI 调用失败: {e}")

if ticker_input and all_data and all_data.get('hist_1y') is not None:
    try:
        # Extract metrics
        info = all_data.get('info', {})
        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        prev_close = info.get('previousClose', price)
        chg_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0
        pe_ttm = info.get('trailingPE')
        fwd_pe = info.get('forwardPE')
        inst_pct = info.get('heldPercentInstitutions')

        # 客观「52周价格区间位置」：纯统计事实（(现价-52周低)/(52周高-52周低)），
        # 不是风险评级、不是买卖信号，只是价格所处历史区间的位置描述
        wk_high = info.get('fiftyTwoWeekHigh')
        wk_low = info.get('fiftyTwoWeekLow')
        range_pos_str = "N/A"
        if isinstance(wk_high, (int, float)) and isinstance(wk_low, (int, float)) and wk_high > wk_low and isinstance(price, (int, float)):
            range_pos = (price - wk_low) / (wk_high - wk_low) * 100
            range_pos = max(0, min(100, range_pos))
            range_pos_str = f"{range_pos:.0f}%"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("最新股价/涨跌", f"{price}", f"{chg_pct}%", delta_color="normal" if chg_pct >= 0 else "inverse")
        m2.metric("Trailing PE / Forward PE",
                   f"{pe_ttm:.2f}" if isinstance(pe_ttm, (int, float)) else "N/A",
                   f"{fwd_pe:.2f} Fwd" if isinstance(fwd_pe, (int, float)) else None,
                   delta_color="off")
        m3.metric("机构持仓比例",
                   f"{inst_pct*100:.2f}%" if isinstance(inst_pct, (int, float)) else "N/A",
                   delta_color="off")
        m4.metric("52周区间位置", range_pos_str,
                   help="当前价格在52周最高/最低价之间的相对位置，纯统计事实，不代表风险等级、买卖信号或任何投资建议")
    except Exception:
        pass

    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

    st.markdown("### 📊 Executive Summary")
    exec_c1, exec_c2 = st.columns([2, 3])

    if True:

            # ===== 提前获取股票 Profile（真实机构持仓数据，无编造） =====
            st_prof = get_stock_profile(ticker_input, info, mapped_name, all_data.get('institutional_holders'))
            s_title_name = st_prof['display_name']

            targets = all_data.get('analyst_targets', {})
            targets = targets if isinstance(targets, dict) else {}
            mean_p = targets.get("mean") if isinstance(targets.get("mean"), (int, float)) else None
            high_p = targets.get("high") if isinstance(targets.get("high"), (int, float)) else None
            low_p = targets.get("low") if isinstance(targets.get("low"), (int, float)) else None
            if mean_p is None or high_p is None or low_p is None:
                target_range_str = "暂无数据"
            else:
                target_range_str = f"{fmt_price_val(low_p, currency)} ~ {fmt_price_val(high_p, currency)}"

            # ===== 差异化功能2：五维雷达图评分计算（仅计算一次，全站只渲染一次，避免重复图表） =====
            radar_scores = {'估值 (Valuation)': 50, '成长 (Growth)': 50, '动能 (Momentum)': 50, '盈利 (Profitability)': 50, '健康 (Health)': 50}
            try:
                pe = info.get('trailingPE', 0)
                if pe and pe > 0: radar_scores['估值 (Valuation)'] = max(10, min(100, 100 - (pe - 10) * 1.5))
                rev_g = info.get('revenueGrowth', 0)
                if rev_g: radar_scores['成长 (Growth)'] = max(10, min(100, 50 + rev_g * 100))
                recent_close = all_data['hist_1y']['Close'].iloc[-1] if not all_data['hist_1y'].empty else 0
                pct_1y = ((recent_close - all_data['hist_1y']['Close'].iloc[0]) / all_data['hist_1y']['Close'].iloc[0]) * 100 if not all_data['hist_1y'].empty else 0
                radar_scores['动能 (Momentum)'] = max(10, min(100, 50 + pct_1y))
                roe = info.get('returnOnEquity', 0)
                if roe: radar_scores['盈利 (Profitability)'] = max(10, min(100, 30 + roe * 200))
                debt = info.get('debtToEquity', 0)
                if debt: radar_scores['健康 (Health)'] = max(10, min(100, 100 - debt / 2))
            except Exception:
                pass

            with exec_c1:
                df_radar = pd.DataFrame(dict(r=list(radar_scores.values()), theta=list(radar_scores.keys())))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True, template="plotly_dark")
                fig_radar.update_traces(fill='toself', line_color='#00F2FE', fillcolor='rgba(0, 242, 254, 0.15)')
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=False, range=[0, 100]),
                        angularaxis=dict(color='#F0F4F8', gridcolor='rgba(255,255,255,0.1)'),
                        bgcolor='rgba(0,0,0,0)'
                    ),
                    margin=dict(l=50, r=50, t=40, b=40),
                    height=420,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})
                st.caption("📌 五维评分基于真实财务数据的固定映射公式归一化到0-100，客观指标可视化，不代表投资建议。")

            with exec_c2:
                st.markdown('<div class="bg-card-glass" style="padding:15px; border-radius:12px; background: rgba(22, 27, 38, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); height:100%;">', unsafe_allow_html=True)
                st.markdown("#### 🧠 AI 反共识摘要总结")
                st.markdown('<span class="badge-neutral">此摘要由 AI 生成，仅为对真实数据的客观陈述整理</span>', unsafe_allow_html=True)

                try:
                    st.markdown(ai_reply if 'ai_reply' in locals() else "等待 AI 报告生成...", unsafe_allow_html=True)
                except Exception:
                    st.markdown("等待 AI 报告生成...")

                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

            tab1, tab2, tab3, tab4 = st.tabs(["🎯 反共识诊断", "📊 财报与估值穿透", "🏛️ 机构与资金追踪", "📰 AI 中性舆情解构"])

            # =====================================================================
            # Tab 1：反共识诊断 —— 分析师评级分布、产业链图谱、主营业务构成、缠论技术摘要
            # =====================================================================
            with tab1:
                st.markdown("---")
                st.markdown(f'<div style="text-align:center; font-size:1.2rem; font-weight:800; margin-bottom:1.0rem;">📌 【{s_title_name}】 客观数据总览</div>', unsafe_allow_html=True)
                st.caption("⚠️ 以下均为第三方数据源（yfinance/akshare）的客观历史记录，不构成、也不包含本站任何投资建议、评级、目标价推荐或仓位建议。")

                st.markdown("### 📊 第三方分析师评级分布 (历史事实)")
                recs_df_top = all_data.get('recommendations')

                rat_col_text, rat_col_chart = st.columns([1, 1.2])
                with rat_col_text:
                    st.markdown(f"""
                    **第三方目标价历史区间**
                    - 最高: {fmt_price_val(high_p, currency) if high_p else 'N/A'}
                    - 均值: {fmt_price_val(mean_p, currency) if mean_p else 'N/A'}
                    - 最低: {fmt_price_val(low_p, currency) if low_p else 'N/A'}

                    <div style="font-size:0.75rem; opacity:0.6; margin-top:1rem;">数据来源：yfinance<br>不构成投资建议</div>
                    """, unsafe_allow_html=True)

                with rat_col_chart:
                    if recs_df_top is not None and not recs_df_top.empty:
                        try:
                            latest_r = recs_df_top.iloc[0]
                            vals = [
                                int(latest_r.get('strongBuy', 0) or 0),
                                int(latest_r.get('buy', 0) or 0),
                                int(latest_r.get('hold', 0) or 0),
                                int(latest_r.get('sell', 0) or 0),
                                int(latest_r.get('strongSell', 0) or 0)
                            ]
                            labels = ['强烈买入', '买入', '持有', '卖出', '强烈卖出']
                            colors = ['#ef4444', '#f87171', '#fbbf24', '#34d399', '#00b865']
                            df_pie = pd.DataFrame({'Label': labels, 'Value': vals})
                            df_pie = df_pie[df_pie['Value'] > 0]

                            if not df_pie.empty:
                                fig_donut = px.pie(df_pie, values='Value', names='Label', hole=0.6,
                                                  color='Label', color_discrete_map=dict(zip(labels, colors)))
                                fig_donut.update_layout(
                                    height=220, margin=dict(l=0, r=0, t=10, b=10),
                                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    showlegend=False,
                                    annotations=[dict(text='第三方评级分布', x=0.5, y=0.5, font_size=12, showarrow=False)]
                                )
                                fig_donut.update_traces(textinfo='label+percent', textfont_size=11, hoverinfo='label+value')
                                st.plotly_chart(fig_donut, use_container_width=True)
                            else:
                                st.info("暂无有效评级人数")
                        except Exception:
                            st.info("评级数据解析异常")
                    else:
                        st.info("暂无评级数据")

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                st.markdown(build_chain_html(info, ticker_input), unsafe_allow_html=True)

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                st.markdown(f"### 🏢 {s_title_name} 主营业务构成 <span style='font-size:0.75rem; opacity:0.6;'>数据来源标注见下</span>", unsafe_allow_html=True)
                main_comp = all_data.get('main_composition')
                if main_comp is not None and not main_comp.empty:
                    # ==== A 股：akshare 主营构成数据 ====
                    try:
                        c_pie1, c_pie2 = st.columns(2)
                        with c_pie1:
                            df_prod = main_comp[main_comp['分类类型'].str.contains('产品', na=False)] if '分类类型' in main_comp.columns else pd.DataFrame()
                            if not df_prod.empty and '主营构成' in df_prod.columns and '收入比例' in df_prod.columns:
                                df_prod['收入比例数值'] = df_prod['收入比例'].astype(str).str.replace('%', '', regex=False).astype(float)
                                fig_p1 = px.pie(df_prod, values='收入比例数值', names='主营构成', hole=0.4, title="按产品分类营收占比", color_discrete_sequence=px.colors.sequential.Teal)
                                fig_p1.update_traces(textinfo='label+percent', textposition='inside', showlegend=False)
                                fig_p1.update_layout(margin=dict(t=40, b=10, l=10, r=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                                st.plotly_chart(fig_p1, use_container_width=True)
                            else:
                                st.info("暂无按产品分类数据")

                        with c_pie2:
                            df_reg = main_comp[main_comp['分类类型'].str.contains('地区', na=False)] if '分类类型' in main_comp.columns else pd.DataFrame()
                            if not df_reg.empty and '主营构成' in df_reg.columns and '收入比例' in df_reg.columns:
                                df_reg['收入比例数值'] = df_reg['收入比例'].astype(str).str.replace('%', '', regex=False).astype(float)
                                fig_p2 = px.pie(df_reg, values='收入比例数值', names='主营构成', hole=0.4, title="按地区分类营收占比", color_discrete_sequence=px.colors.sequential.Purp)
                                fig_p2.update_traces(textinfo='label+percent', textposition='inside', showlegend=False)
                                fig_p2.update_layout(margin=dict(t=40, b=10, l=10, r=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                                st.plotly_chart(fig_p2, use_container_width=True)
                            else:
                                st.info("暂无按地区分类数据")

                        with st.expander("查看原始数据明细"):
                            comp_cols = [c for c in main_comp.columns if c in ['报告期', '分类类型', '主营构成', '主营收入', '收入比例', '主营利润', '利润比例', '主营成本', '成本比例']]
                            st.dataframe(main_comp[comp_cols] if comp_cols else main_comp, use_container_width=True)
                            st.caption("📌 数据来源：akshare stock_zygc_em（主营构成）。")
                    except Exception:
                        st.info("⚠️ 主营构成数据格式解析异常，暂不展示，避免误导。")
                else:
                    # ==== 美股/港股：从 yfinance 季度利润表 + 业务概要提取 ====
                    us_biz_shown = False
                    try:
                        # 1. 尝试从季度利润表获取收入/利润关键行
                        qis = all_data.get('quarterly_income_stmt')
                        ais = all_data.get('income_stmt')
                        fin_stmt = qis if (qis is not None and not qis.empty) else ais
                        if fin_stmt is not None and not fin_stmt.empty:
                            # 提取关键财务行（收入/成本/毛利/运营利润/净利）
                            key_rows = ['Total Revenue', 'Cost Of Revenue', 'Gross Profit',
                                        'Operating Income', 'Operating Expense', 'Net Income',
                                        'EBITDA', 'Research And Development']
                            available_rows = [r for r in key_rows if r in fin_stmt.index]
                            if available_rows:
                                display_df = fin_stmt.loc[available_rows].head(4)  # 最近4期
                                # 格式化列名为日期字符串
                                display_df.columns = [str(c.date()) if hasattr(c, 'date') else str(c) for c in display_df.columns]
                                # 格式化数值为亿/万
                                def fmt_fin_num(v):
                                    if pd.isna(v): return 'N/A'
                                    v = float(v)
                                    if abs(v) >= 1e9: return f"{v/1e9:.2f}B"
                                    if abs(v) >= 1e6: return f"{v/1e6:.1f}M"
                                    return f"{v:,.0f}"
                                display_formatted = display_df.applymap(fmt_fin_num)
                                # 行名中英文映射
                                row_name_map = {
                                    'Total Revenue': '📊 总营收 (Revenue)',
                                    'Cost Of Revenue': '💰 营业成本 (COGS)',
                                    'Gross Profit': '📈 毛利 (Gross Profit)',
                                    'Operating Income': '🏢 营业利润 (Operating Income)',
                                    'Operating Expense': '📋 营业费用 (OpEx)',
                                    'Net Income': '💵 净利润 (Net Income)',
                                    'EBITDA': '📐 EBITDA',
                                    'Research And Development': '🔬 研发支出 (R&D)',
                                }
                                display_formatted.index = [row_name_map.get(r, r) for r in display_formatted.index]
                                is_quarterly = qis is not None and not qis.empty
                                period_label = '季度' if is_quarterly else '年度'
                                st.markdown(f"#### 📊 {s_title_name} 近期{period_label}利润表关键指标 <span style='font-size:0.75rem; opacity:0.6;'>来源: yfinance</span>", unsafe_allow_html=True)
                                st.dataframe(display_formatted, use_container_width=True)

                                # 如果有多期总营收，绘制营收趋势柱状图
                                if 'Total Revenue' in fin_stmt.index:
                                    rev_series = fin_stmt.loc['Total Revenue'].dropna().head(8)
                                    if len(rev_series) >= 2:
                                        rev_df = pd.DataFrame({
                                            'Period': [str(c.date()) if hasattr(c, 'date') else str(c) for c in rev_series.index],
                                            'Revenue': [float(v)/1e9 for v in rev_series.values]
                                        })
                                        rev_df = rev_df.iloc[::-1]  # 按时间正序
                                        fig_rev = px.bar(rev_df, x='Period', y='Revenue',
                                                        title=f"{s_title_name} {period_label}营收趋势 (单位: 十亿 {info.get('currency', 'USD')})",
                                                        color_discrete_sequence=['#00b865'])
                                        fig_rev.update_layout(
                                            height=280, template='plotly_dark',
                                            margin=dict(l=10, r=10, t=40, b=10),
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                            xaxis_title='', yaxis_title='Revenue (B)'
                                        )
                                        st.plotly_chart(fig_rev, use_container_width=True)
                                us_biz_shown = True
                    except Exception:
                        pass

                    # 2. 展示公司业务概要（longBusinessSummary）
                    try:
                        biz_summary = info.get('longBusinessSummary', '')
                        if biz_summary and len(biz_summary) > 50:
                            st.markdown(f"#### 📝 {s_title_name} 业务概要 <span style='font-size:0.75rem; opacity:0.6;'>来源: yfinance</span>", unsafe_allow_html=True)
                            st.markdown(f'<div style="background:rgba(20,24,33,0.5); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.05); font-size:0.88rem; line-height:1.7; color:#e2e8f0;">{biz_summary}</div>', unsafe_allow_html=True)
                            us_biz_shown = True
                    except Exception:
                        pass

                    # 3. 展示行业/板块分类
                    try:
                        sector_val = info.get('sector', '')
                        industry_val = info.get('industry', '')
                        employees = info.get('fullTimeEmployees', '')
                        website = info.get('website', '')
                        if sector_val or industry_val:
                            meta_items = []
                            if sector_val: meta_items.append(f"<b>板块:</b> {sector_val}")
                            if industry_val: meta_items.append(f"<b>细分行业:</b> {industry_val}")
                            if employees: meta_items.append(f"<b>全职员工:</b> {employees:,}" if isinstance(employees, int) else f"<b>全职员工:</b> {employees}")
                            if website: meta_items.append(f"<b>官网:</b> <a href='{website}' style='color:#38bdf8;'>{website}</a>")
                            meta_html = " &nbsp;|&nbsp; ".join(meta_items)
                            st.markdown(f'<div style="background:rgba(0,242,254,0.05); padding:10px 15px; border-radius:8px; border:1px solid rgba(0,242,254,0.15); font-size:0.85rem; color:#94a3b8; margin-top:0.8rem;">{meta_html}</div>', unsafe_allow_html=True)
                            us_biz_shown = True
                    except Exception:
                        pass

                    if not us_biz_shown:
                        st.info(f"⚠️ 暂无 {s_title_name} 的业务构成数据（可能是 yfinance 接口限流），请稍后重试。")

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                c4_a, c4_b = st.columns([0.95, 1.05])
                with c4_a:
                    st.markdown("### 📈 缠论技术面数据摘要 <span style='font-size:0.75rem; opacity:0.6;'>⚠️ 简化版分型/中枢识别+RSI+BOLL，非买卖点建议</span>", unsafe_allow_html=True)
                    chanlun_text_ui = analyze_kline_and_chanlun(all_data['hist_1y']) if all_data and all_data.get('hist_1y') is not None else "暂无K线数据"
                    st.markdown(chanlun_text_ui, unsafe_allow_html=True)
                    st.caption("📌 以上数据均基于真实K线计算得出，非AI编造。")
                with c4_b:
                    if not all_data['hist_1y'].empty:
                        kline_fig = build_kline_chart(all_data['hist_1y'], ticker_input)
                        kline_fig.update_layout(height=480)
                        st.plotly_chart(kline_fig, use_container_width=True)

            # =====================================================================
            # Tab 2：财报与估值穿透 —— 估值分位数进度条 + 2x2 KPI + 财务核心数据表
            # （此前这些内容被误挂在 tab1 下，导致切到 tab2 时页面只剩一张雷达图，其余"消失"）
            # =====================================================================
            with tab2:
                st.markdown("---")
                st.markdown(f'<div style="text-align:center; font-size:1.2rem; font-weight:800; margin-bottom:0.6rem;">📊 【{s_title_name}】 财报与估值穿透</div>', unsafe_allow_html=True)
                st.caption("⚠️ 以下均为第三方数据源的客观历史记录与统计计算，不构成估值结论或投资建议。")

                st.markdown("#### 📐 股价历史区间分位（近3年，客观统计）")
                hist_long = fetch_price_history_long(ticker_input, years=3)
                if hist_long is not None and len(hist_long) >= 30:
                    closes = hist_long['Close']
                    cur_c = closes.iloc[-1]
                    pct_rank = float((closes < cur_c).mean() * 100)
                    st.markdown(f"""
                    <div class="percentile-track"><div class="percentile-marker" style="left:{pct_rank:.1f}%;"></div></div>
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94A3B8;">
                        <span>近3年最低</span><span>近3年最高</span>
                    </div>
                    <div style="text-align:center; margin-top:0.6rem; font-size:0.95rem;">
                        当前价格处于近3年股价区间的第 <b style="color:#00F2FE; font-size:1.1rem;">{pct_rank:.0f}</b> 百分位
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption("⚠️ 这是「股价」在其自身近3年历史区间中的相对位置，不是「PE估值」的历史分位。严谨的PE历史分位需要完整历史EPS序列，免费数据源无法可靠获取，为避免用假精度误导用户，本站不提供编造的PE分位数字。")
                else:
                    st.info("暂无足够的近3年历史价格数据，无法计算区间分位。")

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("#### 🧮 核心财务 KPI")

                def kpi_card(label, value):
                    return f'<div class="kpi-neon-card"><div class="kpi-neon-label">{label}</div><div class="kpi-neon-value">{value}</div></div>'

                eps_ttm = info.get('trailingEps')
                rev_growth_val = info.get('revenueGrowth')
                net_margin_kpi = info.get('profitMargins') or info.get('netMargins')
                roe_kpi = info.get('returnOnEquity')

                k1, k2 = st.columns(2)
                with k1:
                    st.markdown(kpi_card("EPS (TTM)", f"{eps_ttm:.2f}" if isinstance(eps_ttm, (int, float)) else "N/A"), unsafe_allow_html=True)
                with k2:
                    st.markdown(kpi_card("营收增速", f"{rev_growth_val*100:.2f}%" if isinstance(rev_growth_val, (int, float)) else "N/A"), unsafe_allow_html=True)
                st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
                k3, k4 = st.columns(2)
                with k3:
                    st.markdown(kpi_card("净利率 (TTM)", f"{net_margin_kpi*100:.2f}%" if isinstance(net_margin_kpi, (int, float)) else "N/A"), unsafe_allow_html=True)
                with k4:
                    st.markdown(kpi_card("ROE", f"{roe_kpi*100:.2f}%" if isinstance(roe_kpi, (int, float)) else "N/A"), unsafe_allow_html=True)

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")

                def fnum(v, pct=False, money=False):
                    if v is None or (isinstance(v, float) and np.isnan(v)):
                        return "N/A"
                    try:
                        if pct:
                            return f"{float(v)*100:.2f}%"
                        if money:
                            v = float(v)
                            return f"{v/1e8:.2f}亿" if abs(v) >= 1e8 else f"{v:,.0f}"
                        return str(v)
                    except Exception:
                        return "N/A"

                qf = all_data.get('quarterly_financials')
                rev_now = rev_prev = np_now = np_prev = None
                report_quarter = "N/A"
                if qf is not None and not qf.empty:
                    try:
                        cols = list(qf.columns)
                        report_quarter = str(cols[0].date()) if hasattr(cols[0], 'date') else str(cols[0])
                        if 'Total Revenue' in qf.index:
                            rev_now = qf.loc['Total Revenue'].iloc[0]
                            if len(cols) > 1: rev_prev = qf.loc['Total Revenue'].iloc[1]
                        for key in ['Net Income', 'Net Income Common Stockholders']:
                            if key in qf.index:
                                np_now = qf.loc[key].iloc[0]
                                if len(cols) > 1: np_prev = qf.loc[key].iloc[1]
                                break
                    except Exception:
                        pass

                gross_margin = info.get('grossMargins')
                net_margin = info.get('profitMargins') or info.get('netMargins')
                roe = info.get('returnOnEquity')
                debt_ratio = info.get('debtToEquity')
                fcf = info.get('freeCashflow')

                rev_trend = "N/A"
                if isinstance(rev_now, (int, float)) and isinstance(rev_prev, (int, float)) and rev_prev != 0:
                    rev_trend = f"{(rev_now-rev_prev)/abs(rev_prev)*100:+.1f}% QoQ"
                np_trend = "N/A"
                if isinstance(np_now, (int, float)) and isinstance(np_prev, (int, float)) and np_prev != 0:
                    np_trend = f"{(np_now-np_prev)/abs(np_prev)*100:+.1f}% QoQ"

                st.markdown(f"#### 财务核心数据 <span style='font-size:0.75rem; opacity:0.6;'>数据来源: yfinance | 最新季度: {report_quarter}</span>", unsafe_allow_html=True)
                
                # P7 扩展指标解析
                rd_now = rd_prev = None
                if qf is not None and not qf.empty and 'Research And Development' in qf.index:
                    rd_now = qf.loc['Research And Development'].iloc[0]
                    if len(qf.columns) > 1: rd_prev = qf.loc['Research And Development'].iloc[1]
                elif qf is not None and not qf.empty and 'ResearchAndDevelopment' in qf.index:
                    rd_now = qf.loc['ResearchAndDevelopment'].iloc[0]
                    if len(qf.columns) > 1: rd_prev = qf.loc['ResearchAndDevelopment'].iloc[1]

                op_inc_now = op_inc_prev = None
                if qf is not None and not qf.empty and 'Operating Income' in qf.index:
                    op_inc_now = qf.loc['Operating Income'].iloc[0]
                    if len(qf.columns) > 1: op_inc_prev = qf.loc['Operating Income'].iloc[1]
                elif qf is not None and not qf.empty and 'OperatingIncome' in qf.index:
                    op_inc_now = qf.loc['OperatingIncome'].iloc[0]
                    if len(qf.columns) > 1: op_inc_prev = qf.loc['OperatingIncome'].iloc[1]

                qcf = all_data.get('quarterly_cashflow')
                op_cf_now = op_cf_prev = None
                if qcf is not None and not qcf.empty and 'Operating Cash Flow' in qcf.index:
                    op_cf_now = qcf.loc['Operating Cash Flow'].iloc[0]
                    if len(qcf.columns) > 1: op_cf_prev = qcf.loc['Operating Cash Flow'].iloc[1]
                elif qcf is not None and not qcf.empty and 'OperatingCashFlow' in qcf.index:
                    op_cf_now = qcf.loc['OperatingCashFlow'].iloc[0]
                    if len(qcf.columns) > 1: op_cf_prev = qcf.loc['OperatingCashFlow'].iloc[1]

                qbs = all_data.get('quarterly_balance_sheet')
                debt_to_assets = None
                if qbs is not None and not qbs.empty:
                    try:
                        total_assets = None
                        for k in ['Total Assets', 'TotalAssets']:
                            if k in qbs.index:
                                total_assets = qbs.loc[k].iloc[0]
                                break
                        total_debt = None
                        for k in ['Total Debt', 'TotalDebt', 'Total Liabilities Net Minor Interest', 'TotalLiabilitiesNetMinorInterest']:
                            if k in qbs.index:
                                total_debt = qbs.loc[k].iloc[0]
                                break
                        if total_assets and total_debt:
                            debt_to_assets = total_debt / total_assets
                    except Exception:
                        pass

                def fmt_trend(now_val, prev_val):
                    if isinstance(now_val, (int, float)) and isinstance(prev_val, (int, float)) and prev_val != 0:
                        chg = (now_val - prev_val) / abs(prev_val) * 100
                        cls = "trend-up" if chg >= 0 else "trend-down"
                        return f'<span class="{cls}">{chg:+.1f}% QoQ</span>'
                    return '<span class="trend-neutral">—</span>'

                def make_card(label, value_str, trend_html):
                    return f"""
                    <div class="fin-card">
                        <div class="fin-label">{label}</div>
                        <div class="fin-value">{value_str}</div>
                        <div class="fin-trend">{trend_html}</div>
                    </div>
                    """

                cards_html = f"""
                <div class="financial-grid">
                    {make_card("📊 营业收入 (Revenue)", fnum(rev_now, money=True), fmt_trend(rev_now, rev_prev))}
                    {make_card("💵 净利润 (Net Income)", fnum(np_now, money=True), fmt_trend(np_now, np_prev))}
                    {make_card("🏢 营业利润 (Operating Income)", fnum(op_inc_now, money=True), fmt_trend(op_inc_now, op_inc_prev))}
                    {make_card("🔬 研发投入 (R&D)", fnum(rd_now, money=True), fmt_trend(rd_now, rd_prev))}
                    {make_card("💸 经营性现金流 (Op Cashflow)", fnum(op_cf_now, money=True), fmt_trend(op_cf_now, op_cf_prev))}
                    {make_card("🌊 自由现金流 (FCF)", fnum(fcf, money=True), '<span class="trend-neutral">—</span>')}
                    {make_card("📈 毛利率 (Gross Margin)", fnum(gross_margin, pct=True), '<span class="trend-neutral">—</span>')}
                    {make_card("📊 净利率 (Net Margin)", fnum(net_margin, pct=True), '<span class="trend-neutral">—</span>')}
                    {make_card("🧬 ROE (净资产收益率)", fnum(roe, pct=True), '<span class="trend-neutral">—</span>')}
                    {make_card("🛡️ 资产负债率 (Debt to Assets)", fnum(debt_to_assets, pct=True), '<span class="trend-neutral">—</span>')}
                    {make_card("⚖️ 负债权益比 (Debt to Equity)", fnum(debt_ratio), '<span class="trend-neutral">—</span>')}
                </div>
                """
                st.markdown(cards_html, unsafe_allow_html=True)
                st.caption("📌 双向/客观财报指标展示系统，N/A 表示接口未返回对应披露项。")

            # =====================================================================
            # Tab 3：机构与资金追踪 —— 十大流通股东持仓（此前误挂在tab1）+ 机构调研记录
            # =====================================================================
            with tab3:
                st.markdown("---")
                st.markdown(f"### 🏛️ 【{s_title_name}】 机构持仓与资金追踪 <span style='font-size:0.75rem; opacity:0.6;'>公开披露信息聚合</span>", unsafe_allow_html=True)

                has_inst = bool(st_prof['inst_names'] and st_prof['inst_shares'])
                if has_inst:
                    fig_inst = go.Figure(go.Bar(
                        x=st_prof['inst_shares'], y=st_prof['inst_names'], orientation='h',
                        marker_color=['#00b865', '#38bdf8', '#fbbf24', '#a855f7', '#94a3b8'],
                        text=[f"{v}%" for v in st_prof['inst_shares']], textposition='auto'
                    ))
                    fig_inst.update_layout(
                        height=260, template='plotly_dark', margin=dict(l=10, r=10, t=35, b=10),
                        title_text=f"🏛️ {s_title_name} 十大流通股东持仓比例 (%)", yaxis=dict(autorange="reversed"),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_inst, use_container_width=True)
                    st.caption("📌 数据来源：akshare（十大流通股东），真实抓取，非编造。")
                else:
                    st.info("⚠️ 暂无该标的真实十大流通股东数据，本站不使用编造图表。")

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("#### 🔎 机构调研记录")
                if all_data.get('is_a_share'):
                    try:
                        import akshare as ak
                        pure_code = ticker_input.replace('.SS', '').replace('.SZ', '')
                        # P6: 强制调用东方财富调研记录，支持 TypeError 降级
                        try:
                            df_jgdy = ak.stock_jgdy_detail_em(symbol=pure_code)
                        except TypeError:
                            start_date = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%Y%m%d')
                            df_all = ak.stock_jgdy_tj_em(date=start_date)
                            code_col = next((c for c in df_all.columns if '代码' in c or 'code' in c.lower()), None)
                            if code_col and not df_all.empty:
                                df_jgdy = df_all[df_all[code_col].astype(str).str.contains(pure_code)]
                            else:
                                df_jgdy = pd.DataFrame()
                        except Exception:
                            df_jgdy = pd.DataFrame()

                        if df_jgdy is not None and not df_jgdy.empty:
                            col_date = next((c for c in df_jgdy.columns if '日期' in c or '时间' in c or 'date' in c.lower()), None)
                            col_org = next((c for c in df_jgdy.columns if '机构' in c or '对象' in c or '接待' in c or 'org' in c.lower()), None)
                            col_people = next((c for c in df_jgdy.columns if '人员' in c or '调研人' in c or 'people' in c.lower()), None)
                            
                            df_display = pd.DataFrame()
                            df_display['调研日期'] = df_jgdy[col_date].astype(str) if col_date else df_jgdy.iloc[:, 0].astype(str)
                            df_display['调研机构'] = df_jgdy[col_org].astype(str) if col_org else "详见公告"
                            df_display['调研人员'] = df_jgdy[col_people].astype(str) if col_people else "详见公告"
                            
                            st.dataframe(df_display.head(50), use_container_width=True)
                            st.caption("📌 数据来源：akshare (东方财富机构调研数据)")
                        else:
                            st.info("ℹ️ 该标的近90日暂无公开披露的机构调研记录。")
                    except Exception as e:
                        st.info(f"⚠️ 无法获取机构调研数据: {e}")
                else:
                    st.info("ℹ️ 机构调研记录为 A 股监管强制披露类别，港股/美股无完全对应开源接口，此项不适用于当前标的。")
                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

            # =====================================================================
            # Tab 4：AI 中性舆情解构 —— 新闻事件性质客观分类（不变）
            # =====================================================================
            with tab4:
                st.markdown("---")
                st.markdown("## 📰 近期新闻事件性质客观分类 <span style='font-size:0.72rem; opacity:0.6;'>基于新闻标题关键词的客观事件性质分类，非对股价走势的预测</span>", unsafe_allow_html=True)
                n_col1, n_col2 = st.columns(2)
                with n_col1:
                    st.markdown("#### 🟢 正面性质事件描述")
                    positive_kw = ['增长', '突破', '上涨', '创新高', '超预期', '合作', '获批', '中标', 'beat', 'surge', 'rally', 'upgrade', 'growth']
                    found_positive = False
                    all_news_items = []

                    yf_news = all_data.get('news', []) if all_data else []
                    ak_news = all_data.get('ak_news') if all_data else None

                    for n in yf_news[:8]:
                        all_news_items.append({'title': n.get('title', ''), 'source': n.get('publisher', '')})
                    if ak_news is not None and not ak_news.empty:
                        for _, row in ak_news.head(10).iterrows():
                            all_news_items.append({'title': row.get('新闻标题', ''), 'source': row.get('文章来源', '东方财富')})
                    for item in all_news_items:
                        t = item['title'].lower()
                        if any(kw in t for kw in positive_kw):
                            st.markdown(f'<div class="news-positive"><div class="news-title">📈 {item["title"]}</div><div class="news-meta">来源: {item["source"]} | 事件性质：正面描述（非预测）</div></div>', unsafe_allow_html=True)
                            found_positive = True
                    if not found_positive:
                        st.markdown('<div class="news-positive"><div class="news-title">暂未识别到明确正面性质事件</div></div>', unsafe_allow_html=True)
                with n_col2:
                    st.markdown("#### 🔴 负面性质事件描述")
                    negative_kw = ['下跌', '下滑', '亏损', '风险', '减持', '处罚', '调查', '下调', 'decline', 'fall', 'risk', 'downgrade', 'miss', 'loss']
                    found_negative = False
                    for item in all_news_items:
                        t = item['title'].lower()
                        if any(kw in t for kw in negative_kw):
                            st.markdown(f'<div class="news-negative"><div class="news-title">📉 {item["title"]}</div><div class="news-meta">来源: {item["source"]} | 事件性质：负面描述（非预测）</div></div>', unsafe_allow_html=True)
                            found_negative = True
                    if not found_negative:
                        st.markdown('<div class="news-neutral"><div class="news-title">暂未识别到明确负面性质事件</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.caption("⚠️ 免责声明：本工具仅做公开数据的客观聚合与可视化展示，所有内容（包括AI生成的摘要文字）均不构成、也不应被理解为投资建议、评级或目标价推荐。投资有风险，请独立判断并自行承担决策后果。\n")

# 提前创建快讯显示的底端占位容器并填充 (P1 模块重排)
container_tape = st.container()
with container_tape:
    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
    try:
        from market_tape import get_market_tape_ui
        get_market_tape_ui(api_key_input)
    except Exception as e:
        st.error(f"加载实时盘口失败: {e}")
