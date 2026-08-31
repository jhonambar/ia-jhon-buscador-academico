import html
import re
import unicodedata

from functools import lru_cache

import requests


URL_MYMEMORY = "https://api.mymemory.translated.net/get"

TIMEOUT_TRADUCCION = 8


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
    comparaciones, traducciones y caché.
    """

    if not texto:
        return ""

    texto = str(
        texto
    ).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = re.sub(
        r"[^\w\s-]",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def obtener_traduccion_local(tema):
    """
    Busca una traducción académica conocida
    en el diccionario local.
    """

    consulta = normalizar_consulta(
        tema
    )

    if not consulta:
        return ""

    return TRADUCCIONES_ACADEMICAS.get(
        consulta,
        ""
    )


def es_consulta_inglesa_conocida(tema):
    """
    Comprueba si una consulta corresponde
    a una traducción inglesa ya conocida
    en el diccionario académico.

    Evita enviar innecesariamente esos términos
    a MyMemory como si fueran español.
    """

    consulta = normalizar_consulta(
        tema
    )

    if not consulta:
        return False

    traducciones_ingles = {
        normalizar_consulta(
            traduccion
        )
        for traduccion
        in TRADUCCIONES_ACADEMICAS.values()
    }

    return (
        consulta
        in traducciones_ingles
    )


@lru_cache(maxsize=256)
def traducir_con_mymemory(tema):
    """
    Intenta traducir automáticamente
    una consulta del español al inglés.

    La respuesta se guarda temporalmente
    en caché para evitar consultas repetidas
    al servicio externo.

    Si el servicio falla,
    devuelve una cadena vacía.
    """

    tema = (
        tema
        or ""
    ).strip()

    if not tema:
        return ""

    try:

        respuesta = requests.get(
            URL_MYMEMORY,
            params={
                "q": tema,
                "langpair": "es|en"
            },
            timeout=TIMEOUT_TRADUCCION
        )

        if respuesta.status_code != 200:

            print(
                "[Traducción] MyMemory respondió "
                f"HTTP {respuesta.status_code}"
            )

            return ""

        datos = respuesta.json()

        traduccion = (
            datos
            .get(
                "responseData",
                {}
            )
            .get(
                "translatedText",
                ""
            )
        )

        traduccion = (
            traduccion
            or ""
        ).strip()

        traduccion = html.unescape(
            traduccion
        )

        if not traduccion:
            return ""

        if (
            normalizar_consulta(
                traduccion
            )
            == normalizar_consulta(
                tema
            )
        ):
            return ""

        return traduccion

    except requests.RequestException as error:

        print(
            "[Traducción] Error de conexión "
            f"con MyMemory: {error}"
        )

        return ""

    except ValueError as error:

        print(
            "[Traducción] Respuesta JSON inválida: "
            f"{error}"
        )

        return ""


@lru_cache(maxsize=256)
def traducir_consulta_academica(tema):
    """
    Traduce una consulta académica
    del español al inglés.

    Prioridad:

    1. Diccionario académico local.
    2. Reconocimiento de términos ingleses conocidos.
    3. Traducción automática con MyMemory.
    4. Consulta original como respaldo.

    El resultado se almacena temporalmente
    en caché para reutilizarlo entre
    las distintas fuentes académicas.
    """

    tema = (
        tema
        or ""
    ).strip()

    if not tema:
        return ""

    traduccion_local = (
        obtener_traduccion_local(
            tema
        )
    )

    if traduccion_local:
        return traduccion_local

    if es_consulta_inglesa_conocida(
        tema
    ):
        return tema

    traduccion_automatica = (
        traducir_con_mymemory(
            tema
        )
    )

    if traduccion_automatica:
        return traduccion_automatica

    return tema


def preparar_consultas_academicas(tema):
    """
    Devuelve las consultas académicas útiles.

    Conserva siempre la consulta original
    y agrega una versión inglesa cuando
    la traducción sea diferente.

    Esta función puede utilizarse en
    distintas fuentes académicas.
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

    traduccion = (
        traducir_consulta_academica(
            tema
        )
    )

    if (
        traduccion
        and normalizar_consulta(
            traduccion
        )
        != normalizar_consulta(
            tema
        )
    ):

        consultas.append(
            traduccion
        )

    return consultas


def preparar_consultas_arxiv(tema):
    """
    Mantiene compatibilidad con el servicio
    de arXiv.

    Internamente utiliza la función genérica
    de preparación de consultas académicas.
    """

    return preparar_consultas_academicas(
        tema
    )
