import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Quant Master Ultimate", layout="wide")

# ==========================================
# 1. SIDEBAR: CONFIGURAÇÕES E RISCO
# ==========================================
st.sidebar.title("⚙️ Painel de Controle")
ativo_input = st.sidebar.text_input("Ativos (separados por vírgula)", "NQ=F, ES=F, GC=F")
ativo_selecionado = st.sidebar.selectbox("Ativo Atual", [x.strip() for x in ativo_input.split(",")])
timeframe = st.sidebar.selectbox("Tempo Gráfico", ["1m", "5m", "15m", "1h", "1d"], index=2)
periodo_historico = st.sidebar.selectbox("Histórico", ["5d", "30d", "60d", "1y"], index=1)

st.sidebar.subheader("💼 Gestão de Risco & Mesa")
fase = st.sidebar.selectbox("Fase Operacional", ["Avaliação (Fase 1)", "Colchão (Fase 2)", "Manutenção (Fase 3)"])
capital = st.sidebar.number_input("Capital da Conta ($)", value=300000)
drawdown_limite = st.sidebar.number_input("Drawdown Máximo ($)", value=7500)
risco_por_trade = st.sidebar.number_input("Risco por Operação ($)", value=2400)
meta_assertividade = st.sidebar.slider("Alvo de Assertividade (%)", 50, 100, 80, step=5)

# ==========================================
# 2. MEGA DICIONÁRIO DE ESTRATÉGIAS
# ==========================================
st.title("🧩 Mega Construtor Quantitativo & Playbook")

codigos_padrao = {
    # --- ESCOLA INSTITUCIONAL (SMC / ICT) ---
    "ICT_MMX": """df['Sweep_Low'] = df['Low'] < df['Low'].shift(1).rolling(5).min()\ndf['BOS'] = df['Close'] > df['High'].shift(1).rolling(3).max()\ndf['Signal_ICT_MMX'] = np.where(df['Sweep_Low'].shift(1) & df['BOS'], 1, 0)""",
    "SMC_FVG": """df['FVG_Up'] = df['Low'] > df['High'].shift(2)\ndf['Signal_SMC_FVG'] = np.where(df['FVG_Up'], 1, 0)""",
    
    # --- ESCOLA DE REVERSÃO À MÉDIA E EXAUSTÃO ---
    "VWAP_ZSCORE": """df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3\ndf['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()\ndf['StDev'] = df['TP'].rolling(20).std()\ndf['Signal_VWAP_ZSCORE'] = np.where(df['Close'] < (df['VWAP'] - (df['StDev'] * 2.5)), 1, 0)""",
    "RSI_OB_OS": """delta = df['Close'].diff()\ngain = (delta.where(delta > 0, 0)).rolling(14).mean()\nloss = (-delta.where(delta < 0, 0)).rolling(14).mean()\nrs = gain / loss\ndf['RSI'] = 100 - (100 / (1 + rs))\ndf['Signal_RSI'] = np.where(df['RSI'] < 30, 1, 0)""",
    "BOLLINGER_REVERSAL": """df['SMA20'] = df['Close'].rolling(20).mean()\ndf['BB_Lower'] = df['SMA20'] - (df['Close'].rolling(20).std() * 2)\ndf['Signal_BB'] = np.where(df['Close'] < df['BB_Lower'], 1, 0)""",
    
    # --- ESCOLA DE TENDÊNCIA E PRICE ACTION ---
    "LARRY_WILLIAMS_91": """df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()\ndf['Turn_Up'] = (df['EMA9'] > df['EMA9'].shift(1)) & (df['EMA9'].shift(1) < df['EMA9'].shift(2))\ndf['Signal_LW91'] = np.where(df['Turn_Up'] & (df['Close'] > df['High'].shift(1)), 1, 0)""",
    "MACD_CROSS": """df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()\ndf['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()\ndf['MACD'] = df['EMA12'] - df['EMA26']\ndf['Signal_MACD'] = np.where((df['MACD'] > 0) & (df['MACD'].shift(1) <= 0), 1, 0)""",
    "EMA_CROSSOVER": """df['EMA9'] = df['Close'].ewm(span=9).mean()\ndf['EMA21'] = df['Close'].ewm(span=21).mean()\ndf['Signal_EMA_CROSS'] = np.where((df['EMA9'] > df['EMA21']) & (df['EMA9'].shift(1) <= df['EMA21'].shift(1)), 1, 0)""",
    "TURTLE_BREAKOUT": """df['High_20'] = df['High'].rolling(20).max().shift(1)\ndf['Signal_TURTLE'] = np.where(df['Close'] > df['High_20'], 1, 0)"""
}

col_setups, col_editor = st.columns([1, 2])

with col_setups:
    st.subheader("Flags de Setup (Mega Dicionário)")
    st.markdown("**Institucional**")
    use_ict = st.checkbox("ICT MMX", value=True)
    use_smc = st.checkbox("SMC (Fair Value Gap)", value=False)
    
    st.markdown("**Reversão & Exaustão**")
    use_vwap = st.checkbox("VWAP Z-Score", value=True)
    use_rsi = st.checkbox("RSI Sobrevendido", value=False)
    use_bb = st.checkbox("Bollinger Bands (Furo Inferior)", value=False)
    
    st.markdown("**Tendência & Clássicos**")
    use_lw91 = st.checkbox("Larry Williams 9.1", value=False)
    use_macd = st.checkbox("MACD Crossover", value=False)
    use_emacross = st.checkbox("EMA 9x21 Crossover", value=False)
    use_turtle = st.checkbox("Turtle (Rompimento 20p)", value=False)

with col_editor:
    st.subheader("Editor Base (Python)")
    
    codigo_final = ""
    sinais_ativos_nomes = []
    
    if use_ict: codigo_final += "\n# --- ICT MMX ---\n" + codigos_padrao["ICT_MMX"]; sinais_ativos_nomes.append("Signal_ICT_MMX")
    if use_smc: codigo_final += "\n# --- SMC FVG ---\n" + codigos_padrao["SMC_FVG"]; sinais_ativos_nomes.append("Signal_SMC_FVG")
    if use_vwap: codigo_final += "\n# --- VWAP Z-SCORE ---\n" + codigos_padrao["VWAP_ZSCORE"]; sinais_ativos_nomes.append("Signal_VWAP_ZSCORE")
    if use_rsi: codigo_final += "\n# --- RSI ---\n" + codigos_padrao["RSI_OB_OS"]; sinais_ativos_nomes.append("Signal_RSI")
    if use_bb: codigo_final += "\n# --- BOLLINGER ---\n" + codigos_padrao["BOLLINGER_REVERSAL"]; sinais_ativos_nomes.append("Signal_BB")
    if use_lw91: codigo_final += "\n# --- LARRY WILLIAMS 9.1 ---\n" + codigos_padrao["LARRY_WILLIAMS_91"]; sinais_ativos_nomes.append("Signal_LW91")
    if use_macd: codigo_final += "\n# --- MACD ---\n" + codigos_padrao["MACD_CROSS"]; sinais_ativos_nomes.append("Signal_MACD")
    if use_emacross: codigo_final += "\n# --- EMA CROSS ---\n" + codigos_padrao["EMA_CROSSOVER"]; sinais_ativos_nomes.append("Signal_EMA_CROSS")
    if use_turtle: codigo_final += "\n# --- TURTLE ---\n" + codigos_padrao["TURTLE_BREAKOUT"]; sinais_ativos_nomes.append("Signal_TURTLE")
    
    codigo_editado = st.text_area("Código Ativo (Você pode editar a lógica gerada abaixo):", value=codigo_final, height=250)

# ==========================================
# 3. MOTOR DE BACKTEST & MONTE CARLO FILTRADO
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados(ticker, tf, per):
    df = yf.download(ticker, period=per, interval=tf, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

df = carregar_dados(ativo_selecionado, timeframe, periodo_historico)

if not df.empty and st.button("Executar Backtest & Filtrar Monte Carlo", type="primary"):
    local_vars = {'df': df.copy(), 'np': np}
    exec(codigo_editado, {}, local_vars)
    df_calc = local_vars['df']
    
    df_calc['Retorno_Futuro'] = df_calc['Close'].shift(-3) - df_calc['Close']
    
    st.divider()
    st.subheader("🏆 Ranking de Setups Aprovados (Filtro Monte Carlo)")
    st.markdown(f"*Critério: Apenas setups que atingiram mais de **{meta_assertividade}%** de chance de passar na Prop Firm.*")
    
    # Roda simulação para cada setup ativado individualmente
    setups_aprovados = []
    
    for sinal in sinais_ativos_nomes:
        if sinal in df_calc.columns:
            entradas = df_calc[sinal].sum()
            wins = len(df_calc[(df_calc[sinal] == 1) & (df_calc['Retorno_Futuro'] > 0)])
            taxa_acerto_setup = (wins / entradas * 100) if entradas > 0 else 0
            
            # Simulação Monte Carlo Rápida para o Setup (500 runs)
            falhas = 0
            for i in range(500):
                cap = capital
                pico = capital
                for t in range(50): # 50 trades
                    if np.random.rand() <= (taxa_acerto_setup / 100):
                        cap += (risco_por_trade * 2) # Assume Payoff 1:2 genérico
                    else:
                        cap -= risco_por_trade
                    pico = max(pico, cap)
                    if (pico - cap) >= drawdown_limite:
                        falhas += 1
                        break
            
            prob_sucesso = 100 - ((falhas / 500) * 100)
            
            if prob_sucesso >= meta_assertividade:
                setups_aprovados.append({
                    "Setup": sinal.replace("Signal_", ""),
                    "Entradas": int(entradas),
                    "Win Rate Base": f"{taxa_acerto_setup:.1f}%",
                    "Prob. Aprovação (Mesa)": prob_sucesso
                })
    
    if setups_aprovados:
        df_ranking = pd.DataFrame(setups_aprovados).sort_values(by="Prob. Aprovação (Mesa)", ascending=False)
        # Formata para visualização
        df_ranking["Prob. Aprovação (Mesa)"] = df_ranking["Prob. Aprovação (Mesa)"].apply(lambda x: f"{x:.1f}%")
        st.table(df_ranking)
    else:
        st.error(f"Nenhum dos setups isolados atingiu os {meta_assertividade}% de probabilidade de passar na mesa neste ativo/período. Ajuste o código ou as exigências.")

# ==========================================
# 4. PLAYBOOK VISUAL OPERACIONAL
# ==========================================
st.divider()
st.subheader("📖 Seu Playbook Visual de Execução")
st.markdown("Guia tático de bolso gerado dinamicamente para manter sua disciplina na tela durante o pregão.")

# Cálculos dinâmicos para o Playbook
payoff_exigido = 2.8 if "Avaliação" in fase else (1.5 if "Colchão" in fase else 2.0)
risco_max_diario = drawdown_limite * 0.4 # Estipula que você pode perder no máx 40% do limite global em um único dia

# Cria painéis coloridos baseados na Fase
if "Avaliação" in fase:
    st.info(f"**FASE ATUAL: AVALIAÇÃO** - Foco em Payoff (Risco/Retorno) Extremo para bater a meta rápida.")
elif "Colchão" in fase:
    st.warning(f"**FASE ATUAL: COLCHÃO** - Foco em Acerto (Win Rate). Garanta capital de giro e fuja do Risco de Ruína.")
else:
    st.success(f"**FASE ATUAL: MANUTENÇÃO** - Foco em Perpetuação. Risco controlado, saques mensais.")

col_p1, col_p2, col_p3 = st.columns(3)

with col_p1:
    st.markdown("### 🛑 Gestão de Conta")
    st.markdown(f"- **Capital Base:** ${capital:,}")
    st.markdown(f"- **Risco Fixo por Trade:** ${risco_por_trade}")
    st.markdown(f"- **Limite de Perda Diária (Sugerido):** ${risco_max_diario}")
    st.markdown(f"- **Drawdown Global Restante:** ${drawdown_limite}")

with col_p2:
    st.markdown("### 🎯 Alvos da Operação")
    st.markdown(f"- **Alvo Mínimo (Take Profit):** ${risco_por_trade * payoff_exigido}")
    st.markdown(f"- **Payoff Exigido:** 1 : {payoff_exigido}")
    st.markdown("- **Horário Operacional:** 18:00 às 16:45 NY")
    st.markdown("- **Fechamento Forçado:** 16:45 NY")

with col_p3:
    st.markdown("### 🧠 Checklist Psicológico")
    st.markdown("- [ ] O setup apareceu no Ranking de Monte Carlo?")
    st.markdown("- [ ] O volume confirma a exaustão institucional?")
    st.markdown("- [ ] Estou respeitando o limite diário?")
    st.markdown("- [ ] Se romper o Drawdown diário, vou desligar a plataforma?")
