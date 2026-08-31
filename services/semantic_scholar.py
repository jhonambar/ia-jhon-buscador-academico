import os
import time
import requests
from urllib.parse import quote


URL_SEMANTIC_SCHOLAR = (
    "https://api.semanticscholar.org/graph/v1"
)

URL_BUSQUEDA = (
    f"{URL_SEMANTIC_SCHOLAR}/paper/search/bulk"
)

API_KEY = os.getenv(
    "SEMANTIC_SCHOLAR_API_KEY",
    ""
)


CAMPOS = ",".join([
    "paperId",
    "title",
    "abstract",
    "year",
    "publicationDate",
    "authors",
    "venue",
    "journal",
    "citationCount",
    "externalIds",
    "url",
    "openAccessPdf",
    "publicationTypes",
    "fieldsOfStudy"
])


def obtener_headers():
    """
    Devuelve los encabezados necesarios
    para consultar Semantic Scholar.
    """

    headers = {
        "User-Agent":
            "IA-Jhon-Buscador-Academico/1.0"
    }

    if API_KEY:
        headers["x-api-key"] = API_KEY

    return headers


def realizar_peticion(
    url,
    parametros=None,
    intentos=3
):
    """
    Realiza una consulta a Semantic Scholar.

    Si recibe un error 429 aplica esperas
    progresivas antes de volver a intentar.

    Devuelve:
    - Response si la petición funciona.
    - "limite" si continúa el error 429.
    - None si ocurre otro error.
    """

    esperas = [1, 2, 4]

    for intento in range(intentos):

        try:

            respuesta = requests.get(
                url,
                params=parametros,
                headers=obtener_headers(),
                timeout=20
            )

        except requests.RequestException as error:

            print(
                "[Semantic Scholar] "
                f"Error de conexión: {error}"
            )

            return None

        if respuesta.status_code == 429:

            print(
                "[Semantic Scholar] "
                "Límite de solicitudes alcanzado."
            )

            if intento < intentos - 1:

                tiempo = esperas[
                    min(
                        intento,
                        len(esperas) - 1
                    )
                ]

                print(
                    "[Semantic Scholar] "
                    f"Reintentando en {tiempo} segundos..."
                )

                time.sleep(tiempo)

                continue

            return "limite"

        try:
            respuesta.raise_for_status()

        except requests.RequestException as error:

            print(
                "[Semantic Scholar] "
                f"Error HTTP: {error}"
            )

            return None

        return respuesta

    return None


def obtener_autores(item):

    autores = []

    for autor in item.get("authors") or []:

        nombre = (
            autor.get("name")
            or ""
        ).strip()

        if nombre:
            autores.append(nombre)

    if autores:
        return ", ".join(autores)

    return "Autor no disponible"


def obtener_revista(item):

    journal = item.get("journal") or {}

    nombre_journal = (
        journal.get("name")
        or ""
    ).strip()

    if nombre_journal:
        return nombre_journal

    venue = (
        item.get("venue")
        or ""
    ).strip()

    if venue:
        return venue

    return "Fuente no disponible"


def obtener_doi(item):

    external_ids = (
        item.get("externalIds")
        or {}
    )

    doi = (
        external_ids.get("DOI")
        or ""
    )

    return str(doi).strip()


def obtener_tipo(item):

    tipos = (
        item.get("publicationTypes")
        or []
    )

    if tipos:

        return ", ".join(
            str(tipo)
            for tipo in tipos
            if tipo
        )

    return "N/D"


def obtener_palabras_clave(item):

    campos = (
        item.get("fieldsOfStudy")
        or []
    )

    if campos:

        return ", ".join(
            str(campo)
            for campo in campos
            if campo
        )

    return "No disponibles"


def obtener_url_oa(item):

    open_access_pdf = (
        item.get("openAccessPdf")
        or {}
    )

    return (
        open_access_pdf.get("url")
        or ""
    )


def convertir_item_semantic_scholar(item):

    if not item:
        return None

    paper_id = (
        item.get("paperId")
        or ""
    )

    titulo = (
        item.get("title")
        or "Sin título"
    )

    abstract = (
        item.get("abstract")
        or "Resumen no disponible"
    )

    url_oa = obtener_url_oa(item)

    acceso_abierto = bool(url_oa)

    return {
        "id_semantic_scholar":
            paper_id,

        "titulo":
            titulo,

        "autores":
            obtener_autores(item),

        "instituciones":
            "Institución no disponible",

        "anio":
            item.get("year")
            or "",

        "fecha_publicacion":
            item.get("publicationDate")
            or "",

        "revista":
            obtener_revista(item),

        "doi":
            obtener_doi(item),

        "url":
            item.get("url")
            or url_oa
            or "",

        "url_open_access":
            url_oa,

        "citas":
            item.get(
                "citationCount",
                0
            )
            or 0,

        "idioma":
            "N/D",

        "tipo":
            obtener_tipo(item),

        "acceso_abierto":
            acceso_abierto,

        "abstract":
            abstract,

        "palabras_clave":
            obtener_palabras_clave(item),

        "fuente_busqueda":
            "Semantic Scholar"
    }


def buscar_semantic_scholar(
    tema,
    desde=2020,
    hasta=2026,
    cantidad=20
):

    tema = (
        tema
        or ""
    ).strip()

    if not tema:
        return []

    try:

        desde = int(desde)
        hasta = int(hasta)
        cantidad = int(cantidad)

    except (TypeError, ValueError):

        desde = 2020
        hasta = 2026
        cantidad = 20

    if desde > hasta:
        return []

    cantidad = min(
        max(cantidad, 1),
        100
    )

    parametros = {
        "query": tema,
        "fields": CAMPOS,
        "year": f"{desde}-{hasta}"
    }

    resultados = []
    token = None

    while len(resultados) < cantidad:

        parametros_pagina = (
            parametros.copy()
        )

        if token:

            parametros_pagina[
                "token"
            ] = token

        respuesta = realizar_peticion(
            URL_BUSQUEDA,
            parametros_pagina
        )

        if (
            respuesta is None
            or respuesta == "limite"
        ):
            break

        try:

            datos = respuesta.json()

        except ValueError as error:

            print(
                "[Semantic Scholar] "
                f"JSON inválido: {error}"
            )

            break

        items = (
            datos.get("data")
            or []
        )

        if not items:
            break

        for item in items:

            resultado = (
                convertir_item_semantic_scholar(
                    item
                )
            )

            if resultado:

                resultados.append(
                    resultado
                )

            if (
                len(resultados)
                >= cantidad
            ):
                break

        token = datos.get("token")

        if not token:
            break

    return resultados[:cantidad]


def obtener_trabajo_semantic_scholar(
    paper_id
):

    paper_id = (
        paper_id
        or ""
    ).strip()

    if not paper_id:
        return None

    paper_id_url = quote(
        paper_id,
        safe=""
    )

    url = (
        f"{URL_SEMANTIC_SCHOLAR}"
        f"/paper/{paper_id_url}"
    )

    parametros = {
        "fields": CAMPOS
    }

    respuesta = realizar_peticion(
        url,
        parametros
    )

    if respuesta == "limite":

        return {
            "_estado":
                "limite_api"
        }

    if respuesta is None:

        return None

    try:

        item = respuesta.json()

    except ValueError as error:

        print(
            "[Semantic Scholar] "
            "JSON inválido en detalle: "
            f"{error}"
        )

        return None

    return convertir_item_semantic_scholar(
        item
    )
