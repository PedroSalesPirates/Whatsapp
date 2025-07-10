import os
from supabase import create_client, Client

# Configurações do Supabase
url: str = "https://xukjbccvcnxatoqfidhw.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1a2piY2N2Y254YXRvcWZpZGh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAyMjA1MzYsImV4cCI6MjA2NTc5NjUzNn0.EcHnw_2bHeBEhA5YO4shwLkjI8CBIshVpZ9FbeIBUAE"
supabase: Client = create_client(url, key)

# Consulta a tabela para selecionar apenas o registro do Pedro
response = supabase.table("biblioteca-ia").select("*").eq("nome", "Pedro ").execute()

# Dados brutos:
print("Dados brutos:")
print(response)

# Apenas os dados (mais limpo):
print("\nDados formatados:")
print(response.data)

# Se encontrou algum registro
if response.data:
    print("\nInformações do Pedro:")
    pedro = response.data[0]
    print(f"Nome completo: {pedro['nome']} {pedro['sobrenome']}")
    print(f"Empresa: {pedro['empresa']}")
    print(f"Cargo: {pedro['cargo']}")
    print(f"WhatsApp: {pedro['whatsapp']}")
    print(f"LinkedIn: {pedro['linkedin']}")
else:
    print("\nRegistro do Pedro não encontrado.")
