// Inicializa CodeMirror
const editor = CodeMirror.fromTextArea(document.getElementById('code'), {
    lineNumbers: true,
    mode: 'javascript',
    tabSize: 4,
    indentUnit: 4,
    extraKeys: {
        Tab: (cm) => {
            if (cm.somethingSelected()) {
                cm.indentSelection("add");
            } else {
                cm.replaceSelection("\t");
            }
        }
    }
});

const runButton = document.getElementById('run-button');
const openButton = document.getElementById('open-button');
const downloadButton = document.getElementById('download-button');
const clearButton = document.getElementById('clear-button');
const fileInput = document.getElementById('file-input');
const output = document.getElementById('output');
const MAX_LINES = 1000;
const outputLines = [];
const lineBuffer = [];
const STORAGE_KEY = 'libraPlaygroundCode';

// Carrega o código salvo ou o padrão ao iniciar
const savedCode = localStorage.getItem(STORAGE_KEY);
if (savedCode !== null) {
    editor.setValue(savedCode);
} else {
    editor.setValue('exibir("Olá, Mundo!")');
}

// Garante que o estado do botão "Executar" esteja correto no carregamento
runButton.disabled = editor.getValue().trim().length === 0;

// Lógica dos Botões
openButton.onclick = () => {
    fileInput.click();
};

fileInput.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
        editor.setValue(event.target.result);
    };
    reader.readAsText(file);
    e.target.value = '';
};

downloadButton.onclick = () => {
    const code = editor.getValue();
    const blob = new Blob([code], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'script.libra';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
};

clearButton.onclick = () => {
    editor.setValue('');
    output.textContent = '';
    outputLines.length = 0;
    lineBuffer.length = 0;
};

// Atualiza DOM a cada 50ms
setInterval(() => {
    if (lineBuffer.length > 0) {
        outputLines.push(...lineBuffer.splice(0));
        if (outputLines.length > MAX_LINES) {
            outputLines.splice(0, outputLines.length - MAX_LINES);
        }
        output.textContent = outputLines.join('\n');
        output.scrollTop = output.scrollHeight;
    }
}, 50);

// Salva o código no localStorage e atualiza o estado do botão a cada mudança
editor.on('change', () => {
    const code = editor.getValue();
    runButton.disabled = code.trim().length === 0;
    localStorage.setItem(STORAGE_KEY, code);
});

runButton.onclick = async function () {
    output.textContent = '';
    outputLines.length = 0;
    lineBuffer.length = 0;
    runButton.disabled = true;

    const code = editor.getValue();

    try {
        const res = await fetch('/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });

        const data = await res.json();

        if (window.eventSource) {
            window.eventSource.close();
        }

        window.eventSource = new EventSource('/stream?id=' + data.id);
        window.eventSource.onmessage = function (e) {
            try {
                const parsed = JSON.parse(e.data);
                lineBuffer.push(parsed);
            } catch (err) {
                lineBuffer.push("[Erro ao processar linha do servidor]");
            }
        };

        window.eventSource.onerror = function () {
            window.eventSource.close();
            runButton.disabled = false;
        };
    } catch (error) {
        output.textContent = 'Erro ao iniciar execução: ' + error;
        runButton.disabled = false;
    }
};