# app.py

from flask import Flask, request, render_template, Response
from libra import execute_libra_script
import threading
import queue
import json
import uuid
import time

app = Flask(__name__)

# --- CONFIGURAÇÕES DE SEGURANÇA ---
MAX_CONCURRENT_EXECUTIONS = 10 
MAX_INPUT_QUEUE_SIZE = 50      
EXECUTION_TTL_SECONDS = 60     

executions = {}
executions_lock = threading.Lock()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    with executions_lock:
        if len(executions) >= MAX_CONCURRENT_EXECUTIONS:
            return {'error': 'Servidor ocupado, tente novamente mais tarde.'}, 503

        data = request.get_json()
        code = data.get('code', '')
        exec_id = str(uuid.uuid4())
        
        executions[exec_id] = {
            'code': code,
            'input_q': queue.Queue(maxsize=MAX_INPUT_QUEUE_SIZE),
            'output_q': queue.Queue(),
            'created_at': time.time(),
            'process': None # Para armazenar o objeto do processo
        }
        return {'id': exec_id}

@app.route('/input', methods=['POST'])
def handle_input():
    data = request.get_json()
    exec_id = data.get('id')
    text = data.get('text', '')
    
    execution = executions.get(exec_id)
    if execution:
        try:
            execution['input_q'].put_nowait(text)
            return {'status': 'ok'}
        except queue.Full:
            return {'status': 'error', 'message': 'Fila de entrada cheia.'}, 429
    return {'status': 'error', 'message': 'Execução não encontrada'}, 404

@app.route('/stream')
def stream():
    exec_id = request.args.get('id')
    
    with executions_lock:
        execution = executions.get(exec_id)
        if not execution:
            return Response("ID de execução inválido ou expirado.", status=404)
        
        if 'created_at' in execution:
            del execution['created_at']
    
    code = execution['code']
    input_q = execution['input_q']
    output_q = execution['output_q']

    return Response(libra_output_stream(code, input_q, output_q, exec_id), mimetype='text/event-stream')

def libra_output_stream(code, input_q, output_q, exec_id):
    def run():
        def on_line(line):
            output_q.put(line)

        def on_process_start(p):
            with executions_lock:
                if exec_id in executions:
                    executions[exec_id]['process'] = p

        # Passa o novo callback para a função de execução
        execute_libra_script(
            code, 
            on_line, 
            input_q=input_q, 
            on_process_start=on_process_start,
            memory_limit_mb=2048 # Aumenta o limite de memória
        )
        output_q.put(None)

    threading.Thread(target=run).start()

    try:
        while True:
            line = output_q.get()
            if line is None:
                break
            safe_line = json.dumps(line.strip(), ensure_ascii=False)
            yield f"data: {safe_line}\n\n"
    finally:
        # Este bloco é EXECUTADO SEMPRE, incluindo quando o cliente desconecta.
        with executions_lock:
            if exec_id in executions:
                execution = executions[exec_id]
                process = execution.get('process')
                # Se o processo existe e ainda está rodando, finaliza-o.
                if process and process.poll() is None:
                    process.kill()
                
                # Limpa a execução do dicionário
                del executions[exec_id]

def cleanup_stale_executions():
    """Limpa execuções que foram iniciadas mas nunca usadas."""
    while True:
        time.sleep(EXECUTION_TTL_SECONDS)
        with executions_lock:
            now = time.time()
            stale_ids = [
                exec_id for exec_id, data in executions.items()
                if 'created_at' in data and (now - data['created_at']) > EXECUTION_TTL_SECONDS
            ]
            for exec_id in stale_ids:
                del executions[exec_id]

if __name__ == '__main__':
    cleanup_thread = threading.Thread(target=cleanup_stale_executions, daemon=True)
    cleanup_thread.start()
    app.run(debug=True)