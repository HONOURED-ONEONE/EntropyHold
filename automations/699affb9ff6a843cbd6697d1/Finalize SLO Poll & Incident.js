const axios = require("axios")

async function raiseTurboticIncident(title, details) {
  // Placeholder: Replace with Turbotic's native incident API if available
  console.warn("[INCIDENT]", title, JSON.stringify(details))
}

async function pollFinalizeSLO() {
  const baseUrl = process.env.HONEYPOT_BASE_URL
  const adminKey = process.env.HONEYPOT_ADMIN_KEY
  const p95FinalizeWarn = parseFloat(process.env.P95_FINALIZE_WARN)
  const now = Date.now()

  const maxAttempts = 2
  let lastErr = null
  let resp = null
  let snapshot = null

  for (let attempt = 1; attempt <= maxAttempts; ++attempt) {
    try {
      resp = await axios.get(`${baseUrl.replace(/\/$/, "")}/admin/slo`, {
        timeout: 5000,
        headers: { "x-admin-key": adminKey },
        validateStatus: () => true
      })
      try {
        snapshot = resp.data
      } catch (parseErr) {
        lastErr = parseErr
      }
      break // Success if got a response
    } catch (e) {
      lastErr = e
      if (attempt < maxAttempts) {
        await new Promise(res => setTimeout(res, Math.pow(2, attempt) * 100))
      }
    }
  }

  if (!resp || !snapshot || typeof snapshot !== "object") {
    console.log(JSON.stringify({ service: "honeypot", finalize_slo_poll: "fail", code: resp && resp.status, ts: now }))
    await raiseTurboticIncident("Finalize SLO Polling Error", { error: lastErr ? lastErr.message : "No response", ts: now })
    return
  }

  const finalizeSuccessRate = parseFloat(snapshot.finalize_success_rate_15m)
  const finalizeP95 = parseFloat(snapshot.finalize_p95_seconds_15m)
  let breached = false
  let breachFields = {}

  // SLO logic: Breach if p95 > warn or success rate < 1.0
  if (isFinite(finalizeP95) && p95FinalizeWarn && finalizeP95 > p95FinalizeWarn) {
    breached = true
    breachFields.finalize_p95_seconds = finalizeP95
  }
  if (isFinite(finalizeSuccessRate) && finalizeSuccessRate < 1.0) {
    breached = true
    breachFields.finalize_success_rate = finalizeSuccessRate
  }

  if (breached) {
    const details = {
      service: "honeypot",
      slo_breach: true,
      code: resp.status,
      ...breachFields,
      threshold_finalize_p95: p95FinalizeWarn,
      ts: now
    }
    console.log(JSON.stringify(details))
    await raiseTurboticIncident("Finalize SLO Breach", details)
  } else {
    const healthy = {
      service: "honeypot",
      slo_ok: true,
      code: resp.status,
      finalize_success_rate: finalizeSuccessRate,
      finalize_p95_seconds: finalizeP95,
      ts: now
    }
    console.log(JSON.stringify(healthy))
  }
}

;(async () => {
  try {
    await pollFinalizeSLO()
  } catch (e) {
    await raiseTurboticIncident("Finalize SLO Poll Script Error", { error: e.message || String(e), ts: Date.now() })
    process.exit(1)
  }
})()
