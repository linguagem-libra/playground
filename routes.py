from flask import request, Response
from execution_manager import start_execution, add_input, get_execution
from streaming import libra_output_stream

def register_routes(app):
    @app.route('/start', methods=['POST'])
    def start():
        return start_execution(request.get_json())

    @app.route('/input', methods=['POST'])
    def handle_input():
        data = request.get_json()
        return add_input(data)

    @app.route('/stream')
    def stream():
        exec_id = request.args.get('id')
        execution = get_execution(exec_id)
        if not execution:
            return Response("ID de execução inválido ou expirado.", status=404)

        code = execution['code']
        input_q = execution['input_q']
        output_q = execution['output_q']
        return Response(libra_output_stream(code, input_q, output_q, exec_id), mimetype='text/event-stream')
