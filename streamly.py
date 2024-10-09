import openai
import streamlit as st
import logging
from PIL import Image, ImageEnhance
import time
import json
import requests
import base64
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
openai.api_key = OPENAI_API_KEY
client = openai.OpenAI()

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
            ### Powered by GPT-4o

            **GitHub**: https://github.com/YourGitHubUsername/

            CarAI is an AI-powered assistant designed to help you analyze vehicle purchases,
            calculate the best negotiation strategies with banks, and provide clear,
            objective, and precise business options and potential profits.
        """
    }
)

# Login functionality
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

def img_to_base64(image_path):
    """Convert image to base64."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        logging.error(f"Error converting image to base64: {str(e)}")
        return None

def initialize_conversation():
    """
    Initialize the conversation history with system and assistant messages.

    Returns:
    - list: Initialized conversation history.
    """
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
        model_engine = "gpt-4o"
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

def main():
    """
    Main function to run the Streamlit app.
    """
    if check_password():
        initialize_session_state()

        if not st.session_state.history:
            initial_bot_message = "Olá! Sou o CarAI, seu assistente especializado em análise de veículos e negociações bancárias. Como posso ajudar você hoje?"
            st.session_state.history.append({"role": "assistant", "content": initial_bot_message})
            st.session_state.conversation_history = initialize_conversation()

        # Insert custom CSS for glowing effect
        st.markdown(
            """
            <style>
            .cover-glow {
                width: 100%;
                height: auto;
                padding: 3px;
                box-shadow: 
                    0 0 5px #000033,
                    0 0 10px #000066,
                    0 0 15px #000099,
                    0 0 20px #0000CC,
                    0 0 25px #0000FF,
                    0 0 30px #3333FF,
                    0 0 35px #6666FF;
                position: relative;
                z-index: -1;
                border-radius: 45px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Load and display sidebar image
        img_path = "imgs/car_ai_avatar.png"  # Replace with your car AI image
        img_base64 = img_to_base64(img_path)
        if img_base64:
            st.sidebar.markdown(
                f'<img src="data:image/png;base64,{img_base64}" class="cover-glow">',
                unsafe_allow_html=True,
            )

        st.sidebar.markdown("---")

        # Sidebar for information
        st.sidebar.markdown("""
        ### Como usar o CarAI
        - **Forneça informações do veículo**: Informe detalhes sobre o carro, parcelas e banco.
        - **Peça análises**: Solicite cálculos de quitação, estratégias de negócio e lucros esperados.
        - **Obtenha resumos**: Peça um resumo final com as melhores opções de negócio.
        """)

        st.sidebar.markdown("---")

        # Load and display image with glowing effect
        img_path = "imgs/car_ai_banner.png"  # Replace with your car AI banner image
        img_base64 = img_to_base64(img_path)
        if img_base64:
            st.sidebar.markdown(
                f'<img src="data:image/png;base64,{img_base64}" class="cover-glow">',
                unsafe_allow_html=True,
            )

        # Main chat interface
        st.title("CarAI - Seu Assistente Inteligente para Compra de Carros")
        
        chat_input = st.chat_input("Pergunte sobre análise de veículos ou estratégias de negociação:")
        if chat_input:
            on_chat_submit(chat_input)

        # Display chat history
        for message in st.session_state.history[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
            role = message["role"]
            avatar_image = "imgs/car_ai_avatar.png" if role == "assistant" else "imgs/user_avatar.png"
            with st.chat_message(role, avatar=avatar_image):
                st.write(message["content"])

if __name__ == "__main__":
    main()
