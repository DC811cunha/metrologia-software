# ADR-002: Modelo de Dados Relacional Inspirado em Metrologia Industrial

**Data:** 12/04/2026
**Status:** Substituído (modelo de dados da proposta original)
**Autor:** Diego Cunha

> **Nota (05/11/2026):** este ADR registra o modelo da RFC v1.0 (sistemas, requisitos, ciclos de
> teste, medições e laudos digitados manualmente). Com o pivô de arquitetura (ADR-003) o produto
> passou a analisar repositórios GitHub automaticamente, e o modelo vigente tem 6 tabelas —
> `users`, `repositories`, `analyses`, `measurements`, `reports` e `password_reset_tokens`
> (esta última do ADR-005). Ver `specs/001-softmeter-plataforma-mvp/data-model.md` e a seção 5.2
> do RFC-001. Mantido como registro histórico; os princípios de UUID como chave primária e de
> rastreabilidade entre medição e resultado continuam valendo.

---

## Contexto

O framework de Metrologia de Software exige rastreabilidade completa entre requisitos,
medições e laudos — análoga à rastreabilidade metrológica exigida pela ISO 10012
na indústria de manufatura. O modelo de dados precisa refletir essa cadeia de forma
estruturada e auditável.

## Decisão

Adotar modelo relacional com 5 entidades principais:

```
tb_usuarios → tb_sistemas → tb_requisitos
                         → tb_ciclos_teste → tb_medicoes → tb_laudos
```

Cada entidade possui UUID como chave primária para compatibilidade com ambientes
distribuídos e segurança (IDs não sequenciais não revelam volume de dados).

## Justificativa

- **Rastreabilidade:** cada medição referencia explicitamente o requisito e o ciclo,
  garantindo trilha de auditoria completa (equivalente ao rastreamento de calibração
  na metrologia industrial)
- **Integridade referencial:** FKs com ON DELETE CASCADE garantem consistência
  quando sistemas ou requisitos são removidos
- **Desvio calculado:** campo `desvio_absoluto` é GENERATED ALWAYS AS no PostgreSQL,
  eliminando inconsistências entre valor armazenado e calculado
- **UUID:** evita enumeração sequencial de recursos via API (segurança)

## Consequências

- Modelo não suporta NoSQL nesta versão — decisão intencional para maximizar
  integridade dos dados de conformidade
- Migrações futuras devem preservar rastreabilidade histórica (não deletar medições antigas)
