# Itineris 🌍✈️

Projeto acadêmico de simulação e agendamento de viagens baseado na arquitetura de microsserviços. Desenvolvido para a disciplina de DevOps.

## 🏗️ Arquitetura
O ecossistema é composto por serviços isolados comunicando-se via REST:
- **API Gateway (Nginx):** Ponto de entrada único e proxy reverso.
- **Auth Service:** Autenticação e emissão de tokens JWT.
- **Roteiro Service:** Gerenciamento de destinos e orquestração da Saga Pattern para o agendamento.
- **Cotação Service:** Gerenciamento de orçamento e reserva de passagens, utilizando o padrão CQRS.

## 🚀 Tecnologias e Padrões
- **Linguagem/Framework:** Python 3.13 com FastAPI
- **Banco de Dados:** SQLite via SQLModel (bancos independentes por microsserviço)
- **Padrões Adotados:** API Gateway, Saga Pattern (Orquestrada) e CQRS
- **Infraestrutura:** Docker e Docker Compose

## ⚙️ Como executar
1. Clone o repositório: `git clone https://github.com/HenriqueKnaul/itineris.git`
2. Configure as variáveis de ambiente baseando-se no arquivo `.env.example` (criar caso não exista).
3. Suba a infraestrutura via Docker:
   ```bash
   docker-compose up --build