"""Disegno realistico delle finestre con QPainter, anteprima ed esportazione JPG/PDF.
Tutte le coordinate sono in millimetri.

Una geometria è una tupla (x, y, w, h, forma, ah):
ah è l'altezza della parte ad arco (solo per le forme ad arco)."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QColor, QFont, QImage, QPdfWriter, QPageSize, QPageLayout,
    QPainterPath, QLinearGradient, QBrush, QPolygonF,
)
from PySide6.QtWidgets import QWidget

from modelli import TIPI, Elemento, Profilo

MARGINE_QUOTE = 560      # mm di spazio attorno al disegno quando ci sono le quote
MARGINE_QUOTE_BASE = 320  # mm attorno al disegno con le quote, senza sopraluce
MARGINE_NUDO = 30        # mm di spazio quando le quote sono escluse
FERMAVETRO = 14.0        # larghezza del fermavetro (mm)
OMBRA = 10.0             # spostamento dell'ombra del serramento (mm)
NERO = QColor("#222222")
ROSSO = QColor("#cc0000")


def _pen(colore, larghezza, tratteggio=False):
    pen = QPen(colore, larghezza)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    if tratteggio:
        pen.setStyle(Qt.PenStyle.DashLine)
    return pen


def _pen_arrotondato(colore, larghezza):
    pen = QPen(colore, larghezza)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


# ---------------------------------------------------------------------------
# Geometrie
# ---------------------------------------------------------------------------
def _ah_arco(forma, w):
    if forma == "arco_tondo":
        return w / 2
    if forma == "arco_ribassato":
        return w * 0.3
    return 0.0


def _ins(g, s):
    """Geometria rimpicciolita di s mm su ogni lato."""
    x, y, w, h, f, ah = g
    return (x + s, y + s, max(w - 2 * s, 1.0), max(h - 2 * s, 1.0), f,
            max(ah - s, 0.0) if ah else 0.0)


def _path(g) -> QPainterPath:
    x, y, w, h, f, ah = g
    p = QPainterPath()
    if f == "tondo":
        d = min(w, h)
        p.addEllipse(QRectF(x + (w - d) / 2, y + (h - d) / 2, d, d))
    elif f in ("arco_tondo", "arco_ribassato") and ah > 0:
        ah = min(ah, h * 0.95)
        p.moveTo(x, y + h)
        p.lineTo(x, y + ah)
        p.arcTo(QRectF(x, y, w, 2 * ah), 180, -180)
        p.lineTo(x + w, y + h)
        p.closeSubpath()
    else:
        p.addRect(QRectF(x, y, w, h))
    return p


# ---------------------------------------------------------------------------
# Materiali: telaio, metallo, vetro
# ---------------------------------------------------------------------------
def _riempi_telaio(p, path, colore, spessore=1.3):
    """Riempimento con sfumatura da chiaro a scuro, per dare volume al profilo."""
    r = path.boundingRect()
    grad = QLinearGradient(r.topLeft(), r.bottomRight())
    grad.setColorAt(0.0, colore.lighter(120))
    grad.setColorAt(0.5, colore)
    grad.setColorAt(1.0, colore.darker(115))
    p.setPen(_pen(NERO, spessore))
    p.setBrush(QBrush(grad))
    p.drawPath(path)


def _telaio(p, g, colore):
    """Profilo di telaio o anta, con bordo di luce interno."""
    _riempi_telaio(p, _path(g), colore)
    p.setPen(QPen(colore.lighter(140), 2.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(_path(_ins(g, 7)))


def _metallo(p, x, y, w, h, colore):
    _riempi_telaio(p, _path((x, y, w, h, "rettangolare", 0)), colore, 1.0)


def _riempi_vetro(p, path, vetro):
    """Vetro con sfumatura verticale e riflesso diagonale."""
    r = path.boundingRect()
    grad = QLinearGradient(r.topLeft(), r.bottomLeft())
    grad.setColorAt(0.0, vetro.lighter(115))
    grad.setColorAt(1.0, vetro.darker(106))
    p.save()
    p.setClipPath(path)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawPath(path)
    w, h, x0, y0 = r.width(), r.height(), r.left(), r.top()
    riflesso = QPolygonF([
        QPointF(x0 + 0.12 * w, y0 + h),
        QPointF(x0 + 0.42 * w, y0),
        QPointF(x0 + 0.55 * w, y0),
        QPointF(x0 + 0.25 * w, y0 + h),
    ])
    p.setBrush(QColor(255, 255, 255, 60))
    p.drawPolygon(riflesso)
    p.restore()
    p.setPen(_pen(NERO, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)


def _pannello(p, g, telaio, vetro, fermavetri):
    """Una specchiatura di vetro, con fermavetri opzionale."""
    if fermavetri:
        _riempi_telaio(p, _path(g), telaio, 1.0)
        _riempi_vetro(p, _path(_ins(g, FERMAVETRO)), vetro)
    else:
        _riempi_vetro(p, _path(g), vetro)


def _vetrata(p, e: Elemento, g, telaio, vetro):
    """Zona vetrata di un'anta: vetro singolo o diviso da listelli, con zoccolo in porta."""
    x, y, w, h, f, ah = g
    zoccolo = e.tipo == "porta" and e.zoccolo and f == "rettangolare"
    vh = h
    if zoccolo:
        zh = min(max(e.altezza_zoccolo, 100), max(h - 200, 100), h)
        vh = h - zh
        _telaio(p, (x, y + vh, w, zh, "rettangolare", 0), telaio)

    gv = (x, y, w, vh, f, ah)
    if e.tipo == "porta" and e.vetro_porta == "multiplo" and f == "rettangolare" and vh > 0:
        nc = max(1, e.divisioni_colonne)
        nr = max(1, e.divisioni_righe)
        L = e.larghezza_listello
        # il fondo è del colore del telaio: si vedono solo i listelli tra le specchiature
        _riempi_telaio(p, _path(gv), telaio, 1.0)
        cw, ch = w / nc, vh / nr
        for i in range(nc):
            for j in range(nr):
                sx = L / 2 if i > 0 else 0.0
                dx = L / 2 if i < nc - 1 else 0.0
                sy = L / 2 if j > 0 else 0.0
                dy = L / 2 if j < nr - 1 else 0.0
                cella = (x + i * cw + sx, y + j * ch + sy,
                         max(cw - sx - dx, 1.0), max(ch - sy - dy, 1.0),
                         "rettangolare", 0)
                _pannello(p, cella, telaio, vetro, e.fermavetri)
    else:
        _pannello(p, gv, telaio, vetro, e.fermavetri)


# ---------------------------------------------------------------------------
# Ferramenta
# ---------------------------------------------------------------------------
def _cerniere_verticali(p, x, y, h, n, colore):
    n = max(2, n)
    for i in range(n):
        yy = y + 200 + (h - 400) * i / (n - 1)
        _metallo(p, x - 15, yy - 60, 30, 120, colore)


def _cerniere_orizzontali(p, x, w, y, n, colore):
    n = max(2, n)
    for i in range(n):
        xx = x + 200 + (w - 400) * i / (n - 1)
        _metallo(p, xx - 60, y - 15, 120, 30, colore)


def _leva(p, col, rosetta: QRectF, a: QPointF, b: QPointF, off: QPointF):
    """Maniglia a leva: ombra, rosetta, leva arrotondata con riflesso e perno.
    a = centro della rosetta, b = estremità della leva, off = spostamento del riflesso."""
    # ombra della leva
    ombra = QPointF(2.5, 4.0)
    p.setPen(_pen_arrotondato(QColor(0, 0, 0, 60), 15))
    p.drawLine(a + ombra, b + ombra)

    # rosetta con angoli arrotondati
    rosa = QPainterPath()
    rosa.addRoundedRect(rosetta, 9, 9)
    _riempi_telaio(p, rosa, col, 1.0)

    # leva
    p.setPen(_pen_arrotondato(col.darker(112), 14))
    p.drawLine(a, b)
    p.setPen(_pen_arrotondato(col.lighter(155), 4))
    p.drawLine(a + off, b + off)

    # perno
    perno = QPainterPath()
    perno.addEllipse(a, 10.0, 10.0)
    _riempi_telaio(p, perno, col, 1.0)


def _maniglia_verticale(p, tipo, col, xe, yc, d):
    """Maniglia su bordo verticale. d = +1 o -1 indica il verso verso l'interno dell'anta."""
    if tipo == "maniglia":
        _leva(p, col,
              QRectF(xe - 11, yc - 38, 22, 77),
              QPointF(xe, yc), QPointF(xe + d * 126, yc),
              QPointF(0, -3))
    elif tipo == "maniglione":
        xb = xe + d * 60
        for yy in (yc - 400, yc + 400):
            _metallo(p, min(xe, xb), yy - 12, abs(xb - xe), 24, col)
        _metallo(p, xb - 15, yc - 400, 30, 800, col)


def _maniglia_orizzontale(p, tipo, col, xc, ye, d):
    """Maniglia su bordo orizzontale (vasistas). d = -1 indica verso l'alto."""
    if tipo == "maniglia":
        _leva(p, col,
              QRectF(xc - 38, ye - 11, 77, 22),
              QPointF(xc, ye), QPointF(xc, ye + d * 126),
              QPointF(-3, 0))
    elif tipo == "maniglione":
        yb = ye + d * 60
        for xx in (xc - 400, xc + 400):
            _metallo(p, xx - 12, min(yb, ye), 24, abs(yb - ye), col)
        _metallo(p, xc - 400, yb - 15, 800, 30, col)


# ---------------------------------------------------------------------------
# Ante
# ---------------------------------------------------------------------------
def _anta_battente(p, e, x, y, w, h, S, telaio, vetro, cerniera, yc,
                   con_maniglia, ribalta, col_cern, col_mani):
    """Anta a battente. cerniera: 'sx' o 'dx'. ribalta: aggiunge il simbolo di ribalta."""
    g = (x, y, w, h, "rettangolare", 0)
    _telaio(p, g, telaio)
    _vetrata(p, e, _ins(g, S), telaio, vetro)

    cx, cy = x + w / 2, y + h / 2
    p.setPen(_pen(ROSSO, 2.2, e.verso == "esterno"))
    if cerniera == "sx":
        xcer, xe, d = x, x + w - S / 2, -1
        p.drawLine(QPointF(x, y), QPointF(x + w, cy))
        p.drawLine(QPointF(x, y + h), QPointF(x + w, cy))
    else:
        xcer, xe, d = x + w, x + S / 2, +1
        p.drawLine(QPointF(x + w, y), QPointF(x, cy))
        p.drawLine(QPointF(x + w, y + h), QPointF(x, cy))
    if ribalta:
        p.drawLine(QPointF(x, y + h), QPointF(cx, y))
        p.drawLine(QPointF(x + w, y + h), QPointF(cx, y))

    _cerniere_verticali(p, xcer, y, h, e.numero_cerniere, col_cern)
    if con_maniglia and e.maniglia != "nessuna":
        _maniglia_verticale(p, e.maniglia, col_mani, xe, yc, d)


def _anta_vasistas(p, e, x, y, w, h, S, telaio, vetro, col_cern, col_mani):
    """Ribalta (vasistas): cerniere sul bordo superiore, maniglia in basso."""
    g = (x, y, w, h, "rettangolare", 0)
    _telaio(p, g, telaio)
    _vetrata(p, e, _ins(g, S), telaio, vetro)

    cx = x + w / 2
    p.setPen(_pen(ROSSO, 2.2, e.verso == "esterno"))
    p.drawLine(QPointF(x, y), QPointF(cx, y + h))
    p.drawLine(QPointF(x + w, y), QPointF(cx, y + h))

    _cerniere_orizzontali(p, x, w, y, e.numero_cerniere, col_cern)
    if e.maniglia != "nessuna":
        _maniglia_orizzontale(p, e.maniglia, col_mani, cx, y + h - S / 2, -1)


def _freccia_doppia(p, x1, x2, y):
    """Freccia doppia rossa: l'anta scorre nei due sensi."""
    p.setPen(_pen_arrotondato(ROSSO, 2.2))
    p.drawLine(QPointF(x1, y), QPointF(x2, y))
    for xa, d in ((x1, 1), (x2, -1)):
        p.drawLine(QPointF(xa, y), QPointF(xa + d * 55, y - 40))
        p.drawLine(QPointF(xa, y), QPointF(xa + d * 55, y + 40))


def _anta_scorrevole(p, e, x, y, w, h, S, telaio, vetro, col_mani, yc, xe, d,
                     ribalta=False, col_cern=None):
    """Anta scorrevole: telaio, vetro, maniglia sul bordo interno e freccia di scorrimento.
    Con ribalta: cerniere sul bordo superiore e simbolo di ribalta."""
    g = (x, y, w, h, "rettangolare", 0)
    _telaio(p, g, telaio)
    _vetrata(p, e, _ins(g, S), telaio, vetro)
    if ribalta:
        # vasistas: cerniere sul bordo superiore, l'anta si apre dal basso
        p.setPen(_pen(ROSSO, 2.2, e.verso == "esterno"))
        p.drawLine(QPointF(x, y), QPointF(x + w / 2, y + h))
        p.drawLine(QPointF(x + w, y), QPointF(x + w / 2, y + h))
        _cerniere_orizzontali(p, x, w, y, e.numero_cerniere, col_cern)
    _freccia_doppia(p, x + w * 0.2, x + w * 0.8, y + h / 2)
    if e.maniglia != "nessuna":
        _maniglia_verticale(p, e.maniglia, col_mani, xe, yc, d)


def _scorrevole(p, e, ox, oy, ow, oh, S, telaio, vetro, col_cern, col_mani, yc, tipo, lato):
    """Scorrevole a 1 anta, oppure anta scorrevole affiancata a un'anta fissa."""
    if tipo == "scorrevole-1":
        _anta_scorrevole(p, e, ox, oy, ow, oh, S, telaio, vetro, col_mani, yc,
                         ox + ow - S / 2, -1, e.anta_ribalta, col_cern)
        return
    wf = ow / 2
    if lato == "sinistra":
        xs, xf = ox, ox + wf
        xe, d = xs + wf - S / 2, -1          # maniglia sul bordo interno, verso il centro
    else:
        xs, xf = ox + wf, ox
        xe, d = xs + S / 2, +1
    fissa = (xf, oy, wf, oh, "rettangolare", 0)
    _telaio(p, fissa, telaio)
    _vetrata(p, e, _ins(fissa, S), telaio, vetro)
    _anta_scorrevole(p, e, xs, oy, wf, oh, S, telaio, vetro, col_mani, yc, xe, d,
                     e.anta_ribalta, col_cern)


COS35, SIN35 = 0.8192, 0.5736   # posizione delle cerniere sul bordo della tonda (35°)


def _anta_curva(p, e, g, S, telaio, vetro, cerniera, yc, col_cern, col_mani, ribalta):
    """Anta ad arco o tonda, apribile a battente. cerniera: 'sx' o 'dx'.
    Nell'arco le cerniere stanno sul lato dritto; nella tonda sul bordo, a 35° dal centro."""
    x, y, w, h, f, ah = g
    _telaio(p, g, telaio)
    _vetrata(p, e, _ins(g, S), telaio, vetro)
    p.setPen(_pen(ROSSO, 2.2, e.verso == "esterno"))

    if f == "tondo":
        R = min(w, h) / 2
        cx, cy = x + w / 2, y + h / 2
        lato = -1 if cerniera == "sx" else 1      # lato delle cerniere
        xcer = cx + lato * R * COS35
        xe = cx - lato * (R - S / 2)              # maniglia sul lato opposto
        for dy in (-R * SIN35, R * SIN35):
            # il pennello va reimpostato ogni volta: le cerniere disegnate prima lo cambiano
            p.setPen(_pen(ROSSO, 2.2, e.verso == "esterno"))
            p.drawLine(QPointF(xcer, cy + dy), QPointF(xe, cy))
            _metallo(p, xcer - 15, cy + dy - 40, 30, 80, col_cern)
        if e.maniglia != "nessuna":
            _maniglia_verticale(p, e.maniglia, col_mani, xe, cy, lato)
        return

    # arco: il lato dritto parte dall'attacco dell'arco
    ys = min(y + ah, y + h - 200)
    yh = min(max(yc, ys + 150), y + h - 150)     # altezza della maniglia
    if cerniera == "sx":
        xcer, xe, d, punta = x, x + w - S / 2, -1, (x + w, yh)
        attacchi = [(x, ys), (x, y + h)]
    else:
        xcer, xe, d, punta = x + w, x + S / 2, +1, (x, yh)
        attacchi = [(x + w, ys), (x + w, y + h)]
    for ax, ay in attacchi:
        p.drawLine(QPointF(ax, ay), QPointF(punta[0], punta[1]))
    if ribalta:
        p.drawLine(QPointF(x, y + h), QPointF(x + w / 2, y))
        p.drawLine(QPointF(x + w, y + h), QPointF(x + w / 2, y))
    _cerniere_verticali(p, xcer, ys, y + h - ys, e.numero_cerniere, col_cern)
    if e.maniglia != "nessuna":
        _maniglia_verticale(p, e.maniglia, col_mani, xe, yh, d)


def _nastro(p, e, ox, oy, ow, oh, F, S, telaio, vetro, col_cern, col_mani, yc):
    """Nastro: moduli affiancati separati da un montante del telaio.
    Valori di ciascun modulo:
      fisso | battente-sx | battente-dx | battente-sx-ribalta | battente-dx-ribalta | vasistas"""
    moduli = e.moduli or ["fisso"]
    n = len(moduli)
    total = ow - (n - 1) * F                  # spazio disponibile per i moduli
    if not e.nastro_simmetrico and len(e.larghezze_moduli) == n:
        imposte = [max(v, 0.0) for v in e.larghezze_moduli]
    else:
        imposte = [0.0] * n
    somma = sum(imposte)
    if somma > total:                          # misure troppo grandi: le riduco in proporzione
        imposte = [v * total / somma for v in imposte]
        somma = total
    liberi = [i for i, v in enumerate(imposte) if v <= 0]
    rimanenza = (total - somma) / len(liberi) if liberi else 0.0
    larghezze = [v if v > 0 else max(rimanenza, 30.0) for v in imposte]

    x = ox
    for i, (tipo, wm) in enumerate(zip(moduli, larghezze)):
        if tipo == "fisso":
            g = (x, oy, wm, oh, "rettangolare", 0)
            _telaio(p, g, telaio)
            _vetrata(p, e, _ins(g, S), telaio, vetro)
        elif tipo == "vasistas":
            _anta_vasistas(p, e, x, oy, wm, oh, S, telaio, vetro, col_cern, col_mani)
        elif tipo == "scorrevole":
            _anta_scorrevole(p, e, x, oy, wm, oh, S, telaio, vetro, col_mani, yc,
                             x + wm - S / 2, -1)
        else:
            cerniera = "sx" if tipo.startswith("battente-sx") else "dx"
            ribalta = tipo.endswith("-ribalta")
            _anta_battente(p, e, x, oy, wm, oh, S, telaio, vetro, cerniera, yc,
                           con_maniglia=True, ribalta=ribalta,
                           col_cern=col_cern, col_mani=col_mani)
        x += wm
        if i < n - 1:
            _telaio(p, (x, oy, F, oh, "rettangolare", 0), telaio)
            x += F


# ---------------------------------------------------------------------------
# Disegno completo
# ---------------------------------------------------------------------------
def disegna(p: QPainter, e: Elemento, profilo: Profilo, con_quote=True):
    """Disegna la finestra in mm, con origine in alto a sinistra."""
    W, H = e.larghezza, e.altezza
    F, S = profilo.spessore_telaio, profilo.spessore_anta
    forma = "rettangolare" if e.nastro else e.forma
    rett = forma == "rettangolare"
    sopra = e.sopraluce and rett
    yTop = min(max(e.altezza_sopraluce, 2 * F + 50), H - 300) if sopra else F

    telaio = QColor(e.colore_telaio)
    vetro = QColor(e.colore_vetro)
    col_cern = QColor(e.colore_cerniere)
    col_mani = QColor(e.colore_maniglia)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # 1. Ombra e telaio esterno
    G = (0.0, 0.0, W, H, forma, _ah_arco(forma, W))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 45))
    p.drawPath(_path(G).translated(OMBRA, OMBRA))
    _telaio(p, G, telaio)

    # 2. Sopraluce fisso con traversa
    if sopra:
        _pannello(p, (F, F, W - 2 * F, yTop - 2 * F, "rettangolare", 0),
                  telaio, vetro, e.fermavetri)
        _telaio(p, (F, yTop - F, W - 2 * F, F, "rettangolare", 0), telaio)

    # 3. Anta, ante o nastro
    ox, oy = F, yTop
    ow, oh = W - 2 * F, H - F - yTop
    # altezza della maniglia: 0 = centro dell'anta, altrimenti altezza da terra
    if e.altezza_maniglia > 0:
        yc = min(max(H - e.altezza_maniglia, oy + 150), oy + oh - 150)
    else:
        yc = oy + oh / 2
    if e.nastro:
        a = "fisso"
    elif rett or e.apertura in ("battente-sx", "battente-dx"):
        a = e.apertura
    else:
        a = "fisso"                 # forme curve: solo fisse o a battente
    # area dell'anta: rettangolare, oppure l'interno del telaio ad arco
    ga = (ox, oy, ow, oh, "rettangolare", 0) if rett else _ins(G, F)

    if e.nastro:
        _nastro(p, e, ox, oy, ow, oh, F, S, telaio, vetro, col_cern, col_mani, yc)

    elif a == "fisso":
        _telaio(p, ga, telaio)
        _vetrata(p, e, _ins(ga, S), telaio, vetro)

    elif not rett:
        cerniera = "sx" if a == "battente-sx" else "dx"
        _anta_curva(p, e, ga, S, telaio, vetro, cerniera, yc, col_cern, col_mani,
                    e.anta_ribalta)

    elif a in ("scorrevole-1", "scorrevole-2"):
        _scorrevole(p, e, ox, oy, ow, oh, S, telaio, vetro, col_cern, col_mani, yc,
                    a, e.lato_scorrevole)

    elif a == "ribalta":
        _anta_vasistas(p, e, ox, oy, ow, oh, S, telaio, vetro, col_cern, col_mani)

    elif a == "doppia-anta":
        m = F                                   # montante centrale (spessore del telaio)
        if not e.doppia_simmetrica and e.larghezza_anta_sx > 0:
            wl = min(max(e.larghezza_anta_sx, 50.0), ow - m - 50.0)
        else:
            wl = max((ow - m) / 2, 50)
        wr = max(ow - m - wl, 50)
        xd = ox + wl + m
        pr = e.anta_principale

        _anta_battente(p, e, ox, oy, wl, oh, S, telaio, vetro, "sx", yc,
                       con_maniglia=(pr == "sinistra"),
                       ribalta=(e.anta_ribalta and pr == "sinistra"),
                       col_cern=col_cern, col_mani=col_mani)
        _anta_battente(p, e, xd, oy, wr, oh, S, telaio, vetro, "dx", yc,
                       con_maniglia=(pr == "destra"),
                       ribalta=(e.anta_ribalta and pr == "destra"),
                       col_cern=col_cern, col_mani=col_mani)
        _telaio(p, (ox + wl, oy, m, oh, "rettangolare", 0), telaio)

    else:  # battente-sx / battente-dx
        cerniera = "sx" if a == "battente-sx" else "dx"
        _anta_battente(p, e, ox, oy, ow, oh, S, telaio, vetro, cerniera, yc,
                       con_maniglia=True, ribalta=e.anta_ribalta,
                       col_cern=col_cern, col_mani=col_mani)

    # 4. Quote (facoltative)
    if con_quote:
        font = QFont()
        font.setPixelSize(55)
        p.setFont(font)
        p.setPen(QPen(NERO))
        _quota_orizzontale(p, 0, W, -130, f"{W:.0f} mm")
        _quota_verticale(p, 0, H, -130, f"{H:.0f} mm")
        if sopra:
            _quota_verticale(p, 0, yTop, W + 130)
            p.setPen(QPen(NERO))
            p.drawText(
                QRectF(W + 160, yTop / 2 - 90, 360, 180),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"Sopraluce\n{yTop:.0f} mm",
            )


def _quota_orizzontale(p, x1, x2, y, testo):
    p.setPen(_pen(NERO, 1.2))
    p.drawLine(QPointF(x1, y), QPointF(x2, y))
    for x in (x1, x2):
        p.drawLine(QPointF(x - 25, y + 25), QPointF(x + 25, y - 25))
    p.drawText(QRectF(x1, y - 75, x2 - x1, 60), Qt.AlignmentFlag.AlignCenter, testo)


def _quota_verticale(p, y1, y2, x, testo=None):
    p.setPen(_pen(NERO, 1.2))
    p.drawLine(QPointF(x, y1), QPointF(x, y2))
    for y in (y1, y2):
        p.drawLine(QPointF(x - 25, y + 25), QPointF(x + 25, y - 25))
    if testo:
        p.save()
        p.translate(x, (y1 + y2) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-(y2 - y1) / 2, -75, y2 - y1, 60), Qt.AlignmentFlag.AlignCenter, testo)
        p.restore()


# ---------------------------------------------------------------------------
# Adattamento alla pagina ed esportazione
# ---------------------------------------------------------------------------
def _adatta(p: QPainter, area: QRectF, e: Elemento, profilo: Profilo, con_quote=True):
    """Disegna il serramento centrato e scalato nell'area indicata."""
    W, H = e.larghezza, e.altezza
    if con_quote:
        m = MARGINE_QUOTE if e.sopraluce else MARGINE_QUOTE_BASE   # il sopraluce ha la quota a destra
    else:
        m = MARGINE_NUDO
    box = QRectF(-m, -m, W + 2 * m, H + 2 * m)
    scala = min(area.width() / box.width(), area.height() / box.height())
    centro = box.center()
    p.save()
    p.translate(area.center())
    p.scale(scala, scala)
    p.translate(-centro.x(), -centro.y())
    disegna(p, e, profilo, con_quote)
    p.restore()


def disegna_pagina(p: QPainter, rect: QRectF, e: Elemento, profilo: Profilo,
                   con_quote=True, con_didascalia=True):
    """Pagina completa per l'esportazione: didascalia in alto e disegno sotto."""
    p.fillRect(rect, QColor("white"))
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    testata_h = rect.height() * 0.08 if con_didascalia else 0.0
    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(12, int(rect.height() * 0.04)))
    p.setFont(font)
    p.setPen(QPen(NERO))
    info = (f"{e.nome}   |   {e.larghezza:.0f} × {e.altezza:.0f} mm   |   "
            f"{'Nastro' if e.nastro else TIPI.get(e.tipo, e.tipo)}   |   Profilo: {profilo.nome}")
    if con_didascalia:
        p.drawText(QRectF(rect.left(), rect.top(), rect.width(), testata_h),
               Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, info)

    area = QRectF(rect.left(), rect.top() + testata_h,
                  rect.width(), rect.height() - testata_h)
    _adatta(p, area, e, profilo, con_quote)


DIMENSIONI_PAGINA = {"A4": (297, 210), "A3": (420, 297), "A5": (210, 148)}   # mm, orizzontale
PAGINE_PDF = {
    "A4": QPageSize.PageSizeId.A4,
    "A3": QPageSize.PageSizeId.A3,
    "A5": QPageSize.PageSizeId.A5,
}


def esporta_jpg(percorso, e: Elemento, profilo: Profilo, con_quote=True, con_didascalia=True,
                formato="A4", dpi=300):
    """Esporta in JPG orizzontale nel formato e alla risoluzione indicati."""
    w_mm, h_mm = DIMENSIONI_PAGINA[formato]
    w_px = round(w_mm / 25.4 * dpi)
    h_px = round(h_mm / 25.4 * dpi)
    margine = round(w_px * 0.027)
    img = QImage(w_px, h_px, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.white)
    p = QPainter(img)
    try:
        disegna_pagina(p, QRectF(0, 0, w_px, h_px).adjusted(margine, margine, -margine, -margine),
                       e, profilo, con_quote, con_didascalia)
    finally:
        p.end()
    if not img.save(percorso, "JPG", 92):
        raise OSError("Salvataggio JPG non riuscito")


def esporta_pdf(percorso, e: Elemento, profilo: Profilo, con_quote=True, con_didascalia=True,
                formato="A4"):
    """Esporta un elemento in PDF orizzontale nel formato indicato."""
    esporta_pdf_multi(percorso, [(e, profilo, con_quote, con_didascalia)], formato, e.nome)


def esporta_pdf_multi(percorso, voci, formato="A4", titolo="Serramenti"):
    """PDF con una pagina per elemento. voci: lista di (elemento, profilo, con_quote, con_didascalia)."""
    writer = QPdfWriter(percorso)
    writer.setResolution(300)
    writer.setPageSize(QPageSize(PAGINE_PDF[formato]))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    writer.setTitle(titolo)
    p = QPainter(writer)
    try:
        for i, (e, profilo, con_quote, con_didascalia) in enumerate(voci):
            if i > 0:
                writer.newPage()
            disegna_pagina(p, QRectF(0, 0, writer.width(), writer.height()).adjusted(120, 120, -120, -120),
                           e, profilo, con_quote, con_didascalia)
    finally:
        p.end()


class Anteprima(QWidget):
    """Widget che mostra il disegno dell'elemento selezionato."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.elemento = None
        self.profilo = None
        self.setMinimumSize(400, 300)

    def mostra(self, elemento, profilo):
        self.elemento = elemento
        self.profilo = profilo
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#ffffff"))
        if self.elemento is None:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Nessun elemento selezionato")
        else:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            _adatta(p, QRectF(self.rect()).adjusted(20, 20, -20, -20),
                    self.elemento, self.profilo, self.elemento.mostra_quote)
        p.end()
