# libra.py

import subprocess
import tempfile
import os
import threading
import resource  # Apenas em Unix/Linux
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

LIBRA_PATH = os.getenv('LIBRA_PATH', 'libra')

def execute_libra_script(
    script_content: str,
    line_callback=print,
    timeout: int = 3,
    memory_limit_mb: int = 2048,
    output_limit_mb: int = 0.25
):
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".libra", dir=temp_dir, delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(script_content.encode())

    command = [LIBRA_PATH, temp_file_path]

    # Convert MB to bytes
    output_limit_bytes = output_limit_mb * 1024 * 1024
    total_output_bytes = 0
    output_limit_exceeded = threading.Event()

    def set_memory_limit():
        soft, hard = memory_limit_mb * 1024 * 1024, memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (soft, hard))  # Address space (virtual memory)

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=set_memory_limit  # Apenas em Unix
        )

        def reader():
            nonlocal total_output_bytes
            for line in process.stdout:
                if output_limit_exceeded.is_set():
                    break
                line = line.rstrip()
                encoded_line = line.encode('utf-8')
                total_output_bytes += len(encoded_line)
                if total_output_bytes > output_limit_bytes:
                    output_limit_exceeded.set()
                    line_callback("Limite de tamanho de output excedido.")
                    process.kill()
                    break
                line_callback(line)

        thread = threading.Thread(target=reader)
        thread.start()

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            line_callback("Limite de tempo excedido.")
        thread.join()

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
