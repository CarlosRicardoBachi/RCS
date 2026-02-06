
# PATCH: GMPR raster restore using SVG world-space (viewBox units)
# Source of truth: SVG user units post-viewBox (Rustic-compatible)

class SvgView:
    def _compute_mm_per_svg_unit(self):
        svg = self._svg_doc
        vb = svg.viewbox  # (x, y, w, h)
        svg_w_mm = svg.width_mm
        svg_h_mm = svg.height_mm
        self._mm_per_u_x = svg_w_mm / vb.w
        self._mm_per_u_y = svg_h_mm / vb.h

    def add_raster_from_gmpr(self, raster_img, transform):
        if not hasattr(self, "_mm_per_u_x"):
            self._compute_mm_per_svg_unit()

        # Legacy compat
        if "sx" not in transform and "s" in transform:
            transform["sx"] = transform["sy"] = transform["s"]

        x_mm = transform.get("x", 0) * self._mm_per_u_x
        y_mm = transform.get("y", 0) * self._mm_per_u_y
        sx_mm = transform.get("sx", 1) * self._mm_per_u_x
        sy_mm = transform.get("sy", 1) * self._mm_per_u_y
        rot = transform.get("rot", 0)

        item = self._create_raster_item(raster_img)
        item.setPos(x_mm, y_mm)
        item.setScaleNonUniform(sx_mm, sy_mm)
        item.setRotation(rot)
        self.scene().addItem(item)
        return item
