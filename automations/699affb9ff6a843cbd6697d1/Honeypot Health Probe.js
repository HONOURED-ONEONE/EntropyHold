const axios = require("axios")

async function probeHoneypotHealth() {
  const baseUrl = process.env.HONEYPOT_BASE_URL
  const apiKey = process.env.API_KEY

  if (!baseUrl) {
    console.error("HONEYPOT_BASE_URL is required")
    process.exit(1)
  }

  const url = `${baseUrl.replace(/\/$/, "")}/health`
  const maxRetries = 2
  const timeout = 3000 // 3 seconds
  let attempt = 0

  async function tryProbe() {
    try {
      const headers = apiKey ? { "x-api-key": apiKey } : {}
      const res = await axios.get(url, {
        headers,
        timeout
      })
      if (res.status === 200 && res.data && res.data.status === "ok") {
        const logObj = { service: "honeypot", health: "ok", ts: Date.now() }
        console.log(JSON.stringify(logObj))
        return true
      } else {
        const respBody = typeof res.data === "string" ? res.data : JSON.stringify(res.data)
        const logObj = {
          service: "honeypot",
          health: "fail",
          code: res.status,
          body: respBody.slice(0, 200),
          ts: Date.now()
        }
        console.log(JSON.stringify(logObj))
        await raiseTurboticIncident("Honeypot health probe failed", logObj)
        return false
      }
    } catch (err) {
      const status = err.response ? err.response.status : null
      let bodyTrunc = ""
      if (err.response && err.response.data) {
        bodyTrunc = typeof err.response.data === "string" ? err.response.data : JSON.stringify(err.response.data)
        bodyTrunc = bodyTrunc.slice(0, 200)
      } else if (err.message) {
        bodyTrunc = err.message.slice(0, 200)
      }
      const logObj = {
        service: "honeypot",
        health: "fail",
        code: status,
        body: bodyTrunc,
        ts: Date.now()
      }
      console.log(JSON.stringify(logObj))
      await raiseTurboticIncident("Honeypot health probe failed", logObj)
      return false
    }
  }

  while (attempt <= maxRetries) {
    // Exponential backoff: 0ms, 1000ms, 2000ms for attempts (1st, 2nd, 3rd)
    if (attempt > 0) await new Promise(r => setTimeout(r, Math.pow(2, attempt - 1) * 1000))
    const ok = await tryProbe()
    if (ok) break
    attempt++
  }
}

async function raiseTurboticIncident(reason, context) {
  // Use Turbotic system incident logging if available
  if (typeof logTurboticIncident === "function") {
    await logTurboticIncident(reason, context)
    return
  }
  // Fallback: log to console as warning
  console.warn("[Turbotic incident]", reason, JSON.stringify(context))
}

probeHoneypotHealth()
