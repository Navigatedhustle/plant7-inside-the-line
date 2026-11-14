import * as T from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
export const palette={blue:0x004bdf,steel:0x71879a,silver:0xcbd3da,graphite:0x26333e,amber:0xf2a333};
const mats=new Map<string,T.MeshStandardMaterial>();
export function mat(color:number,metal=.35,rough=.45){const k=`${color},${metal},${rough}`;if(!mats.has(k))mats.set(k,new T.MeshStandardMaterial({color,metalness:metal,roughness:rough}));return mats.get(k)!;}
export function box(parent:T.Object3D,size:number[],pos:number[],color:number,bevel=.035){const m=new T.Mesh(bevel?new RoundedBoxGeometry(size[0],size[1],size[2],1,bevel):new T.BoxGeometry(...size as [number,number,number]),mat(color));m.position.set(...pos as [number,number,number]);parent.add(m);return m;}
export function cylinder(parent:T.Object3D,r:number,h:number,pos:number[],color:number,segments=16){const m=new T.Mesh(new T.CylinderGeometry(r,r,h,segments),mat(color));m.position.set(...pos as [number,number,number]);parent.add(m);return m;}
function profile(parent:T.Object3D,points:number[][],depth:number,z:number,color:number){const s=new T.Shape();points.forEach((p,i)=>i?s.lineTo(p[0],p[1]):s.moveTo(p[0],p[1]));s.closePath();const g=new T.ExtrudeGeometry(s,{depth,bevelEnabled:true,bevelSegments:1,steps:1,bevelSize:.035,bevelThickness:.035});const mesh=new T.Mesh(g,mat(color));mesh.position.z=z;parent.add(mesh);return mesh;}
export function label(parent:T.Object3D,text:string,pos:number[],size=1.5,color='#35516c'){
 const c=document.createElement('canvas');c.width=768;c.height=128;const ctx=c.getContext('2d')!;ctx.fillStyle=color;ctx.font='600 58px Arial';ctx.textAlign='center';ctx.fillText(text,384,80);
 const texture=new T.CanvasTexture(c);texture.colorSpace=T.SRGBColorSpace;const m=new T.Mesh(new T.PlaneGeometry(size*5,size*.83),new T.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false,side:T.DoubleSide}));m.position.set(...pos as [number,number,number]);m.rotation.x=-Math.PI/2;parent.add(m);return m;
}
export function vehicle(detailed=true,color=0x90a8be){
 const root=new T.Group(),shell=new T.Group(),chassis=new T.Group();root.add(chassis,shell);
 // Original 4.7m SUV proportions. Mesh groups allow later licensed CAD replacement.
 for(const z of [-.72,.72])box(chassis,[4.35,.18,.14],[0,.62,z],palette.graphite);
 for(const x of [-1.55,-.55,.6,1.5])box(chassis,[.14,.14,1.7],[x,.64,0],palette.steel);
 box(chassis,[3.55,.12,1.72],[0,.82,0],0x596d7b);box(chassis,[2.3,.2,1.45],[.2,.58,0],0x344852);
 for(const x of [-1.46,1.5]){
  const axle=cylinder(chassis,.08,2.15,[x,.49,0],palette.steel);axle.rotation.x=Math.PI/2;
  for(const z of [-1.02,1.02]){
   const tire=cylinder(chassis,.46,.25,[x,.48,z],0x20272d,24);tire.rotation.x=Math.PI/2;
   const rim=cylinder(chassis,.285,.27,[x,.48,z*1.01],0x94a5b1,16);rim.rotation.x=Math.PI/2;
   const hub=cylinder(chassis,.1,.29,[x,.48,z*1.015],palette.graphite,12);hub.rotation.x=Math.PI/2;
   if(detailed)for(let a=0;a<6;a++){const spoke=box(chassis,[.36,.06,.015],[x+Math.cos(a*Math.PI/3)*.09,.48+Math.sin(a*Math.PI/3)*.09,z*1.15],0xdce3e9,.01);spoke.rotation.z=a*Math.PI/3;}
  }
 }
 const body=[[-2.3,.85],[-2.27,1.15],[-1.55,1.27],[-1.0,1.33],[1.5,1.32],[2.25,1.18],[2.34,.85]];
 profile(shell,body,1.9,-.95,color);
 // Cabin frame, pitched windshield, distinct rear hatch and continuous door seams.
 for(const z of [-.93,.91]){
  profile(shell,[[-1.15,1.3],[-.64,2.02],[1.23,2.02],[1.88,1.35]],.04,z,color);
  profile(shell,[[-1.04,1.4],[-.57,1.91],[.15,1.91],[.15,1.4]],.05,z-.006,0x243f50);
  profile(shell,[[.27,1.4],[.27,1.91],[1.16,1.91],[1.65,1.4]],.05,z-.006,0x243f50);
  for(const x of [.2,1.35])box(shell,[.018,.63,.025],[x,1.07,z*1.04],0x5c7385,.003);
  for(const x of [-.35,.85])box(shell,[.22,.035,.04],[x,1.33,z*1.055],0xced9e1,.012);
  box(shell,[3.75,.09,.1],[.05,.82,z*1.07],palette.graphite);
  box(shell,[2.0,.055,.06],[.32,2.09,z*.8],palette.graphite);
  box(shell,[.29,.13,.2],[-.92,1.48,z*1.18],color);
 }
 box(shell,[1.88,.09,1.88],[.33,2.02,0],color,.055);
 const front=box(shell,[.055,.66,1.75],[-.94,1.68,0],0x294656);front.rotation.z=-.59;
 const back=box(shell,[.05,.64,1.75],[1.55,1.66,0],0x294656);back.rotation.z=.66;
 for(const x of [-2.3,2.32]){
  box(shell,[.16,.2,1.85],[x,.82,0],palette.graphite);
  for(const z of [-.71,.71])box(shell,[.07,.12,.37],[x,1.12,z],x<0?0xe5f2ff:0xbe3b32);
 }
 for(let i=0;i<5;i++)box(shell,[.035,.025,.91],[-2.33,.99+i*.04,0],0x394c59,.005);
 if(detailed){
  for(const x of [-.5,.75])for(const z of [-.43,.43]){box(chassis,[.58,.22,.55],[x,1.0,z],0x3d4d58);box(chassis,[.13,.6,.54],[x+.22,1.28,z],0x3d4d58);}
  box(chassis,[.32,.65,.65],[-1.1,1.13,0],0x566a79);
 }
 return {root,shell,chassis};
}
export function bracket(){const root=new T.Group();
 box(root,[1.45,.15,1.25],[0,1.02,.72],palette.graphite);
 box(root,[1.17,.12,1.08],[0,1.14,.72],0xa9bbc9);
 box(root,[.45,.13,.8],[0,1.265,.72],0x46789f);
 box(root,[.15,.45,.6],[0,1.46,.72],0x779ebd);
 const bolts:T.Mesh[]=[];
 const positions=[[-.43,.32],[.43,.32],[.43,1.12],[-.43,1.12]];
 positions.forEach(([x,z],i)=>{cylinder(root,.11,.025,[x,1.215,z],0x394d60);const b=cylinder(root,.082,.09,[x,1.26,z],palette.blue,6);b.name=`B${i+1}`;b.userData={entity:`B${i+1}`};bolts.push(b);});
 for(const z of [.08,1.4]){box(root,[1.6,.12,.17],[0,.95,z],0x8fa4b1);for(const x of [-.6,.6]){cylinder(root,.04,.19,[x,1.01,z],0x242d38);box(root,[.12,.12,.1],[x,1.11,z],0xe5a33e);}}
 return {root,bolts,positions};}
export function robot(){const root=new T.Group();cylinder(root,.42,.28,[0,.14,0],palette.graphite);cylinder(root,.28,.5,[0,.5,0],0xb4c2ca);const arm=new T.Group();arm.position.y=.75;root.add(arm);box(arm,[.25,1.05,.3],[0,.48,0],0xd5ab64);const joint=cylinder(arm,.22,.38,[0,1.03,0],palette.graphite);joint.rotation.x=Math.PI/2;const fore=box(arm,[.25,.93,.25],[.22,1.34,0],0xd5ab64);fore.rotation.z=-.65;box(arm,[.14,.18,.34],[.47,1.68,0],palette.steel);return {root,arm};}
