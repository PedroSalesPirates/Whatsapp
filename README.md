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

**IMPORTANTE:** Para que o chatbot responda corretamente às mensagens dos clientes, os webhooks devem ser configurados para apontar para as rotas raiz do servidor, não para as rotas específicas de cada aplicativo.

Para configurar os webhooks corretamente:

1. Acesse a página inicial do servidor
2. Na seção "Configuração de Webhooks", insira a URL base do seu servidor (ex: https://seu-servidor.com)
3. Clique nos botões "Configurar Webhooks Leads" e "Configurar Webhooks Contato"

Ou configure manualmente através das APIs:

```
POST /leads/configurar-todos-webhooks
{
  "url": "https://seu-servidor.com"
}

POST /contato/configurar-todos-webhooks
{
  "url": "https://seu-servidor.com"
}
```

Os webhooks serão configurados para as seguintes rotas:
- Ao receber mensagens: `/on-message-received`
- Status de mensagens: `/webhook-status`
- Confirmação de entrega: `/webhook-delivery`
- Outros eventos: `/webhook-connected`, `/webhook-disconnected`, etc.

### Enviar mensagem inicial

Para enviar uma mensagem inicial para um cliente específico:

```
GET /leads/testar
GET /contato/testar
```

### Enviar mensagens em massa

Para enviar mensagens para todos os clientes que ainda não receberam a primeira mensagem:

```
GET /leads/enviar-para-todos
GET /contato/enviar-para-todos
```

Parâmetros opcionais:
- `force=true` - Enviar para todos os clientes, mesmo que já tenham recebido mensagem
- `nome=Pedro` - Filtrar clientes pelo nome

### Solução de problemas

Se os clientes não estiverem recebendo respostas automáticas após responderem às mensagens:

1. Verifique se os webhooks estão configurados corretamente para apontar para as rotas raiz
2. Verifique os logs do servidor para identificar possíveis erros
3. Teste o webhook manualmente usando a rota `/webhook-test` 