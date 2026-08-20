import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import akshare as ak
from datetime import datetime

@st.cache_data(ttl=60, show_spinner=False)
def fetch_national_team_etfs():
    """Fetch real-time data for key broad-based ETFs commonly bought by the National Team"""
    etfs = {
        '510300.SS': '华泰柏瑞沪深300',
        '510050.SS': '华夏上证50',
        '510500.SS': '南方中证500',
        '159915.SZ': '易方达创业板',
        '159845.SZ': '华夏中证1000',
        '512890.SS': '华泰柏瑞红利'
    }
    
    results = []
    for tk, name in etfs.items():
        try:
            t = yf.Ticker(tk)
            hist = t.history(period='2d')
            if len(hist) >= 1:
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                volume = hist['Volume'].iloc[-1]
                
                chg_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0
                turnover_100m = (current_price * volume) / 100000000 # 亿元
                
                results.append({
                    '代码': tk,
                    '名称': name,
                    '当前价': current_price,
                    '涨跌幅': chg_pct,
                    '成交额(亿元)': turnover_100m
                })
        except Exception as e:
            pass
            
    return pd.DataFrame(results)

@st.cache_data(ttl=120, show_spinner=False)
def fetch_sector_fund_flow():
    """Fetch real-time sector fund flow from akshare"""
    try:
        df = ak.stock_fund_flow_industry(symbol='即时')
        # columns: 序号, 行业, 行业指数, 行业-涨跌幅, 流入资金, 流出资金, 净额, 公司家数, 领涨股, 领涨股-涨跌幅, 当前价
        
        def parse_amount(val):
            if isinstance(val, str):
                val = val.replace('亿', '').replace('万', '').strip()
                try:
                    return float(val)
                except:
                    return 0
            return float(val) if pd.notnull(val) else 0
            
        if '净额' in df.columns:
            df['净流入(亿元)'] = df['净额'].apply(parse_amount)
            df['绝对净流入'] = df['净流入(亿元)'].abs()
            
            # Clean up percentage
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
        st.caption("实时监控核心宽基 ETF 成交额异常放大，捕捉神秘资金进场信号。")
        
        df_etf = fetch_national_team_etfs()
        if not df_etf.empty:
            cols = st.columns(len(df_etf))
            for i, row in df_etf.iterrows():
                with cols[i]:
                    chg = row['涨跌幅']
                    turnover = row['成交额(亿元)']
                    
                    # 异动判定：假设单日成交额大于 30 亿视为异动 (简化逻辑)
                    alert = "🔥 异动爆量" if turnover > 30 else ""
                    
                    color = "normal"
                    if chg > 0: color = "normal" # Streamlit metric green
                    elif chg < 0: color = "inverse" # Streamlit metric red? wait, delta_color="normal" handles +/-
                    
                    st.metric(
                        label=f"{row['名称']} {alert}",
                        value=f"{turnover:.2f} 亿",
                        delta=f"{chg:.2f}%",
                        delta_color="normal" if chg >= 0 else "normal" # Default green up red down
                    )
        else:
            st.warning("暂无 ETF 数据")
            
        st.markdown("---")
        st.markdown("### 🗺️ 全市场行业主力资金净流入热力图 (Treemap)")
        st.caption("方块大小代表资金活跃度(净额绝对值)，绿色代表净流入，红色代表净流出。点击可下钻或悬停查看详情。")
        
        df_sector = fetch_sector_fund_flow()
        if not df_sector.empty and '行业' in df_sector.columns:
            # Prepare data for Treemap
            df_sector['板块'] = 'A股全市场'
            
            # Create a custom colorscale where Negative is Red (#ef4444) and Positive is Green (#00b865)
            # Center it at 0
            max_val = df_sector['净流入(亿元)'].abs().max()
            if max_val == 0: max_val = 1
            
            fig = px.treemap(
                df_sector,
                path=['板块', '行业'],
                values='绝对净流入',
                color='净流入(亿元)',
                color_continuous_scale=[[0, '#ef4444'], [0.5, '#262730'], [1, '#00b865']],
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
            
            fig.update_traces(
                texttemplate="<b>%{label}</b><br>净额: %{customdata[0]:.2f}亿<br>涨幅: %{customdata[1]:.2f}%",
                hovertemplate="<b>%{label}</b><br>净流入: %{customdata[0]:.2f}亿<br>行业涨跌: %{customdata[1]:.2f}%<br>领涨龙头: %{customdata[2]}<extra></extra>"
            )
            
            fig.update_layout(
                margin=dict(t=10, l=10, r=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=500,
                coloraxis_colorbar=dict(
                    title="净流入(亿)",
                    thicknessmode="pixels", thickness=15,
                    lenmode="pixels", len=300,
                    yanchor="top", y=1,
                    ticks="outside"
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, key="macro_treemap")
        else:
            st.info("当前时段暂无行业资金流向数据。")
