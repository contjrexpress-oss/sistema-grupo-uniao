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

def atualizar_status(id_cadastro, novo_status):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("UPDATE cadastros SET status = ? WHERE id = ?", (novo_status, id_cadastro))
    conn.commit()
    conn.close()

def excluir_cadastro(id_cadastro):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("DELETE FROM cadastros WHERE id = ?", (id_cadastro,))
    conn.commit()
    conn.close()

def carregar_cadastros_basicos():
    conn = sqlite3.connect('grupouniao.db')
    df = pd.read_sql_query("SELECT id, data_cadastro, nome, cpf, telefone, moto, placa, regiao, status FROM cadastros ORDER BY id DESC", conn)
    conn.close()
    return df

def carregar_cadastro_completo(id_cadastro):
    conn = sqlite3.connect('grupouniao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cadastros WHERE id=?", (id_cadastro,))
    colunas = [description[0] for description in c.description]
    registro = c.fetchone()
    conn.close()
    if registro:
        return dict(zip(colunas, registro))
    return None

# ==========================================
# GERAÇÃO DE PDF
# ==========================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'GRUPO UNIÃO PRIME RJ', 0, 1, 'C')
        self.ln(5)

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
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0) # Cor do texto preta

    pdf.chapter_title("Ficha de Cadastro de Motoboy")
    pdf.ln(2)

    # Status
    status_text = dados.get('status', 'Pendente')
    if status_text == 'Aprovado':
        pdf.set_text_color(0, 128, 0) # Verde
    elif status_text == 'Rejeitado':
        pdf.set_text_color(255, 0, 0) # Vermelho
    else:
        pdf.set_text_color(255, 165, 0) # Laranja
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Status: {status_text}", 0, 1, 'C')
    pdf.set_text_color(0, 0, 0) # Volta para preto
    pdf.ln(5)

    pdf.chapter_title("Dados Pessoais")
    pdf.chapter_body("Nome Completo", dados['nome'])
    pdf.chapter_body("CPF", dados['cpf'])
    pdf.chapter_body("Telefone", dados['telefone'])
    pdf.chapter_body("Data do Cadastro", dados['data_cadastro'])
    pdf.ln(2)

    pdf.chapter_title("Dados do Veículo")
    pdf.chapter_body("Moto", dados['moto'])
    pdf.chapter_body("Placa", dados['placa'])
    pdf.ln(2)

    pdf.chapter_title("Dados Operacionais")
    pdf.chapter_body("Região de Trabalho", dados['regiao'])
    pdf.ln(2)

    # Adicionar Termo de Aceite
    pdf.chapter_title("Termo de Aceite")
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, "O motoboy aceitou os termos e regras de serviço do Grupo União Prime RJ.", 0, 'L')
    pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
init_db()

# Variável de estado para login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Sidebar para navegação
with st.sidebar:
    st.image("https://i.imgur.com/your_logo_here.png", use_column_width=True) # Substitua pela URL do seu logo
    st.title("Sistema Grupo União")

    if not st.session_state.logged_in:
        st.subheader("Acesso Rápido")
        st.info("Para motoboys: use o menu 'Cadastro'.")
        st.info("Para administradores: use o menu 'Administração'.")

        st.markdown("---")
        st.header("Navegação")
        pagina_selecionada = st.radio(" ", ["🏠 Início", "📝 Cadastro"])
    else:
        st.header("Navegação")
        pagina_selecionada = st.radio(" ", ["🏠 Início", "📝 Cadastro", "⚙️ Administração"])

# --- Página Inicial (Home) ---
if pagina_selecionada == "🏠 Início":
    st.title("👋 Bem-vindo ao Grupo União!")
    st.markdown("""
        Estamos cadastrando novos motoboys para atuar em diversas regiões. 
        Se você tem compromisso e responsabilidade, junte-se a nós.

        ### Requisitos:
        *   CNH e CRLV em dia
        *   Moto com baú
        *   Comprovante de residência

        👉 Acesse o menu lateral e clique em **'Formulário de Cadastro'**.

        ---

        ### Para Administradores:
        Acesse o menu lateral e clique em **'Administração'** para gerenciar os cadastros.
    """)

# --- Página de Cadastro ---
elif pagina_selecionada == "📝 Cadastro":
    st.title("📝 Formulário de Cadastro de Motoboy")
    st.markdown("Preencha todos os campos e anexe os documentos solicitados.")

    with st.form("cadastro_motoboy", clear_on_submit=True):
        st.subheader("Dados Pessoais")
        nome = st.text_input("Nome Completo *")
        cpf = st.text_input("CPF *", max_chars=11)
        telefone = st.text_input("Telefone (WhatsApp) *", placeholder="(XX) XXXXX-XXXX")

        st.subheader("Dados do Veículo")
        moto = st.text_input("Modelo da Moto *")
        placa = st.text_input("Placa da Moto *", max_chars=7)
        regiao = st.text_input("Região que costuma trabalhar (ex: Centro, Zona Sul, Barra, etc.) *")

        st.subheader("Documentos (Imagens ou PDFs)")
        cnh = st.file_uploader("Foto da CNH *", type=['png', 'jpg', 'jpeg', 'pdf'])
        crlv = st.file_uploader("Documento da moto (CRLV) *", type=['png', 'jpg', 'jpeg', 'pdf'])
        comprovante = st.file_uploader("Comprovante de residência *", type=['png', 'jpg', 'jpeg', 'pdf'])
        foto_moto = st.file_uploader("Foto da moto pegando a placa e baú *", type=['png', 'jpg', 'jpeg', 'pdf'])
        selfie = st.file_uploader("Foto do Rosto (selfie) *", type=['png', 'jpg', 'jpeg', 'pdf'])

        st.subheader("Termo de Aceite")
        conhecer_regras = st.radio("Quer conhecer as regras da empresa?", ["Sim", "Não"])
        aceite = st.checkbox("Aceito os termos e regras de serviço *")

        submit_button = st.form_submit_button("Enviar Cadastro")

        if submit_button:
            if not nome or not cpf or not telefone or not moto or not placa or not regiao or not aceite:
                st.error("⚠️ Por favor, preencha todos os campos obrigatórios (*) e aceite os termos antes de enviar.")
            elif not cnh or not crlv or not comprovante or not foto_moto or not selfie:
                st.error("⚠️ Por favor, faça o upload de todos os documentos obrigatórios.")
            else:
                arquivos = {
                    'cnh': {'bytes': cnh.getvalue(), 'name': cnh.name},
                    'crlv': {'bytes': crlv.getvalue(), 'name': crlv.name},
                    'comprovante': {'bytes': comprovante.getvalue(), 'name': comprovante.name},
                    'foto_moto': {'bytes': foto_moto.getvalue(), 'name': foto_moto.name},
                    'selfie': {'bytes': selfie.getvalue(), 'name': selfie.name},
                }
                salvar_cadastro(nome, cpf, telefone, moto, placa, regiao, arquivos)
                st.success(f"✅ Cadastro de {nome} realizado com sucesso! Seus documentos foram recebidos pela equipe do Grupo União.")

# --- Página de Administração ---
elif pagina_selecionada == "⚙️ Administração":
    st.title("⚙️ Painel Administrativo")

    if not st.session_state.logged_in:
        st.subheader("Login de Administrador")
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            login_button = st.form_submit_button("Entrar")

            if login_button:
                if verificar_login(username, password):
                    st.session_state.logged_in = True
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    else:
        st.success(f"Bem-vindo, {st.session_state.username}!")

        df_cadastros = carregar_cadastros_basicos()

        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Tabela Geral", "🔎 Conferência Detalhada", "➕ Novo Admin"])

        with tab1:
            st.subheader("Visão Geral dos Cadastros")
            if df_cadastros.empty:
                st.info("Nenhum cadastro recebido até o momento para exibir no dashboard.")
            else:
                total = len(df_cadastros)
                pendentes = len(df_cadastros[df_cadastros['status'] == 'Pendente'])
                aprovados = len(df_cadastros[df_cadastros['status'] == 'Aprovado'])
                rejeitados = len(df_cadastros[df_cadastros['status'] == 'Rejeitado'])

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total de Cadastros", total)
                c2.metric("Pendentes ⏳", pendentes)
                c3.metric("Aprovados ✅", aprovados)
                c4.metric("Rejeitados ❌", rejeitados)

                st.markdown("---")
                st.write("**Distribuição de Status**")
                status_counts = df_cadastros['status'].value_counts()
                st.bar_chart(status_counts, color="#1E3A8A")

        with tab2:
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

        with tab3:
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