# Atbswp
![Logo](./atbswp/img/icon.png)

Literalmente "Automate the boring stuff with Python": grava as ações de mouse e teclado e
reproduz tudo igual, quantas vezes você quiser.

Fork de [RMPR/atbswp](https://github.com/RMPR/atbswp) com reprodução mais rápida
(velocidade 1x/2x/3x/5x, pular movimentos do mouse, espera mínima) e o script `tools/acelerar.py`.

# Instalação

## Windows

Instale o Python 3 (https://www.python.org, marque "Add python.exe to PATH") e depois:

```shell
git clone https://github.com/guircamargo/atbswp.git
cd atbswp
py -m pip install wxPython pyautogui pynput
py atbswp\main.py
```

## Linux Mint (XFCE / X11, inclusive dentro do VirtualBox)

```shell
sudo apt install git python3-pip python3-tk python3-dev python3-xlib python3-wxgtk4.0
git clone https://github.com/guircamargo/atbswp.git
cd atbswp
python3 -m pip install --user --break-system-packages pyautogui pynput
python3 atbswp/main.py
```

- O `--break-system-packages` é necessário no Mint 22 e mais novos, onde o pip bloqueia instalar
  pacotes no Python do sistema. No Mint 21 o pip é antigo e não conhece essa opção: rode o mesmo
  comando sem ela.
- Só funciona em sessão **X11** (o padrão do XFCE). Wayland não é suportado.
- No VirtualBox, instale os *Guest Additions* e deixe a resolução da VM fixa entre a gravação e a
  reprodução: as posições do mouse são gravadas em pixels absolutos.

## Outras distribuições

Fedora
```shell
sudo dnf install python3-wxpython4 python3-xlib python3-tkinter
python3 -m pip install --user pyautogui pynput
python3 atbswp/main.py
```
Manjaro/Arch (também no [AUR](https://aur.archlinux.org/packages/atbswp/))
```shell
sudo pacman -S tk python-wxpython
python3 -m pip install --user pyautogui pynput
python3 atbswp/main.py
```

# Uso rápido

- **F9** inicia/para a gravação, **F10** reproduz (dá para mudar nas preferências, ⚙).
- O botão de salvar copia a gravação atual para um arquivo `.py`, e o de abrir carrega uma gravação salva.
- A gravação é um script Python comum: dá para rodar sozinha com `python gravacao.py`.

# Velocidade da reprodução

Por que ficava lento: o pyautogui espera `pyautogui.PAUSE` (0,1 s) **depois de cada chamada**.
Uma gravação com 500 movimentos de mouse ganhava 50 s a mais só com isso. Agora:

- **Gravações novas** já saem com `pyautogui.PAUSE = 0`. O tempo entre apertar e soltar um botão
  ou uma tecla também passa a ser gravado, então nada fica "colado".
- **Gravações antigas** continuam reproduzindo exatamente como antes em 1x.

No menu de preferências (⚙):

| Opção | O que faz |
|---|---|
| **Playback Speed → 1x / 2x / 3x / 5x / 10x / 20x / 50x / max** | Divide todos os `time.sleep` da gravação pelo fator. **max** remove todas as esperas gravadas: sobra só a espera mínima antes de cada clique ou tecla. |
| **Skip Mouse Moves** | Descarta os movimentos intermediários do mouse e mantém só a posição final antes de cada clique, tecla ou rolagem. As esperas desses movimentos são somadas, não perdidas (o tempo de carregar a página continua lá). |
| **Minimum Wait (ms)** | Espera mínima antes de cada clique, tecla ou rolagem (padrão 50 ms), para o navegador não perder cliques em velocidade alta. Não vale para movimentos do mouse. |

Notas:

- As opções são salvas na configuração do programa (`~/.config/atbswp.cfg` no Linux,
  `%APPDATA%\atbswp.cfg` no Windows) e só afetam a **reprodução**. O arquivo gravado não é alterado,
  e o botão de salvar continua salvando a gravação original.
- Em 1x, com "Skip Mouse Moves" desligado, a gravação roda sem nenhuma alteração. Com qualquer
  aceleração ligada, a pausa de 0,1 s do pyautogui também é removida e a espera mínima entra no lugar
  dela como proteção.
- Se o site perder cliques, aumente a espera mínima (100 a 200 ms) ou baixe a velocidade.
- A partir de uns 10x, quem manda no tempo é a espera mínima. Para ir mais rápido ainda, baixe
  ela (20 a 30 ms), sabendo que o navegador pode perder cliques. Em **max** a gravação também
  deixa de esperar o carregamento das páginas: use quando o macro não depende disso.

# Script `tools/acelerar.py`

Gera uma **cópia** acelerada de uma gravação que já existe. Serve, por exemplo, para rodar o
macro fora do atbswp com `python`. O original nunca é sobrescrito.

```shell
python tools/acelerar.py gravacao.py --velocidade 3 --sem-movimentos
# -> gravacao_3x_sem-movimentos.py
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--velocidade N` | 1 | Divide os `time.sleep` por N (ex.: 2, 10, 50, 2.5). `max` remove todas as esperas gravadas. |
| `--sem-movimentos` | desligado | Mantém só a posição final do mouse antes de cada clique/tecla. |
| `--espera-minima S` | 0.05 | Espera mínima, em segundos, antes de cada clique/tecla/rolagem. |
| `-o ARQUIVO`, `--saida ARQUIVO` | `<nome>_<N>x[_sem-movimentos].py` | Nome do arquivo gerado. |
| `--forcar` | desligado | Permite sobrescrever um arquivo de **saída** que já existe (o original, nunca). |

A cópia gerada sempre tem `pyautogui.PAUSE = 0`. Dá para abrir ela no atbswp ou rodar direto:

```shell
python gravacao_3x_sem-movimentos.py
```

No Linux, use `python3` no lugar de `python`.

# Testes

```shell
cd atbswp
python -m pip install pytest
python -m pytest tests/test_acelerar.py -v
```

Os testes de `test_acelerar.py` não precisam de tela nem do wxPython. O `tests/test_atbswp.py`
veio do projeto original e já estava quebrado: ele importa `atbswp.__version__`, que não existe.

# Demo

![atbswp quick demo](demo/demo.gif)

# Rolagem do mouse

O atbswp original gravava a rolagem como `pyautogui.scroll(<posição Y do mouse>)`, o que fazia
a página pular centenas de linhas. Agora cada dente da rodinha vira uma linha
`pyautogui.scroll(<quantidade>, x, y)`. No Windows a quantidade é multiplicada por 120, porque é
nessa unidade que o pyautogui trabalha lá. Por isso, uma gravação feita no Linux rola bem menos
no Windows e vice-versa. As posições do mouse também já não batem entre os dois sistemas, então
o ideal é gravar no mesmo sistema em que o macro vai rodar.

A rolagem horizontal só é gravada no Linux: no Windows o `pyautogui.hscroll` rola na vertical.
Gravações antigas não são corrigidas (o valor certo não foi salvo nelas), então grave de novo os
trechos com rolagem.

# Problemas conhecidos

No Linux só funciona com Xorg/X11. No GNOME com Wayland, desative o Wayland:

```
sudo sed 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm/custom.conf -i
```

# Créditos

Projeto original de Paul Mairo ([RMPR/atbswp](https://github.com/RMPR/atbswp)), licença GPL v3.
Contribuições: veja [CONTRIBUTING.md](./CONTRIBUTING.md).
