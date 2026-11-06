"""Esportazione multipla: più elementi del progetto in una sola operazione."""
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLabel, QListWidget,
    QListWidgetItem, QProgressDialog, QVBoxLayout,
)

from disegno import esporta_jpg, esporta_pdf, esporta_pdf_multi

MODALITA = {
    "jpg": "JPG, un file per elemento",
    "pdf": "PDF, un file per elemento",
    "pdf_unico": "PDF unico, una pagina per elemento",
}


class BatchDialog(QDialog):
    """Elenco degli elementi con casella di selezione, opzioni comuni e modalità."""

    def __init__(self, elementi, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Esportazione multipla")
        self.resize(440, 520)
        self.elementi = list(elementi)

        self.lista = QListWidget()
        for e in self.elementi:
            voce = QListWidgetItem(e.nome)
            voce.setFlags(voce.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            voce.setCheckState(Qt.CheckState.Checked)
            self.lista.addItem(voce)

        # Opzioni valide per tutti gli elementi esportati
        self.f_quote = QCheckBox("Includi quote")
        self.f_quote.setChecked(True)
        self.f_didascalia = QCheckBox("Includi didascalia")
        self.f_didascalia.setChecked(True)

        self.modalita_box = QComboBox()
        for chiave, testo in MODALITA.items():
            self.modalita_box.addItem(testo, chiave)

        pulsanti = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                    | QDialogButtonBox.StandardButton.Cancel)
        pulsanti.button(QDialogButtonBox.StandardButton.Ok).setText("Scegli cartella…")
        pulsanti.button(QDialogButtonBox.StandardButton.Ok).setMinimumWidth(140)
        pulsanti.button(QDialogButtonBox.StandardButton.Cancel).setText("Annulla")
        pulsanti.button(QDialogButtonBox.StandardButton.Cancel).setMinimumWidth(100)
        pulsanti.accepted.connect(self.accept)
        pulsanti.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Elementi da esportare"))
        layout.addWidget(self.lista, 1)
        layout.addWidget(QLabel("Contenuto"))
        layout.addWidget(self.f_quote)
        layout.addWidget(self.f_didascalia)
        layout.addWidget(QLabel("Modalità"))
        layout.addWidget(self.modalita_box)
        layout.addWidget(pulsanti)

    def selezionati(self):
        return [e for i, e in enumerate(self.elementi)
                if self.lista.item(i).checkState() == Qt.CheckState.Checked]

    def modalita(self) -> str:
        return self.modalita_box.currentData()

    def con_quote(self) -> bool:
        return self.f_quote.isChecked()

    def con_didascalia(self) -> bool:
        return self.f_didascalia.isChecked()


def _nome_file(nome: str, usati: set) -> str:
    """Nome sicuro per il file, senza duplicati (confronto senza maiuscole)."""
    base = re.sub(r"[^\w\- ]+", "_", nome).strip() or "elemento"
    candidato, n = base, 2
    while candidato.lower() in usati:
        candidato = f"{base} ({n})"
        n += 1
    usati.add(candidato.lower())
    return candidato


def esporta_batch(elementi, profilo_di, formato, dpi, modalita, cartella: Path,
                  titolo, con_quote, con_didascalia, parent=None):
    """Esporta più elementi con le stesse opzioni. Ritorna (file_creati, errori)."""
    creati, errori = [], []

    if modalita == "pdf_unico":
        voci = [(e, profilo_di(e), con_quote, con_didascalia) for e in elementi]
        percorso = cartella / f"{_nome_file(titolo, set())}.pdf"
        try:
            esporta_pdf_multi(str(percorso), voci, formato, titolo)
            creati.append(percorso)
        except OSError as err:
            errori.append(f"{percorso.name}: {err}")
        return creati, errori

    progresso = QProgressDialog("Esportazione in corso…", "Annulla", 0, len(elementi), parent)
    progresso.setWindowModality(Qt.WindowModality.WindowModal)
    progresso.setMinimumDuration(0)
    usati = set()
    for i, e in enumerate(elementi):
        progresso.setValue(i)
        if progresso.wasCanceled():
            break
        estensione = "jpg" if modalita == "jpg" else "pdf"
        percorso = cartella / f"{_nome_file(e.nome, usati)}.{estensione}"
        try:
            if modalita == "jpg":
                esporta_jpg(str(percorso), e, profilo_di(e), con_quote, con_didascalia,
                            formato, dpi)
            else:
                esporta_pdf(str(percorso), e, profilo_di(e), con_quote, con_didascalia,
                            formato)
            creati.append(percorso)
        except OSError as err:
            errori.append(f"{percorso.name}: {err}")
    progresso.setValue(len(elementi))
    return creati, errori
