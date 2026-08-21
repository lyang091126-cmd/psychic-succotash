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
    
    # 优先使用 akshare 获取实时行情 (EM 接口)
    ak_data = {}
    try:
        df_spot = ak.fund_etf_spot_em()
        if df_spot is not None and not df_spot.empty:
            for _, row in df_spot.iterrows():
                code = str(row.get('代码', ''))
                if code:
                    ak_data[code] = {
                        'current_price': float(row.get('最新价', 0)) if row.get('最新价') is not None else 0.0,
                        'chg_pct': float(row.get('涨跌幅', 0)) if row.get('涨跌幅') is not None else 0.0,
                        'turnover_100m': float(row.get('成交额', 0)) / 1e8 if row.get('成交额') else 0.0
                    }
    except Exception:
        pass

    def get_etf(tk, name):
        code = tk.split('.')[0]
        current_price = None
        chg_pct = None
        turnover_100m = None

        # 优先从 akshare 提取
        if code in ak_data:
            current_price = ak_data[code]['current_price']
            chg_pct = ak_data[code]['chg_pct']
            turnover_100m = ak_data[code]['turnover_100m']

        # 如果 akshare 数据缺失，或者为0/NaN，降级使用 yfinance
        if current_price is None or pd.isna(current_price) or current_price == 0:
            try:
                t = yf.Ticker(tk)
                hist = t.history(period='5d')
                if len(hist) >= 1:
                    current_price = float(hist['Close'].iloc[-1])
                    if len(hist) >= 2:
                        prev_close = float(hist['Close'].iloc[-2])
                        chg_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0
                    else:
                        chg_pct = 0.0
                    volume = float(hist['Volume'].iloc[-1])
                    turnover_100m = (current_price * volume) / 1e8
            except Exception:
                pass

        if current_price is not None and not pd.isna(current_price):
            # 获取主力净流入 (通过东财接口)
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

            return {
                '代码': tk,
                '名称': name,
                '当前价': current_price,
                '涨跌幅': chg_pct if chg_pct is not None else 0.0,
                '成交额(亿元)': turnover_100m if turnover_100m is not None else 0.0,
                '主力净流入(亿元)': net_inflow_100m
            }
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
    # 优先采用官方 JSON 数据接口，防网页 DOM 变化导致 HTML 解析崩溃 (P2 & P1)
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日")
        if df is not None and not df.empty:
            df = df.rename(columns={
                '名称': '行业',
                '今日主力净流入-净额': '净流入(亿元)',
                '今日涨跌幅': '涨跌幅',
            })
            if '净流入(亿元)' in df.columns:
                df['净流入(亿元)'] = df['净流入(亿元)'].apply(lambda x: round(float(x) / 1e8, 2) if pd.notnull(x) else 0.0)
            else:
                net_col = [c for c in df.columns if '主力净流入-净额' in c or '净流入' in c]
                if net_col:
                    df['净流入(亿元)'] = df[net_col[0]].apply(lambda x: round(float(x) / 1e8, 2) if pd.notnull(x) else 0.0)
                else:
                    df['净流入(亿元)'] = 0.0
            
            chg_col = [c for c in df.columns if '涨跌幅' in c or '涨跌' in c]
            if chg_col:
                df['涨跌幅'] = df[chg_col[0]].apply(lambda x: round(float(str(x).replace('%', '').strip()), 2) if (pd.notnull(x) and str(x).strip() != '?') else 0.0)
            else:
                df['涨跌幅'] = 0.0

            df['绝对净流入'] = df['净流入(亿元)'].abs()
            df['领涨股'] = df.get('今日领涨股票', 'N/A')
            return df
    except Exception:
        pass

    # 备用降级逻辑 1
    try:
        df = ak.stock_fund_flow_industry(symbol='即时')
        def parse_amount(val):
            if isinstance(val, str):
                val = val.replace('亿', '').replace('万', '').strip()
                try: return float(val)
                except: return 0.0
            return float(val) if pd.notnull(val) else 0.0
        if df is not None and not df.empty:
            if '净额' in df.columns:
                df['净流入(亿元)'] = df['净额'].apply(parse_amount)
                df['净流入(亿元)'] = df['净流入(亿元)'].apply(lambda x: round(float(x), 2) if pd.notnull(x) else 0.0)
                df['绝对净流入'] = df['净流入(亿元)'].abs()
            else:
                df['净流入(亿元)'] = 0.0
                df['绝对净流入'] = 0.0
                
            if '行业-涨跌幅' in df.columns:
                df['涨跌幅'] = df['行业-涨跌幅'].astype(str).str.replace('%', '').str.strip()
                df['涨跌幅'] = df['涨跌幅'].apply(lambda x: round(float(x), 2) if (pd.notnull(x) and x != '?' and x != 'nan' and x != '') else 0.0)
            else:
                df['涨跌幅'] = 0.0
            return df
    except Exception:
        pass

    return pd.DataFrame()

def render_macro_capital_board():
    with st.expander("🌊 宏观资金面监控室 (Macro Capital Flows)", expanded=True):
        st.markdown("### 📊 核心宽基 ETF 资金异动监控")
        st.caption("实时监控核心宽基 ETF 成交额异常放大，捕捉主力/神秘资金大单进场与护盘交易信号。")
        
        df_etf = fetch_national_team_etfs()
        if not df_etf.empty:
            # Top metrics for the top 5 ETFs by Turnover
            top5 = df_etf.sort_values(by='成交额(亿元)', ascending=False).head(5)
            cols = st.columns(len(top5))
            for i, row in top5.reset_index().iterrows():
                with cols[i]:
                    chg = row['涨跌幅']
                    turnover = row['成交额(亿元'] if '成交额(亿元' in row else row.get('成交额(亿元)')
                    alert = "🔥 异动爆量" if turnover > 30 else ""
                    
                    st.metric(
                        label=f"{row['名称']} {alert}",
                        value=f"{turnover:.2f} 亿",
                        delta=f"{chg:.2f}%",
                        delta_color="normal"
                    )
            
            st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
            
            # P6: 柱状图逻辑彻底改回以“成交额 (亿元)”为轴进行排行，恢复高可读性
            metric_x = '成交额(亿元)'
            title_suffix = "成交额"
            hover_data = {
                '成交额(亿元)': ':.2f',
                '涨跌幅': ':.2f',
                '名称': False,
                '颜色': False
            }
            custom_data = ['涨跌幅', '当前价', '成交额(亿元)']

            df_etf_sorted = df_etf.sort_values(by=metric_x, ascending=True) # Ascending for horizontal bar
            if '涨跌幅' in df_etf_sorted.columns:
                df_etf_sorted['颜色'] = df_etf_sorted['涨跌幅'].apply(lambda x: '#ef4444' if pd.notnull(x) and x >= 0 else '#00b865')
            else:
                df_etf_sorted['颜色'] = df_etf_sorted[metric_x].apply(lambda x: '#ef4444' if x > 0 else '#00b865')
            
            fig_etf = px.bar(
                df_etf_sorted,
                x=metric_x,
                y='名称',
                orientation='h',
                color='颜色',
                color_discrete_map='identity',
                title=f"📈 核心宽基 ETF {title_suffix} 排行 (亿元)",
                hover_data=hover_data,
                custom_data=custom_data
            )
            
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
                xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                bargap=0.2
            )
            st.plotly_chart(fig_etf, use_container_width=True, key="macro_etf_barchart")
            
        else:
            st.warning("暂无 ETF 数据")
            
        st.markdown("---")
        st.markdown("### 🗺️ 全市场行业主力资金净流入热力图 (Treemap)")
        st.caption("方块大小代表资金活跃度(净额绝对值)，红色代表净流入，绿色代表净流出。点击可下钻或悬停查看详情。")
        
        df_sector = fetch_sector_fund_flow()
        if not df_sector.empty and '行业' in df_sector.columns:
            # P5: 过滤掉净额绝对值过小的尾部行业，只保留主力核心大行业，避免极小区块挤压字号而无法显示文字
            df_sector = df_sector.sort_values(by='绝对净流入', ascending=False)
            df_sector = df_sector[df_sector['绝对净流入'] >= 1.0].head(25)
            
            if not df_sector.empty:
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
                
                try:
                    fig_tree.update_traces(
                        textinfo="label+value+percent parent",
                        texttemplate="<b>%{label}</b><br>净额: %{customdata[0]:.2f}亿<br>涨幅: %{customdata[1]:+.2f}%",
                        textfont=dict(size=26, family="Arial, sans-serif"),  # 将大区块字号基准拉高至 26px
                        textposition="middle center",
                        hovertemplate="<b>%{label}</b><br>净流入: %{customdata[0]:.2f}亿<br>行业涨跌: %{customdata[1]:.2f}%<br>领涨龙头: %{customdata[2]}<extra></extra>",
                        marker=dict(cornerradius=4, pad=dict(t=2, l=2, r=2, b=2), line=dict(color='#0A0D14', width=2))
                    )
                except Exception:
                    try:
                        fig_tree.update_traces(
                            textinfo="label+value",
                            textfont=dict(size=26, family="Arial, sans-serif"),
                            textposition="middle center",
                            marker=dict(cornerradius=4, pad=dict(t=2, l=2, r=2, b=2), line=dict(color='#0A0D14', width=2))
                        )
                    except Exception:
                        pass
                
                fig_tree.update_layout(
                    font=dict(family="Inter, Roboto, 'Microsoft YaHei', sans-serif"),
                    uniformtext=dict(
                        minsize=11,  # 设定字号下限为 11px
                        mode='hide'  # 小于 11px 的微小区块自动隐藏文字，避免拖累大区块
                    ),
                    height=650,  # 确保给热力图充裕的垂直空间
                    margin=dict(l=10, r=10, t=35, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
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
                st.warning("当前时段接口维护，资金流数据暂缓更新")
        else:
            st.warning("当前时段接口维护，资金流数据暂缓更新")
            
        # P6: 新增：过往 30 天主力资金净流入/流出趋势图
        st.markdown("---")
        st.markdown("### 📊 核心宽基 ETF 近 30 日主力资金流向趋势")
        st.caption("基于每日成交额与价格涨跌幅权重估算的主力资金流入/流出趋势。")
        
        etf_choice = st.selectbox("选择要查看趋势的 ETF", ["510300.SS (华泰柏瑞沪深300 ETF)", "588000.SS (华夏科创50 ETF)"])
        etf_tk = etf_choice.split(" ")[0]
        
        try:
            # 抓取 45 天数据以保证获取 30 个交易日
            t_etf = yf.Ticker(etf_tk)
            hist_etf = t_etf.history(period="45d")
            if not hist_etf.empty and len(hist_etf) >= 2:
                hist_etf['Prev_Close'] = hist_etf['Close'].shift(1)
                hist_etf['chg_pct'] = (hist_etf['Close'] - hist_etf['Prev_Close']) / hist_etf['Prev_Close']
                hist_etf['turnover'] = hist_etf['Close'] * hist_etf['Volume'] / 1e8
                
                # 资金流向粗略估算算法
                hist_etf['net_flow'] = hist_etf['turnover'] * hist_etf['chg_pct'] * 4.0
                hist_etf['net_flow'] = hist_etf.apply(lambda r: np.clip(r['net_flow'], -0.2 * r['turnover'], 0.2 * r['turnover']), axis=1)
                hist_etf = hist_etf.dropna().tail(30)
                
                df_trend = pd.DataFrame({
                    '日期': [d.strftime('%m-%d') for d in hist_etf.index],
                    '净流入(亿元)': hist_etf['net_flow'].values
                })
                
                # 水平线上方红色，水平线下方绿色
                colors_trend = ['#ef4444' if val >= 0 else '#00b865' for val in df_trend['净流入(亿元)']]
                
                fig_trend = go.Figure(go.Bar(
                    x=df_trend['日期'],
                    y=df_trend['净流入(亿元)'],
                    marker_color=colors_trend,
                    name="估算主力净流入"
                ))
                
                fig_trend.update_layout(
                    height=280,
                    margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    template='plotly_dark',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="净额 (亿元)")
                )
                
                st.plotly_chart(fig_trend, use_container_width=True, key=f"flow_trend_{etf_tk}")
            else:
                st.info("暂无足够的历史日线数据来估算资金流趋势。")
        except Exception as e:
            st.info(f"资金流量趋势计算暂缓: {e}")
