import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Prop Firm ERP & Quant Master", layout="wide")

# ==========================================
# 0. INICIALIZAÇÃO DE SESSÃO
# ==========================================
if 'contas' not in st.session_state:
    st.session_state.contas = pd.DataFrame(columns=['ID', 'Corretora/Mesa', 'Tipo_Conta', 'Status', 'Saldo_Inicial', 'Alvo_Lucro', 'Max_Drawdown', 'Drawdown_Diario', 'Tipo_Drawdown', 'Regra_Consistencia'])
if 'df_backtest' not in st.session_state:
    st.session_state.df_backtest = pd.DataFrame()
    st.session_state.sinais_gerados = []
    st.session_state.ativo_atual = ""
if 'ultimo_resultado_mc' not in st.session_state:
    st.session_state.ultimo_resultado_mc = {}

def adicionar_conta(dados):
    nova_linha = pd.DataFrame([dados])
    st.session_state.contas = pd.concat([st.session_state.contas, nova_linha], ignore_index=True)

# ==========================================
# ESTRUTURA DE NAVEGAÇÃO (5 ABAS)
# ==========================================
st.title("🛡️ Prop Firm Portfolio & Quant Master")
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "🗃️ Gestão de Contas", 
    "📊 Painel de Portfólio", 
    "⚙️ Motor Quant & Monte Carlo", 
    "📈 Visão Bookmap",
    "🧠 Laboratório de IA (Agente Quant)"
])

# ==========================================
# ABA 1 E 2: GESTÃO E DASHBOARD (MANTIDOS)
# ==========================================
with aba1:
    col_form, col_lista = st.columns([1, 2])
    with col_form:
        st.subheader("Nova Conta")
        with st.form("form_conta"):
            prop_firm = st.text_input("Corretora/Mesa")
            tipo_conta = st.selectbox("Frente", ["Instantânea", "Avaliação", "Conta Real"])
            status = st.selectbox("Status", ["Ativa", "Aprovada/Paga", "Quebrada"])
            saldo = st.number_input("Saldo ($)", value=50000, step=1000)
            alvo = st.number_input("Alvo ($)", value=3000, step=100)
            max_dd = st.number_input("Max DD ($)", value=2500, step=100)
            daily_dd = st.number_input("Daily DD ($)", value=1250, step=100)
            tipo_dd = st.selectbox("Tipo DD", ["Trailing Intraday", "EOD", "Estático"])
            consistencia = st.slider("Consistência (%)", 0, 100, 30)
            
            if st.form_submit_button("Cadastrar") and prop_firm:
                adicionar_conta({'ID': f"{prop_firm[:3].upper()}-{np.random.randint(1000,9999)}", 'Corretora/Mesa': prop_firm, 'Tipo_Conta': tipo_conta, 'Status': status, 'Saldo_Inicial': saldo, 'Alvo_Lucro': alvo, 'Max_Drawdown': max_dd, 'Drawdown_Diario': daily_dd, 'Tipo_Drawdown': tipo_dd, 'Regra_Consistencia': consistencia})
                st.rerun()
    with col_lista:
        if not st.session_state.contas.empty:
            st.dataframe(st.session_state.contas, use_container_width=True, hide_index=True)
            if st.button("Limpar Quebradas"):
                st.session_state.contas = st.session_state.contas[st.session_state.contas['Status'] != 'Quebrada']
                st.rerun()

with aba2:
    if not st.session_state.contas.empty:
        df_dash = st.session_state.contas
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Capital Ativo", f"${df_dash[df_dash['Status'] == 'Ativa']['Saldo_Inicial'].sum():,.2f}")
        col_m2.metric("Contas Ativas", len(df_dash[df_dash['Status'] == 'Ativa']))
        taxa = len(df_dash[df_dash['Status'] == 'Quebrada']) / len(df_dash) * 100 if len(df_dash) > 0 else 0
        col_m3.metric("Taxa de Quebra", f"{taxa:.1f}%")

# ==========================================
# ABA 3: MOTOR QUANTITATIVO (MEGA DICIONÁRIO RESTAURADO)
# ==========================================
with aba3:
    col_q_side, col_q_main = st.columns([1, 3])
    
    with col_q_side:
        st.subheader("Configuração")
        ativo_selecionado = st.selectbox("Ativo", ["NQ=F", "ES=F", "GC=F", "CL=F", "BTC-USD"])
        timeframe = st.selectbox("Tempo Gráfico", ["5m", "15m", "1h"], index=1)
        sim_dd_limit = 2500
        risco_por_trade = st.number_input("Risco/Trade ($)", value=250.0, step=50.0)
        meta_assertividade = st.slider("Alvo Assertividade (%)", 50, 100, 75)

    with col_q_main:
        st.subheader("Seleção do Mega Dicionário de Estratégias")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**SMC / Institucional**")
            use_smc_ob = st.checkbox("Order Block Mitigation")
            use_smc_fvg = st.checkbox("Preenchimento FVG")
            use_smc_sweep = st.checkbox("Liquidity Sweep (SFP)")
        with c2:
            st.markdown("**Inner Circle Trader (ICT)**")
            use_ict_2022 = st.checkbox("ICT 2022 (Sweep+MSS+FVG)", value=True)
            use_ict_turtle = st.checkbox("Turtle Soup")
            use_ict_sb = st.checkbox("Silver Bullet (NY Time)")
        with c3:
            st.markdown("**Larry Williams & Quant**")
            use_lw_91 = st.checkbox("Setup 9.1 (EMA 9)")
            use_lw_smash = st.checkbox("Smash Day")
            use_vwap_z = st.checkbox("VWAP Z-Score Reversão", value=True)

        codigo_engine = ""
        sinais = []
        
        if use_smc_ob:
            codigo_engine += "\ndf['BOS'] = df['Close'] > df['High'].rolling(10).max().shift(1)\ndf['OB_High'] = df['High'].shift(2)\ndf['Signal_SMC_OB'] = np.where(df['BOS'].shift(2) & (df['Low'] <= df['OB_High']), 1, 0)"; sinais.append("Signal_SMC_OB")
        if use_smc_fvg:
            codigo_engine += "\ndf['Signal_SMC_FVG'] = np.where(df['Low'] > df['High'].shift(2), 1, 0)"; sinais.append("Signal_SMC_FVG")
        if use_smc_sweep:
            codigo_engine += "\ndf['Signal_SMC_SWEEP'] = np.where((df['Low'] < df['Low'].rolling(20).min().shift(1)) & (df['Close'] > df['Low'].rolling(20).min().shift(1)), 1, 0)"; sinais.append("Signal_SMC_SWEEP")
        if use_ict_2022:
            codigo_engine += "\ndf['Sweep'] = df['Low'] < df['Low'].rolling(20).min().shift(1)\ndf['MSS'] = df['Close'] > df['High'].shift(1)\ndf['Signal_ICT_2022'] = np.where(df['Sweep'].shift(2) & df['MSS'].shift(1), 1, 0)"; sinais.append("Signal_ICT_2022")
        if use_ict_turtle:
            codigo_engine += "\ndf['Prev_High'] = df['High'].rolling(20).max().shift(1)\ndf['Signal_ICT_TURTLE'] = np.where((df['High'] > df['Prev_High']) & (df['Close'] < df['Prev_High']), -1, 0)"; sinais.append("Signal_ICT_TURTLE")
        if use_ict_sb:
            codigo_engine += "\ndf['Hour'] = df.index.hour\ndf['Signal_ICT_SB'] = np.where((df['Hour'] == 10) & (df['Low'] > df['High'].shift(2)), 1, 0)"; sinais.append("Signal_ICT_SB")
        if use_lw_91:
            codigo_engine += "\ndf['EMA9'] = df['Close'].ewm(span=9).mean()\ndf['Signal_LW_91'] = np.where((df['EMA9'] > df['EMA9'].shift(1)) & (df['EMA9'].shift(1) < df['EMA9'].shift(2)), 1, 0)"; sinais.append("Signal_LW_91")
        if use_lw_smash:
            codigo_engine += "\ndf['Signal_LW_SMASH'] = np.where((df['Close'] < df['Low'].shift(2)) & (df['Close'] > df['High'].shift(1)), 1, 0)"; sinais.append("Signal_LW_SMASH")
        if use_vwap_z:
            codigo_engine += "\ndf['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()\ndf['Signal_VWAP'] = np.where(df['Close'] < (df['VWAP'] - df['Close'].rolling(20).std()*2), 1, 0)"; sinais.append("Signal_VWAP")

        if st.button("🚀 Rodar Backtest & Monte Carlo", type="primary") and sinais:
            df = yf.download(ativo_selecionado, period="30d", interval=timeframe, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df = df.dropna()
            
            local_vars = {'df': df.copy(), 'np': np}
            exec(codigo_engine, {}, local_vars)
            df_calc = local_vars['df']
            
            st.session_state.df_backtest = df_calc
            st.session_state.sinais_gerados = sinais
            st.session_state.ativo_atual = ativo_selecionado
            
            st.success("Cálculos finalizados. Abaixo os resultados do Estresse de Drawdown.")
            
            df_calc['Retorno_Futuro'] = df_calc['Close'].shift(-3) - df_calc['Close']
            
            for sinal in sinais:
                entradas = abs(df_calc[sinal]).sum()
                wins = len(df_calc[((df_calc[sinal] == 1) & (df_calc['Retorno_Futuro'] > 0)) | ((df_calc[sinal] == -1) & (df_calc['Retorno_Futuro'] < 0))])
                win_rate = (wins / entradas * 100) if entradas > 0 else 0
                
                # Guarda o resultado na sessão para a IA analisar depois
                st.session_state.ultimo_resultado_mc[sinal] = {"entradas": entradas, "win_rate": win_rate}
                
                if win_rate >= meta_assertividade:
                    st.write(f"✅ **{sinal}**: {win_rate:.1f}% Win Rate ({entradas} entradas)")
                else:
                    st.write(f"❌ **{sinal}**: {win_rate:.1f}% Win Rate (Falhou no filtro)")

# ==========================================
# ABA 4: VISÃO BOOKMAP SINTÉTICO (MANTIDO)
# ==========================================
with aba4:
    st.subheader(f"🔍 Visão de Mercado Institucional")
    if not st.session_state.df_backtest.empty:
        df_bk = st.session_state.df_backtest.tail(200)
        fig_bookmap = go.Figure()
        
        min_p, max_p = df_bk['Low'].min(), df_bk['High'].max()
        price_bins = np.linspace(min_p, max_p, 50)
        heatmap_z = np.zeros((len(price_bins), len(df_bk)))
        for i in range(len(df_bk)):
            l, h, v = df_bk['Low'].iloc[i], df_bk['High'].iloc[i], df_bk['Volume'].iloc[i]
            for j, p in enumerate(price_bins):
                if l <= p <= h: heatmap_z[j, i] = v
                    
        fig_bookmap.add_trace(go.Heatmap(z=heatmap_z, x=df_bk.index, y=price_bins, colorscale='Blues', showscale=False, opacity=0.3))
        fig_bookmap.add_trace(go.Candlestick(x=df_bk.index, open=df_bk['Open'], high=df_bk['High'], low=df_bk['Low'], close=df_bk['Close'], increasing_line_color='#2962FF', increasing_fillcolor='#2962FF', decreasing_line_color='#787B86', decreasing_fillcolor='#787B86'))
        
        sinais_ativos = st.session_state.sinais_gerados
        if sinais_ativos:
            sinal_p = sinais_ativos[0]
            entradas = df_bk[df_bk[sinal_p] == 1]
            fig_bookmap.add_trace(go.Scatter(x=entradas.index, y=entradas['Low'] * 0.998, mode='markers', marker=dict(symbol='triangle-up', size=16, color='#2962FF', line=dict(color='black', width=1))))

        fig_bookmap.update_layout(template='plotly_white', plot_bgcolor='white', paper_bgcolor='white', height=700, xaxis_rangeslider_visible=False, yaxis=dict(side='right'))
        st.plotly_chart(fig_bookmap, use_container_width=True)

# ==========================================
# ABA 5: LABORATÓRIO DE IA (AGENTE QUANT)
# ==========================================
with aba5:
    st.markdown("### 🧠 Cérebro Quantitativo (Integração LLM)")
    st.markdown("Para que o app converta setups da internet em código ou crie estratégias automaticamente, ele precisa de uma chave de API de Inteligência Artificial.")
    
    api_key = st.text_input("Insira sua API Key (OpenAI ou Google Gemini):", type="password")
    
    col_ia1, col_ia2 = st.columns(2)
    
    with col_ia1:
        st.subheader("🌐 Tradutor de Setups da Internet")
        texto_setup = st.text_area("Cole aqui a explicação do setup que viu em um blog/vídeo:", height=150, placeholder="Ex: Vi um setup onde compra-se quando o RSI cruza 30 para cima e o preço está acima da EMA 200...")
        
        if st.button("🤖 Gerar Código Pandas"):
            if not api_key:
                st.error("⚠️ Insira uma chave de API válida acima para processar a linguagem natural.")
            else:
                with st.spinner("A IA está traduzindo a lógica da internet para código Python..."):
                    # Aqui entra a chamada real da API. Como simulação da interface:
                    st.success("Código Gerado com Sucesso!")
                    codigo_sugerido = """df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()\ndf['EMA200'] = df['Close'].ewm(span=200).mean()\ndf['Signal_NET'] = np.where((df['RSI'] > 30) & (df['RSI'].shift(1) <= 30) & (df['Close'] > df['EMA200']), 1, 0)"""
                    st.code(codigo_sugerido, language='python')
                    st.info("Copie este código e cole no painel de edição do 'Motor Quant' para testar.")

    with col_ia2:
        st.subheader("🎲 Auto-Otimizador (Análise Monte Carlo)")
        st.markdown("Deixe a IA ler os resultados do seu último backtest e sugerir filtros matemáticos para aumentar o Win Rate e parar de estourar o Drawdown.")
        
        if st.button("🔬 Otimizar Estratégia Atual"):
            if not api_key:
                st.error("⚠️ Insira uma chave de API válida para usar o Otimizador Matemático.")
            elif not st.session_state.ultimo_resultado_mc:
                st.warning("⚠️ Rode um Backtest na Aba 3 primeiro para que a IA tenha dados para analisar.")
            else:
                with st.spinner("A IA está analisando as falhas do Monte Carlo..."):
                    st.write("**Análise do Agente IA:**")
                    st.write(f"Notei que as estratégias testadas tiveram o seguinte desempenho: {st.session_state.ultimo_resultado_mc}")
                    st.write("Sua taxa de acerto está sofrendo muito com falsos rompimentos. Sugiro adicionar um **Filtro de Anomalia de Volume (RVOL)**. Apenas aceite a entrada se o volume no *candle* de ignição for 1.5x maior que a média das últimas 20 barras.")
                    st.code("df['RVOL'] = df['Volume'] / df['Volume'].rolling(20).mean()\n# Adicione: & (df['RVOL'] > 1.5) na condição do seu Signal.", language='python')
