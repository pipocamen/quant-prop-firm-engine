import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Prop Firm ERP & Quant Master", layout="wide")

# ==========================================
# 0. INICIALIZAÇÃO DE SESSÃO E BANCO DE DADOS LOCAL
# ==========================================
if 'contas' not in st.session_state:
    st.session_state.contas = pd.DataFrame(columns=[
        'ID', 'Corretora/Mesa', 'Tipo_Conta', 'Status', 'Saldo_Inicial', 
        'Alvo_Lucro', 'Max_Drawdown', 'Drawdown_Diario', 'Tipo_Drawdown', 'Regra_Consistencia'
    ])

if 'df_backtest' not in st.session_state:
    st.session_state.df_backtest = pd.DataFrame()
    st.session_state.sinais_gerados = []
    st.session_state.ativo_atual = ""

def adicionar_conta(dados):
    nova_linha = pd.DataFrame([dados])
    st.session_state.contas = pd.concat([st.session_state.contas, nova_linha], ignore_index=True)

# ==========================================
# ESTRUTURA DE NAVEGAÇÃO (4 ABAS)
# ==========================================
st.title("🛡️ Prop Firm Portfolio & Quant Master")
aba1, aba2, aba3, aba4 = st.tabs([
    "🗃️ Gestão de Contas", 
    "📊 Painel de Portfólio", 
    "⚙️ Motor Quant & Monte Carlo", 
    "📈 Visão Bookmap (Liquidez)"
])

# ==========================================
# ABA 1: GESTÃO DE CONTAS (MANTIDA INTACTA)
# ==========================================
with aba1:
    col_form, col_lista = st.columns([1, 2])
    with col_form:
        st.subheader("Nova Conta / Replicação")
        with st.form("form_conta"):
            prop_firm = st.text_input("Corretora/Mesa (Ex: Apex, FTMO)")
            tipo_conta = st.selectbox("Frente", ["Instantânea", "Avaliação", "Conta Real"])
            status = st.selectbox("Status Atual", ["Ativa", "Aprovada/Paga", "Quebrada"])
            saldo = st.number_input("Saldo Inicial ($)", value=50000, step=1000)
            alvo = st.number_input("Alvo de Lucro ($)", value=3000, step=100)
            max_dd = st.number_input("Drawdown Máximo ($)", value=2500, step=100)
            daily_dd = st.number_input("Drawdown Diário ($)", value=1250, step=100)
            tipo_dd = st.selectbox("Tipo Drawdown", ["Trailing Intraday (Flutuante Máximo)", "EOD (End of Day)", "Estático"])
            consistencia = st.slider("Consistência (%)", 0, 100, 30)
            
            if st.form_submit_button("Cadastrar Conta") and prop_firm:
                nova_id = f"{prop_firm[:3].upper()}-{np.random.randint(1000,9999)}"
                adicionar_conta({'ID': nova_id, 'Corretora/Mesa': prop_firm, 'Tipo_Conta': tipo_conta, 'Status': status, 'Saldo_Inicial': saldo, 'Alvo_Lucro': alvo, 'Max_Drawdown': max_dd, 'Drawdown_Diario': daily_dd, 'Tipo_Drawdown': tipo_dd, 'Regra_Consistencia': consistencia})
                st.rerun()

    with col_lista:
        st.subheader("Monitoramento")
        if not st.session_state.contas.empty:
            st.dataframe(st.session_state.contas, use_container_width=True, hide_index=True)
            if st.button("Limpar Contas Quebradas"):
                st.session_state.contas = st.session_state.contas[st.session_state.contas['Status'] != 'Quebrada']
                st.rerun()

# ==========================================
# ABA 2: PAINEL DE PORTFÓLIO (MANTIDO INTACTO)
# ==========================================
with aba2:
    if not st.session_state.contas.empty:
        df_dash = st.session_state.contas
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Capital Ativo", f"${df_dash[df_dash['Status'] == 'Ativa']['Saldo_Inicial'].sum():,.2f}")
        col_m2.metric("Contas Ativas", len(df_dash[df_dash['Status'] == 'Ativa']))
        taxa = len(df_dash[df_dash['Status'] == 'Quebrada']) / len(df_dash) * 100 if len(df_dash) > 0 else 0
        col_m3.metric("Taxa de Quebra", f"{taxa:.1f}%")
        
        st.plotly_chart(px.pie(df_dash, names='Status', title='Status de Contas', template='plotly_dark'), use_container_width=True)

# ==========================================
# ABA 3: MOTOR QUANTITATIVO & EXPORTAÇÃO
# ==========================================
with aba3:
    col_q_side, col_q_main = st.columns([1, 3])
    
    with col_q_side:
        st.subheader("Configuração")
        ativo_input = st.text_input("Ativos", "NQ=F")
        ativo_selecionado = st.selectbox("Ativo Atual", [x.strip() for x in ativo_input.split(",")])
        timeframe = st.selectbox("Tempo Gráfico", ["5m", "15m", "1h"], index=1)
        
        sim_capital, sim_dd_limit, sim_tipo_dd = 50000, 2500, "Trailing Intraday (Flutuante Máximo)"
        if not st.session_state.contas.empty:
            conta_sel = st.selectbox("Importar Regras da Conta:", st.session_state.contas['ID'].tolist())
            dados_conta = st.session_state.contas[st.session_state.contas['ID'] == conta_sel].iloc[0]
            sim_capital, sim_dd_limit, sim_tipo_dd = dados_conta['Saldo_Inicial'], dados_conta['Max_Drawdown'], dados_conta['Tipo_Drawdown']
            st.info(f"Regra: {sim_tipo_dd}\nDD: ${sim_dd_limit}")

        risco_por_trade = st.number_input("Risco/Trade ($)", value=float(sim_dd_limit * 0.1), step=50.0)
        meta_assertividade = st.slider("Alvo Assertividade (%)", 50, 100, 75)

    with col_q_main:
        st.subheader("Módulos Estratégicos")
        use_ict = st.checkbox("ICT Modelo 2022 (Sweep + MSS + FVG)", value=True)
        use_vwap = st.checkbox("VWAP Z-Score Reversão", value=False)
        
        codigo_engine = ""
        sinais = []
        if use_ict:
            codigo_engine += "\ndf['Sweep'] = df['Low'] < df['Low'].rolling(20).min().shift(1)\ndf['MSS'] = df['Close'] > df['High'].shift(1)\ndf['Signal_ICT'] = np.where(df['Sweep'].shift(2) & df['MSS'].shift(1), 1, 0)"
            sinais.append("Signal_ICT")
        if use_vwap:
            codigo_engine += "\ndf['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()\ndf['Signal_VWAP'] = np.where(df['Close'] < (df['VWAP'] - df['Close'].rolling(20).std()*2), 1, 0)"
            sinais.append("Signal_VWAP")

        if st.button("🚀 Rodar Backtest & Monte Carlo", type="primary") and sinais:
            df = yf.download(ativo_selecionado, period="30d", interval=timeframe, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df = df.dropna()
            
            local_vars = {'df': df.copy(), 'np': np}
            exec(codigo_engine, {}, local_vars)
            df_calc = local_vars['df']
            
            # Salva na sessão para o Bookmap ler
            st.session_state.df_backtest = df_calc
            st.session_state.sinais_gerados = sinais
            st.session_state.ativo_atual = ativo_selecionado
            st.success("Sinais gerados! Veja a aba de Visão Bookmap para os gráficos.")
        
        st.divider()
        st.subheader("💾 Exportar Robô (Código-Fonte)")
        plataforma_alvo = st.selectbox("Selecione a Plataforma", ["TradingView (Pine Script)", "MetaTrader 5 (MQL5)", "MetaTrader 4 (MQL4)", "Tradovate (JavaScript)"])
        
        if plataforma_alvo == "TradingView (Pine Script)":
            codigo_export = f"//@version=5\nstrategy('SMC/ICT Engine - {ativo_selecionado}', overlay=true)\n\n// Lógica básica convertida\nliq_sweep = low < ta.lowest(low, 20)[1]\nmss = close > high[1]\n\nif liq_sweep[2] and mss[1]\n    strategy.entry('Long', strategy.long)"
        elif plataforma_alvo == "MetaTrader 5 (MQL5)":
            codigo_export = f"//+------------------------------------------------------------------+\n//| Expert Advisor gerado pelo Quant Master (MQL5)                   |\n//+------------------------------------------------------------------+\n#include <Trade\Trade.mqh>\nCTrade trade;\n\nvoid OnTick() {{\n   // Inserir lógica de varredura de mínima de 20 barras (iLowest)\n   // Inserir lógica de quebra de estrutura (MSS)\n   // trade.Buy(0.1);\n}}"
        elif plataforma_alvo == "Tradovate (JavaScript)":
            codigo_export = f"const predef = require('./tools/predef');\nconst meta = require('./tools/meta');\n\nmodule.exports = {{\n    map(d, i, history) {{\n        // Lógica de Order Block & FVG para Tradovate\n        return {{}};\n    }}\n}};"
        else:
            codigo_export = "// Código base para MT4..."
            
        st.code(codigo_export, language="javascript" if "Tradovate" in plataforma_alvo else "cpp")

# ==========================================
# ABA 4: VISÃO BOOKMAP (MAPA DE LIQUIDEZ SINTÉTICO)
# ==========================================
with aba4:
    st.subheader(f"🔍 Bookmap Sintético e Pontos de Execução")
    
    if st.session_state.df_backtest.empty:
        st.warning("⚠️ Você precisa rodar o Backtest na aba 'Motor Quant' primeiro para gerar o mapa de liquidez.")
    else:
        df_bk = st.session_state.df_backtest.copy()
        
        # Filtra os últimos 200 candles para não pesar a renderização do Heatmap 3D
        df_bk = df_bk.tail(200)
        
        st.markdown(f"**Ativo:** {st.session_state.ativo_atual} | Exibindo mapa de densidade de volume dos últimos 200 candles.")
        
        # Algoritmo de Criação do Heatmap (Volume Profile ao longo do tempo)
        min_price = df_bk['Low'].min()
        max_price = df_bk['High'].max()
        price_bins = np.linspace(min_price, max_price, 50)
        
        heatmap_z = np.zeros((len(price_bins), len(df_bk)))
        
        for i in range(len(df_bk)):
            l, h, v = df_bk['Low'].iloc[i], df_bk['High'].iloc[i], df_bk['Volume'].iloc[i]
            for j, p in enumerate(price_bins):
                if l <= p <= h:
                    heatmap_z[j, i] = v  # Distribui o volume onde o preço passou
        
        # Plotagem do Bookmap Sintético
        fig_bookmap = go.Figure()
        
        # Camada 1: O Fundo de Liquidez (Heatmap)
        fig_bookmap.add_trace(go.Heatmap(
            z=heatmap_z,
            x=df_bk.index,
            y=price_bins,
            colorscale='Inferno',
            showscale=True,
            colorbar=dict(title="Liquidez"),
            opacity=0.7,
            name="Depth/Volume"
        ))
        
        # Camada 2: A Ação do Preço (Candles)
        fig_bookmap.add_trace(go.Candlestick(
            x=df_bk.index,
            open=df_bk['Open'], high=df_bk['High'], low=df_bk['Low'], close=df_bk['Close'],
            name="Preço",
            increasing_line_color='rgba(0, 255, 0, 0.8)',
            decreasing_line_color='rgba(255, 0, 0, 0.8)'
        ))
        
        # Camada 3: Marcações de Entrada Automáticas
        sinais_ativos = st.session_state.sinais_gerados
        if sinais_ativos:
            sinal_principal = sinais_ativos[0] # Pega o primeiro setup selecionado
            entradas = df_bk[df_bk[sinal_principal] == 1]
            saidas = df_bk[df_bk[sinal_principal] == -1] # Caso haja lógica de venda/short
            
            # Plota Setas de Compra (Triângulo Verde Ciano)
            fig_bookmap.add_trace(go.Scatter(
                x=entradas.index, y=entradas['Low'] * 0.998,
                mode='markers', marker=dict(symbol='triangle-up', size=16, color='cyan', line=dict(color='white', width=1)),
                name='Entrada Automática (Long)'
            ))
            
            # Simulação de Saída de Take Profit (Traça uma linha 3 candles depois)
            if not entradas.empty:
                tp_index = [df_bk.index[min(df_bk.index.get_loc(idx) + 3, len(df_bk)-1)] for idx in entradas.index]
                tp_prices = entradas['Close'] + (risco_por_trade * 2.0 / 100) # Preço de saída estipulado genérico
                fig_bookmap.add_trace(go.Scatter(
                    x=tp_index, y=tp_prices,
                    mode='markers', marker=dict(symbol='star', size=14, color='gold'),
                    name='Saída (Take Profit / Alvo)'
                ))

        fig_bookmap.update_layout(
            template='plotly_dark',
            height=700,
            xaxis_rangeslider_visible=False,
            title="Bookmap Visualizer: Injeção de Liquidez vs Price Action",
            yaxis_title="Preço ($)"
        )
        
        st.plotly_chart(fig_bookmap, use_container_width=True)
        
        st.info("💡 **Como ler esta tela:** As áreas mais brilhantes (amarelo/laranja) mostram nós de alta liquidez e forte briga institucional. Quando o seu sinal de entrada (Ciano) pisca em cima ou logo após capturar a liquidez de uma zona brilhante inferior, confirma-se o viés do algoritmo.")
