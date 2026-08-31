import requests

from utils.query_utils import traducir_consulta_academica


URL_OPENALEX = "https://api.openalex.org/works"


def reconstruir_abstract(indice):
    """
    OpenAlex puede entregar el abstract
    como índice invertido.

    Esta función lo reconstruye
    como texto normal.
    """

    if not indice:
        return "Resumen no disponible"

    palabras = []

    for palabra, posiciones in indice.items():

        for posicion in posiciones:

            palabras.append(
                (
                    posicion,
                    palabra
                )
            )

    palabras.sort(
        key=lambda x: x[0]
    )

    return " ".join(
        palabra
        for _, palabra in palabras
    )


def preparar_consulta_openalex(tema):
    """
    Prepara la consulta para OpenAlex.

    Si existe una traducción académica
    al inglés, utiliza esa versión.

    Si la traducción no está disponible,
    conserva la consulta original.
    """

    tema = (
        tema
        or ""
    ).strip()

    if not tema:
        return ""

    traduccion = traducir_consulta_academica(
        tema
    )

    traduccion = (
        traduccion
        or ""
    ).strip()

    if traduccion:
        return traduccion

    return tema


def obtener_autores_instituciones(trabajo):
    """
    Obtiene autores e instituciones
    de un trabajo de OpenAlex.
    """

    autores = []
    instituciones = []

    for autoria in (
        trabajo.get("authorships")
        or []
    ):

        autor = (
            autoria.get("author")
            or {}
        )

        nombre = (
            autor.get("display_name")
            or ""
        ).strip()

        if nombre:
            autores.append(
                nombre
            )

        for institucion in (
            autoria.get("institutions")
            or []
        ):

            nombre_institucion = (
                institucion.get(
                    "display_name"
                )
                or ""
            ).strip()

            if (
                nombre_institucion
                and nombre_institucion
                not in instituciones
            ):
                instituciones.append(
                    nombre_institucion
                )

    autores_texto = (
        ", ".join(autores)
        if autores
        else "Autor no disponible"
    )

    instituciones_texto = (
        ", ".join(instituciones)
        if instituciones
        else "Institución no disponible"
    )

    return (
        autores_texto,
        instituciones_texto
    )


def obtener_revista(trabajo):
    """
    Obtiene la revista o fuente principal.
    """

    ubicacion = (
        trabajo.get("primary_location")
        or {}
    )

    fuente = (
        ubicacion.get("source")
        or {}
    )

    return (
        fuente.get("display_name")
        or "Fuente no disponible"
    )


def obtener_doi(trabajo):
    """
    Obtiene el DOI sin el prefijo
    https://doi.org/
    """

    doi = (
        trabajo.get("doi")
        or ""
    ).strip()

    prefijo = "https://doi.org/"

    if doi.startswith(prefijo):

        doi = doi[
            len(prefijo):
        ]

    return doi


def obtener_palabras_clave(trabajo):
    """
    Obtiene palabras clave.

    Si OpenAlex no devuelve keywords,
    utiliza concepts como alternativa.
    """

    palabras_clave = []

    for keyword in (
        trabajo.get("keywords")
        or []
    ):

        nombre_keyword = (
            keyword.get("display_name")
            or ""
        ).strip()

        if nombre_keyword:
            palabras_clave.append(
                nombre_keyword
            )

    if not palabras_clave:

        for concepto in (
            trabajo.get("concepts")
            or []
        )[:8]:

            nombre_concepto = (
                concepto.get(
                    "display_name"
                )
                or ""
            ).strip()

            if nombre_concepto:
                palabras_clave.append(
                    nombre_concepto
                )

    if palabras_clave:

        return ", ".join(
            palabras_clave
        )

    return "No disponibles"


def convertir_trabajo_openalex(trabajo):
    """
    Convierte un trabajo de OpenAlex
    al formato utilizado por IA Jhon.
    """

    if not trabajo:
        return None

    autores, instituciones = (
        obtener_autores_instituciones(
            trabajo
        )
    )

    ubicacion = (
        trabajo.get("primary_location")
        or {}
    )

    open_access = (
        trabajo.get("open_access")
        or {}
    )

    doi = obtener_doi(
        trabajo
    )

    url_oa = (
        open_access.get("oa_url")
        or ""
    )

    url = (
        ubicacion.get(
            "landing_page_url"
        )
        or url_oa
        or trabajo.get("doi")
        or ""
    )

    abstract = reconstruir_abstract(
        trabajo.get(
            "abstract_inverted_index"
        )
    )

    return {
        "id_openalex":
            trabajo.get("id")
            or "",

        "titulo":
            trabajo.get("display_name")
            or "Sin título",

        "autores":
            autores,

        "instituciones":
            instituciones,

        "anio":
            trabajo.get(
                "publication_year"
            )
            or "",

        "fecha_publicacion":
            trabajo.get(
                "publication_date"
            )
            or "",

        "revista":
            obtener_revista(
                trabajo
            ),

        "doi":
            doi,

        "url":
            url,

        "url_open_access":
            url_oa,

        "citas":
            trabajo.get(
                "cited_by_count",
                0
            )
            or 0,

        "idioma":
            trabajo.get(
                "language"
            )
            or "N/D",

        "tipo":
            trabajo.get(
                "type"
            )
            or "N/D",

        "acceso_abierto":
            bool(
                open_access.get(
                    "is_oa",
                    False
                )
            ),

        "abstract":
            abstract,

        "palabras_clave":
            obtener_palabras_clave(
                trabajo
            ),

        "fuente_busqueda":
            "OpenAlex"
    }


def buscar_openalex(
    tema,
    desde=2020,
    hasta=2026,
    cantidad=20
):
    """
    Busca publicaciones académicas
    utilizando OpenAlex.

    Las consultas en español intentan
    traducirse al inglés antes de buscar,
    evitando duplicar peticiones.
    """

    tema = (
        tema
        or ""
    ).strip()

    if not tema:
        return []

    try:

        desde = int(
            desde
        )

        hasta = int(
            hasta
        )

        cantidad = int(
            cantidad
        )

    except (TypeError, ValueError):

        desde = 2020
        hasta = 2026
        cantidad = 20

    if desde > hasta:
        return []

    cantidad = min(
        max(
            cantidad,
            1
        ),
        100
    )

    consulta = preparar_consulta_openalex(
        tema
    )

    if not consulta:
        return []

    parametros = {
        "search":
            consulta,

        "filter":
            (
                f"from_publication_date:"
                f"{desde}-01-01,"
                f"to_publication_date:"
                f"{hasta}-12-31"
            ),

        "per-page":
            cantidad
    }

    try:

        respuesta = requests.get(
            URL_OPENALEX,
            params=parametros,
            timeout=20
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

    except requests.RequestException as error:

        print(
            "[OpenAlex] "
            f"Error de conexión: {error}"
        )

        return []

    except ValueError as error:

        print(
            "[OpenAlex] "
            f"Respuesta JSON inválida: {error}"
        )

        return []

    resultados = []

    for trabajo in (
        datos.get("results")
        or []
    ):

        resultado = (
            convertir_trabajo_openalex(
                trabajo
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

    return resultados


def obtener_trabajo_openalex(
    id_openalex
):
    """
    Obtiene una publicación específica
    de OpenAlex utilizando su ID.
    """

    id_openalex = (
        id_openalex
        or ""
    ).strip()

    if not id_openalex:
        return None

    prefijo = (
        "https://openalex.org/"
    )

    if id_openalex.startswith(
        prefijo
    ):

        id_openalex = id_openalex[
            len(prefijo):
        ]

    url = (
        f"{URL_OPENALEX}/"
        f"{id_openalex}"
    )

    try:

        respuesta = requests.get(
            url,
            timeout=20
        )

        respuesta.raise_for_status()

        trabajo = respuesta.json()

    except requests.RequestException as error:

        print(
            "[OpenAlex] "
            "Error al obtener detalle: "
            f"{error}"
        )

        return None

    except ValueError as error:

        print(
            "[OpenAlex] "
            "JSON inválido en detalle: "
            f"{error}"
        )

        return None

    return convertir_trabajo_openalex(
        trabajo
    )
