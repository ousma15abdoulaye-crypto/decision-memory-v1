/* DMS API client – vanilla JS, no framework */
var dmsApi = (function() {
  var baseUrl = '';

  function getToken() {
    return localStorage.getItem('dms_token') || '';
  }

  function setToken(token) {
    localStorage.setItem('dms_token', token);
  }

  function headers() {
    var h = { 'Content-Type': 'application/json' };
    var token = getToken();
    if (token) h['Authorization'] = 'Bearer ' + token;
    return h;
  }

  async function login(username, role) {
    var res = await fetch(baseUrl + '/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, role: role })
    });
    if (!res.ok) throw new Error('Login failed');
    var data = await res.json();
    setToken(data.access_token);
    return data;
  }

  async function get(url) {
    var res = await fetch(baseUrl + url, { headers: headers() });
    if (!res.ok) throw new Error('GET ' + url + ' failed: ' + res.status);
    return res.json();
  }

  async function post(url, body) {
    var opts = { method: 'POST', headers: headers() };
    if (body) opts.body = JSON.stringify(body);
    var res = await fetch(baseUrl + url, opts);
    if (!res.ok) throw new Error('POST ' + url + ' failed: ' + res.status);
    return res.json();
  }

  async function upload(url, formData) {
    var h = {};
    var token = getToken();
    if (token) h['Authorization'] = 'Bearer ' + token;
    var res = await fetch(baseUrl + url, { method: 'POST', headers: h, body: formData });
    if (!res.ok) throw new Error('Upload failed: ' + res.status);
    return res.json();
  }

  return { login: login, get: get, post: post, upload: upload, setToken: setToken, getToken: getToken };
})();
