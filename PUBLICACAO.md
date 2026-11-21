# Checklist de publicação Firefox + aplicativo local

Estado: **candidato técnico v1.0.0, ainda sem assinatura Mozilla e sem instalador Windows nativo**. Não enviar à loja sem testes reais e assinatura.

1. Faça backup de `data/dsi.db` e da pasta `data/backups` antes de atualizar.
2. Instale Python >= 3.10; execute `Instalar e iniciar DSI.bat` e verifique `http://127.0.0.1:8000/health`.
3. Abra o dashboard, vá a Configurações, clique em Copiar chave e cole-a no popup da extensão.
4. Teste listagem, scroll e coleta 40+40+restante; valide 24h de bloqueio e recaptura individual.
5. Teste Produtos, Organização em lote, Radar, Custos, Oportunidades, Mesa de Pesquisa, favoritos, Settings (backup, integridade, exportação e limpeza em banco descartável).
6. Teste saída e retorno do servidor; confirme mensagens de erro e restauração do pareamento.
7. Gere extensão: `npx web-ext lint --source-dir extension` e `npx web-ext build --source-dir extension --artifacts-dir dist`. Não inclua `data`, `.venv`, backups, logs ou chave de acesso.
8. Submeta o arquivo construído em https://addons.mozilla.org/developers/ para assinatura, após avaliar as políticas de dados e permissões vigentes. A conta e a assinatura Mozilla exigem ação do proprietário.
9. Publique instruções de instalação do aplicativo local, aviso de privacidade e licença. Verifique os termos do AliExpress quanto à coleta.

Limitações: Windows e Firefox reais não foram exercitados no ambiente de construção; pacote local em Python não é instalador nativo assinado.

## Requisitos que dependem do proprietário

- Registrar o nome, e-mail de suporte, marca e conta de desenvolvedor; reservar o identificador permanente da extensão antes da primeira submissão. O ID `dsi-local@example.invalid` é provisório para testes: substituí-lo por um ID controlado pelo publicador **antes da primeira assinatura** e mantê-lo em todas as futuras atualizações.
- Definir licença de distribuição do software e verificar licenças das dependências e direitos sobre ícones, marcas e descrições.
- Publicar aviso de privacidade coerente com `PRIVACIDADE.md`, e os termos de uso do serviço.
- Validar permissões e declaração `websiteContent` em Firefox 140+ e política Mozilla de 01/12/2026.
- Avaliar autorização e termos do AliExpress para a modalidade de coleta proposta.
- Testar o aplicativo em Windows 10 e 11 e Firefox estável, incluindo atualização sobre banco legado real (sempre com backup).

## Riscos residuais

- Qualquer programa com acesso à conta local pode ler a chave e o SQLite; não é um isolamento entre usuários do Windows.
- A v1.0 usa scripts `.bat` e requer Python. Não há instalador nativo nem binário assinado.
- A extração depende da estrutura HTML do AliExpress e requer testes com anúncios reais.
- O dashboard tradicional limita a exibição do catálogo a 500 itens por carregamento; a Mesa já usa paginação.
- A validação do navegador automatizado com servidor HTTP local é bloqueada neste ambiente; os testes API via TestClient foram executados.
