# DSI — Dropshipping Intelligence 0.4.0

Extensão Firefox + API Python local + painel web para organizar produtos capturados no AliExpress. A versão 0.4.0 acrescenta histórico de preços e alertas de alterações detectadas entre capturas.

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

Na primeira inicialização da v0.4.0, o backend cria as tabelas novas automaticamente. A migração é aditiva. Mesmo assim, mantenha o backup antes da atualização.

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

## Atualizar extensão Firefox

1. Acesse `about:debugging#/runtime/this-firefox`.
2. Remova a extensão temporária antiga, se necessário.
3. Clique em **Carregar extensão temporária...** e selecione `extension/manifest.json`.
4. Atualize a aba do AliExpress antes de capturar.

## Limitações conhecidas e próximos passos

- O histórico só avança quando há nova captura; ainda não existe robô de coleta periódica.
- A extração depende da estrutura atual da página do AliExpress e pode não preencher todos os campos.
- A API é local e não possui autenticação. Não a exponha diretamente à internet.
- Próxima etapa recomendada: definir fonte permitida para atualização periódica, agendador configurável, regras de alerta (limiares) e notificações sem duplicidade.
