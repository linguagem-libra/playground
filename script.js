function executar() {
  const codigo = document.getElementById('entrada').value;
  const saida = document.getElementById('saida');

  saida.textContent = 'Executando...';

  fetch('https://lucasof.com:5103/executar', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ codigo })
  })
    .then(res => res.text())
    .then(texto => {
      const textoEscapado = texto
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

      saida.innerHTML = textoEscapado;
      Prism.highlightElement(saida);
    })
    .catch(err => {
      saida.textContent = "Erro na requisição: " + err.message;
    });
}

// Quando apertar TAB dentro do textarea, insere 4 espaços
document.getElementById('entrada').addEventListener('keydown', function(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    const textarea = this;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    // Inserir 4 espaços
    const spaces = '    ';
    textarea.value = textarea.value.substring(0, start) + spaces + textarea.value.substring(end);

    // Mover o cursor
    textarea.selectionStart = textarea.selectionEnd = start + spaces.length;
  }
});
