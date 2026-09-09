(() => {
  'use strict';
  const data = window.PALLET_DATA;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (value, digits=3) => value == null ? '—' : Number(value).toFixed(digits);
  const query = new URLSearchParams(location.search);
  let selected = data.boxes.find(b => b.box_id === query.get('box')) || data.boxes[0];
  let hour = query.has('hour') && data.metadata.hours.includes(Number(query.get('hour'))) ? Number(query.get('hour')) : 24;
  const table = (headers, rows) => `<table><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;

  $('box-picker').innerHTML = data.boxes.map(b=>`<option value="${esc(b.box_id)}">${esc(b.box_id)} · Layer ${b.layer}</option>`).join('');
  $('audit-summary').textContent = `${data.audit.observed_rows.toLocaleString()} observed readings and ${data.audit.simulated_rows.toLocaleString()} simulation samples checked. Numerical and coordinate checks passed; ${data.audit.mismatches.length} surface-count discrepancies need review.`;
  $('audit-checks').innerHTML = data.audit.checks.map(c=>`<div class="audit-card"><strong>${c.passed?'✓':'!'} ${esc(c.name)}</strong><span>${esc(c.detail)}</span></div>`).join('');
  $('mismatch-summary').textContent = data.audit.mismatches.map(id=>{const b=data.boxes.find(b=>b.box_id===id);return `${id}: ${b.exposed_surfaces} recorded versus ${b.geometry.side_count} inferred outer vertical sides.`;}).join(' ')+' Source counts have not been overwritten. Bottom-face air exposure remains unconfirmed.';
  $('geometry-rule').textContent = data.audit.geometry_rule;
  $('source-files').innerHTML = data.sources.map(s=>`<div class="source-file"><a download href="${esc(s.href)}">Download ${esc(s.name)} ↗</a><small>Original: ${esc(s.original)}</small><small>SHA-256: ${esc(s.sha256)}</small></div>`).join('');
  $('original-plots').innerHTML = [1,2,3,4].map(layer=>`<a href="sources/layer_${layer}_hour24_heatmap.png" target="_blank" rel="noopener"><img src="sources/layer_${layer}_hour24_heatmap.png" alt="Original observed hour-24 heat map, Layer ${layer}" loading="lazy"></a>`).join('');

  function render() {
    const b = selected, g = b.geometry;
    $('box-picker').value = b.box_id;
    $('hour-picker').value = String(hour);
    const url = `index.html?box=${b.box_id}&hour=${hour}`;
    $('view-box').href = url;
    $('back-link').href = url;
    $('selected-heading').textContent = `${b.box_id} · Layer ${b.layer}`;
    $('box-facts').textContent = `Center (X, Y, Z): (${b.x_inches}, ${b.y_inches}, ${b.z_inches}) inches. Inferred footprint: ${g.width} × ${g.depth} inches; height: ${g.height} inches. First individual trial ≥ 4: ${b.first_risk_hour==null?'not reached by hour 24':`hour ${b.first_risk_hour}`}.`;
    $('selected-alignment').className = `alignment-note ${g.mismatch?'mismatch':''}`;
    $('selected-alignment').textContent = `Recorded exposed surfaces: ${b.exposed_surfaces}. Inferred vertical outer sides: ${g.side_count} (${g.side_faces.join(', ')}). Top boundary: ${g.top_faces}. Bottom boundary: ${g.bottom_boundary_faces}${g.bottom_boundary_faces?' (pallet contact; not confirmed air exposure)':''}. ${g.mismatch?'Recorded count and inferred arrangement disagree; confirm the stacking plan.':'Boundary count matches under the stated comparison convention.'}`;
    $('observed-table').innerHTML = table(['Hour','Mean','Std. deviation','Minimum','Maximum','Trials'], b.observed.map(r=>[r.hour,fmt(r.mean_value),fmt(r.stdev_value),fmt(r.min_value),fmt(r.max_value),r.trial_count]));
    $('simulation-table').innerHTML = table(['Hour','Mean','Std. deviation','5th percentile','Median','95th percentile','Exceedance ≥ 4','Samples'],b.simulated.map(r=>[r.hour,fmt(r.mean_simulated_value),fmt(r.stdev_simulated_value),fmt(r.p05_simulated_value),fmt(r.p50_simulated_value),fmt(r.p95_simulated_value),fmt(r.risk_percent,1)+'%',r.simulation_count]));
    $('trial-table').innerHTML = table(['Hour','Trial','Observed value','Value ≥ 4'], b.trials.filter(r=>r.hour===hour).map(r=>[r.hour,r.trial,fmt(r.value,4),r.value>=4?'Yes':'No']));
    $('sample-table').innerHTML = table(['Hour','Simulation trial','Simulated value','Value ≥ 4'],b.samples.filter(r=>r[0]===hour).map(r=>[r[0],r[1],fmt(r[2],6),r[2]>=4?'Yes':'No']));
    const columns = ['Box','Layer','X (in)','Y (in)','Z (in)','Recorded count','Outer sides','Top boundary','Bottom boundary*','Check'];
    $('alignment-table').innerHTML = table(columns,data.boxes.map(box=>[box.box_id,box.layer,box.x_inches,box.y_inches,box.z_inches,box.exposed_surfaces,box.geometry.side_count,box.geometry.top_faces,box.geometry.bottom_boundary_faces,box.geometry.mismatch?'Review mismatch':box.layer===4?'Matches if bottom included':'Matches']));
    $('alignment-table').querySelectorAll('tbody tr').forEach((row,i)=>{row.classList.toggle('flagged',data.boxes[i].geometry.mismatch);row.classList.toggle('selected-row',data.boxes[i].box_id===b.box_id);});
    $('layer-maps').innerHTML = [1,2,3,4].map(layer=>`<div class="layer-map"><h3>Layer ${layer} · Z ${40-layer*10+5} in</h3><svg viewBox="0 0 60 53" role="group" aria-label="Layer ${layer}, top-down arrangement"><path d="M6 3V44H56" stroke="#819a88" stroke-width=".2"/><text x="54" y="48" font-size="2.2" fill="#526b59">X →</text><text x="1" y="5" font-size="2.2" fill="#526b59">Y ↑</text><text x="3" y="47" font-size="2" fill="#526b59">0</text>${data.boxes.filter(box=>box.layer===layer).map(box=>{const gg=box.geometry,x=6+box.x_inches-gg.width/2,y=44-box.y_inches-gg.depth/2;return `<g role="button" tabindex="0" data-map-box="${box.box_id}" aria-label="Select ${box.box_id}, ${box.exposed_surfaces} recorded surfaces, ${gg.side_count} inferred outer sides"><rect x="${x}" y="${y}" width="${gg.width}" height="${gg.depth}" fill="${box.box_id===b.box_id?'#d0e6d8':gg.mismatch?'#f6ddc7':'#edf2e7'}" stroke="${box.box_id===b.box_id?'#28645a':gg.mismatch?'#bb7b42':'#94a894'}" stroke-width="${box.box_id===b.box_id?'.7':'.25'}"/><circle cx="${6+box.x_inches}" cy="${44-box.y_inches}" r=".45" fill="#28645a" stroke="none"/><text x="${6+box.x_inches}" y="${41-box.y_inches}" text-anchor="middle" font-size="2.2" fill="#253c38">${box.box_id}</text><text x="${6+box.x_inches}" y="${47-box.y_inches}" text-anchor="middle" font-size="1.75" fill="#526b59">${box.x_inches}, ${box.y_inches}</text></g>`;}).join('')}</svg></div>`).join('');
    document.title = `${b.box_id} — Pallet data & alignment`;
    // Preserve the selection when this page is bookmarked or refreshed.
    try {history.replaceState(null,'',`?box=${b.box_id}&hour=${hour}`);} catch (_) { /* file:// history may be restricted */ }
  }
  $('box-picker').addEventListener('change',e=>{selected=data.boxes.find(b=>b.box_id===e.target.value);render();});
  $('hour-picker').addEventListener('change',e=>{hour=Number(e.target.value);render();});
  function selectMap(event) {
    const target=event.target.closest('[data-map-box]');
    if(!target)return;
    if(event.type==='keydown' && !['Enter',' '].includes(event.key))return;
    event.preventDefault();selected=data.boxes.find(b=>b.box_id===target.dataset.mapBox);render();
    document.querySelector(`[data-map-box="${selected.box_id}"]`).focus();
  }
  $('layer-maps').addEventListener('click',selectMap);
  $('layer-maps').addEventListener('keydown',selectMap);
  render();
})();
