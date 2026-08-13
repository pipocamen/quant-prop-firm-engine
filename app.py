import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io

st.set_page_config(page_title="Prop Firm ERP & Quant Master", layout="wide")

# ==========================================
# 0. INICIALIZAÇÃO DE BANCO DE DADOS LOCAL (SESSION STATE)
# ==========================================
if 'contas' not in st.session_state:
    st.session_state.contas = pd.DataFrame(columns=[
        'ID', 'Corretora/Mesa', 'Tipo_Conta', 'Status', 'Saldo_Inicial', 
        'Alvo_Lucro', 'Max_Drawdown', 'Drawdown_Diario', 'Tipo_Drawdown', 'Regra_Consistencia'
    ])

def adicionar_conta(dados):
    nova_linha = pd.DataFrame([dados])
    st.session_state.contas = pd.concat([st.session_state.contas, nova_linha], ignore_index=True)

# ==========================================
# ESTRUTURA DE NAVEGAÇÃO POR ABAS
# ==========================================
st.title("🛡️ Prop Firm Portfolio & Quant Master")
aba1, aba2, aba3 = st.tabs(["🗃️ Gestão de Contas (Prop Firms)", "📊 Dashboard de Portfólio", "⚙️ Motor Quantitativo & Monte Carlo"])

# ==========================================
# ABA 1: GESTÃO DE CONTAS (CADASTRO E REGRAS)
# ==========================================
with aba1:
    st.markdown("### 🏦 Central de Cadastros e Monitoramento")
    
    col_form, col_lista = st.columns([1, 2])
    
    with col_form:
        st.subheader("Nova Conta / Replicação")
        with st.form("form_conta"):
            prop_firm = st.text_input("Nome da Corretora/Mesa (Ex: Apex, FTMO, Topstep)")
            tipo_conta = st.selectbox("Frente de Operação (Laddering)", ["Instantânea (Fluxo de Caixa)", "Avaliação (Teste)", "Conta Real (Funded)"])
            status = st.selectbox("Status Atual", ["Ativa", "Aprovada/Paga", "Quebrada (Blown)"])
            
            saldo = st.number_input("Saldo Inicial ($)", min_value=1000, value=50000, step=1000)
            alvo = st.number_input("Alvo de Lucro / Saque ($)", min_value=0, value=3000, step=100)
            
            st.markdown("**Regras de Blindagem (Drawdown)**")
            max_dd = st.number_input("Drawdown Máximo Total ($)", min_value=100, value=2500, step=100)
            daily_dd = st.number_input("Drawdown Máximo Diário ($)", min_value=100, value=1250, step=100)
            tipo_dd = st.selectbox("Tipo de Trailing", ["EOD (End of Day)", "Trailing Intraday (Flutuante Máximo)", "Estático (Fixo no Saldo Inicial)"])
            consistencia = st.slider("Regra de Consistência (Máx % num único dia)", 0, 100, 30, step=5)
            
            submitted = st.form_submit_button("Cadastrar / Replicar Conta")
            if submitted and prop_firm != "":
                nova_id = f"{prop_firm[:3].upper()}-{np.random.randint(1000,9999)}"
                adicionar_conta({
                    'ID': nova_id, 'Corretora/Mesa': prop_firm, 'Tipo_Conta': tipo_conta, 'Status': status,
                    'Saldo_Inicial': saldo, 'Alvo_Lucro': alvo, 'Max_Drawdown': max_dd, 
                    'Drawdown_Diario': daily_dd, 'Tipo_Drawdown': tipo_dd, 'Regra_Consistencia': consistencia
                })
                st.success(f"Conta {nova_id} cadastrada com sucesso!")
                st.rerun()

    with col_lista:
        st.subheader("Monitoramento de Contas Ativas")
        if not st.session_state.contas.empty:
            st.dataframe(st.session_state.contas, use_container_width=True, hide_index=True)
            
            # Exportar/Importar CSV para não perder dados ao fechar o navegador
            csv = st.session_state.contas.to_csv(index=False).encode('utf-8')
            col_csv1, col_csv2 = st.columns(2)
            col_csv1.download_button(label="📥 Baixar Backup das Contas (CSV)", data=csv, file_name='minhas_contas_prop.csv', mime='text/csv')
            
            upload_csv = col_csv2.file_uploader("📤 Restaurar Backup (CSV)", type="csv")
            if upload_csv is not None:
                st.session_state.contas = pd.read_csv(upload_csv)
                st.success("Backup restaurado!")
                st.rerun()
                
            # Ferramenta para deletar conta
            conta_del = st.selectbox("Selecione uma ID para Deletar", st.session_state.contas['ID'].tolist())
            if st.button("Deletar Conta"):
                st.session_state.contas = st.session_state.contas[st.session_state.contas['ID'] != conta_del]
                st.rerun()
        else:
            st.info("Nenhuma conta cadastrada. Preencha o formulário ao lado.")

# ==========================================
# ABA 2: DASHBOARD DE PORTFÓLIO E ANÁLISE
# ==========================================
with aba2:
    if st.session_state.contas.empty:
        st.warning("Cadastre contas na Aba 1 para visualizar o Dashboard de Portfólio.")
    else:
        df_dash = st.session_state.contas
        
        st.markdown("### 📊 Visão Geral do Portfólio")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        capital_sob_gestao = df_dash[df_dash['Status'] == 'Ativa']['Saldo_Inicial'].sum()
        capacidade_risco = df_dash[df_dash['Status'] == 'Ativa']['Max_Drawdown'].sum()
        contas_ativas = len(df_dash[df_dash['Status'] == 'Ativa'])
        taxa_quebra = len(df_dash[df_dash['Status'] == 'Quebrada (Blown)']) / len(df_dash) * 100 if len(df_dash) > 0 else 0
        
        col_m1.metric("Capital Ativo sob Gestão", f"${capital_sob_gestao:,.2f}")
        col_m2.metric("Risco Total Permitido (Margem)", f"${capacidade_risco:,.2f}")
        col_m3.metric("Contas Ativas", contas_ativas)
        col_m4.metric("Taxa de Quebra Geral", f"{taxa_quebra:.1f}%")
        
        st.divider()
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            fig_status = px.pie(df_dash, names='Status', title='Distribuição por Status de Conta', hole=0.4, template='plotly_dark')
            st.plotly_chart(fig_status, use_container_width=True)
            
        with col_g2:
            fig_tipo = px.bar(df_dash[df_dash['Status'] == 'Ativa'], x='Tipo_Conta', y='Saldo_Inicial', color='Corretora/Mesa', 
                              title='Exposição de Capital por Tipo de Frente', template='plotly_dark', barmode='group')
            st.plotly_chart(fig_tipo, use_container_width=True)

# ==========================================
# ABA 3: MOTOR QUANTITATIVO (VINCULADO ÀS CONTAS)
# ==========================================
with aba3:
    st.markdown("### ⚙️ Engine Quantitativo Acoplado")
    
    col_q_side, col_q_main = st.columns([1, 3])
    
    with col_q_side:
        st.subheader("Configuração da Análise")
        ativo_input = st.text_input("Ativos", "NQ=F, ES=F")
        ativo_selecionado = st.selectbox("Ativo Atual", [x.strip() for x in ativo_input.split(",")])
        timeframe = st.selectbox("Tempo Gráfico", ["1m", "5m", "15m", "1h"], index=2)
        
        st.markdown("#### 🔗 Acoplar Regras de Prop Firm")
        if not st.session_state.contas.empty:
            conta_selecionada = st.selectbox("Importar Regras da Conta:", st.session_state.contas[st.session_state.contas['Status'] != 'Quebrada (Blown)']['ID'].tolist())
            
            # Puxa os dados da conta selecionada para travar o motor de Monte Carlo
            dados_conta = st.session_state.contas[st.session_state.contas['ID'] == conta_selecionada].iloc[0]
            sim_capital = dados_conta['Saldo_Inicial']
            sim_dd_limit = dados_conta['Max_Drawdown']
            sim_tipo_dd = dados_conta['Tipo_Drawdown']
            sim_consistencia = dados_conta['Regra_Consistencia']
            
            st.info(f"**Limites Importados:**\n- Drawdown: ${sim_dd_limit}\n- Tipo: {sim_tipo_dd}\n- Consistência Máx: {sim_consistencia}%/dia")
        else:
            st.warning("Nenhuma conta cadastrada. Usando valores padrões.")
            sim_capital, sim_dd_limit, sim_tipo_dd, sim_consistencia = 300000, 7500, "Estático", 30

        risco_por_trade = st.number_input("Risco por Operação ($)", value=float(sim_dd_limit * 0.1), step=50.0)
        meta_assertividade = st.slider("Alvo de Assertividade (%)", 50, 100, 80)

    with col_q_main:
        st.subheader("Seleção de Módulos Estratégicos (Institucional)")
        
        col_f1, col_f2 = st.columns(2)
        use_ict_2022 = col_f1.checkbox("ICT Modelo 2022 (Sweep + MSS)", value=True)
        use_smc_ob = col_f1.checkbox("SMC (Mitigação de Order Block)", value=False)
        use_vwap_z = col_f2.checkbox("Reversão VWAP Z-Score Institucional", value=True)
        use_lw_smash = col_f2.checkbox("Larry Williams Smash Day", value=False)
        
        # Códigos Pandas (Mega Dicionário Compactado)
        codigo_engine = ""
        sinais = []
        
        if use_ict_2022:
            codigo_engine += "\ndf['Liq_Sweep'] = df['Low'] < df['Low'].rolling(20).min().shift(1)\ndf['MSS'] = df['Close'] > df['High'].shift(1)\ndf['FVG'] = df['Low'].shift(-1) > df['High'].shift(1)\ndf['Signal_ICT'] = np.where(df['Liq_Sweep'].shift(2) & df['MSS'].shift(1) & df['FVG'], 1, 0)"
            sinais.append("Signal_ICT")
        if use_smc_ob:
            codigo_engine += "\ndf['BOS'] = df['Close'] > df['High'].rolling(10).max().shift(1)\ndf['OB_High'] = df['High'].shift(2)\ndf['Signal_SMC'] = np.where(df['BOS'].shift(2) & (df['Low'] <= df['OB_High']), 1, 0)"
            sinais.append("Signal_SMC")
        if use_vwap_z:
            codigo_engine += "\ndf['TP'] = (df['High'] + df['Low'] + df['Close']) / 3\ndf['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()\ndf['StDev'] = df['TP'].rolling(20).std()\ndf['Signal_VWAP'] = np.where(df['Close'] < (df['VWAP'] - (df['StDev'] * 2.5)), 1, 0)"
            sinais.append("Signal_VWAP")
        if use_lw_smash:
            codigo_engine += "\ndf['Close_Near_Low'] = df['Close'] < (df['Low'] + (df['High'] - df['Low']) * 0.33)\ndf['Under_Prev_Low'] = df['Close'] < df['Low'].shift(2)\ndf['Smash_Trigger'] = df['Close'] > df['High'].shift(1)\ndf['Signal_SMASH'] = np.where(df['Close_Near_Low'].shift(1) & df['Under_Prev_Low'].shift(1) & df['Smash_Trigger'], 1, 0)"
            sinais.append("Signal_SMASH")

        codigo_editavel = st.text_area("Código do Motor de Sinais (Editável):", value=codigo_engine, height=200)

        if st.button("🚀 Processar Setups e Filtrar pelo Risco da Conta Selecionada", type="primary") and len(sinais) > 0:
            df = yf.download(ativo_selecionado, period="60d", interval=timeframe, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df = df.dropna()
            
            local_vars = {'df': df.copy(), 'np': np}
            exec(codigo_editavel, {}, local_vars)
            df_calc = local_vars['df']
            df_calc['Retorno_Futuro'] = df_calc['Close'].shift(-3) - df_calc['Close']
            
            st.markdown(f"### 🛡️ Teste de Estresse (Focado na Regra: {sim_tipo_dd})")
            
            setups_aprovados = []
            
            for sinal in sinais:
                if sinal in df_calc.columns:
                    entradas = abs(df_calc[sinal]).sum()
                    wins = len(df_calc[((df_calc[sinal] == 1) & (df_calc['Retorno_Futuro'] > 0)) | ((df_calc[sinal] == -1) & (df_calc['Retorno_Futuro'] < 0))])
                    win_rate = (wins / entradas * 100) if entradas > 0 else 0
                    
                    # Simulação de Monte Carlo Ajustada para Trailing vs Static
                    falhas = 0
                    if entradas > 0:
                        for i in range(500):
                            cap = sim_capital
                            pico = sim_capital
                            for t in range(50):
                                if np.random.rand() <= (win_rate / 100):
                                    lucro = (risco_por_trade * 2.0)
                                    cap += lucro
                                else:
                                    cap -= risco_por_trade
                                
                                # Lógica de Drawdown Dinâmico (Mesa)
                                if "Trailing" in sim_tipo_dd:
                                    pico = max(pico, cap)
                                    dd_atual = pico - cap
                                else: # EOD ou Estático
                                    dd_atual = sim_capital - cap
                                    
                                if dd_atual >= sim_dd_limit:
                                    falhas += 1
                                    break
                                    
                    prob_sucesso = 100 - ((falhas / 500) * 100) if entradas > 0 else 0
                    
                    if prob_sucesso >= meta_assertividade and entradas > 0:
                        setups_aprovados.append({
                            "Setup": sinal.replace("Signal_", ""),
                            "Win Rate Real": f"{win_rate:.1f}%",
                            "Prob. Sobrevivência (Drawdown)": f"{prob_sucesso:.1f}%"
                        })
            
            if setups_aprovados:
                st.table(pd.DataFrame(setups_aprovados).sort_values(by="Prob. Sobrevivência (Drawdown)", ascending=False))
            else:
                st.error("Risco de Ruína Alto. O setup estourou o Drawdown máximo estabelecido nas regras desta conta.")
