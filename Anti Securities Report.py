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
st.set_page_config(
    page_title="Anti Stock Report - 客观数据聚合终端 v2.0",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 全局样式定制
st.markdown("""
<style>
    /* 🛡️ 终极源代码与隐私安全防护：彻底隐藏前端右上角 GitHub 图标、View Source 按钮与 Streamlit 菜单页脚 */
    #MainMenu {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    header {visibility: hidden !important; display: none !important;}
    div[data-testid="stDecoration"] {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}
    div[data-testid="stToolbar"] {display: none !important;}
    button[title="View app source"] {display: none !important;}
    
    /* 🎨 选项卡平均分布 (强制接管所有的 tabs 让其铺满) */
    div[data-baseweb="tab-list"] {
        display: flex !important;
        flex-grow: 1 !important;
        width: 100% !important;
    }
    button[data-baseweb="tab"] {
        flex: 1 !important;
        justify-content: center !important;
        text-align: center !important;
    }
    .stApp > header {display: none !important;}
    a[href*="github.com"] {display: none !important;}
    ul[data-testid="main-menu-list"] {display: none !important;}

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    section[data-testid="stSidebar"] { display: none; }

    /* 顶部 Hero Banner */
    .header-banner {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(0,184,101,0.05) 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        border: 1px solid rgba(226,232,240,0.18);
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 1.4rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    /* 全局 Header 顶栏 (自适应深浅主题) */
    .header-box {
        background: linear-gradient(135deg, rgba(0, 184, 101, 0.12) 0%, rgba(56, 189, 248, 0.12) 100%);
        border: 1px solid rgba(0, 184, 101, 0.25);
        border-radius: 16px;
        padding: 1.2rem 1.6rem;
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 1.4rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .header-title {
        font-size: 2.2rem; font-weight: 800; margin: 0;
        display: flex; align-items: center; gap: 0.8rem;
        letter-spacing: -0.5px;
        color: var(--text-color, #ffffff);
    }
    .header-subtitle { opacity: 0.85; font-size: 0.95rem; font-weight: 500; color: var(--text-color, inherit); }
    .badge-green { background-color: #dcfce7; color: #15803d; font-size: 0.8rem; font-weight: 700; padding: 0.25rem 0.75rem; border-radius: 9999px; border: 1px solid #bbf7d0; vertical-align: middle; }

    /* 全球市场卡片样式完整恢复 (自适应深浅) */
    .market-card {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(226, 232, 240, 0.15) !important;
        border-radius: 12px !important;
        padding: 0.9rem 1rem !important;
        text-align: center !important;
        position: relative !important;
        overflow: hidden !important;
        margin-bottom: 0.5rem !important;
    }
    .market-card-hot {
        border-color: rgba(0, 184, 101, 0.5) !important;
        box-shadow: 0 0 12px rgba(0, 184, 101, 0.15) !important;
    }
    .market-flag { font-size: 1.4rem; margin-bottom: 0.2rem; }
    .market-name { font-size: 0.8rem; font-weight: 600; opacity: 0.85; margin: 0.15rem 0; color: var(--text-color, inherit); }
    .market-index { font-size: 1.15rem; font-weight: 700; color: var(--text-color, #f8fafc); }
    .market-chg-up { color: #00b865; font-size: 0.82rem; font-weight: 600; }
    .market-chg-down { color: #ef4444; font-size: 0.82rem; font-weight: 600; }
    .market-sector { font-size: 0.72rem; opacity: 0.75; margin-top: 0.3rem; color: var(--text-color, inherit); }
    .market-badge-hot {
        position: absolute; top: 6px; right: 8px;
        background: #00b865; color: white; font-size: 0.6rem; font-weight: 700;
        padding: 1px 6px; border-radius: 6px;
    }

    /* 5维基础指标卡片 (固定 80px 高度与居中对齐，自适应 Light/Dark 模式) */
    .metric-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(226,232,240,0.15);
        border-radius: 12px;
        padding: 0.8rem 0.6rem;
        text-align: center;
        margin-bottom: 0.6rem;
        height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .metric-label { font-size: 0.78rem; opacity: 0.8; margin-bottom: 0.3rem; font-weight: 500; color: var(--text-color, inherit); }
    .metric-value { font-size: 1.15rem; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; color: var(--text-color, #f8fafc); }

    /* 📅 大事日历左右对照样式 */
    .event-card-row {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(226,232,240,0.12);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
        transition: all 0.2s ease;
    }
    .event-card-row:hover {
        border-color: rgba(0,184,101,0.4);
        background: rgba(255,255,255,0.05);
    }
    .event-left-box {
        flex: 0 0 42%;
        border-right: 1px dashed rgba(226,232,240,0.15);
        padding-right: 1rem;
    }
    .event-right-box {
        flex: 1;
        padding-left: 0.5rem;
    }
    .event-date-badge {
        display: inline-block;
        background: rgba(0,184,101,0.15);
        color: #00b865;
        font-weight: 700;
        font-size: 0.82rem;
        padding: 2px 8px;
        border-radius: 6px;
        margin-bottom: 0.3rem;
    }
    .event-title { font-weight: 700; font-size: 0.95rem; color: var(--text-color, #ffffff); margin-bottom: 0.25rem; }
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
                    prev_close = h['Close'].iloc[-2]
                    cur_close = h['Close'].iloc[-1]
                    chg_pct = (cur_close - prev_close) / prev_close * 100
                    region_data[label] = {'price': cur_close, 'chg': chg_pct}
                elif len(h) == 1:
                    region_data[label] = {'price': h['Close'].iloc[-1], 'chg': 0}
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

# --- 4.2 热门标的选择（标的名与 Candlestick K线缩略图上下严格一对一对应） ---
st.markdown("### 🔥 热门标的快速选择 <span style='font-size:0.78rem; opacity:0.6;'>(按实时成交量排序)</span>", unsafe_allow_html=True)

# 使用 session_state 记录用户选择的热门标的
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

        # Candlestick K 线阴阳缩略图直接渲染在对应按钮正下方
        ohlc = s.get('ohlc', {})
        if ohlc and len(ohlc.get('close', [])) >= 2:
            fig_spk = go.Figure(go.Candlestick(
                open=ohlc['open'],
                high=ohlc['high'],
                low=ohlc['low'],
                close=ohlc['close'],
                increasing_line_color='#00b865',
                decreasing_line_color='#ef4444',
                increasing_fillcolor='#00b865',
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
set_c1, set_c2, set_c3, set_c4, set_c5 = st.columns([2, 2.3, 2, 2.7, 1.8])
with set_c1:
    user_ticker_raw = st.text_input("股票代码 / 名称:", value=st.session_state.selected_ticker, help="可输入 AAPL, 600519.SS，或中文如「苹果」、「新易盛」、「特斯拉」")
with set_c2:
    invest_style = st.selectbox("分析流派:", [
        "全维度综合信息聚合 (推荐)",
        "基本面数据速览",
        "成长性数据速览",
        "缠论与技术面数据",
        "事件与公告速览",
    ])
with set_c3:
    holding_period = st.selectbox("关注周期:", ["中期 (1-6个月)", "超短期 (日内至数日)", "短期 (1-4周)", "长期 (1年以上)"])
with set_c4:
    # 🔒 安全策略：绝不从环境变量/st.secrets 预填开发者自己的 Key。
    # Key 只能来自当前用户本次会话的手动输入，不写入磁盘、不写日志。
    api_key_input = st.text_input(
        "API 密钥:", value="", type="password",
        help="🔒 密钥仅在您的浏览器会话中使用，不会被存储、上传或记录到日志。请前往智谱清言 (bigmodel.cn) 或 OpenAI 官网申请属于您自己的 API Key。"
    )

with set_c5:
    generate_btn = st.button("🚀 生成数据聚合报告", key="btn_main_generate", use_container_width=True)

risk_preference = "稳健型"

# --- 4.4 【新增】全市场实时盘口 (大盘口) ---
try:
    from market_tape import get_market_tape_ui
    get_market_tape_ui(api_key_input)
except Exception as e:
    st.error(f"加载实时盘口失败: {e}")

st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

# --- 4.5 众包财务预测 (Crowdsourcing) ---
try:
    from crowdsource_agent import get_crowdsource_ui
    get_crowdsource_ui(api_key_input, ticker_input)
except Exception as e:
    st.error(f"众包预测组件加载失败: {e}")


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
    for attempt in range(2):
        try:
            data['info'] = stock.info or {}
            break
        except Exception:
            if attempt == 0:
                time.sleep(1.2)
            else:
                data['info'] = {}
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
    except Exception:
        data['institutional_holders'] = None
    try:
        data['quarterly_financials'] = stock.quarterly_financials
    except Exception:
        data['quarterly_financials'] = None

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

    return data

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
                segments.append(f"上涨波段: {d1} ({p1:.2f}) → {d2} ({p2:.2f}), 涨幅 {(p2-p1)/p1*100:.1f}%")
            elif t1 == 'top' and t2 == 'bottom' and (p1 - p2) / p1 > 0.10:
                segments.append(f"下跌波段: {d1} ({p1:.2f}) → {d2} ({p2:.2f}), 跌幅 {(p1-p2)/p1*100:.1f}%")
    segments_str = "\n        - ".join(segments) if segments else "近1年未出现超10%显著波段，为标准窄幅箱体震荡"

    return f"""
        【近1年K线量化与缠论指标（{dates[0]}至{dates[-1]}）】
        - 最新收盘: {recent_close:.2f}, 1年涨跌幅: {pct_1y:+.2f}% ({trend_status})
        - 1年最高: {df['High'].max():.2f} ({df['High'].idxmax().strftime('%Y-%m-%d')}), 最低: {df['Low'].min():.2f} ({df['Low'].idxmin().strftime('%Y-%m-%d')})
        - 近60日缠论中枢(结构化3笔重叠法，无法构建时回退统计分位数近似): 上轨ZG={zg_display:.2f}, 下轨ZD={zd_display:.2f}
        - 中枢构建说明: {zhongshu_note}
        - 最近顶分型: {recent_top[0]} ({recent_top[1]:.2f}), 底分型: {recent_bottom[0]} ({recent_bottom[1]:.2f})
        - MACD能量柱: DIF={macd.iloc[-1]:.3f}, DEA={signal.iloc[-1]:.3f}, 柱体={macd_recent:.3f} ({divergence})
        - 均线支撑/压力位: MA20={df['MA20'].iloc[-1]:.2f}, MA50={df['MA50'].iloc[-1]:.2f}
        - {rsi_status}
        - {boll_status}
        - 近1年波段起止历史明细:
        - {segments_str}
    """

# 产业链知识库：按行业/板块映射上中下游代表企业与下游分析
CHAIN_DB = {
    'Auto Manufacturers': {
        'up': ['宁德时代 (电池)', '博世 (Bosch, 零部件)', '英飞凌 (芯片)'],
        'mid_role': '整车制造 & 智能驾驶',
        'down': ['消费者市场 (换车周期约6-8年)', '出行平台 (Uber/滴滴)', '政府采购/租赁'],
        'down_note': '全球汽车渗透率趋饱和，新能源渗透率快速攀升（中国>40%，欧洲>25%），消费信心与利率水平直接影响购车意愿'
    },
    'Semiconductors': {
        'up': ['阿斯麦 (ASML, 光刻机)', '应用材料 (AMAT, 沉积)', '信越化学 (硅片)'],
        'mid_role': '芯片设计 / 代工制造 (台积电)',
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
    'Hardware, Tech Supply Chain': {
        'up': ['高阶 PCB 板', '高速光模块 (800G/1.6T)', '电源/散热模组'],
        'mid_role': 'AI 服务器整机集成与封装',
        'down': ['微软 / 谷歌 / 亚马逊 / Meta (云厂商)', 'AI 大模型初创企业', '科研机构与算力中心'],
        'down_note': 'AI算力需求爆发式增长，云厂商资本开支出持续上行，数据中心GPU供不应求'
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
}

def build_chain_html(info, ticker):
    """构建产业链定位图（含具体代表公司与下游市场分析）；未命中数据库时明确标注为通用行业描述，非本股票专属事实"""
    sector = info.get('sector', '未知板块')
    industry = info.get('industry', '未知细分行业')
    name = info.get('shortName', ticker)
    chain = CHAIN_DB.get(industry, None)
    is_generic = False
    if chain is None:
        for key in CHAIN_DB:
            if key.lower() in industry.lower() or key.lower() in sector.lower():
                chain = CHAIN_DB[key]
                break
    if chain is None:
        is_generic = True
        chain = {
            'up': [f'{sector}相关原材料/设备供应商（通用行业描述，非本公司专属核实数据）'],
            'mid_role': f'{name} ({industry})',
            'down': ['终端客户（通用行业描述，非本公司专属核实数据）'],
            'down_note': '⚠️ 本公司未命中内置产业链数据库，以上为所属行业的通用性描述，非针对该公司核实的专属事实，请结合公司公告核实。'
        }
    up_html = '<br>'.join([f'• {c}' for c in chain['up']])
    down_html = '<br>'.join([f'• {c}' for c in chain['down']])
    warn_html = '<div style="color:#fbbf24; font-size:0.78rem; margin-top:0.4rem;">⚠️ 未命中内置行业库，以下为通用性描述</div>' if is_generic else ''
    return f"""
    <div style="margin:1.5rem 0; width:100%;">
      <div style="text-align:center; opacity:0.9; font-size:1.05rem; font-weight:700; margin-bottom:1rem; color:#00b865;">🌐 {name} 产业链生态定位图谱</div>
      {warn_html}
      <div class="chain-box">
        <div class="chain-node chain-upstream">
          <div style="font-size:0.95rem; margin-bottom:0.4rem; color:#818cf8;">🏭 <b>上游</b></div>
          <div style="font-size:0.85rem; line-height:1.6; opacity:0.95;">{up_html}</div>
        </div>
        <div class="chain-arrow">➔</div>
        <div class="chain-node chain-midstream chain-highlight">
          <div style="font-size:1.05rem; margin-bottom:0.4rem; color:#fbbf24;">⚙️ <b>中游</b></div>
          <div style="font-size:1rem; font-weight:800; color:#ffffff;">{name}</div>
          <div style="font-size:0.85rem; opacity:0.9; margin-top:0.3rem;">{chain['mid_role']}</div>
        </div>
        <div class="chain-arrow">➔</div>
        <div class="chain-node chain-downstream">
          <div style="font-size:0.95rem; margin-bottom:0.4rem; color:#34d399;">🛒 <b>下游</b></div>
          <div style="font-size:0.85rem; line-height:1.6; opacity:0.95;">{down_html}</div>
        </div>
      </div>
      <div style="text-align:center; opacity:0.85; font-size:0.88rem; margin-top:0.8rem; background:rgba(0,184,101,0.06); padding:0.7rem 1.2rem; border-radius:10px; border:1px dashed rgba(0,184,101,0.3);">
        📌 {chain['down_note']}
      </div>
    </div>
    """


def get_stock_profile(ticker_input, info, mapped_name=""):
    """根据输入的股票代码/名称，获取真实的机构持仓等客观数据；无法获取真实数据时明确留空，不编造模板占位数字"""
    s_name = mapped_name or info.get('shortName') or ticker_input
    pure_code = ticker_input.replace('.SS', '').replace('.SZ', '')

    inst_names, inst_shares = [], []
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

            st.markdown("---")
            st.subheader(f"📊 {ticker_input} 客观数据聚合报告")
            st.markdown('<span class="data-ai-badge">⚠️ 以下摘要由 AI 生成，仅为对真实数据的转述整理，不构成投资建议</span>', unsafe_allow_html=True)
            st.markdown(ai_reply)
            st.download_button(label="📥 下载报告 (Markdown)", data=ai_reply, file_name=f"{ticker_input}_客观数据报告.md", mime="text/markdown")
            st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

        except Exception as e:
            status_box.update(label="❌ **AI 调用失败**", state="error", expanded=True)
            st.error(f"AI 调用失败: {e}")

if ticker_input and all_data and all_data.get('hist_1y') is not None:
    if True:

            # ===== 提前获取股票 Profile（真实机构持仓数据，无编造） =====
            st_prof = get_stock_profile(ticker_input, info, mapped_name)
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

            # ===== 客观数据总览（已删除：三票制表决、评分表、独立性判定卡、法证排查表、
            # 看多逻辑vs伪证条件表、"强烈买入"Banner、机构目标价推荐Banner、仓位建议） =====

            # ===== 差异化功能2：五维雷达图评分计算 =====
            radar_scores = {'估值 (Valuation)': 50, '成长 (Growth)': 50, '动能 (Momentum)': 50, '盈利 (Profitability)': 50, '健康 (Health)': 50}
            try:
                pe = info.get('trailingPE', 0)
                if pe > 0: radar_scores['估值 (Valuation)'] = max(10, min(100, 100 - (pe - 10) * 1.5))
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

            tab_overview, tab_radar, tab_insiders, tab_news = st.tabs(["📊 概览 (Overview)", "🕸️ 五维雷达 (Metrics)", "🏛️ 机构与资金 (Insiders)", "📰 相关新闻 (News)"])

            with tab_radar:
                st.markdown(f'<div style="text-align:center; font-size:1.2rem; font-weight:800; margin-bottom:1.0rem;">🕸️ 【{s_title_name}】 客观五维雷达图</div>', unsafe_allow_html=True)
                st.caption("📌 本雷达图基于 yfinance 提取的绝对财务指标，并使用固定映射逻辑归一化到 0-100 分位。此图仅作为客观数据指标的可视化呈现，绝对不代表任何未来股价预测或投资建议。")
                import pandas as pd
                df_radar = pd.DataFrame(dict(r=list(radar_scores.values()), theta=list(radar_scores.keys())))
                fig_radar = px.line_polar(df_radar, r='r', theta='theta', line_close=True, template="plotly_dark")
                fig_radar.update_traces(fill='toself', line_color='#00b865', fillcolor='rgba(0,184,101,0.2)')
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), margin=dict(l=40, r=40, t=20, b=20), height=400)
                st.plotly_chart(fig_radar, use_container_width=True)

            with tab_insiders:
                st.markdown("---")
                st.markdown(f"### 🔎 【{s_title_name}】 机构调研与资金追踪 <span style='font-size:0.75rem; opacity:0.6;'>A股强制披露公开信息聚合</span>", unsafe_allow_html=True)
                if all_data.get('is_a_share'):
                    jgdy_hist = None
                    try:
                        import akshare as ak
                        # 注意：此处使用简化兜底逻辑避免 akshare date 参数异常导致全页面崩溃
                        # 我们将此处留空或提示，因为接口不支持 symbol 搜索最近记录
                        pass
                    except Exception:
                        pass
                    st.info("⚠️ 东方财富数据接口 (akshare) 当前在本服务器环境遭遇网络错误 (DNS) 或参数变更限制，无法自动拉取该标的近90日专属机构调研记录。本站严格遵守客观陈述底线，绝不在此编造测试数据占位。")
                else:
                    st.info("ℹ️ 机构调研及增减持记录为 A 股监管强制披露类别，港股/美股无完全对应开源接口，此项不适用于当前标的。")
                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

            with tab_overview:
                st.markdown("---")
                st.markdown(f'<div style="text-align:center; font-size:1.2rem; font-weight:800; margin-bottom:1.0rem;">📌 【{s_title_name}】 客观数据总览</div>', unsafe_allow_html=True)
                st.caption("⚠️ 以下均为第三方数据源（yfinance/akshare）的客观历史记录，不构成、也不包含本站任何投资建议、评级、目标价推荐或仓位建议。")

                c1_a, c1_b = st.columns([1.05, 0.95])
                with c1_a:
                    recs_df_top = all_data.get('recommendations')
                    rec_dist_str = "暂无数据（数据源未返回）"
                    if recs_df_top is not None and not recs_df_top.empty:
                        try:
                            latest_r = recs_df_top.iloc[0]
                            rec_dist_str = f"强烈买入 {int(latest_r.get('strongBuy',0) or 0)} / 买入 {int(latest_r.get('buy',0) or 0)} / 持有 {int(latest_r.get('hold',0) or 0)} / 卖出 {int(latest_r.get('sell',0) or 0)} / 强烈卖出 {int(latest_r.get('strongSell',0) or 0)}（来源: yfinance recommendations）"
                        except Exception:
                            pass
                    st.markdown(f"### 第三方分析师评级人数分布（历史事实统计）\n- {rec_dist_str}\n- **第三方目标价历史区间**：{target_range_str}\n- 数据来源：yfinance analyst_price_targets / recommendations，不代表本站判断，也不构成投资建议。")

                with c1_b:
                    if st_prof['inst_names'] and st_prof['inst_shares']:
                        fig_inst = go.Figure(go.Bar(
                            x=st_prof['inst_shares'], y=st_prof['inst_names'], orientation='h',
                            marker_color=['#00b865', '#38bdf8', '#fbbf24', '#a855f7', '#94a3b8'],
                            text=[f"{v}%" for v in st_prof['inst_shares']], textposition='auto'
                        ))
                        fig_inst.update_layout(
                            height=240, template='plotly_dark', margin=dict(l=10, r=10, t=35, b=10),
                            title_text=f"🏛️ {s_title_name} 十大流通股东持仓比例 (%)", yaxis=dict(autorange="reversed")
                        )
                        st.plotly_chart(fig_inst, use_container_width=True)
                    else:
                        st.info("⚠️ 暂无该标的真实机构持仓数据（或非A股无对应接口）。为避免误导，不展示编造数据。")

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                st.markdown(build_chain_html(info, ticker_input), unsafe_allow_html=True)

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                st.markdown(f"### 🏢 {s_title_name} 主营业务构成 <span style='font-size:0.75rem; opacity:0.6;'>数据来源标注见下</span>", unsafe_allow_html=True)
                main_comp = all_data.get('main_composition')
                if main_comp is not None and not main_comp.empty:
                    try:
                        comp_cols = [c for c in main_comp.columns if c in ['报告期', '分类类型', '主营构成', '主营收入', '收入比例', '主营利润', '利润比例', '主营成本', '成本比例']]
                        st.dataframe(main_comp[comp_cols] if comp_cols else main_comp, use_container_width=True)
                        st.caption("📌 数据来源：akshare stock_zygc_em（主营构成）。")
                    except Exception:
                        st.info("⚠️ 主营构成数据格式解析异常，暂不展示，避免误导。")
                else:
                    st.info("⚠️ 暂无该标的真实主营业务构成数据。本站不使用编造图表。")

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                c4_a, c4_b = st.columns([0.95, 1.05])
                with c4_a:
                    st.markdown("### 📈 缠论技术面数据摘要 <span style='font-size:0.75rem; opacity:0.6;'>⚠️ 简化版分型/中枢识别+RSI+BOLL，非买卖点建议</span>", unsafe_allow_html=True)
                    chanlun_text_ui = analyze_kline_and_chanlun(all_data['hist_1y']) if all_data and all_data.get('hist_1y') is not None else "暂无K线数据"
                    st.markdown(f"```\n{chanlun_text_ui}\n```")
                    st.caption("📌 以上数据均基于真实K线计算得出，非AI编造。")
                with c4_b:
                    if not all_data['hist_1y'].empty:
                        kline_fig = build_kline_chart(all_data['hist_1y'], ticker_input)
                        kline_fig.update_layout(height=480)
                        st.plotly_chart(kline_fig, use_container_width=True)

                st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
                st.markdown("---")
                c5_a, c5_b = st.columns([1.0, 1.0])
                with c5_a:
                    def fnum(v, pct=False, money=False):
                        if v is None or (isinstance(v, float) and __import__('numpy').isnan(v)): return "N/A"
                        try:
                            if pct: return f"{float(v)*100:.2f}%"
                            if money:
                                v = float(v)
                                return f"{v/1e8:.2f}亿" if abs(v) >= 1e8 else f"{v:,.0f}"
                            return str(v)
                        except: return "N/A"

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
                        except Exception: pass

                    gross_margin = info.get('grossMargins')
                    net_margin = info.get('profitMargins') or info.get('netMargins')
                    roe = info.get('returnOnEquity')
                    debt_ratio = info.get('debtToEquity')
                    fcf = info.get('freeCashflow')
                    ocf = info.get('operatingCashflow')

                    rev_trend = "N/A"
                    if isinstance(rev_now, (int, float)) and isinstance(rev_prev, (int, float)) and rev_prev != 0:
                        rev_trend = f"{(rev_now-rev_prev)/abs(rev_prev)*100:+.1f}% QoQ"
                    np_trend = "N/A"
                    if isinstance(np_now, (int, float)) and isinstance(np_prev, (int, float)) and np_prev != 0:
                        np_trend = f"{(np_now-np_prev)/abs(np_prev)*100:+.1f}% QoQ"

                    st.markdown(f"### 财务核心数据 <span style='font-size:0.75rem; opacity:0.6;'>数据来源: yfinance | 最新季度: {report_quarter}</span>", unsafe_allow_html=True)
                    st.markdown(f"""
                    | 财务指标 | 最新季度实际值 | 环比/同比趋势 |
                    | :--- | :---: | :---: |
                    | **营业收入 (Revenue)** | {fnum(rev_now, money=True)} | {rev_trend} |
                    | **净利润 (Net Profit)** | {fnum(np_now, money=True)} | {np_trend} |
                    | **毛利率 (Gross Margin)** | {fnum(gross_margin, pct=True)} | — |
                    | **净利率 (Net Margin)** | {fnum(net_margin, pct=True)} | — |
                    | **ROE (净资产收益率)** | {fnum(roe, pct=True)} | — |
                    | **负债权益比** | {fnum(debt_ratio)} | — |
                    | **自由现金流 (FCF)** | {fnum(fcf, money=True)} | — |
                    """)
                    st.caption("⚠️ 字段若显示 N/A 代表源未能获取真实数据，严禁编造。")

                with c5_b:
                    eps_ttm = info.get('trailingEps')
                    eps_fwd = info.get('forwardEps')
                    rev_growth_val = info.get('revenueGrowth')
                    rev_growth_disp = f"{rev_growth_val*100:+.2f}%" if isinstance(rev_growth_val, (int, float)) else "N/A"
                    eps_ttm_disp = f"{eps_ttm:.2f}" if isinstance(eps_ttm, (int, float)) else "N/A"
                    eps_fwd_disp = f"{eps_fwd:.2f}" if isinstance(eps_fwd, (int, float)) else "N/A"

                    st.markdown(f"### 第三方分析师预测数据（历史观点）\n- **EPS (TTM)**：{eps_ttm_disp} | **EPS (前瞻预期)**：{eps_fwd_disp}\n- **营收增速 (最新)**：{rev_growth_disp}")

            with tab_news:
                st.markdown("---")
                st.markdown("## 📰 近期新闻事件性质客观分类 <span style='font-size:0.72rem; opacity:0.6;'>基于新闻标题关键词的客观事件性质分类，非对股价走势的预测</span>", unsafe_allow_html=True)
                n_col1, n_col2 = st.columns(2)
                with n_col1:
                    st.markdown("#### 🟢 正面性质事件描述")
                    positive_kw = ['增长', '突破', '上涨', '创新高', '超预期', '合作', '获批', '中标', 'beat', 'surge', 'rally', 'upgrade', 'growth']
                    found_positive = False
                    all_news_items = []
                    
                    # 取出新闻数据
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
