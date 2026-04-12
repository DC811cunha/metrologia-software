# Diagramas de Arquitetura — SoftMeter

## Nível 1 — Diagrama de Contexto (C4)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOFTMETER                                │
│                  Sistema de Metrologia de Software              │
│                                                                 │
│  ┌───────────────┐    ┌───────────────┐    ┌────────────────┐   │
│  │  Analista QA  │    │  Gestor de TI │    │ Desenvolvedor  │   │
│  │               │    │               │    │                │   │
│  │ Registra      │    │ Consulta      │    │ Verifica       │   │
│  │ medições e    │    │ laudos e      │    │ conformidade   │   │
│  │ ciclos de     │    │ índices de    │    │ antes do       │   │
│  │ teste         │    │ conformidade  │    │ deploy         │   │
│  └───────┬───────┘    └───────┬───────┘    └───────┬────────┘   │
│          │                   │                     │            │
│          └───────────────────┴─────────────────────┘            │
│                              │                                  │
│                              ▼                                  │
│                   ┌──────────────────┐                          │
│                   │  SoftMeter App   │                          │
│                   │  (Web App)       │                          │
│                   └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## Nível 2 — Diagrama de Containers (C4)

```
┌──────────────────────────────────────────────────────────────────┐
│  Usuário (Browser)                                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Frontend SPA (React + TypeScript)                          │ │
│  │  Porta: 3000                                                │ │
│  │  Responsabilidade: Interface, navegação, chamadas à API     │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │ REST / HTTPS / JSON                │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │  Backend API (Node.js + Express + TypeScript)               │ │
│  │  Porta: 3001                                                │ │
│  │  Responsabilidade: Autenticação, regras de negócio,        │ │
│  │  cálculo de desvios, geração de laudos PDF                 │ │
│  └──────────┬──────────────────────────────┬───────────────────┘ │
│             │ SQL                          │ PDF                 │
│  ┌──────────▼──────────┐    ┌─────────────▼───────────────────┐ │
│  │ PostgreSQL          │    │ PDF Generator (pdfkit)          │ │
│  │ Porta: 5432         │    │ (biblioteca interna)            │ │
│  │ Dados: sistemas,    │    │ Responsabilidade: geração do    │ │
│  │ requisitos,         │    │ Laudo de Conformidade em PDF    │ │
│  │ medições, laudos    │    │                                 │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Nível 3 — Diagrama de Componentes do Backend (C4)

```
Backend API (Node.js + Express)
│
├── routes/
│   ├── auth.routes.ts          → AuthController
│   ├── sistemas.routes.ts      → SistemasController
│   ├── requisitos.routes.ts    → RequisitosController
│   ├── ciclos.routes.ts        → CiclosController
│   ├── medicoes.routes.ts      → MedicoesController
│   └── laudos.routes.ts        → LaudosController
│
├── controllers/
│   ├── AuthController          → Recebe HTTP, valida entrada, delega ao Service
│   ├── SistemasController      → CRUD de sistemas
│   ├── RequisitosController    → CRUD de requisitos com tolerâncias
│   ├── CiclosController        → Abertura/encerramento de ciclos
│   ├── MedicoesController      → Registro de medições
│   └── LaudosController        → Geração e consulta de laudos
│
├── services/
│   ├── auth.service.ts         → JWT, bcrypt, registro/login
│   ├── sistemas.service.ts     → Regras de sistemas
│   ├── requisitos.service.ts   → Regras de cotas
│   ├── ciclos.service.ts       → Regras de ciclos (encerramento)
│   ├── medicoes.service.ts     → ⭐ NÚCLEO: cálculo de desvios e conformidade
│   └── laudos.service.ts       → Índice de conformidade, classificação, PDF
│
├── repositories/
│   ├── usuarios.repository.ts  → Queries PostgreSQL de usuários
│   ├── sistemas.repository.ts  → Queries de sistemas
│   ├── requisitos.repository.ts→ Queries de requisitos
│   ├── ciclos.repository.ts    → Queries de ciclos
│   ├── medicoes.repository.ts  → Queries de medições
│   └── laudos.repository.ts    → Queries de laudos
│
└── middleware/
    ├── auth.middleware.ts       → Validação de JWT
    ├── validate.middleware.ts   → Validação de body/params
    └── error.middleware.ts      → Tratamento centralizado de erros
```

## Fluxo de Dados — Geração de Laudo

```
Usuário encerra ciclo
        │
        ▼
CiclosController.encerrar()
        │
        ▼
CiclosService.encerrarCiclo(id_ciclo)
  ├── Valida: ciclo existe e está aberto
  ├── Valida: todos os requisitos ativos têm medição
  ├── Atualiza status do ciclo para 'encerrado'
        │
        ▼
LaudosService.gerarLaudo(id_ciclo)
  ├── Busca todas as medições do ciclo
  ├── Calcula: totalRequisitos, totalAprovados
  ├── Calcula: indiceConformidade = (aprovados/total) × 100
  ├── Verifica: tem crítico reprovado? → nao_conforme imediato
  ├── Classifica: conforme (≥90%) / condicional (70-89%) / nao_conforme (<70%)
  ├── Gera PDF do laudo
  └── Persiste tb_laudos
        │
        ▼
Retorna Laudo de Conformidade ao usuário
```

## Modelo de Dados (DER simplificado)

```
tb_usuarios (1) ──────────── (N) tb_sistemas
                                       │
                              ┌────────┴──────────┐
                              │                   │
                             (N)                 (N)
                         tb_requisitos     tb_ciclos_teste
                              │                   │
                              │                   │
                             (N)                 (1)
                          tb_medicoes ────── tb_laudos
                         (N por ciclo,
                          1 por requisito
                          dentro do ciclo)
```
