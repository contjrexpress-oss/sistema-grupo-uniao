import streamlit as st
import sqlite3
import pandas as pd
import datetime
import hashlib
from fpdf import FPDF
import plotly.express as px # Esta é a linha que precisa da instalação do plotly

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

    /* Estilos para os novos cartões de métricas */
    .metric-box {
        border-radius: 8px;
        padding: 15px 20px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100px; /* Altura fixa para todos os cartões */
    }
    .metric-box h3 {
        color: white;
        margin: 0;
        font-size: 1.8em;
        font-weight: 600;
    }
    .metric-box p {
        color: rgba(255, 255, 255, 0.8);
        margin: 0;
        font-size: 0.9em;
    }
    .metric-box.total { background-color: #00BCD4; } /* Azul Ciano */
    .metric-box.pendente { background-color: #FF9800; } /* Laranja */
    .metric-box.aprovado { background-color: #4CAF50; } /* Verde */
    .metric-box.rejeitado { background-color: #F44336; } /* Vermelho */

    /* Ajustes para o gráfico */
    .stPlotlyChart {
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        padding: 10px;
        background-color: white;
    }

    /* Esconder a barra lateral padrão do Streamlit */
    .st-emotion-cache-vk3wp9 {
        display: none;
    }
    /* Ajustar o padding do conteúdo principal para ocupar o espaço */
    .st-emotion-cache-z5fcl4 {
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    /* Centralizar a logo no topo */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
        padding-top: 20px;
    }
    .logo-container img {
        max-width: 200px; /* Ajuste o tamanho da logo conforme necessário */
        height: auto;
    }
    /* Estilo para os botões de navegação no topo */
    .top-nav-buttons {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-bottom: 30px;
    }
    .top-nav-buttons .stButton > button {
        background-color: #1E3A8A;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 1em;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .top-nav-buttons .stButton > button:hover {
        background-color: #152b66;
    }
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
                    cnh BLOB,
                    cnh_nome TEXT,
                    crlv BLOB,
                    crlv_nome TEXT,
                    comprovante BLOB,
                    comprovante_nome TEXT,
                    foto_moto BLOB,
                    foto_moto_nome TEXT,
                    selfie BLOB,
                    selfie_nome TEXT,
                    status TEXT DEFAULT 'Pendente')''')

    # Adicionar administrador padrão se não existir
    if not c.execute("SELECT * FROM adms WHERE username = 'jrentregas'").fetchone():
        c.execute("INSERT INTO adms (username, password) VALUES (?, ?)", ('jrentregas', hashlib.sha256('850916'.encode()).hexdigest()))

    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(username, password):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    hashed_pass = hash_password(password)
    c.execute("SELECT * FROM adms WHERE username = ? AND password = ?", (username, hashed_pass))
    result = c.fetchone()
    conn.close()
    return result is not None

def adicionar_adm(username, password):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    try:
        hashed_pass = hash_password(password)
        c.execute("INSERT INTO adms (username, password) VALUES (?, ?)", (username, hashed_pass))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Usuário já existe
    finally:
        conn.close()

def salvar_cadastro(nome, cpf, telefone, moto, placa, regiao, arquivos):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    data_cadastro = datetime.date.today().strftime("%Y-%m-%d")

    c.execute("INSERT INTO cadastros (data_cadastro, nome, cpf, telefone, moto, placa, regiao, cnh, cnh_nome, crlv, crlv_nome, comprovante, comprovante_nome, foto_moto, foto_moto_nome, selfie, selfie_nome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (data_cadastro, nome, cpf, telefone, moto, placa, regiao, 
               arquivos['cnh']['bytes'], arquivos['cnh']['name'],
               arquivos['crlv']['bytes'], arquivos['crlv']['name'],
               arquivos['comprovante']['bytes'], arquivos['comprovante']['name'],
               arquivos['foto_moto']['bytes'], arquivos['foto_moto']['name'],
               arquivos['selfie']['bytes'], arquivos['selfie']['name']))
    conn.commit()
    conn.close()

def get_all_cadastros():
    conn = sqlite3.connect('grupouniao.db')
    df = pd.read_sql_query("SELECT id, data_cadastro, nome, cpf, telefone, moto, placa, regiao, status FROM cadastros", conn)
    conn.close()
    return df

def get_cadastro_details(cadastro_id):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cadastros WHERE id = ?", (cadastro_id,))
    columns = [description[0] for description in c.description]
    data = c.fetchone()
    conn.close()
    if data:
        return dict(zip(columns, data))
    return None

def atualizar_status(cadastro_id, status):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("UPDATE cadastros SET status = ? WHERE id = ?", (status, cadastro_id))
    conn.commit()
    conn.close()

def excluir_cadastro(cadastro_id):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("DELETE FROM cadastros WHERE id = ?", (cadastro_id,))
    conn.commit()
    conn.close()

# ==========================================
# FUNÇÕES DE GERAÇÃO DE PDF
# ==========================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Ficha de Cadastro de Motoboy', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, label, text):
        self.set_font('Arial', 'B', 10)
        self.cell(40, 7, label + ":", 0, 0, 'L')
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 7, text, 0, 'L')
        self.ln(1)

def gerar_pdf_ficha(dados):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.chapter_title("Dados Pessoais")
    pdf.chapter_body("Nome", dados['nome'])
    pdf.chapter_body("CPF", dados['cpf'])
    pdf.chapter_body("Telefone", dados['telefone'])
    pdf.chapter_body("Status", dados['status'])
    pdf.ln(5)

    pdf.chapter_title("Dados da Moto")
    pdf.chapter_body("Modelo da Moto", dados['moto'])
    pdf.chapter_body("Placa", dados['placa'])
    pdf.chapter_body("Região de Atuação", dados['regiao'])
    pdf.ln(5)

    # Documentos não são incorporados diretamente no PDF, apenas listados
    pdf.chapter_title("Documentos Anexados")
    pdf.chapter_body("CNH", dados['cnh_nome'])
    pdf.chapter_body("CRLV", dados['crlv_nome'])
    pdf.chapter_body("Comprovante de Residência", dados['comprovante_nome'])
    pdf.chapter_body("Foto da Moto", dados['foto_moto_nome'])
    pdf.chapter_body("Selfie", dados['selfie_nome'])
    pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1') # Retorna bytes do PDF

# ==========================================
# INICIALIZAÇÃO
# ==========================================
init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'pagina_publica' not in st.session_state:
    st.session_state['pagina_publica'] = "🏠 Início"
if 'pagina_adm' not in st.session_state:
    st.session_state['pagina_adm'] = "Dashboard" # Página padrão para admin

# ==========================================
# LAYOUT PRINCIPAL
# ==========================================

# Logo no topo para todas as páginas
st.markdown(
    f"""
    <div class="logo-container">
        <img src="https://i.imgur.com/XqwkeselctWdszxkOJaqI5FQigDAantl8IX2D0gu2DFGl.png" alt="Logo UNIÃO PRIME RJ">
    </div>
    """,
    unsafe_allow_html=True
)

if st.session_state['logged_in']:
    # Botão de Logout no canto superior direito da área administrativa
    col_title, col_logout = st.columns([0.8, 0.2])
    with col_logout:
        st.markdown("<div style='text-align: right; margin-top: 20px;'>", unsafe_allow_html=True)
        if st.button("Sair (Logout) 🚪", key="logout_btn"):
            st.session_state['logged_in'] = False
            st.session_state['pagina_publica'] = "🏠 Início" # Volta para a página inicial pública
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.title("Painel Administrativo 📊")

    # Navegação por abas para o administrador
    tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Tabela Geral", "Conferência Detalhada", "Criar Admin"])

    with tab1:
        st.subheader("Visão Geral dos Cadastros")
        df_cadastros = get_all_cadastros()

        total_cadastros = len(df_cadastros)
        pendentes = df_cadastros[df_cadastros['status'] == 'Pendente'].shape[0]
        aprovados = df_cadastros[df_cadastros['status'] == 'Aprovado'].shape[0]
        rejeitados = df_cadastros[df_cadastros['status'] == 'Rejeitado'].shape[0]

        # Cartões de Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
                <div class="metric-box total">
                    <h3>{total_cadastros}</h3>
                    <p>Total de Cadastros</p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="metric-box pendente">
                    <h3>{pendentes}</h3>
                    <p>Cadastros Pendentes</p>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="metric-box aprovado">
                    <h3>{aprovados}</h3>
                    <p>Cadastros Aprovados</p>
                </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
                <div class="metric-box rejeitado">
                    <h3>{rejeitados}</h3>
                    <p>Cadastros Rejeitados</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Distribuição de Status")
        if not df_cadastros.empty:
            status_counts = df_cadastros['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Contagem']

            fig = px.bar(status_counts, x='Status', y='Contagem', 
                         color='Status',
                         color_discrete_map={'Pendente': '#FF9800', 'Aprovado': '#4CAF50', 'Rejeitado': '#F44336'},
                         title='Cadastros por Status')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum cadastro para exibir no dashboard.")

    with tab2:
        st.subheader("Tabela Geral de Cadastros")
        df_cadastros_tabela = get_all_cadastros()
        if not df_cadastros_tabela.empty:
            st.dataframe(df_cadastros_tabela, use_container_width=True)
        else:
            st.info("Nenhum cadastro para exibir.")

    with tab3:
        st.subheader("Conferência Detalhada")
        df_cadastros_conferencia = get_all_cadastros()
        if not df_cadastros_conferencia.empty:
            cadastros_pendentes = df_cadastros_conferencia[df_cadastros_conferencia['status'] == 'Pendente']

            if not cadastros_pendentes.empty:
                # Exibir apenas os pendentes para conferência
                st.write("### Cadastros Pendentes para Conferência")
                st.dataframe(cadastros_pendentes[['id', 'data_cadastro', 'nome', 'cpf', 'status']], use_container_width=True)

                id_selecionado = st.selectbox("Selecione o ID do cadastro para conferir:", cadastros_pendentes['id'].tolist())

                if id_selecionado:
                    dados = get_cadastro_details(id_selecionado)
                    if dados:
                        st.markdown(f"### Detalhes do Cadastro ID: {id_selecionado} - Status: **{dados['status']}**")

                        col_info, col_docs = st.columns(2)
                        with col_info:
                            st.write(f"**Nome:** {dados['nome']}")
                            st.write(f"**CPF:** {dados['cpf']}")
                            st.write(f"**Telefone:** {dados['telefone']}")
                            st.write(f"**Moto:** {dados['moto']}")
                            st.write(f"**Placa:** {dados['placa']}")
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
            else:
                st.info("Não há cadastros pendentes para conferência no momento.")
        else:
            st.info("Nenhum cadastro para exibir na conferência detalhada.")

    with tab4:
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
    # Navegação por botões para o público
    col_home, col_cadastro, col_login = st.columns(3)
    with col_home:
        if st.button("🏠 Início", key="nav_home", use_container_width=True):
            st.session_state['pagina_publica'] = "🏠 Início"
    with col_cadastro:
        if st.button("📝 Cadastro", key="nav_cadastro", use_container_width=True):
            st.session_state['pagina_publica'] = "📝 Cadastro"
    with col_login:
        if st.button("🔒 Login Admin", key="nav_login", use_container_width=True):
            st.session_state['pagina_publica'] = "🔒 Login Admin"

    if 'pagina_publica' not in st.session_state:
        st.session_state['pagina_publica'] = "🏠 Início"

    if st.session_state['pagina_publica'] == "🏠 Início":
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
        st.info("👉 Para se cadastrar, clique em '📝 Cadastro' acima.")

    elif st.session_state['pagina_publica'] == "📝 Cadastro":
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

    elif st.session_state['pagina_publica'] == "🔒 Login Admin":
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
