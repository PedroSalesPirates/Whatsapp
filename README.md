# Sistema de Conversas com WhatsApp e IA

Este projeto permite enviar mensagens pelo WhatsApp e manter conversas automatizadas com clientes usando inteligência artificial.

## Funcionalidades

- Envio de mensagens via WhatsApp usando a Z-API
- Recebimento de mensagens através de webhook
- Respostas automáticas usando OpenAI GPT
- Armazenamento do histórico de conversas no Supabase
- Personalização das respostas com base no histórico
- Suporte para dois aplicativos diferentes (leads e contatos)
- Envio em massa de mensagens para todos os clientes

## Requisitos

- Python 3.7+
- Flask
- Supabase
- OpenAI
- Z-API (conta e configuração)
- Werkzeug

## Instalação

1. Clone o repositório
2. Instale as dependências:
```
pip install -r requirements.txt
```

## Configuração

1. Configure sua conta na Z-API e obtenha as credenciais
2. Configure seu banco de dados Supabase
3. Crie uma tabela `conversas` no Supabase com os campos:
   - numero (texto)
   - nome (texto)
   - mensagem (texto)
   - tipo (texto) - 'enviada' ou 'recebida'
   - data (timestamp)

## Uso

### Iniciar o servidor

```
python wsgi.py
```

### Estrutura do aplicativo

O sistema agora consiste em dois aplicativos Flask separados que são servidos pelo mesmo servidor:

1. **app.py** - Gerencia leads e usa a tabela "leads" no Supabase
   - Acessível através do prefixo `/leads`
   - Exemplo: `/leads/on-message-received`

2. **appContato.py** - Gerencia contatos e usa a tabela "biblioteca-ia" no Supabase
   - Acessível através do prefixo `/contato`
   - Exemplo: `/contato/on-message-received`

### Configurar Webhooks na Z-API

Para configurar os webhooks, você precisa usar os endpoints específicos para cada aplicativo:

#### Para app.py (leads):

```
POST /leads/configurar-todos-webhooks
{
  "url": "https://seu-servidor.com"
}
```

#### Para appContato.py (contatos):

```
POST /contato/configurar-todos-webhooks
{
  "url": "https://seu-servidor.com"
}
```

### Enviar mensagem inicial

#### Para app.py (leads):

```
POST /leads/enviar-mensagem
{
  "numero": "5511999999999",
  "mensagem": "Olá! Tudo bem? Sou o Wald da Sales Pirates."
}
```

#### Para appContato.py (contatos):

```
POST /contato/enviar-mensagem
{
  "numero": "5511999999999",
  "mensagem": "Olá! Tudo bem? Sou o Wald da Sales Pirates."
}
```

### Enviar mensagens em massa

Para enviar mensagens para todos os clientes que ainda não receberam a primeira abordagem:

#### Para app.py (leads):

```
GET /leads/enviar-para-todos
```

#### Para appContato.py (contatos):

```
GET /contato/enviar-para-todos
```

Para forçar o reenvio mesmo para clientes que já receberam mensagens:

```
GET /leads/enviar-para-todos?force=true
GET /contato/enviar-para-todos?force=true
```

### Testar o sistema

#### Para app.py (leads):

- Testar envio: `/leads/testar`
- Testar webhook: `/leads/webhook-test`
- Ver conversas: `/leads/conversas`

#### Para appContato.py (contatos):

- Testar envio: `/contato/testar`
- Testar webhook: `/contato/webhook-test`
- Ver conversas: `/contato/conversas`

## Implantação no Render

Para implantar no Render:

1. Conecte seu repositório Git ao Render
2. Selecione o tipo de serviço "Web Service"
3. Defina o comando de construção como `pip install -r requirements.txt`
4. Defina o comando de inicialização como `gunicorn wsgi:application`
5. Defina a versão do Python (3.7+)

O sistema usará o arquivo `Procfile` para iniciar o servidor com o Gunicorn. 