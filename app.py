import streamlit as st
import pandas as pd
import datetime
import requests
import json
import base64

st.set_page_config(page_title="Painel de Prazos Arq", page_icon="📐", layout="wide")

st.title("📐 Painel de Prazos e Entregas")
st.caption("Gestão de cronograma para arquitetos e projetistas.")

# ---------------- CONFIGURAÇÃO GITHUB ----------------
# Pega os dados secretos que você configurou no Streamlit
TOKEN = st.secrets.get("GITHUB_TOKEN")
REPO = st.secrets.get("GITHUB_REPO")
ARQUIVO_DADOS = "dados_projetos.json"
URL_API = f"https://api.github.com/repos/{REPO}/contents/{ARQUIVO_DADOS}"

headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Função para carregar os dados do GitHub
def carregar_dados():
    if not TOKEN or not REPO:
        st.error("⚠️ Configure os 'Secrets' no painel do Streamlit para salvar os dados permanentemente.")
        return []
    
    response = requests.get(URL_API, headers=headers)
    if response.status_code == 200:
        conteudo_base64 = response.json()['content']
        conteudo_str = base64.b64decode(conteudo_base64).decode('utf-8')
        return json.loads(conteudo_str)
    elif response.status_code == 404:
        return [] # Se o arquivo não existe ainda, começa vazio
    else:
        st.error("Erro ao carregar dados do GitHub.")
        return []

# Função para salvar os dados no GitHub
def salvar_dados(projetos):
    if not TOKEN or not REPO:
        return
        
    # Pega o SHA do arquivo atual (o GitHub exige isso para atualizar)
    response = requests.get(URL_API, headers=headers)
    sha = response.json().get('sha') if response.status_code == 200 else None
    
    # Prepara o conteúdo
    conteudo_str = json.dumps(projetos, ensure_ascii=False, indent=4)
    conteudo_base64 = base64.b64encode(conteudo_str.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": "Atualizando painel de projetos",
        "content": conteudo_base64
    }
    if sha:
        data["sha"] = sha
        
    # Envia para o GitHub
    put_response = requests.put(URL_API, headers=headers, data=json.dumps(data))
    if put_response.status_code not in [200, 201]:
        st.error("Erro ao salvar os dados no GitHub. Verifique o Token.")

# Carrega os dados (na primeira vez que roda, ou se limpar o cache)
if 'projetos' not in st.session_state:
    st.session_state['projetos'] = carregar_dados()

# ---------------- SIDEBAR: CADASTRO ----------------
etapas_padrao = [
    "Levantamento / Estudo Preliminar",
    "Anteprojeto",
    "Projeto Legal",
    "Projeto Executivo",
    "Compatibilização",
    "Detalhamento"
]

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
                
                st.session_state['projetos'].append({
                    "Projeto": nome_projeto,
                    "Etapa": etapa,
                    "Início": data_inicio.strftime("%d/%m/%Y"),
                    "Entrega": data_entrega.strftime("%d/%m/%Y"),
                    "Status": status,
                    "Dias Restantes": dias_restantes,
                    "Data_Real": data_entrega.strftime("%Y-%m-%d")
                })
                
                # SALVA NO GITHUB
                salvar_dados(st.session_state['projetos'])
                st.success("Etapa salva permanentemente!")

# ---------------- ÁREA PRINCIPAL ----------------
if not st.session_state['projetos']:
    st.info("Nenhum projeto cadastrado. Adicione um no menu lateral.")
else:
    df = pd.DataFrame(st.session_state['projetos'])
    df['Data_Real'] = pd.to_datetime(df['Data_Real'])
    df = df.sort_values(by="Data_Real")
    
    df_exibicao = df.drop(columns=["Data_Real"])

    st.subheader("📋 Visão Geral dos Prazos")
    
    col1, col2, col3 = st.columns(3)
    atrasados = len(df[df["Dias Restantes"] < 0])
    entregas_hoje = len(df[df["Dias Restantes"] == 0])
    no_prazo = len(df[df["Dias Restantes"] > 0])
    
    col1.metric("Atrasados", atrasados, delta="-Urgente" if atrasados > 0 else "0", delta_color="inverse")
    col2.metric("Entregas Hoje", entregas_hoje)
    col3.metric("No Prazo", no_prazo)

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

    st.markdown("---")
    st.subheader("📢 Gerar Alerta de Cobrança/Entrega")
    projeto_alerta = st.selectbox("Selecione o projeto para gerar o alerta:", df_exibicao["Projeto"].unique())
    
    if projeto_alerta:
        etapas_projeto = df_exibicao[df_exibicao["Projeto"] == projeto_alerta]
        texto_alerta = f"*Alerta de Projeto: {projeto_alerta}*\n\n"
        
        for index, row in etapas_projeto.iterrows():
            if "Atrasado" in row["Status"] or "Hoje" in row["Status"] or "Atenção" in row["Status"]:
                texto_alerta += f"🚨 Etapa: *{row['Etapa']}*\n📅 Entrega: {row['Entrega']}\nStatus: {row['Status']}\n\n"
        
        if texto_alerta == f"*Alerta de Projeto: {projeto_alerta}*\n\n":
            texto_alerta += "Tudo em dia! Nenhuma etapa urgente no momento. 👍"
            
        st.text_area("Texto do Alerta (Copie e Cole no WhatsApp/Telegram):", texto_alerta, height=150)