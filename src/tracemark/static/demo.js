"use strict";

const demo = window.TRACEMARK_DEMO || {};
const ADMIN_TOKEN = demo.admin_token;
const SUBJECTS = demo.subjects || {};

async function postJson(url, body, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = "Bearer " + token;
  const resp = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error((data.detail && JSON.stringify(data.detail)) || resp.statusText);
  return data;
}

function fmtP(p) {
  if (p === undefined || p === null) return "—";
  if (p === 0) return "0";
  if (p >= 0.001) return p.toFixed(4);
  return p.toExponential(2);
}

document.getElementById("watermark-btn").addEventListener("click", async (e) => {
  const btn = e.target;
  btn.disabled = true;
  const status = document.getElementById("wm-status");
  try {
    const subjectId = document.getElementById("subject").value;
    const scope = document.getElementById("scope").value || null;
    const policy = document.getElementById("policy").value;
    const text = document.getElementById("original").value;
    const token = SUBJECTS[subjectId] && SUBJECTS[subjectId].token;

    const result = await postJson(
      "/v1/watermark",
      { text, policy, model_scope: scope },
      token
    );
    document.getElementById("watermarked").value = result.text;
    status.textContent = `${result.opportunities_found} opportunities, ${result.transformations_applied} applied`;
    const lines = (result.transformations || []).map(
      (t) => `${t.rule_id} bit=${t.bit}  "${t.original}" -> "${t.replacement}"`
    );
    document.getElementById("transformations").textContent = lines.length
      ? lines.join("\n")
      : "(no changes)";
  } catch (err) {
    status.textContent = "error: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("detect-btn").addEventListener("click", async (e) => {
  const btn = e.target;
  btn.disabled = true;
  const status = document.getElementById("det-status");
  const resultBox = document.getElementById("result");
  try {
    const text = document.getElementById("suspect").value;
    const policy = document.getElementById("policy").value;
    const result = await postJson(
      "/v1/detect",
      { text, tenant_id: demo.tenant_id, policy },
      ADMIN_TOKEN
    );
    renderResult(result);
    status.textContent = `usable opportunities: ${result.usable_opportunities}`;
  } catch (err) {
    status.textContent = "error: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

function renderResult(r) {
  const box = document.getElementById("result");
  box.classList.remove("hidden", "good", "bad");
  let html = "";
  if (r.detected && r.best_candidate) {
    box.classList.add("good");
    const bc = r.best_candidate;
    const who = bc.subject ? bc.subject.external_ref : bc.subject_tag;
    html += `<h3 class="big">Likely fingerprint: ${who}${bc.model_scope ? " / " + bc.model_scope : ""}</h3>`;
  } else {
    box.classList.add("bad");
    const reasons = {
      insufficient_evidence: "Not enough usable linguistic choices for reliable attribution.",
      not_significant: "No candidate passed the significance threshold.",
      insufficient_separation: "Best candidate did not separate clearly from the runner-up.",
    };
    html += `<h3 class="big">No confident attribution</h3>`;
    html += `<p>${reasons[r.reason] || r.reason}</p>`;
  }
  if (r.best_candidate) {
    const rows = [r.best_candidate, r.runner_up].filter(Boolean).map((c) => {
      const who = c.subject ? c.subject.external_ref : c.subject_tag.slice(0, 8);
      return `<tr>
        <td>${who}</td>
        <td>${c.matches}/${c.opportunities}</td>
        <td>${(c.match_rate * 100).toFixed(1)}%</td>
        <td>${fmtP(c.p_value)}</td>
        <td>${fmtP(c.adjusted_p_value)}</td>
        <td>${c.evidence_score.toFixed(1)}</td>
      </tr>`;
    });
    html += `<table>
      <tr><th>candidate</th><th>matches</th><th>match</th><th>p</th><th>adj p</th><th>evidence</th></tr>
      ${rows.join("")}
    </table>`;
  }
  html += `<p class="muted">${r.usable_opportunities} usable opportunities, ${r.candidates_tested} candidates tested.</p>`;
  box.innerHTML = html;
}
