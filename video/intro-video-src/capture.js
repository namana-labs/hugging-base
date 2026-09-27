const {chromium}=require('playwright');const {spawn}=require('child_process');
(async()=>{
 const FPS=+process.env.FPS||60, T0=+(process.env.T0||0), T1=+(process.env.T1||31.3), out=process.env.OUT||'video.mp4';
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:1920,height:1080}});
 p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto('http://127.0.0.1:8777/index.html?capture');await p.evaluate(()=>window.ready);
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','png','-i','-','-c:v','libx264','-preset','medium','-crf','14','-pix_fmt','yuv420p','-tune','animation',out],{stdio:['pipe','inherit','inherit']});
 const n=Math.round((T1-T0)*FPS);const st=Date.now();
 for(let i=0;i<n;i++){const t=T0+i/FPS;
   const b64=await p.evaluate(t=>{render(t);return document.getElementById('c').toDataURL('image/png').slice(22);},t);
   const buf=Buffer.from(b64,'base64');if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));
   if(i%300===0)console.log(i,n,((Date.now()-st)/1000).toFixed(1)+'s');}
 ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done',((Date.now()-st)/1000).toFixed(1));
})();
