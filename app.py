# app.py

from flask import Flask, request, render_template, Response
from libra import execute_libra_script
import threading
import queue
import json

app = Flask(__name__)

import uuid

executions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json()
    code = data.get('code', '')
    exec_id = str(uuid.uuid4())
    # Prepara as filas para a nova execução
    executions[exec_id] = {
        'code': code,
        'input_q': queue.Queue(),
        'output_q': queue.Queue()
    }
    return {'id': exec_id}

@app.route('/input', methods=['POST'])
def handle_input():
    data = request.get_json()
    exec_id = data.get('id')
    text = data.get('text', '')
    
    execution = executions.get(exec_id)
    if execution:
        execution['input_q'].put(text)
        return {'status': 'ok'}
    return {'status': 'error', 'message': 'Execução não encontrada'}, 404

@app.route('/stream')
def stream():
    exec_id = request.args.get('id')
    execution = executions.get(exec_id)
    if not execution:
        return Response("ID de execução inválido ou expirado.", status=404)
        
    code = execution['code']
    input_q = execution['input_q']
    output_q = execution['output_q']

    return Response(libra_output_stream(code, input_q, output_q, exec_id), mimetype='text/event-stream')

def libra_output_stream(code, input_q, output_q, exec_id):
    def run():
        def on_line(line):
            output_q.put(line)
        # Passa a fila de input para a função de execução
        execute_libra_script(code, on_line, input_q=input_q)
        output_q.put(None) # Sinaliza o fim do output

    threading.Thread(target=run).start()

    while True:
        line = output_q.get()
        if line is None:
            break
        # Escapar corretamente para SSE
        safe_line = json.dumps(line.strip(), ensure_ascii=False)
        yield f"data: {safe_line}\n\n"

    # Limpa a execução do dicionário após o término
    if exec_id in executions:
        del executions[exec_id]

if __name__ == '__main__':
    app.run(debug=True)
