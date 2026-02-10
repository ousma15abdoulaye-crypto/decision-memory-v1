const uploadForm = document.getElementById("cba-upload-form");
const uploadStatus = document.getElementById("upload-status");
const pvStatus = document.getElementById("pv-status");

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(uploadForm);
  uploadStatus.textContent = "Envoi en cours...";
  const response = await fetch("/api/cba-review/upload", {
    method: "POST",
    body: formData,
  });
  const payload = await response.json();
  uploadStatus.textContent = response.ok
    ? `CBA chargé: ${payload.document_id}`
    : `Erreur: ${payload.detail || "upload"}`;
});

const triggerPv = async (endpoint) => {
  const lotId = document.getElementById("pv-lot-id").value;
  if (!lotId) {
    pvStatus.textContent = "Veuillez renseigner un lot.";
    return;
  }
  pvStatus.textContent = "Génération en cours...";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lot_id: lotId }),
  });
  const payload = await response.json();
  pvStatus.textContent = response.ok
    ? `PV généré: ${payload.document_id}`
    : `Erreur: ${payload.detail || "PV"}`;
};

document.getElementById("pv-ouverture").addEventListener("click", () => {
  triggerPv("/api/pv/ouverture");
});
document.getElementById("pv-analyse").addEventListener("click", () => {
  triggerPv("/api/pv/analyse");
});
