# airflow_and_dbt

Este repositório demonstra Airflow + dbt usando DuckDB com a arquitetura Medalhão (Landing Zone -> Bronze -> Silver -> Gold).

O que foi adicionado nesta mudança:
- Ingestão de CSV baseada em seed para o schema Landing Zone via `dbt seed`.
- Modelo Bronze que desduplica o estado mais recente por `case_id`.
- Tabela incremental Silver no DuckDB (estratégia merge), tipada e filtrada por `updated_at`.
- Modelo Gold agregado com KPIs prontos para negócio por empresa e produto.

## Tecnologias
- dbt-core + dbt-duckdb
- DuckDB como mecanismo analítico (banco de arquivo único).
- Nenhum serviço externo é necessário; o banco fica em `dbt/dbt_duckdb_medalhao/target/duckdb.db`.

## Projeto dbt
- Caminho do projeto: `dbt/dbt_duckdb_medalhao`
- Profiles: `dbt/dbt_duckdb_medalhao/profiles.yml`
- Seeds: `dbt/dbt_duckdb_medalhao/seeds/consumer_cases.csv`
- Models:
  - landing_zone: view(s) no schema `landing_zone`, a partir da tabela fonte `landing_zone.consumer_cases` (criada pelo seed)
  - bronze: views no schema `bronze`
  - silver: tabela incremental DuckDB no schema `silver`
  - gold: tabelas/views no schema `gold`

## Configuração
Atualize `dbt/dbt_duckdb_medalhao/profiles.yml` para DuckDB (já pré-configurado):
```
profile: dbt_duckdb_medalhao
outputs.dev:
  type: duckdb
  path: target/duckdb.db
  schema: main
```
Nenhuma credencial de nuvem é necessária. O arquivo do banco será criado automaticamente.

## Execução
A partir de `dbt/dbt_duckdb_medalhao`:

1) Instalar dependências (se houver):
- `dbt deps`

2) Carregar o CSV na Landing Zone (tabela DuckDB via seeds):
- `dbt seed`  # cria `landing_zone.consumer_cases`

3) Construir as camadas do medalhão:
- `dbt run --select landing_zone+ bronze+ silver+ gold+`
  - ou simplesmente: `dbt run`

4) (Opcional) Rodar testes:
- `dbt test`

### Executar via Airflow
- Após alterar o Dockerfile, é necessário reconstruir as imagens: `docker compose build --no-cache`
- Suba o stack: `docker compose up -d`
- Abra o Airflow em http://localhost:8080, habilite e dispare a DAG `dbt_medallion_pipeline`.
- A DAG executa as tarefas na ordem: dbt_deps -> dbt_seed -> dbt_run_medallion -> dbt_test.

## Estrutura do Projeto

Após limpeza e otimização, a estrutura final do projeto:

```
airflow_and_dbt/
├── dags/
│   └── dbt_medallion_dag.py
├── dbt/
│   └── dbt_duckdb_medalhao/
│       ├── macros/
│       │   └── generate_schema_name.sql
│       ├── models/
│       │   ├── bronze/
│       │   ├── silver/
│       │   ├── gold/
│       │   └── landing_zone/
│       ├── seeds/
│       │   └── consumer_cases.csv
│       ├── dbt_project.yml
│       ├── profiles.yml
│       └── README.md
├── .dockerignore
├── .gitignore
├── docker-compose.yaml
├── Dockerfile
├── README.md
├── ARTIGO_AIRFLOW_DBT_DUCKDB.md
└── requirements.txt
```

## Correções Aplicadas
- **Conflito de dependências**: Removido o arquivo de constraints do Airflow que causava conflito entre `protobuf==4.25.6` (Airflow) e `protobuf>=5.0` (dbt-core>=1.8.1).
- **Comando dbt não encontrado**: Atualizada a DAG para usar o caminho completo `/home/airflow/.local/bin/dbt` em vez de apenas `dbt`.
- **Versões compatíveis**: Fixadas versões `dbt-core>=1.8.1,<1.9.0` e `dbt-duckdb>=1.8.2` no requirements.txt.
- **Limpeza do projeto**: Removidos arquivos gerados automaticamente (target/, dbt_packages/, logs/) e criados .gitignore e .dockerignore otimizados.

## Arquivos de Configuração

### .gitignore
Configura o Git para ignorar:
- Logs do Airflow e dbt
- Arquivos gerados pelo dbt (target/, dbt_packages/)
- Bancos de dados DuckDB
- Arquivos Python compilados
- Configurações de IDE

### .dockerignore
Otimiza builds do Docker ignorando:
- Documentação e logs
- Arquivos gerados automaticamente
- Configurações locais

## Observações
- O modelo Silver usa incremental (merge) no DuckDB com chave `case_id`.
- Schemas (landing_zone, bronze, silver, gold) serão criados automaticamente pelo dbt no arquivo DuckDB, se não existirem.
- Aviso de compatibilidade entre dbt-core e dbt-duckdb é esperado, mas não afeta o funcionamento.
- Projeto otimizado para desenvolvimento e produção com arquivos desnecessários removidos.
