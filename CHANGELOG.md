# Changelog

## 0.8.1 — Revisão técnica e refinamento visual
- Centralizada a normalização e persistência de produtos, removendo duplicação entre captura individual e lotes.
- Isolamento transacional por item em sessões de coleta para que uma falha não interrompa o restante do lote.
- Indicadores do dashboard calculados com agregações SQL, reduzindo leitura e processamento em memória.
- Ordenação de preços corrigida para manter itens sem conversão no final em ambas as direções.
- Removida migração redundante na inicialização.
- Dashboard redesenhado com navegação lateral escura, workspace claro, cartões mais legíveis e adaptação para telas menores.
- Preservados endpoints, campos, funcionalidades de captura, favoritos, histórico, alertas e coleta em lote.


## 0.8.0 — Sessões de coleta em lote
- Nova sessão de garimpo na extensão Firefox para páginas de busca/categoria do AliExpress.
- Prévia de até 40 produtos já carregados na página, com envio em lote para o DSI.
- Deduplicação por identidade do produto e atualização de produtos já cadastrados.
- Histórico persistente de sessões com contagem de novos, atualizados e ignorados.
- Nova área "Coleta automatizada" no dashboard.
- Coleta limitada ao conteúdo disponível na aba; sem navegação automática, bypass de login, CAPTCHA ou bloqueios.


## 0.7.0 — Favoritos e organização de oportunidades
- Produtos podem ser marcados/desmarcados como favoritos diretamente nos cards do dashboard.
- Nova seção de favoritos na visão geral e página dedicada com todos os produtos salvos.
- Estado de favorito persistido no SQLite por meio de migração aditiva (`products.is_favorite`).
- Novos endpoints `PUT /products/{id}/favorite` e `GET /favorites`.
- A API e a extensão passam a identificar a versão 0.7.0; o fluxo de captura da extensão foi preservado.
- Não há coleta automática nova nem alteração do mecanismo de histórico/alertas.



## 0.5.0 — Extensão Firefox: histórico e alertas
- Popup atualizado com indicadores de monitoramento e alertas não lidos.
- Consulta do histórico recente após captura de produto.
- Ação para marcar alertas como lidos.
- Melhorias de estado da conexão, identificação de página e mensagens de erro.
- Na época desta entrega, o backend permanecia na versão 0.4.0; esta versão incrementou somente a extensão.

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

## 0.6.0 — Extensão: pré-visualização e fluxo de captura
- A extensão agora lê e apresenta título, preço e vendedor antes de salvar.
- Captura utiliza os dados pré-visualizados, evitando uma segunda extração inconsistente no mesmo clique.
- Botão de captura fica habilitado somente quando API, página e dados estão prontos.
- Adicionados timeout de comunicação com a API, reconexão manual e proteção contra cliques duplicados.
- Melhoradas mensagens de estado, erros e rótulos da interface.
- Backend e banco permanecem inalterados; nenhuma coleta automática em segundo plano foi adicionada.
