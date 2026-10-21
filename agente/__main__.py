import sys
from .sistema import montar_sistema


def main():
    sistema = montar_sistema()
    if len(sys.argv) > 1:                      # python -m agente "pergunta"
        print(sistema.resposta(" ".join(sys.argv[1:])))
        return
    print("Sistema pedagogico: padrao State.")  # modo conversa
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
