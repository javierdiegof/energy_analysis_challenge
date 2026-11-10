(function () {
  const DATA = window.MONCLOVA_DASHBOARD_DATA;
  if (!DATA) return;

  const PLANT_MW = 42;
  let activeTab = "tab1";

  // Palantir Blueprint v6 Dark Telemetry Tokens
  const PAL = {
    grid: "#2a3038",
    axisZero: "#404854",
    tick: "#8f99a8",
    blue: "#4c90f0",
    blueLight: "#8abbff",
    red: "#e76a6e",
    redDeep: "#cd4246",
    green: "#32a467",
    greenLight: "#72ca9b",
    amber: "#ec9a3c",
    amberLight: "#fbb360",
    slateBar: "#404854",
    darkSurface: "#252a31",
    nowLine: "#c5cbd3",
  };

  let t1ScenarioKey = "jun11_scarcity";
  let t1Mode = "combined";
  let t2ScenarioKey = "jun10_scarcity";
  let t2FeedMode = "scada";
  let t2CurtailActive = false;
  let t2BessActive = false;
  let t2EventLogged = false;

  const fmtMoney = (v) => {
    const sign = v < 0 ? "-" : "";
    return `${sign}$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };
  const fmtIntMoney = (v) => {
    const sign = v < 0 ? "-" : "";
    return `${sign}$${Math.round(Math.abs(v)).toLocaleString("en-US")}`;
  };
  const fmtSignedInt = (v) => {
    const sign = v > 0 ? "+" : v < 0 ? "-" : "";
    return `${sign}$${Math.round(Math.abs(v)).toLocaleString("en-US")}`;
  };
  const fmtMxn = (v) => {
    const sign = v < 0 ? "-" : "";
    return `${sign}MXN ${Math.round(Math.abs(v)).toLocaleString("en-US")}`;
  };

  function svgEl(tag, attrs = {}, text = null) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) {
      el.setAttribute(k, v);
    }
    if (text !== null) el.textContent = text;
    return el;
  }

  function setTagIntent(el, intentClass) {
    el.classList.remove("bp6-intent-danger", "bp6-intent-warning", "bp6-intent-success", "bp6-intent-primary");
    if (intentClass) el.classList.add(intentClass);
  }

  // ==================== TOP NAVBAR STATUS ====================
  function updateTopBar() {
    const clockVal = document.getElementById("top-clock-val");
    const priceVal = document.getElementById("top-price-val");
    const alertPill = document.getElementById("top-alert-pill");
    const alertIcon = alertPill.querySelector(".bp6-icon");
    const alertVal = document.getElementById("top-alert-val");

    if (alertIcon) {
      alertIcon.classList.remove("bp6-icon-warning-sign", "bp6-icon-tick-circle");
      alertIcon.classList.add(activeTab === "tab3" ? "bp6-icon-tick-circle" : "bp6-icon-warning-sign");
    }

    if (activeTab === "tab1") {
      const sc = DATA.tab1_scenarios[t1ScenarioKey];
      const maxCleared = Math.max(...sc.hours.map((h) => h.mda_cleared));
      const minCleared = Math.min(...sc.hours.map((h) => h.mda_cleared));
      clockVal.textContent = "10:15 CST · -01h 45m";
      priceVal.textContent = `${fmtIntMoney(sc.hours[19].forecast)}/MWh Est.`;
      if (maxCleared > 2500) {
        setTagIntent(alertPill, "bp6-intent-danger");
        alertVal.textContent = "SCARCITY >$2,500";
      } else if (minCleared < 0) {
        setTagIntent(alertPill, "bp6-intent-warning");
        alertVal.textContent = `NEG MDA (${fmtMoney(minCleared)})`;
      } else {
        setTagIntent(alertPill, "bp6-intent-warning");
        alertVal.textContent = "EVENING RAMP ($1,507)";
      }
    } else if (activeTab === "tab2") {
      const sc = DATA.tab2_scenarios[t2ScenarioKey];
      const cut = sc.hours[sc.cutoff_he - 1];
      clockVal.textContent = t2FeedMode === "scada" ? "19:20 CST · HE 20" : "D-7 EX-POST";
      priceVal.textContent = `${fmtMoney(cut.mtr_actual)}/MWh`;
      setTagIntent(alertPill, "bp6-intent-danger");
      alertVal.textContent = sc.diagnosis_kind === "system_scarcity" ? "SIN SCARCITY >$2,500" : "GRID EMERGENCY + CONG";
    } else {
      clockVal.textContent = "D+7 · MON 09:00";
      priceVal.textContent = `MXN ${Math.round(DATA.tab3_settlement.summary.total_savings_mxn / 1000)}k Saved`;
      setTagIntent(alertPill, "bp6-intent-success");
      alertVal.textContent = "7/7 DAYS RECONCILED";
    }
  }

  // ==================== TAB SWITCHING ====================
  function setActiveTab(tabId) {
    activeTab = tabId;
    document.querySelectorAll(".nav-tab").forEach((b) => {
      b.setAttribute("aria-selected", b.dataset.tab === tabId ? "true" : "false");
    });
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.classList.toggle("active", p.id === tabId);
    });
    updateTopBar();
  }

  document.querySelectorAll(".nav-tab").forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  });

  // ==================== TAB 1 RENDERING ====================
  function renderTab1() {
    const sc = DATA.tab1_scenarios[t1ScenarioKey];
    const basePct = Number(document.getElementById("t1-base-hedge").value);
    const peakPct = Number(document.getElementById("t1-peak-hedge").value);
    const breakeven = Number(document.getElementById("t1-breakeven").value);

    const baseMw = Math.round((PLANT_MW * basePct) / 100);
    const peakMw = Math.round((PLANT_MW * peakPct) / 100);

    document.getElementById("t1-base-hedge-val").textContent = `${basePct}% (${baseMw} MW)`;
    document.getElementById("t1-peak-hedge-val").textContent = `${peakPct}% (${peakMw} MW)`;
    document.getElementById("t1-breakeven-val").textContent = `${fmtIntMoney(breakeven)} / MWh`;

    document.getElementById("t1-chart-title").textContent =
      t1Mode === "combined"
        ? `Tomorrow (${sc.target_date}) · 24h MDA Forecast Band & Alert`
        : `Tomorrow (${sc.target_date}) · Morning Pre-Noon Band (P10–P90)`;
    document.getElementById("t1-chart-sub").textContent = sc.subtitle;

    const hours = sc.hours;
    const meanEst = hours.reduce((a, h) => a + h.forecast, 0) / 24;
    const minP10 = Math.min(...hours.map((h) => h.p10));
    const maxP90 = Math.max(...hours.map((h) => h.p90));
    const minSolar = hours.slice(8, 15).reduce((m, h) => (h.mda_cleared < m.mda_cleared ? h : m), hours[8]);
    const maxHour = hours.reduce((m, h) => (h.mda_cleared > m.mda_cleared ? h : m), hours[0]);
    const minHour = hours.reduce((m, h) => (h.mda_cleared < m.mda_cleared ? h : m), hours[0]);

    let hedgedMwh = 0;
    let totalBill = 0;
    let peakShield = 0;

    hours.forEach((h) => {
      const isPeak = h.he >= 19 && h.he <= 22;
      const mwLocked = isPeak ? peakMw : baseMw;
      const mwSpot = PLANT_MW - mwLocked;
      const refPrice = t1Mode === "combined" ? h.mda_cleared : h.forecast;
      hedgedMwh += mwLocked;
      totalBill += mwLocked * refPrice + mwSpot * h.mtr_actual;
      if (isPeak) peakShield += mwLocked * Math.max(0, h.p90 - refPrice);
    });

    document.getElementById("t1-kpi-mean").innerHTML = `${fmtIntMoney(meanEst)} <span class="unit">MXN/MWh</span>`;
    document.getElementById("t1-kpi-range").textContent = `P10 ${fmtIntMoney(minP10)} – P90 ${fmtIntMoney(maxP90)}/MWh`;
    document.getElementById("t1-kpi-cheap").textContent = `HE ${String(minSolar.he).padStart(2, "0")} · ${fmtIntMoney(minSolar.mda_cleared)}`;

    if (minHour.mda_cleared < 0) {
      document.getElementById("t1-kpi-shock").textContent = `HE ${String(minHour.he).padStart(2, "0")} · ${fmtMoney(minHour.mda_cleared)}`;
      document.getElementById("t1-kpi-shock-sub").textContent = "Negative MDA (<$0) · Maximize load & BESS charge";
    } else {
      const crisisHrs = hours.filter((h) => h.mda_cleared > 2500).length;
      document.getElementById("t1-kpi-shock").textContent = `HE ${String(maxHour.he).padStart(2, "0")} · ${fmtIntMoney(maxHour.mda_cleared)}`;
      document.getElementById("t1-kpi-shock-sub").textContent =
        crisisHrs > 0
          ? `${crisisHrs} hrs >$2,500 threshold · Escalate plant shifts`
          : `Peak >$1,250 break-even · Recommend high peak lock-in`;
    }

    document.getElementById("t1-kpi-bill").textContent = fmtMxn(totalBill);
    document.getElementById("t1-kpi-bill-sub").textContent = `${(hedgedMwh / 24).toFixed(1)} MW avg locked · ${fmtMxn(peakShield)} evening shield`;
    document.getElementById("t1-vol-mwh").textContent = `${hedgedMwh} / 1,008 MWh`;
    document.getElementById("t1-shield-mxn").textContent = fmtMxn(peakShield);

    // Build Palantir Dark Telemetry SVG Chart
    const W = 860, H = 316;
    const m = { l: 56, r: 18, t: 22, b: 28 };
    const pw = W - m.l - m.r;
    const ph = H - m.t - m.b;

    const allVals = hours.flatMap((h) => [h.p10, h.p90, h.forecast, breakeven, t1Mode === "combined" ? h.mda_cleared : h.forecast]);
    let yMin = Math.min(0, Math.floor(Math.min(...allVals) / 100) * 100);
    let yMax = Math.max(2200, Math.ceil(Math.max(...allVals) / 500) * 500);
    if (t1ScenarioKey === "dec25_negative") {
      yMin = -120;
      yMax = Math.max(900, Math.ceil(Math.max(...allVals) / 100) * 100);
    }

    const xOf = (he) => m.l + 8 + ((he - 1) / 23) * (pw - 16);
    const yOf = (val) => m.t + (1 - (val - yMin) / (yMax - yMin)) * ph;

    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}` });

    // Subtle Foundry regime bands (8% opacity)
    svg.appendChild(svgEl("rect", {
      x: xOf(8.6), y: m.t, width: xOf(15.4) - xOf(8.6), height: ph,
      fill: PAL.green, "fill-opacity": "0.08"
    }));
    svg.appendChild(svgEl("rect", {
      x: xOf(18.5), y: m.t, width: xOf(22.5) - xOf(18.5), height: ph,
      fill: PAL.redDeep, "fill-opacity": "0.10"
    }));
    svg.appendChild(svgEl("text", {
      x: (xOf(9) + xOf(15)) / 2, y: m.t + 14, "text-anchor": "middle",
      fill: PAL.greenLight, "font-size": "10", "font-weight": "700", "letter-spacing": "0.04em"
    }, "SOLAR VALLEY (LOW COST)"));
    svg.appendChild(svgEl("text", {
      x: (xOf(18.5) + xOf(22.5)) / 2, y: m.t + 14, "text-anchor": "middle",
      fill: "#fa999c", "font-size": "10", "font-weight": "700", "letter-spacing": "0.04em"
    }, "PEAKER SURGE (19–22H)"));

    const step = yMax <= 1200 ? 200 : 500;
    for (let yv = Math.ceil(yMin / step) * step; yv <= yMax; yv += step) {
      const yy = yOf(yv);
      svg.appendChild(svgEl("line", {
        x1: m.l, x2: W - m.r, y1: yy, y2: yy,
        stroke: yv === 0 ? PAL.axisZero : PAL.grid, "stroke-width": yv === 0 ? "1.3" : "1"
      }));
      svg.appendChild(svgEl("text", {
        x: m.l - 7, y: yy + 3.5, "text-anchor": "end", fill: PAL.tick,
        "font-size": "10", "font-family": "ui-monospace, Menlo, monospace"
      }, fmtIntMoney(yv)));
    }

    hours.forEach((h) => {
      if (h.he === 1 || h.he % 2 === 0) {
        svg.appendChild(svgEl("text", {
          x: xOf(h.he), y: H - 8, "text-anchor": "middle", fill: PAL.tick,
          "font-size": "10", "font-family": "ui-monospace, Menlo, monospace"
        }, String(h.he).padStart(2, "0")));
      }
    });

    // Uncertainty band P10-P90
    const topPts = hours.map((h) => `${xOf(h.he).toFixed(1)},${yOf(h.p90).toFixed(1)}`);
    const botPts = [...hours].reverse().map((h) => `${xOf(h.he).toFixed(1)},${yOf(h.p10).toFixed(1)}`);
    svg.appendChild(svgEl("polygon", {
      points: [...topPts, ...botPts].join(" "),
      fill: PAL.blue, "fill-opacity": "0.18", stroke: "none"
    }));

    // Break-even cost threshold
    const yBe = yOf(breakeven);
    svg.appendChild(svgEl("line", { x1: m.l, x2: W - m.r, y1: yBe, y2: yBe, stroke: PAL.amber, "stroke-width": "1.6", "stroke-dasharray": "6,4" }));
    svg.appendChild(svgEl("rect", { x: m.l + 6, y: yBe - 17, width: 152, height: 15, rx: 2, fill: PAL.darkSurface, stroke: PAL.amber, "stroke-width": "0.9" }));
    svg.appendChild(svgEl("text", { x: m.l + 12, y: yBe - 6.5, fill: PAL.amberLight, "font-size": "9.5", "font-weight": "700", "font-family": "ui-monospace, Menlo, monospace" }, `BREAK-EVEN: ${fmtIntMoney(breakeven)}/MWh`));

    // Expected MDA Forecast
    const fcPts = hours.map((h) => `${xOf(h.he).toFixed(1)},${yOf(h.forecast).toFixed(1)}`).join(" ");
    svg.appendChild(svgEl("polyline", { points: fcPts, fill: "none", stroke: PAL.blue, "stroke-width": "2.6" }));

    // Cleared Auction + Crisp Alert Tag
    if (t1Mode === "combined") {
      const clPts = hours.map((h) => `${xOf(h.he).toFixed(1)},${yOf(h.mda_cleared).toFixed(1)}`).join(" ");
      svg.appendChild(svgEl("polyline", { points: clPts, fill: "none", stroke: PAL.red, "stroke-width": "2.2", "stroke-dasharray": "5,3" }));

      const callHour = minHour.mda_cleared < 0 ? minHour : maxHour;
      const cx = xOf(callHour.he);
      const cy = yOf(callHour.mda_cleared);
      svg.appendChild(svgEl("circle", { cx, cy, r: "5.0", fill: minHour.mda_cleared < 0 ? PAL.blueLight : PAL.redDeep, stroke: "#f6f7f9", "stroke-width": "1.6" }));

      const boxW = 240;
      const boxX = callHour.he >= 17 ? Math.max(m.l + 10, cx - boxW - 22) : cx + 16;
      const boxY = Math.max(m.t + 26, cy - 38);
      const boxTxt =
        minHour.mda_cleared < 0
          ? `NEGATIVE ALERT: HE ${callHour.he} (${fmtMoney(callHour.mda_cleared)})`
          : `CLEARED ALERT: HE ${callHour.he} @ ${fmtIntMoney(callHour.mda_cleared)}/MWh`;
      svg.appendChild(svgEl("line", { x1: boxX + (callHour.he >= 17 ? boxW : 0), y1: boxY + 11, x2: cx + (callHour.he >= 17 ? -6 : 6), y2: cy, stroke: PAL.red, "stroke-width": "1.2" }));
      svg.appendChild(svgEl("rect", { x: boxX, y: boxY, width: boxW, height: 22, rx: 2, fill: "#2a1719", stroke: PAL.redDeep, "stroke-width": "1.1" }));
      svg.appendChild(svgEl("text", { x: boxX + boxW / 2, y: boxY + 14.5, "text-anchor": "middle", fill: "#fa999c", "font-size": "9.8", "font-weight": "700", "font-family": "ui-monospace, Menlo, monospace" }, boxTxt));
    }

    const container = document.getElementById("t1-chart-container");
    container.innerHTML = "";
    container.appendChild(svg);

    const blocks = document.getElementById("t1-hour-blocks");
    blocks.innerHTML = "";
    hours.forEach((h) => {
      const p = t1Mode === "combined" ? h.mda_cleared : h.forecast;
      const mw = h.he >= 19 && h.he <= 22 ? peakMw : baseMw;
      let cls = "normal";
      if (p > 2500) cls = "crisis";
      else if (p > breakeven) cls = "warn";
      else if (p < 700 || p < 0) cls = "cheap";

      const div = document.createElement("div");
      div.className = `h-cell ${cls}`;
      div.innerHTML = `${String(h.he).padStart(2, "0")}h<span class="mw-sub">${mw}MW</span>`;
      blocks.appendChild(div);
    });

    updateTopBar();
  }

  document.getElementById("t1-scenario-select").addEventListener("change", (e) => {
    t1ScenarioKey = e.target.value;
    renderTab1();
  });
  document.getElementById("t1-mode-toggle").addEventListener("click", (e) => {
    const btn = e.target.closest(".seg-btn");
    if (!btn) return;
    t1Mode = btn.dataset.mode;
    document.querySelectorAll("#t1-mode-toggle .seg-btn").forEach((b) => {
      b.classList.toggle("bp6-intent-primary", b === btn);
      b.classList.toggle("bp6-minimal", b !== btn);
    });
    renderTab1();
  });
  ["t1-base-hedge", "t1-peak-hedge", "t1-breakeven"].forEach((id) => {
    document.getElementById(id).addEventListener("input", renderTab1);
  });

  document.getElementById("t1-export-btn").addEventListener("click", () => {
    const sc = DATA.tab1_scenarios[t1ScenarioKey];
    const baseMw = Math.round((PLANT_MW * Number(document.getElementById("t1-base-hedge").value)) / 100);
    const peakMw = Math.round((PLANT_MW * Number(document.getElementById("t1-peak-hedge").value)) / 100);
    const lines = ["Zone,Node,Target_Date,HE,Committed_MW,Expected_MDA_MXN,Bid_Cap_MXN"];
    sc.hours.forEach((h) => {
      const mw = h.he >= 19 && h.he <= 22 ? peakMw : baseMw;
      lines.push(`MONCLOVA,06MON-115,${sc.target_date},${h.he},${mw},${h.forecast},${Math.round(h.p90)}`);
    });
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `CENACE_MDA_Bid_${sc.target_date}.csv`;
    a.click();
    document.getElementById("t1-toast").textContent = `EXPORTED: CENACE_MDA_Bid_${sc.target_date}.csv (${baseMw}/${peakMw} MW locked).`;
  });

  document.getElementById("t1-warn-btn").addEventListener("click", () => {
    const sc = DATA.tab1_scenarios[t1ScenarioKey];
    const pk = sc.hours.reduce((m, h) => (h.mda_cleared > m.mda_cleared ? h : m), sc.hours[0]);
    document.getElementById("t1-toast").textContent = `ALERT SENT: Melt Shop advised for HE ${pk.he} (${fmtIntMoney(pk.mda_cleared)}/MWh) on ${sc.target_date}.`;
  });

  // ==================== TAB 2 RENDERING ====================
  function renderTab2() {
    const sc = DATA.tab2_scenarios[t2ScenarioKey];
    const nowHour = sc.hours[sc.cutoff_he - 1];

    const banner = document.getElementById("t2-feed-banner");
    banner.classList.toggle("bp6-intent-success", t2FeedMode === "scada");
    banner.classList.toggle("bp6-intent-warning", t2FeedMode !== "scada");
    if (t2FeedMode === "scada") {
      document.getElementById("t2-feed-title").textContent = "LIVE UTILITY SCADA TELEMETRY CONNECTED:";
      document.getElementById("t2-feed-desc").textContent =
        "Sub-hourly plant meter telemetry active. (Official public CENACE MTR API clears D+7 days later; toggle for Ex-Post Review.)";
    } else {
      document.getElementById("t2-feed-title").textContent = "CENACE PUBLIC API MODE (7-DAY EX-POST REVIEW):";
      document.getElementById("t2-feed-desc").textContent =
        "CENACE releases official public MTR 7 days after delivery. Rendering audited Ex-Post replay & 1–4h model horizon.";
    }

    document.getElementById("t2-chart-title").textContent =
      `${sc.date} (HE ${sc.cutoff_he}) · Live MTR vs. MDA & 1–4h GBDT (L1)`;

    const unhedgedMw = 6;
    const rawExposure = -unhedgedMw * nowHour.spread;
    const curtailGain = t2CurtailActive ? 12 * Math.max(0, nowHour.mtr_actual - 950) : 0;
    const bessGain = t2BessActive ? 10 * Math.max(0, nowHour.spread) : 0;
    const netHourImpact = rawExposure + curtailGain + bessGain;

    document.getElementById("t2-kpi-mtr").innerHTML = `${fmtMoney(nowHour.mtr_actual)} <span class="unit">/MWh</span>`;
    document.getElementById("t2-kpi-mtr-sub").textContent = `HE ${sc.cutoff_he} Actual · Peaker Scarcity Active`;
    document.getElementById("t2-kpi-mda").innerHTML = `${fmtMoney(nowHour.mda)} <span class="unit">/MWh</span>`;
    document.getElementById("t2-kpi-spread").innerHTML = `${nowHour.spread >= 0 ? "+" : ""}${fmtMoney(nowHour.spread)} <span class="unit">/MWh</span>`;

    const expEl = document.getElementById("t2-kpi-exposure");
    const expSub = document.getElementById("t2-kpi-exposure-sub");
    const expCard = document.getElementById("t2-exposure-card");
    if (t2CurtailActive || t2BessActive) {
      expCard.classList.remove("kpi-red");
      expCard.classList.add("kpi-green");
      expEl.innerHTML = `<span class="txt-green">+${fmtMxn(netHourImpact)} <span class="unit">/hr saved</span></span>`;
      const parts = [];
      if (t2CurtailActive) parts.push("12 MW EAF Curtailed");
      if (t2BessActive) parts.push("10 MW BESS Discharging");
      expSub.textContent = `Mitigation engaged: ${parts.join(" + ")}`;
    } else {
      expCard.classList.remove("kpi-green");
      expCard.classList.add("kpi-red");
      expEl.innerHTML = `<span class="txt-red">${fmtMxn(rawExposure)} <span class="unit">/hr</span></span>`;
      expSub.textContent = `Unmitigated ${unhedgedMw} MW shortfall @ HE ${sc.cutoff_he}`;
    }

    const diagCard = document.getElementById("t2-diag-card");
    diagCard.classList.toggle("bp6-intent-danger", sc.diagnosis_kind === "system_scarcity");
    diagCard.classList.toggle("bp6-intent-warning", sc.diagnosis_kind !== "system_scarcity");
    const diagBadge = document.getElementById("t2-diag-badge");
    setTagIntent(diagBadge, sc.diagnosis_kind === "system_scarcity" ? "bp6-intent-danger" : "bp6-intent-warning");
    diagBadge.textContent = sc.diagnosis_kind === "system_scarcity" ? "SIN SCARCITY" : "CONGESTION + CRISIS";
    document.getElementById("t2-diag-headline").textContent = sc.diagnosis_headline;
    document.getElementById("t2-diag-body").textContent = sc.diagnosis_detail;

    const snaps = sc.nodes_at_cutoff;
    const zoneMean = snaps.reduce((a, n) => a + n.mtr, 0) / snaps.length;
    const ahmNode = snaps.find((n) => n.id === "06AHM-400") || snaps[0];
    document.getElementById("t2-zone-val").textContent = fmtMoney(zoneMean);
    document.getElementById("t2-ahm-val").textContent = fmtMoney(ahmNode.mtr);
    document.getElementById("t2-span-val").textContent = fmtMoney(snaps[0].mtr - snaps[snaps.length - 1].mtr);
    document.getElementById("t2-ahm-badge").textContent = `DELTA ${ahmNode.delta >= 0 ? "+" : ""}${fmtMoney(ahmNode.delta)}`;

    const miniNodesEl = document.getElementById("t2-mini-nodes");
    miniNodesEl.innerHTML = "";
    snaps.slice(0, 6).forEach((n) => {
      const div = document.createElement("div");
      div.className = `mini-node-pill${n.id === "06AHM-400" ? " hv" : ""}`;
      div.innerHTML = `<span>${n.id}</span><strong>${fmtIntMoney(n.mtr)}</strong>`;
      miniNodesEl.appendChild(div);
    });

    document.getElementById("t2-bess-state").textContent = t2BessActive
      ? `ACTIVE: 10 MW DISCHARGE (+${fmtIntMoney(nowHour.spread)}/MWh SPREAD)`
      : `SIGNAL: DISCHARGE NOW (+${fmtIntMoney(nowHour.spread)}/MWh)`;

    document.getElementById("t2-curtail-btn").classList.toggle("btn-active-state", t2CurtailActive);
    document.getElementById("t2-bess-btn").classList.toggle("btn-active-state", t2BessActive);
    document.getElementById("t2-log-btn").classList.toggle("btn-active-state", t2EventLogged);

    // Dual Telemetry SVG Chart
    const W = 860, H = 374;
    const m = { l: 58, r: 18, t: 18, b: 24 };
    const pw = W - m.l - m.r;
    const xPad = 18;
    const topT = m.t, topB = 222, topH = topB - topT;
    const botT = 256, botB = H - m.b, botH = botB - botT;

    const hrs = sc.hours;
    const xOf = (he) => m.l + xPad + ((he - 1) / 23) * (pw - 2 * xPad);

    const topVals = hrs.flatMap((h) => [
      h.mda,
      h.mtr_actual !== null ? h.mtr_actual : h.outlook,
      h.outlook_high !== null ? h.outlook_high : h.mda,
    ]);
    const yMaxTop = Math.ceil(Math.max(...topVals) / 1000) * 1000;
    const yTop = (v) => topT + (1 - v / yMaxTop) * topH;

    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}` });
    const xNow = xOf(sc.cutoff_he);

    // Subtle outlook zone tint
    svg.appendChild(svgEl("rect", { x: xNow, y: topT, width: xOf(24) - xNow + 12, height: topH, fill: PAL.green, "fill-opacity": "0.08" }));
    svg.appendChild(svgEl("rect", { x: xNow, y: botT, width: xOf(24) - xNow + 12, height: botH, fill: "#ffffff", "fill-opacity": "0.03" }));

    const topStep = yMaxTop > 6000 ? 2500 : 1500;
    for (let v = 0; v <= yMaxTop; v += topStep) {
      const yy = yTop(v);
      svg.appendChild(svgEl("line", { x1: m.l, x2: W - m.r, y1: yy, y2: yy, stroke: v === 0 ? PAL.axisZero : PAL.grid, "stroke-width": "1" }));
      svg.appendChild(svgEl("text", { x: m.l - 7, y: yy + 3.5, "text-anchor": "end", fill: PAL.tick, "font-size": "10", "font-family": "ui-monospace, Menlo, monospace" }, fmtIntMoney(v)));
    }

    const fHrs = hrs.filter((h) => h.he >= sc.cutoff_he);
    const polyTop = fHrs.map((h) => `${xOf(h.he).toFixed(1)},${yTop(h.he === sc.cutoff_he ? h.mtr_actual : h.outlook_high).toFixed(1)}`);
    const polyBot = [...fHrs].reverse().map((h) => `${xOf(h.he).toFixed(1)},${yTop(h.he === sc.cutoff_he ? h.mtr_actual : h.outlook_low).toFixed(1)}`);
    svg.appendChild(svgEl("polygon", { points: [...polyTop, ...polyBot].join(" "), fill: PAL.green, "fill-opacity": "0.18" }));

    const mdaPts = hrs.map((h) => `${xOf(h.he).toFixed(1)},${yTop(h.mda).toFixed(1)}`).join(" ");
    svg.appendChild(svgEl("polyline", { points: mdaPts, fill: "none", stroke: PAL.blue, "stroke-width": "2.2" }));

    const actHrs = hrs.filter((h) => h.mtr_actual !== null);
    const actPts = actHrs.map((h) => `${xOf(h.he).toFixed(1)},${yTop(h.mtr_actual).toFixed(1)}`).join(" ");
    svg.appendChild(svgEl("polyline", { points: actPts, fill: "none", stroke: PAL.red, "stroke-width": "2.6" }));
    actHrs.forEach((h) => {
      svg.appendChild(svgEl("circle", { cx: xOf(h.he), cy: yTop(h.mtr_actual), r: h.he === sc.cutoff_he ? "4.6" : "2.4", fill: PAL.red, stroke: h.he === sc.cutoff_he ? "#f6f7f9" : "none", "stroke-width": "1.2" }));
    });

    const outPts = fHrs.map((h) => `${xOf(h.he).toFixed(1)},${yTop(h.he === sc.cutoff_he ? h.mtr_actual : h.outlook).toFixed(1)}`).join(" ");
    svg.appendChild(svgEl("polyline", { points: outPts, fill: "none", stroke: PAL.greenLight, "stroke-width": "2.4", "stroke-dasharray": "6,4" }));

    svg.appendChild(svgEl("line", { x1: xNow, x2: xNow, y1: topT, y2: botB, stroke: PAL.nowLine, "stroke-width": "1.3", "stroke-dasharray": "4,3" }));
    svg.appendChild(svgEl("rect", { x: xNow - 44, y: topT + 2, width: 88, height: 15, rx: 2, fill: "#2f343c", stroke: PAL.nowLine, "stroke-width": "0.8" }));
    svg.appendChild(svgEl("text", { x: xNow, y: topT + 12.5, "text-anchor": "middle", fill: "#f6f7f9", "font-size": "9.2", "font-weight": "700", "font-family": "ui-monospace, Menlo, monospace" }, `NOW · HE ${sc.cutoff_he}`));
    svg.appendChild(svgEl("text", { x: xOf(22.7), y: topT + 28, "text-anchor": "middle", fill: PAL.greenLight, "font-size": "9.5", "font-weight": "700", "font-family": "ui-monospace, Menlo, monospace" }, "1–4h GBDT (L1)"));

    // Bottom spread chart
    const spreads = hrs.map((h) => h.spread);
    const spMin = Math.min(0, Math.floor(Math.min(...spreads) / 1000) * 1000);
    const spMax = Math.max(3000, Math.ceil(Math.max(...spreads) / 1000) * 1000);
    const yBot = (v) => botT + (1 - (v - spMin) / (spMax - spMin)) * botH;
    const yZero = yBot(0);

    svg.appendChild(svgEl("text", { x: m.l, y: botT - 8, fill: "#c5cbd3", "font-size": "10.5", "font-weight": "700", "letter-spacing": "0.02em" }, "REAL-TIME SPREAD (MTR − LOCKED MDA) · DISPATCH SIGNAL"));
    svg.appendChild(svgEl("line", { x1: m.l, x2: W - m.r, y1: yZero, y2: yZero, stroke: PAL.axisZero, "stroke-width": "1.2" }));

    const spStep = spMax > 5000 ? 4000 : 2000;
    for (let v = spStep; v <= spMax; v += spStep) {
      const yy = yBot(v);
      svg.appendChild(svgEl("line", { x1: m.l, x2: W - m.r, y1: yy, y2: yy, stroke: PAL.grid, "stroke-width": "1" }));
      svg.appendChild(svgEl("text", { x: m.l - 7, y: yy + 3.5, "text-anchor": "end", fill: PAL.tick, "font-size": "9.5", "font-family": "ui-monospace, Menlo, monospace" }, `+${fmtIntMoney(v)}`));
    }
    svg.appendChild(svgEl("text", { x: m.l - 7, y: yZero + 3.5, "text-anchor": "end", fill: PAL.tick, "font-size": "9.5", "font-family": "ui-monospace, Menlo, monospace" }, "$0"));

    const barW = Math.max(12, pw / 24 - 6);
    hrs.forEach((h) => {
      const cx = xOf(h.he);
      const yVal = yBot(h.spread);
      const topY = Math.min(yVal, yZero);
      const bh = Math.max(2, Math.abs(yVal - yZero));
      const isProj = h.he > sc.cutoff_he;
      let fill = h.spread > 2000 ? PAL.redDeep : h.spread > 800 ? PAL.amber : h.spread < 0 ? PAL.green : PAL.slateBar;
      svg.appendChild(svgEl("rect", {
        x: cx - barW / 2, y: topY, width: barW, height: bh, rx: 1.5,
        fill, opacity: isProj ? "0.45" : "0.92"
      }));
      if (h.he === 1 || h.he % 2 === 0) {
        svg.appendChild(svgEl("text", { x: cx, y: H - 6, "text-anchor": "middle", fill: PAL.tick, "font-size": "10", "font-family": "ui-monospace, Menlo, monospace" }, String(h.he).padStart(2, "0")));
      }
    });

    const c2 = document.getElementById("t2-chart-container");
    c2.innerHTML = "";
    c2.appendChild(svg);
    updateTopBar();
  }

  document.getElementById("t2-scenario-select").addEventListener("change", (e) => {
    t2ScenarioKey = e.target.value;
    renderTab2();
  });
  document.getElementById("t2-feed-toggle").addEventListener("click", (e) => {
    const btn = e.target.closest(".seg-btn");
    if (!btn) return;
    t2FeedMode = btn.dataset.feed;
    document.querySelectorAll("#t2-feed-toggle .seg-btn").forEach((b) => {
      b.classList.toggle("bp6-intent-primary", b === btn);
      b.classList.toggle("bp6-minimal", b !== btn);
    });
    renderTab2();
  });
  document.getElementById("t2-curtail-btn").addEventListener("click", () => {
    t2CurtailActive = !t2CurtailActive;
    document.getElementById("t2-toast").textContent = t2CurtailActive
      ? "DISPATCHED: EAF Furnace stepped down 12 MW for HE 20–22."
      : "EAF Curtailment paused.";
    renderTab2();
  });
  document.getElementById("t2-bess-btn").addEventListener("click", () => {
    t2BessActive = !t2BessActive;
    document.getElementById("t2-toast").textContent = t2BessActive
      ? "DISPATCHED: 10 MW BESS Discharge capturing evening MTR − MDA spread."
      : "BESS reverted to Standby Hold.";
    renderTab2();
  });
  document.getElementById("t2-log-btn").addEventListener("click", () => {
    t2EventLogged = !t2EventLogged;
    document.getElementById("t2-toast").textContent = t2EventLogged
      ? "TAGGED: Logged to Tab 3 Weekly Extreme-Event Governance queue."
      : "Event tag removed.";
    renderTab2();
  });

  // ==================== TAB 3 RENDERING ====================
  function renderTab3() {
    const t3 = DATA.tab3_settlement;
    const sum = t3.summary;
    const days = t3.days;

    document.getElementById("t3-kpi-savings").innerHTML = `${fmtMxn(sum.total_savings_mxn)} <span class="unit">(-${sum.savings_pct}%)</span>`;
    document.getElementById("t3-kpi-hedge").textContent = fmtMxn(sum.curtail_and_hedge_mxn);
    document.getElementById("t3-kpi-hedge-sub").textContent = `${fmtIntMoney(sum.curtail_only_mxn / 1000)}k EAF curtail + ${fmtIntMoney(sum.hedge_only_mxn / 1000)}k D-1 pre-hedge`;
    document.getElementById("t3-kpi-bess").textContent = fmtMxn(sum.bess_arbitrage_mxn);
    document.getElementById("t3-kpi-settled").textContent = fmtMxn(sum.settled_mxn);
    document.getElementById("t3-kpi-settled-sub").textContent = `Passive baseline: ${fmtMxn(sum.baseline_mxn)} · 7/7 Days Settled`;

    const W = 640, H = 202;
    const m = { l: 54, r: 16, t: 18, b: 26 };
    const pw = W - m.l - m.r;
    const ph = H - m.t - m.b;
    const maxK = Math.ceil(Math.max(...days.map((d) => d.baseline_mxn / 1000)) / 300) * 300;
    const yOf = (k) => m.t + (1 - k / maxK) * ph;

    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}` });
    for (let v = 0; v <= maxK; v += 500) {
      const yy = yOf(v);
      svg.appendChild(svgEl("line", { x1: m.l, x2: W - m.r, y1: yy, y2: yy, stroke: v === 0 ? PAL.axisZero : PAL.grid, "stroke-width": "1" }));
      svg.appendChild(svgEl("text", { x: m.l - 6, y: yy + 3.5, "text-anchor": "end", fill: PAL.tick, "font-size": "10", "font-family": "ui-monospace, Menlo, monospace" }, `$${v}k`));
    }

    const colW = pw / days.length;
    const bw = Math.min(44, colW * 0.54);
    days.forEach((d, idx) => {
      const cx = m.l + (idx + 0.5) * colW;
      const setK = d.settled_mxn / 1000;
      const savK = d.savings_mxn / 1000;
      const ySet = yOf(setK);
      const yBase = yOf(setK + savK);

      svg.appendChild(svgEl("rect", { x: cx - bw / 2, y: ySet, width: bw, height: yOf(0) - ySet, fill: "#383e47", stroke: "#5f6b7c", "stroke-width": "0.8", rx: "1.5" }));
      if (savK > 0) {
        svg.appendChild(svgEl("rect", { x: cx - bw / 2, y: yBase, width: bw, height: ySet - yBase, fill: PAL.green, rx: "1.5" }));
      }
      const lblTxt = savK > 0.5 ? `+${Math.round(savK)}k` : "$0k";
      const lblY = (savK > 0 ? yBase : ySet) - 5;
      svg.appendChild(svgEl("text", { x: cx, y: lblY, "text-anchor": "middle", fill: savK > 0.5 ? PAL.greenLight : PAL.tick, "font-size": "9.5", "font-weight": "700", "font-family": "ui-monospace, Menlo, monospace" }, lblTxt));
      svg.appendChild(svgEl("text", { x: cx, y: H - 7, "text-anchor": "middle", fill: PAL.tick, "font-size": "9.8", "font-family": "ui-monospace, Menlo, monospace" }, d.day_label));
    });

    const c3 = document.getElementById("t3-savings-chart");
    c3.innerHTML = "";
    c3.appendChild(svg);

    const tbody = document.querySelector("#t3-recon-table tbody");
    tbody.innerHTML = "";
    days.forEach((d) => {
      const svCls = d.savings_mxn > 0 ? "txt-green" : "";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${d.day_label}</strong></td>
        <td class="mono">${fmtIntMoney(d.mda_mean)}</td>
        <td class="mono">${fmtIntMoney(d.mtr_peak)}</td>
        <td class="mono">${fmtIntMoney(d.baseline_mxn)}</td>
        <td class="mono"><strong>${fmtIntMoney(d.settled_mxn)}</strong></td>
        <td class="mono ${svCls}"><strong>${fmtSignedInt(d.savings_mxn)}</strong></td>
        <td><span class="bp6-tag bp6-minimal bp6-intent-success mono">D+7 OK</span></td>
      `;
      tbody.appendChild(tr);
    });

    // Blueprint ProgressBar for Time-of-Day reliability
    const todList = document.getElementById("t3-tod-list");
    todList.innerHTML = "";
    t3.tod_accuracy.forEach((row) => {
      const intent = row.within_100_pct >= 85 ? "bp6-intent-success" : row.within_100_pct >= 70 ? "bp6-intent-primary" : "bp6-intent-warning";
      const div = document.createElement("div");
      div.className = "tod-row";
      div.innerHTML = `
        <div class="tod-name"><strong>${row.period}</strong><span class="mono">${row.hours} · ${row.status}</span></div>
        <div class="bp6-progress-bar bp6-no-stripes ${intent}">
          <div class="bp6-progress-meter" style="width:${row.within_100_pct}%;"></div>
        </div>
        <div class="tod-metrics mono"><strong>${row.within_100_pct}% ≤$100</strong><span>MAE $${row.mae}/MWh</span></div>
      `;
      todList.appendChild(div);
    });

    const aBody = document.querySelector("#t3-anomaly-table tbody");
    aBody.innerHTML = "";
    t3.anomaly_queue.forEach((ev) => {
      const intent = ev.status.includes("Excluded") ? "bp6-intent-danger" : ev.status.includes("Approved") ? "bp6-intent-success" : "bp6-intent-warning";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong class="mono">${ev.date}</strong><br><span style="color:#8f99a8;font-size:10px;">${ev.regime}</span></td>
        <td><strong class="mono">${ev.peak_mtr}</strong><br><span style="color:#8f99a8;font-size:10px;">${ev.cause}</span></td>
        <td><button type="button" class="bp6-tag bp6-interactive bp6-minimal ${intent} decision-btn mono" data-id="${ev.id}">${ev.status}</button></td>
      `;
      aBody.appendChild(tr);
    });

    aBody.querySelectorAll(".decision-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const item = t3.anomaly_queue.find((q) => q.id === btn.dataset.id);
        if (!item) return;
        if (item.status.includes("Pending")) item.status = "Approved";
        else if (item.status.includes("Approved")) item.status = "Excluded from Weekly Retrain";
        else item.status = "Pending Analyst Sign-off";
        renderTab3();
      });
    });

    updateTopBar();
  }

  document.getElementById("t3-retrain-btn").addEventListener("click", () => {
    const q = DATA.tab3_settlement.anomaly_queue;
    const exc = q.filter((i) => i.status.includes("Excluded")).length;
    const app = q.filter((i) => i.status.includes("Approved")).length;
    document.getElementById("t3-toast").textContent =
      `SCHEDULED: HistGBDT (L1) Sunday 02:00 CST retrain (${app} approved, ${exc} outliers masked).`;
  });

  renderTab1();
  renderTab2();
  renderTab3();

  const params = new URLSearchParams(window.location.search);
  const startTab = params.get("tab");
  if (startTab && ["tab1", "tab2", "tab3"].includes(startTab)) {
    setActiveTab(startTab);
  } else {
    setActiveTab("tab1");
  }
})();
