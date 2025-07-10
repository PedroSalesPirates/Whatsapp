import os
import requests
import time
import json
from supabase import create_client, Client
from dotenv import load_dotenv
import openai
from flask import Flask, request, jsonify, redirect
import uuid

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Supabase
url: str = "https://xukjbccvcnxatoqfidhw.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1a2piY2N2Y254YXRvcWZpZGh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAyMjA1MzYsImV4cCI6MjA2NTc5NjUzNn0.EcHnw_2bHeBEhA5YO4shwLkjI8CBIshVpZ9FbeIBUAE"
supabase: Client = create_client(url, key)

# Configurações da Z-API
Z_API_INSTANCE = "3E39A254E6D5C04764E77E3DAFB9E9AB"
Z_API_TOKEN = "24F698E693CFA794F9F34282"
Z_API_CLIENT_TOKEN = "Fb918900e30404a43b39122354c4f21b8S"

# Configuração da OpenAI
openai.api_key = "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"

# Configuração para armazenamento - Apenas Supabase
USAR_ARMAZENAMENTO_LOCAL = False

app = Flask(__name__)

@app.before_request
def log_request_info():
    """Registra informações sobre todas as requisições recebidas"""
    print("=" * 50)
    print(f"Requisição recebida: {request.method} {request.path}")
    print(f"Headers: {dict(request.headers)}")
    print(f"IP: {request.remote_addr}")
    print(f"Data/Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Tenta registrar o corpo da requisição
    try:
        if request.is_json:
            print(f"JSON: {request.json}")
        elif request.form:
            print(f"Form: {request.form}")
        elif request.data:
            print(f"Data: {request.data.decode('utf-8')}")
    except Exception as e:
        print(f"Erro ao registrar corpo da requisição: {e}")
    
    print("=" * 50)

def formatar_numero_whatsapp(numero):
    """Formata o número para o padrão aceito pela Z-API"""
    # Remove caracteres não numéricos
    numero_limpo = ''.join(filter(str.isdigit, numero))
    
    # Garante que o número tenha o formato correto (com código do país)
    if len(numero_limpo) <= 11:  # Sem código do país
        numero_formatado = f"55{numero_limpo}"
    else:
        numero_formatado = numero_limpo
    
    return numero_formatado

def enviar_mensagem_whatsapp(numero, mensagem):
    """Envia mensagem via Z-API"""
    numero_formatado = formatar_numero_whatsapp(numero)

    # Endpoint para envio de texto
    url = f"https://api.z-api.io/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/send-text"
    
    # Remove aspas no início e fim da mensagem, se existirem
    mensagem = mensagem.strip()
    if mensagem.startswith('"') and mensagem.endswith('"'):
        mensagem = mensagem[1:-1]
    elif mensagem.startswith("'") and mensagem.endswith("'"):
        mensagem = mensagem[1:-1]
    
    # Adicionar metadados para identificar mensagens enviadas pela nossa API
    payload = {
        "phone": numero_formatado,
        "message": mensagem,
        "messageId": f"API-{int(time.time())}"  # Identificador único para nossas mensagens
    }

    headers = {
        "Content-Type": "application/json",
        "Client-Token": Z_API_CLIENT_TOKEN
    }

    try:
        print(f"Enviando para {numero_formatado}")
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"Status: {resp.status_code}  Resposta: {resp.text}")
        return resp.status_code in (200, 201)
    except Exception as e:
        print("Erro na requisição:", e)
        return False

def verificar_repeticoes(historico_conversa, resposta_atual, limite=3):
    """
    Verifica se a resposta atual contém repetições de frases ou padrões das últimas mensagens
    
    Args:
        historico_conversa: Lista de mensagens anteriores
        resposta_atual: Resposta que está sendo verificada
        limite: Número de mensagens anteriores para verificar
        
    Returns:
        tuple: (tem_repeticao, resposta_corrigida)
    """
    # Se não houver histórico suficiente, não há como verificar repetições
    if len(historico_conversa) < 1:
        return False, resposta_atual
    
    # Obter as últimas mensagens do assistente
    ultimas_mensagens = []
    for item in reversed(historico_conversa):
        if item["role"] == "assistant" and len(ultimas_mensagens) < limite:
            ultimas_mensagens.append(item["content"].lower())
    
    # Se não houver mensagens anteriores do assistente, não há repetições
    if not ultimas_mensagens:
        return False, resposta_atual
    
    # Verificar repetições de frases específicas de encerramento
    frases_encerramento = [
        "beleza?", 
        "tô sempre por aqui", 
        "ele vai te chamar em breve",
        "seguir esse papo",
        "se mudar de ideia",
        "é só me chamar aqui",
        "posso te ajudar",
        "como posso te ajudar"
    ]
    
    resposta_lower = resposta_atual.lower()
    
    # Verificar se alguma frase de encerramento está sendo repetida
    for frase in frases_encerramento:
        if frase in resposta_lower:
            for mensagem in ultimas_mensagens:
                if frase in mensagem:
                    # Detectou repetição, tentar corrigir
                    print(f"Detectada repetição da frase: '{frase}'")
                    
                    # Remover a frase repetida com base no tipo
                    if "beleza?" in resposta_lower:
                        resposta_corrigida = resposta_atual.replace("beleza?", "").replace("Beleza?", "")
                        # Se terminar com vírgula ou espaço, limpar
                        resposta_corrigida = resposta_corrigida.rstrip(" ,")
                        # Adicionar ponto final se necessário
                        if not resposta_corrigida.endswith(".") and not resposta_corrigida.endswith("!"):
                            resposta_corrigida += "."
                        return True, resposta_corrigida
                    
                    elif "tô sempre por aqui" in resposta_lower:
                        resposta_corrigida = resposta_atual.replace("tô sempre por aqui", "").replace("Tô sempre por aqui", "")
                        resposta_corrigida = resposta_corrigida.rstrip(" ,")
                        if not resposta_corrigida.endswith(".") and not resposta_corrigida.endswith("!"):
                            resposta_corrigida += "."
                        return True, resposta_corrigida
                    
                    elif "ele vai te chamar em breve" in resposta_lower and "pra seguir esse papo" in resposta_lower:
                        resposta_corrigida = resposta_atual.replace("pra seguir esse papo", "")
                        resposta_corrigida = resposta_corrigida.rstrip(" ,")
                        if not resposta_corrigida.endswith(".") and not resposta_corrigida.endswith("!"):
                            resposta_corrigida += "."
                        return True, resposta_corrigida
                    
                    # Verificar se a resposta termina com uma pergunta que já foi feita antes
                    if resposta_lower.endswith("?"):
                        ultima_frase = resposta_lower.split(".")[-1].strip()
                        for msg in ultimas_mensagens:
                            if ultima_frase in msg:
                                # Remover a última frase (pergunta repetida)
                                partes = resposta_atual.split(".")
                                if len(partes) > 1:
                                    resposta_corrigida = ".".join(partes[:-1]) + "."
                                    return True, resposta_corrigida
                    
                    # Para outras frases, apenas retornar que há repetição
                    return True, resposta_atual
    
    # Verificar se a resposta atual é muito similar a alguma mensagem anterior
    for mensagem in ultimas_mensagens:
        # Se a mensagem for muito similar (mais de 70% igual)
        if len(resposta_lower) > 10 and len(mensagem) > 10:
            palavras_resposta = set(resposta_lower.split())
            palavras_mensagem = set(mensagem.split())
            
            # Calcular similaridade com base nas palavras em comum
            palavras_comuns = palavras_resposta.intersection(palavras_mensagem)
            if len(palavras_comuns) > 0.7 * min(len(palavras_resposta), len(palavras_mensagem)):
                print("Detectada alta similaridade com mensagem anterior")
                return True, resposta_atual  # Apenas sinalizar, sem corrigir
    
    return False, resposta_atual

def obter_primeiro_nome(nome_completo):
    """Extrai apenas o primeiro nome de um nome completo"""
    if not nome_completo or nome_completo == "Cliente":
        return "Cliente"
    
    # Dividir o nome pelos espaços e pegar o primeiro elemento
    partes_nome = nome_completo.strip().split()
    if partes_nome:
        return partes_nome[0]
    else:
        return nome_completo  # Retorna o nome original se não conseguir dividir

def gerar_resposta_ia(historico_conversa, mensagem_cliente, nome_cliente=""):
    """Gera uma resposta usando a OpenAI com base no histórico da conversa"""
    try:
        # Extrair apenas o primeiro nome do cliente
        primeiro_nome = obter_primeiro_nome(nome_cliente)
        
        # Construir o histórico de mensagens para o contexto
        messages = [
            {"role": "system", "content": f"""
            # Sub prompt 1: Orientação para construção da conversa e perguntas.

            Aja como um especialista em vendas consultivas no WhatsApp, com domínio completo do método SPIN Selling de Neil Rackham. Seu papel é interpretar e conduzir uma conversa com um lead que respondeu à mensagem de boas-vindas sobre a Biblioteca IA.
            
            Você é o Wald, agente de IA da Sales Pirates. Sua função é agir como um parceiro de conversa confiável, empático e altamente consultivo — alguém que entende o ritmo do dia a dia do lead e ajuda a clarear o cenário antes de conectá-lo a um especialista humano.
            
            O lead é um profissional da área de vendas (como SDR, vendedor, gerente, diretor ou dono de empresa).
            O nome do cliente é: {primeiro_nome if primeiro_nome else "Cliente"}.
            
            Importante: adapte toda a conversa ao cargo do lead. Isso inclui:
            
            O conteúdo das perguntas (o que perguntar);
            
            O vocabulário e o estilo da linguagem (como perguntar);
            
            O nível de profundidade ou contexto esperado em cada etapa.
            
            Regras:
            
            Use um tom descontraído, natural e humano. Evite rigidez, robôs e jargões técnicos.
            
            Comece validando a resposta do lead com uma frase empática e autêntica (ex: "Faz total sentido o que você falou" ou "Imagino como isso deve pesar na rotina…").
            
            Sempre que for fazer uma pergunta, contextualize antes com observações naturais baseadas no que o lead falou. Evite parecer que está seguindo um checklist.
            
            Conduza a conversa com base no método SPIN Selling, seguindo esta ordem:
            
            Situação – explore o contexto atual com perguntas que façam sentido para o cargo do lead (ex: processos se for analista, estratégia se for coordenador).
            
            Problema – aprofunde nos gargalos e frustrações que impactam a operação dele.
            
            Implicação – investigue os impactos e consequências desses problemas (tempo perdido, retrabalho, metas comprometidas).
            
            Necessidade de solução – leve o lead a reconhecer a urgência de mudança ou ajuda externa.
            
            Se o lead mencionar o segmento da empresa, use isso para enriquecer o contexto da conversa.
            
            Use observações, frases de transição e validações entre as perguntas para manter fluidez. Nunca faça uma sequência de perguntas direta e mecânica.
            
            Use até 10 perguntas, no máximo, durante a conversa. Mas esse número é flexível de acordo com a fluidez e clareza do lead. Priorize naturalidade.
            
            Nunca volte a uma etapa anterior do SPIN após avançar para a seguinte.
            
            Se o lead demonstrar clareza sobre a necessidade ou intenção de seguir, encerre com:
            "Perfeito, {primeiro_nome}. Vou passar essas informações para um dos nossos especialistas humanos aqui na Sales Pirates — ele vai te chamar em breve pra seguir esse papo, beleza?"
            
            Se o lead demonstrar desinteresse, finalize com empatia e sem insistência:
            "Tranquilo, {primeiro_nome}. Se mudar de ideia, é só me chamar aqui. Tô sempre por aqui, beleza?"
            
            Use no máximo 2 a 3 frases curtas por mensagem.
            
            # Sub prompt 2: Identificação e encerramento em caso de desinteresse do lead
            
            Durante a conversa, se o lead demonstrar desinteresse explícito (ex: "não quero seguir", "agora não é o momento", "não tenho interesse") ou variações mais sutis (ex: "vou ver depois", "a gente ainda está decidindo", "mais pra frente"), ative o seguinte protocolo:
            
            Nunca insista diretamente.
            
            Faça até 2 tentativas finais de recuperação, utilizando com uma perguntas leves ou provocações estratégicas, baseada exclusivamente no que foi dito pelo lead. Não repita frases anteriores.
            
            O tom deve ser humano, curioso e respeitoso. Exemplo:
            "De boa, {primeiro_nome}. Só pra entender melhor antes de te deixar tranquilo: esse gargalo que você comentou… tem afetado só o comercial ou outras áreas também?"
            
            Após as tentativas, se o lead continuar desinteressado ou não responder:
            "Tranquilo, {primeiro_nome}. Se mudar de ideia, é só me chamar aqui. Tô sempre por aqui, beleza?"
            
            Use no máximo 2 frases curtas por mensagem.
            
            Mantenha a leveza e preserve a boa experiência do lead com a marca.
            
            # Continuação da conversa
            
            Se o lead demonstrar clareza sobre a necessidade ou intenção de seguir, encerre com:
            "Perfeito, {primeiro_nome}. Vou passar essas informações para um dos nossos especialistas humanos aqui na Sales Pirates — ele vai te chamar em breve pra seguir esse papo, beleza?"
            
            A saída esperada é uma resposta consultiva, fluida e estratégica que:
            
            Respeita o SPIN Selling;
            
            Se adapta ao perfil e cargo do lead;
            
            Conduz a conversa com naturalidade e sensibilidade;
            
            E reconhece com precisão o momento de encerrar, sem forçar.
            """}
        ]
        
        # Adicionar histórico da conversa
        for item in historico_conversa:
            messages.append(item)
        
        # Adicionar a mensagem atual do cliente
        messages.append({"role": "user", "content": mensagem_cliente})
        
        # Gerar resposta
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )
        
        resposta = response.choices[0].message.content.strip()
        
        # Verificação final para substituir qualquer placeholder que possa ter escapado
        if primeiro_nome:
            resposta = resposta.replace("{{nome}}", primeiro_nome)
            resposta = resposta.replace("{nome}", primeiro_nome)
        
        # Verificar se há repetições e corrigir se necessário
        tem_repeticao, resposta_corrigida = verificar_repeticoes(historico_conversa, resposta)
        if tem_repeticao:
            print("Detectada repetição na resposta. Usando versão corrigida.")
            resposta = resposta_corrigida
        
        return resposta
    except Exception as e:
        print(f"Erro ao gerar resposta: {e}")
        return "Desculpe, estou com dificuldades técnicas. Um especialista humano entrará em contato em breve."

def salvar_conversa(numero, nome, mensagem, tipo):
    """Salva a conversa no banco de dados Supabase
    tipo: 'recebida' ou 'enviada'
    """
    try:
        data = {
            "numero": numero,
            "nome": nome,
            "mensagem": mensagem,
            "tipo": tipo,
            "data": time.strftime("%Y-%m-%d %H:%M:%S"),
            "id": str(uuid.uuid4())  # Gera um UUID para o ID
        }
        
        # Salvar no Supabase
        try:
            response = supabase.table("Conversas").insert(data).execute()
            print(f"Conversa salva no Supabase: {response}")
            return True
        except Exception as e:
            print(f"Erro ao salvar no Supabase: {e}")
            return False
    except Exception as e:
        print(f"Erro ao salvar conversa: {e}")
        return False

def obter_historico_conversa(numero):
    """Obtém o histórico de conversa com um número específico"""
    try:
        # Obter do Supabase
        response = supabase.table("Conversas").select("*").eq("numero", numero).order("data", desc=False).execute()
        
        historico = []
        for item in response.data:
            if item["tipo"] == "recebida":
                historico.append({"role": "user", "content": item["mensagem"]})
            else:
                historico.append({"role": "assistant", "content": item["mensagem"]})
                
        return historico
    except Exception as e:
        print(f"Erro ao obter histórico: {e}")
        return []

def obter_nome_cliente(numero):
    """Obtém o nome do cliente pelo número de telefone"""
    try:
        # Formatar o número para garantir consistência
        numero_formatado = formatar_numero_whatsapp(numero)
        
        # Buscar na tabela biblioteca-ia
        response = supabase.table("biblioteca-ia").select("nome").eq("whatsapp", numero_formatado).execute()
        if response.data:
            return response.data[0]["nome"]
            
        # Se não encontrou, buscar nas conversas
        response = supabase.table("Conversas").select("nome").eq("numero", numero_formatado).order("data", desc=True).limit(1).execute()
        if response.data and response.data[0]["nome"] != "Cliente" and response.data[0]["nome"] != "Cliente Teste":
            return response.data[0]["nome"]
            
        return "Cliente"
    except Exception as e:
        print(f"Erro ao obter nome do cliente: {e}")
        return "Cliente"

def configurar_webhook(url_webhook):
    """Configura o webhook na Z-API para receber mensagens"""
    # Endpoint para configurar webhook de mensagens recebidas
    url = f"https://api.z-api.io/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/update-webhook-received"
    
    payload = {
        "value": url_webhook
    }

    headers = {
        "Content-Type": "application/json",
        "Client-Token": Z_API_CLIENT_TOKEN
    }

    try:
        print(f"Configurando webhook para: {url_webhook}")
        resp = requests.put(url, json=payload, headers=headers, timeout=15)
        print(f"Status: {resp.status_code}  Resposta: {resp.text}")
        
        if resp.status_code == 200:
            print("Webhook configurado com sucesso!")
            return True
        else:
            print("Falha ao configurar webhook")
            return False
    except Exception as e:
        print(f"Erro ao configurar webhook: {e}")
        return False

def configurar_todos_webhooks(url_base):
    """Configura todos os webhooks na Z-API para a mesma URL base"""
    # Mapeamento de endpoints para configuração de webhooks e seus caminhos correspondentes
    endpoints_map = {
        "update-webhook-received": "/contato/on-message-received",           # Ao receber
        "update-webhook-received-delivery": "/contato/on-message-received",  # Ao receber (com notificação de enviadas por mim)
        "update-webhook-message-status": "/contato/webhook-status",          # Status da mensagem
        "update-webhook-delivery": "/contato/webhook-delivery",              # Ao enviar
        "update-webhook-connected": "/contato/webhook-connected",            # Ao conectar
        "update-webhook-disconnected": "/contato/webhook-disconnected",      # Ao desconectar
        "update-webhook-presence": "/contato/webhook-presence"               # Presença do chat
    }
    
    # Lista de endpoints para configuração de webhooks
    endpoints = list(endpoints_map.keys())
    
    resultados = {}
    
    for endpoint in endpoints:
        url = f"https://api.z-api.io/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/{endpoint}"
        
        # Construir a URL completa para o webhook
        webhook_path = endpoints_map[endpoint]
        webhook_url = f"{url_base}{webhook_path}"
        
        payload = {
            "value": webhook_url
        }
        
        print(f"Configurando {endpoint} para: {webhook_url}")

        headers = {
            "Content-Type": "application/json",
            "Client-Token": Z_API_CLIENT_TOKEN
        }

        try:
            print(f"Configurando webhook {endpoint} para: {url_base}")
            resp = requests.put(url, json=payload, headers=headers, timeout=15)
            resultados[endpoint] = {
                "status": resp.status_code,
                "sucesso": resp.status_code == 200
            }
        except Exception as e:
            print(f"Erro ao configurar webhook {endpoint}: {e}")
            resultados[endpoint] = {
                "status": 500,
                "sucesso": False,
                "erro": str(e)
            }
    
    return resultados

def testar_com_pedro():
    """Testa o sistema enviando uma mensagem para o usuário Pedro"""
    try:
        # Busca o usuário Pedro na tabela biblioteca-ia, independente do modo de armazenamento
        response = supabase.table("biblioteca-ia").select("*").eq("nome", "Pedro").execute()
        
        if not response.data:
            print("Usuário Pedro não encontrado. Tentando buscar com ILIKE...")
            # Tenta buscar com ILIKE para ser menos restritivo
            response = supabase.table("biblioteca-ia").select("*").ilike("nome", "%Pedro%").execute()
            
            if not response.data:
                print("Nenhum usuário com nome Pedro encontrado.")
                return False
        
        # Pega o primeiro usuário encontrado
        pedro = response.data[0]
        nome = pedro['nome']
        whatsapp = pedro['whatsapp']
        cargo = pedro.get('cargo', 'profissional')
        empresa = pedro.get('empresa', 'sua empresa')
        
        # Formatar o número para garantir consistência
        whatsapp_formatado = formatar_numero_whatsapp(whatsapp)
        
        # Verifica se a mensagem já foi enviada
        mensagem_ja_enviada = pedro.get('mensagem_enviada', False)
        if mensagem_ja_enviada:
            print(f"Mensagem já foi enviada anteriormente para {nome}. Pulando abordagem inicial...")
            return True
        
        print(f"Testando envio para: {nome}")
        print(f"WhatsApp: {whatsapp_formatado}")
        print(f"Cargo: {cargo}")
        print(f"Empresa: {empresa}")
        
        # Gera mensagem personalizada usando o novo prompt da Biblioteca IA
        mensagem = gerar_mensagem_llm(nome, cargo, empresa)
        
        # Envia mensagem
        sucesso = enviar_mensagem_whatsapp(whatsapp_formatado, mensagem)
        
        if sucesso:
            # Salva mensagem enviada
            salvar_conversa(whatsapp_formatado, nome, mensagem, "enviada")
            print("Mensagem enviada com sucesso!")
            return True
        else:
            print("Falha ao enviar mensagem.")
            return False
            
    except Exception as e:
        print(f"Erro ao testar com Pedro: {e}")
        return False

def testar_com_joao():
    """Testa o sistema enviando uma mensagem para o usuário João"""
    try:
        # Busca o usuário João na tabela biblioteca-ia, independente do modo de armazenamento
        response = supabase.table("biblioteca-ia").select("*").eq("nome", "João").execute()
        
        if not response.data:
            print("Usuário João não encontrado. Tentando buscar com ILIKE...")
            # Tenta buscar com ILIKE para ser menos restritivo
            response = supabase.table("biblioteca-ia").select("*").ilike("nome", "%João%").execute()
            
            if not response.data:
                print("Nenhum usuário com nome João encontrado.")
                return False
        
        # Pega o primeiro usuário encontrado
        joao = response.data[0]
        nome = joao['nome']
        whatsapp = joao['whatsapp']
        cargo = joao.get('cargo', 'profissional')
        empresa = joao.get('empresa', 'sua empresa')
        
        # Formatar o número para garantir consistência
        whatsapp_formatado = formatar_numero_whatsapp(whatsapp)
        
        # Verifica se a mensagem já foi enviada
        mensagem_ja_enviada = joao.get('mensagem_enviada', False)
        if mensagem_ja_enviada:
            print(f"Mensagem já foi enviada anteriormente para {nome}. Pulando abordagem inicial...")
            return True
        
        print(f"Testando envio para: {nome}")
        print(f"WhatsApp: {whatsapp_formatado}")
        print(f"Cargo: {cargo}")
        print(f"Empresa: {empresa}")
        
        # Gera mensagem personalizada usando o novo prompt da Biblioteca IA
        mensagem = gerar_mensagem_llm(nome, cargo, empresa)
        
        # Envia mensagem
        sucesso = enviar_mensagem_whatsapp(whatsapp_formatado, mensagem)
        
        if sucesso:
            # Salva mensagem enviada
            salvar_conversa(whatsapp_formatado, nome, mensagem, "enviada")
            print("Mensagem enviada com sucesso!")
            return True
        else:
            print("Falha ao enviar mensagem.")
            return False
            
    except Exception as e:
        print(f"Erro ao testar com João: {e}")
        return False

@app.route('/on-message-received', methods=['GET', 'POST'])
def on_message_received():
    """Webhook para receber mensagens do WhatsApp via Z-API"""
    # Verificar se é uma requisição GET (verificação de disponibilidade)
    if request.method == 'GET':
        print("Recebida verificação GET para o webhook")
        return jsonify({"status": "success", "message": "Webhook configurado e funcionando"}), 200
    try:
        print("===== WEBHOOK RECEBIDO =====")
        print(f"Headers: {dict(request.headers)}")
        
        # Log do corpo da requisição como texto bruto
        request_data = request.get_data().decode('utf-8')
        print(f"Corpo bruto da requisição: {request_data}")
        
        # Tenta converter para JSON
        try:
            data = request.json
            print(f"JSON recebido: {data}")
        except Exception as e:
            print(f"Erro ao converter para JSON: {e}")
            # Tenta salvar o corpo bruto como mensagem
            if request_data:
                try:
                    salvar_conversa("webhook_erro", "Sistema", f"Erro JSON: {request_data}", "recebida")
                except:
                    pass
            return jsonify({"status": "error", "message": "JSON inválido"}), 400
        
        # Salvar todos os webhooks recebidos para análise
        try:
            with open('todos_webhooks.json', 'a') as f:
                f.write(json.dumps(data) + '\n')
        except:
            pass
        
        # Verificar se é uma mensagem recebida (ReceivedCallback)
        if data.get('type') == 'ReceivedCallback':
            # Verificar se é uma notificação de grupo ou outro tipo de evento que não é uma mensagem
            if data.get('notification'):
                print(f"Recebida notificação: {data.get('notification')}. Ignorando.")
                return jsonify({"status": "success", "message": "Notificação ignorada"}), 200
                
            # Verificar se é uma mensagem de grupo (opcional: podemos processar ou ignorar)
            if data.get('isGroup', False):
                print("Mensagem de grupo recebida. Ignorando.")
                return jsonify({"status": "success", "message": "Mensagem de grupo ignorada"}), 200
            
            # Verificar se é uma mensagem enviada pelo próprio número
            is_from_me = data.get('fromMe', False)
            
            print(f"Mensagem recebida válida! FromMe: {is_from_me}")
            numero = data.get('phone', '')
            
            # Formatar o número para garantir consistência
            numero_formatado = formatar_numero_whatsapp(numero)
            
            mensagem = ""
            
            # Extrair a mensagem de acordo com o tipo de conteúdo
            if 'text' in data and isinstance(data['text'], dict):
                mensagem = data['text'].get('message', '')
            elif 'buttonsResponseMessage' in data:
                mensagem = data['buttonsResponseMessage'].get('message', '')
            elif 'listResponseMessage' in data:
                mensagem = data['listResponseMessage'].get('message', '')
            elif 'hydratedTemplate' in data:
                mensagem = data['hydratedTemplate'].get('message', '')
            elif 'image' in data:
                mensagem = data['image'].get('caption', '[Imagem recebida]')
            elif 'video' in data:
                mensagem = data['video'].get('caption', '[Vídeo recebido]')
            elif 'audio' in data:
                mensagem = '[Áudio recebido]'
            elif 'document' in data:
                mensagem = f"[Documento recebido: {data['document'].get('fileName', 'sem nome')}]"
            elif 'contact' in data:
                mensagem = f"[Contato recebido: {data['contact'].get('displayName', 'sem nome')}]"
            elif 'reaction' in data:
                mensagem = f"[Reação: {data['reaction'].get('value', '')}]"
            elif 'carouselMessage' in data:
                mensagem = data['carouselMessage'].get('text', '[Carrossel recebido]')
            elif 'buttonsMessage' in data:
                mensagem = data['buttonsMessage'].get('message', '[Botões recebidos]')
            
            # Se não conseguiu extrair mensagem, não processa
            if not mensagem:
                print("Mensagem vazia ou formato não suportado")
                # Tentar identificar o tipo de mensagem para debug
                message_keys = [k for k in data.keys() if k not in ['type', 'instanceId', 'messageId', 'phone', 'fromMe', 'status']]
                print(f"Chaves disponíveis na mensagem: {message_keys}")
                return jsonify({"status": "success", "message": "Formato não suportado"}), 200
            
            # Remove aspas no início e fim da mensagem, se existirem
            mensagem = mensagem.strip()
            if mensagem.startswith('"') and mensagem.endswith('"'):
                mensagem = mensagem[1:-1]
            elif mensagem.startswith("'") and mensagem.endswith("'"):
                mensagem = mensagem[1:-1]
                
            print(f"Mensagem recebida: {mensagem} de {numero_formatado}")
            
            # Obter o nome do cliente diretamente da tabela biblioteca-ia
            nome = obter_nome_cliente(numero_formatado)
            
            # Registrar o nome do contato para fins de log, mas não usar
            nome_contato = data.get('senderName') or data.get('chatName')
            if nome_contato and nome_contato != numero_formatado and not nome_contato.startswith('55'):
                print(f"Nome do contato obtido da mensagem: {nome_contato} (usando nome da biblioteca-ia: {nome})")
            
            # Se é uma mensagem enviada pelo próprio número (fromMe)
            if is_from_me:
                print(f"Mensagem enviada pelo próprio número: {mensagem}")
                # Salvar mensagem enviada
                salvar_conversa(numero_formatado, nome, mensagem, "enviada")
                return jsonify({"status": "success", "message": "Mensagem própria salva"}), 200
            
            # Salvar mensagem recebida
            salvar_conversa(numero_formatado, nome, mensagem, "recebida")
            
            # Obter histórico da conversa
            historico = obter_historico_conversa(numero_formatado)
            
            # Aguardar um tempo para simular digitação (opcional)
            tempo_espera = 3.0 + (len(mensagem) / 100.0)  # Tempo base + tempo proporcional ao tamanho da mensagem
            print(f"Aguardando {tempo_espera:.1f} segundos antes de enviar resposta...")
            time.sleep(tempo_espera)
            
            # Gerar resposta com IA
            resposta = gerar_resposta_ia(historico, mensagem, nome)
            
            # Verificar se há repetições com o histórico completo
            tem_repeticao, resposta_corrigida = verificar_repeticoes(historico, resposta)
            if tem_repeticao:
                print("Detectada repetição na resposta. Usando versão corrigida.")
                resposta = resposta_corrigida
            
            # Enviar resposta
            sucesso = enviar_mensagem_whatsapp(numero_formatado, resposta)
            
            if sucesso:
                print(f"Resposta enviada com sucesso para {numero_formatado}")
                # Salvar resposta enviada
                salvar_conversa(numero_formatado, nome, resposta, "enviada")
                
                return jsonify({"status": "success", "message": "Resposta enviada com sucesso"}), 200
            else:
                print(f"Falha ao enviar resposta para {numero_formatado}")
                return jsonify({"status": "error", "message": "Falha ao enviar resposta"}), 500
        
        # Se chegou aqui, é um tipo de webhook não processado
        return jsonify({"status": "success", "message": "Webhook recebido mas não processado"}), 200
        
    except Exception as e:
        print(f"Erro ao processar webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/enviar-mensagem', methods=['POST'])
def enviar_mensagem():
    """Endpoint para enviar mensagem inicial para um cliente"""
    try:
        data = request.json
        numero = data.get('numero')
        mensagem = data.get('mensagem')
        
        if not numero or not mensagem:
            return jsonify({"status": "error", "message": "Número e mensagem são obrigatórios"}), 400
            
        # Formatar o número para garantir consistência
        numero_formatado = formatar_numero_whatsapp(numero)
            
        # Remove aspas no início e fim da mensagem, se existirem
        mensagem = mensagem.strip()
        if mensagem.startswith('"') and mensagem.endswith('"'):
            mensagem = mensagem[1:-1]
        elif mensagem.startswith("'") and mensagem.endswith("'"):
            mensagem = mensagem[1:-1]
        
        # Obter nome do cliente
        nome = obter_nome_cliente(numero_formatado)
        
        # Enviar mensagem
        sucesso = enviar_mensagem_whatsapp(numero_formatado, mensagem)
        
        if sucesso:
            # Salvar mensagem enviada
            salvar_conversa(numero_formatado, nome, mensagem, "enviada")
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Falha ao enviar mensagem"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/configurar-webhook', methods=['POST'])
def rota_configurar_webhook():
    """Endpoint para configurar o webhook"""
    try:
        data = request.json
        url_webhook = data.get('url')
        
        if not url_webhook:
            return jsonify({"status": "error", "message": "URL do webhook é obrigatória"}), 400
        
        sucesso = configurar_webhook(url_webhook)
        
        if sucesso:
            return jsonify({"status": "success", "message": "Webhook configurado com sucesso"}), 200
        else:
            return jsonify({"status": "error", "message": "Falha ao configurar webhook"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/configurar-todos-webhooks', methods=['POST'])
def rota_configurar_todos_webhooks():
    """Endpoint para configurar todos os webhooks para a mesma URL"""
    try:
        data = request.json
        url_base = data.get('url')
        
        if not url_base:
            return jsonify({"status": "error", "message": "URL base é obrigatória"}), 400
        
        resultados = configurar_todos_webhooks(url_base)
        
        # Verifica se todos foram configurados com sucesso
        todos_sucesso = all(resultado["sucesso"] for resultado in resultados.values())
        
        if todos_sucesso:
            return jsonify({
                "status": "success", 
                "message": "Todos os webhooks configurados com sucesso",
                "detalhes": resultados
            }), 200
        else:
            return jsonify({
                "status": "partial", 
                "message": "Alguns webhooks não puderam ser configurados",
                "detalhes": resultados
            }), 207  # Multi-Status
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/testar-joao', methods=['GET'])
def rota_testar_joao():
    """Endpoint para testar o sistema com o usuário João"""
    try:
        sucesso = testar_com_joao()
        
        if sucesso:
            return jsonify({"status": "success", "message": "Teste com João iniciado com sucesso"}), 200
        else:
            return jsonify({"status": "error", "message": "Falha ao iniciar teste com João"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/conversas', methods=['GET'])
def listar_conversas():
    """Endpoint para listar todas as conversas"""
    try:
        # Obter todas as conversas do Supabase
        response = supabase.table("Conversas").select("*").execute()
        
        # Agrupar conversas por número formatado
        conversas_por_numero = {}
        for conversa in response.data:
            numero_original = conversa["numero"]
            # Formatar o número para garantir consistência
            numero_formatado = formatar_numero_whatsapp(numero_original)
            
            if numero_formatado not in conversas_por_numero:
                # Obter nome do cliente usando a função para garantir consistência
                nome = obter_nome_cliente(numero_formatado)
                
                conversas_por_numero[numero_formatado] = {
                    "numero": numero_formatado,
                    "nome": nome,
                    "ultima_mensagem": conversa["mensagem"],
                    "data": conversa["data"],
                    "mensagens": 1
                }
            else:
                conversas_por_numero[numero_formatado]["mensagens"] += 1
                # Atualiza a última mensagem se esta for mais recente
                if conversa["data"] > conversas_por_numero[numero_formatado]["data"]:
                    conversas_por_numero[numero_formatado]["ultima_mensagem"] = conversa["mensagem"]
                    conversas_por_numero[numero_formatado]["data"] = conversa["data"]
        
        # Formatar para exibição HTML
        html = "<h1>Conversas</h1>"
        html += "<style>"
        html += "body { font-family: Arial, sans-serif; margin: 20px; }"
        html += ".conversation { padding: 15px; margin: 10px 0; border-radius: 10px; background-color: #f5f5f5; cursor: pointer; }"
        html += ".conversation:hover { background-color: #e0e0e0; }"
        html += ".name { font-weight: bold; font-size: 1.2em; }"
        html += ".message { color: #666; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }"
        html += ".date { font-size: 0.8em; color: #888; margin-top: 5px; }"
        html += ".count { float: right; background-color: #ff6b6b; color: white; padding: 5px 10px; border-radius: 50%; }"
        html += "</style>"
        
        # Ordenar conversas pela data da última mensagem (mais recente primeiro)
        conversas_ordenadas = sorted(
            conversas_por_numero.values(), 
            key=lambda x: x["data"], 
            reverse=True
        )
        
        for conversa in conversas_ordenadas:
            html += f"<div class='conversation' onclick=\"window.location.href='/conversa/{conversa['numero']}'\">"
            html += f"<div class='count'>{conversa['mensagens']}</div>"
            html += f"<div class='name'>{conversa['nome']} ({conversa['numero']})</div>"
            html += f"<div class='message'>{conversa['ultima_mensagem']}</div>"
            html += f"<div class='date'>{conversa['data']}</div>"
            html += "</div>"
        
        return html
        
    except Exception as e:
        print(f"Erro ao listar conversas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook-test', methods=['GET', 'POST'])
def webhook_test():
    """Endpoint para testar se o webhook está funcionando"""
    if request.method == 'GET':
        # Retorna um formulário HTML simples para teste
        html = """
        <h1>Teste de Webhook</h1>
        <form method="POST" action="/webhook-test">
            <label>Número de telefone:</label>
            <input type="text" name="phone" value="5511986794225"><br>
            <label>Mensagem:</label>
            <input type="text" name="message" value="Olá, isso é um teste!"><br>
            <input type="submit" value="Simular mensagem recebida">
        </form>
        """
        return html
    else:
        # Simula uma mensagem recebida
        phone = request.form.get('phone', '5511986794225')
        message = request.form.get('message', 'Teste de webhook')
        
        # Formatar o número para garantir consistência
        phone_formatado = formatar_numero_whatsapp(phone)
        
        # Cria um objeto JSON similar ao que a Z-API enviaria
        webhook_data = {
            "isStatusReply": False,
            "senderLid": "81896604192873@lid",
            "connectedPhone": "554499999999",
            "waitingMessage": False,
            "isEdit": False,
            "isGroup": False,
            "isNewsletter": False,
            "instanceId": "A20DA9C0183A2D35A260F53F5D2B9244",
            "messageId": "A20DA9C0183A2D35A260F53F5D2B9244",
            "phone": phone_formatado,
            "fromMe": False,
            "momment": int(time.time() * 1000),
            "status": "RECEIVED",
            "chatName": "Teste",
            "senderName": "Teste",
            "type": "ReceivedCallback",
            "text": {
                "message": message
            }
        }
        
        print(f"Simulando webhook com dados: {webhook_data}")
        
        # Salvar a mensagem como se fosse recebida pelo webhook
        try:
            nome = obter_nome_cliente(phone_formatado)
            salvar_conversa(phone_formatado, nome, message, "recebida")
            
            # Obter histórico da conversa
            historico = obter_historico_conversa(phone_formatado)
            
            # Gerar resposta com IA, passando o nome do cliente
            resposta = gerar_resposta_ia(historico, message, nome)
            
            # Verificação adicional para placeholders que possam ter escapado
            primeiro_nome = obter_primeiro_nome(nome)
            if "{{nome}}" in resposta:
                resposta = resposta.replace("{{nome}}", primeiro_nome)
                print("Substituído placeholder {{nome}} pelo primeiro nome do cliente")
            if "{nome}" in resposta:
                resposta = resposta.replace("{nome}", primeiro_nome)
                print("Substituído placeholder {nome} pelo primeiro nome do cliente")
                
            # Verificar novamente se há repetições com o histórico completo
            tem_repeticao, resposta_corrigida = verificar_repeticoes(historico, resposta)
            if tem_repeticao:
                print("Detectada repetição na resposta após substituição de placeholders. Usando versão corrigida.")
                resposta = resposta_corrigida
                
            # Adiciona um tempo de espera para simular digitação humana
            tempo_espera = min(2 + (len(resposta) / 50), 8)
            print(f"Aguardando {tempo_espera:.1f} segundos antes de enviar resposta...")
            time.sleep(tempo_espera)
            
            # Enviar resposta
            sucesso = enviar_mensagem_whatsapp(phone_formatado, resposta)
            
            if sucesso:
                # Salva resposta enviada
                salvar_conversa(phone_formatado, nome, resposta, "enviada")
                return jsonify({
                    "status": "success", 
                    "message": "Teste de webhook processado com sucesso",
                    "resposta": resposta
                }), 200
            else:
                return jsonify({
                    "status": "error", 
                    "message": "Erro ao enviar resposta"
                }), 500
        except Exception as e:
            print(f"Erro ao processar teste de webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    """Página inicial com links úteis"""
    links = [
        {"url": "/testar-joao", "descricao": "Testar envio para João"},
        {"url": "/testar-mensagem", "descricao": "Testar geração de mensagem"},
        {"url": "/webhook-test", "descricao": "Testar webhook (simulação)"},
        {"url": "/conversas", "descricao": "Ver todas as conversas"},
        {"url": "/configurar-todos-webhooks", "descricao": "Configurar todos os webhooks (POST)"}
    ]
    
    webhook_endpoints = [
        {"url": "/on-message-received", "descricao": "Webhook para mensagens recebidas (principal)"},
        {"url": "/webhook-status", "descricao": "Webhook para status de mensagens"},
        {"url": "/webhook-delivery", "descricao": "Webhook para confirmação de entrega"},
        {"url": "/webhook-connected", "descricao": "Webhook para conexão"},
        {"url": "/webhook-disconnected", "descricao": "Webhook para desconexão"},
        {"url": "/webhook-presence", "descricao": "Webhook para presença"}
    ]
    
    html = "<h1>Sistema de Conversas WhatsApp</h1>"
    
    html += "<h2>Links principais</h2>"
    html += "<ul>"
    for link in links:
        if "POST" in link["descricao"]:
            html += f"<li>{link['descricao']} - {link['url']}</li>"
        else:
            html += f"<li><a href='{link['url']}'>{link['descricao']}</a></li>"
    html += "</ul>"
    
    html += "<h2>Endpoints de Webhook</h2>"
    html += "<ul>"
    for endpoint in webhook_endpoints:
        html += f"<li>{endpoint['descricao']} - {endpoint['url']}</li>"
    html += "</ul>"
    
    html += "<h2>Como configurar na Z-API</h2>"
    html += "<p>Use a URL base do seu servidor (ex: https://seu-servidor.com) no endpoint /configurar-todos-webhooks</p>"
    html += "<p>Exemplo de configuração manual na Z-API:</p>"
    html += "<ul>"
    html += "<li>Ao receber: https://seu-servidor.com/on-message-received</li>"
    html += "<li>Status da mensagem: https://seu-servidor.com/webhook-status</li>"
    html += "<li>Ao enviar: https://seu-servidor.com/webhook-delivery</li>"
    html += "</ul>"
    
    return html

@app.route('/webhook-status', methods=['GET', 'POST'])
def webhook_status():
    """Webhook para receber status de mensagens do WhatsApp via Z-API"""
    if request.method == 'GET':
        return jsonify({"status": "success", "message": "Webhook de status configurado e funcionando"}), 200
    try:
        print("===== WEBHOOK STATUS RECEBIDO =====")
        data = request.json
        print(f"Status recebido: {data}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Erro no webhook de status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook-delivery', methods=['GET', 'POST'])
def webhook_delivery():
    """Webhook para receber confirmação de entrega de mensagens do WhatsApp via Z-API"""
    if request.method == 'GET':
        return jsonify({"status": "success", "message": "Webhook de delivery configurado e funcionando"}), 200
    try:
        print("===== WEBHOOK DELIVERY RECEBIDO =====")
        data = request.json
        print(f"Delivery recebido: {data}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Erro no webhook de delivery: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook-connected', methods=['GET', 'POST'])
def webhook_connected():
    """Webhook para receber notificação de conexão do WhatsApp via Z-API"""
    if request.method == 'GET':
        return jsonify({"status": "success", "message": "Webhook de conexão configurado e funcionando"}), 200
    try:
        print("===== WEBHOOK CONNECTED RECEBIDO =====")
        data = request.json
        print(f"Connected recebido: {data}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Erro no webhook de connected: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook-disconnected', methods=['GET', 'POST'])
def webhook_disconnected():
    """Webhook para receber notificação de desconexão do WhatsApp via Z-API"""
    if request.method == 'GET':
        return jsonify({"status": "success", "message": "Webhook de desconexão configurado e funcionando"}), 200
    try:
        print("===== WEBHOOK DISCONNECTED RECEBIDO =====")
        data = request.json
        print(f"Disconnected recebido: {data}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Erro no webhook de disconnected: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook-presence', methods=['GET', 'POST'])
def webhook_presence():
    """Webhook para receber notificação de presença do WhatsApp via Z-API"""
    if request.method == 'GET':
        return jsonify({"status": "success", "message": "Webhook de presença configurado e funcionando"}), 200
    try:
        print("===== WEBHOOK PRESENCE RECEBIDO =====")
        data = request.json
        print(f"Presence recebido: {data}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Erro no webhook de presence: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Manter compatibilidade com o webhook antigo
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Webhook antigo para compatibilidade"""
    return on_message_received()

# Manter compatibilidade com o webhook-received
@app.route('/webhook-received', methods=['GET', 'POST'])
def webhook_received():
    """Webhook para compatibilidade"""
    return on_message_received()

# Adicionar endpoint para /receive (mencionado na documentação da Z-API)
@app.route('/receive', methods=['GET', 'POST'])
def receive():
    """Webhook para compatibilidade com o caminho /receive mencionado na documentação da Z-API"""
    print("Recebida requisição no endpoint /receive")
    return on_message_received()

@app.route('/verificar-zapi', methods=['GET'])
def verificar_zapi():
    """Endpoint para verificar o status da instância na Z-API"""
    try:
        # Endpoint para verificar o status da instância
        url = f"https://api.z-api.io/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/status"
        
        headers = {
            "Content-Type": "application/json",
            "Client-Token": Z_API_CLIENT_TOKEN
        }
        
        print(f"Verificando status da Z-API: {url}")
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {resp.status_code}  Resposta: {resp.text}")
        
        # Verificar webhooks configurados
        url_webhooks = f"https://api.z-api.io/instances/{Z_API_INSTANCE}/token/{Z_API_TOKEN}/webhooks"
        resp_webhooks = requests.get(url_webhooks, headers=headers, timeout=15)
        
        return jsonify({
            "status_instancia": resp.json() if resp.status_code == 200 else {"error": resp.text},
            "webhooks": resp_webhooks.json() if resp_webhooks.status_code == 200 else {"error": resp_webhooks.text}
        }), 200
    except Exception as e:
        print(f"Erro ao verificar status da Z-API: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ping', methods=['GET'])
def ping():
    """Endpoint simples para verificar se o servidor está respondendo"""
    print("Ping recebido!")
    return jsonify({
        "status": "success", 
        "message": "Servidor está funcionando!", 
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

def gerar_mensagem_llm(nome, cargo, empresa):
    """Gera uma mensagem personalizada usando OpenAI"""
    
    # Extrair apenas o primeiro nome do cliente
    primeiro_nome = obter_primeiro_nome(nome)
    
    prompt = f"""
    Aja como um especialista em automação de mensagens no WhatsApp com foco em vendas e conteúdo. Crie uma mensagem de boas-vindas para um novo lead que se inscreveu para acessar um material gratuito chamado Biblioteca IA. A mensagem deve ser curta, personalizada, descontraída e iniciar um relacionamento com base nesse interesse.

    O lead é um profissional da área de vendas (como SDR, vendedor, gerente, diretor ou dono de empresa). Ele preencheu um formulário com os seguintes dados dinâmicos que devem ser usados de forma natural: {{nome}}, {{cargo}}, {{empresa}}.

    Regras:

    A mensagem será enviada por WhatsApp, então deve parecer natural e conversacional.

    Use tom leve, direto e empático. Evite qualquer formalidade.

    A mensagem deve obrigatoriamente começar com a apresentação exata:
    "Fala, {{nome}}! Tudo bem? Me chamo Wald, agente de IA da Sales Pirates."
    (Essa frase deve ser usada exatamente como está, sem adaptações.)

    Mencione que vimos que ele solicitou acesso à Biblioteca IA, e inclua uma frase curta valorizando o conteúdo, como: "Esse material é uma mina de ouro pra quem tá querendo usar IA no comercial."

    Forneça o link direto para acesso à Biblioteca IA: https://workdrive.zohoexternal.com/folder/ve8di4c62be7c8ac54dbb9e50f02fa98deeee

    Finalize com uma pergunta aberta que incentive o diálogo e inclua um pequeno incentivo para ele responder (ex: "posso te mandar algo complementar depois", ou "pra eu entender melhor como posso te ajudar com isso").

    A mensagem deve ter no máximo 3 frases curtas (incluindo a apresentação).

    NÃO substitua os campos dinâmicos — mantenha exatamente como: {{nome}}, {{cargo}}, {{empresa}}.

    A saída esperada é uma única mensagem de WhatsApp, pronta para ser enviada automaticamente, sem explicações ou introduções.

    Exemplo de estrutura:
    "Fala {{nome}}! Tudo bem? Me chamo Wald, agente de IA da Sales Pirates. Vi que você acessou a Biblioteca IA — esse material é uma mina de ouro pra quem tá querendo usar IA no comercial. Aqui tá o link: https://workdrive.zohoexternal.com/folder/ve8di4c62be7c8ac54dbb9e50f02fa98deeee. Posso te mandar algo complementar depois?"
    """
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        mensagem = response.choices[0].message.content.strip()
        
        # Substitui os placeholders pelos valores reais
        mensagem = mensagem.replace("{{nome}}", primeiro_nome.strip())
        mensagem = mensagem.replace("{{cargo}}", cargo)
        mensagem = mensagem.replace("{{empresa}}", empresa)
        
        # Também substitui placeholders sem chaves duplas (caso a IA gere assim)
        mensagem = mensagem.replace("{nome}", primeiro_nome.strip())
        mensagem = mensagem.replace("{cargo}", cargo)
        mensagem = mensagem.replace("{empresa}", empresa)
        
        # Verificação final para garantir que não há mais placeholders
        if "{nome}" in mensagem or "{{nome}}" in mensagem:
            print("AVISO: Ainda há placeholders na mensagem!")
            # Força a substituição com uma mensagem garantida
            mensagem = f"Fala, {primeiro_nome.strip()}! Tudo bem? Me chamo Wald, agente de IA da Sales Pirates. Vi que você solicitou acesso à Biblioteca IA — esse material é uma mina de ouro pra quem tá querendo usar IA no comercial. Aqui tá o link: https://workdrive.zohoexternal.com/folder/ve8di4c62be7c8ac54dbb9e50f02fa98deeee. Me conta rapidinho: como tá o processo comercial aí na sua empresa?"
        
        return mensagem
    except Exception as e:
        print(f"Erro ao gerar mensagem: {e}")
        # Fallback para mensagem padrão garantida
        return f"Fala, {primeiro_nome.strip()}! Tudo bem? Me chamo Wald, agente de IA da Sales Pirates. Vi que você solicitou acesso à Biblioteca IA — esse material é uma mina de ouro pra quem tá querendo usar IA no comercial. Aqui tá o link: https://workdrive.zohoexternal.com/folder/ve8di4c62be7c8ac54dbb9e50f02fa98deeee. Me conta rapidinho: como tá o processo comercial aí na sua empresa?"

@app.route('/testar-mensagem', methods=['GET'])
def testar_mensagem():
    """Endpoint para testar a geração de mensagem"""
    try:
        nome = request.args.get('nome', 'Pedro')
        cargo = request.args.get('cargo', 'Gerente de Vendas')
        empresa = request.args.get('empresa', 'Empresa Teste')
        
        # Remove aspas do nome, se houver
        nome = nome.strip()
        if nome.startswith('"') and nome.endswith('"'):
            nome = nome[1:-1]
        elif nome.startswith("'") and nome.endswith("'"):
            nome = nome[1:-1]
            
        # Gera a mensagem
        mensagem = gerar_mensagem_llm(nome, cargo, empresa)
        
        # Verifica se a substituição funcionou
        if "{nome}" in mensagem or "{{nome}}" in mensagem:
            return jsonify({
                "status": "warning",
                "message": "Substituição de placeholders falhou",
                "mensagem_original": mensagem,
                "mensagem_corrigida": f"Fala, {nome}! Tudo bem? Me chamo Wald, agente de IA da Sales Pirates. Vi que você solicitou acesso à Biblioteca IA — esse material é uma mina de ouro pra quem tá querendo usar IA no comercial. Aqui tá o link: https://workdrive.zohoexternal.com/folder/ve8di4c62be7c8ac54dbb9e50f02fa98deeeer. Me conta rapidinho: como tá o processo comercial aí na sua empresa?"
            }), 200
        
        return jsonify({
            "status": "success",
            "mensagem": mensagem,
            "dados": {
                "nome": nome,
                "cargo": cargo,
                "empresa": empresa
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/conversa/<numero>', methods=['GET', 'DELETE'])
def gerenciar_conversa(numero):
    """Endpoint para visualizar e gerenciar o histórico de conversa de um número específico"""
    try:
        # Formatar o número para garantir consistência
        numero_formatado = formatar_numero_whatsapp(numero)
        
        if request.method == 'GET':
            # Obter o histórico de conversas do Supabase
            response = supabase.table("Conversas").select("*").eq("numero", numero_formatado).order("data", desc=False).execute()
            
            # Obter nome do cliente
            nome = obter_nome_cliente(numero_formatado)
            
            # Formatar para exibição HTML
            html = f"<h1>Conversa com {nome} ({numero_formatado})</h1>"
            html += "<style>"
            html += "body { font-family: Arial, sans-serif; margin: 20px; }"
            html += ".message { padding: 10px; margin: 5px; border-radius: 10px; max-width: 80%; }"
            html += ".received { background-color: #f1f0f0; float: left; }"
            html += ".sent { background-color: #dcf8c6; float: right; text-align: right; }"
            html += ".clear { clear: both; }"
            html += ".container { overflow: hidden; margin-bottom: 10px; }"
            html += ".timestamp { font-size: 0.8em; color: #888; margin-top: 5px; }"
            html += ".actions { margin-top: 20px; }"
            html += "button { padding: 10px; background-color: #ff6b6b; color: white; border: none; cursor: pointer; }"
            html += "</style>"
            
            html += "<div class='actions'>"
            html += f"<button onclick=\"if(confirm('Tem certeza que deseja limpar o histórico de {nome}?')) window.location.href='/conversa/{numero}/limpar'\">Limpar histórico</button>"
            html += "</div>"
            
            for conversa in response.data:
                tipo_classe = "received" if conversa["tipo"] == "recebida" else "sent"
                html += f"<div class='container'>"
                html += f"<div class='message {tipo_classe}'>"
                html += f"{conversa['mensagem']}"
                html += f"<div class='timestamp'>{conversa['data']}</div>"
                html += "</div>"
                html += "<div class='clear'></div>"
                html += "</div>"
            
            return html
                
        elif request.method == 'DELETE':
            # Excluir o histórico de conversas do Supabase
            response = supabase.table("Conversas").delete().eq("numero", numero_formatado).execute()
            return jsonify({"status": "success", "message": f"Histórico de {numero_formatado} excluído"}), 200
                
    except Exception as e:
        print(f"Erro ao gerenciar conversa: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/conversa/<numero>/limpar', methods=['GET'])
def limpar_conversa(numero):
    """Endpoint para limpar o histórico de conversa de um número específico"""
    try:
        # Formatar o número para garantir consistência
        numero_formatado = formatar_numero_whatsapp(numero)
        
        # Excluir o histórico de conversas do Supabase
        response = supabase.table("Conversas").delete().eq("numero", numero_formatado).execute()
        return redirect("/conversas")
                
    except Exception as e:
        print(f"Erro ao limpar conversa: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Adicionando a rota para testar a Dani
@app.route('/testar', methods=['GET'])
def testar():
    """Endpoint para testar o envio de mensagem para a teste"""
    try:
        # Busca a usuária na tabela biblioteca-ia
        response = supabase.table("biblioteca-ia").select("*").eq("nome", "João").execute()
        
        if not response.data:
            print("Usuário não encontrado. Tentando buscar com ILIKE...")
            # Tenta buscar com ILIKE para ser menos restritivo
            response = supabase.table("biblioteca-ia").select("*").ilike("nome", "%João%").execute()
            
            if not response.data:
                print("Nenhum usuário encontrado.")
                return jsonify({
                    "status": "error",
                    "message": "Usuário não encontrado"
                }), 404
        
        # Pega o primeiro usuário encontrado
        usuario = response.data[0]
        nome = usuario['nome']
        whatsapp = usuario['whatsapp']
        cargo = usuario.get('cargo', 'profissional')
        empresa = usuario.get('empresa', 'sua empresa')
        
        # Formatar o número para garantir consistência
        whatsapp_formatado = formatar_numero_whatsapp(whatsapp)
        
        # Verifica se a mensagem já foi enviada e se deve forçar o envio
        mensagem_ja_enviada = usuario.get('mensagem_enviada', False)
        force = request.args.get('force', '').lower() == 'true'
        
        if mensagem_ja_enviada and not force:
            print(f"Mensagem já foi enviada anteriormente para {nome}. Pulando abordagem inicial...")
            return jsonify({
                "status": "info",
                "message": f"Mensagem já foi enviada anteriormente para {nome}. Use o parâmetro force=true para enviar novamente."
            })
        
        print(f"Testando envio para: {nome}")
        print(f"WhatsApp: {whatsapp_formatado}")
        print(f"Cargo: {cargo}")
        print(f"Empresa: {empresa}")
        
        # Gera mensagem personalizada usando o prompt da Biblioteca IA
        mensagem = gerar_mensagem_llm(nome, cargo, empresa)
        
        # Envia mensagem e salva no banco através da função enviar_mensagem_whatsapp
        sucesso = enviar_mensagem_whatsapp(whatsapp_formatado, mensagem)
        
        if sucesso:
            # Salva mensagem enviada - usando a função salvar_conversa para garantir consistência
            salvar_conversa(whatsapp_formatado, nome, mensagem, "enviada")
            
            # Atualiza o status no banco de dados
            supabase.table("biblioteca-ia").update({"mensagem_enviada": True}).eq("id", usuario['id']).execute()
            
            return jsonify({
                "status": "success",
                "mensagem": mensagem,
                "nome": nome,
                "whatsapp": whatsapp_formatado
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Falha ao enviar mensagem"
            }), 500
            
    except Exception as e:
        print(f"Erro ao testar: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/testar-dani-webhook', methods=['GET'])
def testar_dani_webhook():
    """Endpoint para simular o recebimento de uma mensagem da Dani e salvar no Supabase"""
    try:
        # Obtém a mensagem da query string ou usa uma padrão
        mensagem = request.args.get('mensagem', 'Olá, estou testando o webhook!')
        
        # Busca a usuária Dani na tabela biblioteca-ia
        response = supabase.table("biblioteca-ia").select("*").eq("nome", "João").execute()
        
        if not response.data:
            print("Usuário João não encontrado. Tentando buscar com ILIKE...")
            # Tenta buscar com ILIKE para ser menos restritivo
            response = supabase.table("biblioteca-ia").select("*").ilike("nome", "%João%").execute()
            
            if not response.data:
                print("Nenhum usuário com nome João encontrado.")
                return jsonify({
                    "status": "error",
                    "message": "Usuário João não encontrado"
                }), 404
        
        # Pega o primeiro usuário encontrado
        usuario = response.data[0]
        nome = usuario['nome']
        whatsapp = usuario['whatsapp']
        
        # Formatar o número para garantir consistência
        whatsapp_formatado = formatar_numero_whatsapp(whatsapp)
        
        print(f"Simulando recebimento de mensagem de: {nome}")
        print(f"WhatsApp: {whatsapp_formatado}")
        print(f"Mensagem: {mensagem}")
            
        # Salva mensagem recebida no Supabase
        data_recebida = {
            "numero": whatsapp_formatado,
            "nome": nome,
            "mensagem": mensagem,
            "tipo": "recebida",
            "data": time.strftime("%Y-%m-%d %H:%M:%S"),
            "id": str(uuid.uuid4())  # Gera um UUID para o ID
        }
        
        # Salvar no Supabase
        try:
            insert_response = supabase.table("Conversas").insert(data_recebida).execute()
            print(f"Mensagem recebida salva no Supabase: {insert_response}")
        except Exception as e:
            print(f"Erro ao salvar mensagem recebida no Supabase: {e}")
        
        # Gera resposta com IA
        historico = obter_historico_conversa(whatsapp_formatado)  # Buscar o histórico real do Supabase
        resposta = gerar_resposta_ia(historico, mensagem, nome)
        
        # Verificação adicional para placeholders que possam ter escapado
        primeiro_nome = obter_primeiro_nome(nome)
        if "{{nome}}" in resposta:
            resposta = resposta.replace("{{nome}}", primeiro_nome)
            print("Substituído placeholder {{nome}} pelo primeiro nome do cliente")
        if "{nome}" in resposta:
            resposta = resposta.replace("{nome}", primeiro_nome)
            print("Substituído placeholder {nome} pelo primeiro nome do cliente")
            
        # Envia resposta
        sucesso = enviar_mensagem_whatsapp(whatsapp_formatado, resposta)
        
        if sucesso:
            # Salva resposta enviada usando a função salvar_conversa para garantir consistência
            salvar_conversa(whatsapp_formatado, nome, resposta, "enviada")
            
            return jsonify({
                "status": "success",
                "mensagem_recebida": mensagem,
                "resposta_enviada": resposta,
                "nome": nome,
                "whatsapp": whatsapp_formatado
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Falha ao enviar resposta"
            }), 500
            
    except Exception as e:
        print(f"Erro ao testar webhook com João: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    # Verifica se a tabela Conversas existe no Supabase
    try:
        # Verificar se a tabela existe
        response = supabase.table("Conversas").select("count", count="exact").limit(1).execute()
        print("Tabela de conversas verificada")
    except Exception as e:
        print(f"Erro ao verificar tabela de conversas: {e}")
        print("Certifique-se de que a tabela Conversas existe no Supabase")
    
    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
