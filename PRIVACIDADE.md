# Privacidade — DSI v1.0.0

O DSI captura informações de anúncios do AliExpress **somente após ação do usuário**, nas páginas de produto ou listagens abertas no Firefox. Dados incluem título, URL, imagens, preço, moeda, avaliações, pedidos e informações públicas da loja, quando identificáveis.

As informações capturadas são enviadas **apenas ao serviço local** em `http://127.0.0.1:8000`, armazenadas no SQLite `data/dsi.db` e usadas para pesquisa e análises no próprio computador. Não existe conta de usuário, telemetria nem envio de seu catálogo a um servidor DSI.

A extensão armazena uma chave de acesso local no armazenamento do Firefox para pareamento. Evite compartilhar essa chave. Um programa com acesso à mesma conta do computador pode acessar os dados locais: a chave não protege contra software malicioso instalado no PC.

Consultas de taxa de câmbio e imagens externas podem realizar conexões de rede fora do localhost. Consulte o código de `backend/fx.py` e as URLs das imagens para os respectivos provedores; essas conexões não transmitem intencionalmente seu catálogo completo.

Você pode exportar os dados pelo dashboard, criar backups ou excluir os produtos em Configurações. A limpeza cria um backup antes da exclusão; backups antigos não são automaticamente apagados. Para remover todos os dados, exclua também backups e a pasta local, depois de encerrar o aplicativo.

Não contornamos controles de acesso, CAPTCHA ou bloqueios do AliExpress. A disponibilidade dos campos depende da página.
