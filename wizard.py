"""Guida rapida in forma di wizard: si apre all'avvio e dal menu Aiuto.
All'avvio compare finché l'utente non sceglie «Non mostrare più all'avvio»."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWizard, QWizardPage

from modelli import CARTELLA_DATI

FILE_NASCOSTA = CARTELLA_DATI / "guida_nascosta"

# (titolo, sottotitolo, testo in HTML)
PAGINE = [
    (
        "Benvenuto",
        "Disegno di serramenti quotati",
        "Con questa applicazione disegni finestre, portefinestre e porte, "
        "le quoti e le esporti in JPG o PDF.<br><br>"
        "<b>Elenco a sinistra:</b> gli elementi del progetto.<br>"
        "<b>Anteprima al centro:</b> il disegno dell'elemento selezionato.<br>"
        "<b>Sezioni a destra:</b> tutti i parametri, divisi per argomento.",
    ),
    (
        "Dati e forma",
        "Dimensioni, sopraluce e profilo",
        "Nella sezione <b>Dati</b> imposti tipo, forma, larghezza, altezza, "
        "sopraluce e profilo di telaio e anta.<br><br>"
        "La <b>forma</b> può essere rettangolare, ad arco a tutto sesto, ad arco "
        "ribassato o tonda. Le forme ad arco e tonde possono essere fisse oppure a "
        "battente, con cerniere a sinistra o a destra. Doppia anta, sopraluce e nastro "
        "sono disponibili solo per le forme rettangolari.",
    ),
    (
        "Apertura",
        "Come si apre il serramento",
        "Nella sezione <b>Apertura</b> scegli fisso, <b>scorrevole</b> (una sola anta, oppure "
        "un'anta scorrevole affiancata a un'anta fissa), battente con cerniere a sinistra "
        "o a destra, doppia anta oppure ribalta (vasistas).<br><br>"
        "Nella doppia anta indichi l'<b>anta principale</b>, quella che porta la maniglia. "
        "Togli la spunta <b>Doppia anta simmetrica</b> per digitare la larghezza dell'anta sinistra. "
        "<b>Anta ribalta</b> aggiunge il simbolo di ribalta. Il <b>verso</b> distingue "
        "l'apertura verso l'interno (linea continua) da quella verso l'esterno (tratteggiata).",
    ),
    (
        "Nastro",
        "Più moduli affiancati",
        "Un <b>nastro</b> è una serie di moduli affiancati, separati da un montante del telaio.<br><br>"
        "Attiva il nastro e scegli il numero di moduli. Ogni modulo può essere "
        "<b>fisso</b>, a battente con cerniere a sinistra o a destra, a battente "
        "con <b>anta ribalta</b> oppure <b>vasistas</b>.",
    ),
    (
        "Ferramenta e colori",
        "Maniglia, cerniere e finiture",
        "Nella sezione <b>Ferramenta</b> scegli maniglia a leva o maniglione, colore e "
        "numero di cerniere. L'<b>altezza della maniglia</b> è predefinita al centro "
        "dell'anta: inserisci un valore per fissarla da terra.<br><br>"
        "Nella sezione <b>Colori</b> scegli telaio e vetro dalla mazzetta RAL, "
        "oppure un colore personalizzato.",
    ),
    (
        "Porta",
        "Specchiature e zoccolo",
        "Quando il tipo è Porta, nella sezione <b>Dati</b> compaiono le opzioni della porta. Puoi scegliere "
        "il vetro singolo o multiplo, con listelli di larghezza regolabile, e aggiungere "
        "uno <b>zoccolo</b> in basso con altezza impostabile.",
    ),
    (
        "Esportazione",
        "Quote, didascalia e formati",
        "Nella sezione <b>Esportazione</b> decidi, per ogni elemento, se includere le "
        "<b>quote</b> e la <b>didascalia</b> in alto alla pagina.<br><br>"
        "Scegli il formato di pagina (A4, A3 o A5) e la risoluzione JPG (150, 300 o 600 dpi). "
        "Con <i>Esporta tutti</i> o dal menu <i>File</i> esporti più elementi in una volta, "
        "in file separati o in un unico PDF.",
    ),
    (
        "Progetti e profili",
        "Salvataggio e libreria",
        "Il <b>progetto</b> si salva in un file .dfp da riaprire in seguito, dal menu <i>File</i>."
        "<br><br>I <b>profili</b> (spessori di telaio e anta) si gestiscono da "
        "<i>Profili → Gestisci libreria profili</i>.<br><br>"
        "Puoi riaprire questa guida in ogni momento da <i>Aiuto → Guida rapida</i>.",
    ),
]


def _pagina(titolo: str, sottotitolo: str, testo: str) -> QWizardPage:
    pagina = QWizardPage()
    pagina.setTitle(titolo)
    pagina.setSubTitle(sottotitolo)
    etichetta = QLabel(testo)
    etichetta.setWordWrap(True)
    etichetta.setTextFormat(Qt.TextFormat.RichText)
    etichetta.setAlignment(Qt.AlignmentFlag.AlignTop)
    layout = QVBoxLayout(pagina)
    layout.addWidget(etichetta)
    layout.addStretch()
    return pagina


class GuidaRapida(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guida rapida")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.WizardButton.NextButton, "Avanti")
        self.setButtonText(QWizard.WizardButton.BackButton, "Indietro")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Fine")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Chiudi")
        for pulsante in (QWizard.WizardButton.NextButton, QWizard.WizardButton.BackButton,
                         QWizard.WizardButton.FinishButton, QWizard.WizardButton.CancelButton):
            self.button(pulsante).setMinimumWidth(104)
        self.resize(600, 460)

        for titolo, sottotitolo, testo in PAGINE:
            self.addPage(_pagina(titolo, sottotitolo, testo))

        # Casella «Non mostrare più» a sinistra della barra dei pulsanti
        self.non_mostrare = QCheckBox("Non mostrare più all'avvio")
        self.non_mostrare.setChecked(FILE_NASCOSTA.exists())
        self.setOption(QWizard.WizardOption.HaveCustomButton1, True)
        self.setButton(QWizard.WizardButton.CustomButton1, self.non_mostrare)
        self.setButtonLayout([
            QWizard.WizardButton.CustomButton1,
            QWizard.WizardButton.Stretch,
            QWizard.WizardButton.BackButton,
            QWizard.WizardButton.NextButton,
            QWizard.WizardButton.FinishButton,
            QWizard.WizardButton.CancelButton,
        ])


def mostra_guida(parent=None):
    """Apre la guida dal menu Aiuto. Se l'utente sceglie di non vederla più, lo ricorda."""
    guida = GuidaRapida(parent)
    guida.exec()
    _ricorda_scelta(guida)


def guida_all_avvio(parent=None):
    """All'avvio mostra la guida, a meno che l'utente non l'abbia nascosta.
    Compare dopo che la finestra è visibile."""
    if FILE_NASCOSTA.exists():
        return
    QTimer.singleShot(400, lambda: mostra_guida(parent))


def guida_all_avvio_attiva() -> bool:
    """True se la guida deve comparire all'avvio."""
    return not FILE_NASCOSTA.exists()


def imposta_guida_all_avvio(attiva: bool):
    """Attiva o disattiva la guida all'avvio (voce del menu Aiuto)."""
    try:
        if attiva:
            FILE_NASCOSTA.unlink(missing_ok=True)
        else:
            FILE_NASCOSTA.parent.mkdir(parents=True, exist_ok=True)
            FILE_NASCOSTA.write_text("ok", encoding="utf-8")
    except OSError:
        pass


def _ricorda_scelta(guida: GuidaRapida):
    imposta_guida_all_avvio(not guida.non_mostrare.isChecked())
