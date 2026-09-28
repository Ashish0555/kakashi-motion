export type Point = [number, number];
export type Box = [number, number, number, number];
export type Mapping = {invert:boolean;sensitivity:number;dead_zone:number;smoothing_ms:number};
export type FrameState = {
  type:string; frame_id:number; capture_t:number; phase:string; samples:number;
  tracking:string; reason:string; control:{value:number;raw:number;filtered:number;available:boolean;status:string;smoothing_ms:number};
  parts:{polygon:Point[];valid:boolean;inliers:number;points:Point[]}[];
  timing:{processing_ms:number;tracking_ms:number;decode_ms:number;p50_ms:number;p95_ms:number};
  backend:{name:string;provider:string|string[];model_ms:number|null;features_ms:number;neural_refresh_hz?:number;npu_verified:boolean};
};

export class Transport {
  ws:WebSocket;
  sequence=0;
  frameSequence=0;
  pending=new Map<number,{resolve:(x:any)=>void;reject:(e:Error)=>void;timer:ReturnType<typeof setTimeout>}>();
  framePending:null|{resolve:(x:FrameState)=>void;reject:(e:Error)=>void;timer:ReturnType<typeof setTimeout>}=null;
  ready:Promise<void>;
  onDisconnect:()=>void=()=>{};
  constructor(){
    this.ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
    this.ready=new Promise((resolve,reject)=>{
      this.ws.onopen=()=>resolve();this.ws.onerror=()=>reject(new Error('The local service is not connected. Start Kakashi and reload.'));
    });
    this.ws.onmessage=e=>{
      const m=JSON.parse(e.data);
      if(m.request_id && this.pending.has(m.request_id)){
        const p=this.pending.get(m.request_id)!;clearTimeout(p.timer);this.pending.delete(m.request_id);
        m.type==='error'?p.reject(new Error(m.message)):p.resolve(m);
      }else if((m.type==='frame'||m.type==='error')&&this.framePending){
        const p=this.framePending;this.framePending=null;clearTimeout(p.timer);
        m.type==='error'?p.reject(new Error(m.message)):p.resolve(m);
      }
    };
    this.ws.onclose=()=>{
      const err=new Error('Local service disconnected. Reconnect, then reload your saved controller.');
      this.pending.forEach(p=>{clearTimeout(p.timer);p.reject(err)});this.pending.clear();
      if(this.framePending){clearTimeout(this.framePending.timer);this.framePending.reject(err);this.framePending=null;}
      this.onDisconnect();
    };
  }
  async command(data:Record<string,unknown>):Promise<any>{
    await this.ready;
    if(this.ws.readyState!==WebSocket.OPEN)throw new Error('Local service disconnected. Reload the page after restarting it.');
    const request_id=++this.sequence;
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(request_id);reject(new Error('The service did not respond. Retry or restart Kakashi.'));},15000);
      this.pending.set(request_id,{resolve,reject,timer});
      this.ws.send(JSON.stringify({...data,request_id}));
    });
  }
  async frame(jpeg:Blob, capture_t:number):Promise<FrameState>{
    await this.ready;
    if(this.framePending)throw new Error('A camera frame is already in flight.');
    const frame_id=++this.frameSequence;
    const header=new TextEncoder().encode(JSON.stringify({frame_id,capture_t}));
    const size=new ArrayBuffer(4);new DataView(size).setUint32(0,header.length,true);
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.framePending=null;reject(new Error('Camera processing timed out. Reconnect and retry.'));},10000);
      this.framePending={resolve,reject,timer};
      this.ws.send(new Blob([size,header,jpeg]));
    });
  }
}

export class Capture {
  video=document.createElement('video');
  buffer=document.createElement('canvas');
  stream:MediaStream|null=null;
  paused=false; stopped=false; inFlight:Promise<void>|null=null;
  width=640;height=480;
  onFrame:(state:FrameState,age:number)=>void;
  onError:(error:Error)=>void;
  source='camera';
  objectURL:string|null=null;
  constructor(public transport:Transport,public display:HTMLCanvasElement,onFrame:Capture['onFrame'],onError:Capture['onError']){
    this.onFrame=onFrame;this.onError=onError;this.video.muted=true;this.video.playsInline=true;
  }
  async start(source:string,deviceId?:string,file?:File){
    this.source=source;
    if(source==='camera'){
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('Camera access requires localhost and a supported browser.');
      try{this.stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:640},height:{ideal:480},frameRate:{ideal:30,max:30},...(deviceId?{deviceId:{exact:deviceId}}:{})},audio:false});}
      catch(e){const name=e instanceof DOMException?e.name:'';throw new Error(name==='NotAllowedError'?'Camera access was denied. Allow it in the browser’s address bar, then reconnect.':name==='NotFoundError'?'No camera was found. Connect a webcam or open a recorded video.':name==='NotReadableError'?'Camera is busy or unavailable. Close other camera apps and reconnect.':'Could not open this camera. Reconnect it or choose a recorded video.');}
      this.video.srcObject=this.stream;
    }else{
      this.video.src=file?(this.objectURL=URL.createObjectURL(file)):`/fixtures/${source}.webm`;
      this.video.loop=false;
    }
    try{await this.video.play();}catch{this.stream?.getTracks().forEach(t=>t.stop());throw new Error('This video could not be played. Try a WebM or a browser-supported MP4 file.');}
    const ratio=Math.min(640/this.video.videoWidth,480/this.video.videoHeight);
    this.width=Math.round(this.video.videoWidth*ratio);this.height=Math.round(this.video.videoHeight*ratio);
    this.buffer.width=this.display.width=this.width;this.buffer.height=this.display.height=this.height;
    this.tick();
  }
  async pause(){this.paused=true;if(this.source!=='camera')this.video.pause();await this.inFlight;}
  async resume(){this.paused=false;if(this.source!=='camera')await this.video.play();}
  tick=()=>{
    if(this.stopped)return;
    if(!this.paused&&!this.inFlight&&this.video.readyState>=2&&!this.video.ended){
      this.inFlight=this.send().catch(e=>{this.paused=true;this.onError(e)}).finally(()=>{this.inFlight=null});
    }
    setTimeout(this.tick,1000/30);
  };
  async send(){
    const timestamp=performance.now()/1000;
    this.buffer.getContext('2d')!.drawImage(this.video,0,0,this.width,this.height);
    const jpeg=await new Promise<Blob>((resolve,reject)=>this.buffer.toBlob(b=>b?resolve(b):reject(new Error('Camera frame could not be encoded.')),'image/jpeg',.84));
    if(this.stopped)return;
    const state=await this.transport.frame(jpeg,timestamp);
    if(this.stopped)return;
    // The displayed image and overlays always have exactly the same frame ID.
    this.display.getContext('2d')!.drawImage(this.buffer,0,0);
    this.onFrame(state,performance.now()-timestamp*1000);
  }
  async stop(){this.stopped=true;this.video.pause();this.stream?.getTracks().forEach(t=>t.stop());await this.inFlight;if(this.objectURL)URL.revokeObjectURL(this.objectURL);}
}
