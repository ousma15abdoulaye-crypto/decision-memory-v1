const tableBody = document.getElementById("dashboard-body");
const chartCanvas = document.getElementById("status-chart");
let statusChart = null;

const formatValue = (value) => (value === null || value === undefined ? "—" : value);

const buildRow = (item) => {
  const row = document.createElement("tr");
  row.setAttribute("role", "row");
  row.innerHTML = `
    <td class="p-3" role="cell">${formatValue(item.acheteur)}</td>
    <td class="p-3" role="cell">
      <a class="text-indigo-600" href="/templates/offre_detail.html?id=${item.id}" aria-label="Voir détail offre ${formatValue(item.fournisseur)}">
        ${formatValue(item.fournisseur)}
      </a>
    </td>
    <td class="p-3" role="cell">${formatValue(item.date)}</td>
    <td class="p-3" role="cell">${formatValue(item.type)}</td>
    <td class="p-3" role="cell">${formatValue(item.montant)}</td>
    <td class="p-3" role="cell">${formatValue(item.score)}</td>
    <td class="p-3" role="cell">${formatValue(item.statut)}</td>
  `;
  return row;
};

const updateChart = (statusCounts) => {
  const labels = Object.keys(statusCounts);
  const values = Object.values(statusCounts);
  const summaryEl = document.getElementById("chart-summary");
  const summaryText = labels.length
    ? labels.map((l, i) => `${l}: ${values[i]}`).join("; ")
    : "Aucune donnée";
  if (summaryEl) summaryEl.textContent = `Répartition des statuts: ${summaryText}`;
  if (statusChart) {
    statusChart.data.labels = labels;
    statusChart.data.datasets[0].data = values;
    statusChart.update();
    return;
  }
  statusChart = new Chart(chartCanvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: ["#4f46e5", "#22c55e", "#f97316", "#ef4444"],
        },
      ],
    },
  });
};

const loadDashboard = async () => {
  const lot = document.getElementById("filter-lot").value;
  const status = document.getElementById("filter-status").value;
  const date = document.getElementById("filter-date").value;
  const params = new URLSearchParams();
  if (lot) params.append("lot_id", lot);
  if (status) params.append("status", status);
  if (date) params.append("start_date", date);

  const response = await fetch(`/api/dashboard?${params.toString()}`);
  const payload = await response.json();
  tableBody.innerHTML = "";
  tableBody.setAttribute("role", "rowgroup");
  payload.items.forEach((item) => tableBody.appendChild(buildRow(item)));
  updateChart(payload.status_counts || {});
};

document.getElementById("apply-filters").addEventListener("click", loadDashboard);
loadDashboard();
