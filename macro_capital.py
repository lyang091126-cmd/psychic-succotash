import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import akshare as ak
from datetime import datetime
import concurrent.futures
import requests

@st.cache_data(ttl=60, show_spinner=False)
def fetch_national_team_etfs():
    """Fetch real-time data for key broad-based ETFs commonly bought by the National Team"""
    etfs = {
        '510300.SS': '华泰柏瑞沪深300', '510050.SS': '华夏上证50',
        '510500.SS': '南方中证500', '159915.SZ': '易方达创业板',
        '159845.SZ': '华夏中证1000', '512890.SS': '华泰红利',
        '510310.SS': '易方达沪深300', '159919.SZ': '嘉实沪深300',
        '510330.SS': '华夏沪深300', '588000.SS': '华夏科创50',
        '588090.SS': '易方达科创50', '159949.SZ': '华夏创业板50',
        '512100.SS': '南方中证1000', '159852.SZ': '广发中证1000',
        '512000.SS': '华宝券商ETF', '512800.SS': '华宝银行ETF'
    }
    
    def get_etf(tk, name):
        try:
            # yfinance fetch for standard OHLCV
            t = yf.Ticker(tk)
            hist = t.history(period='2d')
            if len(hist) >= 1:
                current_price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                volume = float(hist['Volume'].iloc[-1])
                
                chg_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0
                turnover_100m = (current_price * volume) / 100000000 # 亿元
                
                # Eastmoney fetch for Main Force Net Inflow (主力净流入)
                code = tk.split('.')[0]
                secid = f"1.{code}" if tk.endswith('.SS') else f"0.{code}"
                url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f137"
                net_inflow_100m = 0.0
                try:
                    r = requests.get(url, timeout=2).json()
                    if r and 'data' in r and r['data']:
                        f137 = r['data'].get('f137')
                        if f137 and f137 != '-':
                            net_inflow_100m = float(f137) / 100000000.0
                except Exception:
                    pass
                
                if turnover_100m > 0:
                    return {
                        '代码': tk,
                        '名称': name,
                        '当前价': current_price,
                        '涨跌幅': chg_pct,
                        '成交额(亿元)': turnover_100m,
                        '主力净流入(亿元)': net_inflow_100m
                    }
        except Exception:
            pass
        return None

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_etf, tk, name): tk for tk, name in etfs.items()}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
            
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values(by='主力净流入(亿元)', ascending=False)
    return df

@st.cache_data(ttl=120, show_spinner=False)
def fetch_sector_fund_flow():
    """Fetch real-time sector fund flow from akshare"""
    try:
        df = ak.stock_fund_flow_industry(symbol='即时')
        def parse_amount(val):
            if isinstance(val, str):
                val = val.replace('亿', '').replace('万', '').strip()
                try: return float(val)
                except: return 0
            return float(val) if pd.notnull(val) else 0
        if '净额' in df.columns:
            df['净流入(亿元)'] = df['净额'].apply(parse_amount)
            df['绝对净流入'] = df['净流入(亿元)'].abs()
            if '行业-涨跌幅' in df.columns:
                df['涨跌幅'] = df['行业-涨跌幅'].astype(str).str.replace('%', '').astype(float)
            else:
                df['涨跌幅'] = 0.0
            return df
    except Exception as e:
        st.error(f"行业资金流向获取失败: {e}")
    return pd.DataFrame()

def render_macro_capital_board():
    with st.expander("🌊 宏观资金面监控室 (Macro Capital Flows)", expanded=True):
        st.markdown("### 🛡️ 国家队 (中央汇金) 护盘先锋监控")
        st.caption("实时监控核心宽基 ETF 成交额异常放大及主力资金净流入（大单+超大单差额），捕捉神秘资金进场信号。")
        
        df_etf = fetch_national_team_etfs()
        if not df_etf.empty:
            # Top metrics for the top 5 ETFs by Turnover (Turnover is still good for Metrics)
            top5 = df_etf.sort_values(by='成交额(亿元)', ascending=False).head(5)
            cols = st.columns(len(top5))
            for i, row in top5.reset_index().iterrows():
                with cols[i]:
                    chg = row['涨跌幅']
                    turnover = row['成交额(亿元)']
                    alert = "🔥 异动爆量" if turnover > 30 else ""
                    
                    st.metric(
                        label=f"{row['名称']} {alert}",
                        value=f"{turnover:.2f} 亿",
                        delta=f"{chg:.2f}%",
                        delta_color="normal"
                    )
            
            st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
            
            # Bar chart for ALL tracked ETFs based on Main Force Net Inflow OR Turnover
            # Fallback to turnover if Eastmoney net inflow API fails
            if '主力净流入(亿元)' in df_etf.columns and df_etf['主力净流入(亿元)'].abs().sum() == 0:
                metric_x = '成交额(亿元)'
                title_suffix = "成交额"
                hover_data = {
                    '成交额(亿元)': ':.2f',
                    '涨跌幅': ':.2f',
                    '名称': False,
                    '颜色': False
                }
                custom_data = ['涨跌幅', '当前价', '成交额(亿元)']
            else:
                metric_x = '主力净流入(亿元)'
                title_suffix = "主力资金净流入 (大单+超大单)"
                hover_data = {
                    '主力净流入(亿元)': ':.2f',
                    '成交额(亿元)': ':.2f',
                    '涨跌幅': ':.2f',
                    '名称': False,
                    '颜色': False
                }
                custom_data = ['涨跌幅', '当前价', '成交额(亿元)', '主力净流入(亿元)']

            df_etf_sorted = df_etf.sort_values(by=metric_x, ascending=True) # Ascending for horizontal bar
            df_etf_sorted['颜色'] = df_etf_sorted[metric_x].apply(lambda x: '#FF4B4B' if x > 0 else '#00E676')
            
            fig_etf = px.bar(
                df_etf_sorted,
                x=metric_x,
                y='名称',
                orientation='h',
                color='颜色',
                color_discrete_map='identity',
                title=f"📈 核心宽基 ETF {title_suffix} (亿元)",
                hover_data=hover_data,
                custom_data=custom_data
            )
            
            if metric_x == '主力净流入(亿元)':
                fig_etf.update_traces(
                    hovertemplate="<b>%{y}</b><br>主力净流入: %{customdata[3]:.2f}亿<br>总成交额: %{customdata[2]:.2f}亿<br>涨跌幅: %{customdata[0]:.2f}%<br>现价: %{customdata[1]:.3f}<extra></extra>"
                )
            else:
                fig_etf.update_traces(
                    hovertemplate="<b>%{y}</b><br>总成交额: %{customdata[2]:.2f}亿<br>涨跌幅: %{customdata[0]:.2f}%<br>现价: %{customdata[1]:.3f}<extra></extra>"
                )
                
            fig_etf.update_layout(
                margin=dict(t=40, l=10, r=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                showlegend=False,
                xaxis_title=f"{title_suffix} (亿元)",
                yaxis_title="",
                xaxis=dict(gridcolor='rgba(255,255,255,0.1)')
            )
            st.plotly_chart(fig_etf, use_container_width=True, key="macro_etf_barchart")
            
        else:
            st.warning("暂无 ETF 数据")
            
        st.markdown("---")
        st.markdown("### 🗺️ 全市场行业主力资金净流入热力图 (Treemap)")
        st.caption("方块大小代表资金活跃度(净额绝对值)，红色代表净流入，绿色代表净流出。点击可下钻或悬停查看详情。")
        
        df_sector = fetch_sector_fund_flow()
        if not df_sector.empty and '行业' in df_sector.columns:
            df_sector['板块'] = 'A股全市场'
            fig_tree = px.treemap(
                df_sector,
                path=['板块', '行业'],
                values='绝对净流入',
                color='净流入(亿元)',
                color_continuous_scale=[[0, '#00E676'], [0.5, '#262730'], [1, '#FF4B4B']],
                color_continuous_midpoint=0,
                hover_data={
                    '净流入(亿元)': ':.2f',
                    '涨跌幅': ':.2f',
                    '领涨股': True,
                    '绝对净流入': False,
                    '板块': False
                },
                custom_data=['净流入(亿元)', '涨跌幅', '领涨股']
            )
            
            fig_tree.update_traces(
                textfont=dict(family="Inter, Roboto, 'Microsoft YaHei', sans-serif"),
                texttemplate="<b>%{label}</b><br>净额: %{customdata[0]:.2f}亿<br>涨幅: %{customdata[1]:.2f}%",
                hovertemplate="<b>%{label}</b><br>净流入: %{customdata[0]:.2f}亿<br>行业涨跌: %{customdata[1]:.2f}%<br>领涨龙头: %{customdata[2]}<extra></extra>"
            )
            
            fig_tree.update_layout(
                font=dict(family="Inter, Roboto, 'Microsoft YaHei', sans-serif"),
                uniformtext=dict(minsize=10, mode='hide'),
                height=700,
                width=None,
                margin=dict(l=40, r=40, t=60, b=40),
                title_font_size=20,
                xaxis=dict(tickangle=-45, tickfont=dict(size=11)),
                yaxis=dict(tickfont=dict(size=11)),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                coloraxis_colorbar=dict(
                    title="净流入(亿)",
                    thicknessmode="pixels", thickness=15,
                    lenmode="pixels", len=300,
                    yanchor="top", y=1,
                    ticks="outside"
                )
            )
            st.plotly_chart(fig_tree, use_container_width=True, key="macro_treemap")
        else:
            st.info("当前时段暂无行业资金流向数据。")
