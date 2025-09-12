import json
import threading
from execution_manager import executions, executions_lock
from libra import execute_libra_script

def libra_output_stream(code, input_q, output_q, exec_id):
    def run():
        def on_line(line):
            output_q.put(line)

        def on_process_start(p):
            with executions_lock:
                if exec_id in executions:
                    executions[exec_id]['process'] = p

        execute_libra_script(
            code,
            on_line,
            input_q=input_q,
            on_process_start=on_process_start,
            memory_limit_mb=2048
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
        with executions_lock:
            if exec_id in executions:
                execution = executions[exec_id]
                process = execution.get('process')
                if process and process.poll() is None:
                    process.kill()
                del executions[exec_id]
