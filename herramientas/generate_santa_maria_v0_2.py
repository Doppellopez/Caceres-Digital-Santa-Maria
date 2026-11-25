import json, numpy as np
from pathlib import Path
from shapely.geometry import Polygon, Point, box
from shapely.geometry.polygon import orient
from shapely import make_valid
from shapely.ops import triangulate
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.spatial import Delaunay, cKDTree
import trimesh

P=Path(__file__).parent
D=json.load(open(P/'santa_maria_dxf_local.json'))
U=next(v for k,v in D.items() if 'trama' in k)
R=next(v for k,v in D.items() if 'relieve' in k)
Z0=440.0
BOUNDS=box(-75, -75, 75, 75)

def parts(g):
  if g.is_empty:
    return []
  if g.geom_type == 'Polygon':
    return [g]
  if hasattr(g, 'geoms'):
    out = []
    for x in g.geoms:
      out.extend(parts(x))
    return out
  return []

def uniq(a, tol=3):
  a = np.asarray(a, float)
  if len(a) == 0:
    return a
  xy, inv = np.unique(np.round(a[:, :2], tol), axis=0, return_inverse=True)
  z = np.array([np.median(a[inv == i, 2]) for i in range(len(xy))])
  return np.c_[xy, z]

def build():
  pts = []
  for src in (U, R):
    for _t, layer, arr, _closed, _txt in src:
      if layer in (
        'Punto cota', 'Escalera', 'Bordillo', 'Soportal', 'Pilar',
        'Muro contención', 'Muralla'
      ):
        for p in arr:
          if 420 < p[2] < 470 and abs(p[0]) <= 80 and abs(p[1]) <= 80:
            pts.append(p)
  ground = uniq(pts)
  lin = LinearNDInterpolator(ground[:, :2], ground[:, 2])
  near = NearestNDInterpolator(ground[:, :2], ground[:, 2])

  def gz(xy):
    a = np.asarray(xy, float)
    z = np.asarray(lin(a), float)
    return np.where(np.isnan(z), near(a), z)

  roof = uniq([
    p for _t, layer, arr, _closed, _txt in U
    if layer == 'Limatesa y limahoyas'
    for p in arr
    if 430 < p[2] < 480 and abs(p[0]) <= 80 and abs(p[1]) <= 80
  ])
  rt = cKDTree(roof[:, :2])

  scene = trimesh.Scene()
  meshes = []

  def add(name, verts, faces, color):
    if len(faces) == 0 or len(verts) == 0:
      return
    m = trimesh.Trimesh(
      vertices=np.asarray(verts) - [0, 0, Z0],
      faces=np.asarray(faces),
      process=False,
    )
    scene.add_geometry(m, node_name=name, geom_name=name)
    m.visual.face_colors = np.array(color)
    meshes.append((name, m, color))

  xs = np.arange(-75, 75.001, 0.8)
  ys = np.arange(-75, 75.001, 0.8)
  grid = np.array([(x, y) for x in xs for y in ys])
  xy = np.unique(np.round(np.vstack([grid, ground[:, :2]]), 3), axis=0)
  tri = Delaunay(xy).simplices
  faces = []
  for f in tri:
    p = xy[f]
    lens = [np.linalg.norm(p[(i + 1) % 3] - p[i]) for i in range(3)]
    if max(lens) < 4.0:
      faces.append(f.tolist())
  add('Terreno_interpolado', np.c_[xy, gz(xy)], faces,
      [154, 143, 122, 255])

  records = []
  for t, layer, arr, closed, _txt in U:
    if not layer.startswith('Edificio') or not closed or len(arr) < 4:
      continue
    arr = np.array(arr, float)
    geom = make_valid(Polygon(arr[:, :2])).intersection(BOUNDS)
    for p in parts(geom):
      if p.area > 2:
        records.append((t, layer, arr, p))
  records.sort(key=lambda r: (r[0] != 'POLYLINE', r[3].area))

  used = Polygon()
  n = 0
  for _t, _layer, arr, geom in records:
    for poly in parts(geom.difference(used)):
      if poly.area < 3:
        continue
      poly = orient(poly, 1.0)
      n += 1
      label = f'Edificio_{n:02d}'
      boundary = uniq(arr)
      bt = cKDTree(boundary[:, :2])
      ring = np.asarray(poly.exterior.coords)[:-1]
      interior = []
      for p in roof:
        if poly.buffer(0.35).covers(Point(p[:2])):
          interior.append(p)
      interior = np.array(interior, float) if interior else np.empty((0, 3))
      if len(interior):
        keep = []
        for p in interior:
          if not keep:
            keep.append(p)
            continue
          arrk = np.array(keep)
          if np.min(np.linalg.norm(arrk[:, :2] - p[:2], axis=1)) > 0.7:
            keep.append(p)
        interior = np.array(keep)

      def bz(xy):
        xy = np.asarray(xy, float)
        _dist, idx = bt.query(xy)
        z = boundary[idx, 2].copy()
        rd, ri = rt.query(xy)
        mask = rd < 0.05
        z[mask] = roof[ri[mask], 2]
        return z

      pts = np.unique(np.round(np.vstack([
        ring,
        interior[:, :2] if len(interior) else np.empty((0, 2)),
      ]), 3), axis=0)
      if len(pts) < 3:
        continue

      rz = bz(pts)
      d, i = rt.query(pts)
      mask = d < 0.03
      rz[mask] = roof[i[mask], 2]
      rz = np.maximum(rz, gz(pts) + 1.2)

      try:
        ts = Delaunay(pts).simplices
      except Exception:
        ts = []
      faces = []
      for f in ts:
        tri2 = Polygon(pts[f])
        if not poly.buffer(0.01).covers(tri2):
          continue
        pa = pts[f]
        lens = np.array([
          np.linalg.norm(pa[(i + 1) % 3] - pa[i]) for i in range(3)
        ])
        s = lens.sum() / 2.0
        area = max(s * (s - lens[0]) * (s - lens[1]) * (s - lens[2]), 0) ** 0.5
        if area < 0.02 or lens.max() / max(lens.min(), 1e-6) > 30:
          continue
        if lens.max() > 25:
          continue
        v3 = np.c_[pa, rz[f]]
        normal = np.cross(v3[1] - v3[0], v3[2] - v3[0])
        nn = np.linalg.norm(normal)
        if nn < 1e-6:
          continue
        slope = abs(normal[2]) / nn
        if slope < 0.25:
          continue
        faces.append(f.tolist())
      if not faces:
        verts = []
        mp = {}
        for x, y in ring:
          mp[(round(x, 3), round(y, 3))] = len(verts)
          verts.append([
            x, y,
            max(np.median(boundary[:, 2]), np.median(gz([[x, y]])) + 1.2)
          ])
        faces = []
        for tri_poly in triangulate(poly):
          coords = np.asarray(tri_poly.exterior.coords)[:-1]
          idx = []
          ok = True
          for x, y in coords:
            key = (round(x, 3), round(y, 3))
            if key not in mp:
              ok = False
              break
            idx.append(mp[key])
          if ok and len(idx) == 3:
            faces.append(idx)
        add(label + '_cubierta', verts, faces, [170, 109, 77, 255])
      else:
        add(label + '_cubierta', np.c_[pts, rz], faces,
            [170, 109, 77, 255])

      wallv = []
      wallf = []
      for rr in [poly.exterior, *poly.interiors]:
        q = np.asarray(rr.coords)
        top = np.maximum(bz(q), gz(q) + 1.2)
        base = gz(q) - 0.10
        for j in range(len(q) - 1):
          if np.linalg.norm(q[j + 1] - q[j]) < 0.05:
            continue
          k = len(wallv)
          wallv.extend([
            [q[j, 0], q[j, 1], base[j]],
            [q[j + 1, 0], q[j + 1, 1], base[j + 1]],
            [q[j + 1, 0], q[j + 1, 1], top[j + 1]],
            [q[j, 0], q[j, 1], top[j]],
          ])
          wallf.extend([[k, k + 1, k + 2], [k, k + 2, k + 3]])
      add(label + '_fachadas', wallv, wallf, [205, 190, 162, 255])
      used = used.union(poly)

  rot = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
  scene2 = scene.copy()
  scene2.apply_transform(rot)
  (P / 'santa_maria_v0_2.glb').write_bytes(scene2.export(file_type='glb'))

  with open(P / 'santa_maria_v0_2.obj', 'w') as f:
    f.write('mtllib santa_maria_v0_2.mtl\n')
    offset = 1
    uv = 1
    for name, m, _color in meshes:
      mat = ('terreno' if name.startswith('Terreno') else
             'cubierta' if name.endswith('cubierta') else 'fachada')
      f.write(f'o {name}\nusemtl {mat}\n')
      for v in m.vertices:
        f.write('v %.5f %.5f %.5f\n' % tuple(v))
      for face in m.faces:
        vv = m.vertices[face]
        normal = np.cross(vv[1] - vv[0], vv[2] - vv[0])
        axis = np.argmax(abs(normal))
        coords = np.delete(vv, axis, axis=1)
        for a, b in coords:
          f.write(f'vt {a:.5f} {b:.5f}\n')
        f.write('f ' + ' '.join(
          f'{offset + j}/{uv + k}' for k, j in enumerate(face)
        ) + '\n')
        uv += 3
      offset += len(m.vertices)

  (P / 'santa_maria_v0_2.mtl').write_text(
    'newmtl terreno\nKd .60 .56 .48\n'
    'newmtl cubierta\nKd .67 .43 .30\n'
    'newmtl fachada\nKd .80 .75 .64\n'
  )

if __name__ == '__main__':
  build()
