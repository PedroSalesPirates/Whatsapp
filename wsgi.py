from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

# Importar os aplicativos Flask de cada arquivo
from app import app as app_leads
from appContato import app as app_contato

# Criar um aplicativo raiz vazio
app = Flask(__name__)

# Configurar o DispatcherMiddleware para rotear requisições
application = DispatcherMiddleware(app, {
    '/leads': app_leads,
    '/contato': app_contato
})

if __name__ == "__main__":
    # Executar o aplicativo combinado
    run_simple('0.0.0.0', 5000, application, use_reloader=True) 