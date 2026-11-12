// Visual acceptance uses real React in Chrome with controlled HTTP fixtures.
// This matrix does not replace the separate PostgreSQL/Redis integration evidence.
const path = require('node:path');
const fs = require('node:fs/promises');
const { chromium, expect } = require('@playwright/test');
const root = path.resolve(__dirname, '../..');
const change = path.join(root, 'openspec/changes/archive/2026-11-12-c-11-pwa-agenda-gestion');
const output = path.join(change, 'mockups/verify/final');
const id = '55555555-5555-4555-8555-555555555555';
const chair = '22222222-2222-4222-8222-222222222222';
const other = '44444444-4444-4444-8444-444444444444';
const treatmentId = '11111111-1111-4111-8111-111111111111';
const office = '33333333-3333-4333-8333-333333333333';
const superseded = {
 'agenda-fecha-bloqueada': 'G-fecha satisfecho. Se captura agenda con día AR verificado.',
 'config-sena-bloqueada': 'G-sena-config satisfecho. Se captura edición de política habilitada.',
 'cobros-bloqueados': 'G-cobros satisfecho. Se captura bloqueo seguro ante resumen inválido, no un gate artificial.'
};
(async () => {
 await fs.mkdir(output, {recursive:true});
 const source = await fs.readFile(path.join(change, 'mockups/mockups.js'), 'utf8');
 const scenes = [...source.split('// Allowlist')[0].matchAll(/\['([^']+)', '[^']+', '(?:agenda|config|cobros)'\]/g)].map(m => m[1]);
 const browser = await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const report = [];
 try {
 for (const scene of scenes) {
  for (const width of [360,390,1440]) {
   const context = await browser.newContext({baseURL:process.env.C11_VISUAL_URL || 'http://localhost:5195',viewport:{width,height:width===1440?900:844},locale:'es-AR',serviceWorkers:'block',reducedMotion:'reduce'});
   const page = await context.newPage();page.setDefaultTimeout(5000);
   const errors=[], network=[], unexpected=[];
   page.on('pageerror',e=>errors.push(e.message));
   page.on('response',r=>{if(r.status()>=400)network.push({path:new URL(r.url()).pathname,status:r.status()});});
   page.on('console',m=>{if(m.type()==='error' && !/Failed to load resource|net::ERR_FAILED/.test(m.text()))errors.push(m.text());});
   let written=false, amount=7000;
   const dentist=scene.includes('odontologo');
   const treatment={id:treatmentId,nombre:'Control',activo:true,duracion_min:15,precio_referencia_centavos:10000,sena_politica:'deshabilitada',sena_centavos:null};
   const block={id:other,motivo:'Mantenimiento de ejemplo',activo:true,sillon_id:null,desde:'2026-12-02T16:00:00Z',hasta:'2026-12-02T17:00:00Z',warnings:[]};
   const slots=[chair,other].map((sillon_id,i)=>({sillon_id,inicio:'2026-12-03T'+(12+i)+':00:00Z',fin:'2026-12-03T'+(12+i)+':15:00Z'}));
   const turn={id,tratamiento_id:treatmentId,paciente_nombre:'Paciente ficticio B',tratamiento_nombre:'Control',estado:'reservado',inicio:'2026-12-02T13:30:00Z',fin:'2026-12-02T13:45:00Z',tolerancia_min:5,es_sobreturno:scene==='agenda-sobreturno',motivo_sobreturno:scene==='agenda-sobreturno'?'Atención adicional autorizada':null,
    acciones:scene==='agenda-acciones-bloqueadas'?undefined:{confirmar:!dentist,cancelar:!dentist&&scene!=='agenda-ventana',reprogramar:!dentist&&scene!=='agenda-ventana',asistencia:true,sobreturno:!dentist}};
   const pageOf=items=>({items,total:items.length,page:1,page_size:20});
   await context.route('http://localhost:8000/**',async route=>{
    const req=route.request(), url=new URL(req.url()), p=url.pathname, method=req.method();
    const send=(json,status=200)=>route.fulfill({json,status});
    if(p==='/auth/refresh')return send({access_token:'ficticio'});
    if(p==='/auth/me')return send({id:'cuenta-ficticia',rol:scene==='acceso-denegado'?'paciente':dentist?'odontologo':'secretaria'});
    if(p==='/catalogo-publico')return send({sillones:[{id:chair,nombre:'Sillón 1'},{id:other,nombre:'Sillón 2'}],tratamientos:[treatment]});
    if(p==='/agenda'){
     if(scene==='agenda-carga')return;
     if(scene==='agenda-error')return send({},503);
     if(scene==='agenda-vacia')return send([]);
     return send([{sillon_id:chair,sillon_nombre:'Sillón 1',turnos:[turn]},{sillon_id:other,sillon_nombre:'Sillón 2',turnos:[{...turn,id:other,paciente_nombre:'Paciente ficticio D',estado:'confirmado'}]}]);
    }
    if(p==='/horarios-libres')return send(slots);
    if(p.endsWith('/historial'))return scene==='agenda-historial-no-disponible'?send({},503):send([{id:'evento-ficticio',actor_id:office,accion:'confirmar',origen:'mostrador',motivo:null,fecha:'2026-12-02T12:00:00Z'}]);
    if(p.startsWith('/turnos/')&&method==='PATCH'){
     if(scene==='agenda-incierta')return route.abort('failed');
     if(scene==='agenda-conflicto')return send({alternativas:[slots[1]]},409);
     return send({...turn,estado:'confirmado'});
    }
    if(p.startsWith('/cobros/resumen/'))return send(scene==='cobros-bloqueados'?{}:{precio_referencia_centavos:scene==='cobros-sin-precio'?null:10000,sena_acumulada_centavos:3000,total_cobrado_centavos:written?3000+amount:3000,saldo_referencia_centavos:scene==='cobros-sin-precio'?null:written?7000-amount:7000,cerrado:written});
    if(p==='/cobros/operacion')return send({cobro:{id:'operacion-ficticia',turno_id:id,monto_centavos:amount}});
    if(p==='/cobros'&&method==='POST'){
     const body=req.postDataJSON();amount=body.monto_centavos;
     if(scene==='cobros-inciertos'||scene==='cobros-replay'){written=true;return route.abort('failed');}
     if((scene==='cobros-diferencia'||scene==='cobros-exito-diferencia')&&!body.override_motivo)return send({detail:{code:'MONTO_DIFIERE',esperado_centavos:7000}},409);
     written=true;return send({cobro:{id:'operacion-ficticia',turno_id:id,monto_centavos:amount}},201);
    }
    if(p==='/cobros')return send([{id:'sena-ficticia',turno_id:id,monto_centavos:3000,medio:'efectivo',tipo:'sena',estado_mp:null,created_at:'2026-12-01T12:00:00Z'},...(written?[{id:'operacion-ficticia',turno_id:id,monto_centavos:amount,medio:'transferencia',tipo:'total',estado_mp:null,created_at:'2026-12-02T12:00:00Z'}]:[])]);
    if(p==='/api/config/contexto-consultorio')return send({consultorio:scene==='config-contexto-faltante'?null:{id:office,nombre:'Sede ficticia'}});
    if(p.startsWith('/api/config/')&&method==='GET'){
     if(scene==='config-carga')return;
     if(scene==='config-error')return send({},503);
     const active=url.searchParams.get('activo')!=='false';
     return send(pageOf(scene==='config-vacia'?[]:p.endsWith('tratamientos')?[treatment]:p.endsWith('bloqueos')?[block]:[{id:chair,nombre:'Sillón 1',consultorio_id:office,activo:active}]));
    }
    if(p.includes('/api/config/bloqueos/')&&method==='PATCH')return send({...block,...req.postDataJSON(),warnings:[{code:'TURNOS_SOLAPADOS',cantidad:2}]});
    unexpected.push(method+' '+p);return send({},500);
   });
   const btn=name=>page.getByRole('button',{name,exact:true});
   const click=name=>btn(name).click();
   const openTurn=async()=>{await page.getByRole('button',{name:/^Ver turno/}).first().focus();await page.keyboard.press('Enter');await expect(page.getByText('Tolerancia de llegada',{exact:true})).toBeVisible();};
   const config=scene.startsWith('config-');
   await page.goto(config?'/config':scene==='cobros-seleccion'?'/cobros':'/agenda');
   if(scene==='acceso-denegado')await expect(page.getByRole('alert')).toContainText('no tiene acceso');
   else if(config){
    await expect(page.getByRole('heading',{name:'Configuración',exact:true})).toBeVisible();
    if(scene==='config-carga')await expect(page.getByText('Consultando recursos…')).toBeVisible();
    else if(scene==='config-error')await expect(page.getByText(/No se pudo consultar la configuración/)).toBeVisible();
    else if(scene==='config-vacia')await expect(page.getByText(/No hay tratamientos activos/)).toBeVisible();
    else if(/sillon|contexto|desactivar|reactivar/.test(scene)){
     await click('Sillones');
     if(scene==='config-reactivar'){await page.getByLabel('Mostrar').selectOption('false');await click('Consultar');}
     if(/formulario|contexto/.test(scene)){
      await click('Agregar sillón');
      if(scene==='config-contexto-faltante')await expect(page.getByText(/único consultorio activo/)).toBeVisible();
      else {await expect(btn('Crear sillón')).toBeVisible();await page.getByLabel('Nombre',{exact:true}).fill('Sillón ficticio');}
     }else if(/desactivar|reactivar/.test(scene)){await click('Editar Sillón 1');await click(scene==='config-desactivar'?'Desactivar sillón':'Reactivar sillón');}
     else await expect(page.getByRole('heading',{name:'Sillón 1',exact:true})).toBeVisible();
    }else if(/bloqueo|advertencia/.test(scene)){
     await click('Bloqueos');await expect(page.getByRole('heading',{name:block.motivo})).toBeVisible();
     if(scene!=='config-bloqueos'){
      await click('Editar '+block.motivo);
      if(scene==='config-bloqueo-invalido'){await page.getByLabel('Hasta',{exact:true}).fill('2026-12-02T12:00');await click('Guardar bloqueo');await expect(page.getByText(/rango válido/)).toBeVisible();}
      if(scene==='config-advertencia'){await page.getByLabel('Motivo',{exact:true}).fill('Mantenimiento actualizado');await click('Guardar bloqueo');await expect(page.getByText(/turnos solapados y se conservaron/)).toBeVisible();}
     }
    }else{
     await expect(page.getByRole('heading',{name:'Control',exact:true})).toBeVisible();
     if(scene==='config-tratamiento-alta')await click('Agregar tratamiento');
     else if(scene!=='config-tratamientos'){
      await click('Editar Control');
      if(scene==='config-validacion'){await page.getByLabel('Duración en minutos').fill('0');await click('Guardar cambios');await expect(page.getByText(/duración debe ser/)).toBeVisible();}
      if(scene==='config-sena-bloqueada'){await page.getByLabel('Política de seña').selectOption('obligatoria');await page.getByLabel('Seña en ARS').fill('30,00');}
     }
    }
   }else if(scene.startsWith('cobros-')){
    if(scene==='cobros-seleccion')await expect(page.getByText(/Elegí un turno desde/)).toBeVisible();
    else{
     await openTurn();await click('Ver cobros del turno');
     if(scene==='cobros-bloqueados')await expect(page.getByText(/No se pudo consultar el resumen/)).toBeVisible();
     else{
      await expect(page.getByRole('heading',{name:'Movimientos'})).toBeVisible();await expect(page.getByText(/Seña ·/)).toBeVisible();
      if(/diferencia|exito|replay|inciertos/.test(scene)){
       await page.getByLabel('Importe en ARS').fill(scene.includes('diferencia')?'60,00':'70,00');await page.getByLabel(/^Medio/).selectOption('transferencia');await click('Registrar cobro');
       if(scene.includes('diferencia')){await expect(page.getByLabel('Motivo de la diferencia')).toBeVisible();await page.getByLabel('Motivo de la diferencia').fill('Descuento ficticio autorizado');if(scene==='cobros-exito-diferencia')await click('Confirmar cobro con diferencia');}
       if(scene==='cobros-replay'){await click('Consultar resultado del cobro');await expect(page.getByText('Cobro cerrado.')).toBeVisible();}
       if(scene==='cobros-inciertos')await expect(btn('Consultar resultado del cobro')).toBeVisible();
       if(scene.startsWith('cobros-exito'))await expect(page.getByText('Cobro cerrado.')).toBeVisible();
      }
     }
    }
   }else if(scene==='agenda-carga')await expect(page.getByText('Consultando turnos…')).toBeVisible();
   else if(scene==='agenda-error')await expect(page.getByText(/No se pudo consultar la agenda/)).toBeVisible();
   else if(scene==='agenda-vacia')await expect(page.getByText(/No hay turnos/)).toBeVisible();
   else{
    await openTurn();
    if(scene==='agenda-offline'){await context.setOffline(true);await expect(page.getByText(/La agenda no se guarda/)).toBeVisible();}
    if(scene.includes('historial')){await click('Ver historial');await expect(page.getByText(scene.endsWith('no-disponible')?'No se pudo consultar el historial del turno.':'Historial del turno',{exact:true})).toBeVisible();}
    if(/confirmar|cancelar|reprogramar|conflicto|asistencia|sobreturno|incierta/.test(scene)){
     const action=scene==='agenda-confirmar'||scene==='agenda-incierta'?'Confirmar turno':scene==='agenda-cancelar'?'Cancelar turno':scene.includes('asistencia')?'Marcar asistido':scene==='agenda-sobreturno'?'Marcar sobreturno':'Reprogramar turno';
     await click(action);
     if(scene.includes('asistencia')||scene==='agenda-sobreturno')await page.getByLabel('Motivo',{exact:true}).fill('Atención ficticia registrada');
     if(action==='Reprogramar turno'){
      await click('Buscar horarios');await expect(page.getByRole('button',{name:/09:00.*Sillón 1/})).toBeVisible();
      if(scene!=='agenda-reprogramar')await page.getByRole('button',{name:/09:00.*Sillón 1/}).click();
      if(scene==='agenda-conflicto'){await click('Aplicar cambio');await expect(page.getByText(/Elegí otro horario/)).toBeVisible();}
     }
     if(scene==='agenda-incierta'){await click('Aplicar cambio');await expect(btn('Consultar estado del turno')).toBeVisible();}
    }
   }
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),scene+' overflow').toBe(true);
   // Real keyboard focus and visible focus indicator, including narrow viewport.
   await page.getByRole('link',{name:/Turnos odontologia/}).focus();
   await page.keyboard.press('Tab');
   const focus=await page.evaluate(()=>{const e=document.activeElement;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName,outline:s.outlineStyle,width:s.outlineWidth,visible:r.width>0&&r.height>0};});
   expect(focus.visible,scene+' focus').toBe(true);
   expect(focus.outline!=='none'&&focus.width!=='0px',scene+' focus ring').toBe(true);
   await page.evaluate(()=>window.scrollTo(0,0));
   if(width!==360)await page.screenshot({path:path.join(output,scene+'-'+width+'.png'),fullPage:true});
   expect(unexpected).toEqual([]);expect(errors).toEqual([]);
   report.push({scene,width,passed:true,focus,network,comparison:superseded[scene]||'Estado vigente; comparar con mockup revisión 1.'});
   await context.close();
  }
  console.log('PASS '+scene);
 }
 await fs.writeFile(path.join(output,'matrix.json'),JSON.stringify({date:new Date().toISOString(),mode:'React real, HTTP simulado; no acredita backend',scenes:scenes.length,checks:report},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
