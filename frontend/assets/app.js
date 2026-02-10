/* DMS – Depot page logic */
(function() {
  var loginBtn = document.getElementById('btn-login');
  var loginStatus = document.getElementById('login-status');
  var depotForm = document.getElementById('depot-form');
  var resultDiv = document.getElementById('result');

  if (loginBtn) {
    loginBtn.addEventListener('click', async function() {
      var username = document.getElementById('username').value;
      var role = document.getElementById('role').value;
      try {
        await dmsApi.login(username, role);
        loginStatus.textContent = 'Connecté ✓';
        loginStatus.className = 'ml-3 text-sm text-green-600';
      } catch(e) {
        loginStatus.textContent = 'Échec connexion';
        loginStatus.className = 'ml-3 text-sm text-red-600';
      }
    });
  }

  if (depotForm) {
    depotForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      var formData = new FormData(depotForm);
      try {
        var data = await dmsApi.upload('/api/depot', formData);
        resultDiv.className = 'mt-4 p-3 bg-green-100 rounded';
        resultDiv.innerHTML = '<strong>Succès!</strong> Submission ID: ' + data.submission_id;
      } catch(err) {
        resultDiv.className = 'mt-4 p-3 bg-red-100 rounded';
        resultDiv.innerHTML = '<strong>Erreur:</strong> ' + err.message;
      }
    });
  }
})();
