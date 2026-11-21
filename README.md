# DSI — Dropshipping Intelligence 0.8.1

Extensão Firefox + API Python local + painel web para garimpar, catalogar e analisar produtos do AliExpress, com favoritos persistentes, histórico de preços, alertas e sessões de coleta em lote.

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
- A API 0.8.1 mantém compatibilidade com os endpoints anteriores.

## Novidades da extensão Firefox 0.5.0

- Popup redesenhado com estado da API e identificação da página de produto.
- Captura e atualização do produto com retorno da qualidade dos dados.
- Consulta dos seis registros mais recentes do histórico após a captura.
- Resumo de produtos com histórico, observações e alertas não lidos.
- Lista de alertas recentes com ação para marcá-los como lidos.
- Atualização manual dos indicadores do monitoramento.

Esta seção documenta a evolução da extensão na v0.5.0; os recursos de captura permanecem preservados na v0.8.0.

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
| GET | `/stats` | Indicadores do catálogo |
| GET | `/categories` | Categorias identificadas |
| GET | `/exchange-rates` | Taxas de conversão para BRL |

## Conversão cambial

A conversão para BRL continua sendo uma referência indicativa via Frankfurter (referência BCE). Não inclui spread, IOF, frete, tributos, tarifas ou cupons. Moeda ausente não é inferida automaticamente.

## Atualizar extensão Firefox (0.8.1)

1. Acesse `about:debugging#/runtime/this-firefox`.
2. Remova a extensão temporária antiga, se necessário.
3. Clique em **Carregar extensão temporária...** e selecione `extension/manifest.json`.
4. Atualize a aba do AliExpress antes de capturar.
5. O popup permite capturar um produto individual ou iniciar uma sessão de coleta em lote numa página de busca/categoria. O dashboard registra o histórico das sessões.

## Limitações conhecidas e próximos passos

- A sessão em lote coleta somente itens já carregados na página aberta; para mais resultados, role a listagem e execute outra sessão. Não existe navegação automática entre páginas ou coleta periódica em segundo plano.
- A extração depende da estrutura atual da página do AliExpress e pode não preencher todos os campos.
- A API é local e não possui autenticação. Não a exponha diretamente à internet.
- Próxima etapa recomendada: definir fonte permitida para atualização periódica, agendador configurável, regras de alerta (limiares) e notificações sem duplicidade.
