import {useEffect,useRef,useState} from 'react';
import {X,Upload,Undo2,Check} from 'lucide-react';
import type {Drawing} from './Rigs';
export function DrawingEditor({onSave,onClose,initial}:{onSave:(d:Drawing)=>void;onClose:()=>void;initial?:Drawing}){
  const canvas=useRef<HTMLCanvasElement>(null), input=useRef<HTMLInputElement>(null);
  const [part,setPart]=useState(0),[parts,setParts]=useState<string[]>(initial?.parts||['','']),[pivot,setPivot]=useState<[number,number]>(initial?.pivot||[200,160]);
  const [tool,setTool]=useState<'draw'|'pivot'>('draw'),[kind,setKind]=useState<'hinge'|'slider'>(initial?.kind||'hinge'),[axis,setAxis]=useState(initial?.axis||0),[travel,setTravel]=useState(initial?.travel||65);
  const drawing=useRef(false),[error,setError]=useState('');
  const commit=()=>{const next=[...parts];next[part]=canvas.current!.toDataURL('image/png');setParts(next);return next;};
  useEffect(()=>{const c=canvas.current!,g=c.getContext('2d')!;g.clearRect(0,0,400,320);if(parts[part]){const i=new Image();i.onload=()=>g.drawImage(i,0,0,400,320);i.src=parts[part];}},[part]);
  function point(e:React.PointerEvent){const r=canvas.current!.getBoundingClientRect();return [(e.clientX-r.left)/r.width*400,(e.clientY-r.top)/r.height*320] as [number,number]}
  return <div className="modal-backdrop"><section className="modal drawing-modal" aria-label="Assisted drawing rig editor">
    <div className="section-heading"><div><span className="eyebrow">MAKE IT YOURS</span><h2>Two parts. Your creation.</h2></div><button className="icon-btn" onClick={onClose} aria-label="Close drawing editor"><X size={20}/></button></div>
    <p>Draw or import each part on the same canvas. Place the joint yourself, then bind your copied control.</p>
    <div className="segmented">{['Part A · fixed','Part B · moving'].map((s,i)=><button key={i} className={part===i?'active':''} onClick={()=>{commit();setPart(i)}}>{s}</button>)}</div>
    <div className="draw-surface">
      {parts[1-part]&&<img className="ghost-part" src={parts[1-part]} alt="Other part placement"/>}
      <canvas width="400" height="320" ref={canvas} onPointerDown={e=>{const [x,y]=point(e);if(tool==='pivot'){setPivot([x,y]);return;}drawing.current=true;e.currentTarget.setPointerCapture(e.pointerId);const g=canvas.current!.getContext('2d')!;g.beginPath();g.moveTo(x,y);g.strokeStyle=part===0?'#d8ded7':'#e67564';g.lineWidth=12;g.lineCap='round';g.lineJoin='round'}} onPointerMove={e=>{if(!drawing.current)return;const [x,y]=point(e);const g=canvas.current!.getContext('2d')!;g.lineTo(x,y);g.stroke()}} onPointerUp={()=>{drawing.current=false;commit()}}/>
      <span className="pivot-handle" style={{left:`${pivot[0]/4}%`,top:`${pivot[1]/3.2}%`}}>+</span>
    </div>
    <div className="row"><button className={tool==='draw'?'active':''} onClick={()=>setTool('draw')}>Draw</button><button className={tool==='pivot'?'active':''} onClick={()=>setTool('pivot')}>Place pivot</button><button onClick={()=>input.current?.click()}><Upload size={14}/> Import PNG</button><button onClick={()=>{canvas.current!.getContext('2d')!.clearRect(0,0,400,320);commit()}}><Undo2 size={14}/> Clear part</button></div>
    <input type="file" ref={input} hidden accept="image/png,image/jpeg,image/webp" onChange={e=>{const f=e.target.files?.[0];if(!f)return;if(f.size>5e6){setError('Use an image smaller than 5 MB.');return;}const url=URL.createObjectURL(f),im=new Image();im.onload=()=>{const g=canvas.current!.getContext('2d')!;g.clearRect(0,0,400,320);const s=Math.min(400/im.width,320/im.height);g.drawImage(im,(400-im.width*s)/2,(320-im.height*s)/2,im.width*s,im.height*s);URL.revokeObjectURL(url);commit()};im.src=url}}/>
    <div className="draw-settings"><label>Joint<select value={kind} onChange={e=>setKind(e.target.value as 'hinge'|'slider')}><option value="hinge">Hinge</option><option value="slider">Slide</option></select></label><label>{kind==='hinge'?'Rotation (degrees)':'Travel (pixels)'}<input type="number" value={travel} min="-300" max="300" onChange={e=>setTravel(Math.max(-300,Math.min(300,+e.target.value)))}/></label>{kind==='slider'&&<label>Axis (degrees)<input type="number" value={axis} onChange={e=>setAxis(+e.target.value)}/></label>}</div>
    {error&&<p role="alert" className="error-text">{error}</p>}
    <button className="primary wide" onClick={()=>{const p=commit();if(p.some(x=>!x)){setError('Add both parts before binding.');return;}onSave({parts:p,pivot,kind,axis,travel})}}><Check size={16}/> Save & bind drawing</button>
  </section></div>
}
