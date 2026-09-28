const state = { vehicleId: "", assessment: null, explanation: null };
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
  evidenceCount: $("#evidence-count"), timeline: $("#timeline"), reportForm: $("#report-form"),
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

function renderEvidence(finding) {
  const evidence = allEvidence(finding);
  elements.evidenceCount.textContent = evidence.length + " report" + (evidence.length === 1 ? "" : "s");

  if (!evidence.length) {
    elements.timeline.innerHTML = '<p class="muted">No reports matched this finding.</p>';
    return;
  }

  elements.timeline.innerHTML = evidence.map((item) =>
    '<article class="evidence-item">' +
      '<div class="evidence-meta"><time datetime="' + escapeHtml(item.observed_at) + '">' +
      formatDate(item.observed_at) + '</time><span>·</span><span>' +
      escapeHtml(titleCase(item.source_type)) + ' · ' + escapeHtml(item.source_id) +
      '</span><span class="evidence-polarity ' + escapeHtml(item.polarity) + '">' +
      escapeHtml(item.polarity) + '</span></div>' +
      '<p class="evidence-text">' + escapeHtml(item.text) + '</p>' +
      '<p class="evidence-weight">Effective source weight: ' +
      Number(item.effective_reliability ?? 0).toFixed(2) + '</p></article>'
  ).join("");
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
  elements.memoryStatus.textContent =
    payload.memory_status === "available" ? "Historical memory available" : "No matching history";

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

async function checkBackend() {\n  const status = $("#api-status");\n  if (!status) return;\n  try {\n    const payload = await fetchJson("/health", { headers: { Accept: "application/json" } });\n    status.textContent = "API: " + (payload.status === "ok" ? "online" : "unavailable");\n    status.classList.add("online");\n  } catch {\n    status.textContent = "API: offline";\n    status.classList.add("offline");\n  }\n}\n\nasync function loadVehicle(vehicleId) {
  setStatus("Retrieving historical evidence…");
  elements.vehicleView.hidden = true;
  elements.searchButton.disabled = true;

  try {
    const payload = await fetchJson(
      "/api/vehicles/" + encodeURIComponent(vehicleId) +
      "/assessment/explanation?issue=transmission_shift_behavior",
      { headers: { Accept: "application/json" } }
    );
    state.vehicleId = vehicleId;
    renderAssessment(payload);
    setStatus("", false);
  } catch (error) {
    setStatus(error.message || "Vehicle history could not be retrieved.");
    elements.emptyState.hidden = false;
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
    const payload = await fetchJson("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body)
    });

    const reportId = payload.report?.report_id || "report";
    elements.reportResult.textContent = "Saved " + reportId + ". Refreshing assessment…";
    elements.reportForm.reset();
    elements.reportVehicleId.value = state.vehicleId;
    await loadVehicle(state.vehicleId);
    elements.reportResult.textContent = "Saved " + reportId + ".";
  } catch (error) {
    elements.reportResult.textContent = error.message || "The report could not be saved.";
  } finally {
    elements.reportButton.disabled = false;
  }
});

if (elements.reportObservedAt && !elements.reportObservedAt.value) {
  elements.reportObservedAt.value = new Date().toISOString().slice(0, 10);
}
\ncheckBackend();\n