import streamlit as st
import sqlite3
import pandas as pd
import datetime
import hashlib
from fpdf import FPDF
import plotly.express as px

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E ESTILO
# ==========================================
st.set_page_config(page_title="Grupo União - Sistema", page_icon="🏍️", layout="wide")

# CSS para estilização e remoção da barra lateral padrão
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
    .css-1lcbmhc, .css-1lcbmhc.e1fqkh3o0 {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:first-child {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:last-child {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:nth-child(2) {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:nth-child(3) {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:nth-child(4) {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:nth-child(5) {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:nth-child(6) {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:nth-child(7) {
        display: none;
    }
    .css-1lcbmhc.e1fqkh3o0 > div:nth-child(8) {
        display: none;
    }
    /* Adicione mais regras .css-1lcbmhc.e1fqkh3o0 > div:nth-child(X) { display: none; } se a barra lateral ainda aparecer */
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DE BANCO DE DADOS
# ==========================================
@st.cache_resource
def init_db():
    """Inicializa o banco de dados SQLite e cria as tabelas se não existirem."""
    try:
        conn = sqlite3.connect('motoboys.db')
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS motoboys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE NOT NULL,
                telefone TEXT NOT NULL,
                moto TEXT NOT NULL,
                placa TEXT NOT NULL,
                regiao TEXT NOT NULL,
                status TEXT DEFAULT 'Pendente',
                data_cadastro TEXT,
                cnh_path TEXT,
                crlv_path TEXT,
                comprovante_path TEXT,
                foto_moto_path TEXT,
                selfie_path TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        # Inserir admin padrão se não existir
        cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
        if cursor.fetchone() is None:
            hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", ('admin', hashed_password))
        conn.commit()
        return conn
    except sqlite3.Error as e:
        st.error(f"Erro ao inicializar o banco de dados: {e}")
        return None

conn = init_db()

def hash_password(password):
    """Gera o hash SHA256 de uma senha."""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(username, password):
    """Verifica as credenciais de login do administrador."""
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM admins WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result:
            stored_password_hash = result[0]
            return stored_password_hash == hash_password(password)
    return False

def salvar_cadastro(nome, cpf, telefone, moto, placa, regiao, arquivos):
    """Salva os dados do motoboy e seus documentos no banco de dados e no sistema de arquivos."""
    if conn:
        try:
            data_cadastro = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Salvar arquivos e obter seus caminhos
            paths = {}
            for doc_type, file_data in arquivos.items():
                file_extension = file_data['name'].split('.')[-1]
                file_name = f"{cpf}_{doc_type}.{file_extension}"
                file_path = f"documentos/{file_name}"

                # Criar diretório se não existir
                import os
                os.makedirs("documentos", exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(file_data['bytes'])
                paths[doc_type + '_path'] = file_path

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO motoboys (nome, cpf, telefone, moto, placa, regiao, data_cadastro, status,
                                     cnh_path, crlv_path, comprovante_path, foto_moto_path, selfie_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nome, cpf, telefone, moto, placa, regiao, data_cadastro, 'Pendente',
                  paths.get('cnh_path'), paths.get('crlv_path'), paths.get('comprovante_path'),
                  paths.get('foto_moto_path'), paths.get('selfie_path')))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            st.error("❌ Erro: CPF já cadastrado.")
            return False
        except sqlite3.Error as e:
            st.error(f"Erro ao salvar cadastro: {e}")
            return False
    return False

def get_motoboys():
    """Retorna todos os motoboys cadastrados."""
    if conn:
        return pd.read_sql_query("SELECT * FROM motoboys", conn)
    return pd.DataFrame()

def update_motoboy_status(motoboy_id, status):
    """Atualiza o status de um motoboy."""
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE motoboys SET status = ? WHERE id = ?", (status, motoboy_id))
        conn.commit()

def add_admin(username, password):
    """Adiciona um novo usuário administrador."""
    if conn:
        try:
            hashed_password = hash_password(password)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            st.error("❌ Erro: Nome de usuário já existe.")
            return False
        except sqlite3.Error as e:
            st.error(f"Erro ao adicionar administrador: {e}")
            return False
    return False

# ==========================================
# LAYOUT DO APP
# ==========================================

# Inicialização do estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'pagina_publica' not in st.session_state:
    st.session_state['pagina_publica'] = "🏠 Início"
if 'admin_page' not in st.session_state:
    st.session_state['admin_page'] = "Dashboard"

# Área Administrativa
if st.session_state['logged_in']:
    st.sidebar.empty() # Garante que a sidebar padrão não apareça na área admin

    # Cabeçalho da área administrativa com logo e botão de logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.image("logo_uniao_prime_rj.jpeg", width=150) # Logo na área administrativa
    with col2:
        if st.button("Sair (Logout)", key="admin_logout_btn"):
            st.session_state['logged_in'] = False
            st.session_state['pagina_publica'] = "🏠 Início"
            st.rerun()

    st.title("Painel Administrativo")

    # Navegação entre as páginas do administrador
    admin_pages = ["Dashboard", "Conferência de Cadastros", "Gerenciar Administradores"]
    st.session_state['admin_page'] = st.radio("Navegação", admin_pages, index=admin_pages.index(st.session_state['admin_page']))

    if st.session_state['admin_page'] == "Dashboard":
        st.subheader("Visão Geral dos Cadastros")
        motoboys_df = get_motoboys()

        if not motoboys_df.empty:
            total_cadastros = len(motoboys_df)
            pendentes = len(motoboys_df[motoboys_df['status'] == 'Pendente'])
            aprovados = len(motoboys_df[motoboys_df['status'] == 'Aprovado'])
            rejeitados = len(motoboys_df[motoboys_df['status'] == 'Rejeitado'])

            col_total, col_pendente, col_aprovado, col_rejeitado = st.columns(4)
            with col_total:
                st.markdown(f"<div class='metric-box total'><h3>{total_cadastros}</h3><p>Total de Cadastros</p></div>", unsafe_allow_html=True)
            with col_pendente:
                st.markdown(f"<div class='metric-box pendente'><h3>{pendentes}</h3><p>Cadastros Pendentes</p></div>", unsafe_allow_html=True)
            with col_aprovado:
                st.markdown(f"<div class='metric-box aprovado'><h3>{aprovados}</h3><p>Cadastros Aprovados</p></div>", unsafe_allow_html=True)
            with col_rejeitado:
                st.markdown(f"<div class='metric-box rejeitado'><h3>{rejeitados}</h3><p>Cadastros Rejeitados</p></div>", unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("Cadastros por Status")
            status_counts = motoboys_df['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            fig = px.pie(status_counts, values='Quantidade', names='Status', title='Distribuição de Cadastros por Status',
                         color_discrete_map={'Pendente':'orange', 'Aprovado':'green', 'Rejeitado':'red'})
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.subheader("Cadastros Recentes")
            st.dataframe(motoboys_df.sort_values('data_cadastro', ascending=False).head(10))
        else:
            st.info("Nenhum motoboy cadastrado ainda.")

    elif st.session_state['admin_page'] == "Conferência de Cadastros":
        st.subheader("Conferência e Aprovação de Motoboys")
        motoboys_df = get_motoboys()

        if not motoboys_df.empty:
            for index, motoboy in motoboys_df.iterrows():
                with st.expander(f"**{motoboy['nome']}** (CPF: {motoboy['cpf']}) - Status: **{motoboy['status']}**"):
                    st.write(f"**Telefone:** {motoboy['telefone']}")
                    st.write(f"**Moto:** {motoboy['moto']} - **Placa:** {motoboy['placa']}")
                    st.write(f"**Região:** {motoboy['regiao']}")
                    st.write(f"**Data de Cadastro:** {motoboy['data_cadastro']}")

                    st.markdown("---")
                    st.subheader("Documentos Anexados:")

                    doc_paths = {
                        "CNH": motoboy['cnh_path'],
                        "CRLV": motoboy['crlv_path'],
                        "Comprovante de Residência": motoboy['comprovante_path'],
                        "Foto da Moto": motoboy['foto_moto_path'],
                        "Selfie": motoboy['selfie_path']
                    }

                    for doc_name, path in doc_paths.items():
                        if path and os.path.exists(path):
                            st.download_button(
                                label=f"Baixar {doc_name}",
                                data=open(path, "rb").read(),
                                file_name=os.path.basename(path),
                                key=f"download_{motoboy['id']}_{doc_name}"
                            )
                            # Opcional: exibir imagem se for um formato suportado por st.image
                            if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                                st.image(path, caption=doc_name, width=300)
                            elif path.lower().endswith('.pdf'):
                                st.info(f"Visualização de PDF para {doc_name} não disponível diretamente. Por favor, baixe o arquivo.")
                        else:
                            st.warning(f"Documento '{doc_name}' não encontrado ou não anexado.")

                    st.markdown("---")
                    st.subheader("Ação:")
                    col_aprov, col_reprov = st.columns(2)
                    with col_aprov:
                        if st.button("✅ Aprovar", key=f"aprovar_{motoboy['id']}"):
                            update_motoboy_status(motoboy['id'], 'Aprovado')
                            st.success(f"Motoboy {motoboy['nome']} aprovado!")
                            st.rerun()
                    with col_reprov:
                        if st.button("❌ Rejeitar", key=f"rejeitar_{motoboy['id']}"):
                            update_motoboy_status(motoboy['id'], 'Rejeitado')
                            st.error(f"Motoboy {motoboy['nome']} rejeitado!")
                            st.rerun()
        else:
            st.info("Nenhum cadastro para conferir.")

    elif st.session_state['admin_page'] == "Gerenciar Administradores":
        st.subheader("Adicionar Novo Administrador")
        with st.form("add_admin_form", clear_on_submit=True):
            new_username = st.text_input("Nome de Usuário para o novo Admin")
            new_password = st.text_input("Senha para o novo Admin", type="password")
            add_admin_button = st.form_submit_button("Adicionar Admin")

            if add_admin_button:
                if new_username and new_password:
                    if add_admin(new_username, new_password):
                        st.success(f"Administrador '{new_username}' adicionado com sucesso!")
                    else:
                        st.error("Falha ao adicionar administrador. Verifique o nome de usuário.")
                else:
                    st.error("Por favor, preencha todos os campos.")

# Páginas Públicas (antes do login)
else:
    # Cabeçalho da página pública com logo e botões de navegação
    col_logo, col_spacer, col_cad, col_login = st.columns([2, 1, 1, 1])
    with col_logo:
        st.image("logo_uniao_prime_rj.jpeg", width=200) # Logo na página inicial
    with col_cad:
        if st.button("📝 Cadastro", key="public_cad_btn_header"):
            st.session_state['pagina_publica'] = "📝 Cadastro"
            st.rerun()
    with col_login:
        if st.button("🔒 Login Admin", key="public_login_btn_header"):
            st.session_state['pagina_publica'] = "🔒 Login Admin"
            st.rerun()

    st.markdown("---") # Linha divisória para separar o cabeçalho do conteúdo

    if st.session_state['pagina_publica'] == "🏠 Início":
        st.title("Bem-vindo ao Grupo União Prime RJ")
        st.markdown("""
            <p style='font-size: 1.1em;'>
                Estamos buscando motoboys dedicados para fazer parte da nossa equipe.
                Se você tem moto própria, baú e os documentos em dia, junte-se a nós.
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
        # Botões de navegação para Cadastro e Login Admin
        col_cad_footer, col_login_footer = st.columns(2)
        with col_cad_footer:
            if st.button("📝 Cadastre-se Agora", key="public_cad_btn_footer"):
                st.session_state['pagina_publica'] = "📝 Cadastro"
                st.rerun()
        with col_login_footer:
            if st.button("🔒 Acesso Administrativo", key="public_login_btn_footer"):
                st.session_state['pagina_publica'] = "🔒 Login Admin"
                st.rerun()

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
