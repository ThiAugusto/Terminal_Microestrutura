import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    st.caption("Desenvolvido para Portfólio Quantitativo • Mock Data")

# ==========================================
# 3. MOTOR QUANTITATIVO (MODO PORTFÓLIO FORÇADO)
# ==========================================
@st.cache_data(ttl=10)
def carregar_dados_microestrutura(symbol, limit):
    # DADOS SIMULADOS PARA CONTORNAR O BLOQUEIO DE IP DA NUVEM
    np.random.seed(np.random.randint(0, 1000))
    tempos = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq='100ms')
    base_price = 90000 if symbol == "BTCUSDT" else (3000 if symbol == "ETHUSDT" else 150)
    precos_simulados = base_price + np.cumsum(np.random.normal(0, base_price * 0.0001, limit))
    quantidades = np.random.exponential(0.1, limit) + 0.001
    is_buyer_maker = np.random.choice([True, False], limit)
    
    df = pd.DataFrame({
        'price': precos_simulados,
        'qty': quantidades,
        'time': tempos,
        'isBuyerMaker': is_buyer_maker
    })
        
    df['agressor'] = np.where(df['isBuyerMaker'], 'Vendedor', 'Comprador')
    df['vol_compra'] = np.where(df['agressor'] == 'Comprador', df['qty'], 0)
    df['vol_venda'] = np.where(df['agressor'] == 'Vendedor', df['qty'], 0)
    df['delta'] = df['vol_compra'] - df['vol_venda']
    df['cvd'] = df['delta'].cumsum()
    
    df['pv'] = df['price'] * df['qty']
    df['vwap'] = df['pv'].cumsum() / df['qty'].cumsum()
    rolling_std = df['price'].rolling(window=50, min_periods=10).std()
    df['vwap_up'] = df['vwap'] + (rolling_std * 1.2)
    df['vwap_down'] = df['vwap'] - (rolling_std * 1.2)
    
    q98 = df['qty'].quantile(0.98)
    df['preco_diff'] = df['price'].diff().abs()
    df['iceberg_compra'] = (df['qty'] >= q98) & (df['agressor'] == 'Comprador') & (df['preco_diff'] <= df['price'].mean() * 0.0001)
    df['iceberg_venda'] = (df['qty'] >= q98) & (df['agressor'] == 'Vendedor') & (df['preco_diff'] <= df['price'].mean() * 0.0001)
    
    return df

with st.spinner(f"A carregar motor quantitativo para {simbolo}..."):
    df = carregar_dados_microestrutura(simbolo, limite_ticks)

# ==========================================
# 4. CABEÇALHO E MÉTRICAS
# ==========================================
st.title("🔬 TERMINAL DE MICROESTRUTURA & ORDER FLOW")
st.warning("⚠️ Modo Portfólio Ativo: A usar motor quantitativo de simulação de alta fidelidade para contornar bloqueios da corretora.")
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
# 5. VOLUME PROFILE COM TRAVA
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

iteracoes = 0
while va_vol < target_vol and iteracoes < len(prices):
    idx_val = prices.index(val)
