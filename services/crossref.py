import re
import html
import requests
from urllib.parse import quote


URL_CROSSREF = "https://api.crossref.org/works"
CORREO_CONTACTO = "jerazo023@gmail.com"


def limpiar_html(texto):
    """
    Elimina etiquetas HTML que algunos registros
    de Crossref incluyen en el abstract.
    """

    if not texto:
        return "Resumen no disponible"

    texto = html.unescape(texto)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def obtener_fecha(item):
    """
    Obtiene la mejor fecha de publicación disponible.
    """

    campos_fecha = [
        "published-print",
        "published-online",
        "published",
        "issued"
    ]

    for campo in campos_fecha:

        fecha = item.get(campo) or {}
        partes = fecha.get("date-parts") or []

        if partes and partes[0]:

            valores = partes[0]

            anio = valores[0] if len(valores) > 0 else None
            mes = valores[1] if len(valores) > 1 else None
            dia = valores[2] if len(valores) > 2 else None

            if anio and mes and dia:
                return f"{anio:04d}-{mes:02d}-{dia:02d}"

            if anio and mes:
                return f"{anio:04d}-{mes:02d}"

            if anio:
                return str(anio)

    return ""


def obtener_anio(item):
    """
    Obtiene el año de publicación.
    """

    fecha = obtener_fecha(item)

    if fecha:
        try:
            return int(fecha[:4])
        except ValueError:
            pass

    return ""


def obtener_autores(item):
    """
    Convierte los autores de Crossref
    en un texto legible.
    """

    autores = []

    for autor in item.get("author", []):

        nombre = autor.get("given", "").strip()
        apellido = autor.get("family", "").strip()

        nombre_completo = " ".join(
            parte
            for parte in [nombre, apellido]
            if parte
        )

        if nombre_completo:
            autores.append(nombre_completo)

    if autores:
        return ", ".join(autores)

    return "Autor no disponible"


def obtener_instituciones(item):
    """
    Obtiene las afiliaciones o instituciones
    de los autores.
    """

    instituciones = []

    for autor in item.get("author", []):

        for afiliacion in autor.get("affiliation", []):

            nombre = (
                afiliacion.get("name", "")
                .strip()
            )

            if (
                nombre
                and nombre not in instituciones
            ):
                instituciones.append(nombre)

    if instituciones:
        return ", ".join(instituciones)

    return "Institución no disponible"


def obtener_titulo(item):
    """
    Obtiene el título principal.
    """

    titulos = item.get("title") or []

    if titulos:
        return titulos[0].strip()

    return "Sin título"


def obtener_revista(item):
    """
    Obtiene la revista, libro o fuente.
    """

    fuentes = item.get("container-title") or []

    if fuentes:
        return fuentes[0].strip()

    editorial = item.get("publisher")

    if editorial:
        return editorial

    return "Fuente no disponible"


def obtener_url(item):
    """
    Obtiene el enlace principal de la publicación.
    """

    url = item.get("URL") or ""

    if url:
        return url

    doi = item.get("DOI") or ""

    if doi:
        return f"https://doi.org/{doi}"

    return ""


def obtener_url_texto_completo(item):
    """
    Busca un posible enlace al texto completo.

    Crossref puede incluir enlaces en el campo link,
    aunque esto no significa necesariamente
    que sean de acceso abierto.
    """

    enlaces = item.get("link") or []

    for enlace in enlaces:

        url = enlace.get("URL")

        if url:
            return url

    return ""


def limpiar_doi_crossref(doi):
    """
    Limpia un DOI para utilizarlo
    en consultas a Crossref.
    """

    if not doi:
        return ""

    doi = str(doi).strip()

    doi = re.sub(
        r"^https?://(?:dx\.)?doi\.org/",
        "",
        doi,
        flags=re.IGNORECASE
    )

    doi = re.sub(
        r"^doi:\s*",
        "",
        doi,
        flags=re.IGNORECASE
    )

    return doi.strip()


def convertir_item_crossref(item):
    """
    Convierte un registro de Crossref al formato
    utilizado por IA Jhon.
    """

    if not item:
        return None

    doi = limpiar_doi_crossref(
        item.get("DOI") or ""
    )

    palabras = item.get("subject") or []

    if palabras:
        palabras_clave = ", ".join(palabras)
    else:
        palabras_clave = "No disponibles"

    return {
        "id_crossref": doi,
        "titulo": obtener_titulo(item),
        "autores": obtener_autores(item),
        "instituciones": obtener_instituciones(item),
        "anio": obtener_anio(item),
        "fecha_publicacion": obtener_fecha(item),
        "revista": obtener_revista(item),
        "doi": doi,
        "url": obtener_url(item),
        "url_open_access": "",
        "citas": item.get(
            "is-referenced-by-count",
            0
        ),
        "idioma": (
            item.get("language", "N/D")
            or "N/D"
        ),
        "tipo": (
            item.get("type")
            or "N/D"
        ),
        "acceso_abierto": False,
        "abstract": limpiar_html(
            item.get("abstract")
        ),
        "palabras_clave": palabras_clave,
        "fuente_busqueda": "Crossref",
        "url_texto_completo":
            obtener_url_texto_completo(item)
    }


def buscar_crossref(
    tema,
    desde=2020,
    hasta=2026,
    cantidad=20
):
    """
    Busca publicaciones académicas en Crossref.
    """

    tema = (tema or "").strip()

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

    filtros = (
        f"from-pub-date:{desde}-01-01,"
        f"until-pub-date:{hasta}-12-31"
    )

    parametros = {
        "query.bibliographic": tema,
        "filter": filtros,
        "rows": cantidad,
        "mailto": CORREO_CONTACTO
    }

    headers = {
        "User-Agent": (
            "IA-Jhon-Buscador-Academico/1.0 "
            f"(mailto:{CORREO_CONTACTO})"
        )
    }

    try:

        respuesta = requests.get(
            URL_CROSSREF,
            params=parametros,
            headers=headers,
            timeout=20
        )

        respuesta.raise_for_status()
        datos = respuesta.json()

    except requests.RequestException as error:

        print(
            f"[Crossref] Error de conexión: {error}"
        )

        return []

    except ValueError as error:

        print(
            f"[Crossref] JSON inválido: {error}"
        )

        return []

    mensaje = datos.get("message") or {}
    resultados = []

    for item in mensaje.get("items", []):

        resultado = convertir_item_crossref(item)

        if resultado:
            resultados.append(resultado)

    return resultados


def obtener_trabajo_crossref(doi):
    """
    Obtiene una publicación específica de Crossref
    utilizando su DOI.
    """

    doi = limpiar_doi_crossref(doi)

    if not doi:
        return None

    doi_url = quote(
        doi,
        safe="/"
    )

    url = f"{URL_CROSSREF}/{doi_url}"

    parametros = {
        "mailto": CORREO_CONTACTO
    }

    headers = {
        "User-Agent": (
            "IA-Jhon-Buscador-Academico/1.0 "
            f"(mailto:{CORREO_CONTACTO})"
        )
    }

    try:

        respuesta = requests.get(
            url,
            params=parametros,
            headers=headers,
            timeout=20
        )

        respuesta.raise_for_status()
        datos = respuesta.json()

    except requests.RequestException as error:

        print(
            f"[Crossref] Error al obtener detalle: {error}"
        )

        return None

    except ValueError as error:

        print(
            f"[Crossref] JSON inválido en detalle: {error}"
        )

        return None

    item = datos.get("message") or {}

    return convertir_item_crossref(item)
