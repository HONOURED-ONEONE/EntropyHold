const axios = require("axios")
const crypto = require("crypto")

;(async () => {
  try {
    const baseUrl = process.env.HONEYPOT_BASE_URL
    const adminKey = process.env.HONEYPOT_ADMIN_KEY
    const sessionId = process.env.SESSION_ID
    const sinceMinutes = process.env.SINCE_MINUTES
    const partnerEndpoint = process.env.PARTNER_ENDPOINT
    if (!baseUrl || !adminKey) {
      console.error(JSON.stringify({ error: "Missing required Honeypot env vars." }))
      process.exit(1)
    }
    const headers = { "x-admin-key": adminKey }
    const fetchWithRetry = async (url, config = {}, maxRetries = 1) => {
      let attempt = 0
      let delay = 2500
      while (true) {
        try {
          return await axios.get(url, { ...config, timeout: 15000 })
        } catch (e) {
          attempt++
          if (attempt > maxRetries) throw e
          await new Promise(res => setTimeout(res, delay))
          delay *= 2
        }
      }
    }
    const postWithTimeout = async (url, payload) => {
      try {
        return await axios.post(url, payload, { headers: { "Content-Type": "application/json" }, timeout: 15000 })
      } catch (e) {
        throw new Error("POST to partner endpoint failed: " + e.message)
      }
    }
    const maskSecrets = data => {
      if (!data) return data
      const redact = val => (typeof val === "string" ? "**redacted**" : val)
      if (Array.isArray(data)) return data.map(maskSecrets)
      if (typeof data === "object") {
        const out = {}
        for (const k in data) {
          if (["HONEYPOT_ADMIN_KEY", "PARTNER_ENDPOINT", "SESSION_ID"].includes(k)) {
            out[k] = redact(data[k])
          } else {
            out[k] = maskSecrets(data[k])
          }
        }
        return out
      }
      return data
    }
    // Manual mode
    if (sessionId) {
      let sessionData, timelineData
      try {
        const resp1 = await fetchWithRetry(`${baseUrl}/admin/session/${sessionId}`, { headers }, 1)
        sessionData = resp1.data
        const resp2 = await fetchWithRetry(`${baseUrl}/admin/session/${sessionId}/timeline`, { headers }, 1)
        timelineData = resp2.data
      } catch (e) {
        console.error(JSON.stringify({ error: "Failed to fetch session data", message: e.message, ts: Date.now() }))
        process.exit(1)
      }
      // Assemble summary
      const summary = {
        session_id: sessionId,
        state: sessionData?.state,
        cq_metrics: sessionData?.cq_metrics || {},
        callback_status: sessionData?.callback_status,
        timeline: timelineData || [],
        created_at: sessionData?.created_at,
        fingerprint: crypto.createHash("sha256").update(JSON.stringify(sessionData)).digest("hex"),
        ts: Date.now()
      }
      // Forward or log
      if (partnerEndpoint) {
        try {
          await postWithTimeout(partnerEndpoint, summary)
          console.log(JSON.stringify({ forwarded: true, partner_url: "**redacted**", session_id: sessionId, ts: Date.now() }))
        } catch (e) {
          console.error(JSON.stringify({ error: "partner post failed", message: e.message, session_id: sessionId, ts: Date.now() }))
        }
      } else {
        console.log(JSON.stringify(maskSecrets(summary)))
      }
      return
    }
    // Batch mode (query by since_minutes): NOT IMPLEMENTED
    if (sinceMinutes) {
      console.log(JSON.stringify({ note: "Batch mode not implemented; need session list source.", since_minutes: sinceMinutes, ts: Date.now() }))
      // Optionally, raise a request for user clarification or future source.
      return
    }
    // If neither SESSION_ID nor SINCE_MINUTES provided
    console.log(JSON.stringify({ note: "No SESSION_ID or SINCE_MINUTES provided. Nothing to assemble.", ts: Date.now() }))
  } catch (e) {
    console.error(JSON.stringify({ error: e.message, ts: Date.now() }))
    process.exit(1)
  }
})()
