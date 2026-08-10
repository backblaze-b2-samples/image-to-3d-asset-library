"""Headless preview render + multi-resolution texture/preview map derivation.

No OpenGL: the 3D preview is rendered with matplotlib's Agg backend (no
moderngl / pyglet / display server), and the multi-resolution maps are produced
by downsampling that render with Pillow. All imports are inside functions so
importing the engines package stays cheap.

The stored mesh is always full resolution; only the *preview* is decimated (by
face subsampling) when a mesh is very dense, so the thumbnail renders quickly.
"""

import contextlib
import io

# Cap on faces drawn in the matplotlib preview. The stored GLB keeps every face;
# this only bounds preview render time for a dense TripoSR mesh.
_PREVIEW_FACE_CAP = 12000


def _load_trimesh(glb_bytes: bytes):
    import trimesh

    loaded = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")
    if isinstance(loaded, trimesh.Scene):
        if len(loaded.geometry) == 0:
            raise ValueError("empty scene: nothing to render")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    return loaded


def _face_colors(mesh, faces):
    """Per-face RGB in [0,1]. Uses vertex colors when present, else a neutral
    slate so the shape still reads on a dark card."""
    import numpy as np

    vc = getattr(mesh.visual, "vertex_colors", None)
    if vc is not None and len(vc) == len(mesh.vertices):
        cols = np.asarray(vc, dtype=float)[:, :3] / 255.0
        return cols[faces].mean(axis=1)
    return np.tile(np.array([0.62, 0.66, 0.72]), (len(faces), 1))


def render_mesh_png(glb_bytes: bytes, size: int, seed: int = 0) -> bytes:
    """Render a dark, single-subject square PNG of the mesh at `size`x`size`."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    mesh = _load_trimesh(glb_bytes)
    verts = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces)

    if len(faces) > _PREVIEW_FACE_CAP:
        rng = np.random.default_rng(seed)
        faces = faces[rng.choice(len(faces), _PREVIEW_FACE_CAP, replace=False)]

    facecolors = _face_colors(mesh, faces)

    dpi = 100
    fig = plt.figure(figsize=(size / dpi, size / dpi), dpi=dpi)
    fig.patch.set_facecolor("#0c0e12")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0c0e12")

    tris = verts[faces]
    collection = Poly3DCollection(
        tris, facecolors=facecolors, edgecolors="none", linewidths=0.0
    )
    collection.set_alpha(1.0)
    ax.add_collection3d(collection)

    mins, maxs = verts.min(axis=0), verts.max(axis=0)
    center = (mins + maxs) / 2.0
    radius = float(np.max(maxs - mins)) / 2.0 or 1.0
    axis_setters = (ax.set_xlim, ax.set_ylim, ax.set_zlim)
    for setlim, c in zip(axis_setters, center, strict=False):
        setlim(c - radius, c + radius)

    ax.view_init(elev=18, azim=-62)
    ax.set_axis_off()
    with contextlib.suppress(Exception):  # older matplotlib without set_box_aspect
        ax.set_box_aspect((1, 1, 1))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return buf.getvalue()


def downsample_png(png_bytes: bytes, size: int) -> bytes:
    """Resize a PNG to `size`x`size` (Lanczos), preserving RGBA."""
    from PIL import Image

    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def multi_resolution_maps(base_png: bytes, resolutions: list[int]) -> dict[int, bytes]:
    """Derive one PNG per resolution by downsampling the base render. This is
    the write-amplification fan-out: one input image -> many texture maps."""
    return {res: downsample_png(base_png, res) for res in resolutions}


def resolution_ladder(top: int, floor: int = 256) -> list[int]:
    """[top, top/2, top/4, ...] down to (and including) `floor`."""
    ladder: list[int] = []
    res = top
    while res >= floor:
        ladder.append(res)
        res //= 2
    return ladder or [top]
