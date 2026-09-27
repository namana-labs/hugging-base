const {chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'}).catch(async()=>await chromium.launch());
 const p=await b.newPage({viewport:{width:1920,height:1080}});
 p.on('console',m=>console.log('console',m.text())); p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto('http://127.0.0.1:8777/index.html?capture');
 await p.evaluate(()=>window.ready);
 const ts=(process.argv[2]||'0.8,3,4.6,6.3,7.4,10,13.5,18,22.5,25.8,29,33.5,38.5,44').split(',').map(Number);
 for(const t of ts){await p.evaluate(t=>render(t),t);await p.screenshot({path:`st/s_${t.toFixed(2)}.png`});}
 await b.close();
})();
