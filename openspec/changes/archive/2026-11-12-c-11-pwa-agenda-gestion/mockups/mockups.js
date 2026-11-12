/* Maquetas locales: textos ficticios constantes, sin API, storage ni pagos.
 * La query solo selecciona claves de esta allowlist; jamás se inserta como HTML.
 */
(() => {
  const scenes = [
    ['agenda-secretaria', 'Agenda · secretaria', 'agenda'],
    ['agenda-odontologo', 'Agenda · odontólogo', 'agenda'],
    ['agenda-carga', 'Agenda · cargando', 'agenda'],
    ['agenda-vacia', 'Agenda · sin turnos', 'agenda'],
    ['agenda-error', 'Agenda · error de consulta', 'agenda'],
    ['agenda-offline', 'Agenda · sin conexión', 'agenda'],
    ['agenda-fecha-bloqueada', 'Agenda · día pendiente de verificar', 'agenda'],
    ['agenda-acciones-bloqueadas', 'Agenda · permisos pendientes', 'agenda'],
    ['acceso-denegado', 'Acceso · paciente sin permisos', 'agenda'],
    ['agenda-historial', 'Turno · historial de ejemplo', 'agenda'],
    ['agenda-historial-no-disponible', 'Turno · historial no disponible', 'agenda'],
    ['agenda-confirmar', 'Turno · confirmar', 'agenda'],
    ['agenda-cancelar', 'Turno · cancelar', 'agenda'],
    ['agenda-ventana', 'Turno · ventana de 2 horas', 'agenda'],
    ['agenda-reprogramar', 'Turno · reprogramar', 'agenda'],
    ['agenda-conflicto', 'Turno · conflicto de horario', 'agenda'],
    ['agenda-asistencia', 'Turno · marcar asistencia', 'agenda'],
    ['agenda-asistencia-odontologo', 'Turno · asistencia por odontólogo', 'agenda'],
    ['agenda-sobreturno', 'Turno · motivo de sobreturno', 'agenda'],
    ['agenda-incierta', 'Turno · resultado no verificado', 'agenda'],
    ['config-tratamientos', 'Configuración · tratamientos', 'config'],
    ['config-tratamiento-alta', 'Tratamiento · alta', 'config'],
    ['config-tratamiento-formulario', 'Tratamiento · edición', 'config'],
    ['config-validacion', 'Tratamiento · validación', 'config'],
    ['config-sena-bloqueada', 'Tratamiento · seña no editable', 'config'],
    ['config-sillones', 'Configuración · sillones', 'config'],
    ['config-sillon-formulario', 'Sillón · alta con contexto', 'config'],
    ['config-contexto-faltante', 'Sillón · falta sede configurada', 'config'],
    ['config-bloqueos', 'Configuración · bloqueos', 'config'],
    ['config-bloqueo-formulario', 'Bloqueo · edición', 'config'],
    ['config-bloqueo-invalido', 'Bloqueo · rango inválido', 'config'],
    ['config-advertencia', 'Bloqueo · guardado con advertencia', 'config'],
    ['config-desactivar', 'Sillón · confirmar desactivación', 'config'],
    ['config-reactivar', 'Sillón · reactivación', 'config'],
    ['config-carga', 'Configuración · cargando', 'config'],
    ['config-vacia', 'Configuración · sin recursos', 'config'],
    ['config-error', 'Configuración · error de consulta', 'config'],
    ['cobros-bloqueados', 'Cobros · contrato pendiente', 'cobros'],
    ['cobros-seleccion', 'Cobros · seleccionar turno', 'cobros'],
    ['cobros-resumen', 'Cobros · registro incremental', 'cobros'],
    ['cobros-diferencia', 'Cobros · confirmar diferencia', 'cobros'],
    ['cobros-exito', 'Cobros · registrado', 'cobros'],
    ['cobros-replay', 'Cobros · operación ya registrada', 'cobros'],
    ['cobros-inciertos', 'Cobros · resultado no verificado', 'cobros'],
    ['cobros-sin-precio', 'Cobros · precio sin referencia', 'cobros'],
    ['agenda-reprogramar-confirmacion', 'Turno · confirmar nuevo horario', 'agenda'],
    ['cobros-exito-diferencia', 'Cobros · diferencia auditada', 'cobros'],
  ];
  // Allowlist compartida con el catálogo y el proceso de capturas.
  window.C11_SCENES = scenes.map(([id, title, group]) => ({ id, title, group }));
  const link = (id, text, style = 'secondary') => `<a class="button ${style}" href="index.html?scene=${id}">${text}</a>`;
  const badge = (text, variant = '') => `<span class="badge ${variant}">${text}</span>`;
  const notice = (title, text, variant = 'warning') => `<div class="notice ${variant}"><strong>${title}</strong><p>${text}</p></div>`;
  const head = (title, text, action = '') => `<div class="page-head"><div><h1>${title}</h1><p class="muted">${text}</p></div>${action}</div>`;
  const actions = (html) => `<div class="actions">${html}</div>`;
  const field = (label, value, extra = '') => `<label>${label}<input value="${value}" ${extra}></label>`;
  const select = (label, values, extra = '') => `<label>${label}<select ${extra}>${values.map(v => `<option>${v}</option>`).join('')}</select></label>`;
  const form = (content) => `<form class="form">${content}</form>`;
  const facts = (rows) => `<dl class="facts">${rows.map(([k,v,total])=>`<div${total?' class="total"':''}><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>`;
  const panel = (title, subtitle, html) => `<aside class="panel" aria-label="${title}"><div class="panel-title"><h2>${title}</h2><small>${subtitle}</small></div>${html}</aside>`;
  const skeleton = () => `<div role="status" aria-label="Cargando datos">${[1,2,3].map(()=>'<div class="skeleton-row"><div class="skeleton short"></div><div class="skeleton"></div></div>').join('')}</div>`;
  const caption = '<p class="demo-caption">Vista de diseño con datos ficticios. Los estados de éxito ilustran el contrato esperado; no acreditan una operación real ni desbloquean dependencias.</p>';
  const filters = (offline = false) => `<form class="filters">${field('Fecha', '2026-11-12', `type="date" ${offline?'disabled':''}`)}${select('Sillón',['Todos los sillones','Sillón 1','Sillón 2'],offline?'disabled':'')}${select('Estado',['Todos los estados','Reservado','Confirmado','Asistido','Ausente','Cancelado'],offline?'disabled':'')}<button type="submit" ${offline?'disabled':''}>Consultar</button></form>`;
  const appointment = (hour, end, person, treatment, state, selected = false, extra = '') => `<article class="appointment${selected?' selected':''}"><div class="time"><strong>${hour}</strong><small>${end}</small></div><div><span class="person">${person}</span><small>${treatment}</small><div class="badge-row">${badge(state,state==='Confirmado'?'success':'')}${extra?badge('Sobreturno','warning'):''}</div>${extra?`<small>${extra}</small>`:''}</div><a class="row-link" href="index.html?scene=agenda-historial-no-disponible#detalle">Ver turno</a></article>`;
  const schedule = () => `<div><section class="chair"><div class="chair-head"><h2>Sillón 1</h2><small>Tolerancia: 5 min</small></div>${appointment('09:00','09:30','Paciente ficticio A','Limpieza · 30 min','Confirmado')}${appointment('10:30','10:45','Paciente ficticio B','Control · 15 min','Reservado',true)}${appointment('11:15','11:45','Paciente ficticio C','Limpieza · 30 min','Confirmado',false,'Motivo ficticio: atención adicional autorizada')}</section><section class="chair"><div class="chair-head"><h2>Sillón 2</h2><small>Tolerancia: 5 min</small></div>${appointment('09:30','10:30','Paciente ficticio D','Conducto · 60 min','Confirmado')}${appointment('11:00','11:15','Paciente ficticio E','Control · 15 min','Asistido')}</section></div>`;
  const turnFacts = () => facts([['Paciente','Paciente ficticio B'],['Tratamiento','Control · 15 min'],['Fecha','12 nov 2026'],['Hora Argentina','10:30–10:45'],['Sillón','Sillón 1'],['Estado',badge('Reservado')],['Origen','Online']]);
  const turnLinks = () => actions(link('agenda-confirmar','Confirmar turno','')+link('agenda-reprogramar','Reprogramar')+link('agenda-cancelar','Cancelar turno','danger'))+actions(link('agenda-asistencia','Marcar asistencia')+link('agenda-sobreturno','Marcar sobreturno'));
  const historyUnavailable = () => notice('Historial no disponible','No se puede consultar quién realizó cada cambio. El origen actual no reemplaza el historial.','info');
  function turnDetail(id, isDentist) {
    let body = turnFacts();
    if(id === 'agenda-historial') return panel('Historial del turno','Ejemplo del resultado esperado tras verificar la auditoría',body.replace('<dd>Online</dd>','<dd>Mostrador</dd>')+notice('Ejemplo futuro','Esta secuencia es ficticia. La API actual todavía no entrega este historial.','info')+'<ol class="history"><li><strong>Reprogramado por secretaria de ejemplo</strong><small>12 nov · 08:05 · origen mostrador</small></li><li><strong>Reservado por paciente de ejemplo</strong><small>11 nov · 16:20 · origen online</small></li></ol>'+link('agenda-historial-no-disponible','Ver estado actual sin historial'));
    if(id === 'agenda-confirmar') body += '<h3 class="section-label">Confirmar este turno</h3><p>Se cambiará de reservado a confirmado. La confirmación no registra un cobro.</p>'+actions(link('agenda-secretaria','Confirmar turno','')+link('agenda-secretaria','Volver'));
    else if(id === 'agenda-cancelar') body += notice('¿Cancelar este turno?','Se liberará el horario. Esta acción debe respetar la ventana que valida el servidor.')+actions(link('agenda-secretaria','Sí, cancelar turno','danger')+link('agenda-secretaria','Conservar turno'));
    else if(id === 'agenda-ventana') body += notice('No se puede cancelar ni reprogramar','Faltan menos de 2 horas para el inicio. La restricción también se aplica a secretaria.')+actions('<button disabled>Cancelar turno</button><button disabled>Reprogramar</button>')+link('agenda-secretaria','Consultar estado');
    else if(id === 'agenda-reprogramar-confirmacion') body += '<h3 class="section-label">Confirmar nuevo horario</h3>'+facts([['Nuevo día','13 nov 2026'],['Nueva hora',new URLSearchParams(location.search).get('slot')==='0930'?'09:30–09:45':'09:00–09:15'],['Nuevo sillón','Sillón 2']])+'<p>El turno original se conserva hasta que el servidor valide y confirme el cambio.</p>'+actions(link('agenda-secretaria','Confirmar reprogramación','')+link('agenda-reprogramar','Elegir otro horario'));
    else if(id === 'agenda-reprogramar' || id === 'agenda-conflicto') body += '<h3 class="section-label">Nuevo horario</h3>'+form(field('Fecha','2026-11-13','type="date"')+select('Sillón',['Sillón 2','Sillón 1']))+(id==='agenda-conflicto'?notice('El horario ya no está disponible','El turno original sigue el 12 nov a las 10:30. Elegí otra alternativa; no se guardó ningún cambio.','danger'):'<p>El turno original se conserva hasta que el servidor confirme el cambio.</p>')+'<div class="option-list">'+link('agenda-reprogramar-confirmacion','13 nov · 09:00')+link('agenda-reprogramar-confirmacion&slot=0930','13 nov · 09:30')+'</div><small>Seleccioná un horario y confirmá el cambio. El servidor calcula el fin.</small>'+actions('<button disabled>Confirmar reprogramación</button>'+link('agenda-secretaria','Volver'));
    else if(id.startsWith('agenda-asistencia')) body += '<h3 class="section-label">Registrar asistencia</h3><p>Elegí el resultado de la atención. La tolerancia de 5 minutos es informativa.</p>'+actions(link(isDentist?'agenda-odontologo':'agenda-secretaria','Marcar asistido','')+link(isDentist?'agenda-odontologo':'agenda-secretaria','Marcar ausente'));
    else if(id === 'agenda-sobreturno') body += '<h3 class="section-label">Marcar como sobreturno</h3><p>Solo secretaria. La marca no permite crear un solapamiento ni evita las validaciones.</p>'+form('<label>Motivo<textarea placeholder="Explicá por qué se marca como sobreturno"></textarea></label>')+actions(link('agenda-secretaria','Guardar marca','')+link('agenda-secretaria','Volver'));
    else if(id === 'agenda-incierta') body += notice('Resultado no verificado','La conexión se cortó al enviar el cambio. Consultá el estado antes de repetir la operación. Una consulta vacía no demuestra que el cambio no ocurrió.','danger')+actions(link('agenda-secretaria','Consultar estado','')+'<button disabled>Repetir cambio</button>');
    else if(id === 'agenda-acciones-bloqueadas') body += notice('Acciones no disponibles','Todavía no se pudieron verificar los permisos y la ventana del servidor. Podés consultar el turno.','info')+actions('<button disabled>Cancelar</button><button disabled>Reprogramar</button>')+historyUnavailable();
    else if(isDentist) body += actions(link('agenda-asistencia-odontologo','Marcar asistencia',''))+'<small>Confirmar, cancelar y reprogramar corresponden a secretaria.</small>'+historyUnavailable();
    else body += turnLinks()+`<h3 class="section-label">Historial</h3>`+historyUnavailable()+link('cobros-bloqueados','Ver cobros del turno');
    return `<div id="detalle">${panel('Detalle del turno','12 nov · hora Argentina',body)}</div>`;
  }
  function agenda(id) {
    const dentist = id.includes('odontologo');
    if(id==='acceso-denegado') return head('Esta sección es para el consultorio','La cuenta paciente no tiene acceso a la agenda del personal.')+notice('Acceso no permitido','No se cargaron datos de pacientes ni cobros.','info')+link('agenda-secretaria','Volver a la maqueta de secretaria');
    let html=head('Agenda del día','Jueves 12 de noviembre de 2026 · hora Argentina',link('agenda-secretaria','Actualizar'))+filters(id==='agenda-offline');
    if(id==='agenda-offline') return html+notice('Sin conexión','No hay agenda privada guardada en este dispositivo. No se enviarán cambios al reconectar.','info')+'<div class="state-box"><h2>Conectate para consultar la agenda</h2><p>La disponibilidad y las acciones necesitan datos actuales del servidor.</p><button disabled>Consultar agenda</button></div>';
    if(id==='agenda-carga') return html+'<p role="status">Consultando agenda…</p>'+skeleton();
    if(id==='agenda-vacia') return html+'<div class="state-box"><h2>No hay turnos para esta consulta</h2><p>Cambiá la fecha o quitá un filtro para consultar otros turnos.</p>'+link('agenda-secretaria','Quitar filtros','')+'</div>';
    if(id==='agenda-error') return html+notice('No se pudo consultar la agenda','No se puede afirmar que el día esté vacío. Volvé a consultar cuando el servicio esté disponible.','danger')+link('agenda-secretaria','Reintentar consulta','');
    if(id==='agenda-fecha-bloqueada') return html+notice('El día aún no está verificado','La consulta de fechas del servidor está pendiente de conciliación. No se muestran horarios como si fueran el día argentino correcto.','info')+'<button disabled>Gestionar turnos</button>';
    return html+`<div class="split">${dentist?schedule().replaceAll('agenda-historial-no-disponible','agenda-odontologo'):schedule()}${turnDetail(id,dentist)}</div>`+caption;
  }
  const resourceTabs = (resource) => `<nav class="resource-tabs" aria-label="Recursos">${[['tratamientos','Tratamientos'],['sillones','Sillones'],['bloqueos','Bloqueos']].map(([id,text])=>`<a href="index.html?scene=config-${id}"${id===resource?' aria-current="page"':''}>${text}</a>`).join('')}</nav>`;
  const catalogRow = (name, desc, target, status='Activo') => `<li class="catalog-row"><div><strong>${name}</strong><small>${desc}</small><div class="badge-row">${badge(status,status==='Activo'?'success':'')}</div></div><a class="row-link" href="index.html?scene=${target}#editor">Editar</a></li>`;
  function resourceList(resource, inactive=false) {
    let rows;
    if(resource==='tratamientos') rows = catalogRow('Control','15 min · precio de referencia ARS $ 100,00','config-tratamiento-formulario')+catalogRow('Limpieza','30 min · precio sin referencia','config-tratamiento-formulario')+catalogRow('Conducto','60 min · seña deshabilitada','config-sena-bloqueada');
    else if(resource==='sillones') rows=inactive?catalogRow('Sillón 3 de ejemplo','Desactivado · históricos conservados','config-reactivar','Inactivo'):catalogRow('Sillón 1','Sede de ejemplo (ficticia)','config-desactivar')+catalogRow('Sillón 2','Sede de ejemplo (ficticia)','config-desactivar');
    else rows=catalogRow('Mantenimiento de ejemplo','12 nov · 13:00–14:00 · todos los sillones','config-bloqueo-formulario')+catalogRow('Pausa de ejemplo','12 nov · 16:00–16:30 · sillón 1','config-bloqueo-formulario');
    return `<div><ul class="catalog-list">${rows}</ul><div class="pagination"><small>Página 1 · ${resource==='tratamientos'?'3':'2'} registros de ejemplo</small><div class="actions"><button class="secondary" disabled>Anterior</button><button class="secondary" disabled>Siguiente</button></div></div></div>`;
  }
  function treatmentForm(id) {
    const invalid=id==='config-validacion';
    if(id==='config-tratamiento-alta') return panel('Agregar tratamiento','Nuevo recurso · datos de ejemplo',form(field('Nombre','','maxlength="120" placeholder="Nombre del tratamiento"')+field('Duración en minutos','','inputmode="numeric" placeholder="Minutos"')+field('Precio de referencia en ARS','','inputmode="decimal" placeholder="Opcional"')+'<small>Podés dejar el precio sin referencia. La seña queda deshabilitada por defecto.</small>')+actions(link('config-tratamientos','Crear tratamiento','')+link('config-tratamientos','Volver')));
    return panel('Editar tratamiento','Ejemplo ficticio · campos editables según permiso',form(field('Nombre','Control','maxlength="120"')+field('Duración en minutos',invalid?'0':'15',`inputmode="numeric" ${invalid?'aria-invalid="true" aria-describedby="duration-error"':''}`)+(invalid?'<small id="duration-error" class="field-error">La duración debe ser un entero mayor que cero.</small>':'')+field('Precio de referencia en ARS','100,00','inputmode="decimal" aria-describedby="price-help"')+'<small id="price-help">Opcional. Se guardará como 10000 centavos. No es un nuevo cobro.</small><label class="check"><input type="checkbox">Sin precio de referencia</label>'+select('Política de seña',['Deshabilitada'],'disabled aria-describedby="sena-help"')+'<small id="sena-help">La edición de señas espera verificación del contrato de pagos. No se activa desde esta maqueta.</small>')+(id==='config-sena-bloqueada'?notice('Seña no editable','Podés modificar nombre, duración y precio. La política de seña depende de C-09.','info'):'')+actions(link('config-tratamientos','Guardar cambios','')+link('config-tratamientos','Volver')));
  }
  function chairForm(id) {
    if(id==='config-contexto-faltante') return panel('Agregar sillón','Configuración inicial pendiente',notice('Falta la sede del consultorio','No se puede crear el primer sillón sin contexto autorizado. Solicitá completar la configuración inicial. No necesitás escribir un UUID.','info')+form(field('Nombre','Sillón de ejemplo')+select('Consultorio',['No disponible'],'disabled'))+actions('<button disabled>Crear sillón</button>'+link('config-sillones','Volver')));
    if(id==='config-desactivar') return panel('Desactivar sillón','Sillón 1',notice('Los históricos se conservan','Se dejará de ofrecer disponibilidad para este sillón. Los turnos existentes no se borran ni se cancelan automáticamente.')+actions(link('config-sillones','Desactivar sillón','danger')+link('config-sillones','Conservar activo')));
    if(id==='config-reactivar') return panel('Reactivar sillón','Sillón 3 de ejemplo · inactivo','<p>Volverá a estar activo y podrá participar en las consultas de disponibilidad. Se conservan sus turnos históricos.</p>'+actions(link('config-sillones','Reactivar sillón','')+link('config-sillones','Volver')));
    return panel('Agregar sillón','Ejemplo futuro con contexto de sede verificado',form(field('Nombre','Sillón de ejemplo','maxlength="80"')+field('Consultorio','Sede de ejemplo (ficticia)','disabled'))+notice('Contexto autorizado','La sede se obtiene del servidor. No se puede cambiar escribiendo un identificador.','info')+actions(link('config-sillones','Crear sillón','')+link('config-sillones','Volver')));
  }
  function blockForm(id) {
    const invalid=id==='config-bloqueo-invalido';
    return panel('Editar bloqueo','Hora Argentina · America/Argentina/Buenos_Aires',form(field('Motivo','Mantenimiento de ejemplo','maxlength="120"')+select('Alcance',['Todos los sillones','Sillón 1','Sillón 2'])+field('Desde','2026-11-12T13:00','type="datetime-local"')+field('Hasta',invalid?'2026-11-12T12:00':'2026-11-12T14:00',`type="datetime-local" ${invalid?'aria-invalid="true" aria-describedby="range-error"':''}`)+(invalid?'<small id="range-error" class="field-error">Hasta debe ser posterior a desde. No se guardó el cambio.</small>':'<small>Las fechas se envían con zona. Un bloqueo no cancela turnos existentes.</small>'))+(id==='config-advertencia'?notice('Bloqueo guardado con advertencia','Coincide con 2 turnos activos de ejemplo. Los turnos se conservan; revisá la agenda.'):'' )+actions(link('config-bloqueos','Guardar bloqueo','')+link('config-bloqueos','Volver')));
  }
  function config(id) {
    let resource='tratamientos';
    if(/sillon|contexto|desactivar|reactivar/.test(id)) resource='sillones';
    if(/bloqueo|advertencia/.test(id)) resource='bloqueos';
    const target=resource==='tratamientos'?'config-tratamiento-alta':resource==='sillones'?'config-contexto-faltante':'config-bloqueo-formulario';
    let html=head('Configuración','Administración del consultorio · solo secretaria',link(target,resource==='sillones'?'Agregar sillón':resource==='bloqueos'?'Agregar bloqueo':'Agregar tratamiento',''))+resourceTabs(resource)+`<form class="filters compact">${select('Mostrar',id==='config-reactivar'?['Inactivos','Activos']:['Activos','Inactivos'])}<button class="secondary">Consultar</button></form>`;
    if(id==='config-carga') return html+'<p role="status">Consultando recursos…</p>'+skeleton();
    if(id==='config-vacia') return html+'<div class="state-box"><h2>No hay tratamientos activos</h2><p>Agregá un tratamiento o consultá los inactivos para reactivar uno existente.</p>'+link('config-tratamiento-alta','Agregar tratamiento','')+'</div>';
    if(id==='config-error') return html+notice('No se pudo consultar la configuración','No se cargaron recursos. No se enviaron cambios.','danger')+link('config-tratamientos','Reintentar consulta','');
    let editor;
    if(resource==='tratamientos') editor=treatmentForm(id);
    else if(resource==='sillones') editor=chairForm(id);
    else editor=blockForm(id);
    return html+`<div class="split">${resourceList(resource,id==='config-reactivar')}<div id="editor">${editor}</div></div>`+caption;
  }
  function cobros(id) {
    let html=head('Cobros','Registro local contra un turno · solo secretaria',link('agenda-secretaria','Volver a agenda'));
    html+=notice('Sin factura electrónica en v1','Registrar un cobro no emite factura. Mercado Pago manual es un registro de mostrador, no un pago online verificado.','info');
    if(id==='cobros-seleccion') return html+'<div class="state-box"><h2>Seleccioná un turno de la agenda</h2><p>Necesitamos identificar el turno para consultar sus movimientos. No se ingresa un paciente o un monto desde la URL.</p>'+link('agenda-secretaria','Abrir agenda','')+'</div>';
    if(id==='cobros-bloqueados') return html+notice('Registro de cobros no habilitado','Está pendiente verificar conciliación, claves de operación y prevención de doble cierre en C-09. No se enviarán cobros.','warning')+`<div class="split"><section><h2>Turno seleccionado</h2>${turnFacts()}<p class="muted">Los totales no se muestran hasta poder verificarlos.</p></section>${panel('Registrar cobro','Pendiente de verificación del contrato',form(field('Dinero nuevo recibido en ARS','','disabled placeholder="No disponible"')+select('Medio',['Efectivo','Transferencia','Mercado Pago manual'],'disabled'))+'<button disabled>Registrar cobro</button>')}</div>`;
    const differencePaid=id==='cobros-exito-diferencia';
    const finished=id==='cobros-exito'||id==='cobros-replay'||differencePaid;
    const uncertain=id==='cobros-inciertos';
    const noPrice=id==='cobros-sin-precio';
    const override=id==='cobros-diferencia';
    const received=differencePaid?'ARS $ 60,00':'ARS $ 70,00';
    const finalTotal=differencePaid?'ARS $ 90,00':'ARS $ 100,00';
    const finalBalance=differencePaid?'ARS $ 10,00':'ARS $ 0,00';
    if(finished) html+=notice(id==='cobros-replay'?'Esta operación ya estaba registrada':'Cobro registrado',id==='cobros-replay'?'Se recuperó el mismo cobro de ejemplo. No se sumó otra vez el importe.':`El servidor confirmó el cobro de ejemplo por ${received}.`,'success');
    if(differencePaid) html+=notice('Diferencia registrada con motivo','Motivo ficticio: descuento autorizado por el consultorio. La diferencia de ARS $ 10,00 queda visible y auditada.');
    if(uncertain) html+=notice('Resultado no verificado','Se perdió la respuesta del cobro. No vuelvas a cobrar ni recargues para repetirlo. Consultá la operación; si no puede verificarse, pedí revisión.','danger');
    html+=`<div class="split"><section><h2>Turno y movimientos</h2>${turnFacts()}${facts([['Precio de referencia',noPrice?'Sin referencia':'ARS $ 100,00'],['Seña recibida','ARS $ 30,00'],['Total cobrado',finished?finalTotal:'ARS $ 30,00'],['Saldo de referencia',noPrice?'No calculable':finished?finalBalance:'ARS $ 70,00',true]])}<ul class="history"><li><strong>Seña · ARS $ 30,00</strong><small>11 nov · Mercado Pago verificado · dato ficticio</small></li>${finished?`<li><strong>Cierre · ${received}</strong><small>12 nov · efectivo · operación ficticia OP-001</small></li>`:''}</ul></section>`;
    let right;
    if(finished) right=panel('Cierre registrado','Operación ficticia OP-001',facts([['Dinero nuevo recibido',received],['Medio','Efectivo'],['Saldo de referencia',finalBalance,true]])+'<p>La seña previa está incluida en el total, no se registró de nuevo.</p>'+actions(link('agenda-secretaria','Volver a agenda','')+'<button disabled>Registrar otro cierre</button>'));
    else if(uncertain) right=panel('Consultar la operación','No se enviará un nuevo cobro','<p>La consulta debe identificar la misma operación. Una respuesta vacía o un error no prueban que no se registró.</p>'+actions(link('cobros-replay','Consultar estado','')+'<button disabled>Repetir cobro</button>')+'<small>Si sigue sin verificarse, solicitá revisión al consultorio.</small>');
    else right=panel(override?'Revisar diferencia':'Registrar cobro','Ejemplo futuro tras desbloquear C-09',form(field('Dinero nuevo recibido en ARS',override?'60,00':'70,00','inputmode="decimal" aria-describedby="money-help"')+'<small id="money-help">Ingresá solo el dinero que recibís ahora, sin volver a sumar la seña.</small>'+select('Medio',['Efectivo','Transferencia','Mercado Pago manual'])+select('Tipo',['Total · cierre del turno','Seña']))+(override?notice('El monto difiere del esperado','Esperado: ARS $ 70,00. Recibido: ARS $ 60,00. Todavía no se registró el cobro.')+form('<label>Motivo del importe diferente<textarea>Descuento ficticio autorizado por el consultorio</textarea></label>')+'<p>Confirmar registra el motivo auditado y envía una nueva operación explícita.</p>':noPrice?notice('Precio sin referencia','Se registra el importe recibido, pero no se inventa un saldo.','warning'):'')+actions(link(override?'cobros-exito-diferencia':'cobros-exito',override?'Confirmar con motivo':'Confirmar cobro','')+link('agenda-secretaria','Volver')));
    return html+right+'</div>'+caption;
  }
  function reviewCatalog() {
    document.getElementById('contenido').innerHTML=head('Revisión de mockups C-11','Sistema visual 1 aprobado · mockups revisión 1 pendientes de aprobación')+'<p>Elegí una vista para recorrer su HTML local. Las capturas móvil y escritorio se generan para cada estado. Todos los datos son ficticios y no se realizan operaciones.</p><div class="review-grid">'+scenes.map(([id,title])=>`<article class="review-item"><h2>${title}</h2><a href="index.html?scene=${id}">Abrir vista</a><a href="previews/${id}-390.png">Móvil</a><a href="previews/${id}-1440.png">Escritorio</a></article>`).join('')+'</div>';
  }
  if(document.body.dataset.catalog==='true') {
    reviewCatalog();
    return;
  }
  const requested = new URLSearchParams(location.search).get('scene');
  const scene = scenes.find(([id])=>id===requested) || scenes[0];
  const [id,title,group] = scene;
  document.title=`${title} · maqueta C-11`;
  document.body.dataset.scene=id;
  document.getElementById('navigation').innerHTML=(id==='acceso-denegado'?[]:[['agenda','Agenda',id.includes('odontologo')?'agenda-odontologo':'agenda-secretaria'],['cobros','Cobros','cobros-bloqueados'],['config','Configuración','config-tratamientos']].filter(([key])=>!id.includes('odontologo')||key==='agenda')).map(([key,text,target])=>`<a href="index.html?scene=${target}"${group===key?' aria-current="page"':''}>${text}</a>`).join('');
  document.getElementById('role-label').textContent=id.includes('odontologo')?'Odontólogo':id==='acceso-denegado'?'Paciente':'Secretaria';
  document.getElementById('contenido').innerHTML=group==='agenda'?agenda(id):group==='config'?config(id):cobros(id);
  // Fechas textuales de maqueta: evitar que el locale nativo de Chromium/OS
  // convierta 12 de noviembre en una presentación ambigua 11/12/2026.
  // No es un parser ni un control de fechas productivo.
  document.querySelectorAll('input[type="date"], input[type="datetime-local"]').forEach(node=>{
    const [dayPart, clock] = node.value.split('T');
    const [year, month, day] = dayPart.split('-');
    node.type='text';
    node.value=`${day}/${month}/${year}${clock?` ${clock}`:''}`;
    node.inputMode='numeric';
    node.setAttribute('aria-label',`${node.closest('label').firstChild.textContent.trim()} (día/mes/año${clock?', hora Argentina de 24 horas':''})`);
  });
  document.querySelectorAll('form').forEach(node=>node.addEventListener('submit',event=>event.preventDefault()));
})();
