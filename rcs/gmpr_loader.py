
# PATCH: GMPR SVG Embedded Import Fix
# Archivo: rcs/gmpr_loader.py
#
# Hotfix: reconstruir SVG embebido como raíz geométrica
# antes de importar raster relativo.

def load_gmpr_project(data, scene):
    svg_root = None

    # 1) Restaurar SVG embebido como sistema de referencia
    svg_embedded = data.get("svg_embedded")
    if svg_embedded:
        svg_bytes = decode_svg_embedded(svg_embedded)
        svg_root = create_svg_item_from_bytes(svg_bytes)
        scene.addItem(svg_root)

    # 2) Restaurar objetos raster relativos al SVG
    for obj in data.get("objects", []):
        if obj.get("type") == "raster":
            raster = create_raster_item(obj, svg_root)
            scene.addItem(raster)


def decode_svg_embedded(svg_embedded):
    import base64, gzip, io
    raw = base64.b64decode(svg_embedded["data"])
    return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
