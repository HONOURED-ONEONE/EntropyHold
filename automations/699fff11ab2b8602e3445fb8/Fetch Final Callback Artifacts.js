const axios = require("axios")

;(async () => {
  function getTimestamp() {
    return Date.now()
  }
  function redactSecrets(obj) {
    // Redact known secrets (admin key, partner endpoints, evidence endpoints)
    if (!obj) return obj
    let str = JSON.stringify(obj)
    str = str.replace(process.env.HONEYPOT_ADMIN_KEY || "", "[REDACTED]")
    if (process.env.EVIDENCE_STORE_ENDPOINT) str = str.replace(process.env.EVIDENCE_STORE_ENDPOINT, "[REDACTED_ENDPOINT]")
    if (process.env.PARTNER_ENDPOINT) str = str.replace(process.env.PARTNER_ENDPOINT, "[REDACTED_ENDPOINT]")
    return str
  }
  function truncate(str, maxLen = 350) {
    if (!str || typeof str !== "string") return ""
    return str.length > maxLen ? str.slice(0, maxLen) + "... [truncated]" : str
  }

  // Load env vars
  const baseUrl = process.env.HONEYPOT_BASE_URL
  const adminKey = process.env.HONEYPOT_ADMIN_KEY
  const sessionId = process.env.SESSION_ID
  const evidenceEndpoint = process.env.EVIDENCE_STORE_ENDPOINT
  const partnerEndpoint = process.env.PARTNER_ENDPOINT
  const dryRun = String(process.env.DRY_RUN).toLowerCase() === "true"

  if (!baseUrl || !adminKey || !sessionId) {
    console.error(
      JSON.stringify({
        error: "Missing required Honeypot env vars (BASE_URL, ADMIN_KEY, SESSION_ID)",
        ts: getTimestamp()
      })
    )
    process.exit(1)
  }

  const apiUrl = baseUrl.endsWith("/") ? baseUrl + "admin/callbacks" : baseUrl + "/admin/callbacks"
  const headers = { "x-admin-key": adminKey }

  // Retry wrapper (aligned with previous step)
  const requestWithRetry = async (axiosOpts, retryMax = 2) => {
    let attempt = 0,
      lastErr
    while (attempt <= retryMax) {
      try {
        return await axios(axiosOpts)
      } catch (e) {
        lastErr = e
        if (attempt < retryMax) {
          await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 1000))
          attempt++
        } else {
          throw e
        }
      }
    }
  }

  // Fetch callback artifacts
  let payload
  let fetchStart = getTimestamp()
  try {
    const cbRes = await requestWithRetry({
      method: "GET",
      url: apiUrl + `?sessionId=${encodeURIComponent(sessionId)}`,
      headers,
      timeout: 6000
    })
    payload = cbRes.data || {}
    console.log(
      JSON.stringify({
        fetched_callback: true,
        session_id: sessionId,
        elapsed_ms: getTimestamp() - fetchStart,
        ts: getTimestamp()
      })
    )
  } catch (e) {
    const errObj = {
      error: "Failed to fetch callback artifacts",
      code: e && e.response ? e.response.status : "CONN_ERROR",
      body: truncate(e && e.response && e.response.data ? JSON.stringify(e.response.data) : e && e.message ? e.message : ""),
      ts: getTimestamp()
    }
    console.error(JSON.stringify(errObj))
    process.exit(1)
  }

  // Forwarding logic based on finalReport
  if (payload && payload.finalReport) {
    let dest
    if (evidenceEndpoint && /^https?:\/\//.test(evidenceEndpoint)) {
      dest = evidenceEndpoint
    } else if (partnerEndpoint && /^https?:\/\//.test(partnerEndpoint)) {
      dest = partnerEndpoint
    }
    if (!dest) {
      console.log(
        JSON.stringify({
          forwarded: false,
          reason: "No valid endpoint set.",
          session_id: sessionId,
          ts: getTimestamp()
        })
      )
      process.exit(0)
    }
    // Forward or only log in dry-run
    if (dryRun) {
      console.log(
        JSON.stringify({
          DRY_RUN: true,
          would_post_to: dest.replace(/\?.*$/, ""),
          payload_redacted: true,
          payload_keys: Object.keys(payload.finalReport || {}),
          session_id: sessionId,
          ts: getTimestamp()
        })
      )
      process.exit(0)
    }
    // Real POST
    let postStart = getTimestamp()
    try {
      await requestWithRetry({
        method: "POST",
        url: dest,
        headers: { "Content-Type": "application/json" },
        data: payload.finalReport,
        timeout: 5000
      })
      console.log(
        JSON.stringify({
          forwarded: true,
          to: dest.replace(/\?.*$/, ""),
          session_id: sessionId,
          elapsed_ms: getTimestamp() - postStart,
          ts: getTimestamp()
        })
      )
    } catch (e) {
      let errObj = {
        error: "Failed to forward finalReport",
        session_id: sessionId,
        code: e && e.response ? e.response.status : "CONN_ERROR",
        body: truncate(e && e.response && e.response.data ? JSON.stringify(e.response.data) : e && e.message ? e.message : ""),
        ts: getTimestamp()
      }
      console.error(JSON.stringify(errObj))
      process.exit(1)
    }
  } else {
    console.log(
      JSON.stringify({
        result: "No finalReport found in callback payload. Not forwarding.",
        session_id: sessionId,
        ts: getTimestamp()
      })
    )
  }

  process.exit(0)
})()
