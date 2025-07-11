from flask import Flask, redirect, url_for, jsonify, request

# Importar os aplicativos Flask de cada arquivo
import app as app_leads_module
import appContato as app_contato_module

# Criar um novo aplicativo Flask combinado
app = Flask(__name__)

# Registrar as rotas do app_leads com prefixo /leads
for rule in app_leads_module.app.url_map.iter_rules():
    # Pular a rota estática
    if rule.endpoint == 'static':
        continue
    
    # Obter a função de visualização do app original
    view_func = app_leads_module.app.view_functions[rule.endpoint]
    
    # Registrar a mesma função com o prefixo /leads
    # Garantir que a rota comece com /
    endpoint_rule = rule.rule
    if not endpoint_rule.startswith('/'):
        endpoint_rule = '/' + endpoint_rule
        
    app.add_url_rule(f"/leads{endpoint_rule}", f"leads_{rule.endpoint}", view_func, methods=rule.methods)

# Registrar as rotas do app_contato com prefixo /contato
for rule in app_contato_module.app.url_map.iter_rules():
    # Pular a rota estática
    if rule.endpoint == 'static':
        continue
    
    # Obter a função de visualização do app original
    view_func = app_contato_module.app.view_functions[rule.endpoint]
    
    # Registrar a mesma função com o prefixo /contato
    # Garantir que a rota comece com /
    endpoint_rule = rule.rule
    if not endpoint_rule.startswith('/'):
        endpoint_rule = '/' + endpoint_rule
        
    app.add_url_rule(f"/contato{endpoint_rule}", f"contato_{rule.endpoint}", view_func, methods=rule.methods)

# Adicionar rotas diretas para webhooks importantes
@app.route('/on-message-received', methods=['GET', 'POST'])
def webhook_direct():
    """Redireciona para ambos os webhooks de mensagem recebida"""
    try:
        # Primeiro tenta processar com o app de leads
        response_leads = app_leads_module.on_message_received()
        print("Webhook processado pelo app_leads")
        return response_leads
    except Exception as e:
        print(f"Erro ao processar webhook com app_leads: {e}")
        try:
            # Se falhar, tenta com o app de contato
            response_contato = app_contato_module.on_message_received()
            print("Webhook processado pelo app_contato")
            return response_contato
        except Exception as e:
            print(f"Erro ao processar webhook com app_contato: {e}")
            return jsonify({"status": "error", "message": "Erro ao processar webhook"}), 500

# Adicionar outras rotas de webhook diretas
webhook_routes = [
    '/webhook-status', 
    '/webhook-delivery', 
    '/webhook-connected', 
    '/webhook-disconnected',
    '/webhook-presence',
    '/webhook',
    '/webhook-received',
    '/receive'
]

# Função para criar handlers de webhook
def create_webhook_handler(webhook_name):
    def webhook_handler():
        try:
            # Primeiro tenta processar com o app de leads
            handler = getattr(app_leads_module, webhook_name.replace('-', '_'))
            response = handler()
            print(f"Webhook {webhook_name} processado pelo app_leads")
            return response
        except Exception as e:
            print(f"Erro ao processar {webhook_name} com app_leads: {e}")
            try:
                # Se falhar, tenta com o app de contato
                handler = getattr(app_contato_module, webhook_name.replace('-', '_'))
                response = handler()
                print(f"Webhook {webhook_name} processado pelo app_contato")
                return response
            except Exception as e:
                print(f"Erro ao processar {webhook_name} com app_contato: {e}")
                return jsonify({"status": "error", "message": f"Erro ao processar {webhook_name}"}), 500
    
    return webhook_handler

# Registrar todas as rotas de webhook
for route in webhook_routes:
    endpoint_name = route.replace('/', '').replace('-', '_')
    handler = create_webhook_handler(endpoint_name)
    app.add_url_rule(route, f"direct_{endpoint_name}", handler, methods=['GET', 'POST'])

# Adicionar rotas de teste diretas
@app.route('/leads-test')
def leads_test():
    return jsonify({"status": "success", "message": "App Leads está funcionando!"})

@app.route('/contato-test')
def contato_test():
    return jsonify({"status": "success", "message": "App Contato está funcionando!"})

@app.route('/')
def index():
    return """
    <h1>Sistema de Conversas WhatsApp</h1>
    <h2>Escolha um dos aplicativos:</h2>
    <ul>
        <li><a href="/leads/">App Leads</a></li>
        <li><a href="/contato/">App Contato</a></li>
    </ul>
    <p>Teste rápido: <a href="/leads-test">Testar App Leads</a> | <a href="/contato-test">Testar App Contato</a></p>
    <p>Teste de envio: <a href="/leads/testar">Testar Envio Leads</a> | <a href="/contato/testar">Testar Envio Contato</a></p>
    <p><strong>Envio em massa:</strong> <a href="/leads/enviar-para-todos">Enviar para todos os Leads</a> | <a href="/contato/enviar-para-todos">Enviar para todos os Contatos</a></p>
    
    <h2>Configuração de Webhooks</h2>
    <p><strong>IMPORTANTE:</strong> Para garantir que o chatbot responda às mensagens dos clientes, configure os webhooks da Z-API para apontarem para as rotas raiz:</p>
    <form id="configForm" style="margin: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px;">
        <label for="baseUrl">URL base do seu servidor (ex: https://seu-servidor.com):</label><br>
        <input type="text" id="baseUrl" name="url" style="width: 100%; padding: 8px; margin: 10px 0;" placeholder="https://seu-servidor.com"><br>
        <button type="button" onclick="configurarWebhooks('leads')" style="padding: 10px; background-color: #4CAF50; color: white; border: none; cursor: pointer; margin-right: 10px;">Configurar Webhooks Leads</button>
        <button type="button" onclick="configurarWebhooks('contato')" style="padding: 10px; background-color: #2196F3; color: white; border: none; cursor: pointer;">Configurar Webhooks Contato</button>
    </form>
    
    <script>
    function configurarWebhooks(app) {
        const baseUrl = document.getElementById('baseUrl').value;
        if (!baseUrl) {
            alert('Por favor, informe a URL base do servidor');
            return;
        }
        
        fetch(`/${app}/configurar-todos-webhooks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({url: baseUrl})
        })
        .then(response => response.json())
        .then(data => {
            alert(`Webhooks ${app} configurados: ${data.message}`);
            console.log(data);
        })
        .catch(error => {
            alert(`Erro ao configurar webhooks: ${error}`);
            console.error('Erro:', error);
        });
    }
    </script>
    
    <p>Webhooks configurados na raiz:</p>
    <ul>
        <li>/on-message-received</li>
        <li>/webhook</li>
        <li>/webhook-status</li>
        <li>/webhook-delivery</li>
        <li>... e outros</li>
    </ul>
    """

# Para compatibilidade com gunicorn
application = app

if __name__ == "__main__":
    # Executar o aplicativo combinado
    app.run(host='0.0.0.0', port=5000, debug=True) 