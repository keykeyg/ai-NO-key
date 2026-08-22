/* Offline demo data — bar night, Houston */
window.DEMO = {
  mode: "demo",
  device: "demo",
  cameras: [
    { name: "hookah", videos: 1, sample: "Downstairs Across Hookah D1-Aug 21, 11:33 PM - Aug 21, 11:35 PM.mp4" },
    { name: "bar_main", videos: 1 },
    { name: "bar_service", videos: 1 },
    { name: "entrance", videos: 1 },
    { name: "kitchen", videos: 1 },
    { name: "patio", videos: 1 },
  ],
  profiles: [
    { name: "Marcus", role: "hookah" },
    { name: "Nadia", role: "manager" },
  ],
  tagPeople: [
    { index: 0, conf: 0.91, box: [180, 90, 340, 520], label: "black tee, left" },
    { index: 1, conf: 0.87, box: [420, 120, 560, 500], label: "apron, center" },
    { index: 2, conf: 0.74, box: [620, 150, 740, 480], label: "guest, right" },
  ],
  trails: {
    Marcus: {
      name: "Marcus",
      num_appearances: 7,
      window: { start: "2026-08-21T21:00:00", end: "2026-08-22T03:00:00" },
      appearances: [
        { camera: "entrance", local_id: 12, start_s: 42, end_s: 78, score: 0.91 },
        { camera: "bar_main", local_id: 3, start_s: 95, end_s: 140, score: 0.88 },
        { camera: "hookah", local_id: 1, start_s: 5, end_s: 55, score: 0.94 },
        { camera: "hookah", local_id: 18, start_s: 210, end_s: 265, score: 0.86 },
        { camera: "bar_service", local_id: 7, start_s: 300, end_s: 330, score: 0.79 },
        { camera: "patio", local_id: 4, start_s: 400, end_s: 455, score: 0.83 },
        { camera: "entrance", local_id: 29, start_s: 520, end_s: 560, score: 0.81 },
      ],
    },
    Nadia: {
      name: "Nadia",
      num_appearances: 4,
      appearances: [
        { camera: "office", local_id: 2, start_s: 10, end_s: 90, score: 0.93 },
        { camera: "bar_main", local_id: 11, start_s: 120, end_s: 160, score: 0.85 },
        { camera: "kitchen", local_id: 5, start_s: 200, end_s: 240, score: 0.80 },
        { camera: "bar_main", local_id: 22, start_s: 300, end_s: 360, score: 0.88 },
      ],
    },
  },
};

/** Draw a fake CCTV frame with numbered people for demo tag view */
window.drawDemoFrame = function (canvas, people) {
  const w = 960, h = 540;
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");

  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, "#1a1520");
  g.addColorStop(1, "#0c0a10");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);

  for (let i = 0; i < 12; i++) {
    ctx.fillStyle = `rgba(45, 212, 191, ${0.03 + Math.random() * 0.04})`;
    ctx.beginPath();
    ctx.arc(80 + i * 75, 40 + (i % 3) * 20, 18, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.fillStyle = "#151018";
  ctx.fillRect(0, h * 0.72, w, h * 0.28);

  ctx.fillStyle = "#221a28";
  ctx.fillRect(300, 360, 360, 40);
  ctx.fillStyle = "#2a2033";
  ctx.beginPath();
  ctx.ellipse(480, 360, 180, 18, 0, 0, Math.PI * 2);
  ctx.fill();

  const colors = ["#5eead4", "#a78bfa", "#fbbf24"];
  people.forEach((p, i) => {
    const [x1, y1, x2, y2] = p.box;
    ctx.fillStyle = i === 0 ? "#2a3540" : i === 1 ? "#3a2f28" : "#2c2c38";
    ctx.fillRect(x1, y1 + 40, x2 - x1, y2 - y1 - 40);
    ctx.beginPath();
    ctx.arc((x1 + x2) / 2, y1 + 28, 22, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = colors[i % colors.length];
    ctx.lineWidth = 3;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    const label = `#${p.index}`;
    ctx.font = "bold 18px ui-monospace, monospace";
    const tw = ctx.measureText(label).width + 12;
    ctx.fillStyle = colors[i % colors.length];
    ctx.fillRect(x1, Math.max(8, y1 - 28), tw, 24);
    ctx.fillStyle = "#042f2e";
    ctx.fillText(label, x1 + 6, Math.max(26, y1 - 10));
  });

  ctx.fillStyle = "rgba(0,0,0,0.55)";
  ctx.fillRect(12, 12, 220, 44);
  ctx.fillStyle = "#5eead4";
  ctx.font = "12px ui-monospace, monospace";
  ctx.fillText("DEMO · HOOKAH CAM", 24, 30);
  ctx.fillStyle = "#8b93a7";
  ctx.fillText("11:33:18 PM  ·  Aug 21", 24, 48);

  return canvas.toDataURL("image/jpeg", 0.85);
};

window.drawDemoCrop = function (person) {
  const c = document.createElement("canvas");
  c.width = 120;
  c.height = 160;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#12151c";
  ctx.fillRect(0, 0, 120, 160);
  ctx.fillStyle = person.index === 0 ? "#2a3540" : person.index === 1 ? "#3a2f28" : "#2c2c38";
  ctx.fillRect(30, 50, 60, 100);
  ctx.beginPath();
  ctx.arc(60, 36, 20, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#5eead4";
  ctx.lineWidth = 2;
  ctx.strokeRect(8, 8, 104, 144);
  ctx.fillStyle = "#5eead4";
  ctx.font = "bold 14px monospace";
  ctx.fillText("#" + person.index, 14, 28);
  return c.toDataURL("image/jpeg", 0.8);
};
