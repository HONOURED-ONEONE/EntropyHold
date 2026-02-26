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
  const cbSuccessWarn = parseFloat(process.env.CB_SUCCESS_WARN)
  const cbP95Warn = parseFloat(process.env.CB_P95_WARN)
  const sloUrl = baseUrl && baseUrl.endsWith("/") ? baseUrl + "admin/slo" : baseUrl + "/admin/slo"

  if (!baseUrl || !adminKey || isNaN(cbSuccessWarn) || isNaN(cbP95Warn)) {
    console.error(
      JSON.stringify({
        error: "Missing required environment variables for SLO Snapshot Poll",
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
      if (res.status === 200 && res.data && typeof res.data === "object" && "callback_delivery_success_rate_15m" in res.data && "callback_p95_seconds_15m" in res.data) {
        metrics = {
          callback_delivery_success_rate_15m: parseFloat(res.data.callback_delivery_success_rate_15m),
          callback_p95_seconds_15m: parseFloat(res.data.callback_p95_seconds_15m)
        }
        const isBreach = metrics.callback_delivery_success_rate_15m < cbSuccessWarn || metrics.callback_p95_seconds_15m > cbP95Warn
        if (isBreach) {
          const breachReport = {
            service: "honeypot",
            slo: "callback_delivery",
            breach: true,
            metrics,
            thresholds: {
              success_rate: cbSuccessWarn,
              p95: cbP95Warn
            },
            ts
          }
          console.error(JSON.stringify(breachReport))
          // Incident marker/title per conventions
          console.error(`[TURBOTIC_INCIDENT] Callback SLO Breach: Success rate or P95 violated - metrics: ${JSON.stringify(metrics)}`)
          process.exit(2)
        } else {
          const normalReport = {
            service: "honeypot",
            slo: "callback_delivery",
            breach: false,
            metrics,
            thresholds: {
              success_rate: cbSuccessWarn,
              p95: cbP95Warn
            },
            ts
          }
          console.log(JSON.stringify(normalReport))
          return
        }
      } else {
        // Malformed/bad data
        let failBody = res.data ? (typeof res.data === "object" ? JSON.stringify(res.data) : String(res.data)) : ""
        console.error(
          JSON.stringify({
            service: "honeypot",
            slo: "callback_delivery",
            error: "Malformed or missing SLO data",
            code: res.status,
            body: truncate(failBody),
            ts
          })
        )
        // Mark the incident for downstream/console capture
        console.error("[TURBOTIC_INCIDENT] SLO endpoint returned invalid/malformed data")
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
            slo: "callback_delivery",
            error: "Request/connection error",
            code: e && e.response ? e.response.status : "CONN_ERROR",
            body: truncate(body),
            ts
          })
        )
        console.error("[TURBOTIC_INCIDENT] Error polling Honeypot SLO endpoint")
        process.exit(2)
      }
    }
  }
})()
