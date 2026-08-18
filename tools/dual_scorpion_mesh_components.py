#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,struct
from pathlib import Path
import numpy as np

FILES=["ds_urdf_v4_1.stl","right_link_2.stl","ds_urdf_v4.stl","right_link_5.stl"]

def read(path):
 d=path.read_bytes(); n=struct.unpack_from('<I',d,80)[0]
 if 84+50*n!=len(d): raise RuntimeError(path)
 dt=np.dtype([('normal','<f4',(3,)),('verts','<f4',(3,3)),('attr','<u2')])
 return np.asarray(np.frombuffer(d,dtype=dt,offset=84,count=n)['verts'],dtype=np.float64)

def components(tri):
 # STL exports duplicate vertices, so quantize tightly and union facets sharing a vertex.
 scale=1e8
 keys=np.rint(tri.reshape(-1,3)*scale).astype(np.int64)
 parent=np.arange(len(tri),dtype=np.int64); rank=np.zeros(len(tri),dtype=np.int8)
 def find(x):
  while parent[x]!=x:
   parent[x]=parent[parent[x]]; x=parent[x]
  return int(x)
 def union(a,b):
  a=find(a); b=find(b)
  if a==b:return
  if rank[a]<rank[b]:a,b=b,a
  parent[b]=a
  if rank[a]==rank[b]:rank[a]+=1
 seen={}
 for vi,k in enumerate(map(tuple,keys)):
  f=vi//3
  old=seen.get(k)
  if old is None: seen[k]=f
  else: union(f,old)
 groups={}
 for i in range(len(tri)): groups.setdefault(find(i),[]).append(i)
 rows=[]
 total_area=0.0
 for ids in groups.values():
  t=tri[np.asarray(ids)]; p=t.reshape(-1,3)
  area=float((0.5*np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)).sum()); total_area+=area
  rows.append({'facets':len(ids),'area':area,'bbox_min':p.min(axis=0).tolist(),'bbox_max':p.max(axis=0).tolist(),'centroid':p.mean(axis=0).tolist()})
 rows.sort(key=lambda r:r['area'],reverse=True)
 for r in rows:r['area_fraction']=r['area']/max(total_area,1e-30)
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('repo',type=Path);a=ap.parse_args();root=a.repo/'dual_scorpion_Full_urdf/meshes'
 out={}
 for name in FILES:
  c=components(read(root/name));out[name]={'component_count':len(c),'components':c[:20]}
 print(json.dumps(out,indent=2,sort_keys=True))
if __name__=='__main__':main()
