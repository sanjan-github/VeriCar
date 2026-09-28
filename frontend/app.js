const state = { vehicleId: "", assessment: null, explanation: null };
const $ = (selector) => document.querySelector(selector);

const elements = {
  searchForm: $("#search-form"), vehicleInput: $("#vehicle-id"), statusBanner: $("#status-banner"),
  emptyState: $("#empty-state"), vehicleView: $("#vehicle-view"), vehicleTitle: $("#vehicle-title"),
  memoryStatus: $("#memory-status"), findingState: $("#finding-state"), confidenceValue: $("#confidence-value"),
  confidenceCopy: $("#confidence-copy"), confidenceToggle: $("#confidence-toggle"), confidenceDetails: $("#confidence-details"),
  supportCount: $("#support-count"), contradictionCount: $("#contradiction-count"), supportWeight: $("#support-weight"),
  contradictionWeight: $("#contradiction-weight"), explanationStatus: $("#explanation-status"),
  explanationContent: $("#explanation-content"), evidenceCount: $("#evidence-count"), timeline: $("#timeline"),
  reportForm: $("#report-form"), reportVehicleId: $("#report-vehicle-id"), reportVin: $("#report-vin"),
  reportSourceId: $("#report-source-id"), reportSourceType: $("#report-source-type"),
  reportObservedAt: $("#report-observed-at"), reportText: $("#report-text"), reportResult: $("#report-result")
};

function setStatus(message, visible = true) {
  elements.statusBanner.textContent = message;
  elements.statusBanner.hidden = !visible;
}

function formatDate(value) {
  if (!value) return "Unknown date";
  const date = new Date(String(value) + "T00:00:00");
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(date);
}

function titleCase(value) {
  return String(value).replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function allEvidence(finding) {
  return [
    ...finding.supporting_evidence.map((item) => ({ ...item, polarity: "supporting" })),
    ...finding.contradicting_evidence.map((item) => ({ ...item, polarity: "contradicting" })),
    ...finding.unresolved_evidence.map((item) => ({ ...item, polarity: "unresolved" }))
  ].sort((a, b) => String(b.observed_at).localeCompare(String(a.observed_at)));
}

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function renderEvidence(finding) {
  const evidence = allEvidence(finding);
  elements.evidenceCount.textContent = evidence.length + " report" + (evidence.length === 1 ? "" : "s");
  if (!evidence.length) {
    elements.timeline.innerHTML = '<p class="muted">No evidence matched this finding.</p>';
    return;
  }
  elements.timeline.innerHTML = evidence.map((item) => {
    return '<article class="evidence-item">' +
      '<div class="evidence-meta"><time datetime="' + escapeHtml(item.observed_at) + '">' + formatDate(item.observed_at) +
      '</time><span>·</span><span>' + escapeHtml(titleCase(item.source_type)) + ' · ' + escapeHtml(item.source_id) +
      '</span><span class="evidence-polarity ' + escapeHtml(item.polarity) + '">' + escapeHtml(item.polarity) + '</span></div>' +
      '<p class="evidence-text">' + escapeHtml(item.text) + '</p>' +
      '<p class="evidence-weight">Effective source weight: ' + Number(item.effective_reliability).toFixed(2) + '</p></article>';
  }).join("");
}

function renderExplanation(explanation, status) {
  elements.explanationStatus.textContent = status === "available" ? "Generated from supplied evidence" : "Unavailable";
  if (!explanation) {
    elements.explanationContent.innerHTML = '<p class="muted">Automated explanation is unavailable. The deterministic evidence assessment remains the source of truth.</p>';
    return;
  }
  const caveats = explanation.caveats && explanation.caveats.length
    ? "<h4>Caveats</h4><ul>" + explanation.caveats.map((item) => "<li>" + escapeHtml(item) + "</li>").join("") + "</ul>" : "";
  elements.explanationContent.innerHTML =
    "<p><strong>" + escapeHtml(explanation.summary) + "</strong></p>" +
    "<h4>Rationale</h4><p>" + escapeHtml(explanation.rationale) + "</p>" + caveats;
}

function renderAssessment(payload) {
  state.assessment = payload;
  state.explanation = payload.explanation;
  const finding = payload.findings[0];
  const confidence = finding.evidence_confidence;
  elements.vehicleTitle.textContent = payload.vehicle_id;
  elements.memoryStatus.textContent = payload.memory_status === "available" ? "Historical memory available" : "No historical evidence";
  elements.findingState.textContent = String(finding.status).replaceAll("_", " ");
  elements.confidenceValue.textContent = confidence == null ? "—" : Math.round(confidence) + "%";
  const copy = {
    insufficient_evidence: "There is not enough evidence to characterize this finding.",
    limited_evidence: "Some evidence exists, but the accumulated record is limited.",
    moderate_evidence: "The available evidence supports a moderate-strength finding.",
    strong_evidence: "The available evidence provides strong support for this finding."
  };
  elements.confidenceCopy.textContent = copy[finding.status] || "Assessment available.";
  elements.supportCount.textContent = finding.supporting_sources;
  elements.contradictionCount.textContent = finding.contradicting_sources;
  elements.supportWeight.textContent = Number(finding.support_weight).toFixed(2);
  elements.contradictionWeight.textContent = Number(finding.contradiction_weight).toFixed(2);
  renderExplanation(payload.explanation, payload.explanation_status);
  renderEvidence(finding);
  elements.reportVehicleId.value = payload.vehicle_id;
  elements.vehicleView.hidden = false;
  elements.emptyState.hidden = true;
}

async function loadVehicle(vehicleId) {
  setStatus("Retrieving historical evidence…");
  elements.vehicleView.hidden = true;
  try {
    const response = await fetch("/api/vehicles/" + encodeURIComponent(vehicleId) + "/assessment/explanation?issue=transmission_shift_behavior", {
      headers: { Accept: "application/json" }
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = payload && payload.detail;
      throw new Error((detail && detail.error && detail.error.message) || (detail && detail.message) || "Vehicle history could not be retrieved.");
    }
    state.vehicleId = vehicleId;
    renderAssessment(payload);
    setStatus("", false);
  } catch (error) {
    setStatus(error.message || "Vehicle history could not be retrieved.");
    elements.emptyState.hidden = false;
    elements.vehicleView.hidden = true;
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
  const body = {
    vehicle_id: elements.reportVehicleId.value || state.vehicleId,
    vin: elements.reportVin.value.trim() || null,
    source_id: elements.reportSourceId.value.trim(),
    source_type: elements.reportSourceType.value,
    observed_at: elements.reportObservedAt.value,
    text: elements.reportText.value.trim()
  };
  try {
    const response = await fetch("/api/reports", {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error((payload.detail && payload.detail.message) || "The report could not be saved.");
    const reportId = payload.report.report_id;
    elements.reportResult.textContent = "Saved " + reportId + ". Refreshing assessment…";
    elements.reportForm.reset();
    elements.reportVehicleId.value = state.vehicleId;
    await loadVehicle(state.vehicleId);
    elements.reportResult.textContent = "Saved " + reportId + ".";
  } catch (error) {
    elements.reportResult.textContent = error.message || "The report could not be saved.";
  }
});