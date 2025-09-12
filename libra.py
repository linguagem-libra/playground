import os
import tempfile
import queue
import logging
from dotenv import load_dotenv
from process_runner import ProcessRunner
import threading

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s"
)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

LIBRA_PATH = os.getenv("LIBRA_PATH", "libra")


def execute_libra_script(
    script_content: str,
    line_callback=print,
    input_q: queue.Queue = None,
    on_process_start=None,
    timeout: int = 10,
    memory_limit_mb: int = 256,
    output_limit_mb: float = 0.25,
):
    logging.info("Iniciando execução do script Libra.")
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)

    temp_file_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".libra",
            dir=temp_dir,
            delete=False,
            mode="w",
            encoding="utf-8",
        ) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(script_content)

        logging.debug(f"Arquivo temporário criado em: {temp_file_path}")

        command = [LIBRA_PATH, temp_file_path]
        logging.debug(f"Comando a ser executado: {command}")

        runner = ProcessRunner(
            command=command,
            input_q=input_q,
            stdout_callback=line_callback,
            stderr_callback=lambda line: logging.error(f"PROCESSO LIBRA: {line}"),
            timeout=timeout,
            memory_limit_mb=memory_limit_mb,
            output_limit_mb=output_limit_mb,
            on_process_start=on_process_start,
        )

        runner.run()

    except Exception as e:
        logging.critical(f"Erro ao executar script Libra: {e}", exc_info=True)
        line_callback("Erro interno ao tentar executar o script.")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            logging.debug(f"Limpando arquivo temporário: {temp_file_path}")
            os.remove(temp_file_path)
