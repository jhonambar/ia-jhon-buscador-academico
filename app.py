from flask import Flask, render_template, request
from services.openalex import buscar_openalex


app = Flask(__name__)

ULTIMOS_RESULTADOS = []


@app.route("/", methods=["GET", "POST"])
def index():

    global ULTIMOS_RESULTADOS

    resultados = []
    mensaje = ""
    busqueda_realizada = False

    tema = ""
    desde = 2020
    hasta = 2026
    tipo = "todos"
    idioma = "todos"

    if request.method == "POST":

        busqueda_realizada = True

        tema = request.form.get("tema", "").strip()

        try:
            desde = int(request.form.get("desde", 2020))
            hasta = int(request.form.get("hasta", 2026))

        except ValueError:
            desde = 2020
            hasta = 2026

        tipo = request.form.get("tipo", "todos")
        idioma = request.form.get("idioma", "todos")

        if not tema:

            mensaje = "Escribe un tema para realizar la búsqueda."

        elif desde > hasta:

            mensaje = "El año inicial no puede ser mayor que el año final."

        else:

            resultados = buscar_openalex(
                tema=tema,
                desde=desde,
                hasta=hasta,
                cantidad=20
            )

            if idioma != "todos":

                resultados = [
                    r for r in resultados
                    if str(
                        r.get("idioma", "")
                    ).lower() == idioma.lower()
                ]

            if tipo != "todos":

                resultados = [
                    r for r in resultados
                    if tipo.lower()
                    in str(
                        r.get("tipo", "")
                    ).lower()
                ]

            if not resultados:
                mensaje = (
                    "No se encontraron publicaciones "
                    "con esos filtros."
                )

            ULTIMOS_RESULTADOS = resultados

    return render_template(
        "index.html",
        resultados=resultados,
        mensaje=mensaje,
        busqueda_realizada=busqueda_realizada,
        tema=tema,
        desde=desde,
        hasta=hasta,
        tipo=tipo,
        idioma=idioma
    )


@app.route("/detalle/<int:indice>")
def detalle(indice):

    if indice < 0 or indice >= len(ULTIMOS_RESULTADOS):
        return "Publicación no encontrada", 404

    articulo = ULTIMOS_RESULTADOS[indice]

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
