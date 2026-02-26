const axios = require("axios")

;(async () => {
  function getTimestamp() {
    return Date.now()
  }
  // Utility: Truncate a string (for error/fail log bodies only)
  function truncate(str, maxLen = 350) {
    if (!str || typeof str !== "string") return ""
    return str.length > maxLen ? str.slice(0, maxLen) + "... [truncated]" : str
  }

  // Load env/config
  const baseUrl = process.env.HONEYPOT_BASE_URL
  const apiKey = process.env.API_KEY
  const healthUrl = baseUrl && baseUrl.endsWith("/") ? baseUrl + "health" : baseUrl + "/health"

  if (!baseUrl) {
    console.error(JSON.stringify({ error: "HONEYPOT_BASE_URL is not set", ts: getTimestamp() }))
    process.exit(1)
  }

  let attempt = 0
  let maxRetries = 2
  let lastError = null

  // Retry with exponential backoff: 1s, 2s
  while (attempt <= maxRetries) {
    try {
      const axiosOptions = {
        method: "GET",
        url: healthUrl,
        headers: apiKey ? { "x-api-key": apiKey } : {},
        timeout: 3000, // 3s per try
        validateStatus: () => true // handle errors manually
      }
      const res = await axios(axiosOptions)
      const ts = getTimestamp()
      if (res.status === 200 && res.data && res.data.status === "ok") {
        console.log(JSON.stringify({ service: "honeypot", health: "ok", ts }))
        return
      } else {
        // Unexpected status/data shape
        let failBody = res.data ? (typeof res.data === "object" ? JSON.stringify(res.data) : String(res.data)) : ""
        console.error(
          JSON.stringify({
            service: "honeypot",
            health: "fail",
            code: res.status,
            body: truncate(failBody),
            ts
          })
        )
        // Incident logic: For now, log a marker. If Turbotic exposes an incident API, call it here.
        console.error("[TURBOTIC_INCIDENT] Honeypot unhealthy – see logs")
        process.exit(2)
      }
    } catch (e) {
      lastError = e
      // Axios timeout/connection/etc.
      if (attempt < maxRetries) {
        const delay = Math.pow(2, attempt) * 1000 // 1s, 2s
        await new Promise(res => setTimeout(res, delay))
        attempt++
      } else {
        const ts = getTimestamp()
        let body = e && e.response && e.response.data ? JSON.stringify(e.response.data) : e && e.message ? e.message : ""
        console.error(
          JSON.stringify({
            service: "honeypot",
            health: "fail",
            code: e && e.response ? e.response.status : "CONN_ERROR",
            body: truncate(body),
            ts
          })
        )
        console.error("[TURBOTIC_INCIDENT] Honeypot probe error – see logs")
        process.exit(2)
      }
    }
  }
})()
