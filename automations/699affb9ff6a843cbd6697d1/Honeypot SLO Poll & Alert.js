const axios = require("axios")

async function raiseTurboticIncident(title, details) {
  // Placeholder: Replace with native incident function if available
  console.warn("[INCIDENT]", title, JSON.stringify(details))
}

async function pollHoneypotSLO() {
  const baseUrl = process.env.HONEYPOT_BASE_URL
  const adminKey = process.env.HONEYPOT_ADMIN_KEY
  const cbSuccessWarn = parseFloat(process.env.CB_SUCCESS_WARN)
  const cbP95Warn = parseFloat(process.env.CB_P95_WARN)
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
    console.log(JSON.stringify({ service: "honeypot", poll: "fail", code: resp && resp.status, ts: now }))
    await raiseTurboticIncident("Callback SLO Polling Error", { error: lastErr ? lastErr.message : "No response", ts: now })
    return
  }

  const successRate = parseFloat(snapshot.callback_delivery_success_rate_15m)
  const p95 = parseFloat(snapshot.callback_p95_seconds_15m)
  let breached = false
  let breachFields = {}
  if (isFinite(successRate) && cbSuccessWarn && successRate < cbSuccessWarn) {
    breached = true
    breachFields.success_rate = successRate
  }
  if (isFinite(p95) && cbP95Warn && p95 > cbP95Warn) {
    breached = true
    breachFields.p95_seconds = p95
  }
  if (breached) {
    const details = {
      service: "honeypot",
      slo_breach: true,
      code: resp.status,
      ...breachFields,
      threshold_success: cbSuccessWarn,
      threshold_p95: cbP95Warn,
      ts: now
    }
    console.log(JSON.stringify(details))
    await raiseTurboticIncident("Callback SLO Breach", details)
  } else {
    const healthy = {
      service: "honeypot",
      slo_ok: true,
      code: resp.status,
      success_rate,
      p95_seconds: p95,
      ts: now
    }
    console.log(JSON.stringify(healthy))
  }
}

;(async () => {
  try {
    await pollHoneypotSLO()
  } catch (e) {
    // Fail the step if anything unhandled
    await raiseTurboticIncident("SLO Poll Script Error", { error: e.message || String(e), ts: Date.now() })
    process.exit(1)
  }
})()
