import streamlit as st
import sqlite3
import pandas as pd
import datetime
import hashlib
from fpdf import FPDF

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E ESTILO
# ==========================================
st.set_page_config(page_title="Grupo União - Sistema", page_icon="🏍️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    h1, h2, h3 { color: #1E3A8A; font-family: sans-serif; }
    .stButton>button { background-color: #1E3A8A; color: white; border-radius: 5px; }
    .stButton>button:hover { background-color: #152b66; color: white; }
    .status-aprovado { color: green; font-weight: bold; }
    .status-rejeitado { color: red; font-weight: bold; }
    .status-pendente { color: orange; font-weight: bold; }
    .metric-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
    .stExpander { border-radius: 8px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stExpander > div > div > p { font-weight: bold; color: #1E3A8A; }
    .stFileUploader { margin-top: 10px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DO BANCO DE DADOS
# ==========================================
def init_db():
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS adms (
                    username TEXT PRIMARY KEY, 
                    password TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS cadastros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_cadastro TEXT,
                    nome TEXT,
                    cpf TEXT,
                    telefone TEXT,
                    moto TEXT,
                    placa TEXT,
                    regiao TEXT,
                    status TEXT DEFAULT 'Pendente',
                    cnh BLOB, cnh_nome TEXT,
                    crlv BLOB, crlv_nome TEXT,
                    comprovante BLOB, comprovante_nome TEXT,
                    foto_moto BLOB, foto_moto_nome TEXT,
                    selfie BLOB, selfie_nome TEXT)''')

    try:
        c.execute("ALTER TABLE cadastros ADD COLUMN status TEXT DEFAULT 'Pendente'")
    except sqlite3.OperationalError:
        pass

    c.execute("SELECT * FROM adms WHERE username='admin'")
    if not c.fetchone():
        senha_hash = hashlib.sha256('123'.encode()).hexdigest()
        c.execute("INSERT INTO adms VALUES (?, ?)", ('admin', senha_hash))

    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(username, password):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("SELECT password FROM adms WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return True
    return False

def adicionar_adm(username, password):
    try:
        conn = sqlite3.connect('grupouniao.db')
        c = conn.cursor()
        c.execute("INSERT INTO adms VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def salvar_cadastro(nome, cpf, telefone, moto, placa, regiao, arquivos):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute('''INSERT INTO cadastros 
                 (data_cadastro, nome, cpf, telefone, moto, placa, regiao, status,
                  cnh, cnh_nome, crlv, crlv_nome, comprovante, comprovante_nome, 
                  foto_moto, foto_moto_nome, selfie, selfie_nome)
                 VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendente', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (data_atual, nome, cpf, telefone, moto, placa, regiao,
               arquivos['cnh']['bytes'], arquivos['cnh']['name'],
               arquivos['crlv']['bytes'], arquivos['crlv']['name'],
               arquivos['comprovante']['bytes'], arquivos['comprovante']['name'],
               arquivos['foto_moto']['bytes'], arquivos['foto_moto']['name'],
               arquivos['selfie']['bytes'], arquivos['selfie']['name']))
    conn.commit()
    conn.close()

def carregar_cadastros():
    conn = sqlite3.connect('grupouniao.db')
    df = pd.read_sql_query("SELECT * FROM cadastros", conn)
    conn.close()
    return df

def carregar_cadastro_completo(id_cadastro):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cadastros WHERE id=?", (id_cadastro,))
    dados = c.fetchone()
    conn.close()
    if dados:
        colunas = [description[0] for description in c.description]
        return dict(zip(colunas, dados))
    return None

def atualizar_status(id_cadastro, novo_status):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("UPDATE cadastros SET status=? WHERE id=?", (novo_status, id_cadastro))
    conn.commit()
    conn.close()

def excluir_cadastro(id_cadastro):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("DELETE FROM cadastros WHERE id=?", (id_cadastro,))
    conn.commit()
    conn.close()

def gerar_pdf_ficha(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Título
    pdf.set_fill_color(30, 58, 138) # Azul escuro
    pdf.rect(0, 0, 210, 20, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "FICHA DE CADASTRO - GRUPO UNIÃO PRIME RJ", 0, 1, 'C')
    pdf.ln(5)

    pdf.set_text_color(0, 0, 0) # Preto
    pdf.set_font("Arial", size=10)

    # Função auxiliar para adicionar seção
    def add_section(title, data_dict):
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(230, 230, 230) # Cinza claro
        pdf.cell(0, 8, title, 0, 1, 'L', 1)
        pdf.set_font("Arial", size=10)
        pdf.ln(2)
        for key, value in data_dict.items():
            pdf.multi_cell(0, 5, f"• {key}: {value}")
        pdf.ln(5)

    # Dados Pessoais
    dados_pessoais = {
        "Nome Completo": dados['nome'],
        "CPF": dados['cpf'],
        "Telefone": dados['telefone'],
        "Data de Cadastro": dados['data_cadastro'],
        "Status": dados['status']
    }
    add_section("Dados Pessoais", dados_pessoais)

    # Dados do Veículo
    dados_veiculo = {
        "Moto": dados['moto'],
        "Placa": dados['placa']
    }
    add_section("Dados do Veículo", dados_veiculo)

    # Dados Operacionais
    dados_operacionais = {
        "Região de Trabalho": dados['regiao']
    }
    add_section("Dados Operacionais", dados_operacionais)

    # Documentos (apenas nomes dos arquivos)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, "Documentos Anexados", 0, 1, 'L', 1)
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    pdf.multi_cell(0, 5, f"• CNH: {dados['cnh_nome']}")
    pdf.multi_cell(0, 5, f"• CRLV: {dados['crlv_nome']}")
    pdf.multi_cell(0, 5, f"• Comprovante de Residência: {dados['comprovante_nome']}")
    pdf.multi_cell(0, 5, f"• Foto da Moto: {dados['foto_moto_nome']}")
    pdf.multi_cell(0, 5, f"• Selfie: {dados['selfie_nome']}")
    pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    # Sidebar para navegação do Admin
    st.sidebar.image("https://i.imgur.com/XqwkeselctWdszxkOJaqI5FQigDAantl8IX2D0gu2DFGl.png", use_column_width=True) # Logo JR Entregas
    st.sidebar.title("Painel Administrativo")
    pagina_adm = st.sidebar.radio("Navegação", ["📊 Dashboard", "📋 Tabela Geral", "🔎 Conferência Detalhada", "➕ Criar Admin"])

    df_cadastros = carregar_cadastros()

    if pagina_adm == "📊 Dashboard":
        st.title("📊 Dashboard de Cadastros")

        total_cadastros = len(df_cadastros)
        pendentes = df_cadastros[df_cadastros['status'] == 'Pendente'].shape[0]
        aprovados = df_cadastros[df_cadastros['status'] == 'Aprovado'].shape[0]
        rejeitados = df_cadastros[df_cadastros['status'] == 'Rejeitado'].shape[0]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>Total</h3><h1>{total_cadastros}</h1></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h3>Pendentes</h3><h1 style='color: orange;'>{pendentes}</h1></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h3>Aprovados</h3><h1 style='color: green;'>{aprovados}</h1></div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div class='metric-card'><h3>Rejeitados</h3><h1 style='color: red;'>{rejeitados}</h1></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Distribuição de Status")
        if not df_cadastros.empty:
            status_counts = df_cadastros['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            st.bar_chart(status_counts.set_index('Status'))
        else:
            st.info("Nenhum dado para exibir no dashboard ainda.")

    elif pagina_adm == "📋 Tabela Geral":
        st.subheader("Todos os Cadastros")
        if df_cadastros.empty:
            st.info("Nenhum cadastro recebido até o momento.")
        else:
            busca_tabela = st.text_input("🔍 Buscar por Nome ou CPF:", placeholder="Digite para filtrar a tabela...", key="busca_tab2")
            df_tab2 = df_cadastros.copy()

            if busca_tabela:
                df_tab2 = df_tab2[
                    df_tab2['nome'].str.contains(busca_tabela, case=False, na=False) | 
                    df_tab2['cpf'].str.contains(busca_tabela, case=False, na=False)
                ]

            st.dataframe(df_tab2, use_container_width=True, hide_index=True)
            st.download_button(
                label="📥 Exportar Tabela para Excel (CSV)",
                data=df_tab2.to_csv(index=False).encode('utf-8'),
                file_name='cadastros_grupouniao.csv',
                mime='text/csv',
            )

    elif pagina_adm == "🔎 Conferência Detalhada":
        st.subheader("Conferência e Aprovação")
        if df_cadastros.empty:
            st.warning("Não há cadastros para conferir.")
        else:
            busca_conf = st.text_input("🔍 Buscar por Nome ou CPF:", placeholder="Digite para encontrar um motoboy específico...", key="busca_tab3")
            df_tab3 = df_cadastros.copy()

            if busca_conf:
                df_tab3 = df_tab3[
                    df_tab3['nome'].str.contains(busca_conf, case=False, na=False) | 
                    df_tab3['cpf'].str.contains(busca_conf, case=False, na=False)
                ]

            if df_tab3.empty:
                st.info("Nenhum motoboy encontrado com esse Nome ou CPF.")
            else:
                opcoes = df_tab3.apply(lambda row: f"ID: {row['id']} - {row['nome']} ({row['status']})", axis=1).tolist()
                selecao = st.selectbox("Selecione o motoboy para conferência:", opcoes)

                if selecao:
                    id_selecionado = int(selecao.split(" - ")[0].replace("ID: ", ""))
                    dados = carregar_cadastro_completo(id_selecionado)
                    status_atual = dados.get('status', 'Pendente')

                    st.markdown("---")
                    col_info, col_docs = st.columns([1, 1.5])

                    with col_info:
                        st.markdown(f"### 👤 {dados['nome']}")
                        st.write(f"**Status:** <span class='status-{status_atual.lower()}'>{status_atual}</span>", unsafe_allow_html=True)
                        st.write(f"**Data:** {dados['data_cadastro']}")
                        st.write(f"**CPF:** {dados['cpf']}")
                        st.write(f"**Telefone:** {dados['telefone']}")
                        st.write(f"**Moto:** {dados['moto']} (Placa: {dados['placa']})")
                        st.write(f"**Região:** {dados['regiao']}")

                        st.markdown("#### Ações")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("✅ Aprovar", use_container_width=True):
                                atualizar_status(id_selecionado, "Aprovado")
                                st.rerun()
                        with c2:
                            if st.button("❌ Rejeitar", use_container_width=True):
                                atualizar_status(id_selecionado, "Rejeitado")
                                st.rerun()
                        with c3:
                            if st.button("🗑️ Excluir", use_container_width=True):
                                excluir_cadastro(id_selecionado)
                                st.rerun()

                        st.markdown("#### Exportação")
                        pdf_bytes = gerar_pdf_ficha(dados)
                        st.download_button(
                            label="📄 Baixar Ficha em PDF",
                            data=pdf_bytes,
                            file_name=f"Ficha_{dados['nome'].replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

                    with col_docs:
                        st.markdown("### 📄 Documentos Anexados")
                        docs_lista = [
                            ("CNH", dados['cnh'], dados['cnh_nome']),
                            ("CRLV", dados['crlv'], dados['crlv_nome']),
                            ("Comprovante", dados['comprovante'], dados['comprovante_nome']),
                            ("Foto da Moto", dados['foto_moto'], dados['foto_moto_nome']),
                            ("Selfie", dados['selfie'], dados['selfie_nome'])
                        ]

                        for titulo, arquivo_bytes, nome_arquivo in docs_lista:
                            with st.expander(f"Visualizar {titulo} ({nome_arquivo})"):
                                if nome_arquivo.lower().endswith('.pdf'):
                                    st.info("Este arquivo é um PDF. Clique abaixo para baixar.")
                                    st.download_button(label=f"Baixar {titulo}", data=arquivo_bytes, file_name=nome_arquivo, mime="application/pdf", key=f"dl_{titulo}_{id_selecionado}")
                                else:
                                    st.image(arquivo_bytes, caption=titulo, use_container_width=True)

    elif pagina_adm == "➕ Criar Admin":
        st.subheader("Adicionar Novo Administrador")
        with st.form("new_adm_form", clear_on_submit=True):
            new_user = st.text_input("Novo Usuário")
            new_pass = st.text_input("Nova Senha", type="password")
            btn_create = st.form_submit_button("Criar Conta")

            if btn_create:
                if new_user and new_pass:
                    if adicionar_adm(new_user, new_pass):
                        st.success(f"✅ Administrador '{new_user}' criado com sucesso!")
                    else:
                        st.error("⚠️ Este nome de usuário já existe.")
                else:
                    st.warning("Preencha usuário e senha.")

else: # Página de Login ou Início Público
    st.sidebar.image("https://i.imgur.com/XqwkeselctWdszxkOJaqI5FQigDAantl8IX2D0gu2DFGl.png", use_column_width=True) # Logo JR Entregas
    st.sidebar.title("Navegação")
    pagina_publica = st.sidebar.radio("Escolha uma opção", ["🏠 Início", "📝 Cadastro", "🔒 Login Admin"])

    if pagina_publica == "🏠 Início":
        st.title("🚀 Faça parte da nossa equipe!")
        st.markdown("""
            <p style='font-size: 1.1em;'>
            Estamos cadastrando novos motoboys para atuar em diversas regiões. Se você tem compromisso e responsabilidade, junte-se a nós.
            </p>
            <br>
        """, unsafe_allow_html=True)

        st.subheader("✅ Requisitos:")
        st.markdown("""
            - **CNH e CRLV** em dia 📄
            - **Moto com baú** 🏍️
            - **Comprovante de residência** 🏠
            - **Foto da moto** (pegando a placa e o baú) 📸
            - **Selfie** (foto do rosto) 🤳
        """)
        st.markdown("---")
        st.info("👉 Para se cadastrar, acesse o menu lateral e clique em '📝 Cadastro'.")

    elif pagina_publica == "📝 Cadastro":
        st.title("📝 Formulário de Cadastro")
        st.subheader("Preencha seus dados e envie os documentos")

        with st.form("cadastro_motoboy", clear_on_submit=True):
            st.markdown("### Dados Pessoais")
            nome = st.text_input("Nome Completo *")
            cpf = st.text_input("CPF *")
            telefone = st.text_input("Telefone (WhatsApp) *")

            st.markdown("### Dados da Moto")
            moto = st.text_input("Modelo da Moto *")
            placa = st.text_input("Placa da Moto *")
            regiao = st.text_input("Região que costuma trabalhar (ex: Centro, Zona Sul, Barra, etc.) *")

            st.markdown("### Documentos (apenas PNG, JPG, JPEG ou PDF)")
            cnh = st.file_uploader("Foto da CNH (frente e verso) *", type=['png', 'jpg', 'jpeg', 'pdf'])
            crlv = st.file_uploader("Documento da Moto (CRLV) *", type=['png', 'jpg', 'jpeg', 'pdf'])
            comprovante = st.file_uploader("Comprovante de residência *", type=['png', 'jpg', 'jpeg', 'pdf'])
            foto_moto = st.file_uploader("Foto da Moto (pegando a placa e o baú) *", type=['png', 'jpg', 'jpeg', 'pdf'])
            selfie = st.file_uploader("Foto do Rosto (selfie) *", type=['png', 'jpg', 'jpeg', 'pdf'])

            submitted = st.form_submit_button("Enviar Cadastro")

            if submitted:
                if nome and cpf and telefone and moto and placa and regiao and cnh and crlv and comprovante and foto_moto and selfie:
                    arquivos = {
                        'cnh': {'bytes': cnh.read(), 'name': cnh.name},
                        'crlv': {'bytes': crlv.read(), 'name': crlv.name},
                        'comprovante': {'bytes': comprovante.read(), 'name': comprovante.name},
                        'foto_moto': {'bytes': foto_moto.read(), 'name': foto_moto.name},
                        'selfie': {'bytes': selfie.read(), 'name': selfie.name}
                    }
                    salvar_cadastro(nome, cpf, telefone, moto, placa, regiao, arquivos)
                    st.success("✅ Cadastro enviado com sucesso! Aguarde a aprovação.")
                else:
                    st.error("⚠️ Por favor, preencha todos os campos e anexe todos os documentos obrigatórios.")

    elif pagina_publica == "🔒 Login Admin":
        st.title("🔒 Login do Administrador")
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            login_button = st.form_submit_button("Entrar")

            if login_button:
                if verificar_login(username, password):
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
