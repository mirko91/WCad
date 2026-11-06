"""Modelli dati, salvataggio progetto e libreria profili."""
import json
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path

CARTELLA_DATI = Path.home() / ".disegno_finestre"
FILE_PROFILI = CARTELLA_DATI / "profili.json"
ESTENSIONE_PROGETTO = ".dfp"

TIPI = {
    "finestra": "Finestra",
    "portafinestra": "Portafinestra",
    "porta": "Porta",
}

FORME = {
    "rettangolare": "Rettangolare",
    "arco_tondo": "Arco a tutto sesto",
    "arco_ribassato": "Arco ribassato",
    "tondo": "Tonda",
}

APERTURE = {
    "fisso": "Fisso",
    "battente-sx": "Battente, cerniere sx",
    "battente-dx": "Battente, cerniere dx",
    "doppia-anta": "Doppia anta",
    "ribalta": "Ribalta (vasistas)",
    "scorrevole-1": "Scorrevole, 1 anta",
    "scorrevole-2": "Scorrevole + fisso",
}

# Apertura di ciascun modulo di un nastro
MODULI = {
    "fisso": "Fisso",
    "battente-sx": "Battente sx",
    "battente-dx": "Battente dx",
    "battente-sx-ribalta": "Battente sx + ribalta",
    "battente-dx-ribalta": "Battente dx + ribalta",
    "vasistas": "Vasistas",
    "scorrevole": "Scorrevole",
}

VERSI = {
    "interno": "Interno (linea continua)",
    "esterno": "Esterno (linea tratteggiata)",
}

MANIGLIE = {
    "nessuna": "Nessuna",
    "maniglia": "Maniglia a leva",
    "maniglione": "Maniglione (barra)",
}

ANTE_PRINCIPALI = {
    "sinistra": "Sinistra",
    "destra": "Destra",
}

VETRI_PORTA = {
    "singolo": "Singolo",
    "multiplo": "Multiplo (con listelli)",
}

# Dimensioni predefinite quando si sceglie il tipo: (larghezza, altezza) in mm
DIMENSIONI_TIPO = {
    "finestra": (1200, 1400),
    "portafinestra": (700, 2000),
    "porta": (900, 2100),
}

FORMATI_PAGINA = {
    "A4": "A4 orizzontale",
    "A3": "A3 orizzontale",
    "A5": "A5 orizzontale",
}

RISOLUZIONI_DPI = {
    150: "150 dpi (anteprima)",
    300: "300 dpi (stampa)",
    600: "600 dpi (alta qualità)",
}

# Palette: (nome, colore esadecimale). I colori sono indicativi a schermo.
COLORI_SERRAMENTO = [
    ("RAL 9016 Bianco traffico", "#f6f6f6"),
    ("RAL 9010 Bianco puro", "#f1ece1"),
    ("RAL 9001 Bianco crema", "#ece6d7"),
    ("RAL 9002 Bianco grigiastro", "#d7d7d0"),
    ("RAL 9003 Bianco segnale", "#ecebe3"),
    ("RAL 9006 Alluminio bianco", "#a5a5a5"),
    ("RAL 9007 Alluminio grigio", "#8f8b84"),
    ("RAL 7044 Grigio seta", "#cac4b0"),
    ("RAL 7035 Grigio luce", "#c5c7c4"),
    ("RAL 7032 Grigio ghiaia", "#b8b799"),
    ("RAL 7038 Grigio agata", "#b5b8b1"),
    ("RAL 7040 Grigio finestra", "#9da1aa"),
    ("RAL 7037 Grigio polvere", "#7d7f7d"),
    ("RAL 7042 Grigio traffico A", "#8e9291"),
    ("RAL 7024 Grigio grafite", "#474a51"),
    ("RAL 7043 Grigio traffico B", "#4e5452"),
    ("RAL 7016 Grigio antracite", "#383e42"),
    ("RAL 7021 Grigio nero", "#2e3234"),
    ("RAL 9005 Nero intenso", "#0e0e10"),
    ("RAL 9011 Nero grafite", "#1d1d21"),
    ("RAL 8017 Marrone cioccolato", "#45322e"),
    ("RAL 8014 Marrone seppia", "#4a3b31"),
    ("RAL 8016 Marrone mogano", "#4c2f27"),
    ("RAL 8011 Marrone noce", "#5b3a29"),
    ("RAL 8028 Marrone terra", "#4e3b31"),
    ("RAL 8001 Ocra bruna", "#9d622b"),
    ("Effetto noce chiaro", "#a47149"),
    ("Effetto noce scuro", "#5c3d2e"),
    ("RAL 1015 Avorio chiaro", "#e6d2b5"),
    ("RAL 1001 Beige", "#d0b084"),
    ("RAL 6005 Verde muschio", "#2f4538"),
    ("RAL 6009 Verde abete", "#27382b"),
    ("RAL 6021 Verde pallido", "#8a9a7b"),
    ("RAL 5010 Blu genziana", "#0e4c7a"),
    ("RAL 5003 Blu zaffiro", "#1e2a5a"),
    ("RAL 3000 Rosso fuoco", "#a72920"),
    ("RAL 3005 Rosso vino", "#5e2129"),
]

COLORI_VETRO = [
    ("Trasparente", "#cfe8ff"),
    ("Extrachiaro", "#e8f4f8"),
    ("Satinato", "#e6eef0"),
    ("Bronzo", "#8a7560"),
    ("Grigio fumé", "#6b7178"),
    ("Verde", "#b7d4c0"),
    ("Blu riflettente", "#5b7a96"),
]

COLORI_FERRAMENTA = [
    ("Argento", "#c0c4c8"),
    ("Cromo lucido", "#e3e6e9"),
    ("Acciaio inox", "#aab2b8"),
    ("Ottone", "#b5975a"),
    ("Oro spazzolato", "#c9a86a"),
    ("Nero opaco", "#1e1e1e"),
    ("Bronzo", "#6e5a43"),
    ("Bianco", "#f4f4f4"),
]


@dataclass
class Profilo:
    nome: str
    spessore_telaio: float = 70.0   # mm
    spessore_anta: float = 60.0     # mm


PROFILI_PREDEFINITI = [
    Profilo("PVC 70 mm", 70, 60),
    Profilo("PVC 85 mm", 85, 70),
    Profilo("Alluminio 60 mm", 60, 50),
    Profilo("Legno 80 mm", 80, 65),
]


class LibreriaProfili:
    """Libreria dei profili, salvata in un file JSON nella cartella utente."""

    def __init__(self, file=FILE_PROFILI):
        self.file = Path(file)
        self.profili: list[Profilo] = []
        self._carica()

    def _carica(self):
        if self.file.exists():
            dati = json.loads(self.file.read_text(encoding="utf-8"))
            self.profili = [Profilo(**d) for d in dati]
        else:
            self.profili = [Profilo(**asdict(p)) for p in PROFILI_PREDEFINITI]
            self.salva()

    def salva(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        dati = [asdict(p) for p in self.profili]
        self.file.write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")

    def nomi(self) -> list[str]:
        return [p.nome for p in self.profili]

    def trova(self, nome: str) -> Profilo:
        for p in self.profili:
            if p.nome == nome:
                return p
        return self.profili[0] if self.profili else Profilo("Predefinito")


@dataclass
class Elemento:
    """Una singola finestra, portafinestra, porta o nastro di serramenti."""
    nome: str = "Finestra 1"
    tipo: str = "finestra"
    forma: str = "rettangolare"          # rettangolare, arco_tondo, arco_ribassato, tondo
    larghezza: float = 1200.0
    altezza: float = 1400.0
    sopraluce: bool = False
    altezza_sopraluce: float = 400.0
    apertura: str = "battente-sx"
    verso: str = "interno"
    anta_principale: str = "sinistra"   # solo doppia anta: quale anta ha la maniglia
    anta_ribalta: bool = False          # anta ribaltabile (battente o anta principale)
    # nastro: più moduli affiancati, ognuno fisso o a battente
    nastro: bool = False
    moduli: list = field(default_factory=lambda: ["battente-sx", "fisso", "battente-dx"])
    nastro_simmetrico: bool = True      # moduli di uguale larghezza
    larghezze_moduli: list = field(default_factory=list)   # mm per modulo; 0 = automatica
    lato_scorrevole: str = "destra"     # scorrevole + fisso: lato dell'anta scorrevole
    doppia_simmetrica: bool = True      # doppia anta con due ante uguali
    larghezza_anta_sx: float = 0.0      # mm dell'anta sinistra; 0 = automatica
    profilo: str = "PVC 70 mm"
    colore_telaio: str = "#f6f6f6"
    colore_vetro: str = "#cfe8ff"
    fermavetri: bool = True             # mostra i fermavetri intorno al vetro
    mostra_quote: bool = True           # quote nell'anteprima
    esp_quote: bool = True              # includi le quote nell'esportazione
    esp_didascalia: bool = True         # includi la didascalia nell'esportazione
    # ferramenta
    maniglia: str = "maniglia"
    altezza_maniglia: float = 0.0       # altezza da terra (mm); 0 = centro dell'anta
    colore_maniglia: str = "#c0c4c8"
    numero_cerniere: int = 2
    colore_cerniere: str = "#c0c4c8"
    # solo porta
    vetro_porta: str = "singolo"
    divisioni_colonne: int = 2
    divisioni_righe: int = 3
    larghezza_listello: float = 40.0    # spessore dei listelli tra le specchiature (mm)
    zoccolo: bool = False
    altezza_zoccolo: float = 300.0


@dataclass
class Progetto:
    nome: str = "Nuovo progetto"
    elementi: list = field(default_factory=list)


def salva_progetto(percorso, progetto: Progetto):
    dati = {
        "versione": 5,
        "nome": progetto.nome,
        "elementi": [asdict(e) for e in progetto.elementi],
    }
    Path(percorso).write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")


def _elemento_da_dizionario(d: dict) -> Elemento:
    """Crea un Elemento ignorando campi sconosciuti, così i file vecchi e nuovi si aprono sempre."""
    campi = {f.name for f in fields(Elemento)}
    return Elemento(**{k: v for k, v in d.items() if k in campi})


def apri_progetto(percorso) -> Progetto:
    dati = json.loads(Path(percorso).read_text(encoding="utf-8"))
    elementi = [_elemento_da_dizionario(e) for e in dati.get("elementi", [])]
    return Progetto(nome=dati.get("nome", "Progetto"), elementi=elementi)
