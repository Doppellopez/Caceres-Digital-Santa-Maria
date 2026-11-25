import json, numpy as np, trimesh
from scipy.spatial import Delaunay, cKDTree
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from shapely.geometry import Polygon, Point, box, MultiPoint
from shapely.geometry.polygon import orient
from shapely.ops import triangulate, unary_union
from shapely import make_valid
from pathlib import Path
P=Path(__file__).parent
D=json.load(open(P/'santa_maria_dxf_local.json')); U=next(v for k,v in D.items() if 'trama' in k); R=next(v for k,v in D.items() if 'relieve' in k)
Z0=440.; bounds=box(-75,-75,75,75)
def parts(g):
 if g.geom_type=='Polygon': return [g]
 if hasattr(g,'geoms'): return [p for x in g.geoms for p in parts(x)]
 return []
def uniq(a):
 a=np.asarray(a); xy,inv=np.unique(np.round(a[:,:2],3),axis=0,return_inverse=True); z=np.array([np.median(a[inv==i,2]) for i in range(len(xy))]); return np.c_[xy,z]
ground=uniq([p for t,l,a,c,s in U+R if l in ('Punto cota','Escalera','Bordillo','Soportal','Pilar') for p in a if 420<p[2]<470 and abs(p[0])<150 and abs(p[1])<150]); lin=LinearNDInterpolator(ground[:,:2],ground[:,2]); near=NearestNDInterpolator(ground[:,:2],ground[:,2]);
def gz(xy):
 a=np.asarray(xy); z=lin(a); return np.where(np.isnan(z),near(a),z)
roof=uniq([p for t,l,a,c,s in U if l=='Limatesa y limahoyas' for p in a if 430<p[2]<480 and abs(p[0])<150 and abs(p[1])<150]); rt=cKDTree(roof[:,:2]);
scene=trimesh.Scene(); meshes=[]
def add(name,verts,faces,color):
 if not faces:return
 m=trimesh.Trimesh(vertices=np.asarray(verts)-[0,0,Z0],faces=faces,process=False); m.visual.face_colors=color; scene.add_geometry(m,node_name=name,geom_name=name); meshes.append((name,m,color))
# Ground TIN, interpolated on regular grid, augmented with surveyed vertices.
xy=np.unique(np.round(np.vstack([np.array([(x,y) for x in np.arange(-75,75.01,1) for y in np.arange(-75,75.01,1)]),ground[(abs(ground[:,:2])<=75).all(1),:2]]),3),axis=0); tri=Delaunay(xy).simplices; add('Terreno_interpolado',np.c_[xy,gz(xy)],tri.tolist(),[154,143,122,255])
# Closed cadastral outlines, prioritising variable-height 3D traces.
records=[]
for t,l,a,c,s in U:
 if not l.startswith('Edificio') or not c or len(a)<4:continue
 a=np.array(a); g=make_valid(Polygon(a[:,:2])).intersection(bounds)
 for p in parts(g):
  if p.area>2:records.append((t,l,a,p))
records.sort(key=lambda r:(r[0]!='POLYLINE',r[3].area))
used=Polygon(); n=0
for t,l,a,p in records:
 for poly in parts(p.difference(used)):
  if poly.area<2:continue
  poly=orient(poly,sign=1.0)
  n+=1; label=f'Edificio_{n:02d}'; boundary=uniq(a); bt=cKDTree(boundary[:,:2]);
  # Use surveyed heights at outline vertices; interpolate roof using nearby internal ridge points.
  ring=np.asarray(poly.exterior.coords)[:-1]; interior=roof[[poly.contains(Point(q)) for q in roof[:,:2]]];
  def bz(xy):
   dist,idx=bt.query(xy); z=boundary[idx,2].copy(); rd,ri=rt.query(xy); mask=(rd<0.25); z[mask]=roof[ri[mask],2]; return z
  verts=[]; faces=[]; wallv=[]; wallf=[]
  # Triangulation includes all boundary vertices and measured ridge samples; no inferred points outside footprint.
  pts=np.unique(np.round(np.vstack([ring,interior[:,:2]]),3),axis=0)
  if len(pts)<3:continue
  rz=bz(pts); d,i=rt.query(pts); rz[d<.015]=roof[i[d<.015],2]; rz=np.maximum(rz,gz(pts)+1)
  # triangulate using geometry with exact polygon boundary; discard triangles crossing boundary.
  try: ts=Delaunay(pts).simplices
  except Exception: continue
  for f in ts:
   if poly.buffer(.003).covers(Polygon(pts[f])):faces.append(f.tolist())
  add(label+'_cubierta',np.c_[pts,rz],faces,[170,109,77,255]);
  for rr in [poly.exterior,*poly.interiors]:
   q=np.asarray(rr.coords); top=np.maximum(bz(q),gz(q)+1); base=gz(q)-.15
   for j in range(len(q)-1):
    k=len(wallv); wallv.extend([[*q[j],base[j]],[*q[j+1],base[j+1]],[*q[j+1],top[j+1]],[*q[j],top[j]]]); wallf.extend([[k,k+1,k+2],[k,k+2,k+3]])
  add(label+'_fachadas',wallv,wallf,[205,190,162,255]);
 used=used.union(p)
# GLB exported in glTF's Y-up convention.
rot=trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]); scene.apply_transform(rot); (P/'santa_maria.glb').write_bytes(scene.export(file_type='glb'))
# OBJ is Z-up, with per-face planar UVs in metre units.
with open(P/'santa_maria.obj','w') as f:
 f.write('mtllib santa_maria.mtl\n'); offset=1; uv=1
 for name,m,c in meshes:
  mat='terreno' if name.startswith('Terreno') else 'cubierta' if name.endswith('cubierta') else 'fachada'; f.write(f'o {name}\nusemtl {mat}\n')
  for v in m.vertices:f.write('v %.5f %.5f %.5f\n'%tuple(v))
  for face in m.faces:
   vv=m.vertices[face]; normal=np.cross(vv[1]-vv[0],vv[2]-vv[0]); axis=np.argmax(abs(normal)); coords=np.delete(vv,axis,axis=1)
   for a,b in coords:f.write(f'vt {a:.5f} {b:.5f}\n')
   f.write('f '+' '.join(f'{offset+j}/{uv+k}' for k,j in enumerate(face))+'\n'); uv+=3
  offset+=len(m.vertices)
(P/'santa_maria.mtl').write_text('newmtl terreno\nKd .60 .56 .48\nnewmtl cubierta\nKd .67 .43 .30\nnewmtl fachada\nKd .80 .75 .64\n')
# preview
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
fig=plt.figure(figsize=(12,10)); ax=fig.add_subplot(projection='3d');
polys=[]; colors=[]
for name,m,c in meshes:
 v=m.vertices[m.faces]; normals=m.face_normals; light=np.array([-.5,-.6,.8]); light/=np.linalg.norm(light); shade=.65+.35*np.abs(normals@light); col=np.tile(np.array(c)/255,(len(v),1)); col[:,:3]*=shade[:,None]; polys.extend(v); colors.extend(col)
coll=Poly3DCollection(polys,facecolors=colors,edgecolors='none',antialiased=False); ax.add_collection3d(coll)
ax.set(xlim=(-75,75),ylim=(-75,75),zlim=(-12,32)); ax.set_box_aspect((150,150,44)); ax.view_init(48,-65); ax.set_axis_off(); fig.savefig(P/'santa_maria_preview.png',dpi=140,bbox_inches='tight'); print('buildings',n,'meshes',len(meshes),'ground samples',len(ground),'roof samples',len(roof),'faces',sum(len(m.faces) for _,m,_ in meshes))
