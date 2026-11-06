import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from finestra import MainWindow
from wizard import guida_all_avvio

# Palette ispirata ai colori di sistema di macOS
BLU = "#0071e3"
BLU_HOVER = "#0077ed"
BLU_PRESSO = "#006edb"
TESTO = "#1d1d1f"
TESTO_SECONDARIO = "#6e6e73"
SFONDO = "#f5f5f7"
CARD = "#ffffff"
SEPARATORE = "#d2d2d7"
SEPARATORE_LEGGERO = "#e5e5ea"
SIDEBAR = "#ebebf0"

STILE = f"""
QMainWindow {{
    background: {SFONDO};
}}
QWidget {{
    color: {TESTO};
    font-size: 13px;
}}
QLabel {{
    background: transparent;
}}

/* Card: sezioni del pannello */
QGroupBox {{
    background: {CARD};
    border: 1px solid {SEPARATORE_LEGGERO};
    border-radius: 12px;
    margin-top: 18px;
    padding: 18px 14px 12px 14px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 4px;
    color: {TESTO_SECONDARIO};
    background: {CARD};
    font-size: 12px;
    font-weight: 600;
}}

/* Campi di testo e menu a tendina (il padding è lasciato al sistema) */
QComboBox, QLineEdit {{
    background: #fbfbfd;
    border: 1px solid {SEPARATORE};
    border-radius: 6px;
    min-height: 22px;
    selection-background-color: {BLU};
}}
QComboBox:hover, QLineEdit:hover {{
    border: 1px solid #b0b0b8;
}}
QComboBox:focus, QLineEdit:focus {{
    border: 1px solid {BLU};
    background: {CARD};
}}
QComboBox:disabled, QLineEdit:disabled {{
    background: #f2f2f5;
    color: #a1a1a6;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {SEPARATORE};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {BLU};
    selection-color: #ffffff;
    outline: none;
}}

/* Campi numerici: le frecce sono disattivate dal codice (NoButtons) */
QDoubleSpinBox, QSpinBox {{
    background: #fbfbfd;
    border: 1px solid {SEPARATORE};
    border-radius: 6px;
    selection-background-color: {BLU};
}}
QDoubleSpinBox:hover, QSpinBox:hover {{
    border: 1px solid #b0b0b8;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {BLU};
    background: {CARD};
}}
QDoubleSpinBox:disabled, QSpinBox:disabled {{
    background: #f2f2f5;
    color: #a1a1a6;
}}

/* Pulsanti: blu di sistema per l'azione principale */
QPushButton {{
    background: {BLU};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 12px;
    min-width: 64px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {BLU_HOVER};
}}
QPushButton:pressed {{
    background: {BLU_PRESSO};
}}
QPushButton:disabled {{
    background: #b8d6f7;
    color: #f5f9ff;
}}
QPushButton#secondario {{
    background: {CARD};
    color: {TESTO};
    border: 1px solid {SEPARATORE};
}}
QPushButton#secondario:hover {{
    background: #f5f5f7;
}}

/* Elenco elementi */
QListWidget {{
    background: {CARD};
    border: 1px solid {SEPARATORE_LEGGERO};
    border-radius: 12px;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 9px 12px;
    border-radius: 6px;
    margin: 1px 0;
}}
QListWidget::item:hover {{
    background: #f2f2f5;
}}
QListWidget::item:selected {{
    background: {BLU};
    color: #ffffff;
}}

/* Barra laterale di navigazione, in stile macOS */
QListWidget#nav {{
    background: {SIDEBAR};
    border: none;
    border-radius: 10px;
    padding: 8px;
}}
QListWidget#nav::item {{
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 0;
    font-size: 13px;
    color: {TESTO};
}}
QListWidget#nav::item:hover {{
    background: #e0e0e5;
}}
QListWidget#nav::item:selected {{
    background: {CARD};
    color: {TESTO};
    font-weight: 600;
}}

/* Caselle di controllo */
QCheckBox {{
    spacing: 8px;
}}

/* Barra dei menu (su macOS è comunque quella di sistema) */
QMenuBar {{
    background: {CARD};
    border-bottom: 1px solid {SEPARATORE_LEGGERO};
    padding: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background: {SEPARATORE_LEGGERO};
}}
QMenu {{
    background: {CARD};
    border: 1px solid {SEPARATORE};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 22px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background: {BLU};
    color: #ffffff;
}}
QMenu::separator {{
    height: 1px;
    background: {SEPARATORE_LEGGERO};
    margin: 5px 8px;
}}

QToolTip {{
    background: rgba(29, 29, 31, 0.92);
    color: #ffffff;
    border: none;
    padding: 6px 8px;
    border-radius: 6px;
}}

QMessageBox {{
    background: {CARD};
}}
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WCad")
    app.setApplicationDisplayName("WCad")
    app.setApplicationVersion("1.0")
    app.setStyle("Fusion")
    # font di sistema: su macOS è San Francisco
    app.setFont(QFont(app.font().family(), 13))
    app.setStyleSheet(STILE)
    finestra = MainWindow()
    finestra.resize(1480, 920)
    finestra.show()
    guida_all_avvio(finestra)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
