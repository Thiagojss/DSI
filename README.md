## v0.11.0 — Organização manual e categorias mais confiáveis

- No dashboard, clique em **Organizar** no card do produto, na tabela do Radar ou no comparador.
- Defina **nome personalizado**, **categoria própria** e **cor da borda**. A categoria digitada aparece como sugestão em futuras edições, mas não é uma taxonomia automática imposta pelo sistema.
- Nome/categoria capturados são preservados como fonte original; a personalização tem prioridade em **Produtos**, **Radar**, **Custos**, **filtros** e **estatísticas**.
- Novas capturas do mesmo anúncio **não apagam** os valores manuais. Para restaurar a fonte, deixe o nome/categoria vazios e selecione **Sem cor**.
- A categoria de captura tenta ler apenas *breadcrumbs* identificados, não menus de navegação globais; categorias ausentes ficam sem classificação até serem definidas.
- Endpoint: `PUT /products/{id}/organization` com `manual_title`, `manual_category` e `border_color` (`#RRGGBB` ou `null`). Envia os três campos, substituindo a personalização anterior.
- Migração aditiva: `manual_title`, `manual_category`, `border_color` e índice de categoria manual; o ZIP não inclui `data/dsi.db`.

**Atualização:** faça cópia de `data/dsi.db`, preserve a pasta `data` e atualize apenas arquivos de código. Reinicie a API e recarregue a extensão Firefox. Sem acesso a uma sessão real do AliExpress, a extração de categorias em páginas reais ainda precisa ser validada.

# DSI — Dropshipping Intelligence 0.9.0

Extensão Firefox + API Python local + painel web para garimpar, catalogar e analisar produtos do AliExpress, com favoritos persistentes, histórico de preços, alertas e sessões de coleta em lote.

## Versão 0.9.0 — Radar de garimpo e coleta enriquecida

- O dashboard agora inicia em **Radar de garimpo**, com interface mais densa e voltada para tomada de decisão: filtros por categoria, busca por produto ou fornecedor, classificação por evidência, tabela de comparação, faixa de preços em BRL, mediana por categoria, quantidade de dados conhecidos e comparador de até 3 anúncios.
- **Não misturamos preços ou avaliações em uma média geral entre categorias no Radar.** O painel inicia na categoria mais representada; use o seletor para comparar outros nichos. Selecionar "Todas" mostra o panorama por categoria, sem um preço mediano global.
- Listagens do AliExpress passam a reconhecer avaliações, contagem de opiniões e pedidos quando aparecem com **rótulos identificáveis** em português ou inglês, como `★ 4,8`, `1,2 mil avaliações`, `3 mil vendidos`, `4.9 (128)`, `128 reviews`, `2.5K sold`. Suporta números compactos (`mil`, `K`, `M`) sem confundir nota e volume.
- Captura enriquecida quando visíveis: **desconto explicitamente anunciado**, preço original riscado (se reconhecida a mesma moeda), frete descrito, texto de estimativa de entrega e fornecedor identificado pelo elemento do card. Esses dados aparecem no comparador de anúncios.
- Recapturas parciais **não apagam** preço anterior, categoria, nota, vendedor nem outros campos já conhecidos. Capturas sem novo preço não geram uma observação histórica repetida.
- Endpoint `GET /intelligence/radar?limit=2000` com limite máximo de 5.000 produtos. A interface indica quando a análise não cobre todo o catálogo.
- Banco atualizado por **migração aditiva** para os quatro novos campos (`original_price`, `discount_percent`, `shipping_text`, `delivery_text`), sem apagar nem recriar o banco existente.

**Precisão e limites:** os dados são transcritos do conteúdo visível na aba aberta. O AliExpress altera layout, idioma e informações por região. Campos não reconhecidos são mantidos em branco (—); não simulamos volume de vendas ou lucratividade. Desconto é uma afirmação do anúncio, não uma auditoria de preço. Uma contagem de pedidos exibida não comprova demanda futura. Valores cambiais são indicativos e não incluem frete, impostos ou tarifas. Comparação de preços exige categoria e moeda coerentes; produtos e variantes podem continuar sendo diferentes mesmo no mesmo nicho.

## Revisão técnica 0.8.1 — Otimização e dashboard

- Centralizada a preparação e gravação de produtos em uma única rotina compartilhada pela captura individual e pela coleta em lote, evitando divergência entre os dois fluxos.
- Cada item da coleta em lote agora é processado em uma transação isolada; uma falha de persistência em um produto não invalida os demais itens do lote.
- Indicadores do dashboard passaram a usar agregações SQL, evitando carregar todos os produtos para calcular contagens, categorias e qualidade média.
- Corrigida a ordenação por preço para manter produtos sem conversão no final, tanto em ordem crescente quanto decrescente.
- Removida uma execução redundante da migração na inicialização.
- Dashboard redesenhado com sidebar escura, área clara, cartões, espaçamento e estados responsivos mais consistentes. IDs e fluxos JavaScript existentes foram preservados.

## Novidades da versão 0.8.0 — Sessões automatizadas de coleta

- Na extensão Firefox, abra uma página de busca/categoria do AliExpress e use **Sessão de garimpo**.
- A extensão identifica até 40 produtos visíveis/carregados na página, apresenta uma prévia e envia o lote ao backend.
- O backend valida URLs e dados, deduplica pelo ID do AliExpress e atualiza produtos já existentes.
- Cada lote gera um registro persistente em `collection_sessions`, com totais encontrados, novos, atualizados e ignorados.
- O dashboard ganhou a área **Coleta automatizada**, com instruções e histórico das sessões.
- A coleta é acionada pelo usuário na aba aberta. Não há navegação automática entre páginas, coleta em segundo plano, nem tentativa de contornar login, CAPTCHA, bloqueios ou controles do marketplace.

## Novidades da versão 0.7.0 — Produtos favoritos

- Marque/desmarque produtos com o botão **♡ Favoritar** nos cards da visão geral e do catálogo.
- A visão geral tem uma seção com seus produtos favoritos.
- A página **Favoritos** reúne todos os produtos marcados e mostra a contagem atual.
- A seleção fica salva no SQLite e permanece após reiniciar a API ou atualizar o navegador.
- A migração adiciona apenas `products.is_favorite`; produtos existentes começam como não favoritos. Nenhum dado anterior é removido.
- Novos endpoints: `PUT /products/{id}/favorite` e `GET /favorites`.

## Novidades da extensão Firefox 0.6.0

- Pré-visualização do título, preço e vendedor antes de adicionar o produto.
- Botão de captura condicionado à disponibilidade da API e à validação dos dados da página.
- Captura usa o mesmo conjunto de dados apresentado na pré-visualização.
- Timeout nas chamadas à API, botão de reconexão e proteção contra cliques repetidos.
- Mensagens mais claras para páginas incompatíveis, falhas de extração e indisponibilidade do backend.
- A API 0.9.0 mantém compatibilidade com os endpoints anteriores.

## Novidades da extensão Firefox 0.5.0

- Popup redesenhado com estado da API e identificação da página de produto.
- Captura e atualização do produto com retorno da qualidade dos dados.
- Consulta dos seis registros mais recentes do histórico após a captura.
- Resumo de produtos com histórico, observações e alertas não lidos.
- Lista de alertas recentes com ação para marcá-los como lidos.
- Atualização manual dos indicadores do monitoramento.

Esta seção documenta a evolução da extensão na v0.5.0; os recursos de captura permanecem preservados na v0.9.0.

## Novidades da versão 0.4.0

- **Histórico de preços:** cada nova captura com preço válido gera uma observação vinculada ao produto.
- **Detecção de alterações:** compara a observação atual com a anterior quando a moeda é a mesma.
- **Alertas:** registra aumento ou redução de preço, percentual de variação quando calculável e estado de leitura.
- **Dashboard:** botão “Histórico” nos cartões, gráfico simples e lista cronológica; painel com alertas recentes.
- **API:** endpoints para consultar histórico, listar/marcar alertas e consultar resumo do monitoramento.
- **Migração aditiva:** cria as novas tabelas `price_history` e `price_alerts`; não remove nem recria `data/dsi.db` nem a tabela de produtos existente.

## Importante: como funciona o monitoramento

Nesta versão, o monitoramento é **baseado em novas capturas**. O DSI não consulta automaticamente páginas do AliExpress em segundo plano: para atualizar o histórico, abra a página do produto no Firefox e capture novamente com a extensão. Isso evita prometer uma coleta automática que ainda não foi implementada e respeita os limites e controles do marketplace. Uma rotina automática futura dependerá de fonte de dados permitida e estável (preferencialmente API oficial), agendamento, limites e tratamento de falhas.

As observações são armazenadas em moeda original. Alterações só geram alerta comparável quando a moeda atual e a anterior são iguais. Se a moeda mudar ou estiver ausente, não se calcula variação percentual.

## Requisitos

- Windows 10/11
- Python 3.10 ou superior
- Mozilla Firefox

## Atualização no Windows

1. Pare o servidor com `Ctrl + C`.
2. Faça uma cópia de segurança da pasta `data` (principalmente `data/dsi.db`).
3. Extraia o ZIP e substitua os arquivos do projeto. **Preserve a pasta `data` e o banco `dsi.db`.**
4. No VS Code, abra a raiz da pasta `DSI` e execute:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Se ainda não existir ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Na primeira inicialização da v0.4.0, o backend cria as tabelas de histórico automaticamente. Na v0.7.0, adiciona a coluna de favoritos; na v0.8.0, cria a tabela de sessões de coleta se ainda não existir. A migração é aditiva. Mesmo assim, mantenha o backup antes da atualização.

## Painel e documentação

- Dashboard: http://127.0.0.1:8000/dashboard
- API: http://127.0.0.1:8000/docs
- Saúde: http://127.0.0.1:8000/health

## Endpoints principais

| Método | Endpoint | Finalidade |
|---|---|---|
| GET | `/dashboard` | Painel visual |
| GET | `/health` | Estado da API e banco |
| POST | `/products` | Salvar/atualizar produto e registrar observação de preço |
| GET | `/products` | Catálogo com filtros e ordenação |
| GET | `/products/{id}` | Detalhes do produto |
| PUT | `/products/{id}/favorite` | Marcar/desmarcar favorito (`{"is_favorite": true/false}`) |
| GET | `/favorites` | Listar produtos favoritos |
| POST | `/collection-sessions` | Validar e salvar lote de produtos coletados pela extensão |
| GET | `/collection-sessions` | Consultar histórico de sessões de coleta |
| GET | `/products/{id}/history` | Histórico de preços do produto |
| GET | `/alerts` | Listar alertas (`?unread_only=true`) |
| PUT | `/alerts/{id}/read` | Marcar alerta como lido |
| GET | `/monitoring/summary` | Resumo das observações e alertas |
| PUT | `/products/{id}/currency` | Corrigir moeda de um produto |
| GET | `/intelligence/radar` | Análise do catálogo para comparações por categoria (limite explícito) |
| GET | `/stats` | Indicadores do catálogo |
| GET | `/categories` | Categorias identificadas |
| GET | `/exchange-rates` | Taxas de conversão para BRL |

## Conversão cambial

A conversão para BRL continua sendo uma referência indicativa via Frankfurter (referência BCE). Não inclui spread, IOF, frete, tributos, tarifas ou cupons. Moeda ausente não é inferida automaticamente.

## Atualizar extensão Firefox (0.10.0)

1. Acesse `about:debugging#/runtime/this-firefox`.
2. Remova a extensão temporária antiga, se necessário.
3. Clique em **Carregar extensão temporária...** e selecione `extension/manifest.json`.
4. Atualize a aba do AliExpress antes de capturar.
5. O popup permite capturar um produto individual ou iniciar uma sessão de coleta em lote numa página de busca/categoria. O dashboard registra o histórico das sessões.

## Limitações conhecidas e próximos passos

- A sessão em lote coleta somente itens já carregados na página aberta; para mais resultados, role a listagem e execute outra sessão. Não existe navegação automática entre páginas ou coleta periódica em segundo plano.
- A extração depende da estrutura atual da página do AliExpress e pode não preencher todos os campos.
- A API é local e não possui autenticação. Não a exponha diretamente à internet.
- Próxima etapa recomendada: conferir a coleta real nas versões/idiomas do AliExpress usados pelo usuário e registrar exemplos de cards não capturados para ajustar seletores com segurança; validar cenários com documentos reais de frete, tarifas e tributação.
- A nova análise prioriza comparação **descritiva**, sem nota de "produto vencedor" inventada. A falta de evidência não equivale a avaliação negativa do produto.

## v0.10.0 — Custos e margens por produto

O menu **Custos e margens** permite selecionar um item do catálogo, preencher uma simulação unitária e comparar cenários salvos **por categoria**. O DSI preserva todos os produtos e recursos das versões anteriores.

**Custos configuráveis (BRL/unidade):** preço de compra manual (opcional; na ausência, usa o preço coletado convertido), frete informado, alíquota hipotética de importação sobre compra + frete, custos de importação fixos, comissão de marketplace, tarifas de pagamento, tributos sobre venda, reserva de devolução, embalagem, anúncios/CPA e outros gastos. Também aceita preço de venda e meta de margem.

**Resultados:** custo fixo unitário, taxas variáveis na venda, custo total, lucro estimado, margem sobre receita (`lucro / venda`), ROI sobre custo total (`lucro / custo`), preço de equilíbrio e preço necessário à meta de margem, quando viável. Teste de resistência: venda -10%, compra +10% e ambos. Barras de composição de custos.

**Importante:** não existem alíquotas legais padronizadas na aplicação. Os campos percentuais iniciam em zero apenas como **premissas não verificadas**; confirme todos. Frete ausente permanece `null`, impedindo margem/lucro em vez de presumir frete grátis. Preço de venda ausente também impede calcular lucro. Um frete de `0` deve significar frete efetivamente grátis ou integralmente já tratado em outros custos. A ferramenta **não calcula tributos oficiais**, e a base de importação utilizada é uma simplificação configurável, não o cálculo da legislação brasileira. Verifique com profissional habilitado quando necessário.

**Preço de compra usado:** se não houver preço manual, usa o **preço mais recente coletado e convertido para BRL**, portanto a simulação muda se o preço da captura ou o câmbio utilizado mudar. Taxas de câmbio de contingência são sinalizadas. Para preservar uma cotação efetiva, informe preço manual. A análise salva premissas, não um comprovante da compra ou uma cotação cambial congelada.

**Persistência:** nova tabela `cost_scenarios` criada com `Base.metadata.create_all` no banco SQLite existente, sem apagar `data/dsi.db`. Um cenário editável por produto. Novos endpoints:

- `GET /products/{id}/cost-analysis` — obtém análise ou cenário inicial incompleto.
- `PUT /products/{id}/cost-analysis` — valida e grava as premissas (`CostInputs`).
- `GET /intelligence/costs` — análises registradas para comparação por categoria.

**Atualização:** faça backup da pasta `data`; substitua os arquivos do projeto, **nunca substitua ou delete o banco**; reinicie a API e recarregue a extensão no Firefox. Os endpoints anteriores permanecem. Testes `python tests/cost_analysis_test.py` e regressões existentes. O banco do usuário não acompanha o ZIP.
