import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Quant Master Builder", layout="wide")

# ==========================================
# SIDEBAR: CONFIGURAÇÕES
# ==========================================
st.sidebar.title("⚙️ Painel de Controle")
ativo_input = st.sidebar.text_input("Ativos (separados por vírgula)", "NQ=F, ES=F, GC=F")
ativo_selecionado = st.sidebar.selectbox("Ativo Atual", [x.strip() for x in ativo_input.split(",")])
timeframe = st.sidebar.selectbox("Tempo Gráfico", ["1m", "5m", "15m", "1h", "1d"], index=2)
periodo_historico = st.sidebar.selectbox("Histórico", ["5d", "30d", "60d", "1y"], index=1)

st.sidebar.subheader("💼 Gestão de Risco")
capital = st.sidebar.number_input("Capital Inicial ($)", value=300000)
risco_por_trade = st.sidebar.number_input("Risco por Operação ($)", value=2400)
meta_assertividade = st.sidebar.slider("Alvo de Assertividade (%)", 50, 100, 80, step=5)
drawdown_limite = 7500

# ==========================================
# MÓDULO DE SETUPS MODULARES
# ==========================================
st.title("🧩 Construtor Quantitativo & Monte Carlo")

col_setups, col_editor = st.columns([1, 2])

with col_setups:
    st.subheader("Flags de Setup")
    use_ict = st.checkbox("ICT MMX", value=True)
    use_vwap = st.checkbox("Reversão VWAP Z-Score", value=True)

with col_editor:
    st.subheader("Editor de Lógica de Sinal (Python)")
    
    codigos_padrao = {
        "ICT": """
df['Sweep_Low'] = df['Low'] < df['Low'].shift(1).rolling(5).min()
df['BOS'] = df['Close'] > df['High'].shift(1).rolling(3).max()
df['Signal_ICT'] = np.where(df['Sweep_Low'].shift(1) & df['BOS'], 1, 0)
""",
        "VWAP": """
df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
df['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()
df['StDev'] = df['TP'].rolling(20).std()
df['Signal_VWAP'] = np.where(df['Close'] < (df['VWAP'] - (df['StDev'] * 2.5)), 1, 0)
"""
    }

    codigo_final = ""
    if use_ict: codigo_final += "\n# --- ICT ---\n" + codigos_padrao["ICT"]
    if use_vwap: codigo_final += "\n# --- VWAP ---\n" + codigos_padrao["VWAP"]
    
    codigo_editado = st.text_area("Edite o código:", value=codigo_final, height=200)

# ==========================================
# MOTOR DE BACKTEST
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados(ticker, tf, per):
    df = yf.download(ticker, period=per, interval=tf, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

taxa_acerto_real = 0.0
payoff_real = 2.0

if st.button("Executar Backtest", type="primary"):
    df = carregar_dados(ativo_selecionado, timeframe, periodo_historico)
    
    if not df.empty:
        local_vars = {'df': df, 'np': np}
        exec(codigo_editado, {}, local_vars)
        df = local_vars['df']
        
        sinais_ativos = []
        if use_ict: sinais_ativos.append('Signal_ICT')
        if use_vwap: sinais_ativos.append('Signal_VWAP')
        
        if sinais_ativos:
            df['Soma_Sinais'] = df[sinais_ativos].sum(axis=1)
            df['Signal_Final'] = np.where(df['Soma_Sinais'] == len(sinais_ativos), 1, 0)
        
        entradas_totais = df['Signal_Final'].sum()
        df['Retorno_Futuro'] = df['Close'].shift(-3) - df['Close']
        wins = len(df[(df['Signal_Final'] == 1) & (df['Retorno_Futuro'] > 0)])
        
        taxa_acerto_real = (wins / entradas_totais * 100) if entradas_totais > 0 else 0
        
        st.divider()
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("Total de Entradas", int(entradas_totais))
        col_res2.metric("Assertividade Obtida", f"{taxa_acerto_real:.2f}%")

# ==========================================
# TESTE DE ESTRESSE: MONTE CARLO
# ==========================================
st.divider()
st.subheader("🎲 Teste de Estresse (Simulação de Monte Carlo)")
st.markdown("Simula 500 trajetórias de capital para testar a probabilidade de falhar na Prop Firm.")

col_mc1, col_mc2 = st.columns(2)
win_rate_mc = col_mc1.number_input("Taxa de Acerto para Simulação (%)", value=float(taxa_acerto_real) if taxa_acerto_real > 0 else 80.0)
payoff_mc = col_mc2.number_input("Relação Risco/Retorno (Payoff)", value=2.8)

if st.button("Rodar Simulação Monte Carlo"):
    num_simulacoes = 500
    num_trades = 50
    
    ganho_por_trade = risco_por_trade * payoff_mc
    perda_por_trade = -risco_por_trade
    prob_vitoria = win_rate_mc / 100.0
    
    falhas_prop_firm = 0
    todas_curvas = []

    for i in range(num_simulacoes):
        capital_atual = capital
        pico_capital = capital
        curva_capital = [capital]
        quebrou = False
        
        for t in range(num_trades):
            resultado = np.random.rand()
            if resultado <= prob_vitoria:
                capital_atual += ganho_por_trade
            else:
                capital_atual += perda_por_trade
            
            pico_capital = max(pico_capital, capital_atual)
            drawdown_atual = pico_capital - capital_atual
            
            curva_capital.append(capital_atual)
            
            if drawdown_atual >= drawdown_limite:
                quebrou = True
        
        if quebrou:
            falhas_prop_firm += 1
            
        todas_curvas.append(curva_capital)

    prob_sucesso = 100 - ((falhas_prop_firm / num_simulacoes) * 100)
    
    col_r1, col_r2 = st.columns(2)
    col_r1.metric("Probabilidade de Passar na Mesa", f"{prob_sucesso:.1f}%")
    col_r2.metric("Falhas por Drawdown ($7.500)", f"{falhas_prop_firm} de {num_simulacoes}")
    
    # Plota as primeiras 50 simulações para não pesar o navegador
    fig_mc = go.Figure()
    for curva in todas_curvas[:50]:
        fig_mc.add_trace(go.Scatter(y=curva, mode='lines', line=dict(width=1, color='rgba(0, 150, 255, 0.3)'), showlegend=False))
    
    fig_mc.add_hline(y=capital - drawdown_limite, line_dash="dash", line_color="red", annotation_text="Drawdown Limite ($7.500)")
    fig_mc.update_layout(template='plotly_dark', title="Evolução Patrimonial (50 Simulações)", xaxis_title="Número de Trades", yaxis_title="Capital ($)")
    st.plotly_chart(fig_mc, use_container_width=True)