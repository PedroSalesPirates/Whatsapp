from flask import Flask, redirect, url_for, jsonify

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

# Adicionar rotas de teste diretas
@app.route('/leads-test')
def leads_test():
    return jsonify({"status": "success", "message": "App Leads está funcionando!"})

@app.route('/contato-test')
def contato_test():
    return jsonify({"status": "success", "message": "App Contato está funcionando!"})

# Adicionar rotas específicas para as funções de teste
@app.route('/leads/testar')
def leads_testar():
    # Chamar a função testar do app_leads
    return app_leads_module.testar()

@app.route('/contato/testar')
def contato_testar():
    # Chamar a função testar do app_contato
    return app_contato_module.testar()

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
    """

# Para compatibilidade com gunicorn
application = app

if __name__ == "__main__":
    # Executar o aplicativo combinado
    app.run(host='0.0.0.0', port=5000, debug=True) 