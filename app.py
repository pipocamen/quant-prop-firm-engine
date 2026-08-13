import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Quant Master Institucional", layout="wide")

# ==========================================
# 1. SIDEBAR: CONFIGURAÇÕES GERAIS
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
# 2. MEGA DICIONÁRIO DE CÓDIGOS (ENGINE PANDAS)
# ==========================================
st.title("🧩 Construtor Quantitativo Institucional")
st.markdown("Selecione e combine módulos algorítmicos. O código será gerado automaticamente no editor.")

codigos_padrao = {
    # ---------------- SMC (SMART MONEY CONCEPTS) ----------------
    "SMC_OB": """\n# SMC: Order Block Mitigation\ndf['BOS'] = df['Close'] > df['High'].rolling(10).max().shift(1)\ndf['OB_High'] = df['High'].shift(2)\ndf['Signal_SMC_OB'] = np.where(df['BOS'].shift(2) & (df['Low'] <= df['OB_High']), 1, 0)""",
    "SMC_FVG": """\n# SMC: Fair Value Gap (Imbalance)\ndf['FVG_Up'] = df['Low'] > df['High'].shift(2)\ndf['Signal_SMC_FVG'] = np.where(df['FVG_Up'], 1, 0)""",
    "SMC_SFP": """\n# SMC: Swing Failure Pattern (SFP) - Varredura de liquidez\ndf['Sweep_Low'] = df['Low'] < df['Low'].rolling(20).min().shift(1)\ndf['Close_Inside'] = df['Close'] > df['Low'].rolling(20).min().shift(1)\ndf['Signal_SMC_SFP'] = np.where(df['Sweep_Low'] & df['Close_Inside'], 1, 0)""",
    "SMC_LIQ_SWEEP": """\n# SMC: BSL/SSL Sweep (Liquidity Sweep)\ndf['Equal_Highs'] = abs(df['High'].shift(1) - df['High'].shift(2)) < (df['Close']*0.0005)\ndf['Sweep_EH'] = (df['High'] > df['High'].shift(1)) & (df['Close'] < df['High'].shift(1))\ndf['Signal_SMC_SWEEP'] = np.where(df['Equal_Highs'].shift(1) & df['Sweep_EH'], -1, 0)""",
    
    # ---------------- ICT (INNER CIRCLE TRADER) ----------------
    "ICT_2022": """\n# ICT: 2022 Mentorship Model (Sweep + MSS + FVG)\ndf['Liq_Sweep'] = df['Low'] < df['Low'].rolling(20).min().shift(1)\ndf['MSS'] = df['Close'] > df['High'].shift(1)\ndf['FVG'] = df['Low'].shift(-1) > df['High'].shift(1)\ndf['Signal_ICT_2022'] = np.where(df['Liq_Sweep'].shift(2) & df['MSS'].shift(1) & df['FVG'], 1, 0)""",
    "ICT_TURTLE": """\n# ICT: Turtle Soup (Falso Rompimento Imediato)\ndf['Prev_High_20'] = df['High'].rolling(20).max().shift(1)\ndf['Violated'] = df['High'] > df['Prev_High_20']\ndf['Rejected'] = df['Close'] < df['Prev_High_20']\ndf['Signal_ICT_TURTLE'] = np.where(df['Violated'] & df['Rejected'], -1, 0)""",
    "ICT_SILVER_BULLET": """\n# ICT: Silver Bullet (Time-Based FVG 10:00-11:00 NY)\ndf['Hour'] = df.index.tz_convert('America/New_York').hour if df.index.tz is not None else df.index.hour\ndf['Silver_Window'] = (df['Hour'] == 10)\ndf['FVG_Up'] = df['Low'] > df['High'].shift(2)\ndf['Signal_ICT_SB'] = np.where(df['Silver_Window'] & df['FVG_Up'], 1, 0)""",
    "ICT_PO3": """\n# ICT: Power of 3 (AMD) - Compra abaixo da abertura\ndf['Daily_Open'] = df['Open'].groupby(df.index.date).transform('first')\ndf['Manipulation'] = df['Low'] < df['Daily_Open']\ndf['Signal_ICT_PO3'] = np.where(df['Manipulation'], 1, 0)""",

    # ---------------- LARRY WILLIAMS ----------------
    "LW_91": """\n# Larry Williams: Setup 9.1 (Inversão de Média)\ndf['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()\ndf['Turn_Up'] = (df['EMA9'] > df['EMA9'].shift(1)) & (df['EMA9'].shift(1) < df['EMA9'].shift(2))\ndf['Signal_LW_91'] = np.where(df['Turn_Up'] & (df['Close'] > df['High'].shift(1)), 1, 0)""",
    "LW_OOPS": """\n# Larry Williams: Oops! (Gap Rejeitado)\ndf['Gap_Down'] = df['Open'] < df['Low'].shift(1)\ndf['Rejection'] = df['Close'] > df['Low'].shift(1)\ndf['Signal_LW_OOPS'] = np.where(df['Gap_Down'] & df['Rejection'], 1, 0)""",
    "LW_SMASH": """\n# Larry Williams: Smash Day (Armadilha de Fundo)\ndf['Close_Near_Low'] = df['Close'] < (df['Low'] + (df['High'] - df['Low']) * 0.33)\ndf['Under_Prev_Low'] = df['Close'] < df['Low'].shift(2)\ndf['Smash_Trigger'] = df['Close'] > df['High'].shift(1)\ndf['Signal_LW_SMASH'] = np.where(df['Close_Near_Low'].shift(1) & df['Under_Prev_Low'].shift(1) & df['Smash_Trigger'], 1, 0)""",
    "LW_WILLIAMS_R": """\n# Larry Williams: %R Quantificado\ndf['Max_14'] = df['High'].rolling(14).max()\ndf['Min_14'] = df['Low'].rolling(14).min()\ndf['Pct_R'] = ((df['Max_14'] - df['Close']) / (df['Max_14'] - df['Min_14'])) * -100\ndf['Signal_LW_R'] = np.where((df['Pct_R'].shift(1) <= -80) & (df['Pct_R'] > -80), 1, 0)""",

    # ---------------- SISTEMAS CLÁSSICOS CONSISTENTES (EVIDÊNCIA CONCRETA) ----------------
    "QUANT_DONCHIAN": """\n# Richard Donchian: Trend Following (Rompimento 20 periodos - Altíssima consistência macro)\ndf['Donchian_Upper'] = df['High'].rolling(20).max().shift(1)\ndf['Signal_DONCHIAN'] = np.where(df['Close'] > df['Donchian_Upper'], 1, 0)""",
    "QUANT_BOLLINGER_REV": """\n# John Bollinger: Reversão à Média (Mean Reversion Estatístico)\ndf['SMA20'] = df['Close'].rolling(20).mean()\ndf['StDev'] = df['Close'].rolling(20).std()\ndf['BB_Lower'] = df['SMA20'] - (df['StDev'] * 2.2)\ndf['Signal_BB_REV'] = np.where((df['Low'] < df['BB_Lower']) & (df['Close'] > df['BB_Lower']), 1, 0)""",
    "QUANT_ELDER_RAY": """\n# Alexander Elder: Triple Screen / Impulse System (EMA + MACD Histo)\ndf['EMA13'] = df['Close'].ewm(span=13).mean()\ndf['EMA_Up'] = df['EMA13'] > df['EMA13'].shift(1)\ndf['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()\ndf['MACD_Signal'] = df['MACD'].ewm(span=9).mean()\ndf['MACD_Hist'] = df['MACD'] - df['MACD_Signal']\ndf['Hist_Up'] = df['MACD_Hist'] > df['MACD_Hist'].shift(1)\ndf['Signal_ELDER'] = np.where(df['EMA_Up'] & df['Hist_Up'], 1, 0)"""
}

# ==========================================
# 3. INTERFACE DE SELEÇÃO E GERAÇÃO DE CÓDIGO
# ==========================================
col_smc, col_ict, col_lw, col_quant = st.columns(4)

with col_smc:
    st.subheader("💧 SMC (Smart Money)")
    use_smc_ob = st.checkbox("OB Mitigação")
    use_smc_fvg = st.checkbox("Preenchimento FVG")
    use_smc_sfp = st.checkbox("SFP (Vela de Ignição)")
    use_smc_sweep = st.checkbox("Caça Liquidez (BSL/SSL)")

with col_ict:
    st.subheader("🕰️ ICT (Inner Circle)")
    use_ict_2022 = st.checkbox("Modelo 2022 (MSS)")
    use_ict_turtle = st.checkbox("Turtle Soup")
    use_ict_sb = st.checkbox("Silver Bullet (NY)")
    use_ict_po3 = st.checkbox("PO3 / AMD")

with col_lw:
    st.subheader("📈 Larry Williams")
    use_lw_91 = st.checkbox("Setup 9.1 (Média)")
    use_lw_oops = st.checkbox("Oops! (Gaps)")
    use_lw_smash = st.checkbox("Smash Day")
    use_lw_r = st.checkbox("Williams %R")

with col_quant:
    st.subheader("🏦 Titãs Quantitativos")
    use_donchian = st.checkbox("Donchian Trend")
    use_bb_rev = st.checkbox("Bollinger Reversion")
    use_elder = st.checkbox("Elder Impulse")

# Compilador Automático
codigo_final = ""
sinais_ativos_nomes = []

# Mapeamento dinâmico das checkboxes para as chaves do dicionário
selecoes = {
    "SMC_OB": use_smc_ob, "SMC_FVG": use_smc_fvg, "SMC_SFP": use_smc_sfp, "SMC_LIQ_SWEEP": use_smc_sweep,
    "ICT_2022": use_ict_2022, "ICT_TURTLE": use_ict_turtle, "ICT_SILVER_BULLET": use_ict_sb, "ICT_PO3": use_ict_po3,
    "LW_91": use_lw_91, "LW_OOPS": use_lw_oops, "LW_SMASH": use_lw_smash, "LW_WILLIAMS_R": use_lw_r,
    "QUANT_DONCHIAN": use_donchian, "QUANT_BOLLINGER_REV": use_bb_rev, "QUANT_ELDER_RAY": use_elder
}

for chave, ativo in selecoes.items():
    if ativo:
        codigo_final += codigos_padrao[chave] + "\n"
        # Extrai o nome da variável de sinal gerada (ex: Signal_ICT_2022)
        sinal_var = codigos_padrao[chave].split("df['")[-1].split("']")[0]
        sinais_ativos_nomes.append(sinal_var)

st.divider()
st.subheader("💻 Editor Dinâmico de Lógica de Execução")
codigo_editado = st.text_area("O código Python/Pandas abaixo é gerado em tempo real com base nas suas seleções. Edite livremente:", value=codigo_final, height=300)

# ==========================================
# 4. MOTOR DE EXECUÇÃO & TESTE DE ESTRESSE
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados(ticker, tf, per):
    try:
        df = yf.download(ticker, period=per, interval=tf, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except:
        return pd.DataFrame()

if st.button("🚀 Processar Algoritmos e Filtrar Sobreviventes", type="primary") and len(sinais_ativos_nomes) > 0:
    df = carregar_dados(ativo_selecionado, timeframe, periodo_historico)
    
    if not df.empty:
        # Executa o código Python
        local_vars = {'df': df.copy(), 'np': np}
        exec(codigo_editado, {}, local_vars)
        df_calc = local_vars['df']
        
        # Calcula alvo genérico futuro (ex: 3 barras à frente para scalps institucionais)
        df_calc['Retorno_Futuro'] = df_calc['Close'].shift(-3) - df_calc['Close']
        
        st.divider()
        st.subheader(f"🏆 Relatório de Sobrevivência de Monte Carlo ({ativo_selecionado})")
        st.markdown(f"O motor gerou 500 simulações de capital para cada estratégia selecionada. Apenas setups com probabilidade de aprovação acima de **{meta_assertividade}%** são exibidos.")
        
        setups_aprovados = []
        
        for sinal in sinais_ativos_nomes:
            if sinal in df_calc.columns:
                entradas = abs(df_calc[sinal]).sum() # Absoluto para pegar sinais de venda (-1) também
                
                # Regra de Win: Compra (1) e preço subiu, ou Venda (-1) e preço caiu
                wins = len(df_calc[((df_calc[sinal] == 1) & (df_calc['Retorno_Futuro'] > 0)) | ((df_calc[sinal] == -1) & (df_calc['Retorno_Futuro'] < 0))])
                taxa_acerto_setup = (wins / entradas * 100) if entradas > 0 else 0
                
                falhas = 0
                if entradas > 0:
                    for i in range(500):
                        cap = capital
                        pico = capital
                        for t in range(50):
                            if np.random.rand() <= (taxa_acerto_setup / 100):
                                cap += (risco_por_trade * 2.0) # Payoff base 1:2
                            else:
                                cap -= risco_por_trade
                            pico = max(pico, cap)
                            if (pico - cap) >= drawdown_limite:
                                falhas += 1
                                break
                                
                prob_sucesso = 100 - ((falhas / 500) * 100) if entradas > 0 else 0
                
                if prob_sucesso >= meta_assertividade and entradas > 0:
                    setups_aprovados.append({
                        "Escola / Setup": sinal.replace("Signal_", ""),
                        "Entradas Detectadas": int(entradas),
                        "Win Rate Histórico": f"{taxa_acerto_setup:.1f}%",
                        "Risco de Ruína": f"{(100-prob_sucesso):.1f}%",
                        "Prob. Passar na Prop Firm": f"{prob_sucesso:.1f}%"
                    })
        
        if setups_aprovados:
            df_ranking = pd.DataFrame(setups_aprovados).sort_values(by="Prob. Passar na Prop Firm", ascending=False)
            st.table(df_ranking)
        else:
            st.error(f"Nenhum dos setups suportou o teste de estresse de {meta_assertividade}% para o limite de perda da Prop Firm. Tente tempos gráficos maiores ou ajuste o Risco.")

# ==========================================
# 5. PLAYBOOK VISUAL E GERENCIAMENTO
# ==========================================
st.divider()
st.subheader("📖 Regras de Engajamento e Gestão de Fase")
payoff_exigido = 2.8 if "Avaliação" in fase else (1.5 if "Colchão" in fase else 2.0)
risco_max_diario = drawdown_limite * 0.4 

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    st.markdown("### 🛑 Limites de Conta")
    st.markdown(f"- **Risco por Clique:** ${risco_por_trade}")
    st.markdown(f"- **Drawdown Máx. Diário:** ${risco_max_diario}")
with col_p2:
    st.markdown("### 🎯 Alvos da Operação")
    st.markdown(f"- **Take Profit Mínimo:** ${risco_por_trade * payoff_exigido}")
    st.markdown(f"- **Payoff Ativo:** 1 : {payoff_exigido}")
with col_p3:
    st.markdown("### 🧠 Confirmação Tática")
    st.markdown("- [ ] O setup está no Ranking de Sobrevivência?")
    st.markdown("- [ ] O prêmio do risco justifica o trade?")
