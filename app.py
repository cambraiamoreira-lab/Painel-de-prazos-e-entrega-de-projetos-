import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Painel de Prazos Arq", page_icon="📐", layout="wide")

st.title("📐 Painel de Prazos e Entregas")
st.caption("Gestão de cronograma para arquitetos e projetistas.")

# Inicializa a lista de projetos na memória se não existir
if 'projetos' not in st.session_state:
    st.session_state['projetos'] = []

# Opções de etapas baseadas no mercado/Lei
etapas_padrao = [
    "Levantamento / Estudo Preliminar",
    "Anteprojeto",
    "Projeto Legal",
    "Projeto Executivo",
    "Compatibilização",
    "Detalhamento"
]

# ---------------- SIDEBAR: CADASTRO DE PROJETO ----------------
with st.sidebar:
    st.header("➕ Cadastrar Nova Etapa")
    
    with st.form("form_novo_projeto", clear_on_submit=True):
        nome_projeto = st.text_input("Nome do Projeto / Cliente", placeholder="Ex.: Residência Silva")
        etapa = st.selectbox("Etapa", etapas_padrao)
        data_inicio = st.date_input("Data de Início", datetime.date.today())
        data_entrega = st.date_input("Data de Entrega", datetime.date.today() + datetime.timedelta(days=15))
        
        botao_salvar = st.form_submit_button("Adicionar ao Painel")
        
        if botao_salvar:
            if nome_projeto.strip() == "":
                st.error("O nome do projeto é obrigatório.")
            else:
                # Calcula o status
                hoje = datetime.date.today()
                dias_restantes = (data_entrega - hoje).days
                
                if dias_restantes < 0:
                    status = "🔴 Atrasado"
                elif dias_restantes == 0:
                    status = "🟠 Entrega Hoje"
                elif dias_restantes <= 3:
                    status = "🟡 Atenção (Prazo curto)"
                else:
                    status = "🟢 No Prazo"
                
                # Adiciona o projeto na lista
                st.session_state['projetos'].append({
                    "Projeto": nome_projeto,
                    "Etapa": etapa,
                    "Início": data_inicio.strftime("%d/%m/%Y"),
                    "Entrega": data_entrega.strftime("%d/%m/%Y"),
                    "Status": status,
                    "Dias Restantes": dias_restantes,
                    "Data_Real": data_entrega # Guarda a data real para cálculo futuro se precisar
                })
                st.success("Etapa cadastrada com sucesso!")

# ---------------- ÁREA PRINCIPAL: PAINEL ----------------
if not st.session_state['projetos']:
    st.info("Nenhum projeto cadastrado ainda. Use o menu lateral para adicionar as etapas do seu projeto.")
else:
    df = pd.DataFrame(st.session_state['projetos'])
    
    # Ordena pelas entregas mais próximas
    df = df.sort_values(by="Data_Real")
    
    # Prepara o DataFrame para exibição (remove a coluna de data real)
    df_exibicao = df.drop(columns=["Data_Real"])

    st.subheader("📋 Visão Geral dos Prazos")
    
    # Métricas no topo
    col1, col2, col3 = st.columns(3)
    atrasados = len(df[df["Dias Restantes"] < 0])
    entregas_hoje = len(df[df["Dias Restantes"] == 0])
    no_prazo = len(df[df["Dias Restantes"] > 0])
    
    col1.metric("Atrasados", atrasados, delta="-Urgente" if atrasados > 0 else "0", delta_color="inverse")
    col2.metric("Entregas Hoje", entregas_hoje)
    col3.metric("No Prazo", no_prazo)

    # Exibição da tabela com cores
    def colorir_status(val):
        if "Atrasado" in val:
            return 'background-color: #ffcccc; color: #990000'
        elif "Hoje" in val:
            return 'background-color: #ffe5b4; color: #cc5200'
        elif "Atenção" in val:
            return 'background-color: #ffffcc; color: #808000'
        elif "No Prazo" in val:
            return 'background-color: #ccffcc; color: #006600'
        return ''

    st.dataframe(
        df_exibicao.style.map(colorir_status, subset=['Status']),
        use_container_width=True,
        hide_index=True
    )

    # ---------------- GERAÇÃO DE ALERTA ----------------
    st.markdown("---")
    st.subheader("📢 Gerar Alerta de Cobrança/Entrega")
    st.write("Como os alertas automáticos via Telegram exigem configuração de bot (faremos na V2), você pode gerar o texto pronto e colar no seu Telegram ou WhatsApp:")
    
    projeto_alerta = st.selectbox("Selecione o projeto para gerar o alerta:", df_exibicao["Projeto"].unique())
    
    if projeto_alerta:
        # Filtra as etapas do projeto selecionado
        etapas_projeto = df_exibicao[df_exibicao["Projeto"] == projeto_alerta]
        texto_alerta = f"*Alerta de Projeto: {projeto_alerta}*\n\n"
        
        for index, row in etapas_projeto.iterrows():
            if "Atrasado" in row["Status"] or "Hoje" in row["Status"] or "Atenção" in row["Status"]:
                texto_alerta += f"🚨 Etapa: *{row['Etapa']}*\n📅 Entrega: {row['Entrega']}\nStatus: {row['Status']}\n\n"
        
        if texto_alerta == f"*Alerta de Projeto: {projeto_alerta}*\n\n":
            texto_alerta += "Tudo em dia! Nenhuma etapa urgente no momento. 👍"
            
        st.text_area("Texto do Alerta (Copie e Cole):", texto_alerta, height=150)