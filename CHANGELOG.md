# Changelog

## 0.4.0 — Histórico de preços e alertas

- Adicionadas as tabelas `price_history` e `price_alerts`.
- Capturas com preço válido passam a gerar observações históricas.
- Alterações comparáveis de preço geram alertas; mudança de faixa/variantes gera alerta separado.
- Novos endpoints de histórico, alertas, leitura de alertas e resumo de monitoramento.
- Dashboard ganhou acesso ao histórico, gráfico simples e alertas recentes com ação para marcar como lido.
- Migração de banco permanece aditiva e preserva os produtos existentes.
- Monitoramento nesta versão é baseado em novas capturas pela extensão; coleta periódica automática ainda não está disponível.

## 0.3.0 — Dashboard e câmbio

- Dashboard visual, catálogo, filtros, ordenação e conversão indicativa para BRL.
