const summaryEl = document.getElementById("offer-summary");
const docsEl = document.getElementById("offer-docs");
const analysisEl = document.getElementById("offer-analysis");

const params = new URLSearchParams(window.location.search);
const offerId = params.get("id");

const render = (payload) => {
  summaryEl.innerHTML = `
    <p><strong>Fournisseur:</strong> ${payload.offer.supplier_name}</p>
    <p><strong>Montant:</strong> ${payload.offer.amount ?? "—"}</p>
    <p><strong>Statut:</strong> ${payload.analysis?.status ?? "EN_ATTENTE"}</p>
  `;
  docsEl.innerHTML = "";
  payload.documents.forEach((doc) => {
    const li = document.createElement("li");
    li.textContent = `${doc.document_type} — ${doc.filename}`;
    docsEl.appendChild(li);
  });
  analysisEl.textContent = JSON.stringify(
    {
      extraction: payload.extraction,
      analysis: payload.analysis,
      missing_fields: payload.missing_fields,
    },
    null,
    2
  );
};

const loadOffer = async () => {
  if (!offerId) {
    summaryEl.textContent = "Aucun identifiant fourni.";
    return;
  }
  const response = await fetch(`/api/offres/${offerId}`);
  if (!response.ok) {
    summaryEl.textContent = "Offre introuvable.";
    return;
  }
  const payload = await response.json();
  render(payload);
};

loadOffer();
