#!/usr/bin/env python3
"""Gera uma cópia acelerada de um arquivo de captura do atbswp.

Exemplo:
    python tools/acelerar.py gravacao.py --velocidade 3 --sem-movimentos

O arquivo original nunca é alterado.
"""
import argparse
import locale
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "atbswp"))

import speedup  # noqa: E402


def nome_saida(entrada, velocidade, sem_movimentos):
    """gravacao.py -> gravacao_3x_sem-movimentos.py"""
    base, ext = os.path.splitext(entrada)
    sufixo = "_" + speedup.speed_label(velocidade)
    if sem_movimentos:
        sufixo += "_sem-movimentos"
    return base + sufixo + (ext or ".py")


def ler(caminho):
    """Retorna (linhas, encoding). O atbswp grava no encoding padrão do sistema."""
    with open(caminho, "rb") as f:
        dados = f.read()
    try:
        return dados.decode("utf-8").splitlines(), "utf-8"
    except UnicodeDecodeError:
        encoding = locale.getpreferredencoding(False)
        return dados.decode(encoding).splitlines(), encoding


def positivo(valor):
    if valor.lower() in ("max", "maximo", "máximo"):
        return speedup.MAX_SPEED
    numero = float(valor)
    if numero <= 0:
        raise argparse.ArgumentTypeError("precisa ser maior que 0")
    return numero


def nao_negativo(valor):
    numero = float(valor)
    if numero < 0:
        raise argparse.ArgumentTypeError("não pode ser negativo")
    return numero


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Gera uma cópia acelerada de uma captura do atbswp (o original não é alterado).")
    parser.add_argument("arquivo", help="arquivo de captura existente")
    parser.add_argument("--velocidade", type=positivo, default=1.0,
                        help="divide os time.sleep por este fator (ex.: 2, 10, 50) ou 'max' para "
                             "remover todas as esperas gravadas (fica só a espera mínima). Padrão: 1")
    parser.add_argument("--sem-movimentos", action="store_true",
                        help="mantém só a posição final do mouse antes de cada clique/tecla")
    parser.add_argument("--espera-minima", type=nao_negativo, default=speedup.DEFAULT_MIN_WAIT,
                        help=f"espera mínima em segundos antes de cada clique/tecla. Padrão: {speedup.DEFAULT_MIN_WAIT}")
    parser.add_argument("-o", "--saida",
                        help="arquivo gerado. Padrão: <arquivo>_<velocidade>x[_sem-movimentos].py")
    parser.add_argument("--forcar", action="store_true",
                        help="permite sobrescrever um arquivo de saída que já existe (nunca o original)")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.arquivo):
        parser.error(f"arquivo não encontrado: {args.arquivo}")

    saida = args.saida or nome_saida(args.arquivo, args.velocidade, args.sem_movimentos)
    if os.path.exists(saida) and os.path.samefile(saida, args.arquivo):
        parser.error("a saída não pode ser o próprio arquivo original")
    if os.path.exists(saida) and not args.forcar:
        parser.error(f"{saida} já existe (use --forcar para sobrescrever)")

    linhas, encoding = ler(args.arquivo)
    novas = speedup.transform(linhas, args.velocidade, args.sem_movimentos, args.espera_minima)
    with open(saida, "w", encoding=encoding) as f:
        f.write("\n".join(novas) + "\n")

    print(f"{len(linhas)} linhas -> {len(novas)} linhas: {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
