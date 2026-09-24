"""Gera os ícones da extensão Chrome do Cofre (icon48.png / icon128.png).

O `chrome-extension/manifest.json` declara estes dois ficheiros; enquanto não
existirem, o Chrome assinala ícone em falta ao carregar a extensão
(«Load unpacked»). Ver `docs/guia-extensao-chrome.md`.

Uso (na raiz do projecto, com o venv activo):
    python scripts/gerar_icones_extensao.py

Requer Pillow (já nas dependências: pillow==10.4.0) e não precisa da app Flask.
"""
import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print('Pillow não está instalado. Corre: pip install -r requirements.txt')
    sys.exit(1)

# Pasta da extensão, relativa a este script (scripts/ -> ../chrome-extension)
DESTINO = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'chrome-extension')
)

AZUL = (67, 97, 238, 255)      # #4361ee — cor do popup
BRANCO = (255, 255, 255, 255)


def criar_icone(tamanho, destino):
    """Desenha um quadrado azul arredondado com um cadeado branco ao centro."""
    img = Image.new('RGBA', (tamanho, tamanho), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(img)

    # Fundo arredondado
    desenho.rounded_rectangle(
        [0, 0, tamanho - 1, tamanho - 1], radius=tamanho * 0.22, fill=AZUL
    )

    # Arco do cadeado (180 -> 360: meio arco, aberto em baixo)
    largura = max(2, int(tamanho * 0.10))
    desenho.arc(
        [tamanho * 0.32, tamanho * 0.20, tamanho * 0.68, tamanho * 0.60],
        start=180, end=360, fill=BRANCO, width=largura
    )

    # Corpo do cadeado
    desenho.rounded_rectangle(
        [tamanho * 0.24, tamanho * 0.44, tamanho * 0.76, tamanho * 0.82],
        radius=tamanho * 0.08, fill=BRANCO
    )

    img.save(destino)
    return destino


def main():
    if not os.path.isdir(DESTINO):
        print(f'Pasta da extensão não encontrada: {DESTINO}')
        sys.exit(1)

    for tamanho in (48, 128):
        caminho = criar_icone(tamanho, os.path.join(DESTINO, f'icon{tamanho}.png'))
        print(f'Criado: {caminho}')

    print('Ícones gerados. Recarrega a extensão em chrome://extensions (botão Recarregar).')


if __name__ == '__main__':
    main()
