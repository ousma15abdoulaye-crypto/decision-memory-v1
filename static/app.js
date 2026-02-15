let selectedCaseId = null;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const txt = await res.text();
  try { return { ok: res.ok, data: JSON.parse(txt) }; }
  catch { return { ok: res.ok, data: txt }; }
}

function renderCases(list) {
  const box = document.getElementById("cases");
  box.innerHTML = "";
  if (!list.length) {
    box.innerHTML = "<p class='muted'>Aucun cas créé.</p>";
    return;
  }
  list.forEach(c => {
    const div = document.createElement("div");
    div.className = "case";
    div.innerHTML = `
      <div role="listitem">
        <b>${c.title}</b>
        <div class="muted">
          ID: ${c.id.substring(0, 8)}... | Type: ${c.case_type} | 
          Lot: ${c.lot || "—"} | Status: ${c.status}
        </div>
      </div>
      <button class="select" aria-label="Sélectionner le cas ${c.title.replace(/"/g, "&quot;")}">Sélectionner</button>
    `;
    div.querySelector(".select").onclick = () => {
      selectedCaseId = c.id;
      document.querySelectorAll(".case").forEach(x => x.classList.remove("selected"));
      div.classList.add("selected");
    };
    box.appendChild(div);
  });
}

async function refreshCases() {
  const r = await api("/api/cases");
  if (r.ok) renderCases(r.data);
  else alert("Erreur chargement cas: " + JSON.stringify(r.data));
}

document.getElementById("check_health").onclick = async () => {
  const r = await api("/api/health");
  document.getElementById("system_info").textContent = JSON.stringify(r.data, null, 2);
};

document.getElementById("load_const").onclick = async () => {
  const r = await api("/api/constitution");
  document.getElementById("system_info").textContent = JSON.stringify(r.data, null, 2);
};

document.getElementById("create_case").onclick = async () => {
  const title = document.getElementById("case_title").value.trim();
  if (!title) return alert("Titre requis");
  
  const payload = {
    case_type: document.getElementById("case_type").value,
    title: title,
    lot: document.getElementById("case_lot").value || null
  };
  
  const r = await api("/api/cases", { method: "POST", body: JSON.stringify(payload) });
  if (!r.ok) return alert("Erreur création: " + JSON.stringify(r.data));
  
  await refreshCases();
  alert("✅ Cas créé avec succès");
  document.getElementById("case_title").value = "";
  document.getElementById("case_lot").value = "";
};

document.getElementById("refresh_cases").onclick = refreshCases;

async function upload(kind) {
  if (!selectedCaseId) return alert("⚠️ Sélectionne un cas d'abord");

  const map = {
    "dao": document.getElementById("dao_file"),
    "offer": document.getElementById("offer_files"),
    "cba_template": document.getElementById("cba_file"),
    "pv_template": document.getElementById("pv_file"),
  };

  const input = map[kind];
  const files = input.files;
  
  if (!files || files.length === 0) return alert("Aucun fichier sélectionné");

  for (const f of files) {
    const fd = new FormData();
    fd.append("file", f);

    const res = await fetch(`/api/upload/${selectedCaseId}/${kind}`, { 
      method: "POST", 
      body: fd 
    });
    
    if (!res.ok) {
      const t = await res.text();
      alert(`❌ Upload échoué (${kind}): ${t}`);
      return;
    }
  }

  alert(`✅ Upload OK: ${kind} (${files.length} fichier${files.length > 1 ? 's' : ''})`);
  input.value = "";
}

document.querySelectorAll(".upload_btn").forEach(btn => {
  btn.onclick = () => upload(btn.dataset.kind);
});

document.getElementById("analyze").onclick = async () => {
  if (!selectedCaseId) return alert("⚠️ Sélectionne un cas d'abord");

  document.getElementById("analyze_result").textContent = "⏳ Analyse en cours...";
  
  const r = await api("/api/analyze", { 
    method: "POST", 
    body: JSON.stringify({ case_id: selectedCaseId }) 
  });
  
  document.getElementById("analyze_result").textContent = JSON.stringify(r.data, null, 2);

  const warnBox = document.getElementById("warnings");
  warnBox.innerHTML = "";
  if (r.ok && r.data.warnings && r.data.warnings.missing_data_count > 0) {
    const warn = document.createElement("div");
    warn.className = "warning";
    warn.setAttribute("role", "alert");
    warn.innerHTML = `
      <strong><span aria-hidden="true">⚠️</span> Données manquantes détectées:</strong><br>
      ${r.data.warnings.suppliers_with_missing_data.join(", ")}
      <br><small>Vérifier les offres et compléter manuellement dans le CBA si nécessaire.</small>
    `;
    warnBox.appendChild(warn);
  }

  const dl = document.getElementById("downloads");
  dl.innerHTML = "";
  if (r.ok && r.data.downloads) {
    if (r.data.downloads.cba) {
      const a = document.createElement("a");
      a.href = r.data.downloads.cba;
      a.innerHTML = "<span aria-hidden=\"true\">📊</span> Télécharger CBA (xlsx)";
      a.className = "download";
      a.target = "_blank";
      a.setAttribute("aria-label", "Télécharger le fichier CBA au format Excel");
      dl.appendChild(a);
    }
    if (r.data.downloads.pv) {
      const a = document.createElement("a");
      a.href = r.data.downloads.pv;
      a.innerHTML = "<span aria-hidden=\"true\">📝</span> Télécharger PV Draft (docx)";
      a.className = "download";
      a.target = "_blank";
      a.setAttribute("aria-label", "Télécharger le PV Draft au format Word");
      dl.appendChild(a);
    }
  }
};

document.getElementById("decide").onclick = async () => {
  if (!selectedCaseId) return alert("⚠️ Sélectionne un cas d'abord");
  
  const supplier = document.getElementById("chosen_supplier").value.trim();
  const reason = document.getElementById("decision_reason").value.trim();
  const action = document.getElementById("next_action").value.trim();
  
  if (!supplier || !reason || !action) {
    return alert("⚠️ Tous les champs sont requis pour la décision");
  }

  const payload = {
    case_id: selectedCaseId,
    chosen_supplier: supplier,
    decision_reason: reason,
    next_action: action
  };
  
  const r = await api("/api/decide", { method: "POST", body: JSON.stringify(payload) });
  document.getElementById("decide_result").textContent = JSON.stringify(r.data, null, 2);

  if (r.ok && r.data.pv_with_decision) {
    const a = document.createElement("a");
    a.href = r.data.pv_with_decision;
    a.innerHTML = "<span aria-hidden=\"true\">📝</span> Télécharger PV FINAL (avec décision)";
    a.className = "download";
    a.target = "_blank";
    a.setAttribute("aria-label", "Télécharger le PV final avec décision au format Word");
    document.getElementById("downloads").appendChild(a);
    
    alert("✅ Décision enregistrée. PV final généré.");
    
    document.getElementById("chosen_supplier").value = "";
    document.getElementById("decision_reason").value = "";
    document.getElementById("next_action").value = "";
  }
};

document.getElementById("search_mem").onclick = async () => {
  if (!selectedCaseId) return alert("⚠️ Sélectionne un cas d'abord");
  
  const q = document.getElementById("mem_q").value.trim();
  if (!q) return alert("⚠️ Entre un terme de recherche");
  
  const r = await api(`/api/search_memory/${selectedCaseId}?q=${encodeURIComponent(q)}`);
  document.getElementById("mem_hits").textContent = JSON.stringify(r.data, null, 2);
};

refreshCases();
