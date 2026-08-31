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


def normalizar_texto(texto):
    """
    Normaliza texto para comparar títulos.
    """

    if not texto:
        return ""

    return (
        str(texto)
        .strip()
        .lower()
        .replace(".", "")
        .replace(",", "")
        .replace(":", "")
        .replace(";", "")
        .replace("-", " ")
    )


def limpiar_doi(doi):
    """
    Normaliza DOI para detectar duplicados.
    """

    if not doi:
        return ""

    doi = str(doi).strip().lower()

    doi = doi.replace(
        "https://doi.org/",
        ""
    )

    doi = doi.replace(
        "http://doi.org/",
        ""
    )

    doi = doi.replace(
        "doi:",
        ""
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

        except (TypeError, ValueError):

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

        try:

            cantidad = int(
                request.form.get(
                    "cantidad",
                    20
                )
            )

        except (TypeError, ValueError):

            cantidad = 20

        cantidad = min(
            max(cantidad, 1),
            100
        )

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

            resultados_openalex = buscar_openalex(
                tema=tema,
                desde=desde,
                hasta=hasta,
                cantidad=cantidad
            )

            resultados_crossref = buscar_crossref(
                tema=tema,
                desde=desde,
                hasta=hasta,
                cantidad=cantidad
            )

            resultados_semantic_scholar = (
                buscar_semantic_scholar(
                    tema=tema,
                    desde=desde,
                    hasta=hasta,
                    cantidad=cantidad
                )
            )

            resultados_arxiv = buscar_arxiv(
                tema=tema,
                desde=desde,
                hasta=hasta,
                cantidad=cantidad
            )

            resultados = (
                resultados_openalex
                +
                resultados_crossref
                +
                resultados_semantic_scholar
                +
                resultados_arxiv
            )

            resultados = eliminar_duplicados(
                resultados
            )

            if idioma != "todos":

                resultados = [
                    r
                    for r in resultados
                    if str(
                        r.get(
                            "idioma",
                            ""
                        )
                    ).lower()
                    == idioma.lower()
                ]

            if tipo != "todos":

                resultados = [
                    r
                    for r in resultados
                    if tipo.lower()
                    in str(
                        r.get(
                            "tipo",
                            ""
                        )
                    ).lower()
                ]

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
        cantidad=cantidad
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
