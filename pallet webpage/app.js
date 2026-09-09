/* Pallet Atlas: dependency-free 3D projection and local study explorer. */
(() => {
  'use strict';
  const data = window.PALLET_DATA;
  if (!data || !Array.isArray(data.boxes) || !data.boxes.length) {
    document.querySelector('main').innerHTML = '<section class="panel" style="padding:32px"><h1>Dataset unavailable</h1><p>Keep data.js beside index.html, styles.css, and app.js, then reopen this page.</p></section>';
    return;
  }
  const boxes = [...data.boxes].sort((a,b) => a.box_number-b.box_number);
  const threshold = data.metadata?.threshold ?? 4;
  const hours = [0,6,12,18,24];
  const query = new URLSearchParams(location.search);
  const initial = boxes.find(b => b.box_id === query.get('box')) || boxes[0];
  const state = { selected: initial.box_id, hour:hours.includes(Number(query.get('hour'))) && query.has('hour') ? Number(query.get('hour')) : 24, layer:'all', yaw:-.68, elevation:.52, zoom:1, explode:0, hover:null };
  const canvas = document.getElementById('pallet-canvas');
  const ctx = canvas.getContext('2d');
  const wrap = document.getElementById('canvas-wrap');
  const tooltip = document.getElementById('hover-tip');
  let width=0, height=0, dpr=1, faces=[], pointer=null, animation=null, drawPending=false;
  const $ = id => document.getElementById(id);
  const fmt = (value,digits=2) => Number.isFinite(Number(value)) && value!==null && value!==undefined ? Number(value).toFixed(digits) : '—';
  const observation = box => box.observed.find(row => Number(row.hour)===state.hour);
  const simulation = box => box.simulated.find(row => Number(row.hour)===state.hour);
  const riskOf = box => Number(simulation(box)?.risk_percent ?? 0);
  const colors = [[169,197,182],[196,208,173],[218,196,149],[212,159,122],[205,129,109]];
  function riskRGB(value) {
    const index=Math.max(0,Math.min(4,value/25)), low=Math.min(3,Math.floor(index)), t=index-low;
    return colors[low].map((channel,i)=>Math.round(channel+(colors[low+1][i]-channel)*t));
  }
  const color = (rgb,shade=1) => `rgb(${rgb.map(v=>Math.round(Math.min(255,v*shade))).join(',')})`;
  const layerName = layer => layer===1?'Top layer':layer===4?'Bottom layer':`Middle layer ${layer-1}`;

  function directory() {
    $('box-directory').innerHTML = [1,2,3,4].map(layer => `<div class="directory-layer"><div class="directory-layer-label"><strong>Layer ${layer}</strong><span>${layerName(layer)}</span></div><div class="box-buttons">${boxes.filter(b=>b.layer===layer).map(b=>`<button class="box-select" data-box="${b.box_id}" aria-pressed="${b.box_id===state.selected}" aria-label="Select box ${b.box_number}, layer ${b.layer}"><i aria-hidden="true" style="background:${color(riskRGB(riskOf(b)))}"></i><span>B${String(b.box_number).padStart(2,'0')}</span></button>`).join('')}</div></div>`).join('');
    document.querySelectorAll('[data-box]').forEach(button => button.addEventListener('click',()=>selectBox(button.dataset.box,true)));
  }

  function selectBox(id,fromDirectory=false) {
    const box=boxes.find(b=>b.box_id===id);
    if(!box)return;
    state.selected=id;
    if(fromDirectory && state.layer!=='all' && state.layer!==String(box.layer)) setLayer(String(box.layer),false);
    document.querySelectorAll('[data-box]').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.box===id)));
    renderReport(); requestDraw();
    $('selection-announcement').textContent=`Box ${box.box_number}, layer ${box.layer} selected. Report shown at hour ${state.hour}.`;
  }

  function setLayer(layer,update=true) {
    state.layer=layer;
    document.querySelectorAll('[data-layer]').forEach(button=>{const active=button.dataset.layer===layer;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
    if(layer!=='all' && String(boxes.find(b=>b.box_id===state.selected).layer)!==layer)selectBox(boxes.find(b=>String(b.layer)===layer).box_id);
    state.hover=null;tooltip.hidden=true;if(update)requestDraw();
  }

  function setHour(hour) {
    state.hour=hour;
    document.querySelectorAll('[data-hour]').forEach(button=>{const active=Number(button.dataset.hour)===hour;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
    $('time-caption').textContent=`Hour ${hour} of 24`;
    document.querySelectorAll('[data-box]').forEach(button=>{const box=boxes.find(b=>b.box_id===button.dataset.box);button.querySelector('i').style.background=color(riskRGB(riskOf(box)));button.title=`${box.box_id} · ${fmt(riskOf(box),1)}% simulated exceedance at hour ${hour}`;});
    renderReport();requestDraw();tooltip.hidden=true;
  }

  function renderReport() {
    const box=boxes.find(b=>b.box_id===state.selected), obs=observation(box), sim=simulation(box), baseline=box.observed.find(row=>Number(row.hour)===0);
    const risk=Number(sim?.risk_percent ?? 0), change=Number(obs?.mean_value)-Number(baseline?.mean_value);
    $('report-heading').textContent=`Box ${String(box.box_number).padStart(2,'0')}`;
    $('box-location').textContent=`${box.box_id} · Layer ${box.layer} · ${layerName(box.layer)}`;
    $('report-index').textContent=`${String(box.box_number).padStart(2,'0')} / ${boxes.length}`;
    $('risk-label').textContent=risk>=50?'Higher exceedance':risk>=20?'Moderate exceedance':'Lower exceedance';
    $('risk-banner').className=`risk-banner ${risk>=50?'':risk>=20?'mid':'low'}`;
    $('risk-banner').title='Display categories: lower <20%, moderate 20–<50%, higher ≥50%. These are visual groupings, not validated safety classifications.';
    $('report-time').textContent=`AT HOUR ${state.hour}`;
    $('observed-mean').textContent=fmt(obs?.mean_value);
    $('risk-percent').innerHTML=`${fmt(sim?.risk_percent,1)}<span class="unit">%</span>`;
    $('snapshot-hour').textContent=`HOUR ${state.hour}`;
    $('observed-range').textContent=`${fmt(obs?.min_value)} to ${fmt(obs?.max_value)}`;
    $('simulation-interval').textContent=`${fmt(sim?.p05_simulated_value)} to ${fmt(sim?.p95_simulated_value)}`;
    $('value-change').textContent=`${change>0?'+':''}${fmt(change)} value`;
    $('first-crossing').textContent=box.first_risk_hour===null||box.first_risk_hour===undefined?'Not reached by hour 24':`Hour ${box.first_risk_hour}`;
    $('exposed-surfaces').textContent=`${box.exposed_surfaces} recorded`;
    const geometry = box.geometry;
    $('alignment-note').className = `alignment-note ${geometry.mismatch ? 'mismatch' : ''}`;
    $('alignment-note').textContent = `${geometry.mismatch ? 'Alignment discrepancy. ' : 'Layout check. '}${geometry.side_count} outer vertical side${geometry.side_count===1?'':'s'} inferred${geometry.top_faces ? ' + top face' : ''}. ${geometry.bottom_boundary_faces ? 'Bottom face contacts the pallet; air exposure is unconfirmed. ' : ''}${geometry.mismatch ? 'The recorded count differs from the nominal layout. Source data is retained for review.' : 'Small drawing gaps do not count as exposure.'}`;
    $('box-data-link').href=`analysis-data.html?box=${box.box_id}&hour=${state.hour}`;
    $('sample-count').textContent=`${obs?.trial_count ?? '—'} observed · ${sim?.simulation_count ?? '—'} simulated`;
    const above=Number(obs?.mean_value)>=threshold;
    $('box-narrative').textContent=`At hour ${state.hour}, the observed mean is ${above?'at or above':'below'} ${threshold}. ${fmt(risk,1)}% of simulated samples meet or exceed that threshold.`;
    renderChart(box);
  }

  function renderChart(box) {
    const w=360,h=174,m={l:27,r:13,t:15,b:25};
    const values=[threshold,...box.observed.map(r=>Number(r.mean_value)),...box.simulated.flatMap(r=>[Number(r.p05_simulated_value),Number(r.p95_simulated_value)])].filter(Number.isFinite);
    const rawMin=Math.min(0,...values),rawMax=Math.max(...values);
    const tickStep=[1,2,3,5,10,20,50].find(step=>step>=(rawMax-rawMin)/4) || Math.ceil((rawMax-rawMin)/4);
    const min=Math.floor(rawMin/tickStep)*tickStep,max=Math.max(min+tickStep,Math.ceil(rawMax/tickStep)*tickStep);
    const x=t=>m.l+Number(t)/24*(w-m.l-m.r),y=v=>h-m.b-(Number(v)-min)/(max-min)*(h-m.t-m.b);
    const observed=[...box.observed].sort((a,b)=>a.hour-b.hour),simulated=[...box.simulated].sort((a,b)=>a.hour-b.hour);
    const path=(rows,key)=>rows.map((r,i)=>`${i?'L':'M'}${x(r.hour).toFixed(2)},${y(r[key]).toFixed(2)}`).join(' ');
    const band=path(simulated,'p95_simulated_value')+' '+[...simulated].reverse().map(r=>`L${x(r.hour)},${y(r.p05_simulated_value)}`).join(' ')+' Z';
    let grids='';for(let v=min;v<=max;v+=tickStep){grids+=`<line x1="${m.l}" y1="${y(v)}" x2="${w-m.r}" y2="${y(v)}" stroke="#edf0e8"/><text x="${m.l-7}" y="${y(v)+3}" text-anchor="end" fill="#a1aa95" font-size="8">${v}</text>`;}
    const active=observation(box),selectedX=x(state.hour);
    $('trend-chart').innerHTML=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Box ${box.box_number} observed and simulated values across 24 hours. Shading is the simulated 5th to 95th percentile interval. Dashed horizontal line marks threshold ${threshold}." style="font-family:inherit;stroke:none">${grids}<path d="${band}" fill="#e7edde" opacity=".74"/><line x1="${m.l}" x2="${w-m.r}" y1="${y(threshold)}" y2="${y(threshold)}" stroke="#caae8c" stroke-dasharray="3 4" stroke-width="1"/><text x="${w-m.r}" y="${y(threshold)-5}" text-anchor="end" fill="#b99a74" font-size="8">threshold ${threshold}</text><line x1="${selectedX}" x2="${selectedX}" y1="${m.t}" y2="${h-m.b}" stroke="#c3cebb" stroke-dasharray="2 4"/><path d="${path(simulated,'mean_simulated_value')}" fill="none" stroke="#b6a270" stroke-width="1.7" stroke-dasharray="4 3"/><path d="${path(observed,'mean_value')}" fill="none" stroke="#497b68" stroke-width="2" stroke-linejoin="round"/>${simulated.map(r=>`<circle cx="${x(r.hour)}" cy="${y(r.mean_simulated_value)}" r="2" fill="#b6a270"/>`).join('')}${active?`<circle cx="${selectedX}" cy="${y(active.mean_value)}" r="5.5" fill="#497b68" opacity=".15"/><circle cx="${selectedX}" cy="${y(active.mean_value)}" r="3" fill="#497b68" stroke="white" stroke-width="1.4"/>`:''}${hours.map(t=>`<text x="${x(t)}" y="${h-7}" text-anchor="middle" fill="${t===state.hour?'#547652':'#a1aa95'}" font-size="8">${t}h</text>`).join('')}</svg>`;
  }

  // World axes: x/y follow the source footprint; z is height above the deck.
  // Orthographic orbit with mild perspective. Positive camera depth is nearer.
  function camera() {
    const extent=40+state.explode*3, targetZ=extent/2;
    return {cos:Math.cos(state.yaw),sin:Math.sin(state.yaw),ce:Math.cos(state.elevation),se:Math.sin(state.elevation),targetZ,scale:Math.min(width/(93+state.explode*.65),height/(80+state.explode*2.5))*state.zoom,focal:240};
  }
  function project(point,cam) {
    const px=point[0]-24,py=point[1]-20,pz=point[2]-cam.targetZ;
    const rx=cam.cos*px-cam.sin*py,ry=cam.sin*px+cam.cos*py;
    const depth=cam.ce*ry+cam.se*pz,perspective=cam.focal/(cam.focal-depth);
    return {x:width*.5+rx*cam.scale*perspective,y:height*.46+(cam.se*ry-cam.ce*pz)*cam.scale*perspective,depth};
  }
  const surfaceDefs=[{ids:[0,3,2,1],normal:[0,0,-1],shade:.68},{ids:[4,5,6,7],normal:[0,0,1],shade:1.09,top:true},{ids:[0,1,5,4],normal:[0,-1,0],shade:.84},{ids:[3,7,6,2],normal:[0,1,0],shade:.90},{ids:[0,4,7,3],normal:[-1,0,0],shade:.78},{ids:[1,2,6,5],normal:[1,0,0],shade:.87}];
  function cuboid(cx,cy,cz,sx,sy,sz,rgb,box,cam,kind='box') {
    const dx=sx/2,dy=sy/2,dz=sz/2;
    const vertices=[[cx-dx,cy-dy,cz-dz],[cx+dx,cy-dy,cz-dz],[cx+dx,cy+dy,cz-dz],[cx-dx,cy+dy,cz-dz],[cx-dx,cy-dy,cz+dz],[cx+dx,cy-dy,cz+dz],[cx+dx,cy+dy,cz+dz],[cx-dx,cy+dy,cz+dz]];
    surfaceDefs.forEach(surface=>{
      const facing=surface.normal[0]*cam.sin*cam.ce+surface.normal[1]*cam.cos*cam.ce+surface.normal[2]*cam.se;
      if(facing<=.015)return;
      const points=surface.ids.map(i=>project(vertices[i],cam));
      faces.push({points,depth:points.reduce((sum,p)=>sum+p.depth,0)/4,fill:color(rgb,surface.shade),box,top:surface.top,world:surface.ids.map(i=>vertices[i]),kind});
    });
  }
  function polygon(points) {ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();}
  function drawGrid(cam) {
    ctx.save();ctx.strokeStyle='#e8ece3';ctx.lineWidth=.7;
    for(let i=-20;i<=70;i+=10){let a=project([i,-16,-5.5],cam),b=project([i,65,-5.5],cam);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();a=project([-20,i,-5.5],cam);b=project([70,i,-5.5],cam);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}
    const center=project([24,20,-5],cam);ctx.translate(center.x,center.y);ctx.scale(1,.35);const shadow=ctx.createRadialGradient(0,0,10,0,0,cam.scale*36);shadow.addColorStop(0,'#40543523');shadow.addColorStop(1,'#40543500');ctx.fillStyle=shadow;ctx.beginPath();ctx.arc(0,0,cam.scale*36,0,Math.PI*2);ctx.fill();ctx.restore();
  }
  function draw() {
    drawPending=false;if(!width||!height)return;
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
    const cam=camera();faces=[];drawGrid(cam);
    // Structural runners and deck boards give the pallet a real open base.
    [5,24,43].forEach(x=>cuboid(x,20,-3,5,40,4,[178,164,133],null,cam,'wood'));
    [3,11.5,20,28.5,37].forEach(y=>cuboid(24,y,-.7,49,6.5,1.35,[207,191,157],null,cam,'wood'));
    boxes.filter(box=>state.layer==='all'||String(box.layer)===state.layer).forEach(box=>{
      cuboid(box.x_inches,box.y_inches,box.z_inches+(4-box.layer)*state.explode,box.geometry.width-.6,box.geometry.depth-.6,box.geometry.height-.65,riskRGB(riskOf(box)),box,cam);
    });
    faces.sort((a,b)=>a.depth-b.depth);
    faces.forEach(face=>{
      polygon(face.points);ctx.fillStyle=face.fill;ctx.fill();
      const selected=face.box?.box_id===state.selected,hovered=face.box?.box_id===state.hover;
      ctx.strokeStyle=selected?'#375c46':hovered?'#668365':face.kind==='wood'?'#94866355':'#536a472d';ctx.lineWidth=selected?1.7:hovered?1.3:.7;ctx.lineJoin='round';ctx.stroke();
      if(face.box && face.top){
        // A subtle packing seam lies on the actual top plane and follows its projection.
        const a=face.world[0],b=face.world[1],c=face.world[2],d=face.world[3];
        const start=project(a.map((v,i)=>(v+b[i])/2),cam),end=project(c.map((v,i)=>(v+d[i])/2),cam);
        ctx.save();polygon(face.points);ctx.clip();ctx.beginPath();ctx.moveTo(start.x,start.y);ctx.lineTo(end.x,end.y);ctx.strokeStyle='#fcfff43d';ctx.lineWidth=3.5;ctx.stroke();ctx.restore();
        const center=project([face.box.x_inches,face.box.y_inches,face.box.z_inches+(4-face.box.layer)*state.explode+4.675],cam);
        const size=Math.max(8,Math.min(13,cam.scale*2.2));ctx.font=`${selected?'650':'500'} ${size}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';
        const label=`B${String(face.box.box_number).padStart(2,'0')}`;
        if(selected){const tw=ctx.measureText(label).width;ctx.fillStyle='#f8fbefde';roundedRect(center.x-tw/2-6,center.y-size/2-3,tw+12,size+6,4);ctx.fill();}
        ctx.fillStyle=selected?'#33563e':'#40513ee6';ctx.fillText(label,center.x,center.y);
      }
    });
  }
  function roundedRect(x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}
  function requestDraw(){if(!drawPending){drawPending=true;requestAnimationFrame(draw);}}
  function resize(){const rect=wrap.getBoundingClientRect();width=rect.width;height=rect.height;dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);requestDraw();}
  function hitTest(x,y){for(let i=faces.length-1;i>=0;i--){const face=faces[i];let inside=false;for(let j=0,k=face.points.length-1;j<face.points.length;k=j++){const a=face.points[j],b=face.points[k];if(((a.y>y)!==(b.y>y))&&(x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x))inside=!inside;}if(inside)return face.box;}return null;}
  function localPoint(event){const rect=canvas.getBoundingClientRect();return{x:event.clientX-rect.left,y:event.clientY-rect.top};}
  function updateHover(event){const p=localPoint(event),box=hitTest(p.x,p.y),id=box?.box_id??null;if(id!==state.hover){state.hover=id;requestDraw();}canvas.classList.toggle('over-box',Boolean(box));tooltip.hidden=!box;if(box){tooltip.textContent=`${box.box_id} · ${fmt(riskOf(box),1)}% ≥ ${threshold}`;tooltip.style.left=`${Math.max(8,Math.min(width-170,p.x+14))}px`;tooltip.style.top=`${Math.max(8,p.y-39)}px`;}}
  function finishPointer(event,cancelled=false){if(!pointer||event.pointerId!==pointer.id)return;const wasClick=!cancelled&&!pointer.moved;pointer=null;canvas.classList.remove('dragging');if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);if(wasClick){const p=localPoint(event),box=hitTest(p.x,p.y);if(box)selectBox(box.box_id);}if(!cancelled&&event.pointerType==='mouse')updateHover(event);}
  canvas.addEventListener('pointerdown',event=>{if(event.button!==0||pointer)return;pointer={id:event.pointerId,x:event.clientX,y:event.clientY,startX:event.clientX,startY:event.clientY,moved:false};canvas.setPointerCapture(event.pointerId);canvas.classList.add('dragging');tooltip.hidden=true;});
  canvas.addEventListener('pointermove',event=>{if(pointer){if(event.pointerId!==pointer.id)return;const dx=event.clientX-pointer.x,dy=event.clientY-pointer.y;if(Math.hypot(event.clientX-pointer.startX,event.clientY-pointer.startY)>4)pointer.moved=true;if(pointer.moved){state.yaw+=dx*.008;state.elevation=Math.max(.10,Math.min(1.40,state.elevation+dy*.006));requestDraw();}pointer.x=event.clientX;pointer.y=event.clientY;}else updateHover(event);});
  canvas.addEventListener('pointerup',event=>finishPointer(event));canvas.addEventListener('pointercancel',event=>finishPointer(event,true));canvas.addEventListener('lostpointercapture',()=>{pointer=null;canvas.classList.remove('dragging');});
  canvas.addEventListener('pointerleave',()=>{if(!pointer){state.hover=null;tooltip.hidden=true;canvas.classList.remove('over-box');requestDraw();}});
  function zoom(amount){state.zoom=Math.max(.6,Math.min(1.65,state.zoom*amount));requestDraw();}
  canvas.addEventListener('wheel',event=>{event.preventDefault();zoom(Math.exp(-event.deltaY*.001));},{passive:false});
  canvas.addEventListener('keydown',event=>{let handled=true;switch(event.key){case'ArrowLeft':state.yaw-=.13;break;case'ArrowRight':state.yaw+=.13;break;case'ArrowUp':state.elevation=Math.min(1.4,state.elevation+.08);break;case'ArrowDown':state.elevation=Math.max(.1,state.elevation-.08);break;case'+':case'=':zoom(1.1);break;case'-':zoom(1/1.1);break;case'Home':resetView();break;default:handled=false;}if(handled){event.preventDefault();requestDraw();}});
  function resetView(){state.yaw=-.68;state.elevation=.52;state.zoom=1;state.hover=null;tooltip.hidden=true;requestDraw();}
  $('reset-view').addEventListener('click',resetView);$('zoom-in').addEventListener('click',()=>zoom(1.12));$('zoom-out').addEventListener('click',()=>zoom(1/1.12));
  $('explode-slider').addEventListener('input',event=>{state.explode=Number(event.target.value);$('explode-value').textContent=`${Math.round(state.explode/12*100)}%`;requestDraw();});
  document.querySelectorAll('[data-layer]').forEach(button=>button.addEventListener('click',()=>setLayer(button.dataset.layer)));
  document.querySelectorAll('[data-hour]').forEach(button=>button.addEventListener('click',()=>{stopPlayback();setHour(Number(button.dataset.hour));}));
  function stopPlayback(){clearInterval(animation);animation=null;$('play-time').setAttribute('aria-pressed','false');$('play-time').setAttribute('aria-label','Play time sequence');$('play-time').innerHTML='<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 9 6-9 6Z"/></svg>';}
  $('play-time').addEventListener('click',()=>{if(animation){stopPlayback();return;}if(state.hour===24)setHour(0);$('play-time').setAttribute('aria-pressed','true');$('play-time').setAttribute('aria-label','Pause time sequence');$('play-time').innerHTML='<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6 4h2v12H6ZM12 4h2v12h-2Z"/></svg>';animation=setInterval(()=>{const next=hours.indexOf(state.hour)+1;if(next>=hours.length){stopPlayback();return;}setHour(hours[next]);if(hours[next]===24)stopPlayback();},1400);});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stopPlayback();});
  directory();setHour(state.hour);new ResizeObserver(resize).observe(wrap);resize();
})();
