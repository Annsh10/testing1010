document.getElementById('skincareForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const age = form.age.value;
  const skin_type = form.skin_type.value;
  const goals = Array.from(form.elements['goals'])
                     .filter(cb => cb.checked)
                     .map(cb => cb.value);
  const other = document.getElementById('other').value;

  const payload = { age, skin_type, goals, other };

  try {
    const resp = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type':'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (data.redirect) {
      window.location.href = data.redirect;
    } else {
      alert("Error generating plan");
    }
  } catch (err) {
    alert("Network error: " + err.message);
  }
});
