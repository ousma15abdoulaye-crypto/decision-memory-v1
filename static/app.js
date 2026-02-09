// DMS Frontend — app.js
// Logique commune pour index.html et registre.html

// Utilities
function showMessage(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `message message-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleString('fr-FR');
}

// API Helpers
async function apiCall(endpoint, options = {}) {
  try {
    const res = await fetch(endpoint, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Erreur inconnue' }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }
    
    return await res.json();
  } catch (err) {
    console.error('API Error:', err);
    throw err;
  }
}

// Export for use in HTML inline scripts
window.DMS = {
  apiCall,
  showMessage,
  formatDate,
};
