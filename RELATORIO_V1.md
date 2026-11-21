# DSI v1.0.0 — Relatório de preparação de lançamento

**Status: candidata a lançamento, não publicada.** Data: 21/11/2026.

## Implementado
- Autenticação local por chave aleatória de 256 bits, persistida em `data/.dsi_access_token`, nunca incluída no pacote.
- Proteção de rotas de dados, exportação CSV, backups e exclusão; rejeição de origens web externas e Host não local.
- Pareamento manual do popup Firefox com a API; chave guardada em `browser.storage.local`, com opção de desconectar.
- Dashboard servido localmente com credencial temporariamente incorporada no HTML da resposta; cache desabilitado e bloqueio de incorporação em frames.
- Preflight CORS explicitamente permitido para a extensão e cabeçalhos exigidos, sem permitir operações sem autenticação.
- Declaração `websiteContent` no manifesto Firefox para transmissão de dados do anúncio ao aplicativo local, Firefox mínimo 140.
- Ícones, exportação autenticada, manifest atualizado, scripts de empacotamento e documentação de privacidade.
- Detecção de versão de API antiga no iniciador.

## Verificações executadas
- Testes Python de regressão: audit_v018, beta_workflow, collection_cooldown, collection_session, cost_analysis, launcher, migration_favorites, migration_v018, opportunities, organization, quality_bulk, radar, research_workflow, settings e smoke: **aprovados**.
- Teste adicional security_launch: sem token, token incorreto, token válido, CORS preflight, origem maliciosa, Host externo, CSV e backup: **aprovado**.
- Contratos JS: catalog_ui, collection, extension, listing_metrics, listing_pagination e supplier_gallery: **aprovados**.
- Compilação Python, sintaxe JS, manifesto JSON: **aprovados**.
- Teste estático do dashboard no Chromium (sem integração HTTP): troca de Mesa, Oportunidades e Settings, chave renderizada, sem exceções JS e sem overflow global mobile: **aprovado**.
- Servidor FastAPI respondeu corretamente ao endpoint `/health` via HTTP real: **aprovado**.

## Verificações não concluídas neste ambiente
- Navegação HTTP do Chromium para o localhost foi bloqueada por política do ambiente (`ERR_BLOCKED_BY_ADMINISTRATOR`); portanto **não** é um teste end-to-end completo.
- Testes manuais Windows 10/11 e Firefox no AliExpress, diferentes layouts de produtos e fornecedores.
- `web-ext lint` oficial e assinatura Mozilla (ferramenta não pré-instalada; exige preparação de ambiente e conta da Mozilla).
- Empacotamento e assinatura de um instalador Windows nativo (distribuição atual é Python + BAT).
- Publicação oficial: depende de conta de publicador, identidade de complemento permanente, licença e validação de políticas/termos.

## Política de dados
O complemento acessa conteúdo do AliExpress quando o usuário pede a captura e transmite os campos extraídos ao serviço local. O servidor usa SQLite; não há serviço remoto DSI. Ver `PRIVACIDADE.md`. As consultas de câmbio e o carregamento de imagens podem acessar serviços externos. Revisar políticas Mozilla vigentes antes da submissão.

## Proteção de banco
Nunca apague `data/dsi.db` no upgrade. Preserve `data/.dsi_access_token` para que o pareamento continue válido. Migrações anteriores são aditivas. Faça backup de todo `data` antes de instalar.
