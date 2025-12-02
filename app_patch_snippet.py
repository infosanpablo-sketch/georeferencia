# Inserta esto dentro de tu función index(), en lugar de:
# return render_template('index.html', nombre=nombre, map_html=map_html, error=error, record=record)
try:
    return render_template('index.html', nombre=nombre, map_html=map_html, error=error, record=record, meses=meses if 'meses' in locals() else [])
except Exception as e:
    # Loggea el error completo (aparecerá en los logs del servidor)
    logger.exception("Error renderizando index.html")
    # Devuelve una página simple para que no salga 500 sin mensaje (temporal)
    return f"<h1>Error interno</h1><p>Se ha producido un error al renderizar la plantilla. Revisa los logs del servidor para más detalles.</p>", 500