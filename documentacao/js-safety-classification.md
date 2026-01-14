# Classificação Técnica dos Alertas de Segurança JavaScript

**Data:** 2026-01-10
**Fonte:** `tools/js_safety_check.py`

---

## Resumo Numérico

- **CRÍTICO:** 68 alertas
- **ATENÇÃO:** 110 alertas
- **MANUTENÇÃO:** 0 alertas
- **TOTAL:** 178 alertas

---

## 🔴 CRÍTICO - Pode quebrar parsing JavaScript ou causar erro imediato

### templates/jornada.html
- **Linha 1265:** Jinja2 em fetch() sem tojson
  ```
  fetch("{{ url_for('jornada.is_holiday') }}?date=" + encodeURIComponent(d))
  ```

### templates/jornada/index.html
- **Linha 1929:** Jinja2 em fetch() sem tojson
  ```
  fetch('{{ url_for("jornada.get_day_value") }}')
  ```
- **Linha 1960:** Jinja2 em fetch() sem tojson
  ```
  fetch('{{ url_for("jornada.set_day_value") }}', {
  ```

### templates/jornada/view_pdf.html
- **Linha 257:** Jinja2 em window.open() sem tojson
  ```
  window.open('{{ pdf_url }}&mode=print', '_blank');
  ```
- **Linha 260:** Jinja2 em window.open() sem tojson
  ```
  window.open('{{ pdf_url }}&mode=print', '_blank');
  ```

### templates/jornada.html
- **Linha 1156:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  form.action = "{{ url_for('jornada.update', worklog_id='__ID__') }}".replace('__ID__', id);
  ```
- **Linha 1227:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  form.action = "{{ url_for('usuarios.gestao_colabs_folga_credito_adi...
  ```
- **Linha 1229:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  form.action = "{{ url_for('usuarios.gestao_colabs_folga_uso_adicionar')...
  ```
- **Linha 1237:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  if (acaoSelect) acaoSelect.addEventListener('change', setAction);
  ```
- **Linha 1269:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  dateFeedback.textContent = 'Feriado: ' + (j.name || '');
  ```
- **Linha 1331:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  const updateUrl = form.action || "{{ url_for('jornada.update', worklog_id='__ID__') }}".replace('__ID__', editIdVal);
  ```
- **Linha 1345:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  submitLabel.textContent = 'Salvar';
  ```
- **Linha 1367:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  createForm.append('tipo', tipo);
  ```

### templates/jornada/index.html
- **Linha 1933:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  const input = document.getElementById('inputValorDia');
  ```

### templates/jornada/view_pdf.html
- **Linha 257:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  window.open('{{ pdf_url }}&mode=print', '_blank');
  ```
- **Linha 260:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  window.open('{{ pdf_url }}&mode=print', '_blank');
  ```
- **Linha 266:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  const title = 'Relatório de Jornada - MultiMax';
  ```

### templates/receitas.html
- **Linha 528:** Jinja2 dentro de strings JavaScript (dentro de <script>)
  ```
  {id: {{ p.id }}, nome: "{{ p.nome|e }}", preco: {{ p.preco_custo or 0 }}},
  ```

### templates/base.html
- **Linha 354:** Uso de innerHTML (risco XSS)
  ```
  list.innerHTML = data.notifications.map(n => `
  ```
- **Linha 367:** Uso de innerHTML (risco XSS)
  ```
  list.innerHTML = `
  ```
- **Linha 393:** Uso de innerHTML (risco XSS)
  ```
  document.getElementById('notificationsList').innerHTML = `
  ```
- **Linha 422:** Uso de innerHTML (risco XSS)
  ```
  document.getElementById('searchResults').innerHTML = `
  ```
- **Linha 438:** Uso de innerHTML (risco XSS)
  ```
  document.getElementById('searchResults').innerHTML = `
  ```
- **Linha 445:** Uso de innerHTML (risco XSS)
  ```
  document.getElementById('searchResults').innerHTML = searchResults.map((r, i) => `
  ```
- **Linha 519:** Uso de innerHTML (risco XSS)
  ```
  btnView.innerHTML = '<i class="bi bi-eye"></i> Visualizar';
  ```
- **Linha 528:** Uso de innerHTML (risco XSS)
  ```
  btnPrint.innerHTML = '<i class="bi bi-printer"></i> Imprimir';
  ```
- **Linha 552:** Uso de innerHTML (risco XSS)
  ```
  btnDownload.innerHTML = '<i class="bi bi-download"></i> Download';
  ```

### templates/carnes.html
- **Linha 424:** Uso de innerHTML (risco XSS)
  ```
  selects.forEach(s=>{ const cur = s.value; s.innerHTML = B_carrierOptions(); s.value = cur; });
  ```
- **Linha 430:** Uso de innerHTML (risco XSS)
  ```
  row.innerHTML = `
  ```
- **Linha 459:** Uso de innerHTML (risco XSS)
  ```
  blk.innerHTML = `
  ```
- **Linha 572:** Uso de innerHTML (risco XSS)
  ```
  blk.innerHTML = `
  ```
- **Linha 675:** Uso de innerHTML (risco XSS)
  ```
  row.innerHTML = `
  ```

### templates/graficos.html
- **Linha 174:** Uso de innerHTML (risco XSS)
  ```
  body.innerHTML = '';
  ```
- **Linha 199:** Uso de innerHTML (risco XSS)
  ```
  tfoot.innerHTML = '';
  ```

### templates/receitas.html
- **Linha 536:** Uso de innerHTML (risco XSS)
  ```
  wrap.innerHTML = `
  ```
- **Linha 573:** Uso de innerHTML (risco XSS)
  ```
  wrap.innerHTML = `
  ```

### templates/jornada/em_aberto.html
- **Linha 453:** Uso de innerHTML (risco XSS)
  ```
  container.innerHTML = '';
  ```
- **Linha 496:** Uso de innerHTML (risco XSS)
  ```
  diaDiv.innerHTML = `
  ```

### templates/jornada/index.html
- **Linha 1957:** Uso de innerHTML (risco XSS)
  ```
  btnSalvar.innerHTML = '<i class="bi bi-hourglass-split"></i> Salvando...';
  ```
- **Linha 1982:** Uso de innerHTML (risco XSS)
  ```
  btnSalvar.innerHTML = '<i class="bi bi-check-lg"></i> Salvar';
  ```
- **Linha 1991:** Uso de innerHTML (risco XSS)
  ```
  btnSalvar.innerHTML = '<i class="bi bi-check-lg"></i> Salvar';
  ```

### templates/jornada/view_pdf.html
- **Linha 317:** Uso de innerHTML (risco XSS)
  ```
  loading.innerHTML = '<i class="bi bi-exclamation-triangle"></i><p>Erro ao carregar PDF. <a href="{{ pdf_url }}&downlo...
  ```

### templates/base.html
- **Linha 354:** Template string JavaScript com interpolação dinâmica
  ```
  list.innerHTML = data.notifications.map(n => `
                        <a href="${n.url}" class="mm-notification-item...
  ```
- **Linha 433:** Template string JavaScript com interpolação dinâmica
  ```
  const res = await fetch(`/api/v1/search?q=${encodeURIComponent(query)}`);
  ```
- **Linha 445:** Template string JavaScript com interpolação dinâmica
  ```
  document.getElementById('searchResults').innerHTML = searchResults.map((r, i) => `
                        <a href="$...
  ```

### templates/carnes.html
- **Linha 417:** Template string JavaScript com interpolação dinâmica
  ```
  const n = names[i] || `Entregador ${i+1}`;
  ```
- **Linha 418:** Template string JavaScript com interpolação dinâmica
  ```
  opts += `<option value="${i}">${n}</option>`;
  ```
- **Linha 459:** Template string JavaScript com interpolação dinâmica
  ```
  blk.innerHTML = `
    <div class="animal-header-modern">
      <strong>Romaneio #${idx}</strong>
  ```
- **Linha 497:** Template string JavaScript com interpolação dinâmica
  ```
  function B_partKey(f){ return `recepcao-bov:${f.animal}:${f.cat}:${f.lado}`; }
  ```
- **Linha 572:** Template string JavaScript com interpolação dinâmica
  ```
  blk.innerHTML = `
    <div class="animal-header-modern">
      <strong>Peso #${idx}</strong>
  ```
- **Linha 610:** Template string JavaScript com interpolação dinâmica
  ```
  const card = `
    <div class="part-card-modern">
      <div class="part-label-modern">${next === 1 ? 'Primeiro peso'...
  ```
- **Linha 638:** Template string JavaScript com interpolação dinâmica
  ```
  function S_partKey(f){ return `recepcao-sui:${f.animal}:${f.cat}:${f.lado}`; }
  ```

### templates/cronograma.html
- **Linha 442:** Template string JavaScript com interpolação dinâmica
  ```
  const targetContent = document.getElementById(`tab-${targetTab}`);
  ```

### templates/jornada.html
- **Linha 1094:** Template string JavaScript com interpolação dinâmica
  ```
  const targetContent = document.getElementById(`tab-${targetTab}`);
  ```
- **Linha 1255:** Template string JavaScript com interpolação dinâmica
  ```
  return `${dd}/${mm}/${yyyy}`;
  ```
- **Linha 1412:** Template string JavaScript com interpolação dinâmica
  ```
  valor = `${parseFloat(vraw)}h`;
  ```
- **Linha 1414:** Template string JavaScript com interpolação dinâmica
  ```
  valor = `${Math.max(1, Math.round(parseFloat(vraw)))} dia(s)`;
  ```
- **Linha 1427:** Template string JavaScript com interpolação dinâmica
  ```
  box.textContent = `Operação: ${tipo} → Valor: ${valor} → Data: ${data} → Colaborador: ${colaborador}`;
  ```

### templates/receitas.html
- **Linha 536:** Template string JavaScript com interpolação dinâmica
  ```
  wrap.innerHTML = `
        <div class="form-group-modern">
            <label class="form-label-modern">Ingrediente</...
  ```
- **Linha 573:** Template string JavaScript com interpolação dinâmica
  ```
  wrap.innerHTML = `
        <div class="form-group-modern">
            <label class="form-label-modern">Ingrediente</...
  ```

### templates/jornada/em_aberto.html
- **Linha 426:** Template string JavaScript com interpolação dinâmica
  ```
  const url = `/jornada/calendario/${year}/${month}`;
  ```
- **Linha 450:** Template string JavaScript com interpolação dinâmica
  ```
  monthYearEl.textContent = `${monthNames[data.month - 1]} ${data.year}`;
  ```
- **Linha 487:** Template string JavaScript com interpolação dinâmica
  ```
  const dateStr = `${data.year}-${String(data.month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  ```
- **Linha 496:** Template string JavaScript com interpolação dinâmica
  ```
  diaDiv.innerHTML = `
            <div class="jornada-calendar-day-number">${day}</div>
  ```
- **Linha 499:** Template string JavaScript com interpolação dinâmica
  ```
  ${diaData.records && diaData.records.length > 0 ? `
                <div class="jornada-calendar-day-records">
  ```
- **Linha 503:** Template string JavaScript com interpolação dinâmica
  ```
  ${r.record_type === 'horas' ? `${r.hours}h` : ''}
  ```
- **Linha 505:** Template string JavaScript com interpolação dinâmica
  ```
  ${r.record_type === 'folga_usada' ? `-${r.days}d` : ''}
  ```
- **Linha 508:** Template string JavaScript com interpolação dinâmica
  ```
  `).join('')}
                    ${diaData.records.length > 2 ? `<div class="jornada-calendar-day-record">+${diaData....
  ```

---

## 🟡 ATENÇÃO - Não quebra agora, mas pode virar erro

### templates/base.html
- **Linha 117:** Evento onclick inline
- **Linha 144:** Evento onclick inline
- **Linha 151:** Evento onclick inline
- **Linha 158:** Evento onclick inline
- **Linha 173:** Evento onclick inline
- **Linha 191:** Evento onclick inline
- **Linha 192:** Evento onclick inline
- **Linha 198:** Evento onclick inline
- **Linha 234:** Evento onclick inline
- **Linha 355:** Evento onclick inline

### templates/carnes.html
- **Linha 129:** Evento onclick inline
- **Linha 143:** Evento onclick inline
- **Linha 211:** Evento onclick inline
- **Linha 272:** Evento onclick inline
- **Linha 440:** Evento onclick inline
- **Linha 462:** Evento onclick inline
- **Linha 481:** Evento onclick inline
- **Linha 575:** Evento onclick inline
- **Linha 594:** Evento onclick inline
- **Linha 598:** Evento onclick inline
- **Linha 625:** Evento onclick inline
- **Linha 681:** Evento onclick inline
- **Linha 478:** Evento onchange inline
- **Linha 377:** Evento onsubmit inline

### templates/carnes_relatorio.html
- **Linha 10:** Evento onsubmit inline

### templates/colaboradores.html
- **Linha 66:** Evento onsubmit inline
- **Linha 131:** Evento onsubmit inline

### templates/cronograma.html
- **Linha 380:** Evento onsubmit inline

### templates/db.html
- **Linha 343:** Evento onclick inline
- **Linha 356:** Evento onclick inline
- **Linha 369:** Evento onclick inline
- **Linha 272:** Evento onchange inline
- **Linha 278:** Evento onchange inline
- **Linha 43:** Evento onsubmit inline
- **Linha 516:** Evento onsubmit inline
- **Linha 522:** Evento onsubmit inline

### templates/escala.html
- **Linha 17:** Evento onclick inline
- **Linha 396:** Evento onclick inline
- **Linha 211:** Evento onsubmit inline

### templates/gestao.html
- **Linha 178:** Evento onsubmit inline
- **Linha 340:** Evento onsubmit inline
- **Linha 463:** Evento onsubmit inline

### templates/index.html
- **Linha 165:** Evento onsubmit inline

### templates/jornada.html
- **Linha 789:** Evento onclick inline
- **Linha 289:** Evento onsubmit inline
- **Linha 430:** Evento onsubmit inline
- **Linha 547:** Evento onsubmit inline
- **Linha 688:** Evento onsubmit inline

### templates/jornada_unificado.html
- **Linha 53:** Evento onclick inline
- **Linha 30:** Evento onchange inline
- **Linha 132:** Evento onchange inline
- **Linha 102:** Evento onsubmit inline
- **Linha 246:** Evento onsubmit inline

### templates/login.html
- **Linha 618:** Evento onclick inline
- **Linha 689:** Evento onclick inline

### templates/perfil.html
- **Linha 50:** Evento onclick inline
- **Linha 400:** Evento onclick inline
- **Linha 401:** Evento onclick inline
- **Linha 407:** Evento onclick inline
- **Linha 413:** Evento onclick inline
- **Linha 416:** Evento onclick inline
- **Linha 435:** Evento onclick inline
- **Linha 459:** Evento onclick inline

### templates/produtos.html
- **Linha 71:** Evento onsubmit inline

### templates/qrcode_produto.html
- **Linha 23:** Evento onclick inline

### templates/receitas.html
- **Linha 395:** Evento onclick inline
- **Linha 472:** Evento onclick inline
- **Linha 502:** Evento onclick inline
- **Linha 557:** Evento onclick inline
- **Linha 594:** Evento onclick inline
- **Linha 486:** Evento onchange inline
- **Linha 495:** Evento onchange inline
- **Linha 543:** Evento onchange inline
- **Linha 550:** Evento onchange inline
- **Linha 580:** Evento onchange inline
- **Linha 587:** Evento onchange inline
- **Linha 144:** Evento onsubmit inline

### templates/receitas_catalogo.html
- **Linha 115:** Evento onsubmit inline

### templates/users.html
- **Linha 48:** Evento onsubmit inline

### templates/ciclos/index.html
- **Linha 188:** Evento onsubmit inline
- **Linha 304:** Evento onsubmit inline

### templates/jornada/arquivados.html
- **Linha 35:** Evento onclick inline
- **Linha 40:** Evento onclick inline
- **Linha 86:** Evento onclick inline

### templates/jornada/arquivar.html
- **Linha 69:** Evento onclick inline

### templates/jornada/em_aberto.html
- **Linha 60:** Evento onclick inline
- **Linha 65:** Evento onclick inline
- **Linha 94:** Evento onclick inline
- **Linha 131:** Evento onchange inline
- **Linha 158:** Evento onchange inline
- **Linha 165:** Evento onchange inline
- **Linha 312:** Evento onsubmit inline

### templates/jornada/fechado_revisao.html
- **Linha 35:** Evento onclick inline
- **Linha 40:** Evento onclick inline
- **Linha 85:** Evento onclick inline
- **Linha 263:** Evento onclick inline
- **Linha 289:** Evento onclick inline
- **Linha 132:** Evento onchange inline
- **Linha 229:** Evento onsubmit inline

### templates/jornada/index.html
- **Linha 74:** Evento onchange inline
- **Linha 101:** Evento onchange inline
- **Linha 108:** Evento onchange inline
- **Linha 477:** Evento onsubmit inline
- **Linha 577:** Evento onsubmit inline
- **Linha 693:** Evento onsubmit inline

### templates/jornada/novo.html
- **Linha 48:** Evento onchange inline

### templates/jornada/situacao_final.html
- **Linha 35:** Evento onclick inline
- **Linha 40:** Evento onclick inline

### templates/jornada/view_pdf.html
- **Linha 212:** Evento onclick inline
- **Linha 216:** Evento onclick inline

---

## 🔵 MANUTENÇÃO - Apenas má prática

*Nenhum alerta de manutenção encontrado.*

---

## 🎯 O que deve ser corrigido primeiro (CRÍTICOS)

### Prioridade 1: Jinja2 em funções JavaScript sem tojson

- **Jinja2 em fetch() sem tojson:** 3 ocorrências
  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais
  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags
  - Arquivos afetados:
    - `templates/jornada.html` (linha 1265)
    - `templates/jornada/index.html` (linhas 1929, 1960)

- **Jinja2 em window.open() sem tojson:** 2 ocorrências
  - Risco: Quebra parsing JavaScript quando URL contém caracteres especiais
  - Solução: Usar `{{ url_for(...) | tojson }}` ou meta tags
  - Arquivos afetados:
    - `templates/jornada/view_pdf.html` (linhas 257, 260)

### Prioridade 2: Jinja2 dentro de strings JavaScript

- **Total:** 13 ocorrências
  - Risco: Quebra parsing quando valores contêm aspas ou caracteres especiais
  - Solução: Extrair para constantes JS usando `|tojson` ou meta tags
  - Arquivos afetados:
    - `templates/jornada.html` (múltiplas linhas)
    - `templates/jornada/index.html` (linha 1933)
    - `templates/jornada/view_pdf.html` (linhas 257, 260, 266)
    - `templates/receitas.html` (linha 528)

### Prioridade 3: innerHTML com dados dinâmicos

- **Total:** 24 ocorrências
  - Risco: XSS (Cross-Site Scripting) se dados vierem do backend
  - Solução: Usar `textContent` ou sanitizar dados antes de inserir
  - Arquivos afetados:
    - `templates/base.html` (9 ocorrências)
    - `templates/carnes.html` (5 ocorrências)
    - `templates/graficos.html` (2 ocorrências)
    - `templates/receitas.html` (2 ocorrências)
    - `templates/jornada/em_aberto.html` (2 ocorrências)
    - `templates/jornada/index.html` (3 ocorrências)
    - `templates/jornada/view_pdf.html` (1 ocorrência)

### Prioridade 4: Template strings com interpolação dinâmica

- **Total:** 26 ocorrências
  - Risco: XSS se dados não forem escapados corretamente
  - Solução: Escapar dados ou usar `textContent`/`createElement`
  - Arquivos afetados:
    - `templates/base.html` (3 ocorrências)
    - `templates/carnes.html` (7 ocorrências)
    - `templates/cronograma.html` (1 ocorrência)
    - `templates/jornada.html` (5 ocorrências)
    - `templates/receitas.html` (2 ocorrências)
    - `templates/jornada/em_aberto.html` (8 ocorrências)

---

## 📝 Notas

- Esta classificação foi gerada automaticamente
- Nenhum código funcional foi alterado durante a geração deste relatório
- Para corrigir os alertas, consulte a documentação técnica do projeto
