export function enableDragDrop(dropTarget, logEl, onUploadStart, onUploadDone){
  function append(text){
    const d = document.createElement('div');
    d.className = 'line muted'; d.innerHTML = text;
    logEl.appendChild(d); logEl.scrollTop = logEl.scrollHeight;
  }
  const overClass = 'drag-over';
  const stop = e => { e.preventDefault(); e.stopPropagation(); };
  ['dragenter','dragover','dragleave','drop'].forEach(evt => dropTarget.addEventListener(evt, stop, false));
  dropTarget.addEventListener('dragenter', ()=> dropTarget.classList.add(overClass));
  dropTarget.addEventListener('dragleave', ()=> dropTarget.classList.remove(overClass));
  dropTarget.addEventListener('drop', async (e)=>{
    dropTarget.classList.remove(overClass);
    const files = e.dataTransfer.files;
    if(!files || !files.length){ return; }
    append(`# Soltados ${files.length} archivo(s)...`);
    const fd = new FormData();
    for(let i=0;i<files.length;i++){ 
      fd.append('file', files[i]);
      append(`# Archivo agregado: ${files[i].name} (${files[i].size} bytes)`);
    }
    try{
      onUploadStart && onUploadStart(files.length);
      const r = await fetch('/upload', { method:'POST', body: fd });
      const data = await r.json();
      onUploadDone && onUploadDone(data);
    }catch(err){
      append(`<span class="error">drop&gt;</span> ${err}`);
    }
  });
}
