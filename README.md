# Itineris 🌍✈️

Projeto acadêmico de simulação e agendamento de viagens baseado em arquitetura de microsserviços, desenvolvido para a disciplina de DevOps.

## 🏗️ Arquitetura

O ecossistema é composto por serviços isolados que se comunicam via REST:

- **API Gateway (`gateway` — porta `8000`):** Ponto de entrada único em NGINX atuando como proxy reverso e validando tokens JWT via `auth_request`.
- **Auth Service (`auth-service` — porta `8001`):** Autenticação *stateless* e emissão/validação de tokens JWT.
- **Roteiro Service (`roteiro-service` — porta `8002`):** Gerenciamento de destinos e orquestração da *Saga Pattern* para o agendamento.
- **Cotação Service (`cotacao-service` — porta `8003`):** Gerenciamento de orçamentos e reserva de passagens utilizando o padrão CQRS.

## 🚀 Tecnologias, Padrões e Práticas DevOps

- **Linguagem / Framework:** Python 3.13 com FastAPI
- **Banco de Dados:** SQLite via SQLModel (bancos independentes por microsserviço)
- **Padrões Adotados:** API Gateway, Saga Pattern (Orquestrada) e CQRS
- **CI/CD:**
  - **Git Flow:** `main` (homologação), `develop` (desenvolvimento) e `feature/*`.
  - **GitHub Actions:** Execução automatizada de build, testes (`pytest`), análise estática de código (SonarCloud) e publicação de imagens no Docker Hub.
  - **Deploy Contínuo:** Integração com o Render para entrega automática por ambiente.
- **Ambientes (DEV e HOMOL):**
  - Controlados via variáveis de ambiente (`ENV` / `AMBIENTE`).
  - Documentação Swagger (`/docs` e `/redoc`) habilitada em **DEV** e desabilitada em **HOMOL**.
- **Observabilidade:**
  - Instrumentação HTTP e de recursos via `prometheus-fastapi-instrumentator` expondo `/metrics` nos microsserviços (`auth-service`, `roteiro-service` e `cotacao-service`).
  - **Prometheus** para coleta de métricas e **Grafana** para visualização em dashboards.
- **Segurança:**
  - **Dependabot** para monitoramento e atualização de dependências.
  - **GitHub Secrets** no pipeline de CI/CD e **Kubernetes Secrets** para credenciais e chaves no cluster.
- **Versionamento (Semantic Versioning — `MAJOR.MINOR.PATCH`):**
  - `MAJOR`: alterações incompatíveis na API (*breaking changes*).
  - `MINOR`: novas funcionalidades compatíveis com versões anteriores.
  - `PATCH`: correções de bugs e ajustes internos retrocompatíveis.

---

## ☸️ Orquestração em Kubernetes (Minikube)

Todos os manifests estão organizados na pasta `k8s/`:

```text
k8s/
├── auth/             # ConfigMap, Secret, Deployment (2 réplicas) e Service
├── cotacao/          # ConfigMap, Secret, Deployment (2 réplicas) e Service
├── roteiro/          # ConfigMap, Secret, Deployment (2 réplicas) e Service
├── gateway/          # ConfigMap (nginx.conf), Deployment (2 réplicas) e Service
├── observabilidade/  # Prometheus e Grafana (com Data Source provisionado)
└── ingress.yaml      # NGINX Ingress expondo o API Gateway
```

### Pré-requisitos
- Docker Desktop em execução
- `kubectl` instalado
- `minikube` instalado

### 1. Iniciar o cluster e habilitar o Ingress
```powershell
minikube start --driver=docker
minikube addons enable ingress
```

### 2. Build e carregamento das imagens locais no Minikube
O `cotacao-service` utiliza a imagem publicada via CI/CD no Docker Hub (`henriqueknaul/itineris-cotacao:latest`). Para os serviços `auth-service` e `roteiro-service`, gere e carregue as imagens no cluster:

```powershell
docker build -t itineris-auth:latest ./auth-service
docker build -t itineris-roteiro:latest ./roteiro-service
minikube image load itineris-auth:latest
minikube image load itineris-roteiro:latest
```

### 3. Aplicar os manifests do Kubernetes
```powershell
kubectl apply -f k8s/cotacao/
kubectl apply -f k8s/auth/
kubectl apply -f k8s/roteiro/
kubectl apply -f k8s/gateway/
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/observabilidade/
```

### 4. Validar execução e réplicas
```powershell
kubectl get pods
kubectl get svc
kubectl get ingress
```
Todos os serviços da aplicação (`auth-service`, `cotacao-service`, `roteiro-service` e `gateway`) devem aparecer com **2 réplicas** em estado `Running`, além dos Pods do `prometheus` e do `grafana`.

### 5. Acessar a aplicação via Ingress
Em um terminal separado (preferencialmente como Administrador), mantenha o túnel ativo:
```powershell
minikube tunnel
```

Endpoints de verificação:
- **Gateway:** `http://localhost/health`
- **Auth Service:** `http://localhost/health/auth`
- **Roteiro Service:** `http://localhost/health/roteiro`
- **Cotação Service:** `http://localhost/health/cotacao`

### 6. Acessar Prometheus e Grafana (Observabilidade no Cluster)
**Prometheus:**
```powershell
kubectl port-forward svc/prometheus 9090:9090
```
Acesse `http://localhost:9090/targets` para confirmar que `auth-service`, `cotacao-service` e `roteiro-service` estão com status `UP`.

**Grafana:**
```powershell
kubectl port-forward svc/grafana 3000:3000
```
Acesse `http://localhost:3000` (usuário `admin`, senha `admin`). O Data Source do Prometheus já é provisionado automaticamente via `ConfigMap`.

---

## 🐳 Como executar localmente com Docker Compose

1. Clone o repositório:
   ```bash
   git clone [https://github.com/HenriqueKnaul/itineris.git](https://github.com/HenriqueKnaul/itineris.git)
   cd itineris
   ```
2. Configure as variáveis de ambiente com base no arquivo `.env.example`.
3. Suba toda a stack com Docker Compose:
   ```bash
   docker-compose up --build
   ```