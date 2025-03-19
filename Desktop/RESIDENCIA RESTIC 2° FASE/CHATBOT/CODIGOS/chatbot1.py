import os
import openai
import openpyxl
from datetime import datetime
import locale
from twilio.rest import Client
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Definir a localidade para português do Brasil
locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")

# Obter as chaves de API da variável de ambiente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Inicializar o cliente da OpenAI
openai.api_key = OPENAI_API_KEY

# Inicializar o Flask
app = Flask(__name__)

# Função para enviar mensagens para o modelo GPT
def enviar_mensagem(mensagem):
    prompt_personalizado = f"Você está conversando com um agricultor no sistema do Campo Inteligente. Responda de forma clara e objetiva sobre cadastro, funcionalidades do sistema, ou uso agrícola. Pergunta: {mensagem}"
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-4", 
            messages=[{"role": "user", "content": prompt_personalizado}],
            max_tokens=150,
            temperature=0.5,
            stop=["\n"],
        )
        texto_resposta = resposta.choices[0].message["content"].strip()
        return texto_resposta
    except openai.error.OpenAIError as e:
        return f"Erro na API do OpenAI: {e}"
    except Exception as e:
        return f"Erro inesperado: {e}"

# Função para salvar dados em uma planilha Excel com nome único
def salvar_planilha(dados):
    nome_arquivo = "respostas_agricultores_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Respostas"
    ws.append(["Nome", "Localização", "Data", "Dia da Semana"])
    for resposta in dados:
        ws.append(resposta)
    wb.save(nome_arquivo)

# Função para coletar os dados do agricultor com validação
def coletar_dados():
    dados = []
    while True:
        nome = input("Digite seu nome: ").strip()
        if not nome:
            print("Nome não pode ser vazio. Tente novamente.")
            continue
        localizacao = input("Informe sua localização: ").strip()
        if not localizacao:
            print("Localização não pode ser vazia. Tente novamente.")
            continue
        data_atual = datetime.now().strftime("%d/%m/%Y")
        dia_da_semana = datetime.now().strftime("%A")
        dados.append([nome, localizacao, data_atual, dia_da_semana])
        if input("Adicionar mais? (s/n): ").strip().lower() != 's':
            break
    salvar_planilha(dados)
    print("Dados salvos com sucesso!")

# Função para respostas frequentes
def respostas_frequentes(pergunta):
    perguntas_freq = {
        "como me cadastrar?": "Para se cadastrar, basta fornecer seu nome, localização e outras informações solicitadas.",
        "quais as funcionalidades do sistema?": "O sistema permite cadastrar agricultores, visualizar relatórios e interagir com o chatbot para tirar dúvidas.",
        "como usar o sistema?": "Após o cadastro, você pode acessar funcionalidades como visualização de dados, cadastro de novos agricultores e obtenção de relatórios.",
    }
    return perguntas_freq.get(pergunta.lower(), None)

# Função para fluxo de perguntas do chatbot com respostas personalizadas
def fluxo_perguntas():
    while True:
        pergunta = input("Pergunte algo: ").strip().lower()
        if pergunta == 'sair':
            print("Saindo do chatbot.")
            break
        resposta = respostas_frequentes(pergunta) or enviar_mensagem(pergunta)
        print(f"Chatbot: {resposta}\n")
        if input("Fazer outra pergunta? (s/n): ").strip().lower() != 's':
            break

# Função para enviar mensagem pelo WhatsApp (via Twilio)
def enviar_mensagem_whatsapp(mensagem, numero):
    client_twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    mensagem_enviada = client_twilio.messages.create(
        body=mensagem,
        from_=TWILIO_WHATSAPP_NUMBER,  # Número da Twilio para WhatsApp
        to=f'whatsapp:{numero}'
    )
    return mensagem_enviada.sid

# Rota Flask para enviar mensagens ao GPT
@app.route('/enviar_mensagem', methods=['POST'])
def flask_enviar_mensagem():
    mensagem = request.json.get('mensagem')
    if not mensagem:
        return jsonify({"error": "Mensagem não fornecida"}), 400
    resposta = enviar_mensagem(mensagem)
    return jsonify({"resposta": resposta})

# Rota Flask para coletar dados dos agricultores
@app.route('/coletar_dados', methods=['POST'])
def flask_coletar_dados():
    dados = request.json.get('dados')
    if not dados:
        return jsonify({"error": "Dados não fornecidos"}), 400
    salvar_planilha(dados)
    return jsonify({"message": "Dados salvos com sucesso!"})

# Rota Flask para enviar WhatsApp
@app.route('/enviar_whatsapp', methods=['POST'])
def flask_enviar_whatsapp():
    numero = request.json.get('numero')
    mensagem = request.json.get('mensagem')
    if not numero or not mensagem:
        return jsonify({"error": "Número ou mensagem não fornecidos"}), 400
    sid = enviar_mensagem_whatsapp(mensagem, numero)
    return jsonify({"sid": sid})

# Inicia o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)
