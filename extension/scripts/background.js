// Ponto de entrada reservado para tarefas em segundo plano.
// A captura inicial é acionada pelo popup e executada pelo content script.
browser.runtime.onInstalled.addListener(() => {
  console.info("DSI instalado.");
});