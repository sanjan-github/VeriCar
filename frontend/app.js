const state = {
  vehicleId: "",
  vehicleRecord: null,
  assessment: null,
  overallAssessment: null,
  explanation: null,
  history: null,
};

function generateIdempotencyKey() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "idem-" + Date.now() + "-" + Math.random().toString(36).substring(2, 11);
}

function getIdempotencyKey() {
  if (!elements.reportForm.dataset.idempotencyKey) {
    elements.reportForm.dataset.idempotencyKey = generateIdempotencyKey();
  }
  return elements.reportForm.dataset.idempotencyKey;
}

const $ = (selector) => (typeof document !== "undefined" && typeof document.querySelector === "function" ? document.querySelector(selector) : null);

const elements = {
  searchForm: $("#search-form"),
  vehicleInput: $("#vehicle-id"),
  searchButton: $("#search-form button") || $("#search-submit-btn"),
  searchSubmitBtn: $("#search-submit-btn"),
  statusBanner: $("#status-banner"),
  emptyState: $("#empty-state"),
  vehicleView: $("#vehicle-view"),
  vehicleTitle: $("#vehicle-title"),
  memoryStatus: $("#memory-status"),
  findingState: $("#finding-state"),
  confidenceValue: $("#confidence-value"),
  confidenceCopy: $("#confidence-copy"),
  confidenceToggle: $("#confidence-toggle"),
  confidenceDetails: $("#confidence-details"),
  supportCount: $("#support-count"),
  contradictionCount: $("#contradiction-count"),
  supportWeight: $("#support-weight"),
  contradictionWeight: $("#contradiction-weight"),
  explanationStatus: $("#explanation-status"),
  explanationContent: $("#explanation-content"),
  evidenceCount: $("#evidence-count"),
  timeline: $("#timeline"),
  reportForm: $("#report-form"),
  pdfButton: $("#pdf-button"),
  reportVehicleId: $("#report-vehicle-id"),
  reportVin: $("#report-vin"),
  reportSourceId: $("#report-source-id"),
  reportSourceType: $("#report-source-type"),
  reportObservedAt: $("#report-observed-at"),
  reportText: $("#report-text"),
  reportButton: $("#report-form button") || $("#save-report-btn"),
  saveReportBtn: $("#save-report-btn"),
  reportResult: $("#report-result"),
  apiStatus: $("#api-status"),
  dbStatus: $("#db-status"),
  toggleRegisterBtn: $("#toggle-register-btn"),
  registerDrawer: $("#register-drawer"),
  registerForm: $("#register-form"),
  regCarId: $("#reg-car-id"),
  regBrand: $("#reg-brand"),
  regModel: $("#reg-model"),
  regYear: $("#reg-year"),
  regVariant: $("#reg-variant"),
  regFuel: $("#reg-fuel"),
  regTransmission: $("#reg-transmission"),
  regOdometer: $("#reg-odometer"),
  regPrice: $("#reg-price"),
  regOwners: $("#reg-owners"),
  regState: $("#reg-state"),
  regVin: $("#reg-vin"),
  regCancelBtn: $("#reg-cancel-btn"),
  regStatus: $("#reg-status"),
  vehicleBadges: $("#vehicle-badges"),
  overallAssessmentCard: $("#overall-assessment-card"),
  verdictBadge: $("#verdict-badge"),
  overallConfidence: $("#overall-confidence"),
  repairRange: $("#repair-range"),
  negotiationReduction: $("#negotiation-reduction"),
  criticalGroupCard: $("#critical-group-card"),
  criticalCount: $("#critical-count"),
  criticalList: $("#critical-list"),
  warningGroupCard: $("#warning-group-card"),
  warningCount: $("#warning-count"),
  warningList: $("#warning-list"),
  infoGroupCard: $("#info-group-card"),
  infoCount: $("#info-count"),
  infoList: $("#info-list"),
  actionGroupCard: $("#action-group-card"),
  nextChecksList: $("#next-checks-list")
};

function setStatus(message, visible = true) {
  if (!elements.statusBanner) return;
  elements.statusBanner.textContent = message;
  elements.statusBanner.hidden = !visible;
}

function formatDate(value) {
  if (!value) return "Unknown date";
  const date = new Date(String(value).length === 10 ? String(value) + "T00:00:00" : value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(date);
}

function formatINR(value) {
  if (value == null || Number.isNaN(Number(value))) return "₹0";
  return "₹" + Number(value).toLocaleString("en-IN");
}

function titleCase(value) {
  return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function allEvidence(finding) {
  return [
    ...(finding.supporting_evidence || []).map((item) => ({ ...item, polarity: "supporting" })),
    ...(finding.contradicting_evidence || []).map((item) => ({ ...item, polarity: "contradicting" })),
    ...(finding.unresolved_evidence || []).map((item) => ({ ...item, polarity: "unresolved" })),
  ].sort((a, b) => String(b.observed_at).localeCompare(String(a.observed_at)));
}

function renderEvidenceItems(items) {
  if (!elements.timeline) return;
  if (!items.length) {
    elements.timeline.innerHTML = '<p class="muted">No historical reports are available for this vehicle.</p>';
    return;
  }

  elements.timeline.innerHTML = items
    .map(
      (item) =>
        '<article class="evidence-item">' +
        '<div class="evidence-meta"><time datetime="' +
        escapeHtml(item.observed_at) +
        '">' +
        formatDate(item.observed_at) +
        '</time><span>·</span><span>' +
        escapeHtml(titleCase(item.source_type)) +
        ' (' +
        escapeHtml(item.source_id) +
        ')</span><span class="evidence-polarity ' +
        escapeHtml(item.polarity || "unresolved") +
        '">' +
        escapeHtml(item.polarity || "unresolved") +
        '</span></div>' +
        '<p class="evidence-text">' +
        escapeHtml(item.text) +
        '</p>' +
        (item.effective_reliability == null
          ? ""
          : '<p class="evidence-weight">Effective Source Weight: ' +
            Number(item.effective_reliability).toFixed(2) +
            '</p>') +
        '</article>'
    )
    .join("");
}

function renderHistory(history) {
  const reports = Array.isArray(history?.reports) ? history.reports : [];
  if (elements.evidenceCount) {
    elements.evidenceCount.textContent = reports.length + " report" + (reports.length === 1 ? "" : "s");
  }
  renderEvidenceItems(reports);
}

function renderEvidence(finding) {
  const evidence = allEvidence(finding);
  if (elements.evidenceCount) {
    elements.evidenceCount.textContent = evidence.length + " report" + (evidence.length === 1 ? "" : "s");
  }

  if (!evidence.length) {
    renderHistory(state.history);
    return;
  }

  renderEvidenceItems(evidence);
}

function renderExplanation(explanation, status) {
  if (!elements.explanationStatus || !elements.explanationContent) return;
  elements.explanationStatus.textContent =
    status === "available" ? "Generated by Groq LLM" : "Unavailable";

  if (!explanation) {
    elements.explanationContent.innerHTML =
      '<p class="muted">Automated explanation is currently unavailable. Deterministic rule evaluation and memory evidence remain authoritative.</p>';
    return;
  }

  const caveats = explanation.caveats?.length
    ? "<h4>Caveats & Missing History</h4><ul>" +
      explanation.caveats.map((item) => "<li>" + escapeHtml(item) + "</li>").join("") +
      "</ul>"
    : "";

  elements.explanationContent.innerHTML =
    "<p><strong>" +
    escapeHtml(explanation.summary) +
    "</strong></p>" +
    "<h4>Rationale</h4><p>" +
    escapeHtml(explanation.rationale) +
    "</p>" +
    caveats;
}

function renderVehicleSpecs(car) {
  if (!elements.vehicleBadges) return;
  if (!car) {
    elements.vehicleBadges.innerHTML = '<span class="spec-entry">Unregistered Vehicle ID</span>';
    return;
  }

  const badges = [];
  if (car.brand && car.model) badges.push(car.brand + " " + car.model + (car.variant ? " " + car.variant : ""));
  if (car.manufacture_year) badges.push("Year: " + car.manufacture_year);
  if (car.fuel_type) badges.push(car.fuel_type);
  if (car.transmission) badges.push(car.transmission);
  if (car.odometer_km != null) badges.push(Number(car.odometer_km).toLocaleString("en-IN") + " km");
  if (car.asking_price_inr != null) badges.push(formatINR(car.asking_price_inr));
  if (car.previous_owners != null) badges.push(car.previous_owners + " Owner" + (car.previous_owners === 1 ? "" : "s"));
  if (car.registration_state) badges.push("State: " + car.registration_state);
  if (car.vin) badges.push("VIN: " + car.vin);

  elements.vehicleBadges.innerHTML = badges
    .map((b) => '<span class="spec-entry">' + escapeHtml(b) + '</span>')
    .join("");
}

function renderOverallAssessment(overall) {
  if (!elements.verdictBadge) return;
  if (!overall) {
    elements.verdictBadge.textContent = "REVIEW";
    elements.verdictBadge.className = "verdict-stamp negotiate";
    if (elements.overallConfidence) elements.overallConfidence.textContent = "—";
    if (elements.repairRange) elements.repairRange.textContent = "—";
    if (elements.negotiationReduction) elements.negotiationReduction.textContent = "—";
    if (elements.criticalGroupCard) elements.criticalGroupCard.hidden = true;
    if (elements.warningGroupCard) elements.warningGroupCard.hidden = true;
    if (elements.infoGroupCard) elements.infoGroupCard.hidden = true;
    if (elements.nextChecksList) {
      elements.nextChecksList.innerHTML = '<li>Submit condition inspection to generate full checklist.</li>';
    }
    return;
  }

  const verdict = (overall.verdict || "REVIEW").toUpperCase();
  elements.verdictBadge.textContent = verdict;
  elements.verdictBadge.className = "verdict-stamp " + verdict.toLowerCase();

  if (elements.overallConfidence) elements.overallConfidence.textContent = overall.confidence != null ? overall.confidence + "%" : "—";
  if (elements.repairRange) {
    if (overall.near_term_repair_range_inr && overall.near_term_repair_range_inr.length === 2) {
      elements.repairRange.textContent =
        formatINR(overall.near_term_repair_range_inr[0]) + " – " + formatINR(overall.near_term_repair_range_inr[1]);
    } else {
      elements.repairRange.textContent = "₹0 – ₹0";
    }
  }

  if (elements.negotiationReduction) {
    elements.negotiationReduction.textContent = formatINR(overall.negotiation_reduction_inr ?? 0);
  }

  // Critical Findings
  const criticals = overall.critical_findings || [];
  if (elements.criticalCount) elements.criticalCount.textContent = criticals.length;
  if (elements.criticalGroupCard) {
    if (criticals.length && elements.criticalList) {
      elements.criticalList.innerHTML = criticals.map((c) => "<li>" + escapeHtml(c) + "</li>").join("");
      elements.criticalGroupCard.hidden = false;
    } else {
      elements.criticalGroupCard.hidden = true;
    }
  }

  // Warning Findings
  const warnings = overall.warning_findings || [];
  if (elements.warningCount) elements.warningCount.textContent = warnings.length;
  if (elements.warningGroupCard) {
    if (warnings.length && elements.warningList) {
      elements.warningList.innerHTML = warnings.map((w) => "<li>" + escapeHtml(w) + "</li>").join("");
      elements.warningGroupCard.hidden = false;
    } else {
      elements.warningGroupCard.hidden = true;
    }
  }

  // Info Findings
  const infos = overall.info_findings || [];
  if (elements.infoCount) elements.infoCount.textContent = infos.length;
  if (elements.infoGroupCard) {
    if (infos.length && elements.infoList) {
      elements.infoList.innerHTML = infos.map((i) => "<li>" + escapeHtml(i) + "</li>").join("");
      elements.infoGroupCard.hidden = false;
    } else {
      elements.infoGroupCard.hidden = true;
    }
  }

  // Next Checks
  const checks = overall.next_checks || [];
  if (elements.nextChecksList) {
    if (checks.length) {
      elements.nextChecksList.innerHTML = checks.map((chk) => "<li>" + escapeHtml(chk) + "</li>").join("");
    } else {
      elements.nextChecksList.innerHTML = "<li>Perform independent physical inspection and verify original documents.</li>";
    }
  }
}

function renderAssessment(payload) {
  const finding = Array.isArray(payload.findings) ? payload.findings[0] : null;

  state.assessment = payload;
  state.overallAssessment = payload.overall_assessment || null;
  state.explanation = payload.explanation || null;

  if (elements.vehicleTitle) {
    elements.vehicleTitle.textContent =
      (state.vehicleRecord?.brand ? state.vehicleRecord.brand + " " + state.vehicleRecord.model + " · " : "") +
      (payload.vehicle_id || state.vehicleId);
  }

  const memoryStatusCopy = {
    available: "Historical memory available",
    empty: "No matching assessment evidence",
    unavailable: "Historical memory temporarily unavailable"
  };
  if (elements.memoryStatus) {
    elements.memoryStatus.textContent =
      memoryStatusCopy[payload.memory_status] || "Historical memory status unavailable";
  }

  if (elements.vehicleView) elements.vehicleView.hidden = false;
  if (elements.emptyState) elements.emptyState.hidden = true;
  if (elements.reportVehicleId) elements.reportVehicleId.value = payload.vehicle_id || state.vehicleId;

  renderOverallAssessment(payload.overall_assessment);

  if (!finding) {
    if (elements.findingState) elements.findingState.textContent = "No finding";
    if (elements.confidenceValue) elements.confidenceValue.textContent = "—";
    if (elements.confidenceCopy) elements.confidenceCopy.textContent = "No evidence was returned for this vehicle and finding.";
    if (elements.supportCount) elements.supportCount.textContent = "0";
    if (elements.contradictionCount) elements.contradictionCount.textContent = "0";
    if (elements.supportWeight) elements.supportWeight.textContent = "0.00";
    if (elements.contradictionWeight) elements.contradictionWeight.textContent = "0.00";
    if (elements.explanationStatus) elements.explanationStatus.textContent = "Unavailable";
    if (elements.explanationContent) elements.explanationContent.innerHTML = '<p class="muted">There is no finding to explain yet.</p>';
    if (elements.evidenceCount) elements.evidenceCount.textContent = "0 reports";
    if (elements.timeline) elements.timeline.innerHTML = '<p class="muted">Add a report to begin building the vehicle history.</p>';
    return;
  }

  const confidence = finding.evidence_confidence;
  const copy = {
    insufficient_evidence: "There is not enough evidence to characterize this finding.",
    limited_evidence: "Some evidence exists, but the accumulated record is limited.",
    moderate_evidence: "The available evidence supports a moderate-strength finding.",
    strong_evidence: "The available evidence provides strong support for this finding."
  };

  if (elements.findingState) elements.findingState.textContent = String(finding.status || "unknown").replaceAll("_", " ");
  if (elements.confidenceValue) elements.confidenceValue.textContent = confidence == null ? "—" : Math.round(confidence) + "%";
  if (elements.confidenceCopy) elements.confidenceCopy.textContent = copy[finding.status] || "Assessment available.";
  if (elements.supportCount) elements.supportCount.textContent = finding.supporting_sources ?? 0;
  if (elements.contradictionCount) elements.contradictionCount.textContent = finding.contradicting_sources ?? 0;
  if (elements.supportWeight) elements.supportWeight.textContent = Number(finding.support_weight ?? 0).toFixed(2);
  if (elements.contradictionWeight) elements.contradictionWeight.textContent = Number(finding.contradiction_weight ?? 0).toFixed(2);

  if (elements.confidenceDetails) elements.confidenceDetails.hidden = true;
  if (elements.confidenceToggle) elements.confidenceToggle.setAttribute("aria-expanded", "false");
  renderExplanation(payload.explanation, payload.explanation_status);
  renderEvidence(finding);
}

async function fetchJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(
      typeof window !== "undefined" && window.location?.protocol === "file:"
        ? "The UI was opened as a file. Start the VeriCar FastAPI server and open http://127.0.0.1:8000/."
        : "The backend could not be reached. Make sure the VeriCar API is running."
    );
  }

  const contentType = (response.headers && response.headers.get("content-type")) || "";
  const payload = contentType.includes("application/json") ? await response.json() : {};

  if (!response.ok) {
    const detail = payload.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.error?.message || detail?.message || "The request could not be completed.";
    throw new Error(message);
  }

  return payload;
}

async function checkBackend() {
  try {
    const payload = await fetchJson("/health", { headers: { Accept: "application/json" } });
    if (elements.apiStatus) {
      elements.apiStatus.textContent = "API: " + (payload.status === "ok" ? "online" : "unavailable");
      if (elements.apiStatus.classList) elements.apiStatus.classList.add(payload.status === "ok" ? "online" : "offline");
    }
  } catch {
    if (elements.apiStatus) {
      elements.apiStatus.textContent = "API: offline";
      if (elements.apiStatus.classList) elements.apiStatus.classList.add("offline");
    }
  }

  try {
    const readiness = await fetchJson("/readiness", { headers: { Accept: "application/json" } });
    if (elements.dbStatus) {
      const dbReady = readiness.checks?.database === "available";
      elements.dbStatus.textContent = "DB: " + (dbReady ? "ready" : "unavailable");
      if (elements.dbStatus.classList) elements.dbStatus.classList.add(dbReady ? "online" : "offline");
    }
  } catch {
    if (elements.dbStatus) {
      elements.dbStatus.textContent = "DB: offline";
      if (elements.dbStatus.classList) elements.dbStatus.classList.add("offline");
    }
  }
}

async function loadVehicle(vehicleId) {
  if (!vehicleId) return;
  setStatus("Retrieving durable vehicle history…");
  if (elements.emptyState) elements.emptyState.hidden = true;
  if (elements.vehicleView) elements.vehicleView.hidden = true;
  if (elements.searchButton) elements.searchButton.disabled = true;

  try {
    const history = await fetchJson(
      "/api/vehicles/" + encodeURIComponent(vehicleId),
      { headers: { Accept: "application/json" } }
    );
    state.vehicleId = vehicleId;
    state.history = history;
    state.vehicleRecord = history.vehicle || null;

    if (elements.vehicleTitle) elements.vehicleTitle.textContent = vehicleId;
    if (elements.reportVehicleId) elements.reportVehicleId.value = vehicleId;
    if (elements.vehicleBadges) renderVehicleSpecs(history.vehicle);
    if (history.vehicle?.vin && elements.reportVin) {
      elements.reportVin.value = history.vehicle.vin;
    }
    if (elements.vehicleView) elements.vehicleView.hidden = false;
    if (elements.pdfButton) {
      elements.pdfButton.href = "/api/vehicles/" + encodeURIComponent(vehicleId) + "/assessment/report.pdf";
      elements.pdfButton.hidden = false;
    }
    renderHistory(history);

    try {
      const payload = await fetchJson(
        "/api/vehicles/" + encodeURIComponent(vehicleId) +
        "/assessment/explanation?issue=transmission_shift_behavior",
        { headers: { Accept: "application/json" } }
      );
      renderAssessment(payload);
      setStatus("", false);
    } catch (error) {
      if (elements.findingState) elements.findingState.textContent = "Assessment unavailable";
      if (elements.confidenceValue) elements.confidenceValue.textContent = "—";
      if (elements.confidenceCopy) {
        elements.confidenceCopy.textContent =
          "The durable vehicle history is available, but historical-memory assessment is temporarily unavailable.";
      }
      if (elements.supportCount) elements.supportCount.textContent = "—";
      if (elements.contradictionCount) elements.contradictionCount.textContent = "—";
      if (elements.supportWeight) elements.supportWeight.textContent = "—";
      if (elements.contradictionWeight) elements.contradictionWeight.textContent = "—";
      if (elements.explanationStatus) elements.explanationStatus.textContent = "Unavailable";
      if (elements.explanationContent) {
        elements.explanationContent.innerHTML =
          '<p class="muted">Assessment is unavailable because the external memory service could not be reached. The local history below remains available.</p>';
      }
      if (elements.memoryStatus) {
        elements.memoryStatus.textContent = "Local history available · assessment unavailable";
      }
      renderHistory(history);
      setStatus(error.message || "Historical-memory assessment is temporarily unavailable.");
    }
  } catch (error) {
    setStatus(error.message || "Vehicle history could not be retrieved.");
    if (elements.emptyState) elements.emptyState.hidden = true;
    if (elements.vehicleView) elements.vehicleView.hidden = true;
  } finally {
    if (elements.searchButton) elements.searchButton.disabled = false;
  }
}

// Event Listeners setup
if (elements.searchForm) {
  elements.searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const vehicleId = elements.vehicleInput ? elements.vehicleInput.value.trim() : "";
    if (vehicleId) await loadVehicle(vehicleId);
  });
}

if (elements.confidenceToggle && elements.confidenceDetails) {
  elements.confidenceToggle.addEventListener("click", () => {
    const expanded = elements.confidenceToggle.getAttribute("aria-expanded") === "true";
    elements.confidenceToggle.setAttribute("aria-expanded", String(!expanded));
    elements.confidenceDetails.hidden = expanded;
  });
}

if (elements.reportForm) {
  elements.reportForm.addEventListener("reset", () => {
    delete elements.reportForm.dataset.idempotencyKey;
  });

  elements.reportForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (elements.reportResult) elements.reportResult.textContent = "Saving…";
    if (elements.reportButton) elements.reportButton.disabled = true;

    const body = {
      vehicle_id: (elements.reportVehicleId && elements.reportVehicleId.value) || state.vehicleId,
      vin: (elements.reportVin && elements.reportVin.value.trim()) || null,
      source_id: (elements.reportSourceId && elements.reportSourceId.value.trim()) || "",
      source_type: (elements.reportSourceType && elements.reportSourceType.value) || "inspector",
      observed_at: (elements.reportObservedAt && elements.reportObservedAt.value) || "",
      text: (elements.reportText && elements.reportText.value.trim()) || ""
    };

    try {
      const idempotencyKey = getIdempotencyKey();
      const payload = await fetchJson("/api/reports", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "Idempotency-Key": idempotencyKey
        },
        body: JSON.stringify(body)
      });

      const reportId = payload.report?.report_id || "report";
      if (elements.reportResult) elements.reportResult.textContent = "Saved " + reportId + ". Refreshing assessment…";
      elements.reportForm.reset();
      if (elements.reportVehicleId) elements.reportVehicleId.value = state.vehicleId;
      await loadVehicle(state.vehicleId);
      if (elements.reportResult) elements.reportResult.textContent = "Saved " + reportId + ".";
    } catch (error) {
      const errorMsg = error.message || "The report could not be saved.";
      if (elements.reportResult) elements.reportResult.textContent = errorMsg;
      const vehicleId = state.vehicleId || body.vehicle_id;
      if (vehicleId) {
        try {
          await loadVehicle(vehicleId);
          if (elements.reportResult) elements.reportResult.textContent = errorMsg;
        } catch {
          // Ignore secondary vehicle load errors, keeping report error message visible
        }
      }
    } finally {
      if (elements.reportButton) elements.reportButton.disabled = false;
    }
  });
}

// Register Drawer Toggle & Submit
if (elements.toggleRegisterBtn && elements.registerDrawer) {
  elements.toggleRegisterBtn.addEventListener("click", () => {
    elements.registerDrawer.hidden = !elements.registerDrawer.hidden;
  });
}

if (elements.regCancelBtn && elements.registerDrawer) {
  elements.regCancelBtn.addEventListener("click", () => {
    elements.registerDrawer.hidden = true;
  });
}

if (elements.registerForm) {
  elements.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (elements.regStatus) elements.regStatus.textContent = "Saving vehicle record…";

    const carId = elements.regCarId ? elements.regCarId.value.trim() : "";
    const payload = {
      car_id: carId,
      brand: (elements.regBrand && elements.regBrand.value.trim()) || "",
      model: (elements.regModel && elements.regModel.value.trim()) || "",
      manufacture_year: elements.regYear ? parseInt(elements.regYear.value, 10) : 2022,
      variant: (elements.regVariant && elements.regVariant.value.trim()) || null,
      fuel_type: (elements.regFuel && elements.regFuel.value) || null,
      transmission: (elements.regTransmission && elements.regTransmission.value) || null,
      odometer_km: elements.regOdometer && elements.regOdometer.value ? parseInt(elements.regOdometer.value, 10) : null,
      asking_price_inr: elements.regPrice && elements.regPrice.value ? parseInt(elements.regPrice.value, 10) : null,
      previous_owners: elements.regOwners && elements.regOwners.value ? parseInt(elements.regOwners.value, 10) : 1,
      registration_state: (elements.regState && elements.regState.value.trim().toUpperCase()) || null,
      vin: (elements.regVin && elements.regVin.value.trim()) || null,
    };

    try {
      await fetchJson("/api/vehicles", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      if (elements.regStatus) elements.regStatus.textContent = "Vehicle registered successfully!";
      elements.registerForm.reset();
      if (elements.registerDrawer) elements.registerDrawer.hidden = true;
      if (elements.vehicleInput) elements.vehicleInput.value = carId;
      await loadVehicle(carId);
    } catch (error) {
      if (elements.regStatus) elements.regStatus.textContent = error.message || "Failed to register vehicle.";
    }
  });
}

// Demo chips
if (typeof document !== "undefined" && typeof document.querySelectorAll === "function") {
  document.querySelectorAll(".demo-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const scenario = btn.dataset?.scenario || btn.getAttribute("data-scenario");
      if (scenario) {
        if (elements.vehicleInput) elements.vehicleInput.value = scenario;
        loadVehicle(scenario);
      }
    });
  });
}

// Default date to today
if (elements.reportObservedAt && !elements.reportObservedAt.value) {
  elements.reportObservedAt.value = new Date().toISOString().slice(0, 10);
}

// Initial checks
checkBackend();
