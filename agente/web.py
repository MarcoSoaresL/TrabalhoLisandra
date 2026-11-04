import argparse
import json
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config
from .grafo import AGENTE_POR_INTENCAO, montar_grafo
from .sistema import Sistema

PAGINA = Path(__file__).parent / "static" / "index.html"
MAX_SESSOES = 50

NOME_AGENTE = {
    "tutor": "Tutor do conceito",
    "exemplificador": "Exemplificador",
    "inquiridor": "Inquiridor",
}
NOME_RECUSA = {
    "padrao_inventado": "Guardião · recusa",
    "fora_escopo": "Fora de escopo",
}


def nome_do_agente(intencao):
    if intencao in AGENTE_POR_INTENCAO:
        return NOME_AGENTE[AGENTE_POR_INTENCAO[intencao]]
    return NOME_RECUSA.get(intencao)


class Sessoes:
    def __init__(self, criar_sistema):
        self.criar_sistema = criar_sistema
        self.sessoes = {}
        self.trava = threading.Lock()

    def obter(self, sessao_id):
        with self.trava:
            if sessao_id not in self.sessoes:
                if len(self.sessoes) >= MAX_SESSOES:  # descarta a mais antiga
                    self.sessoes.pop(next(iter(self.sessoes)))
                self.sessoes[sessao_id] = self.criar_sistema()
            return self.sessoes[sessao_id]

    def encerrar(self, sessao_id):
        with self.trava:
            self.sessoes.pop(sessao_id, None)


def criar_servidor(criar_sistema, porta=8000):
    sessoes = Sessoes(criar_sistema)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silencia o log de cada requisicao
            pass

        def _responder(self, status, corpo, tipo="application/json; charset=utf-8"):
            dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(dados)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(dados)

        def _ler_json(self):
            tamanho = int(self.headers.get("Content-Length") or 0)
            bruto = self.rfile.read(tamanho) or b"{}"
            try:
                texto = bruto.decode("utf-8")
            except UnicodeDecodeError:
                texto = bruto.decode("cp1252", errors="replace")  # clientes de terminal no Windows
            try:
                return json.loads(texto)
            except ValueError:
                return None

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/info":
                self._responder(200, {"padrao": config.PADRAO, "modelo": config.MODELO})
            else:
                self._responder(404, {"erro": "nao encontrado"})

        def do_POST(self):
            dados = self._ler_json()
            if not isinstance(dados, dict):
                return self._responder(400, {"erro": "JSON invalido"})
            sessao_id = str(dados.get("sessao") or "")
            if self.path == "/api/mensagem":
                if not sessao_id:
                    return self._responder(400, {"erro": "sessao ausente"})
                inicio = time.time()
                resultado = sessoes.obter(sessao_id).responder(str(dados.get("texto") or ""))
                self._responder(200, {**resultado, "agente": nome_do_agente(resultado["intencao"]),
                                      "segundos": round(time.time() - inicio, 1)})
            elif self.path == "/api/nova":
                sessoes.encerrar(sessao_id)
                self._responder(200, {"sessao": str(uuid.uuid4())})
            else:
                self._responder(404, {"erro": "nao encontrado"})

    return ThreadingHTTPServer(("127.0.0.1", porta), Handler)


def main():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Interface web do tutor do padrao State")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--sem-navegador", action="store_true", help="nao abre o navegador automaticamente")
    args = parser.parse_args()

    from .llm import get_llm
    grafo = montar_grafo(get_llm())  # memoria separada por thread_id
    try:
        servidor = criar_servidor(lambda: Sistema(grafo), args.porta)
    except OSError:
        sys.exit(f"A porta {args.porta} esta ocupada. Tente: python -m agente.web --porta {args.porta + 1}")

    url = f"http://localhost:{args.porta}"
    print(f"Tutor do padrao {config.PADRAO} rodando em {url}  (modelo local: {config.MODELO})")
    print("Ctrl+C para encerrar.")
    if not args.sem_navegador:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
