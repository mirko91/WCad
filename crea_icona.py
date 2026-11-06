"""Crea icona.png (1024 x 1024): una finestra a quattro vetri su fondo blu.
Lo esegue la compilazione automatica su GitHub; si può anche lanciare a mano:
    python crea_icona.py
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter

DIMENSIONE = 1024


def main():
    app = QGuiApplication([])  # necessario per il disegno con Qt

    img = QImage(DIMENSIONE, DIMENSIONE, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)

    # fondo arrotondato con sfumatura blu
    sfondo = QLinearGradient(0, 0, 0, DIMENSIONE)
    sfondo.setColorAt(0.0, QColor("#4d8dff"))
    sfondo.setColorAt(1.0, QColor("#1f5fd6"))
    p.setBrush(sfondo)
    p.drawRoundedRect(QRectF(0, 0, DIMENSIONE, DIMENSIONE), 220, 220)

    # telaio della finestra
    x, y, w, h = 280, 200, 464, 624
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(x, y, w, h), 24, 24)

    # quattro vetri separati da listelli
    margine, gap = 40, 28
    vw = (w - 2 * margine - gap) / 2
    vh = (h - 2 * margine - gap) / 2
    p.setBrush(QColor("#cfe8ff"))
    for i in range(2):
        for j in range(2):
            p.drawRect(QRectF(x + margine + i * (vw + gap),
                              y + margine + j * (vh + gap), vw, vh))
    p.end()

    img.save("icona.png")
    print("icona.png creata")


if __name__ == "__main__":
    main()
