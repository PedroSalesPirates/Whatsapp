# Sistema de Conversas com WhatsApp e IA

Este projeto permite enviar mensagens pelo WhatsApp e manter conversas automatizadas com clientes usando inteligência artificial.

## Funcionalidades

- Envio de mensagens via WhatsApp usando a Z-API
- Recebimento de mensagens através de webhook
- Respostas automáticas usando OpenAI GPT
- Armazenamento do histórico de conversas no Supabase
- Personalização das respostas com base no histórico

## Requisitos

- Python 3.7+
- Flask
- Supabase
- OpenAI
- Z-API (conta e configuração)

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
python appContato.py
```

### Enviar mensagem inicial

Faça uma requisição POST para `/enviar-mensagem` com o seguinte JSON:

```json
{
  "numero": "5511999999999",
  "mensagem": "Olá! Tudo bem? Sou o Wald da Sales Pirates."
}
```

### Configurar Webhook na Z-API

Existem duas maneiras de configurar o webhook:

#### 1. Pelo painel da Z-API:

1. Acesse sua conta na Z-API em https://app.z-api.io/
2. Selecione sua instância
3. No menu lateral, clique em "Webhooks"
4. Para cada evento que deseja monitorar:
   - Clique no evento (ex: "Ao receber")
   - Ative o botão para habilitar
   - No campo URL, insira: `https://seu-servidor.com/webhook`
   - Clique em Salvar

#### 2. Pela API (recomendado):

Faça uma requisição POST para `/configurar-todos-webhooks` com o seguinte JSON:

```json
{
  "url": "https://seu-servidor.com/webhook"
}
```

Isso configurará automaticamente todos os webhooks necessários para a mesma URL.

## Como funciona

1. Você envia uma mensagem inicial para um cliente
2. O cliente responde
3. O sistema recebe a mensagem via webhook
4. A IA gera uma resposta com base no histórico da conversa
5. A resposta é enviada automaticamente para o cliente
6. Todas as mensagens são salvas no banco de dados

## Personalização

Você pode personalizar o comportamento da IA editando o prompt no método `gerar_resposta_ia()` no arquivo `appContato.py`. 