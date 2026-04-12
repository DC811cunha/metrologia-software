-- =============================================================
-- SoftMeter — Schema do Banco de Dados
-- Metrologia de Software: Plataforma de Inspeção de Conformidade
-- =============================================================

-- Extensão para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Usuários
CREATE TABLE IF NOT EXISTS tb_usuarios (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  nome         VARCHAR(150) NOT NULL,
  email        VARCHAR(200) NOT NULL UNIQUE,
  senha_hash   VARCHAR(255) NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sistemas de software avaliados
CREATE TABLE IF NOT EXISTS tb_sistemas (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_usuario   UUID NOT NULL REFERENCES tb_usuarios(id) ON DELETE CASCADE,
  nome         VARCHAR(150) NOT NULL,
  descricao    TEXT,
  responsavel  VARCHAR(150),
  status       VARCHAR(20) NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'arquivado')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Requisitos (cotas de software)
CREATE TABLE IF NOT EXISTS tb_requisitos (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_sistema       UUID NOT NULL REFERENCES tb_sistemas(id) ON DELETE CASCADE,
  codigo           VARCHAR(20) NOT NULL,           -- Ex: REQ-001
  descricao        TEXT NOT NULL,
  valor_nominal    DECIMAL(15, 4) NOT NULL,
  tolerancia_sup   DECIMAL(15, 4) NOT NULL,
  tolerancia_inf   DECIMAL(15, 4) NOT NULL,
  unidade          VARCHAR(30) NOT NULL,            -- Ex: segundos, %, R$
  criticidade      VARCHAR(10) NOT NULL DEFAULT 'menor'
                   CHECK (criticidade IN ('critico', 'maior', 'menor')),
  ativo            BOOLEAN NOT NULL DEFAULT TRUE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(id_sistema, codigo)
);

-- Ciclos de teste
CREATE TABLE IF NOT EXISTS tb_ciclos_teste (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_sistema       UUID NOT NULL REFERENCES tb_sistemas(id) ON DELETE CASCADE,
  versao_software  VARCHAR(50) NOT NULL,
  ambiente         TEXT,                            -- Descrição do ambiente de teste
  status           VARCHAR(20) NOT NULL DEFAULT 'aberto'
                   CHECK (status IN ('aberto', 'encerrado')),
  data_inicio      DATE NOT NULL DEFAULT CURRENT_DATE,
  data_fim         DATE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Medições individuais
CREATE TABLE IF NOT EXISTS tb_medicoes (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_ciclo              UUID NOT NULL REFERENCES tb_ciclos_teste(id) ON DELETE CASCADE,
  id_requisito          UUID NOT NULL REFERENCES tb_requisitos(id) ON DELETE CASCADE,
  valor_medido          DECIMAL(15, 4) NOT NULL,
  desvio_absoluto       DECIMAL(15, 4) GENERATED ALWAYS AS (valor_medido - (
                          SELECT valor_nominal FROM tb_requisitos WHERE id = id_requisito
                        )) STORED,
  status_conformidade   VARCHAR(10) NOT NULL DEFAULT 'pendente'
                        CHECK (status_conformidade IN ('aprovado', 'alerta', 'reprovado', 'pendente')),
  observacao            TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(id_ciclo, id_requisito)
);

-- Laudos de conformidade
CREATE TABLE IF NOT EXISTS tb_laudos (
  id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  id_ciclo             UUID NOT NULL UNIQUE REFERENCES tb_ciclos_teste(id) ON DELETE CASCADE,
  total_requisitos     INT NOT NULL DEFAULT 0,
  total_aprovados      INT NOT NULL DEFAULT 0,
  indice_conformidade  DECIMAL(5, 2) NOT NULL DEFAULT 0.00,  -- Percentual 0-100
  classificacao_final  VARCHAR(15) NOT NULL
                       CHECK (classificacao_final IN ('conforme', 'condicional', 'nao_conforme')),
  pdf_url              TEXT,
  observacoes_gerais   TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_sistemas_usuario ON tb_sistemas(id_usuario);
CREATE INDEX idx_requisitos_sistema ON tb_requisitos(id_sistema);
CREATE INDEX idx_ciclos_sistema ON tb_ciclos_teste(id_sistema);
CREATE INDEX idx_medicoes_ciclo ON tb_medicoes(id_ciclo);
CREATE INDEX idx_medicoes_requisito ON tb_medicoes(id_requisito);
CREATE INDEX idx_laudos_ciclo ON tb_laudos(id_ciclo);
