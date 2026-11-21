## v0.18.0 — Auditoria, imagens e fornecedor
- Campos de galeria (até 16 URLs), link da loja e avaliações específicas da loja, sem confundir com nota do anúncio.
- Coleta dos dados existentes em DOM/JSON-LD; não percorre sites automaticamente. Campos ausentes permanecem nulos.
- Nova migração aditiva com backup consistente antes de novas colunas.
- Settings: backup manual, exportação CSV com proteção contra fórmulas e verificação de integridade SQLite.
- Bloqueio de requisições de escrita de origens web externas e cabeçalhos de segurança básicos. Isso **não substitui autenticação**: API local ainda precisa de mecanismo de pareamento antes da publicação.
- Testes automatizados para persistência, migração, exportação e bloqueio de origem.

## v0.18.0 — organização por blocos e filtros pessoais
- Navegação lateral por categorias pessoais com contadores.
- Filtros por organizado, não organizado, favoritos e cor.
- Seleção preservada entre filtros e menu modal para aplicar categoria/cor em até 200 produtos.
- Sem migrações: reutiliza o endpoint atômico existente.
- Diagnóstico de qualidade recolhível para reduzir ruído.

## v0.16.0 — Experiência de instalação e diagnóstico
- Iniciadores `.bat` para Windows: primeira instalação isolada em `.venv` e inicialização subsequente em um clique.
- Iniciador Python padrão com verificação de dependências, detecção de porta ocupada, prevenção de segunda instância, abertura do painel e bind exclusivo em `127.0.0.1`.
- Diagnóstico sem inicialização do banco (Python, dependências, porta, saúde da API); instruções de recuperação.
- Popup oferece orientação contextual quando o servidor não responde.
- API, manifesto, painel e testes atualizados para v0.16.0. Sem alterações no schema do banco.
- Limite: não é instalador nativo nem pacote AMO pronto para publicação; revisão de segurança pendente.

## v0.15.0 — Oportunidades explicáveis
- Ranking por categoria com margens simuladas, estresse e lacunas de evidência.
- Endpoint GET /intelligence/opportunities.
- Nenhum dado de demanda ou equivalência de produtos é inferido.
- Mantém a v0.14 e banco sem migração.

## v0.14.0 — Auditoria de cobertura e edição em lote (2026-11-21)

- Endpoint de qualidade da coleta por campo/categoria.
- Organização em lote com atualização atômica de categoria e cor.
- Mantidos dados anteriores e esquema do banco.

## v0.13.0 — Garimpo progressivo com intervalo de 24 horas (2026-11-21)
- A extensão varre todos os cards já carregados no DOM e seleciona até 40 IDs elegíveis por sessão.
- O servidor bloqueia novas capturas em lote do mesmo ID durante 24 horas; vale para outras buscas/categorias.
- Endpoint `POST /collection-eligibility` permite ignorar previamente IDs bloqueados antes do envio.
- O popup atualiza automaticamente o próximo lote após salvar; botão manual para reler após rolagem.
- Coluna `last_batch_collected_at` adicionada por migração aditiva; capturas individuais permanecem independentes.
- O lote é verificado novamente no servidor; itens bloqueados não geram atualizações nem histórico.
- Sem rolagem automática, sem contorno de controles de acesso.

## v0.12.0 — Configurações / limpeza segura (2026-11-21)
- Nova seção **Configurações (Settings)** com indicadores de registros do banco.
- Limpeza sob confirmação digitada (LIMPAR PRODUTOS), com backup consistente SQLite obrigatório antes da transação.
- Exclusão de produtos e registros associados (histórico, alertas, custos, sessões), preservando banco, tabelas, índices e migrações.
- Interface atualiza os painéis após a limpeza; backups salvos em `data/backups/`.
- Não exclui cache de câmbio ou outras tabelas não relacionadas ao catálogo.

## 0.11.0 — Catálogo organizado pelo usuário

- Renomeação de itens, categorias próprias e cores de borda persistentes em produtos.
- Nomes/categorias originais mantidos separados das escolhas manuais.
- Sincronização das categorias efetivas com Radar, Custos, estatísticas e filtros.
- Captura de categorias restrita a trilha de navegação, sem menus globais.
- Migração incremental e testes de organização, recaptura e interface responsiva.

# Changelog

## 0.9.0 — Radar de garimpo e coleta aprofundada
- Nova página principal dedicada ao garimpo: panorama por categoria, histogramas de preço, cobertura de dados, tabela com ordenação e comparação de até 3 anúncios.
- Medianas apenas por categoria, evitando médias de produtos não relacionados.
- Parser de cards aprimorado para estrelas, contagens de avaliações e pedidos rotulados, milhares e milhões em PT/EN.
- Captura adicional de desconto anunciado, preço riscado de mesma moeda, frete e entrega visíveis, e fornecedor quando identificado.
- Coletas parciais preservam campos consolidados; sem novo preço não se inventa nova observação.
- Novo endpoint `GET /intelligence/radar`.
- Migração SQLite aditiva para novos campos de anúncio, sem alterar banco existente no pacote.
- Testes de extração, API e comportamento do novo painel.


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

## 0.10.0 — Custos, margens e teste de resistência
- Nova aba de custos com formulário por produto, comparação por categoria e composição visual de custos.
- Motor decimal para lucro, ROI, margem, equilíbrio, meta de margem e estresse ±10%.
- Registro persistente de um cenário editável por produto em tabela aditiva `cost_scenarios`.
- Nenhuma alíquota tributária presumida; frete e venda ausentes impedem lucro estimado.
- Novos endpoints GET/PUT `/products/{id}/cost-analysis`, GET `/intelligence/costs`.
- Testes de cenários, limites, validação, banco e interface desktop/mobile.
