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

    # Adiciona o admin padrão 'jrentregas' com a senha '850916'
    c.execute("SELECT * FROM adms WHERE username='jrentregas'")
    if not c.fetchone():
        senha_hash = hashlib.sha256('850916'.encode()).hexdigest()
        c.execute("INSERT INTO adms VALUES (?, ?)", ('jrentregas', senha_hash))

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
                 (data_cadastro, nome, cpf, telefone, moto, placa, regiao, 
                  cnh, cnh_nome, crlv, crlv_nome, comprovante, comprovante_nome, 
                  foto_moto, foto_moto_nome, selfie, selfie_nome)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
    df = pd.read_sql_query("SELECT id, data_cadastro, nome, cpf, telefone, moto, placa, regiao, status FROM cadastros", conn)
    conn.close()
    return df

def carregar_cadastro_completo(id_cadastro):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cadastros WHERE id=?", (id_cadastro,))
    dados = c.fetchone()
    conn.close()
    if dados:
        colunas = [
            'id', 'data_cadastro', 'nome', 'cpf', 'telefone', 'moto', 'placa', 'regiao', 'status',
            'cnh', 'cnh_nome', 'crlv', 'crlv_nome', 'comprovante', 'comprovante_nome',
            'foto_moto', 'foto_moto_nome', 'selfie', 'selfie_nome'
        ]
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
    st.success(f"🗑️ Cadastro ID {id_cadastro} excluído permanentemente.")

def gerar_pdf_ficha(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Ficha de Cadastro de Motoboy", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 7, txt="Dados Pessoais:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 7, txt=f"Nome: {dados['nome']}", ln=True)
    pdf.cell(0, 7, txt=f"CPF: {dados['cpf']}", ln=True)
    pdf.cell(0, 7, txt=f"Telefone: {dados['telefone']}", ln=True)
    pdf.cell(0, 7, txt=f"Data de Cadastro: {dados['data_cadastro']}", ln=True)
    pdf.cell(0, 7, txt=f"Status: {dados['status']}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 7, txt="Dados da Moto:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 7, txt=f"Modelo: {dados['moto']}", ln=True)
    pdf.cell(0, 7, txt=f"Placa: {dados['placa']}", ln=True)
    pdf.cell(0, 7, txt=f"Região: {dados['regiao']}", ln=True)
    pdf.ln(5)

    # Documentos (apenas nomes dos arquivos)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 7, txt="Documentos Anexados:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 7, txt=f"CNH: {dados['cnh_nome']}", ln=True)
    pdf.cell(0, 7, txt=f"CRLV: {dados['crlv_nome']}", ln=True)
    pdf.cell(0, 7, txt=f"Comprovante de Residência: {dados['comprovante_nome']}", ln=True)
    pdf.cell(0, 7, txt=f"Foto da Moto: {dados['foto_moto_nome']}", ln=True)
    pdf.cell(0, 7, txt=f"Selfie: {dados['selfie_nome']}", ln=True)

    return pdf.output(dest='S').encode('latin1')

# ==========================================
# INICIALIZAÇÃO DO BANCO DE DADOS
# ==========================================
init_db()

# ==========================================
# LÓGICA DA APLICAÇÃO STREAMLIT
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Função para exibir a logo
def display_logo():
    st.markdown(
        f"""
        <div class="logo-container">
            <img src="https://i.imgur.com/XqwkeselctWdszxkOJaqI5FQigDAantl8IX2D0gu2DFGl.png" alt="Logo UNIÃO PRIME RJ">
        </div>
        """,
        unsafe_allow_html=True
    )

# Exibe a logo em todas as páginas
display_logo()

if st.session_state['logged_in']:
    st.title("⚙️ Painel Administrativo")

    # Navegação por abas para o Admin
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Tabela Geral", "🔎 Conferência Detalhada", "➕ Criar Admin"])

    with tab1:
        st.subheader("Visão Geral dos Cadastros")
        df_cadastros = carregar_cadastros()

        total_cadastros = len(df_cadastros)
        pendentes = df_cadastros[df_cadastros['status'] == 'Pendente'].shape[0]
        aprovados = df_cadastros[df_cadastros['status'] == 'Aprovado'].shape[0]
        rejeitados = df_cadastros[df_cadastros['status'] == 'Rejeitado'].shape[0]

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
            status_counts.columns = ['Status', 'Quantidade']
            st.bar_chart(status_counts.set_index('Status'))
        else:
            st.info("Nenhum cadastro para exibir no gráfico.")

    with tab2:
        st.subheader("Tabela Geral de Cadastros")
        df_cadastros = carregar_cadastros()

        if df_cadastros.empty:
            st.info("Nenhum cadastro encontrado.")
        else:
            busca_geral = st.text_input("🔍 Buscar por Nome ou CPF:", placeholder="Digite para encontrar um motoboy específico...", key="busca_tab2")
            df_filtrado = df_cadastros.copy()

            if busca_geral:
                df_filtrado = df_filtrado[
                    df_filtrado['nome'].str.contains(busca_geral, case=False, na=False) | 
                    df_filtrado['cpf'].str.contains(busca_geral, case=False, na=False)
                ]

            st.dataframe(df_filtrado, use_container_width=True)

    with tab3:
        st.subheader("Conferência Detalhada de Cadastros")
        df_cadastros = carregar_cadastros()

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
