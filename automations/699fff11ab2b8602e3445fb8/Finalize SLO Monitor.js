const axios = require("axios")

;(async () => {
  function getTimestamp() {
    return Date.now()
  }
  function truncate(str, maxLen = 350) {
    if (!str || typeof str !== "string") return ""
    return str.length > maxLen ? str.slice(0, maxLen) + "... [truncated]" : str
  }

  const baseUrl = process.env.HONEYPOT_BASE_URL
  const adminKey = process.env.HONEYPOT_ADMIN_KEY
  const p95FinalizeWarn = parseFloat(process.env.P95_FINALIZE_WARN)
  const sloUrl = baseUrl && baseUrl.endsWith("/") ? baseUrl + "admin/slo" : baseUrl + "/admin/slo"

  if (!baseUrl || !adminKey || isNaN(p95FinalizeWarn)) {
    console.error(
      JSON.stringify({
        error: "Missing required environment variables for Finalize SLO Monitor",
        ts: getTimestamp()
      })
    )
    process.exit(1)
  }

  const axiosOptions = {
    method: "GET",
    url: sloUrl,
    headers: { "x-admin-key": adminKey },
    timeout: 5000,
    validateStatus: () => true
  }

  let attempt = 0
  const maxRetries = 1
  let lastError = null

  while (attempt <= maxRetries) {
    try {
      const res = await axios(axiosOptions)
      const ts = getTimestamp()
      let metrics
      if (res.status === 200 && res.data && typeof res.data === "object" && "finalize_success_rate_15m" in res.data && "finalize_p95_seconds_15m" in res.data) {
        metrics = {
          finalize_success_rate_15m: parseFloat(res.data.finalize_success_rate_15m),
          finalize_p95_seconds_15m: parseFloat(res.data.finalize_p95_seconds_15m)
        }
        const isBreach = metrics.finalize_success_rate_15m < 99 || metrics.finalize_p95_seconds_15m > p95FinalizeWarn
        if (isBreach) {
          const breachReport = {
            service: "honeypot",
            slo: "finalize",
            breach: true,
            metrics,
            thresholds: {
              success_rate: 99,
              p95: p95FinalizeWarn
            },
            ts
          }
          console.error(JSON.stringify(breachReport))
          // Incident marker/title per conventions
          console.error(`[TURBOTIC_INCIDENT] Finalize SLO Breach: Success rate or P95 violated - metrics: ${JSON.stringify(metrics)}`)
          process.exit(2)
        } else {
          const normalReport = {
            service: "honeypot",
            slo: "finalize",
            breach: false,
            metrics,
            thresholds: {
              success_rate: 99,
              p95: p95FinalizeWarn
            },
            ts
          }
          console.log(JSON.stringify(normalReport))
          return
        }
      } else {
        // Malformed or missing SLO data
        let failBody = res.data ? (typeof res.data === "object" ? JSON.stringify(res.data) : String(res.data)) : ""
        console.error(
          JSON.stringify({
            service: "honeypot",
            slo: "finalize",
            error: "Malformed or missing SLO data",
            code: res.status,
            body: truncate(failBody),
            ts
          })
        )
        // Mark the incident for downstream/console capture
        console.error("[TURBOTIC_INCIDENT] SLO endpoint returned invalid/malformed data for finalize SLO")
        process.exit(2)
      }
    } catch (e) {
      lastError = e
      if (attempt < maxRetries) {
        await new Promise(res => setTimeout(res, 1000)) // 1s retry
        attempt++
      } else {
        const ts = getTimestamp()
        let body = e && e.response && e.response.data ? JSON.stringify(e.response.data) : e && e.message ? e.message : ""
        console.error(
          JSON.stringify({
            service: "honeypot",
            slo: "finalize",
            error: "Request/connection error",
            code: e && e.response ? e.response.status : "CONN_ERROR",
            body: truncate(body),
            ts
          })
        )
        console.error("[TURBOTIC_INCIDENT] Error polling Honeypot SLO endpoint for finalize SLO")
        process.exit(2)
      }
    }
  }
})()
