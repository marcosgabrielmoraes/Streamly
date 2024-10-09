import streamlit as st
import openai
from openai import OpenAI
import logging
import hashlib
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)

# Constants
NUMBER_OF_MESSAGES_TO_DISPLAY = 20

# Retrieve and validate API key
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    st.error("Please add your OpenAI API key to the Streamlit secrets.toml file.")
    st.stop()

# Assign OpenAI API Key
client = OpenAI(api_key=OPENAI_API_KEY)

# Streamlit Page Configuration
st.set_page_config(
    page_title="CarAI - Intelligent Car Buying Assistant",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS for custom styling
st.markdown("""
<style>
.stButton>button {
    border: 1px solid #ccc;
    background-color: white;
    color: #444;
    padding: 0.25rem 0.75rem;
    border-radius: 30px;
    font-size: 14px;
    margin-right: 10px;
}
.stButton>button:hover {
    border-color: #888;
    color: #000;
}
.chat-container {
    max-width: 800px;
    margin: auto;
}
</style>
""", unsafe_allow_html=True)

# User authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    if 'users' not in st.session_state:
        st.session_state.users = {'Will': hash_password('1234')}
    return st.session_state.users

def save_users(users):
    st.session_state.users = users

def authenticate(username, password):
    users = load_users()
    if username in users and users[username] == hash_password(password):
        return True
    return False

def register_user(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = hash_password(password)
    save_users(users)
    return True

def login_register_ui():
    st.title("CarAI - Login")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab2:
        new_username = st.text_input("New Username", key="register_username")
        new_password = st.text_input("New Password", type="password", key="register_password")
        if st.button("Register"):
            if register_user(new_username, new_password):
                st.success("Registration successful. You can now log in.")
            else:
                st.error("Username already exists. Please choose a different username.")

def initialize_conversation():
    """Initialize the conversation history with system and assistant messages."""
    system_prompt = """
    Você é uma IA especializada em analisar veículos individuais e calcular a melhor forma de negociação com bancos. Seu objetivo é apresentar as opções de negócio e os lucros possíveis para o cliente de forma clara, objetiva e precisa. No final, você deve fornecer os dados de maneira simples e fácil de compreensão para ajudar o cliente a tomar decisões que impactarão sua vida.

    1. Coleta de Dados do Veículo e da Dívida:
    Coletar o número de parcelas já pagas, quantas parcelas faltam e quantas estão atrasadas.
    identificar o valor de cada parcela e o valor total da dívida.
    Consulte a Tabela FIPE para obter o valor atual do carro.
    identificar o banco que está com a dívida do veículo.

    2. Cálculo das Parcelas e do Valor de Quitação:
    Verifique quais parcelas estão em atraso e calcule o quanto ainda faltam para atingir o número necessário de 12 a 18 parcelas atrasadas para conseguir o melhor desconto do banco.
    Usar o percentual de desconto do banco com base nas informações fornecidas abaixo para calcular o valor total da quitação da dívida.
    A IA deve retirar automaticamente a faixa de desconto correta conforme o banco identificado.

    3. Análise de Bancos para Negociação:
    Bancos Destacados (Melhores para Negociação):
    Santander, Bradesco Financiamentos, BV, Votorantim (BV) Itaú : 70% a 80% de desconto com uma média de 18 parcelas atrasadas.
    Outros Bancos e suas Margens de Desconto:
    Banco Alfa : 60% a 70%
    Aymoré : 70% a 80%
    Banco do Brasil : 50% a 60%
    BMW, Caixa Econômica Federal, Mercedes-Benz, Mercantil, Porto Seguro Financeira, Volkswagen : 50% a 60%
    Daycoval, DigiMais, Fiat, GM/Chevrolet, Honda, Omni, Panamericano, Renner, Toyota : 60% a 70%
    HSBC/Bradesco, PSA (Peugeot Citroën), RCI Brasil (Renault) : 70% a 80%

    4. Sugestões de Estratégias de Negócio e Lucros Esperados:
    Opção 1: Vender o carro por 50% da FIPE (com quitação futura para terceiros)
    Opção 2: Alugar o carro por R$ 2.500/mês e vender por 100% da FIPE após o aluguel
    Opção 3: Se o carro já estiver pronto para quitação

    5. Validação dos Cálculos com Mensagens de Verificação
    6. Resultado Final que a IA deve entregar (com layout otimizado)
    7. Resumo Final para o Cliente
    8. Instruções adicionais para a IA:
    Apresente apenas os números e simplifique ao máximo a explicação, para que qualquer pessoa entenda facilmente os resultados.
    Valide todos os cálculos para garantir precisão e clareza.
    Destaque os lucros potenciais e as melhores opções de negócio de forma clara, utilizando layout otimizado com separadores para facilitar a leitura.
    """

    assistant_message = "Olá! Sou o CarAI, seu assistente especializado em análise de veículos e negociações bancárias. Como posso ajudar você hoje?"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": assistant_message}
    ]

def process_file(file):
    """Process the uploaded file."""
    try:
        content = file.getvalue()
        if file.type.startswith('image'):
            return f"[Imagem carregada: {file.name}]"
        else:
            return content.decode('utf-8')
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        return None

def on_chat_submit(chat_input, uploaded_file=None):
    """Handle chat input submissions and interact with the OpenAI API."""
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = initialize_conversation()

    user_input = chat_input.strip()
    
    if uploaded_file:
        file_content = process_file(uploaded_file)
        user_input += f"\n\nConteúdo do arquivo enviado:\n{file_content}"

    st.session_state.conversation_history.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state.conversation_history
        )
        assistant_reply = response.choices[0].message.content

        st.session_state.conversation_history.append({"role": "assistant", "content": assistant_reply})
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": assistant_reply})

    except Exception as e:
        logging.error(f"Erro ocorrido: {e}")
        st.error(f"Erro ao processar sua solicitação: {str(e)}")

def main():
    """Main function to run the Streamlit app."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_register_ui()
    else:
        if 'history' not in st.session_state:
            st.session_state.history = []
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = initialize_conversation()

        st.title("CarAI - Seu Assistente Inteligente para Compra de Carros")

        # Chat container
        chat_container = st.container()
        
        with chat_container:
            for message in st.session_state.history[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        # Input area
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                chat_input = st.text_input("Digite sua mensagem:", key="chat_input")
            with col2:
                uploaded_file = st.file_uploader("", type=["txt", "pdf", "png", "jpg", "jpeg"])

            # Botões de funcionalidades
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("Criar imagem"):
                    st.write("Funcionalidade de criar imagem não implementada.")
            with col2:
                if st.button("Analisar dados"):
                    st.write("Funcionalidade de analisar dados não implementada.")
            with col3:
                if st.button("Conselhos"):
                    st.write("Funcionalidade de conselhos não implementada.")
            with col4:
                if st.button("Ajude a escrever"):
                    st.write("Funcionalidade de ajuda na escrita não implementada.")
            with col5:
                if st.button("Mais"):
                    st.write("Mais opções não implementadas.")

            if st.button("Enviar"):
                if chat_input or uploaded_file:
                    on_chat_submit(chat_input, uploaded_file)
                    st.rerun()

        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

if __name__ == "__main__":
    main()
