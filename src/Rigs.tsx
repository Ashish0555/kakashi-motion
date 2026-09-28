import {useEffect,useState} from 'react';
export type Drawing={parts:string[];pivot:[number,number];kind:'hinge'|'slider';axis:number;travel:number};
export type RigName='dragon'|'flower'|'claw'|'drawing';

export function Rig({kind,value,drawing,small=false}:{kind:RigName;value:number;drawing?:Drawing;small?:boolean}){
  const [u,setU]=useState(value);
  useEffect(()=>{let raf:number;let old=performance.now();const update=(t:number)=>{const dt=t-old;old=t;setU(p=>Math.abs(p-value)<.0001?value:p+(value-p)*(1-Math.exp(-dt/22)));raf=requestAnimationFrame(update)};raf=requestAnimationFrame(update);return()=>cancelAnimationFrame(raf)},[value]);
  const id=small?`mini-${kind}`:`main-${kind}`;
  return <svg viewBox="0 0 600 450" className={`rig ${small?'mini':''}`} aria-label={`${kind} animated by the copied control`} role="img">
    <defs>
      <linearGradient id={`${id}-metal`} x1="0" y1="0" x2=".8" y2="1"><stop stopColor="#f4f0e4"/><stop offset=".4" stopColor="#9da9ad"/><stop offset="1" stopColor="#3c484e"/></linearGradient>
      <linearGradient id={`${id}-red`} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#ff8f76"/><stop offset=".45" stopColor="#d55045"/><stop offset="1" stopColor="#713b40"/></linearGradient>
      <linearGradient id={`${id}-petal`}><stop stopColor="#d2a79c"/><stop offset=".55" stopColor="#f2d9c7"/><stop offset="1" stopColor="#ac645d"/></linearGradient>
      <radialGradient id={`${id}-shadow`}><stop stopColor="#000" stopOpacity=".5"/><stop offset="1" stopColor="#000" stopOpacity="0"/></radialGradient>
    </defs>
    {!small&&<><ellipse cx="300" cy="375" rx="180" ry="35" fill={`url(#${id}-shadow)`}/><ellipse cx="300" cy="375" rx="168" ry="27" fill="none" stroke="#727b80" strokeOpacity=".15"/><ellipse cx="300" cy="375" rx="105" ry="17" fill="none" stroke="#727b80" strokeOpacity=".15"/></>}
    {kind==='dragon'&&<g>
      {[1,-1].map(side=><g key={side} transform={`translate(300 225) scale(${side} 1)`}>
        <g transform={`rotate(${-43+u*53})`}>
          <path d="M-20 10 Q-91 -100 -229 -94 L-198 -13 Q-163 -38 -144 22 Q-119 0 -89 58 Q-52 28 -20 55Z" fill={`url(#${id}-red)`} stroke="#ec9f88" strokeWidth="1.8"/>
          <path d="M-20 10 Q-90 -94 -229 -94 M-20 10 -198 -13 M-20 10 -144 22 M-20 10 -89 58" fill="none" stroke="#3a3538" strokeWidth="5"/>
          <path d="M-21 7 Q-90 -97 -229 -97 L-226 -110 Q-99 -110 -13 1Z" fill={`url(#${id}-metal)`}/>
          <circle cx="-22" cy="12" r="11" fill="#20282e" stroke="#bfc4bd" strokeWidth="3"/>
        </g>
        <path d="M-22 35 -53 97 -24 91 -10 65" fill={`url(#${id}-metal)`} stroke="#3b454a" strokeWidth="2"/>
      </g>)}
      <path d="M297 260 Q350 311 334 343 Q319 362 281 345 Q317 345 304 324 L275 280Z" fill={`url(#${id}-metal)`}/>
      <path d="M281 190 Q256 211 274 284 L300 309 326 283 Q344 212 319 188Z" fill={`url(#${id}-metal)`} stroke="#d7d8c6" strokeWidth="1.5"/>
      <path d="M298 218 286 269 300 289 314 269 302 218" fill="#29343d"/>
      {[0,1,2,3].map(n=><path key={n} d={`M287 ${230+n*13} L300 ${237+n*13} L313 ${230+n*13}`} stroke="#d0cfc0" strokeWidth="2" fill="none"/>)}
      <path d="M273 161 263 116 289 143 300 136 313 143 338 116 328 164 337 184 316 214 284 214 263 184Z" fill={`url(#${id}-metal)`} stroke="#d5d5c7" strokeWidth="1.5"/>
      <path d="M277 177 290 181 281 184M310 181 324 177 319 184" stroke="#ff655d" strokeWidth="4"/>
      <path d="M286 198 300 203 314 198" fill="none" stroke="#232c33" strokeWidth="3"/>
      <path d="M296 154 300 142 304 154 300 171Z" fill="#edf0db"/>
    </g>}
    {kind==='flower'&&<g>
      <path d="M300 354 Q284 295 303 233" stroke="#729084" strokeWidth="12" fill="none"/>
      <path d="M298 319 Q222 307 229 261 Q290 266 298 319Z" fill="#536f62" stroke="#90a997"/>
      <path d="M298 294 Q376 275 373 244 Q313 247 298 294Z" fill="#728b70" stroke="#a7b69c"/>
      <g transform="translate(300 199)">
        {Array.from({length:10},(_,i)=><g key={i} transform={`rotate(${i*36}) scale(${.34+u*.72} ${.56+u*.6})`}><path d="M0 17 C-30 -6 -67 -73 -37 -121 Q0 -164 37 -121 C67 -73 30 -6 0 17Z" fill={`url(#${id}-petal)`} stroke="#daada0" strokeWidth="1.4"/><path d="M0 0 Q-14 -63 0 -134" stroke="#a76f68" strokeWidth="1" opacity=".6" fill="none"/></g>)}
        {Array.from({length:7},(_,i)=><g key={i} transform={`rotate(${i*360/7+20}) scale(${.25+u*.37} ${.5+u*.25})`}><path d="M0 17 C-30 -6 -67 -73 -37 -121 Q0 -164 37 -121 C67 -73 30 -6 0 17Z" fill={`url(#${id}-red)`} stroke="#eea58f" strokeWidth="2"/></g>)}
        <circle r={15+u*16} fill="#bf9354"/>{Array.from({length:20},(_,i)=><circle key={i} cx={Math.cos(i*2.4)*Math.sqrt(i)*5} cy={Math.sin(i*2.4)*Math.sqrt(i)*5} r="2.5" fill="#f0d591"/>)}
      </g>
    </g>}
    {kind==='claw'&&<g>
      <path d="M251 370 251 337 268 323 274 233 326 233 332 323 349 337 349 370Z" fill={`url(#${id}-metal)`} stroke="#c0c8c4" strokeWidth="2"/>
      <path d="M283 345 283 275 317 275 317 345Z" fill="#242d32"/><path d="M294 319 294 276 306 276 306 319" fill={`url(#${id}-red)`}/>
      {[1,-1].map(side=><g key={side} transform={`translate(300 222) scale(${side} 1)`}>
        <g transform={`rotate(${5+u*46} -28 0)`}>
          <path d="M-11 14 -42 20 -106 -79 -87 -154 -55 -169 -71 -135 -73 -83Z" fill={`url(#${id}-metal)`} stroke="#d4d9cf" strokeWidth="2"/>
          <path d="M-30 4 -90 -81 -77 -139" fill="none" stroke="#d85e53" strokeWidth="6"/>
        </g><circle cx="-28" r="20" fill="#2a3439" stroke="#aab5b5" strokeWidth="4"/><circle cx="-28" r="7" fill="#d56254"/>
      </g>)}
      <path d="M270 224 330 224 320 249 280 249Z" fill={`url(#${id}-metal)`} stroke="#b5beb8"/>
    </g>}
    {kind==='drawing'&&drawing&&<g transform="translate(50 25) scale(1.25)">
      <image href={drawing.parts[0]} width="400" height="320"/>
      <g transform={drawing.kind==='hinge'?`rotate(${u*drawing.travel} ${drawing.pivot[0]} ${drawing.pivot[1]})`:`translate(${Math.cos(drawing.axis*Math.PI/180)*u*drawing.travel} ${Math.sin(drawing.axis*Math.PI/180)*u*drawing.travel})`}>
        <image href={drawing.parts[1]} width="400" height="320"/>
      </g>
    </g>}
  </svg>;
}
