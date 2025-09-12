import threading
import queue
import time
import uuid

MAX_CONCURRENT_EXECUTIONS = 10
MAX_INPUT_QUEUE_SIZE = 50
EXECUTION_TTL_SECONDS = 60

executions = {}
executions_lock = threading.Lock()

def start_execution(data):
    with executions_lock:
        if len(executions) >= MAX_CONCURRENT_EXECUTIONS:
            return {'error': 'Servidor ocupado, tente novamente mais tarde.'}, 503

        code = data.get('code', '')
        exec_id = str(uuid.uuid4())
        executions[exec_id] = {
            'code': code,
            'input_q': queue.Queue(maxsize=MAX_INPUT_QUEUE_SIZE),
            'output_q': queue.Queue(),
            'created_at': time.time(),
            'process': None
        }
        return {'id': exec_id}

def add_input(data):
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

def get_execution(exec_id):
    with executions_lock:
        execution = executions.get(exec_id)
        if not execution:
            return None
        if 'created_at' in execution:
            del execution['created_at']
        return execution

def cleanup_stale_executions():
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

cleanup_thread = threading.Thread(target=cleanup_stale_executions, daemon=True)
cleanup_thread.start()
