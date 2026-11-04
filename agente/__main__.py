import sys
from .sistema import montar_sistema


def _configurar_saida():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main():
    _configurar_saida()
    sistema = montar_sistema()
    if len(sys.argv) > 1:                      # python -m agente "pergunta"
        print(sistema.resposta(" ".join(sys.argv[1:])))
        return
    print("Sistema pedagogico: padrao State.")   # modo conversa
    print("Digite 'sair' para encerrar.")
    while True:
        try:
            pergunta = input("Voce: ")
        except (EOFError, KeyboardInterrupt):
            break
        if pergunta.strip().lower() == "sair":
            break
        print(f"Sistema: {sistema.resposta(pergunta)}")


if __name__ == "__main__":
    main()
