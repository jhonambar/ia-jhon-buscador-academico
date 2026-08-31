import math
import re
import unicodedata

from flask import Flask, render_template, request

from services.openalex import (
    buscar_openalex,
    obtener_trabajo_openalex
)

from services.crossref import (
    buscar_crossref,
    obtener_trabajo_crossref
)

from services.semantic_scholar import (
    buscar_semantic_scholar,
    obtener_trabajo_semantic_scholar
)

from services.arxiv_service import (
    buscar_arxiv,
    obtener_trabajo_arxiv
)


app = Flask(__name__)


PALABRAS_VACIAS = {
    # Español
    "a", "al", "algo", "como", "con", "de", "del", "desde",
    "el", "ella", "en", "entre", "es", "esta", "este", "estos",
    "estas", "la", "las", "lo", "los", "para", "por", "que",
    "se", "sin", "sobre", "su", "sus", "un", "una", "uno",
    "unos", "unas", "y", "o",

    # Inglés
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "in", "is", "of", "on", "or", "that", "the",
    "this", "to", "with"
}


def normalizar_texto(texto):
    """
    Normaliza texto para comparaciones.

    - Convierte a minúsculas.
    - Elimina acentos.
    - Sustituye signos por espacios.
    - Elimina espacios repetidos.
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
        r"[^a-z0-9]+",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def obtener_terminos_busqueda(tema):
    """
    Obtiene las palabras importantes
    de la consulta del usuario.
    """

    tema_normalizado = normalizar_texto(
        tema
    )

    palabras = re.findall(
        r"[a-z0-9]+",
        tema_normalizado
    )

    terminos = [
        palabra
        for palabra in palabras
        if (
            len(palabra) >= 2
            and palabra not in PALABRAS_VACIAS
        )
    ]

    if not terminos:
        terminos = [
            palabra
            for palabra in palabras
            if len(palabra) >= 2
        ]

    # Elimina términos repetidos
    # conservando el orden original.
    return list(
        dict.fromkeys(terminos)
    )


def limpiar_doi(doi):
    """
    Normaliza DOI para detectar duplicados.
    """

    if not doi:
        return ""

    doi = str(doi).strip().lower()

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


def eliminar_duplicados(resultados):
    """
    Elimina publicaciones duplicadas.

    Prioridad:
    1. DOI
    2. Título normalizado
    """

    unicos = []
    dois_vistos = set()
    titulos_vistos = set()

    for resultado in resultados:

        doi = limpiar_doi(
            resultado.get("doi")
        )

        titulo = normalizar_texto(
            resultado.get("titulo")
        )

        if doi:

            if doi in dois_vistos:
                continue

            dois_vistos.add(doi)

        else:

            if (
                titulo
                and titulo in titulos_vistos
            ):
                continue

        if titulo:
            titulos_vistos.add(titulo)

        unicos.append(resultado)

    return unicos


def asignar_ranking_fuente(resultados):
    """
    Guarda temporalmente la posición en la que
    cada API entregó un resultado.

    Las cuatro fuentes ya poseen sus propios
    mecanismos de relevancia. Esta posición
    funciona como una señal adicional, pero
    no decide por sí sola el orden final.
    """

    for posicion, resultado in enumerate(
        resultados,
        start=1
    ):
        resultado["_ranking_fuente"] = posicion

    return resultados


def obtener_anio_seguro(resultado):
    """
    Devuelve el año como número entero.
    Si no existe, devuelve 0.
    """

    try:

        return int(
            resultado.get(
                "anio",
                0
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        return 0


def obtener_citas_seguras(resultado):
    """
    Devuelve el número de citas.

    Si la fuente no proporciona este dato,
    devuelve 0 solo para efectos de ordenamiento.
    """

    citas = resultado.get(
        "citas",
        0
    )

    try:

        return int(
            citas
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        return 0


def calcular_relevancia(
    resultado,
    tema
):
    """
    Calcula un puntaje común de relevancia
    para resultados provenientes de distintas
    fuentes académicas.

    El título recibe el mayor peso.
    Después se consideran palabras clave,
    abstract, cobertura de la consulta,
    posición dentro de la fuente y citas.
    """

    frase = normalizar_texto(
        tema
    )

    terminos = obtener_terminos_busqueda(
        tema
    )

    titulo = normalizar_texto(
        resultado.get(
            "titulo",
            ""
        )
    )

    palabras_clave = normalizar_texto(
        resultado.get(
            "palabras_clave",
            ""
        )
    )

    abstract = normalizar_texto(
        resultado.get(
            "abstract",
            ""
        )
    )

    titulo_tokens = set(
        titulo.split()
    )

    palabras_clave_tokens = set(
        palabras_clave.split()
    )

    abstract_tokens = set(
        abstract.split()
    )

    puntaje = 0.0

    # -------------------------------------------------
    # 1. FRASE COMPLETA
    # -------------------------------------------------

    if frase:

        if frase == titulo:
            puntaje += 180

        elif frase in titulo:
            puntaje += 130

        if frase in palabras_clave:
            puntaje += 70

        if frase in abstract:
            puntaje += 45

    # -------------------------------------------------
    # 2. PALABRAS INDIVIDUALES
    # -------------------------------------------------

    coincidencias_globales = 0
    coincidencias_titulo = 0

    for termino in terminos:

        aparece = False

        if termino in titulo_tokens:
            puntaje += 28
            coincidencias_titulo += 1
            aparece = True

        if termino in palabras_clave_tokens:
            puntaje += 16
            aparece = True

        if termino in abstract_tokens:
            puntaje += 6
            aparece = True

        if aparece:
            coincidencias_globales += 1

    # -------------------------------------------------
    # 3. COBERTURA DE LA CONSULTA
    # -------------------------------------------------

    if terminos:

        cobertura = (
            coincidencias_globales
            / len(terminos)
        )

        puntaje += cobertura * 55

        if coincidencias_globales == len(
            terminos
        ):
            puntaje += 35

        if coincidencias_titulo == len(
            terminos
        ):
            puntaje += 45

    # -------------------------------------------------
    # 4. POSICIÓN ORIGINAL DENTRO DE LA FUENTE
    # -------------------------------------------------

    try:
        ranking_fuente = int(
            resultado.get(
                "_ranking_fuente",
                100
            )
        )

    except (
        TypeError,
        ValueError
    ):
        ranking_fuente = 100

    if ranking_fuente <= 20:

        puntaje += (
            21 - ranking_fuente
        ) * 1.25

    # -------------------------------------------------
    # 5. CITAS COMO SEÑAL SECUNDARIA
    # -------------------------------------------------

    citas = obtener_citas_seguras(
        resultado
    )

    if citas > 0:

        puntaje += min(
            math.log1p(citas) * 2,
            15
        )

    return round(
        puntaje,
        4
    )


def ordenar_resultados(
    resultados,
    orden,
    tema
):
    """
    Ordena las publicaciones según
    la opción seleccionada.
    """

    for resultado in resultados:

        resultado[
            "_puntaje_relevancia"
        ] = calcular_relevancia(
            resultado,
            tema
        )

    if orden == "recientes":

        return sorted(
            resultados,
            key=lambda resultado: (
                obtener_anio_seguro(
                    resultado
                ) > 0,
                obtener_anio_seguro(
                    resultado
                ),
                resultado.get(
                    "_puntaje_relevancia",
                    0
                )
            ),
            reverse=True
        )

    if orden == "antiguos":

        return sorted(
            resultados,
            key=lambda resultado: (
                obtener_anio_seguro(
                    resultado
                ) == 0,
                obtener_anio_seguro(
                    resultado
                )
                if obtener_anio_seguro(
                    resultado
                ) > 0
                else 9999,
                -resultado.get(
                    "_puntaje_relevancia",
                    0
                )
            )
        )

    if orden == "citados":

        return sorted(
            resultados,
            key=lambda resultado: (
                obtener_citas_seguras(
                    resultado
                ),
                resultado.get(
                    "_puntaje_relevancia",
                    0
                )
            ),
            reverse=True
        )

    # Relevancia global entre todas las fuentes.
    return sorted(
        resultados,
        key=lambda resultado: (
            resultado.get(
                "_puntaje_relevancia",
                0
            ),
            obtener_citas_seguras(
                resultado
            ),
            obtener_anio_seguro(
                resultado
            )
        ),
        reverse=True
    )


@app.route("/", methods=["GET", "POST"])
def index():

    resultados = []
    mensaje = ""
    busqueda_realizada = False

    tema = ""
    desde = 2020
    hasta = 2026
    tipo = "todos"
    idioma = "todos"
    cantidad = 20
    orden = "relevancia"

    if request.method == "POST":

        busqueda_realizada = True

        tema = request.form.get(
            "tema",
            ""
        ).strip()

        try:

            desde = int(
                request.form.get(
                    "desde",
                    2020
                )
            )

            hasta = int(
                request.form.get(
                    "hasta",
                    2026
                )
            )

        except (
            TypeError,
            ValueError
        ):

            desde = 2020
            hasta = 2026

        tipo = request.form.get(
            "tipo",
            "todos"
        )

        idioma = request.form.get(
            "idioma",
            "todos"
        )

        orden = request.form.get(
            "orden",
            "relevancia"
        )

        try:

            cantidad = int(
                request.form.get(
                    "cantidad",
                    20
                )
            )

        except (
            TypeError,
            ValueError
        ):

            cantidad = 20

        cantidad = min(
            max(
                cantidad,
                1
            ),
            100
        )

        if orden not in {
            "relevancia",
            "recientes",
            "antiguos",
            "citados"
        }:

            orden = "relevancia"

        if not tema:

            mensaje = (
                "Escribe un tema para realizar "
                "la búsqueda."
            )

        elif desde > hasta:

            mensaje = (
                "El año inicial no puede ser "
                "mayor que el año final."
            )

        else:

            resultados_openalex = (
                asignar_ranking_fuente(
                    buscar_openalex(
                        tema=tema,
                        desde=desde,
                        hasta=hasta,
                        cantidad=cantidad
                    )
                )
            )

            resultados_crossref = (
                asignar_ranking_fuente(
                    buscar_crossref(
                        tema=tema,
                        desde=desde,
                        hasta=hasta,
                        cantidad=cantidad
                    )
                )
            )

            resultados_semantic_scholar = (
                asignar_ranking_fuente(
                    buscar_semantic_scholar(
                        tema=tema,
                        desde=desde,
                        hasta=hasta,
                        cantidad=cantidad
                    )
                )
            )

            resultados_arxiv = (
                asignar_ranking_fuente(
                    buscar_arxiv(
                        tema=tema,
                        desde=desde,
                        hasta=hasta,
                        cantidad=cantidad
                    )
                )
            )

            resultados = (
                resultados_openalex
                + resultados_crossref
                + resultados_semantic_scholar
                + resultados_arxiv
            )

            resultados = eliminar_duplicados(
                resultados
            )

            if idioma != "todos":

                resultados = [
                    resultado
                    for resultado in resultados
                    if str(
                        resultado.get(
                            "idioma",
                            ""
                        )
                    ).lower()
                    == idioma.lower()
                ]

            if tipo != "todos":

                resultados = [
                    resultado
                    for resultado in resultados
                    if tipo.lower()
                    in str(
                        resultado.get(
                            "tipo",
                            ""
                        )
                    ).lower()
                ]

            resultados = ordenar_resultados(
                resultados,
                orden,
                tema
            )

            if not resultados:

                mensaje = (
                    "No se encontraron publicaciones "
                    "con esos filtros."
                )

    return render_template(
        "index.html",
        resultados=resultados,
        mensaje=mensaje,
        busqueda_realizada=busqueda_realizada,
        tema=tema,
        desde=desde,
        hasta=hasta,
        tipo=tipo,
        idioma=idioma,
        cantidad=cantidad,
        orden=orden
    )


@app.route("/detalle/<id_openalex>")
def detalle(id_openalex):
    """
    Muestra el detalle de una publicación
    obtenida desde OpenAlex.
    """

    articulo = obtener_trabajo_openalex(
        id_openalex
    )

    if not articulo:

        return (
            "Publicación no encontrada",
            404
        )

    return render_template(
        "detalle.html",
        articulo=articulo
    )


@app.route("/detalle/crossref")
def detalle_crossref():
    """
    Muestra el detalle de una publicación
    obtenida desde Crossref.
    """

    doi = request.args.get(
        "doi",
        ""
    ).strip()

    if not doi:

        return (
            "DOI no proporcionado",
            400
        )

    articulo = obtener_trabajo_crossref(
        doi
    )

    if not articulo:

        return (
            "Publicación no encontrada",
            404
        )

    return render_template(
        "detalle.html",
        articulo=articulo
    )


@app.route("/detalle/semantic-scholar")
def detalle_semantic_scholar():
    """
    Muestra el detalle de una publicación
    obtenida desde Semantic Scholar.
    """

    paper_id = request.args.get(
        "paper_id",
        ""
    ).strip()

    if not paper_id:

        return (
            "ID de Semantic Scholar "
            "no proporcionado",
            400
        )

    articulo = obtener_trabajo_semantic_scholar(
        paper_id
    )

    if (
        articulo
        and articulo.get("_estado")
        == "limite_api"
    ):

        return render_template(
            "error_api.html",
            titulo=(
                "Semantic Scholar "
                "temporalmente limitado"
            ),
            mensaje=(
                "Semantic Scholar alcanzó "
                "temporalmente su límite de "
                "consultas. La publicación puede "
                "existir, pero en este momento no "
                "es posible recuperar su información "
                "completa. Intenta nuevamente dentro "
                "de unos minutos."
            )
        ), 429

    if not articulo:

        return (
            "Publicación no encontrada",
            404
        )

    return render_template(
        "detalle.html",
        articulo=articulo
    )


@app.route("/detalle/arxiv")
def detalle_arxiv():
    """
    Muestra el detalle de una publicación
    obtenida desde arXiv.
    """

    id_arxiv = request.args.get(
        "id_arxiv",
        ""
    ).strip()

    if not id_arxiv:

        return (
            "ID de arXiv no proporcionado",
            400
        )

    articulo = obtener_trabajo_arxiv(
        id_arxiv
    )

    if not articulo:

        return (
            "Publicación no encontrada",
            404
        )

    return render_template(
        "detalle.html",
        articulo=articulo
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
