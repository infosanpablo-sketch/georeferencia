// Fill hidden fields latitude, longitude and tz on the form
document.addEventListener('DOMContentLoaded', function () {
  const latInput = document.getElementById('latitude');
  const lonInput = document.getElementById('longitude');
  const tzInput = document.getElementById('tz');
  if (tzInput) {
    try {
      tzInput.value = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    } catch (e) {
      tzInput.value = 'UTC';
    }
  }

  const geoBtn = document.getElementById('btn-get-geo');
  if (geoBtn) {
    geoBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (!navigator.geolocation) {
        alert('Geolocalización no disponible en este navegador.');
        return;
      }
      geoBtn.disabled = true;
      geoBtn.textContent = 'Obteniendo ubicación...';
      navigator.geolocation.getCurrentPosition(function (pos) {
        latInput.value = pos.coords.latitude;
        lonInput.value = pos.coords.longitude;
        geoBtn.textContent = 'Ubicación obtenida';
      }, function (err) {
        alert('Error al obtener ubicación: ' + err.message);
        geoBtn.disabled = false;
        geoBtn.textContent = 'Obtener ubicación';
      }, {enableHighAccuracy: true, timeout: 10000, maximumAge: 60000});
    });
  }
});