/* Night Trail extra UX — loaded after main UI script if included */
(function () {
  if (typeof state === "undefined") return;

  // --- Cancel button on progress panel ---
  const prog = document.getElementById("search-progress");
  if (prog && !document.getElementById("btn-cancel")) {
    const b = document.createElement("button");
    b.id = "btn-cancel";
    b.className = "btn";
    b.style.marginTop = ".6rem";
    b.textContent = "Cancel";
    b.onclick = async () => {
      if (!state.job) return toast("No running job");
      await api("/api/jobs/" + state.job + "/cancel", { method: "POST", body: "{}" });
      toast("Cancel requested");
    };
    prog.appendChild(b);
  }

  // Wrap pollJob to track job id
  const _poll = window.pollJob;
  if (typeof _poll === "function") {
    window.pollJob = async function (jobId) {
      state.job = jobId;
      try {
        return await _poll(jobId);
      } finally {
        state.job = null;
      }
    };
  }

  // --- Seed from Protect card ---
  const sidebar = document.querySelector(".sidebar");
  if (sidebar && !document.getElementById("seed-card")) {
    const card = document.createElement("div");
    card.className = "card";
    card.id = "seed-card";
    card.innerHTML = `
      <h3>Seed from NVR</h3>
      <div class="field"><label>Protect camera</label><select id="seed-cam"></select></div>
      <div class="row">
        <div class="field"><label>Time</label><input id="seed-when" placeholder="20:43" value="20:43"/></div>
        <div class="field"><label>Minutes</label><input id="seed-min" value="2"/></div>
      </div>
      <button class="btn btn-primary" id="btn-seed">Pull seed clip</button>
      <p class="hint">Pulls ~2 min around that time so you can tag without manual drop-in.</p>`;
    sidebar.insertBefore(card, sidebar.firstChild);

    async function fillSeedCams() {
      const s = await api("/api/status");
      const sel = document.getElementById("seed-cam");
      if (!sel) return;
      const cams = (s && s.nvr_cameras) || [];
      sel.innerHTML = cams.map(c => `<option value="${c.protect}">${c.protect}</option>`).join("") ||
        `<option value="Hookah Room">Hookah Room</option>`;
    }
    fillSeedCams();

    document.getElementById("btn-seed").onclick = async () => {
      const btn = document.getElementById("btn-seed");
      btn.disabled = true;
      btn.innerHTML = '<span class="loading"></span>';
      const body = {
        camera: document.getElementById("seed-cam").value,
        when: document.getElementById("seed-when").value || "20:43",
        minutes: parseFloat(document.getElementById("seed-min").value || "2"),
      };
      const res = await api("/api/seed", { method: "POST", body: JSON.stringify(body) });
      btn.disabled = false;
      btn.textContent = "Pull seed clip";
      if (!res || !res.ok) return toast((res && res.error) || "Seed pull failed");
      toast(`Seed ready · ${res.files?.length || 0} file(s)`);
      await boot();
      if (res.files && res.files[0]) {
        const vs = document.getElementById("video-path");
        if (vs) vs.value = res.files[0].path;
      }
    };
  }

  // --- Enhance renderTrail with thumbs ---
  const _render = window.renderTrail;
  if (typeof _render === "function") {
    window.renderTrail = function (trail) {
      _render(trail);
      const box = document.getElementById("trail-results");
      if (!box) return;
      box.querySelectorAll(".appear").forEach((el, i) => {
        const a = trail.appearances[i];
        if (!a || el.querySelector(".fb")) return;
        const fb = document.createElement("div");
        fb.className = "fb";
        fb.style.marginTop = ".35rem";
        fb.innerHTML = `<button class="btn" style="width:auto;display:inline-block;padding:.25rem .5rem" data-v="correct">✓</button>
          <button class="btn" style="width:auto;display:inline-block;padding:.25rem .5rem" data-v="wrong">✗</button>`;
        fb.querySelectorAll("button").forEach(b => {
          b.onclick = async () => {
            await api("/api/feedback", {
              method: "POST",
              body: JSON.stringify({
                profile: trail.name,
                trail: trail.name,
                camera: a.camera,
                local_id: a.local_id,
                score: a.score,
                confidence: a.confidence,
                verdict: b.dataset.v,
              }),
            });
            toast(b.dataset.v === "correct" ? "Marked correct" : "Marked wrong");
          };
        });
        el.querySelector("div:nth-child(2)")?.appendChild(fb);
      });
    };
  }

  // --- Site switcher in status area ---
  (async () => {
    const s = await api("/api/status");
    if (!s || !s.sites || s.sites.length < 2) return;
    const pill = document.getElementById("status-pill");
    if (!pill || document.getElementById("site-sel")) return;
    const sel = document.createElement("select");
    sel.id = "site-sel";
    sel.style.cssText = "margin-right:.5rem;background:#12151c;border:1px solid #2a3140;border-radius:8px;padding:.25rem .4rem;font-size:12px";
    sel.innerHTML = s.sites.map(x => `<option value="${x.id}" ${x.active ? "selected" : ""}>${x.name}</option>`).join("");
    sel.onchange = async () => {
      const res = await api("/api/site", { method: "POST", body: JSON.stringify({ site: sel.value }) });
      toast(res ? "Site: " + sel.value : "Site switch failed");
      await boot();
    };
    pill.parentNode.insertBefore(sel, pill);
  })();
})();
