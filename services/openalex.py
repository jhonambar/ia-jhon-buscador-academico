import requests


URL_OPENALEX = "https://api.openalex.org/works"


def reconstruir_abstract(indice):
    """
    OpenAlex puede entregar el abstract como índice invertido.
    Esta función lo reconstruye como texto normal.
    """

    if not indice:
        return "Resumen no disponible"

    palabras = []

    for palabra, posiciones in indice.items():
        for posicion in posiciones:
            palabras.append((posicion, palabra))

    palabras.sort(key=lambda x: x[0])

    return " ".join(palabra for _, palabra in palabras)


def buscar_openalex(tema, desde=2020, hasta=2026, cantidad=20):
    """
    Busca publicaciones académicas utilizando OpenAlex.

    Devuelve una lista normalizada para que Flask pueda
    mostrar los resultados sin depender directamente
    de la estructura original de OpenAlex.
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

    parametros = {
        "search": tema,
        "filter": (
            f"from_publication_date:{desde}-01-01,"
            f"to_publication_date:{hasta}-12-31"
        ),
        "per-page": min(max(cantidad, 1), 100)
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
        print(f"[OpenAlex] Error de conexión: {error}")
        return []

    except ValueError as error:
        print(f"[OpenAlex] Respuesta JSON inválida: {error}")
        return []

    resultados = []

    for trabajo in datos.get("results", []):

        titulo = trabajo.get("display_name") or "Sin título"

        # -----------------------------
        # AUTORES E INSTITUCIONES
        # -----------------------------

        autores = []
        instituciones = []

        for autoria in trabajo.get("authorships", []):

            autor = autoria.get("author") or {}
            nombre = autor.get("display_name")

            if nombre:
                autores.append(nombre)

            for institucion in autoria.get("institutions", []):
                nombre_institucion = institucion.get("display_name")

                if (
                    nombre_institucion
                    and nombre_institucion not in instituciones
                ):
                    instituciones.append(nombre_institucion)

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

        # -----------------------------
        # REVISTA / FUENTE
        # -----------------------------

        ubicacion = trabajo.get("primary_location") or {}
        fuente = ubicacion.get("source") or {}

        revista = (
            fuente.get("display_name")
            or "Fuente no disponible"
        )

        # -----------------------------
        # DOI
        # -----------------------------

        doi = trabajo.get("doi") or ""

        if doi.startswith("https://doi.org/"):
            doi = doi.replace(
                "https://doi.org/",
                ""
            )

        # -----------------------------
        # ACCESO ABIERTO
        # -----------------------------

        open_access = trabajo.get("open_access") or {}

        acceso_abierto = open_access.get(
            "is_oa",
            False
        )

        url_oa = open_access.get("oa_url") or ""

        # -----------------------------
        # ABSTRACT
        # -----------------------------

        abstract = reconstruir_abstract(
            trabajo.get("abstract_inverted_index")
        )

        # -----------------------------
        # PALABRAS CLAVE / TEMAS
        # -----------------------------

        palabras_clave = []

        for keyword in trabajo.get("keywords", []):
            nombre_keyword = keyword.get("display_name")

            if nombre_keyword:
                palabras_clave.append(nombre_keyword)

        if not palabras_clave:

            for concepto in trabajo.get("concepts", [])[:8]:
                nombre_concepto = concepto.get("display_name")

                if nombre_concepto:
                    palabras_clave.append(nombre_concepto)

        palabras_clave_texto = (
            ", ".join(palabras_clave)
            if palabras_clave
            else "No disponibles"
        )

        # -----------------------------
        # URL PRINCIPAL
        # -----------------------------

        url = (
            ubicacion.get("landing_page_url")
            or url_oa
            or trabajo.get("doi")
            or ""
        )

        # -----------------------------
        # RESULTADO NORMALIZADO
        # -----------------------------

        resultados.append({
            "id_openalex": trabajo.get("id") or "",
            "titulo": titulo,
            "autores": autores_texto,
            "instituciones": instituciones_texto,

            "anio": trabajo.get(
                "publication_year"
            ) or "",

            "fecha_publicacion": trabajo.get(
                "publication_date"
            ) or "",

            "revista": revista,
            "doi": doi,
            "url": url,
            "url_open_access": url_oa,

            "citas": trabajo.get(
                "cited_by_count",
                0
            ),

            "idioma": trabajo.get(
                "language"
            ) or "N/D",

            "tipo": trabajo.get(
                "type"
            ) or "N/D",

            "acceso_abierto": acceso_abierto,

            "abstract": abstract,

            "palabras_clave": palabras_clave_texto,

            "fuente_busqueda": "OpenAlex"
        })

    return resultados
