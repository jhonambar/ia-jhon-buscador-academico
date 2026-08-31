import re
import requests
import xml.etree.ElementTree as ET


URL_ARXIV = "https://export.arxiv.org/api/query"


NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom"
}


def limpiar_texto(texto):
    """
    Limpia saltos de línea y espacios repetidos.
    """

    if not texto:
        return ""

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


def obtener_id_arxiv(url_id):
    """
    Extrae el identificador arXiv desde la URL.
    """

    if not url_id:
        return ""

    return (
        url_id
        .replace(
            "https://arxiv.org/abs/",
            ""
        )
        .replace(
            "http://arxiv.org/abs/",
            ""
        )
        .strip()
    )


def obtener_doi(entry):
    """
    Obtiene DOI si arXiv lo proporciona.
    """

    doi = entry.find(
        "arxiv:doi",
        NS
    )

    if doi is not None and doi.text:
        return doi.text.strip()

    return ""


def obtener_revista(entry):
    """
    Obtiene referencia de revista si está disponible.
    """

    journal = entry.find(
        "arxiv:journal_ref",
        NS
    )

    if journal is not None and journal.text:
        return limpiar_texto(
            journal.text
        )

    return "arXiv"


def obtener_pdf(entry):
    """
    Busca el enlace PDF del artículo.
    """

    for enlace in entry.findall(
        "atom:link",
        NS
    ):

        if (
            enlace.attrib.get("title")
            == "pdf"
        ):
            return enlace.attrib.get(
                "href",
                ""
            )

    return ""


def obtener_url_publicacion(entry):
    """
    Obtiene la página principal del artículo.
    """

    for enlace in entry.findall(
        "atom:link",
        NS
    ):

        if enlace.attrib.get("rel") == "alternate":
            return enlace.attrib.get(
                "href",
                ""
            )

    return ""


def convertir_entry(entry):
    """
    Convierte un registro Atom de arXiv
    al formato normalizado de IA Jhon.
    """

    titulo_elemento = entry.find(
        "atom:title",
        NS
    )

    resumen_elemento = entry.find(
        "atom:summary",
        NS
    )

    publicado = entry.find(
        "atom:published",
        NS
    )

    id_elemento = entry.find(
        "atom:id",
        NS
    )

    titulo = limpiar_texto(
        titulo_elemento.text
        if titulo_elemento is not None
        else ""
    )

    abstract = limpiar_texto(
        resumen_elemento.text
        if resumen_elemento is not None
        else ""
    )

    fecha = (
        publicado.text[:10]
        if (
            publicado is not None
            and publicado.text
        )
        else ""
    )

    anio = (
        fecha[:4]
        if fecha
        else ""
    )

    url_id = (
        id_elemento.text
        if (
            id_elemento is not None
            and id_elemento.text
        )
        else ""
    )

    id_arxiv = obtener_id_arxiv(
        url_id
    )

    autores = []

    for autor in entry.findall(
        "atom:author",
        NS
    ):

        nombre = autor.find(
            "atom:name",
            NS
        )

        if (
            nombre is not None
            and nombre.text
        ):
            autores.append(
                limpiar_texto(
                    nombre.text
                )
            )

    categorias = []

    for categoria in entry.findall(
        "atom:category",
        NS
    ):

        termino = categoria.attrib.get(
            "term"
        )

        if termino:
            categorias.append(
                termino
            )

    url_pdf = obtener_pdf(
        entry
    )

    url_publicacion = (
        obtener_url_publicacion(
            entry
        )
        or url_id
    )

    return {
        "id_arxiv":
            id_arxiv,

        "titulo":
            titulo
            or "Sin título",

        "autores":
            ", ".join(autores)
            if autores
            else "Autor no disponible",

        "instituciones":
            "Institución no disponible",

        "anio":
            anio,

        "fecha_publicacion":
            fecha,

        "revista":
            obtener_revista(entry),

        "doi":
            obtener_doi(entry),

        "url":
            url_publicacion,

        "url_open_access":
            url_pdf,

        "citas":
            0,

        "idioma":
            "N/D",

        "tipo":
            "preprint",

        "acceso_abierto":
            True,

        "abstract":
            abstract
            or "Resumen no disponible",

        "palabras_clave":
            ", ".join(categorias)
            if categorias
            else "No disponibles",

        "fuente_busqueda":
            "arXiv"
    }


def buscar_arxiv(
    tema,
    desde=2020,
    hasta=2026,
    cantidad=20
):
    """
    Busca publicaciones en arXiv.
    """

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

    inicio = (
        f"{desde}01010000"
    )

    fin = (
        f"{hasta}12312359"
    )

    consulta = (
        f'all:"{tema}" '
        f'AND submittedDate:'
        f'[{inicio} TO {fin}]'
    )

    parametros = {
        "search_query": consulta,
        "start": 0,
        "max_results": cantidad,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }

    try:

        respuesta = requests.get(
            URL_ARXIV,
            params=parametros,
            timeout=25
        )

        respuesta.raise_for_status()

    except requests.RequestException as error:

        print(
            "[arXiv] Error de conexión: "
            f"{error}"
        )

        return []

    try:

        raiz = ET.fromstring(
            respuesta.text
        )

    except ET.ParseError as error:

        print(
            "[arXiv] XML inválido: "
            f"{error}"
        )

        return []

    resultados = []

    for entry in raiz.findall(
        "atom:entry",
        NS
    ):

        resultado = convertir_entry(
            entry
        )

        resultados.append(
            resultado
        )

    return resultados


def obtener_trabajo_arxiv(
    id_arxiv
):
    """
    Obtiene una publicación concreta
    utilizando su identificador arXiv.
    """

    id_arxiv = (
        id_arxiv
        or ""
    ).strip()

    if not id_arxiv:
        return None

    parametros = {
        "id_list": id_arxiv
    }

    try:

        respuesta = requests.get(
            URL_ARXIV,
            params=parametros,
            timeout=25
        )

        respuesta.raise_for_status()

    except requests.RequestException as error:

        print(
            "[arXiv] Error al obtener detalle: "
            f"{error}"
        )

        return None

    try:

        raiz = ET.fromstring(
            respuesta.text
        )

    except ET.ParseError as error:

        print(
            "[arXiv] XML inválido en detalle: "
            f"{error}"
        )

        return None

    entry = raiz.find(
        "atom:entry",
        NS
    )

    if entry is None:
        return None

    return convertir_entry(
        entry
    )
