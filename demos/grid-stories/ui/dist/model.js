export const SCENARIOS={
 heatwave:{name:'Heat-wave evening',number:'01',difficulty:'●○○ FOUNDATION',headline:'The hottest hour.<br>A little breathing room.',intro:'Air conditioners work overtime. Batteries can ease the evening peak—but the location of that support matters.',objective:'Support the neighborhood through its evening peak. Keep the 20% backup reserve intact.',start:1110,markers:['18:30','Demand rises','Peak support','19:30']},
 rebound:{name:'Charging rebound',number:'02',difficulty:'●●○ INTERMEDIATE',headline:'Cheap energy.<br>Expensive consequences.',intro:'A price drop tells every battery to charge. The market sees one fleet. The neighborhood feels every kilowatt.',objective:'Keep the feeder inside its limits. Find a safer place for the next battery.',start:1170,markers:['19:30','Price drops','Peak rebound','20:30']},
 covert:{name:'Covert channel',number:'03',difficulty:'●●● INVESTIGATION',headline:'The market is quiet.<br>The street is talking.',intro:'A fictional intruder nudges 24 batteries by just 350 watts. Fleet tracking stays inside tolerance. Local physics tells a different story.',objective:'Find the patterned residual, check the voltage evidence, and quarantine the compromised cohort.',start:1170,markers:['19:30','Signal begins','Detect & respond','20:30']}
};
export function rankCandidates(rows,lambda=1){return rows.map(r=>({...r,score:r.value-lambda*r.risk})).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id)).map((r,i)=>({...r,rank:i+1}));}
export function timeLabel(minutes){return `${String(Math.floor(minutes/60)).padStart(2,'0')}:${String(minutes%60).padStart(2,'0')}`;}
export function compliant(f){return f.overloaded===0&&f.voltageViolations===0;}
export function storyFor(scenario,frame,policy,response){
 const s=frame.step;
 if(scenario==='rebound'){
  if(s<3)return {title:'Before the rebound',text:'The neighborhood is within its limits. At 19:45, a scripted price drop sends a charge request to 96 homes.',chapter:1};
  if(policy==='naive')return {title:'One signal. Too much load.',text:`${frame.overloaded} transformers are overloaded. The weakest home falls to ${frame.minVoltage.toFixed(3)} pu, even while the fleet follows its charge request.`,chapter:s<7?2:3};
  return {title:'Headroom changes the decision.',text:`Charging moves toward connections with room. ${frame.shortfallKW.toFixed(0)} kW of market position is given up; ${frame.overloaded} transformers remain overloaded.`,chapter:s<7?3:4};
 }
 if(scenario==='heatwave'){
  if(s<3)return {title:'The evening shift begins',text:'96 batteries carry stored energy into the hottest hour. Every device starts at 72% charge, with a hard 20% reserve.',chapter:1};
  if(s<9)return {title:'Support has an electrical address.',text:`The fleet discharges ${Math.abs(frame.deliveredKW).toFixed(0)} kW. The weakest home measures ${frame.minVoltage.toFixed(3)} pu. Compare where each strategy sends the power.`,chapter:2};
  return {title:'Reserve preserved.',text:`The lowest battery is at ${(frame.minSoc*100).toFixed(0)}% charge. The reserve survives. Now test which uninstalled home adds the most useful support.`,chapter:4};
 }
 if(s<3)return {title:'Nothing unusual in the logs.',text:'Legitimate commands reach the fleet. The detector watches meter residuals and voltage changes against those commands.',chapter:1};
 if(!frame.flags.length)return {title:'Small signals start to repeat.',text:`A ±350 W pattern begins on the Cedar cohort. Aggregate tracking is ${frame.trackingOK?'within':'outside'} tolerance. The detector needs a sustained, correlated signal.`,chapter:2};
 if(response==='quarantine')return {title:'The cohort is quarantined.',text:`${frame.quarantined.length} flagged devices leave future commitments. This branch replays automatic quarantine from first detection, then redispatches the remaining fleet.`,chapter:4};
 return {title:'The feeder gives it away.',text:`${frame.flags.length} devices show structured meter residuals corroborated by voltage. First detection: ${Math.round(frame.detectionSeconds/60)} minutes after injection. Fixed 1 kW thresholds miss the signal.`,chapter:3};
}
