// Inicializa CodeMirror
const editor = CodeMirror.fromTextArea(document.getElementById('code'), {
    lineNumbers: true,
    mode: 'javascript',
    tabSize: 2,
    indentUnit: 2,
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
const stdinInput = document.getElementById('stdin-input');
const stdinSendButton = document.getElementById('stdin-send-button');
const MAX_LINES = 1000;
const outputLines = [];
const lineBuffer = [];
const STORAGE_KEY = 'libraPlaygroundCode';
let currentExecId = null;

// Carrega o código salvo ou o padrão ao iniciar
const savedCode = localStorage.getItem(STORAGE_KEY);
if (savedCode !== null) {
    editor.setValue(savedCode);
} else {
    editor.setValue('// Interpretador da Libra Online - Programe direto do navegador!\nexibir("Olá, Mundo!")');
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
    a.download = 'codigo.libra';
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

// Função para enviar input para o servidor
async function sendInput() {
    const text = stdinInput.value;
    if (text.trim() === '' || !currentExecId) return;

    try {
        await fetch('/input', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: currentExecId, text: text })
        });
        stdinInput.value = ''; // Limpa o campo após o envio
    } catch (error) {
        console.error('Erro ao enviar input:', error);
        lineBuffer.push("[Erro ao enviar input para o servidor]");
    }
}

stdinSendButton.onclick = sendInput;
stdinInput.onkeydown = (e) => {
    if (e.key === 'Enter') {
        sendInput();
    }
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
        currentExecId = data.id; // Salva o ID da execução atual

        if (window.eventSource) {
            window.eventSource.close();
        }

        // Habilita o campo de stdin
        stdinInput.disabled = false;
        stdinSendButton.disabled = false;
        stdinInput.focus();

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
            // Desabilita o campo de stdin
            stdinInput.disabled = true;
            stdinSendButton.disabled = true;
            currentExecId = null;
        };
    } catch (error) {
        output.textContent = 'Erro ao iniciar execução: ' + error;
        runButton.disabled = false;
    }
};

// Fonte inicial
let fontSize = parseInt(localStorage.getItem('libraFontSize')) || 16;
const outputBox = document.getElementById('output');

// Aplica o tamanho salvo
editor.getWrapperElement().style.fontSize = fontSize + "px";
outputBox.style.fontSize = fontSize + "px";
editor.refresh();

// Aumenta a fonte
document.getElementById('font-increase').onclick = () => {
    fontSize += 2;
    editor.getWrapperElement().style.fontSize = fontSize + "px";
    outputBox.style.fontSize = fontSize + "px";
    editor.refresh();
    localStorage.setItem('libraFontSize', fontSize);
};

// Diminui a fonte
document.getElementById('font-decrease').onclick = () => {
    if (fontSize > 8) {
        fontSize -= 2;
        editor.getWrapperElement().style.fontSize = fontSize + "px";
        outputBox.style.fontSize = fontSize + "px";
        editor.refresh();
        localStorage.setItem('libraFontSize', fontSize);
    }
};