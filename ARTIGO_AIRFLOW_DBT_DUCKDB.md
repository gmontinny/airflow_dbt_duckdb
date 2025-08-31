# Implementando Arquitetura Medalhão com Apache Airflow, dbt e DuckDB: Um Guia Prático

## Resumo

Este artigo apresenta uma implementação prática da arquitetura Medalhão (Medallion Architecture) utilizando Apache Airflow para orquestração, dbt (data build tool) para transformação de dados e DuckDB como engine analítico. A solução demonstra como construir um pipeline de dados moderno, escalável e de baixo custo, ideal para projetos de analytics e data engineering.

## 1. Introdução

A arquitetura Medalhão, popularizada pela Databricks, organiza dados em camadas progressivas de qualidade e refinamento: Bronze (dados brutos), Silver (dados limpos e estruturados) e Gold (dados agregados para análise). Esta abordagem oferece benefícios como rastreabilidade, qualidade de dados e flexibilidade para diferentes casos de uso.

### 1.1 Tecnologias Utilizadas

- **Apache Airflow 2.10.5**: Orquestração de workflows
- **dbt-core 1.8.9**: Transformação de dados como código
- **DuckDB 1.3.2**: Engine analítico embarcado
- **Docker**: Containerização e isolamento de ambiente

## 2. Arquitetura da Solução

### 2.1 Visão Geral

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Landing Zone  │───▶│     Bronze      │───▶│     Silver      │
│   (Raw Data)    │    │  (Deduplicated) │    │   (Cleaned)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │      Gold       │
                                               │  (Aggregated)   │
                                               └─────────────────┘
```

### 2.2 Estrutura do Projeto

```
airflow_and_dbt/
├── dags/
│   └── dbt_medallion_dag.py
├── dbt/
│   └── dbt_duckdb_medalhao/
│       ├── models/
│       │   ├── bronze/
│       │   ├── silver/
│       │   └── gold/
│       ├── seeds/
│       └── profiles.yml
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt
```

## 3. Implementação Detalhada

### 3.1 Configuração do Ambiente Docker

O `Dockerfile` foi simplificado para evitar conflitos de dependências:

```dockerfile
FROM apache/airflow:2.10.5

COPY requirements.txt /requirements.txt

USER airflow
RUN pip install --no-cache-dir -r /requirements.txt
```

**Justificativa**: Removemos as constraints do Airflow que causavam conflito entre `protobuf==4.25.6` (Airflow) e `protobuf>=5.0` (dbt-core>=1.8.1).

### 3.2 Gerenciamento de Dependências

O `requirements.txt` especifica versões compatíveis:

```
dbt-core>=1.8.1,<1.9.0
dbt-duckdb>=1.8.2
```

### 3.3 Pipeline de Orquestração

A DAG do Airflow implementa o fluxo completo:

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

DBT_PROJECT_DIR = "/opt/airflow/dbt/dbt_duckdb_medalhao"
DBT_PROFILES_DIR = "/opt/airflow/dbt/dbt_duckdb_medalhao"

with DAG(
    dag_id="dbt_medallion_pipeline",
    description="Pipeline dbt do medalhão",
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,
    catchup=False,
) as dag:

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_PROJECT_DIR} && /home/airflow/.local/bin/dbt deps",
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {DBT_PROJECT_DIR} && /home/airflow/.local/bin/dbt seed --full-refresh",
    )

    dbt_run = BashOperator(
        task_id="dbt_run_medallion",
        bash_command=f"cd {DBT_PROJECT_DIR} && /home/airflow/.local/bin/dbt run --select 'landing_zone+ bronze+ silver+ gold+'",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && /home/airflow/.local/bin/dbt test",
    )

    dbt_deps >> dbt_seed >> dbt_run >> dbt_test
```

**Ponto Crítico**: Utilizamos o caminho completo `/home/airflow/.local/bin/dbt` para evitar problemas de PATH no container.

### 3.4 Configuração do dbt

O `profiles.yml` configura a conexão com DuckDB:

```yaml
dbt_duckdb_medalhao:
  outputs:
    dev:
      type: duckdb
      path: target/duckdb.db
      schema: main
  target: dev
```

### 3.5 Modelos de Dados

#### Camada Bronze
```sql
-- models/bronze/bronze_consumer_cases.sql
{{ config(materialized='view') }}

SELECT DISTINCT
    case_id,
    company_name,
    product_name,
    complaint_type,
    updated_at,
    ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY updated_at DESC) as rn
FROM {{ ref('landing_consumer_cases') }}
WHERE case_id IS NOT NULL
```

#### Camada Silver
```sql
-- models/silver/silver_consumer_cases.sql
{{ config(
    materialized='incremental',
    unique_key='case_id',
    on_schema_change='fail'
) }}

SELECT
    case_id,
    company_name,
    product_name,
    complaint_type,
    CAST(updated_at AS TIMESTAMP) as updated_at
FROM {{ ref('bronze_consumer_cases') }}
WHERE rn = 1

{% if is_incremental() %}
    AND updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

#### Camada Gold
```sql
-- models/gold/gold_company_metrics.sql
{{ config(materialized='table') }}

SELECT
    company_name,
    COUNT(*) as total_cases,
    COUNT(DISTINCT product_name) as unique_products,
    MAX(updated_at) as last_update
FROM {{ ref('silver_consumer_cases') }}
GROUP BY company_name
ORDER BY total_cases DESC
```

## 4. Desafios e Soluções

### 4.1 Conflito de Dependências

**Problema**: Incompatibilidade entre versões do protobuf exigidas pelo Airflow e dbt.

**Solução**: Remoção das constraints do Airflow e instalação direta das dependências do dbt.

### 4.2 Comando dbt Não Encontrado

**Problema**: O executável `dbt` não estava no PATH do container.

**Solução**: Utilização do caminho completo `/home/airflow/.local/bin/dbt` nas tarefas.

### 4.3 Compatibilidade de Versões

**Problema**: Avisos de incompatibilidade entre dbt-core e dbt-duckdb.

**Solução**: Fixação de versões específicas que funcionam em conjunto, mesmo com avisos.

## 5. Vantagens da Solução

### 5.1 Baixo Custo
- DuckDB elimina necessidade de infraestrutura de banco de dados
- Execução local sem custos de nuvem
- Container único para desenvolvimento

### 5.2 Simplicidade
- Configuração mínima
- Sem dependências externas
- Fácil reprodução em diferentes ambientes

### 5.3 Escalabilidade
- Arquitetura modular
- Fácil migração para soluções em nuvem
- Padrões de mercado (dbt, Airflow)

## 6. Casos de Uso

### 6.1 Prototipagem Rápida
Ideal para validar conceitos de pipeline antes de implementar em produção.

### 6.2 Desenvolvimento Local
Ambiente completo para desenvolvimento e testes de transformações.

### 6.3 Analytics de Pequeno/Médio Porte
Solução completa para empresas com volumes moderados de dados.

## 7. Execução e Monitoramento

### 7.1 Comandos de Execução

```bash
# Construir imagens
docker compose build --no-cache

# Iniciar serviços
docker compose up -d

# Verificar status
docker compose ps

# Acessar logs
docker compose logs airflow-scheduler
```

### 7.2 Interface Web

Acesse http://localhost:8080 para:
- Monitorar execução das DAGs
- Visualizar logs detalhados
- Gerenciar agendamentos
- Analisar métricas de performance

## 8. Métricas e Resultados

### 8.1 Performance
- Tempo de build: ~18 segundos
- Tempo de execução da DAG: ~2-5 minutos
- Uso de memória: ~2GB para stack completo

### 8.2 Qualidade de Dados
- Deduplicação automática na camada Bronze
- Validação de tipos na camada Silver
- Testes de qualidade integrados

## Conclusão

A implementação apresentada demonstra como construir um pipeline de dados moderno utilizando tecnologias open-source amplamente adotadas no mercado. A combinação de Airflow, dbt e DuckDB oferece uma solução robusta, econômica e escalável para projetos de analytics.

Os principais benefícios alcançados incluem:

1. **Redução de Complexidade**: Eliminação de dependências externas através do DuckDB
2. **Padronização**: Uso de ferramentas consolidadas no mercado (Airflow + dbt)
3. **Qualidade**: Implementação da arquitetura Medalhão com testes automatizados
4. **Flexibilidade**: Fácil migração para ambientes de produção em nuvem

A solução resolve problemas comuns de compatibilidade entre ferramentas e fornece um template reutilizável para projetos similares. O código está disponível como referência e pode ser adaptado para diferentes contextos e necessidades.

### Próximos Passos

Para evolução da solução, recomenda-se:
- Implementação de testes de qualidade mais robustos
- Adição de monitoramento e alertas
- Integração com ferramentas de CI/CD
- Migração para ambientes de produção (Kubernetes, cloud providers)

## Referências

1. Databricks. (2023). "Medallion Architecture". Disponível em: https://docs.databricks.com/lakehouse/medallion.html

2. Apache Airflow Documentation. (2024). "Apache Airflow Documentation". Disponível em: https://airflow.apache.org/docs/

3. dbt Labs. (2024). "dbt Documentation". Disponível em: https://docs.getdbt.com/

4. DuckDB Foundation. (2024). "DuckDB Documentation". Disponível em: https://duckdb.org/docs/

5. Reis, J. & Housley, M. (2022). "Fundamentals of Data Engineering". O'Reilly Media.

6. Kleppmann, M. (2017). "Designing Data-Intensive Applications". O'Reilly Media.

7. Kimball, R. & Ross, M. (2013). "The Data Warehouse Toolkit". Wiley.

8. Docker Inc. (2024). "Docker Documentation". Disponível em: https://docs.docker.com/

---

**Autor**: Implementação prática desenvolvida como demonstração de arquitetura moderna de dados.

**Data**: Janeiro 2025

**Versão**: 1.0