# libra.py

import subprocess
import tempfile
import os
import threading
import resource  # Apenas em Unix/Linux
import queue
import logging
from dotenv import load_dotenv

# Configuração básica de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

LIBRA_PATH = os.getenv('LIBRA_PATH', 'libra')

def execute_libra_script(
    script_content: str,
    line_callback=print,
    input_q: queue.Queue = None,
    on_process_start=None,
    timeout: int = 10,
    memory_limit_mb: int = 256,
    output_limit_mb: int = 0.25
):
    logging.info("Iniciando execução do script Libra.")
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_file_path = ""
    output_thread = None
    error_thread = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".libra", dir=temp_dir, delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(script_content)
        
        logging.debug(f"Arquivo temporário criado em: {temp_file_path}")

        command = [LIBRA_PATH, temp_file_path]
        logging.debug(f"Comando a ser executado: {command}")

        output_limit_bytes = output_limit_mb * 1024 * 1024
        total_output_bytes = 0
        output_limit_exceeded = threading.Event()

        # Adiciona a variável de ambiente para desativar diagnósticos do CoreCLR
        proc_env = os.environ.copy()
        proc_env["COMPlus_EnableDiagnostics"] = "0"
        logging.debug(f"Variáveis de ambiente do processo definidas: {proc_env.get('COMPlus_EnableDiagnostics')}")

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # Captura o stderr separadamente
            text=True,
            encoding='utf-8',
            # preexec_fn=set_limits, # Removido para diagnóstico
            env=proc_env
        )
        
        logging.info(f"Processo Libra iniciado com PID: {process.pid}")

        if on_process_start:
            on_process_start(process)

        def reader(pipe, callback, name):
            nonlocal total_output_bytes
            for line in iter(pipe.readline, ''):
                if name == "stdout":
                    if output_limit_exceeded.is_set():
                        break
                    
                    encoded_line = line.encode('utf-8')
                    total_output_bytes += len(encoded_line)
                    
                    if total_output_bytes > output_limit_bytes:
                        output_limit_exceeded.set()
                        callback("Limite de tamanho de output excedido.")
                        process.kill()
                        break
                
                callback(line.rstrip())
            pipe.close()

        def writer():
            if not input_q:
                return
            while process.poll() is None:
                try:
                    line = input_q.get(timeout=1)
                    if process.stdin and not process.stdin.closed:
                        process.stdin.write(line + '\n')
                        process.stdin.flush()
                except queue.Empty:
                    continue
                except (BrokenPipeError, OSError):
                    logging.warning("Pipe de stdin quebrado. Encerrando writer.")
                    break
            
            try:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            
        # Thread para stdout
        output_thread = threading.Thread(target=reader, args=(process.stdout, line_callback, "stdout"), name="stdout-reader")
        
        # Thread para stderr
        error_thread = threading.Thread(target=reader, args=(process.stderr, lambda line: logging.error(f"PROCESSO LIBRA: {line}"), "stderr"), name="stderr-reader")

        input_thread = threading.Thread(target=writer, name="stdin-writer", daemon=True)

        output_thread.start()
        error_thread.start()
        input_thread.start()

        process.wait(timeout=timeout)
        logging.info(f"Processo finalizado com código de saída: {process.returncode}")

    except subprocess.TimeoutExpired:
        process.kill()
        logging.warning("Processo excedeu o limite de tempo e foi finalizado.")
        line_callback("Limite de tempo excedido.")
    except Exception as e:
        logging.critical(f"Erro inesperado ao executar o script: {e}", exc_info=True)
        line_callback(f"Erro interno do servidor ao tentar executar o script.")
    finally:
        if output_thread and output_thread.is_alive():
            output_thread.join()
        if error_thread and error_thread.is_alive():
            error_thread.join()
        if os.path.exists(temp_file_path):
            logging.debug(f"Limpando arquivo temporário: {temp_file_path}")
            os.remove(temp_file_path)