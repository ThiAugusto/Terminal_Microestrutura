import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA & ESTILO
# ==========================================
st.set_page_config(page_title="Terminal Quant | Microestrutura", layout="wide", initial_sidebar_state="expanded")

bg_app = "#050505"
bg_card = "#111111"
border_color = "#333333"
text_main = "#F5F5F5"
text_highlight = "#FF9800"

st.markdown(f"""
    <style>
    [data-testid="stHeader"] {{ background-color: transparent !important; }}
    .block-container {{ padding-top: 1rem !important; padding-bottom: 1rem !important; }}
    [data-testid="stSidebar"] {{ background-color: {bg_card} !important; border-right: 1px solid {border_color} !important; }}
    .stApp {{ background-color: {bg_app}; color: {text_main} !important; font-family: 'Segoe UI', sans-serif; }}
    div[data-testid="metric-container"] {{ 
        background-color: {bg_card}; border: 1px solid {border_color}; padding: 15px; 
        border-radius: 8px; box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.4);
    }}
    div[data-testid="metric-container"] label {{ color: {text_highlight} !important; font-weight: bold; font-size: 1rem; }}
    div[data-testid="stMetricValue"] {{ color: {text_main} !important; }}
    h1, h2, h3, h4 {{ color: {text_main} !important; }}
    .insight-box {{ background-color: {bg_card}; padding: 20px; border-left: 6px solid {text_highlight}; border-radius: 6px; line-height: 1.6; color: {text_main} !important; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BARRA LATERAL DE CONFIGURAÇÃO
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Parâmetros do HFT")
    simbolo = st.selectbox("Ativo / Par", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
    limite_ticks = st.slider("Janela de Ticks (Time & Sales)", 500, 1000, 1000, step=100)
    st.markdown("---")
    st.markdown("### 📊 Indicadores Ativos")
    show_vwap = st.checkbox("VWAP & Bandas de Desvio", value=True)
    show_va = st.checkbox("Value Area (70%) & VPOC", value=True)
    show_icebergs = st.checkbox("Detector de Icebergs (Absorção)", value=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("Desenvolvido para Portfólio Quantitativo • Dados API Binance HFT")

# ==========================================
# 3. MOTOR DE DADOS BLINDADO (COM TIMEOUT)
# ==========================================
@st.cache_data(ttl=10)
def carregar_dados_microestrutura(symbol, limit):
    url = f"https://data-api1.binance.com/api/v3/trades?symbol={symbol}&limit={limit}"
    try:
        # Timeout de 6 segundos para evitar travamentos na nuvem
        resposta = requests.get(url, timeout=6)
        if resposta.status_code != 200:
            return pd.DataFrame()
            
        dados = resposta.json()
        if not isinstance(dados, list) or len(dados) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(dados)
        df['price'] = df['price'].astype(float)
        df['qty'] = df['qty'].astype(float)
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        
        # Agressão Direcional
        df['agressor'] = np.where(df['isBuyerMaker'], 'Vendedor', 'Comprador')
        df['vol_compra'] = np.where(df['agressor'] == 'Comprador', df['qty'], 0)
        df['vol_venda'] = np.where(df['agressor'] == 'Vendedor', df['qty'], 0)
        df['delta'] = df['vol_compra'] - df['vol_venda']
        df['cvd'] = df['delta'].cumsum()
        
        # VWAP e Bandas
        df['pv'] = df['price'] * df['qty']
        df['vwap'] = df['pv'].cumsum() / df['qty'].cumsum()
        rolling_std = df['price'].rolling(window=50, min_periods=10).std()
        df['vwap_up'] = df['vwap'] + (rolling_std * 1.2)
        df['vwap_down'] = df['vwap'] - (rolling_std * 1.2)
        
        # Caçador de Icebergs
        q98 = df['qty'].quantile(0.98)
        df['preco_diff'] = df['price'].diff().abs()
        df['iceberg_compra'] = (df['qty'] >= q98) & (df['agressor'] == 'Comprador') & (df['preco_diff'] <= df['price'].mean() * 0.0001)
        df['iceberg_venda'] = (df['qty'] >= q98) & (df['agressor'] == 'Vendedor') & (df['preco_diff'] <= df['price'].mean() * 0.0001)
        
        return df
    except Exception as e:
        return pd.DataFrame()

with st.spinner(f"A capturar fluxo institucional de {simbolo}..."):
    df = carregar_dados_microestrutura(simbolo, limite_ticks)

if df.empty:
    st.error("⚠️ Erro temporário ao comunicar com a Binance ou dados vazios. Por favor, clique em 'Rerun' no canto superior direito.")
    st.stop()

# ==========================================
# 4. CABEÇALHO E MÉTRICAS
# ==========================================
st.title("🔬 TERMINAL DE MICROESTRUTURA & ORDER FLOW")
st.markdown(f"**Análise de Agressão Tick-a-Tick, Perfil de Volume e Detecção de Liquidez Oculta ({simbolo})**")
st.divider()

preco_atual = df['price'].iloc[-1]
vol_compra = df['vol_compra'].sum()
vol_venda = df['vol_venda'].sum()
saldo_delta = vol_compra - vol_venda
num_icebergs = df['iceberg_compra'].sum() + df['iceberg_venda'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Último Preço Negociado", f"${preco_atual:,.2f}")
col2.metric("Agressão Compradora", f"{vol_compra:,.2f}", "Força Taker Buy")
col3.metric("Agressão Vendedora", f"{vol_venda:,.2f}", "Força Taker Sell")
col4.metric("Saldo Delta (CVD)", f"{saldo_delta:,.2f}", delta_color="normal" if saldo_delta > 0 else "inverse")
st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. VOLUME PROFILE COM TRAVA DE SEGURANÇA
# ==========================================
tick_size = max(0.5, preco_atual * 0.0002)
df['price_bin'] = (df['price'] // tick_size) * tick_size
vol_profile = df.groupby('price_bin')['qty'].sum().sort_index()
vpoc_price = vol_profile.idxmax()

total_vol = vol_profile.sum()
target_vol = total_vol * 0.70
va_vol = vol_profile.loc[vpoc_price]
val, vah = vpoc_price, vpoc_price
prices = vol_profile.index.tolist()

# Laço seguro com limite máximo de iterações para evitar loop infinito
iteracoes = 0
while va_vol < target_vol and iteracoes < len(prices):
    idx_val = prices.index(val)
    idx_vah = prices.index(vah)
    vol_down = vol_profile.iloc[idx_val - 1] if idx_val > 0 else 0
    vol_up = vol_profile.iloc[idx_vah + 1] if idx_vah < len(prices) - 1 else 0
    if vol_down == 0 and vol_up == 0: break
    if vol_down >= vol_up:
        val = prices[idx_val - 1]
        va_vol += vol_down
    else:
        vah = prices[idx_vah + 1]
        va_vol += vol_up
    iteracoes += 1

# ==========================================
# 6. CONSTRUÇÃO DO GRÁFICO PLOTLY
# ==========================================
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, row_heights=[0.75, 0.25],
                    subplot_titles=("Ação do Preço & Camadas Institucionais", "Cumulative Volume Delta (CVD)"))

fig.add_trace(go.Scatter(x=df['time'], y=df['price'], mode='lines', name='Preço', line=dict(color='#E0E0E0', width=1.2)), row=1, col=1)

if show_vwap:
    fig.add_trace(go.Scatter(x=df['time'], y=df['vwap'], mode='lines', name='VWAP', line=dict(color='#FF9800', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['vwap_up'], mode='lines', name='Banda Superior (+1.2σ)', line=dict(color='rgba(255,152,0,0.2)', width=1, dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['vwap_down'], mode='lines', name='Banda Inferior (-1.2σ)', line=dict(color='rgba(255,152,0,0.2)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(255,152,0,0.04)'), row=1, col=1)

if show_va:
    fig.add_hrect(y0=val, y1=vah, line_width=0, fillcolor="#42A5F5", opacity=0.10, row=1, col=1, annotation_text=" Value Area (70%)", annotation_position="top left", annotation_font_color="#42A5F5")
    fig.add_hline(y=vpoc_price, line_dash="dash", line_color="#FFB300", line_width=1.5, row=1, col=1, annotation_text=f" VPOC: ${vpoc_price:,.2f}", annotation_font_color="#FFB300")

if show_icebergs:
    ice_c = df[df['iceberg_compra']]
    ice_v = df[df['iceberg_venda']]
    if not ice_c.empty:
        fig.add_trace(go.Scatter(x=ice_c['time'], y=ice_c['price'], mode='markers', name='⚠️ Iceberg (Compra)', marker=dict(color='#00FFFF', size=11, symbol='hexagon')), row=1, col=1)
    if not ice_v.empty:
        fig.add_trace(go.Scatter(x=ice_v['time'], y=ice_v['price'], mode='markers', name='⚠️ Iceberg (Venda)', marker=dict(color='#FF00FF', size=11, symbol='hexagon')), row=1, col=1)

cor_cvd = '#00E676' if saldo_delta > 0 else '#FF1744'
fig.add_trace(go.Scatter(x=df['time'], y=df['cvd'], mode='lines', fill='tozeroy', name='CVD', line=dict(color=cor_cvd, width=2.5)), row=2, col=1)

fig.update_layout(
    template='plotly_dark',
    height=720,
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. PAINEL DE INSIGHTS
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div class="insight-box">
    <h4 style="margin-top:0px; color: #FF9800;">💡 Notas de Execução do Algoritmo & Leitura Quantitativa</h4>
    • <b>Zonas de Equilíbrio (VPOC & VA):</b> O preço tende a gravitar em torno do VPOC (${vpoc_price:,.2f}). Rompimentos fora da faixa azul (Value Area entre ${val:,.2f} e ${vah:,.2f}) acompanhados de divergência no CVD indicam exaustão ou expansão direcional.<br>
    • <b>Absorção Institucional (Icebergs):</b> Foram detetados <b>{num_icebergs} blocos de ordens ocultas</b> onde o volume negociado superou o percentil 98 sem deslocamento proporcional do preço, sinalizando defesa passiva de grandes *players*.<br>
    • <b>Stack Tecnológico:</b> Desenvolvido em Python com ingestão de dados em tempo real via Binance REST API, processamento vetorizado em Pandas/NumPy e renderização interativa via Plotly/Streamlit.
</div>
""", unsafe_allow_html=True)
