"""Finestra principale e gestione della libreria profili."""
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog,
    QStyle, QStyleOptionComboBox, QStylePainter,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from modelli import (
    ANTE_PRINCIPALI, APERTURE, COLORI_FERRAMENTA, COLORI_SERRAMENTO, COLORI_VETRO,
    DIMENSIONI_TIPO, ESTENSIONE_PROGETTO, FORME, FORMATI_PAGINA, MANIGLIE, MODULI,
    RISOLUZIONI_DPI,
    TIPI, VERSI, VETRI_PORTA,
    Elemento, LibreriaProfili, Profilo, Progetto,
    apri_progetto as leggi_progetto, salva_progetto as scrivi_progetto,
)
from disegno import Anteprima, esporta_jpg, esporta_pdf
from batch import BatchDialog, esporta_batch
from wizard import guida_all_avvio_attiva, imposta_guida_all_avvio, mostra_guida


class CampoNumerico(QLineEdit):
    """Campo per misure: si digita direttamente, senza frecce.
    Tasti freccia su/giù e rotella del mouse incrementano il valore quando il campo è attivo."""
    valueChanged = Signal(float)

    def __init__(self, minimo, massimo, decimali=0, passo=10, suffisso=" mm",
                 intero=False, parent=None):
        super().__init__(parent)
        self._min = minimo
        self._max = massimo
        self._dec = decimali
        self._passo = passo
        self._suffisso = suffisso
        self._intero = intero
        self._speciale = ""
        self._valore = minimo
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.textEdited.connect(self._digitato)
        self.editingFinished.connect(self._formatta)
        self._mostra()

    def value(self):
        return int(round(self._valore)) if self._intero else self._valore

    def setValue(self, v):
        v = min(max(float(v), self._min), self._max)
        if self._intero:
            v = round(v)
        if v != self._valore:
            self._valore = v
            self.valueChanged.emit(float(v))
        self._mostra()

    def setRange(self, minimo, massimo):
        self._min, self._max = minimo, massimo
        self.setValue(self._valore)

    def setDecimals(self, decimali):
        self._dec = decimali
        self._mostra()

    def setSingleStep(self, passo):
        self._passo = passo

    def setSuffix(self, suffisso):
        self._suffisso = suffisso
        self._mostra()

    def setSpecialValueText(self, testo):
        self._speciale = testo
        self._mostra()

    def _mostra(self):
        if self._speciale and self._valore == self._min:
            self.setText(self._speciale)
        else:
            self.setText(f"{self._valore:.{self._dec}f}{self._suffisso}")

    def _leggi(self, testo) -> float:
        t = testo.replace(self._suffisso.strip(), "").replace(",", ".").strip()
        return float(t)  # può sollevare ValueError

    def _digitato(self, testo):
        """Aggiornamento durante la digitazione, se il valore è valido."""
        try:
            v = self._leggi(testo)
        except ValueError:
            return
        if not self._min <= v <= self._max:
            return
        if self._intero:
            v = round(v)
        if v != self._valore:
            self._valore = v
            self.valueChanged.emit(float(v))

    def _formatta(self):
        """Alla fine della modifica: riscrive il valore nel formato corretto."""
        try:
            v = self._leggi(self.text())
        except ValueError:
            v = self._valore
        self.setValue(v)

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            passo = self._passo if ev.key() == Qt.Key.Key_Up else -self._passo
            self.setValue(self._valore + passo)
            return
        super().keyPressEvent(ev)

    def wheelEvent(self, ev):
        if self.hasFocus():
            passo = self._passo if ev.angleDelta().y() > 0 else -self._passo
            self.setValue(self._valore + passo)
            ev.accept()
            return
        super().wheelEvent(ev)


def _spin(minimo, massimo, decimali=0, passo=10, suffisso=" mm"):
    return CampoNumerico(minimo, massimo, decimali, passo, suffisso)


def _intero(minimo, massimo):
    return CampoNumerico(minimo, massimo, 0, 1, "", intero=True)


class ComboCentrato(QComboBox):
    """Menu a tendina con il testo della voce selezionata centrato."""

    def paintEvent(self, ev):
        p = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        testo = opt.currentText
        opt.currentText = ""
        p.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        area = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, opt, QStyle.SubControl.SC_ComboBoxEditField, self)
        p.setPen(self.palette().buttonText().color())
        p.drawText(area, Qt.AlignmentFlag.AlignCenter, testo)


def _combo(voci: dict) -> ComboCentrato:
    c = ComboCentrato()
    for k, v in voci.items():
        c.addItem(v, k)
    return c


# ---------------------------------------------------------------------------
# Selettore colore: menu di colori predefiniti + colore personalizzato
# ---------------------------------------------------------------------------
class SelettoreColore(QWidget):
    cambiato = Signal()

    def __init__(self, predefiniti, parent=None):
        super().__init__(parent)
        self._hex = predefiniti[0][1]

        self.combo = ComboCentrato()
        for nome, hx in predefiniti:
            self.combo.addItem(nome, hx)
        self.combo.addItem("Personalizzato…", None)

        self.swatch = QPushButton()
        self.swatch.setFixedWidth(44)
        self.swatch.setToolTip("Scegli un colore personalizzato")
        self.swatch.clicked.connect(self._scegli)
        self.combo.currentIndexChanged.connect(self._da_combo)

        riga = QHBoxLayout(self)
        riga.setContentsMargins(0, 0, 0, 0)
        riga.addWidget(self.combo, 1)
        riga.addWidget(self.swatch)
        self._mostra()

    def colore(self) -> str:
        return self._hex

    def imposta(self, esadecimale: str):
        self._hex = esadecimale
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(self._indice_di(esadecimale))
        self.combo.blockSignals(False)
        self._mostra()

    def _indice_di(self, hx: str) -> int:
        for i in range(self.combo.count()):
            valore = self.combo.itemData(i)
            if valore and valore.lower() == hx.lower():
                return i
        return self.combo.count() - 1  # "Personalizzato…"

    def _da_combo(self, indice):
        hx = self.combo.itemData(indice)
        if hx is None:
            self._scegli()
            return
        self._hex = hx
        self._mostra()
        self.cambiato.emit()

    def _scegli(self):
        colore = QColorDialog.getColor(QColor(self._hex), self, "Scegli colore")
        if not colore.isValid():
            return
        self._hex = colore.name()
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(self.combo.count() - 1)
        self.combo.blockSignals(False)
        self._mostra()
        self.cambiato.emit()

    def _mostra(self):
        self.swatch.setStyleSheet(
            f"background-color: {self._hex}; border: 1px solid #8a94a0; border-radius: 4px;")


# ---------------------------------------------------------------------------
# Dialogo di gestione della libreria profili
# ---------------------------------------------------------------------------
class GestioneProfiliDialog(QDialog):
    def __init__(self, libreria: LibreriaProfili, parent=None):
        super().__init__(parent)
        self.libreria = libreria
        self.rinominati = {}      # nome vecchio -> nome nuovo
        self.modificato = False
        self.setWindowTitle("Libreria profili")
        self.resize(640, 320)

        self.lista = QListWidget()
        self.f_nome = QLineEdit()
        self.f_nome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.f_telaio = _spin(20, 300, 1, 1)
        self.f_anta = _spin(20, 300, 1, 1)

        modulo = QFormLayout()
        modulo.addRow("Nome profilo", self.f_nome)
        modulo.addRow("Spessore telaio", self.f_telaio)
        modulo.addRow("Spessore anta", self.f_anta)

        b_nuovo = QPushButton("Nuovo")
        b_salva = QPushButton("Salva modifiche")
        b_elimina = QPushButton("Elimina")
        b_chiudi = QPushButton("Chiudi")
        b_nuovo.clicked.connect(self._nuovo)
        b_salva.clicked.connect(self._salva)
        b_elimina.clicked.connect(self._elimina)
        b_chiudi.clicked.connect(self.accept)

        pulsanti = QHBoxLayout()
        for b in (b_nuovo, b_salva, b_elimina):
            pulsanti.addWidget(b)
        pulsanti.addStretch()
        pulsanti.addWidget(b_chiudi)

        destra = QVBoxLayout()
        destra.addLayout(modulo)
        destra.addStretch()
        destra.addLayout(pulsanti)

        riga = QHBoxLayout(self)
        riga.addWidget(self.lista, 1)
        riga.addLayout(destra, 2)

        self.lista.currentRowChanged.connect(self._carica)
        self._ricarica(0)

    def _ricarica(self, riga=0):
        self.lista.blockSignals(True)
        self.lista.clear()
        self.lista.addItems(self.libreria.nomi())
        self.lista.blockSignals(False)
        self.lista.setCurrentRow(riga)

    def _carica(self, riga):
        if not 0 <= riga < len(self.libreria.profili):
            return
        p = self.libreria.profili[riga]
        self.f_nome.setText(p.nome)
        self.f_telaio.setValue(p.spessore_telaio)
        self.f_anta.setValue(p.spessore_anta)

    def _nuovo(self):
        self.libreria.profili.append(Profilo("Nuovo profilo", 70, 60))
        self.libreria.salva()
        self.modificato = True
        self._ricarica(len(self.libreria.profili) - 1)

    def _salva(self):
        riga = self.lista.currentRow()
        if not 0 <= riga < len(self.libreria.profili):
            return
        nome = self.f_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Nome mancante", "Inserisci un nome per il profilo.")
            return
        if any(p.nome == nome for i, p in enumerate(self.libreria.profili) if i != riga):
            QMessageBox.warning(self, "Nome duplicato", "Esiste già un profilo con questo nome.")
            return

        p = self.libreria.profili[riga]
        vecchio = p.nome
        if vecchio != nome:
            for k, v in self.rinominati.items():
                if v == vecchio:
                    self.rinominati[k] = nome
            self.rinominati[vecchio] = nome

        p.nome = nome
        p.spessore_telaio = self.f_telaio.value()
        p.spessore_anta = self.f_anta.value()
        self.libreria.salva()
        self.modificato = True
        self._ricarica(riga)

    def _elimina(self):
        riga = self.lista.currentRow()
        if not 0 <= riga < len(self.libreria.profili):
            return
        if len(self.libreria.profili) <= 1:
            QMessageBox.warning(self, "Attenzione", "Deve restare almeno un profilo.")
            return
        nome = self.libreria.profili[riga].nome
        box = QMessageBox(self)
        box.setWindowTitle("Elimina profilo")
        box.setText(f"Eliminare il profilo '{nome}'?")
        b_elimina = box.addButton("Elimina", QMessageBox.ButtonRole.DestructiveRole)
        b_annulla = box.addButton("Annulla", QMessageBox.ButtonRole.RejectRole)
        for b in (b_elimina, b_annulla):
            b.setMinimumWidth(120)
        box.setMinimumWidth(360)
        box.exec()
        if box.clickedButton() is not b_elimina:
            return
        del self.libreria.profili[riga]
        self.libreria.salva()
        self.modificato = True
        self._ricarica(max(0, riga - 1))


# ---------------------------------------------------------------------------
# Finestra principale
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.libreria = LibreriaProfili()
        self.file_corrente = None
        self.modificato = False
        self._caricamento = False
        self.f_mod_combos = []

        self._costruisci_ui()
        self._costruisci_menu()

        self.progetto = Progetto(elementi=[
            Elemento(nome="Finestra 1", profilo=self._profilo_predefinito())
        ])
        self._aggiorna_lista(0)
        self._aggiorna_titolo()

    # ---------- costruzione interfaccia ----------
    @staticmethod
    def _pagina(gruppi) -> QWidget:
        """Contenitore di una scheda: i gruppi sono impilati dall'alto, senza scorrimento."""
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(12)
        for g in gruppi:
            l.addWidget(g)
        l.addStretch()
        return w

    def _costruisci_ui(self):
        centrale = QWidget()
        self.setCentralWidget(centrale)
        layout = QHBoxLayout(centrale)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Colonna sinistra: elenco elementi del progetto
        colonna = QVBoxLayout()
        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._seleziona)
        colonna.addWidget(self.lista)
        riga = QHBoxLayout()
        for testo, slot in (("Nuovo", self.nuovo_elemento),
                            ("Duplica", self.duplica_elemento),
                            ("Elimina", self.elimina_elemento)):
            b = QPushButton(testo)
            b.clicked.connect(slot)
            b.setStyleSheet("padding: 7px 4px; min-width: 0px;")
            riga.addWidget(b, 1)
        riga.setSpacing(6)
        colonna.addLayout(riga)
        colonna.setContentsMargins(0, 0, 0, 0)
        pannello_sx = QWidget()
        pannello_sx.setFixedWidth(240)
        pannello_sx.setLayout(colonna)
        layout.addWidget(pannello_sx, 0)

        # Centro: anteprima
        self.anteprima = Anteprima()
        layout.addWidget(self.anteprima, 1)

        # ----- Scheda "Dati"
        self.f_nome = QLineEdit()
        self.f_nome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.f_tipo = _combo(TIPI)
        self.f_forma = _combo(FORME)
        self.f_largh = _spin(300, 5000)
        self.f_alt = _spin(300, 5000)
        self.f_sop = QCheckBox("Presente")
        self.f_alt_sop = _spin(50, 3000)
        self.f_profilo = ComboCentrato()

        dati = QFormLayout()
        dati.addRow("Nome", self.f_nome)
        dati.addRow("Tipo", self.f_tipo)
        dati.addRow("Forma", self.f_forma)
        dati.addRow("Larghezza", self.f_largh)
        dati.addRow("Altezza", self.f_alt)
        dati.addRow("Sopraluce", self.f_sop)
        dati.addRow("Altezza sopraluce", self.f_alt_sop)
        dati.addRow("Profilo", self.f_profilo)
        gruppo_dati = QGroupBox("Dimensioni e profilo")
        gruppo_dati.setLayout(dati)

        self.f_fermavetri = QCheckBox("Mostra fermavetri")
        self.f_quote = QCheckBox("Mostra quote nell'anteprima")
        opzioni = QVBoxLayout()
        opzioni.addWidget(self.f_fermavetri)
        opzioni.addWidget(self.f_quote)
        gruppo_opzioni = QGroupBox("Opzioni di disegno")
        gruppo_opzioni.setLayout(opzioni)

        # ----- Scheda "Apertura"
        self.f_apertura = _combo(APERTURE)
        self.f_verso = _combo(VERSI)
        self.f_anta_princ = _combo(ANTE_PRINCIPALI)
        self.f_ribalta = QCheckBox("Anta ribalta")

        apertura = QFormLayout()
        apertura.addRow("Apertura", self.f_apertura)
        apertura.addRow("Verso", self.f_verso)
        apertura.addRow("Anta principale", self.f_anta_princ)
        apertura.addRow("", self.f_ribalta)
        self.f_lato_scorr = _combo(ANTE_PRINCIPALI)
        apertura.addRow("Anta scorrevole", self.f_lato_scorr)
        self.f_simm = QCheckBox("Doppia anta simmetrica")
        self.f_simm.setChecked(True)
        self.f_larg_sx = _spin(0, 3000)
        self.f_larg_sx.setSpecialValueText("Auto")
        apertura.addRow("", self.f_simm)
        apertura.addRow("Larghezza anta sx", self.f_larg_sx)
        gruppo_apertura = QGroupBox("Apertura")
        gruppo_apertura.setLayout(apertura)

        # Nastro: moduli affiancati, ognuno fisso o a battente
        self.f_nastro = QCheckBox("Attiva nastro di serramenti")
        self.f_n_moduli = _intero(1, 8)
        self._box_moduli = QWidget()
        self._layout_moduli = QVBoxLayout(self._box_moduli)
        self._layout_moduli.setContentsMargins(0, 0, 0, 0)
        self._layout_moduli.setSpacing(6)

        testa_nastro = QFormLayout()
        testa_nastro.addRow("", self.f_nastro)
        testa_nastro.addRow("N. moduli", self.f_n_moduli)
        self.f_nastro_simm = QCheckBox("Moduli di uguale larghezza")
        self.f_nastro_simm.setChecked(True)
        testa_nastro.addRow("", self.f_nastro_simm)
        gruppo_nastro = QGroupBox("Nastro")
        vl_nastro = QVBoxLayout(gruppo_nastro)
        vl_nastro.addLayout(testa_nastro)
        vl_nastro.addWidget(self._box_moduli)

        # ----- Scheda "Ferramenta"
        self.f_maniglia = _combo(MANIGLIE)
        self.f_alt_maniglia = _spin(0, 3000)
        self.f_alt_maniglia.setSpecialValueText("Centro anta")
        self.f_cerniere = _intero(2, 4)
        self.f_col_maniglia = SelettoreColore(COLORI_FERRAMENTA)
        self.f_col_cerniere = SelettoreColore(COLORI_FERRAMENTA)

        ferramenta = QFormLayout()
        ferramenta.addRow("Maniglia", self.f_maniglia)
        ferramenta.addRow("Altezza maniglia", self.f_alt_maniglia)
        ferramenta.addRow("Colore maniglia", self.f_col_maniglia)
        ferramenta.addRow("N. cerniere", self.f_cerniere)
        ferramenta.addRow("Colore cerniere", self.f_col_cerniere)
        gruppo_ferramenta = QGroupBox("Maniglie e cerniere")
        gruppo_ferramenta.setLayout(ferramenta)

        # ----- Scheda "Colori"
        self.f_col_telaio = SelettoreColore(COLORI_SERRAMENTO)
        self.f_col_vetro = SelettoreColore(COLORI_VETRO)
        colori = QFormLayout()
        colori.addRow("Colore telaio", self.f_col_telaio)
        colori.addRow("Colore vetro", self.f_col_vetro)
        gruppo_colori = QGroupBox("Serramento")
        gruppo_colori.setLayout(colori)

        # ----- Scheda "Porta" (visibile solo per il tipo Porta)
        self.f_vetro_porta = _combo(VETRI_PORTA)
        self.f_div_col = _intero(1, 6)
        self.f_div_righe = _intero(1, 10)
        self.f_listello = _spin(10, 150, 0, 5)
        self.f_zoccolo = QCheckBox("Presente")
        self.f_alt_zoccolo = _spin(100, 1500)

        porta = QFormLayout()
        porta.addRow("Vetro", self.f_vetro_porta)
        porta.addRow("Divisioni orizzontali", self.f_div_col)
        porta.addRow("Divisioni verticali", self.f_div_righe)
        porta.addRow("Larghezza listelli", self.f_listello)
        porta.addRow("Zoccolo", self.f_zoccolo)
        porta.addRow("Altezza zoccolo", self.f_alt_zoccolo)
        gruppo_porta = QGroupBox("Specchiature e zoccolo")
        gruppo_porta.setLayout(porta)

        # ----- Schede
        # ----- Scheda "Esportazione"
        self.f_esp_quote = QCheckBox("Includi quote")
        self.f_esp_didascalia = QCheckBox("Includi didascalia")
        b_esp_jpg = QPushButton("Esporta JPG")
        b_esp_jpg.clicked.connect(self.esporta_jpg_dialogo)
        b_esp_pdf = QPushButton("Esporta PDF")
        b_esp_pdf.clicked.connect(self.esporta_pdf_dialogo)
        riga_esp = QHBoxLayout()
        riga_esp.addWidget(b_esp_jpg)
        riga_esp.addWidget(b_esp_pdf)
        esp = QVBoxLayout()
        esp.addWidget(self.f_esp_quote)
        esp.addWidget(self.f_esp_didascalia)
        esp.addSpacing(8)
        esp.addLayout(riga_esp)

        self.f_pagina = _combo(FORMATI_PAGINA)
        self.f_dpi = _combo(RISOLUZIONI_DPI)
        formato = QFormLayout()
        formato.addRow("Formato pagina", self.f_pagina)
        formato.addRow("Risoluzione JPG", self.f_dpi)
        b_batch = QPushButton("Esporta tutti…")
        b_batch.setObjectName("secondario")
        b_batch.clicked.connect(self.esporta_batch_dialogo)
        esp.addSpacing(8)
        esp.addLayout(formato)
        esp.addWidget(b_batch)
        gruppo_esport = QGroupBox("Contenuto del file")
        gruppo_esport.setLayout(esp)

        # Navigazione laterale + pagine a destra: ogni sezione sta nello spazio disponibile
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(200)
        self.stack = QStackedWidget()
        self.stack.setFixedWidth(380)

        # Le opzioni della porta compaiono in fondo alla sezione Dati, solo per il tipo Porta
        self.gruppo_porta = gruppo_porta
        sezioni = [
            ("Dati", [gruppo_dati, gruppo_opzioni, gruppo_porta]),
            ("Apertura", [gruppo_apertura]),
            ("Nastro", [gruppo_nastro]),
            ("Ferramenta", [gruppo_ferramenta]),
            ("Colori", [gruppo_colori]),
            ("Esportazione", [gruppo_esport]),
        ]
        for titolo, gruppi in sezioni:
            self.nav.addItem(titolo)
            self.stack.addWidget(self._pagina(gruppi))
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        layout.addWidget(self.nav, 0)
        layout.addWidget(self.stack, 0)

        # Collegamenti dei campi alla logica di aggiornamento
        for segnale in (self.f_nome.textChanged,
                        self.f_tipo.currentIndexChanged,
                        self.f_forma.currentIndexChanged,
                        self.f_largh.valueChanged,
                        self.f_alt.valueChanged,
                        self.f_sop.toggled,
                        self.f_alt_sop.valueChanged,
                        self.f_apertura.currentIndexChanged,
                        self.f_verso.currentIndexChanged,
                        self.f_anta_princ.currentIndexChanged,
                        self.f_ribalta.toggled,
                        self.f_nastro.toggled,
                        self.f_profilo.currentIndexChanged,
                        self.f_fermavetri.toggled,
                        self.f_quote.toggled,
                        self.f_maniglia.currentIndexChanged,
                        self.f_alt_maniglia.valueChanged,
                        self.f_cerniere.valueChanged,
                        self.f_vetro_porta.currentIndexChanged,
                        self.f_div_col.valueChanged,
                        self.f_div_righe.valueChanged,
                        self.f_listello.valueChanged,
                        self.f_zoccolo.toggled,
                        self.f_alt_zoccolo.valueChanged):
            segnale.connect(self._modificato_form)
        self.f_n_moduli.valueChanged.connect(self._cambio_n_moduli)
        self.f_esp_quote.toggled.connect(self._modificato_form)
        self.f_esp_didascalia.toggled.connect(self._modificato_form)
        self.f_tipo.currentIndexChanged.connect(self._tipo_cambiato)
        self.f_lato_scorr.currentIndexChanged.connect(self._modificato_form)
        self.f_simm.toggled.connect(self._modificato_form)
        self.f_larg_sx.valueChanged.connect(self._modificato_form)
        self.f_nastro_simm.toggled.connect(self._modificato_form)
        self._impostazioni = QSettings("DisegnoFinestre", "Disegno Finestre")
        self.f_pagina.setCurrentIndex(
            max(0, self.f_pagina.findData(str(self._impostazioni.value("pagina", "A4")))))
        self.f_dpi.setCurrentIndex(
            max(0, self.f_dpi.findData(int(self._impostazioni.value("dpi", 300)))))
        self.f_pagina.currentIndexChanged.connect(self._salva_formato)
        self.f_dpi.currentIndexChanged.connect(self._salva_formato)
        for selettore in (self.f_col_maniglia, self.f_col_cerniere,
                          self.f_col_telaio, self.f_col_vetro):
            selettore.cambiato.connect(self._modificato_form)

    def _costruisci_menu(self):
        mb = self.menuBar()

        m_file = mb.addMenu("&File")
        for testo, slot, scorc in (
            ("&Nuovo progetto", self.nuovo_progetto, QKeySequence.StandardKey.New),
            ("&Apri…", self.apri_progetto, QKeySequence.StandardKey.Open),
            ("&Salva", self.salva, QKeySequence.StandardKey.Save),
            ("Salva &con nome…", self.salva_con_nome, QKeySequence.StandardKey.SaveAs),
        ):
            a = QAction(testo, self)
            a.setShortcut(scorc)
            a.triggered.connect(slot)
            m_file.addAction(a)

        m_file.addSeparator()
        for testo, slot in (("Esporta in &JPG…", self.esporta_jpg_dialogo),
                            ("Esporta in &PDF…", self.esporta_pdf_dialogo)):
            a = QAction(testo, self)
            a.triggered.connect(slot)
            m_file.addAction(a)

        m_file.addSeparator()
        a_batch = QAction("Esportazione &multipla…", self)
        a_batch.triggered.connect(self.esporta_batch_dialogo)
        m_file.addAction(a_batch)

        m_file.addSeparator()
        a_esci = QAction("&Esci", self)
        a_esci.setShortcut(QKeySequence.StandardKey.Quit)
        a_esci.triggered.connect(self.close)
        m_file.addAction(a_esci)

        m_aiuto = mb.addMenu("&Aiuto")
        a_guida = QAction("Guida rapida", self)
        a_guida.triggered.connect(lambda: mostra_guida(self))
        m_aiuto.addAction(a_guida)
        m_aiuto.addSeparator()
        a_avvio = QAction("Mostra guida all'avvio", self)
        a_avvio.setCheckable(True)
        a_avvio.setChecked(guida_all_avvio_attiva())
        a_avvio.toggled.connect(imposta_guida_all_avvio)
        m_aiuto.addAction(a_avvio)

        m_prof = mb.addMenu("&Profili")
        a_prof = QAction("Gestisci libreria profili…", self)
        a_prof.triggered.connect(self.gestisci_profili)
        m_prof.addAction(a_prof)

    # ---------- utilità ----------
    def _corrente(self):
        r = self.lista.currentRow()
        return self.progetto.elementi[r] if 0 <= r < len(self.progetto.elementi) else None

    def _profilo_di(self, e: Elemento) -> Profilo:
        return self.libreria.trova(e.profilo)

    def _profilo_predefinito(self) -> str:
        nomi = self.libreria.nomi()
        return nomi[0] if nomi else "Predefinito"

    @staticmethod
    def _etichetta(e: Elemento) -> str:
        extra = f"  –  nastro {len(e.moduli)} moduli" if e.nastro else ""
        return f"{e.nome}  –  {e.larghezza:.0f} × {e.altezza:.0f}{extra}"

    def _segna_modificato(self):
        self.modificato = True
        self._aggiorna_titolo()

    def _aggiorna_titolo(self):
        nome = Path(self.file_corrente).name if self.file_corrente else "Senza titolo"
        asterisco = "*" if self.modificato else ""
        self.setWindowTitle(f"{asterisco}{nome} – WCad")

    # ---------- moduli del nastro ----------
    def _ricostruisci_combo_moduli(self, valori, larghezze):
        """Crea una riga per ogni modulo: apertura e larghezza (Auto = automatica)."""
        while self._layout_moduli.count():
            voce = self._layout_moduli.takeAt(0)
            if voce.widget():
                voce.widget().deleteLater()
        self.f_mod_combos = []
        self.f_mod_larg = []
        for i, v in enumerate(valori):
            riga = QWidget()
            rl = QHBoxLayout(riga)
            rl.setContentsMargins(0, 0, 0, 0)
            etichetta = QLabel(f"Modulo {i + 1}")
            etichetta.setFixedWidth(72)
            c = _combo(MODULI)
            c.setCurrentIndex(max(0, c.findData(v)))
            c.currentIndexChanged.connect(self._modificato_form)
            larg = _spin(0, 3000)
            larg.setSpecialValueText("Auto")
            larg.setValue(larghezze[i] if i < len(larghezze) else 0.0)
            larg.valueChanged.connect(self._modificato_form)
            rl.addWidget(etichetta)
            rl.addWidget(c, 1)
            rl.addWidget(larg)
            self._layout_moduli.addWidget(riga)
            self.f_mod_combos.append(c)
            self.f_mod_larg.append(larg)

    def _cambio_n_moduli(self, *_):
        """L'utente ha cambiato il numero di moduli: aggiunge o toglie righe."""
        if self._caricamento:
            return
        e = self._corrente()
        if e is None:
            return
        n = self.f_n_moduli.value()
        valori = (list(e.moduli) + ["fisso"] * n)[:n]
        larghezze = (list(e.larghezze_moduli) + [0.0] * n)[:n]
        self._ricostruisci_combo_moduli(valori, larghezze)
        self._modificato_form()

    # ---------- sincronizzazione lista / form / anteprima ----------
    def _aggiorna_lista(self, riga=0):
        self.lista.blockSignals(True)
        self.lista.clear()
        for e in self.progetto.elementi:
            self.lista.addItem(self._etichetta(e))
        self.lista.setCurrentRow(max(0, min(riga, len(self.progetto.elementi) - 1)))
        self.lista.blockSignals(False)
        self._seleziona(self.lista.currentRow())

    def _seleziona(self, _riga=None):
        e = self._corrente()
        if e is not None:
            self._carica_form(e)
        self._aggiorna_anteprima()

    def _riempi_profili(self, selezionato: str):
        self.f_profilo.blockSignals(True)
        self.f_profilo.clear()
        self.f_profilo.addItems(self.libreria.nomi())
        i = self.f_profilo.findText(selezionato)
        if i >= 0:
            self.f_profilo.setCurrentIndex(i)
        self.f_profilo.blockSignals(False)

    def _carica_form(self, e: Elemento):
        self._caricamento = True
        self.f_nome.setText(e.nome)
        self.f_tipo.setCurrentIndex(max(0, self.f_tipo.findData(e.tipo)))
        self.f_forma.setCurrentIndex(max(0, self.f_forma.findData(e.forma)))
        self.f_largh.setValue(e.larghezza)
        self.f_alt.setValue(e.altezza)
        self.f_sop.setChecked(e.sopraluce)
        self.f_alt_sop.setValue(e.altezza_sopraluce)
        self.f_apertura.setCurrentIndex(max(0, self.f_apertura.findData(e.apertura)))
        self.f_verso.setCurrentIndex(max(0, self.f_verso.findData(e.verso)))
        self.f_anta_princ.setCurrentIndex(max(0, self.f_anta_princ.findData(e.anta_principale)))
        self.f_lato_scorr.setCurrentIndex(max(0, self.f_lato_scorr.findData(e.lato_scorrevole)))
        self.f_ribalta.setChecked(e.anta_ribalta)
        self.f_nastro.setChecked(e.nastro)
        self.f_n_moduli.blockSignals(True)
        self.f_n_moduli.setValue(len(e.moduli))
        self.f_n_moduli.blockSignals(False)
        self._ricostruisci_combo_moduli(e.moduli, e.larghezze_moduli)
        self.f_nastro_simm.setChecked(e.nastro_simmetrico)
        self.f_simm.setChecked(e.doppia_simmetrica)
        self.f_larg_sx.setValue(e.larghezza_anta_sx)
        self._riempi_profili(e.profilo)
        self.f_fermavetri.setChecked(e.fermavetri)
        self.f_quote.setChecked(e.mostra_quote)
        self.f_esp_quote.setChecked(e.esp_quote)
        self.f_esp_didascalia.setChecked(e.esp_didascalia)
        self.f_maniglia.setCurrentIndex(max(0, self.f_maniglia.findData(e.maniglia)))
        self.f_alt_maniglia.setValue(e.altezza_maniglia)
        self.f_col_maniglia.imposta(e.colore_maniglia)
        self.f_cerniere.setValue(e.numero_cerniere)
        self.f_col_cerniere.imposta(e.colore_cerniere)
        self.f_col_telaio.imposta(e.colore_telaio)
        self.f_col_vetro.imposta(e.colore_vetro)
        self.f_vetro_porta.setCurrentIndex(max(0, self.f_vetro_porta.findData(e.vetro_porta)))
        self.f_div_col.setValue(e.divisioni_colonne)
        self.f_div_righe.setValue(e.divisioni_righe)
        self.f_listello.setValue(e.larghezza_listello)
        self.f_zoccolo.setChecked(e.zoccolo)
        self.f_alt_zoccolo.setValue(e.altezza_zoccolo)
        self._caricamento = False
        self._aggiorna_visibilita()

    def _aggiorna_visibilita(self):
        # scheda Porta visibile solo per il tipo Porta
        self.gruppo_porta.setVisible(self.f_tipo.currentData() == "porta")
        multiplo = self.f_vetro_porta.currentData() == "multiplo"
        self.f_div_col.setEnabled(multiplo)
        self.f_div_righe.setEnabled(multiplo)
        self.f_listello.setEnabled(multiplo)
        self.f_alt_zoccolo.setEnabled(self.f_zoccolo.isChecked())

        # Nastro: i moduli sostituiscono l'apertura singola
        nastro = self.f_nastro.isChecked()
        self.f_n_moduli.setEnabled(nastro)
        self._box_moduli.setVisible(nastro)
        if nastro and self.f_forma.currentData() != "rettangolare":
            self.f_forma.blockSignals(True)
            self.f_forma.setCurrentIndex(self.f_forma.findData("rettangolare"))
            self.f_forma.blockSignals(False)
        self.f_forma.setEnabled(not nastro)

        # Forme curve: sopraluce e doppia anta solo per le forme rettangolari;
        # la tonda non ha la ribalta; le aperture curve sono fisso o a battente
        rett = self.f_forma.currentData() == "rettangolare" or nastro
        tonda = self.f_forma.currentData() == "tonda"
        if rett:
            self._abilita_voci_apertura(None)
        else:
            self._abilita_voci_apertura(("fisso", "battente-sx", "battente-dx"))
        apertura = self.f_apertura.currentData()
        apribile = nastro or apertura != "fisso"
        self.f_apertura.setEnabled(not nastro)
        self.f_sop.setEnabled(rett)
        self.f_alt_sop.setEnabled(rett and self.f_sop.isChecked())
        self.f_verso.setEnabled(apribile)
        self.f_anta_princ.setEnabled(rett and not nastro and apertura == "doppia-anta")
        self.f_ribalta.setEnabled(not nastro and not tonda
                                  and apertura in ("battente-sx", "battente-dx", "doppia-anta",
                                                   "scorrevole-1", "scorrevole-2"))
        self.f_maniglia.setEnabled(apribile)
        self.f_alt_maniglia.setEnabled(apribile and self.f_maniglia.currentData() != "nessuna")
        self.f_cerniere.setEnabled(apribile)
        self.f_col_cerniere.setEnabled(apribile)

        doppia = rett and not nastro and apertura == "doppia-anta"
        self.f_simm.setEnabled(doppia)
        self.f_larg_sx.setEnabled(doppia and not self.f_simm.isChecked())
        self.f_nastro_simm.setEnabled(nastro)
        for s in self.f_mod_larg:
            s.setEnabled(nastro and not self.f_nastro_simm.isChecked())

        # Scorrevoli: niente cerniere né verso; il lato si sceglie solo per scorrevole + fisso
        scorrevole = apertura in ("scorrevole-1", "scorrevole-2") and not nastro
        self.f_lato_scorr.setEnabled(apertura == "scorrevole-2" and not nastro)
        con_cerniere = apribile and (not scorrevole or self.f_ribalta.isChecked())
        self.f_verso.setEnabled(con_cerniere)
        self.f_cerniere.setEnabled(con_cerniere)
        self.f_col_cerniere.setEnabled(con_cerniere)
        self.f_ribalta.setText("Anche vasistas" if scorrevole else "Anta ribalta")

    def _tipo_cambiato(self, *_):
        """Quando l'utente sceglie il tipo, imposta le dimensioni tipiche."""
        if self._caricamento:
            return
        dimensioni = DIMENSIONI_TIPO.get(self.f_tipo.currentData())
        if dimensioni:
            larghezza, altezza = dimensioni
            self.f_largh.setValue(larghezza)
            self.f_alt.setValue(altezza)

    def _salva_formato(self, *_):
        self._impostazioni.setValue("pagina", self.f_pagina.currentData())
        self._impostazioni.setValue("dpi", self.f_dpi.currentData())

    def _abilita_voci_apertura(self, consentite):
        """Con le forme curve sono selezionabili solo le aperture compatibili."""
        modello = self.f_apertura.model()
        for i in range(self.f_apertura.count()):
            voce = self.f_apertura.itemData(i)
            modello.item(i).setEnabled(consentite is None or voce in consentite)
        if consentite is not None and self.f_apertura.currentData() not in consentite:
            self.f_apertura.blockSignals(True)
            self.f_apertura.setCurrentIndex(self.f_apertura.findData("fisso"))
            self.f_apertura.blockSignals(False)

    def _aggiorna_anteprima(self):
        e = self._corrente()
        self.anteprima.mostra(e, self._profilo_di(e) if e else None)

    def _modificato_form(self, *_):
        if self._caricamento:
            return
        e = self._corrente()
        if e is None:
            return
        e.nome = self.f_nome.text().strip() or "Senza nome"
        e.tipo = self.f_tipo.currentData()
        e.nastro = self.f_nastro.isChecked()
        e.forma = "rettangolare" if e.nastro else self.f_forma.currentData()
        e.larghezza = self.f_largh.value()
        e.altezza = self.f_alt.value()
        e.sopraluce = self.f_sop.isChecked()
        e.altezza_sopraluce = self.f_alt_sop.value()
        e.apertura = self.f_apertura.currentData()
        e.verso = self.f_verso.currentData()
        e.anta_principale = self.f_anta_princ.currentData()
        e.anta_ribalta = self.f_ribalta.isChecked()
        e.lato_scorrevole = self.f_lato_scorr.currentData()
        if self.f_mod_combos:
            e.moduli = [c.currentData() for c in self.f_mod_combos]
            e.larghezze_moduli = [s.value() for s in self.f_mod_larg]
        e.nastro_simmetrico = self.f_nastro_simm.isChecked()
        e.doppia_simmetrica = self.f_simm.isChecked()
        e.larghezza_anta_sx = self.f_larg_sx.value()
        if self.f_profilo.currentText():
            e.profilo = self.f_profilo.currentText()
        e.fermavetri = self.f_fermavetri.isChecked()
        e.mostra_quote = self.f_quote.isChecked()
        e.esp_quote = self.f_esp_quote.isChecked()
        e.esp_didascalia = self.f_esp_didascalia.isChecked()
        e.maniglia = self.f_maniglia.currentData()
        e.altezza_maniglia = self.f_alt_maniglia.value()
        e.colore_maniglia = self.f_col_maniglia.colore()
        e.numero_cerniere = self.f_cerniere.value()
        e.colore_cerniere = self.f_col_cerniere.colore()
        e.colore_telaio = self.f_col_telaio.colore()
        e.colore_vetro = self.f_col_vetro.colore()
        e.vetro_porta = self.f_vetro_porta.currentData()
        e.divisioni_colonne = self.f_div_col.value()
        e.divisioni_righe = self.f_div_righe.value()
        e.larghezza_listello = self.f_listello.value()
        e.zoccolo = self.f_zoccolo.isChecked()
        e.altezza_zoccolo = self.f_alt_zoccolo.value()

        self._aggiorna_visibilita()
        item = self.lista.item(self.lista.currentRow())
        if item:
            item.setText(self._etichetta(e))
        self._segna_modificato()
        self._aggiorna_anteprima()

    # ---------- gestione elementi ----------
    def nuovo_elemento(self):
        n = len(self.progetto.elementi) + 1
        self.progetto.elementi.append(Elemento(nome=f"Finestra {n}",
                                               profilo=self._profilo_predefinito()))
        self._segna_modificato()
        self._aggiorna_lista(len(self.progetto.elementi) - 1)

    def duplica_elemento(self):
        e = self._corrente()
        if e is None:
            return
        riga = self.lista.currentRow()
        copia = replace(e, nome=e.nome + " (copia)", moduli=list(e.moduli),
                        larghezze_moduli=list(e.larghezze_moduli))
        self.progetto.elementi.insert(riga + 1, copia)
        self._segna_modificato()
        self._aggiorna_lista(riga + 1)

    def elimina_elemento(self):
        if len(self.progetto.elementi) <= 1:
            QMessageBox.information(self, "Attenzione",
                                    "Il progetto deve contenere almeno un elemento.")
            return
        riga = self.lista.currentRow()
        del self.progetto.elementi[riga]
        self._segna_modificato()
        self._aggiorna_lista(max(0, riga - 1))

    # ---------- progetto: nuovo / apri / salva ----------
    def _controlla_modifiche(self) -> bool:
        """Chiede di salvare le modifiche. Ritorna False se l'utente annulla."""
        if not self.modificato:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Progetto modificato")
        box.setText("Vuoi salvare le modifiche al progetto?")
        b_salva = box.addButton("Salva", QMessageBox.ButtonRole.AcceptRole)
        b_scarta = box.addButton("Non salvare", QMessageBox.ButtonRole.DestructiveRole)
        b_annulla = box.addButton("Annulla", QMessageBox.ButtonRole.RejectRole)
        for b in (b_salva, b_scarta, b_annulla):
            b.setMinimumWidth(120)
        box.setMinimumWidth(400)
        box.setDefaultButton(b_salva)
        box.exec()
        scelta = box.clickedButton()
        if scelta is b_salva:
            return self.salva()
        if scelta is b_scarta:
            return True
        return False

    def nuovo_progetto(self):
        if not self._controlla_modifiche():
            return
        self.progetto = Progetto(elementi=[
            Elemento(nome="Finestra 1", profilo=self._profilo_predefinito())
        ])
        self.file_corrente = None
        self.modificato = False
        self._aggiorna_lista(0)
        self._aggiorna_titolo()

    def apri_progetto(self):
        if not self._controlla_modifiche():
            return
        percorso, _ = QFileDialog.getOpenFileName(
            self, "Apri progetto", "",
            f"Progetto Disegno Finestre (*{ESTENSIONE_PROGETTO})")
        if not percorso:
            return
        try:
            progetto = leggi_progetto(percorso)
        except (OSError, ValueError, TypeError) as err:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il progetto:\n{err}")
            return
        if not progetto.elementi:
            progetto.elementi.append(Elemento(nome="Finestra 1",
                                              profilo=self._profilo_predefinito()))
        self.progetto = progetto
        self.file_corrente = percorso
        self.modificato = False
        self._aggiorna_lista(0)
        self._aggiorna_titolo()

    def salva(self) -> bool:
        if self.file_corrente is None:
            return self.salva_con_nome()
        return self._scrivi(self.file_corrente)

    def salva_con_nome(self) -> bool:
        percorso, _ = QFileDialog.getSaveFileName(
            self, "Salva progetto", "progetto" + ESTENSIONE_PROGETTO,
            f"Progetto Disegno Finestre (*{ESTENSIONE_PROGETTO})")
        if not percorso:
            return False
        if not percorso.lower().endswith(ESTENSIONE_PROGETTO):
            percorso += ESTENSIONE_PROGETTO
        return self._scrivi(percorso)

    def _scrivi(self, percorso: str) -> bool:
        try:
            scrivi_progetto(percorso, self.progetto)
        except OSError as err:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare il progetto:\n{err}")
            return False
        self.file_corrente = percorso
        self.modificato = False
        self._aggiorna_titolo()
        return True

    # ---------- esportazione ----------
    def esporta_jpg_dialogo(self):
        e = self._corrente()
        if e is None:
            return
        con_quote, con_did = e.esp_quote, e.esp_didascalia
        percorso, _ = QFileDialog.getSaveFileName(
            self, "Esporta in JPG", f"{e.nome}.jpg", "Immagine JPG (*.jpg)")
        if not percorso:
            return
        if not percorso.lower().endswith((".jpg", ".jpeg")):
            percorso += ".jpg"
        try:
            esporta_jpg(percorso, e, self._profilo_di(e), con_quote, con_did,
                        self.f_pagina.currentData(), int(self.f_dpi.currentData()))
        except OSError as err:
            QMessageBox.critical(self, "Errore", f"Esportazione non riuscita:\n{err}")

    def esporta_pdf_dialogo(self):
        e = self._corrente()
        if e is None:
            return
        con_quote, con_did = e.esp_quote, e.esp_didascalia
        percorso, _ = QFileDialog.getSaveFileName(
            self, "Esporta in PDF", f"{e.nome}.pdf", "Documento PDF (*.pdf)")
        if not percorso:
            return
        if not percorso.lower().endswith(".pdf"):
            percorso += ".pdf"
        try:
            esporta_pdf(percorso, e, self._profilo_di(e), con_quote, con_did,
                        self.f_pagina.currentData())
        except OSError as err:
            QMessageBox.critical(self, "Errore", f"Esportazione non riuscita:\n{err}")

    def esporta_batch_dialogo(self):
        if not self.progetto.elementi:
            return
        dialogo = BatchDialog(self.progetto.elementi, self)
        if not dialogo.exec():
            return
        elementi = dialogo.selezionati()
        if not elementi:
            QMessageBox.information(self, "Esportazione multipla",
                                    "Seleziona almeno un elemento.")
            return
        cartella = QFileDialog.getExistingDirectory(self, "Scegli la cartella di destinazione")
        if not cartella:
            return
        titolo = Path(self.file_corrente).stem if self.file_corrente else "Serramenti"
        creati, errori = esporta_batch(
            elementi, self._profilo_di, self.f_pagina.currentData(),
            int(self.f_dpi.currentData()), dialogo.modalita(), Path(cartella),
            titolo, dialogo.con_quote(), dialogo.con_didascalia(), self)
        testo = f"Esportati {len(creati)} file in:\n{cartella}"
        if errori:
            testo += "\n\nErrori:\n" + "\n".join(errori)
        QMessageBox.information(self, "Esportazione multipla", testo)

    # ---------- libreria profili ----------
    def gestisci_profili(self):
        dialogo = GestioneProfiliDialog(self.libreria, self)
        dialogo.exec()
        if not dialogo.modificato:
            return

        nomi = self.libreria.nomi()
        for e in self.progetto.elementi:
            e.profilo = dialogo.rinominati.get(e.profilo, e.profilo)
            if nomi and e.profilo not in nomi:
                e.profilo = nomi[0]

        self._seleziona()
        self._segna_modificato()

    # ---------- chiusura ----------
    def closeEvent(self, event):
        if self._controlla_modifiche():
            event.accept()
        else:
            event.ignore()
