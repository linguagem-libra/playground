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
    executions[exec_id] = code
    return {'id': exec_id}

@app.route('/stream')
def stream():
    exec_id = request.args.get('id')
    code = executions.pop(exec_id, '')
    return Response(libra_output_stream(code), mimetype='text/event-stream')

def libra_output_stream(code):
    q = queue.Queue()
    def run():
        def on_line(line):
            q.put(line)
        execute_libra_script(code, on_line)
        q.put(None)
    threading.Thread(target=run).start()

    while True:
        line = q.get()
        if line is None:
            break
        # Escapar corretamente para SSE
        safe_line = json.dumps(line.strip(), ensure_ascii=False)
        yield f"data: {safe_line}\n\n"

if __name__ == '__main__':
    app.run(debug=True)
