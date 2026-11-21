# DSI v0.16 — Instalação e diagnóstico (Windows)

## Primeira execução

1. Instale **Python 3.10+** no Windows e habilite sua execução por terminal (ou `py`). A internet é necessária apenas para instalar bibliotecas pela primeira vez.
2. Extraia o ZIP em uma pasta permanente, sem colocar arquivos dentro da pasta de outra instalação do DSI antes de fazer backup.
3. Preserve a pasta `data/` da instalação anterior, principalmente `data/dsi.db`. **Não copie nem substitua o banco por um arquivo vazio.**
4. Execute **Instalar e iniciar DSI.bat**. Ele cria `.venv/` e instala bibliotecas em ambiente separado antes de iniciar a API local. O arquivo `.venv/` não é distribuído.
5. O dashboard abrirá em `http://127.0.0.1:8000/dashboard`. Mantenha a janela do iniciador aberta enquanto usar o DSI.
6. No Firefox, abra `about:debugging#/runtime/this-firefox`, clique em **Carregar extensão temporária** e escolha `extension/manifest.json`. Recarregue a aba do AliExpress. Complementos temporários podem precisar ser carregados após reiniciar o Firefox.

## Próximas vezes

Use **Iniciar DSI.bat**. Se a API já estiver ativa, o iniciador abre o dashboard sem criar um segundo servidor.

## Se falhar

- **Python não encontrado:** instale Python 3.10+ e repita a operação.
- **Dependências ausentes:** use **Instalar e iniciar DSI.bat**, que instala no `.venv/` local. Também pode usar `python launcher.py --check`.
- **Porta 8000 ocupada:** encerre o outro aplicativo que estiver usando a porta. O DSI não interrompe processos de terceiros.
- **Extensão desconectada:** execute **Diagnosticar DSI.bat**; abra `http://127.0.0.1:8000/health`. Recarregue a extensão no Firefox e confira se a API está aberta.
- **Erro no banco:** preserve `data/dsi.db` e `data/backups/`. Não apague o banco para tentar resolver problemas. Gere backup e procure o erro exibido no terminal.

## Limitações da pré-publicação

A v0.16 é um pacote local **para desenvolvimento/testes**, não um instalador nativo assinado. Ainda requer Python e instalação inicial de dependências. A API responde em `127.0.0.1` e não deve ser exposta à rede ou à internet. A proteção de endpoints locais contra origens indevidas e o empacotamento/assinatura AMO continuam para a auditoria de segurança da v0.17.
