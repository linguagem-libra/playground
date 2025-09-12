import subprocess
import threading
import os
import queue
import logging
import resource  # Apenas em Unix/Linux


class ProcessRunner:
    def __init__(
        self,
        command: list[str],
        input_q: queue.Queue | None = None,
        stdout_callback=None,
        stderr_callback=None,
        timeout: int = 10,
        memory_limit_mb: int = 256,
        output_limit_mb: float = 1.0,
        on_process_start=None
    ):
        self.command = command
        self.input_q = input_q
        self.stdout_callback = stdout_callback or (lambda line: None)
        self.stderr_callback = stderr_callback or (lambda line: None)
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.output_limit_bytes = int(output_limit_mb * 1024 * 1024)
        self.on_process_start = on_process_start

        self.process = None
        self._output_bytes = 0
        self._output_limit_exceeded = threading.Event()

    def _set_limits(self):
        """Define limites de recursos (apenas Unix/Linux)."""
        if os.name != "posix":
            return
        # Limite de memória
        if self.memory_limit_mb:
            mem_bytes = self.memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # Limite de CPU em segundos
        if self.timeout:
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout))

    def _reader(self, pipe, callback, name: str):
        for line in iter(pipe.readline, ''):
            if name == "stdout":
                if self._output_limit_exceeded.is_set():
                    break

                encoded_line = line.encode("utf-8")
                self._output_bytes += len(encoded_line)

                if self._output_bytes > self.output_limit_bytes:
                    self._output_limit_exceeded.set()
                    callback("Output size limit exceeded.")
                    self.kill()
                    break

            callback(line.rstrip())
        pipe.close()

    def _writer(self):
        if not self.input_q:
            return
        while self.process and self.process.poll() is None:
            try:
                line = self.input_q.get(timeout=1)
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.write(line + "\n")
                    self.process.stdin.flush()
            except queue.Empty:
                continue
            except (BrokenPipeError, OSError):
                logging.warning("Broken stdin pipe. Stopping writer.")
                break
        try:
            if self.process and self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    def run(self):
        """Inicia o processo e gerencia suas threads de I/O."""
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                preexec_fn=self._set_limits if os.name == "posix" else None,
            )

            logging.info(f"Process started with PID {self.process.pid}")

            if self.on_process_start:
                self.on_process_start(self.process)

            stdout_thread = threading.Thread(
                target=self._reader,
                args=(self.process.stdout, self.stdout_callback, "stdout"),
                name="stdout-reader",
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=self._reader,
                args=(self.process.stderr, self.stderr_callback, "stderr"),
                name="stderr-reader",
                daemon=True,
            )
            stdin_thread = threading.Thread(
                target=self._writer,
                name="stdin-writer",
                daemon=True,
            )

            stdout_thread.start()
            stderr_thread.start()
            stdin_thread.start()

            self.process.wait(timeout=self.timeout)
            return self.process.returncode

        except subprocess.TimeoutExpired:
            self.kill()
            self.stdout_callback("Time limit exceeded.")
            return -1

    def kill(self):
        if self.process and self.process.poll() is None:
            self.process.kill()
            logging.info("Process killed.")
