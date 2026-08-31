import re
import unicodedata


TRADUCCIONES_ACADEMICAS = {
    "inteligencia artificial": "artificial intelligence",
    "inteligencia artificial generativa": "generative artificial intelligence",
    "aprendizaje automatico": "machine learning",
    "aprendizaje profundo": "deep learning",
    "redes neuronales": "neural networks",
    "procesamiento de lenguaje natural": "natural language processing",
    "vision por computadora": "computer vision",
    "ciberseguridad": "cybersecurity",
    "seguridad informatica": "cybersecurity",
    "internet de las cosas": "internet of things",
    "cadena de bloques": "blockchain",
    "computacion en la nube": "cloud computing",
    "mineria de datos": "data mining",
    "analisis de datos": "data analysis",
    "big data": "big data",
    "sistema de informacion": "information system",
    "sistemas de informacion": "information systems",
    "sistema de control": "control system",
    "sistemas de control": "control systems",
    "reconocimiento facial": "facial recognition",
    "robotica": "robotics",
    "educacion": "education",
    "salud": "health",
    "medicina": "medicine"
}


def normalizar_consulta(texto):
    """
    Normaliza una consulta para facilitar
    comparaciones y traducciones básicas.
    """

    if not texto:
        return ""

    texto = str(texto).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def traducir_consulta_academica(tema):
    """
    Traduce términos académicos frecuentes
    del español al inglés.

    Si no existe una traducción conocida,
    devuelve la consulta original.
    """

    consulta = normalizar_consulta(
        tema
    )

    if not consulta:
        return ""

    if consulta in TRADUCCIONES_ACADEMICAS:
        return TRADUCCIONES_ACADEMICAS[
            consulta
        ]

    return tema.strip()


def preparar_consultas_arxiv(tema):
    """
    Devuelve consultas útiles para arXiv.

    La primera siempre conserva la consulta
    original del usuario.

    Si existe una traducción académica conocida,
    también se agrega la versión inglesa.
    """

    tema = (
        tema
        or ""
    ).strip()

    if not tema:
        return []

    consultas = [
        tema
    ]

    traduccion = traducir_consulta_academica(
        tema
    )

    if (
        traduccion
        and normalizar_consulta(traduccion)
        != normalizar_consulta(tema)
    ):
        consultas.append(
            traduccion
        )

    return consultas
