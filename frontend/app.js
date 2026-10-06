const state = { vehicleId: "", assessment: null, explanation: null, history: null };

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
const $ = (selector) => document.querySelector(selector);

const elements = {
  searchForm: $("#search-form"), vehicleInput: $("#vehicle-id"), searchButton: $("#search-form button"),
  statusBanner: $("#status-banner"), emptyState: $("#empty-state"), vehicleView: $("#vehicle-view"),
  vehicleTitle: $("#vehicle-title"), memoryStatus: $("#memory-status"), findingState: $("#finding-state"),
  confidenceValue: $("#confidence-value"), confidenceCopy: $("#confidence-copy"),
  confidenceToggle: $("#confidence-toggle"), confidenceDetails: $("#confidence-details"),
  supportCount: $("#support-count"), contradictionCount: $("#contradiction-count"),
  supportWeight: $("#support-weight"), contradictionWeight: $("#contradiction-weight"),
  explanationStatus: $("#explanation-status"), explanationContent: $("#explanation-content"),
  evidenceCount: $("#evidence-count"), timeline: $("#timeline"), reportForm: $("#report-form"), pdfButton: $("#pdf-button"),
  reportVehicleId: $("#report-vehicle-id"), reportVin: $("#report-vin"), reportSourceId: $("#report-source-id"),
  reportSourceType: $("#report-source-type"), reportObservedAt: $("#report-observed-at"),
  reportText: $("#report-text"), reportButton: $("#report-form button"), reportResult: $("#report-result")
};

function setStatus(message, visible = true) {
  elements.statusBanner.textContent = message;
  elements.statusBanner.hidden = !visible;
}

function formatDate(value) {
  if (!value) return "Unknown date";
  const date = new Date(String(value).length === 10 ? String(value) + "T00:00:00" : value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(date);
}

function titleCase(value) {
  return String(value).replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function allEvidence(finding) {
  return [
    ...(finding.supporting_evidence || []).map((item) => ({ ...item, polarity: "supporting" })),
    ...(finding.contradicting_evidence || []).map((item) => ({ ...item, polarity: "contradicting" })),
    ...(finding.unresolved_evidence || []).map((item) => ({ ...item, polarity: "unresolved" }))
  ].sort((a, b) => String(b.observed_at).localeCompare(String(a.observed_at)));
}

function renderEvidenceItems(items) {
  if (!items.length) {
    elements.timeline.innerHTML = '<p class="muted">No reports are available for this vehicle.</p>';
    return;
  }

  elements.timeline.innerHTML = items.map((item) =>
    '<article class="evidence-item">' +
      '<div class="evidence-meta"><time datetime="' + escapeHtml(item.observed_at) + '">' +
      formatDate(item.observed_at) + '</time><span>·</span><span>' +
      escapeHtml(titleCase(item.source_type)) + ' · ' + escapeHtml(item.source_id) +
      '</span><span class="evidence-polarity ' + escapeHtml(item.polarity || "unresolved") + '">' +
      escapeHtml(item.polarity || "unresolved") + '</span></div>' +
      '<p class="evidence-text">' + escapeHtml(item.text) + '</p>' +
      (item.effective_reliability == null ? "" :
        '<p class="evidence-weight">Effective source weight: ' +
        Number(item.effective_reliability).toFixed(2) + '</p>') +
      '</article>'
  ).join("");
}

function renderHistory(history) {
  const reports = Array.isArray(history?.reports) ? history.reports : [];
  elements.evidenceCount.textContent = reports.length + " report" + (reports.length === 1 ? "" : "s");
  renderEvidenceItems(reports);
}

function renderEvidence(finding) {
  const evidence = allEvidence(finding);
  elements.evidenceCount.textContent = evidence.length + " report" + (evidence.length === 1 ? "" : "s");

  if (!evidence.length) {
    renderHistory(state.history);
    return;
  }

  renderEvidenceItems(evidence);
}

function renderExplanation(explanation, status) {
  elements.explanationStatus.textContent =
    status === "available" ? "Generated from supplied evidence" : "Unavailable";

  if (!explanation) {
    elements.explanationContent.innerHTML =
      '<p class="muted">Automated explanation is unavailable. The deterministic evidence assessment remains the source of truth.</p>';
    return;
  }

  const caveats = explanation.caveats?.length
    ? "<h4>Caveats</h4><ul>" +
      explanation.caveats.map((item) => "<li>" + escapeHtml(item) + "</li>").join("") +
      "</ul>"
    : "";

  elements.explanationContent.innerHTML =
    "<p><strong>" + escapeHtml(explanation.summary) + "</strong></p>" +
    "<h4>Rationale</h4><p>" + escapeHtml(explanation.rationale) + "</p>" + caveats;
}

function renderAssessment(payload) {
  const finding = Array.isArray(payload.findings) ? payload.findings[0] : null;

  state.assessment = payload;
  state.explanation = payload.explanation || null;
  elements.vehicleTitle.textContent = payload.vehicle_id || state.vehicleId;
  const memoryStatusCopy = {
    available: "Historical memory available",
    empty: "No matching assessment evidence",
    unavailable: "Historical memory temporarily unavailable"
  };
  elements.memoryStatus.textContent =
    memoryStatusCopy[payload.memory_status] || "Historical memory status unavailable";

  elements.vehicleView.hidden = false;
  elements.emptyState.hidden = true;
  elements.reportVehicleId.value = payload.vehicle_id || state.vehicleId;

  if (!finding) {
    elements.findingState.textContent = "No finding";
    elements.confidenceValue.textContent = "—";
    elements.confidenceCopy.textContent = "No evidence was returned for this vehicle and finding.";
    elements.supportCount.textContent = "0";
    elements.contradictionCount.textContent = "0";
    elements.supportWeight.textContent = "0.00";
    elements.contradictionWeight.textContent = "0.00";
    elements.explanationStatus.textContent = "Unavailable";
    elements.explanationContent.innerHTML =
      '<p class="muted">There is no finding to explain yet.</p>';
    elements.evidenceCount.textContent = "0 reports";
    elements.timeline.innerHTML =
      '<p class="muted">Add a report to begin building the vehicle history.</p>';
    return;
  }

  const confidence = finding.evidence_confidence;
  const copy = {
    insufficient_evidence: "There is not enough evidence to characterize this finding.",
    limited_evidence: "Some evidence exists, but the accumulated record is limited.",
    moderate_evidence: "The available evidence supports a moderate-strength finding.",
    strong_evidence: "The available evidence provides strong support for this finding."
  };

  elements.findingState.textContent = String(finding.status || "unknown").replaceAll("_", " ");
  elements.confidenceValue.textContent = confidence == null ? "—" : Math.round(confidence) + "%";
  elements.confidenceCopy.textContent = copy[finding.status] || "Assessment available.";
  elements.supportCount.textContent = finding.supporting_sources ?? 0;
  elements.contradictionCount.textContent = finding.contradicting_sources ?? 0;
  elements.supportWeight.textContent = Number(finding.support_weight ?? 0).toFixed(2);
  elements.contradictionWeight.textContent = Number(finding.contradiction_weight ?? 0).toFixed(2);

  elements.confidenceDetails.hidden = true;
  elements.confidenceToggle.setAttribute("aria-expanded", "false");
  renderExplanation(payload.explanation, payload.explanation_status);
  renderEvidence(finding);
}

async function fetchJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(
      window.location.protocol === "file:"
        ? "The UI was opened as a file. Start the VeriCar FastAPI server and open http://127.0.0.1:8000/."
        : "The backend could not be reached. Make sure the VeriCar API is running."
    );
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : {};

  if (!response.ok) {
    const detail = payload.detail;
    const message = typeof detail === "string"
      ? detail
      : detail?.error?.message || detail?.message || "The request could not be completed.";
    throw new Error(message);
  }

  return payload;
}

async function checkBackend() {
  const status = $("#api-status");
  if (!status) return;
  try {
    const payload = await fetchJson("/health", { headers: { Accept: "application/json" } });
    status.textContent = "API: " + (payload.status === "ok" ? "online" : "unavailable");
    status.classList.add("online");
  } catch {
    status.textContent = "API: offline";
    status.classList.add("offline");
  }
}

async function loadVehicle(vehicleId) {
  setStatus("Retrieving durable vehicle history…");
  elements.emptyState.hidden = true;
  elements.vehicleView.hidden = true;
  elements.searchButton.disabled = true;

  try {
    const history = await fetchJson(
      "/api/vehicles/" + encodeURIComponent(vehicleId),
      { headers: { Accept: "application/json" } }
    );
    state.vehicleId = vehicleId;
    state.history = history;
    elements.vehicleTitle.textContent = vehicleId;
    elements.reportVehicleId.value = vehicleId;
    elements.vehicleView.hidden = false;
    elements.pdfButton.href = "/api/vehicles/" + encodeURIComponent(vehicleId) + "/assessment/report.pdf";
    elements.pdfButton.hidden = false;
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
      elements.findingState.textContent = "Assessment unavailable";
      elements.confidenceValue.textContent = "—";
      elements.confidenceCopy.textContent =
        "The durable vehicle history is available, but historical-memory assessment is temporarily unavailable.";
      elements.supportCount.textContent = "—";
      elements.contradictionCount.textContent = "—";
      elements.supportWeight.textContent = "—";
      elements.contradictionWeight.textContent = "—";
      elements.explanationStatus.textContent = "Unavailable";
      elements.explanationContent.innerHTML =
        '<p class="muted">Assessment is unavailable because the external memory service could not be reached. The local history below remains available.</p>';
      elements.memoryStatus.textContent = "Local history available · assessment unavailable";
      renderHistory(history);
      setStatus(error.message || "Historical-memory assessment is temporarily unavailable.");
    }
  } catch (error) {
    setStatus(error.message || "Vehicle history could not be retrieved.");
    elements.emptyState.hidden = true;
    elements.vehicleView.hidden = true;
  } finally {
    elements.searchButton.disabled = false;
  }
}

elements.searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const vehicleId = elements.vehicleInput.value.trim();
  if (vehicleId) await loadVehicle(vehicleId);
});

elements.confidenceToggle.addEventListener("click", () => {
  const expanded = elements.confidenceToggle.getAttribute("aria-expanded") === "true";
  elements.confidenceToggle.setAttribute("aria-expanded", String(!expanded));
  elements.confidenceDetails.hidden = expanded;
});

elements.reportForm.addEventListener("reset", () => {
  delete elements.reportForm.dataset.idempotencyKey;
});

elements.reportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  elements.reportResult.textContent = "Saving…";
  elements.reportButton.disabled = true;

  const body = {
    vehicle_id: elements.reportVehicleId.value || state.vehicleId,
    vin: elements.reportVin.value.trim() || null,
    source_id: elements.reportSourceId.value.trim(),
    source_type: elements.reportSourceType.value,
    observed_at: elements.reportObservedAt.value,
    text: elements.reportText.value.trim()
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
    elements.reportResult.textContent = "Saved " + reportId + ". Refreshing assessment…";
    elements.reportForm.reset();
    elements.reportVehicleId.value = state.vehicleId;
    await loadVehicle(state.vehicleId);
    elements.reportResult.textContent = "Saved " + reportId + ".";
  } catch (error) {
    const errorMsg = error.message || "The report could not be saved.";
    elements.reportResult.textContent = errorMsg;
    const vehicleId = state.vehicleId || body.vehicle_id;
    if (vehicleId) {
      try {
        await loadVehicle(vehicleId);
        elements.reportResult.textContent = errorMsg;
      } catch {
        // Ignore secondary vehicle load errors, keeping report error message visible
      }
    }
  } finally {
    elements.reportButton.disabled = false;
  }
});

if (elements.reportObservedAt && !elements.reportObservedAt.value) {
  elements.reportObservedAt.value = new Date().toISOString().slice(0, 10);
}

checkBackend();
