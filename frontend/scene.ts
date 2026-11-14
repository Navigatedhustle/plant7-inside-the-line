import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {box,cylinder,label,vehicle,bracket,robot,palette} from './geometry';
export type SceneState={chapter:number;cutaway:boolean;isolate:boolean;bright:boolean;paused:boolean;selected_fastener:string;cursor:number};
export class PlantScene{
 renderer:T.WebGLRenderer;scene=new T.Scene();camera=new T.PerspectiveCamera(35,1,.1,250);controls:OrbitControls;
 factory=new T.Group();detail=new T.Group();car=vehicle();component=bracket();overviewCars:T.Group[]=[];robots:{arm:T.Group}[]=[];
 targetPos=new T.Vector3();targetLook=new T.Vector3();state:SceneState;fps:number|null=null;frameSamples:number[]=[];lastFrame=0;lastRender=0;movingUntil=0;transition=true;pixelRatio=1;
 reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 markers:HTMLElement[]=[];tool=new T.Group();stationMarker=document.createElement('button');
 boltMaterials=[matFor(0x004bdf),matFor(0xf2a333)];
 constructor(public host:HTMLElement,public onSelect:(id:string)=>void,initial:SceneState){
  this.state=initial;
  this.renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.4));this.renderer.setClearColor(0xeaf0f5);this.renderer.outputColorSpace=T.SRGBColorSpace;this.renderer.toneMapping=T.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.3;host.append(this.renderer.domElement);
  this.scene.add(new T.HemisphereLight(0xffffff,0x8294a3,2.4));const sun=new T.DirectionalLight(0xffffff,3.0);sun.position.set(-5,18,12);this.scene.add(sun);const fill=new T.DirectionalLight(0xb8d3ff,1);fill.position.set(8,7,-10);this.scene.add(fill);
  this.scene.add(this.factory,this.detail);this.buildFactory();this.buildDetail();this.stationMarker.className='station-hotspot';this.stationMarker.textContent='Station 40 ↗';this.stationMarker.onclick=()=>this.onSelect('L3-S40');host.append(this.stationMarker);
  this.camera.position.set(34,35,39);this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.12;this.controls.maxPolarAngle=Math.PI*.48;this.controls.minDistance=3;this.controls.maxDistance=85;this.controls.addEventListener('start',()=>{this.transition=false;this.movingUntil=performance.now()+500});this.controls.addEventListener('change',()=>this.movingUntil=performance.now()+400);
  this.renderer.domElement.addEventListener('pointerup',e=>{const rect=host.getBoundingClientRect();const ray=new T.Raycaster();ray.setFromCamera(new T.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1),this.camera);const hits=ray.intersectObjects(this.component.bolts);if(hits[0]&&this.state.chapter>0)this.onSelect(hits[0].object.name);});
  const ro=new ResizeObserver(()=>this.resize());ro.observe(host);this.resize();this.update(initial,true);requestAnimationFrame(t=>this.frame(t));
 }
 buildFactory(){
  box(this.factory,[36,.25,34],[0,-.22,0],0xdce3e8,.15);
  for(let l=0;l<4;l++){
   const z=(l-1.5)*7.5;const focus=l===2;
   box(this.factory,[32,.02,4.8],[0,-.075,z],focus?0xc5d7ef:0xd0dbe1);
   for(const dz of [-2.3,2.3])box(this.factory,[32,.015,.045],[0,-.04,z+dz],focus?0x004bdf:0x9daeb9,0);
   label(this.factory,`LINE ${l+1}`,[-13,.01,z],.7,focus?'#004BDF':'#536b80');
   for(let station=0;station<4;station++){
    const x=(station-1.5)*6.8;
    if(l===2&&station===1){for(const dz of [-2.2,2.2])box(this.factory,[5.9,.03,.09],[x,-.025,z+dz],0xd49635,0);for(const dx of [-2.95,2.95])box(this.factory,[.09,.03,4.4],[x+dx,-.025,z],0xd49635,0);}
    box(this.factory,[5.5,.24,2.6],[x,.12,z],0x9bafb9);
    for(const dz of [-.77,.77]){box(this.factory,[5.45,.08,.12],[x,.29,z+dz],0x566b77);}
    for(let a=0;a<9;a++){const r=cylinder(this.factory,.09,2.25,[x-2.3+a*.56,.28,z],0xd9e0e4,8);r.rotation.x=Math.PI/2;}
    const car=vehicle(false,focus?0x789aba:0xb3c2ca);car.root.position.set(x,.3,z);car.root.scale.setScalar(.87);this.factory.add(car.root);this.overviewCars.push(car.root);
    if(station===1||station===3){const bot=robot();bot.root.position.set(x,.25,z+1.95);bot.root.scale.setScalar(1.25);this.factory.add(bot.root);this.robots.push(bot);}
    // Gantry posts, overhead track, control cabinets, work lamps and fixture stands.
    if(station%2===1){for(const dz of [-2.45,2.45]){box(this.factory,[.17,4.1,.17],[x,2,z+dz],0x9aaebb);box(this.factory,[.45,.05,.45],[x,.03,z+dz],0x687f8e);}box(this.factory,[.2,.22,5.2],[x,4.1,z],0x7d98ac);box(this.factory,[1,.08,.3],[x,3.9,z],0xf6f9fc);}
    box(this.factory,[.55,1.25,.6],[x+2.25,.65,z+1.8],0xf2f5f6);box(this.factory,[.05,.27,.35],[x+1.94,.95,z+1.8],0x3d667d);
   }
   box(this.factory,[27,.17,.18],[0,4.2,z],0x91a7b7);label(this.factory,focus?'STATION 40 · REVIEW':'ASSEMBLY',[-3.4,.01,z+2.7],.56,focus?'#a26815':'#758995');
  }
  // Cross aisle, lift structures and material racks give physical scale.
  for(const x of [-17,17])for(let i=0;i<5;i++){box(this.factory,[.6,.2,2],[x,.4+i*.3,-8],0xb3c6d1);}
 }
 buildDetail(){
  box(this.detail,[10,.16,7],[0,-.12,0],0xd9e2e9,.1);
  for(const z of [-1.55,1.55]){box(this.detail,[7.8,.18,.18],[0,.15,z],0x788f9d);for(let x=-3;x<=3;x+=1)box(this.detail,[.16,.35,.12],[x,.1,z],0x445d6e);}
  this.detail.add(this.car.root,this.component.root);
  for(const x of [-2.9,2.9])for(const z of [-2,2]){box(this.detail,[.16,3.5,.16],[x,1.6,z],0x8fa8bb);box(this.detail,[.38,.08,.4],[x,.01,z],0x485e70);}
  box(this.detail,[6,.18,.18],[0,3.35,-2],0x829caf);box(this.detail,[6,.18,.18],[0,3.35,2],0x829caf);
  const bot=robot();bot.root.position.set(-2.9,.1,1.65);this.detail.add(bot.root);
  box(this.detail,[.6,1.25,.55],[2.9,.62,1.7],0xedf2f6);box(this.detail,[.04,.28,.35],[2.57,.94,1.7],0x004bdf);
  box(this.tool,[.14,.57,.14],[0,.35,0],0x004bdf);cylinder(this.tool,.065,.22,[0,0,0],0x657f94,12);this.detail.add(this.tool);this.tool.visible=false;
  for(let i=0;i<4;i++){const marker=document.createElement('button');marker.className='fastener-marker';marker.textContent=`${i+1}`;marker.setAttribute('aria-label',`Select fastener B${i+1}`);marker.onclick=()=>this.onSelect(`B${i+1}`);this.host.append(marker);this.markers.push(marker);}
 }
 resize(){const {width,height}=this.host.getBoundingClientRect();this.renderer.setSize(width,height);this.camera.aspect=width/height;this.camera.updateProjectionMatrix();}
 update(state:SceneState,immediate=false){const change=state.chapter!==this.state.chapter||state.isolate!==this.state.isolate;this.state={...state};const overview=state.chapter===0;
  this.factory.visible=overview;this.detail.visible=!overview;this.car.root.visible=!state.isolate;
  this.detail.children.forEach(c=>{if(c!==this.component.root&&c!==this.car.root&&c!==this.tool)c.visible=!state.isolate;});
  this.car.shell.traverse(c=>{if(c instanceof T.Mesh){if(!c.userData.unique){c.material=(c.material as T.MeshStandardMaterial).clone();c.userData.unique=true;}const material=c.material as T.MeshStandardMaterial;material.transparent=state.cutaway;material.opacity=state.cutaway?.11:1;material.depthWrite=!state.cutaway;}});
  this.component.bolts.forEach(b=>b.material=this.boltMaterials[b.name===state.selected_fastener?1:0]);
  this.scene.background=new T.Color(state.bright||overview?0xeaf0f5:0x1b2935);this.renderer.toneMappingExposure=state.bright||overview?1.3:1.55;
  if(change||immediate)this.resetCamera(immediate);
  this.tool.visible=state.chapter===2;this.setTime(state.cursor);
 }
 setTime(cursor:number){this.state.cursor=cursor;const idx=Math.min(3,Math.max(0,Math.floor(cursor-3)));const [x,z]=this.component.positions[idx];this.tool.position.set(x,1.38,z);}
 resetCamera(immediate=false){const o=this.state.chapter===0;this.targetPos.set(...(o?[34,35,39]:this.state.isolate?[3,4.7,4.5]:[7,5.2,7.8]) as [number,number,number]);this.targetLook.set(...(o?[0,.4,0]:[0,1,.45]) as [number,number,number]);this.transition=true;if(immediate||this.reduced){this.camera.position.copy(this.targetPos);this.controls.target.copy(this.targetLook);this.transition=false;}this.movingUntil=performance.now()+1500;}
 orbit(){this.transition=false;const v=this.camera.position.clone().sub(this.controls.target);v.applyAxisAngle(new T.Vector3(0,1,0),Math.PI/6);this.camera.position.copy(this.controls.target).add(v);this.movingUntil=performance.now()+500;}
 frame(t:number){requestAnimationFrame(x=>this.frame(x));if(document.hidden||t-this.lastRender<31)return;
  const elapsed=t-this.lastRender;this.lastRender=t;if(this.lastFrame){this.frameSamples.push(1000/elapsed);if(this.frameSamples.length>300)this.frameSamples.shift();}if(this.frameSamples.length>=90)this.fps=this.frameSamples.slice(-90).reduce((a,b)=>a+b,0)/90;
  if(this.fps&&this.fps<24&&this.pixelRatio>.8){this.pixelRatio=.8;this.renderer.setPixelRatio(.8);}
  if(this.transition){this.camera.position.lerp(this.targetPos,.12);this.controls.target.lerp(this.targetLook,.12);if(this.camera.position.distanceTo(this.targetPos)<.02)this.transition=false;}
  if(!this.reduced&&!this.state.paused&&this.state.chapter===0)this.robots.forEach((r,i)=>r.arm.rotation.y=Math.sin(t*.00025+i)*.2);
  this.controls.update();this.renderer.render(this.scene,this.camera);this.lastFrame=t;
  const stationPos=new T.Vector3(-3.4,2.15,3.75).project(this.camera);this.stationMarker.hidden=this.state.chapter!==0;this.stationMarker.style.left=`${(stationPos.x*.5+.5)*this.host.clientWidth}px`;this.stationMarker.style.top=`${(-stationPos.y*.5+.5)*this.host.clientHeight}px`;
  this.component.bolts.forEach((b,i)=>{const v=b.getWorldPosition(new T.Vector3()).project(this.camera);const m=this.markers[i];m.hidden=![1,2].includes(this.state.chapter)||v.z>1;m.style.left=`${(v.x*.5+.5)*this.host.clientWidth}px`;m.style.top=`${(-v.y*.5+.5)*this.host.clientHeight-21}px`;m.classList.toggle('selected',b.name===this.state.selected_fastener);});
 }
}
function matFor(color:number){return new T.MeshStandardMaterial({color,metalness:.5,roughness:.3});}
