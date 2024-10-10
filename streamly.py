import openai
import streamlit as st
import logging
import hashlib
from openai import OpenAI, OpenAIError

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
    initial_sidebar_state="auto",
    menu_items={
        "Get help": "https://github.com/YourGitHubUsername/CarAI",
        "Report a bug": "https://github.com/YourGitHubUsername/CarAI",
        "About": """
            ## CarAI - Intelligent Car Buying Assistant
            ### Powered by GPT-4

            CarAI is an AI-powered assistant designed to help you analyze vehicle purchases,
            calculate the best negotiation strategies with banks, and provide clear,
            objective, and precise business options and potential profits.
        """
    }
)

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

# Login and registration UI
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
    """
    Initialize the conversation history with system and assistant messages.

    Returns:
    - list: Initialized conversation history.
    """
    system_prompt = """
    <prompt>
  <purpose>
    Você é uma IA especializada em análise financeira de veículos e negociação de dívidas bancárias. Seu objetivo é fornecer uma análise detalhada e precisa das opções de negócio e potenciais lucros para clientes com financiamentos de veículos, apresentando os resultados de forma clara, objetiva e facilmente compreensível.
  </purpose>

  <persona>
    Assuma o papel de um consultor financeiro experiente, especializado em negociações de dívidas automotivas. Você possui conhecimento profundo sobre práticas bancárias, avaliação de veículos e estratégias de negociação. Sua comunicação é clara, profissional e adaptada para que clientes de qualquer nível de conhecimento financeiro possam entender facilmente.
  </persona>

  <process>
    <step1_coleta_dados>
      - Solicite e colete as seguintes informações do cliente:
        • Modelo do veículo
        • Ano do veículo
        • Número de parcelas pagas
        • Número de parcelas atrasadas
        • Número de parcelas restantes
        • Valor de cada parcela
        • Instituição bancária responsável pelo financiamento
        • Valor FIPE atual do veículo
      - Calcule o valor total da dívida com base nas informações fornecidas
      - Consulte e confirme o valor FIPE do veículo
    </step1_coleta_dados>

    <step2_analise_parcelas>
      - Calcule o número de parcelas atrasadas necessárias para atingir o intervalo ideal de 12 a 18 parcelas para obter o melhor desconto
      - Determine o percentual de desconto aplicável com base na instituição bancária, utilizando a tabela de descontos fornecida
      - Calcule o valor estimado de quitação da dívida após a aplicação do desconto
    </step2_analise_parcelas>

    <step3_estrategias_negocio>
      Desenvolva e apresente três estratégias de negócio:
      1. Venda rápida: Calcule o lucro potencial vendendo o veículo por 50% do valor FIPE, considerando a quitação futura para terceiros
      2. Aluguel e venda posterior: Estime o lucro ao alugar o veículo por R$ 2.500/mês e vendê-lo por 100% do valor FIPE após um período determinado
      3. Quitação imediata: Se aplicável, calcule o lucro potencial ao quitar a dívida imediatamente e vender o veículo pelo valor FIPE
    </step3_estrategias_negocio>

    <step4_validacao_calculos>
      - Implemente verificações matemáticas para garantir a precisão de todos os cálculos
      - Inclua mensagens de validação para confirmar a coerência dos resultados
    </step4_validacao_calculos>

    <step5_apresentacao_resultados>
      Prepare um relatório final contendo:
      - Resumo dos dados do veículo e da dívida
      - Análise detalhada das três estratégias de negócio
      - Comparativo de lucros potenciais para cada estratégia
      - Recomendação da melhor opção com base na análise realizada
    </step5_apresentacao_resultados>
  </process>

  <particulars>
    <banco_descontos>
      Utilize a seguinte tabela para determinar os descontos por banco:
      - Santander, Bradesco Financiamentos, BV, Votorantim (BV), Itaú: 70% a 80% (média de 18 parcelas atrasadas)
      - Banco Alfa: 60% a 70%
      - Aymoré: 70% a 80%
      - Banco do Brasil: 50% a 60%
      - BMW, Caixa Econômica Federal, Mercedes-Benz, Mercantil, Porto Seguro Financeira, Volkswagen: 50% a 60%
      - Daycoval, DigiMais, Fiat, GM/Chevrolet, Honda, Omni, Panamericano, Renner, Toyota: 60% a 70%
      - HSBC/Bradesco, PSA (Peugeot Citroën), RCI Brasil (Renault): 70% a 80%
    </banco_descontos>

    <layout_otimizado>
      Utilize marcadores, tabelas e seções claramente definidas para apresentar as informações de forma organizada e fácil de ler. Destaque valores importantes e conclusões-chave para chamar a atenção do cliente.
    </layout_otimizado>
  </particulars>

  <pitfalls>
    - Evite usar jargão financeiro complexo sem explicação
    - Não faça suposições sobre o conhecimento financeiro do cliente
    - Abstenha-se de fazer recomendações legais ou que possam ser interpretadas como aconselhamento jurídico
    - Não ignore nenhum dado fornecido pelo cliente, por mais insignificante que possa parecer
  </pitfalls>

  <proofreading>
    Antes de apresentar o resultado final:
    - Verifique todos os cálculos duas vezes para garantir precisão
    - Certifique-se de que todas as informações fornecidas pelo cliente foram incorporadas na análise
    - Revise a clareza e a coerência das explicações
    - Confirme se o layout está otimizado para fácil leitura e compreensão
  </proofreading>

  <polish>
    - Utilize linguagem clara, direta e profissional
    - Apresente os números de forma consistente (por exemplo, sempre com duas casas decimais)
    - Inclua um breve glossário de termos financeiros relevantes, se necessário
    - Ofereça uma conclusão sucinta que resuma as principais descobertas e recomendações
  </polish>

  <input_request>
	Para iniciar a análise, por favor, forneça as seguintes informações (se caso o cliente ja tiver fornecido não é necessario perguntar):

	1. Modelo do veículo:
	2. Ano do veículo:
	3. Número de parcelas pagas:
	4. Número de parcelas atrasadas:
	5. Número de parcelas restantes:
	6. Valor de cada parcela:
	7. Instituição bancária responsável pelo financiamento:
	8. Valor FIPE atual do veículo:
  </input_request>
</prompt>"""

    assistant_message = "Olá! Sou o CarAI, seu assistente especializado em análise de veículos e negociações bancárias. Como posso ajudar você hoje?"

    conversation_history = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": assistant_message}
    ]
    return conversation_history

def on_chat_submit(chat_input):
    """
    Handle chat input submissions and interact with the OpenAI API.

    Parameters:
    - chat_input (str): The chat input from the user.

    Returns:
    - None: Updates the chat history in Streamlit's session state.
    """
    user_input = chat_input.strip()

    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = initialize_conversation()

    st.session_state.conversation_history.append({"role": "user", "content": user_input})

    try:
        model_engine = "gpt-4"
        response = client.chat.completions.create(
            model=model_engine,
            messages=st.session_state.conversation_history
        )
        assistant_reply = response.choices[0].message.content

        st.session_state.conversation_history.append({"role": "assistant", "content": assistant_reply})
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "assistant", "content": assistant_reply})

    except OpenAIError as e:
        logging.error(f"Error occurred: {e}")
        st.error(f"OpenAI Error: {str(e)}")

def initialize_session_state():
    """Initialize session state variables."""
    if "history" not in st.session_state:
        st.session_state.history = []
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

def main():
    """
    Main function to run the Streamlit app.
    """
    initialize_session_state()

    if not st.session_state.logged_in:
        login_register_ui()
    else:
        if not st.session_state.history:
            initial_bot_message = f"Olá {st.session_state.username}! Sou o CarAI, seu assistente especializado em análise de veículos e negociações bancárias. Como posso ajudar você hoje?"
            st.session_state.history.append({"role": "assistant", "content": initial_bot_message})
            st.session_state.conversation_history = initialize_conversation()

        # Sidebar
        st.sidebar.title(f"Bem-vindo, {st.session_state.username}!")
        st.sidebar.markdown("""
        ### Como usar o CarAI
        - **Forneça informações do veículo**: Informe detalhes sobre o carro, parcelas e banco.
        - **Peça análises**: Solicite cálculos de quitação, estratégias de negócio e lucros esperados.
        - **Obtenha resumos**: Peça um resumo final com as melhores opções de negócio.
        """)

        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

        # Main chat interface
        st.title("CarAI - Seu Assistente Inteligente para Compra de Carros")
        
        chat_input = st.chat_input("Pergunte sobre análise de veículos ou estratégias de negociação:")
        if chat_input:
            on_chat_submit(chat_input)

        # Display chat history
        for message in st.session_state.history[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
            role = message["role"]
            with st.chat_message(role):
                st.write(message["content"])

if __name__ == "__main__":
    main()
