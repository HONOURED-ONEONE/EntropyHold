const axios = require("axios")

;(async () => {
  function getTimestamp() {
    return Date.now()
  }
  function truncate(str, maxLen = 350) {
    if (!str || typeof str !== "string") return ""
    return str.length > maxLen ? str.slice(0, maxLen) + "... [truncated]" : str
  }
  // Load required env/config
  const baseUrl = process.env.HONEYPOT_BASE_URL
  const adminKey = process.env.HONEYPOT_ADMIN_KEY
  const partnerEndpoint = process.env.PARTNER_ENDPOINT
  const sessionId = process.env.SESSION_ID
  const sinceMinutesRaw = process.env.SINCE_MINUTES
  if (!baseUrl || !adminKey) {
    console.error(JSON.stringify({ error: "Missing required Honeypot env vars", ts: getTimestamp() }))
    process.exit(1)
  }
  const baseApi = baseUrl.endsWith("/") ? baseUrl + "admin/session" : baseUrl + "/admin/session"
  const headers = { "x-admin-key": adminKey }

  // Retry logic parameters
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

  async function fetchSessionSummary(sid) {
    const summary = { session_id: sid, fetched_at: getTimestamp() }
    try {
      // Session details
      const sessionRes = await requestWithRetry({
        method: "GET",
        url: baseApi + "/" + encodeURIComponent(sid),
        headers,
        timeout: 5000
      })
      // Timeline details
      const timelineRes = await requestWithRetry({
        method: "GET",
        url: baseApi + "/" + encodeURIComponent(sid) + "/timeline",
        headers,
        timeout: 5000
      })
      // Compact the key session details
      const sessionObj = sessionRes.data || {}
      const timeline = Array.isArray(timelineRes.data) ? timelineRes.data : []
      summary.state = sessionObj.state || null
      summary.core_metrics = {
        create_time: sessionObj.create_time,
        end_time: sessionObj.end_time,
        callback_status: sessionObj.callback_status,
        metrics: sessionObj.metrics || {}
      }
      summary.timeline = timeline.map(ev => ({ ts: ev.ts, event: ev.event, meta: ev.meta }))
      summary.partner = sessionObj.partner || null
      summary.has_callback = !!sessionObj.callback_status
      return summary
    } catch (e) {
      const errObj = {
        error: "Failed to fetch session/timeline",
        session_id: sid,
        code: e && e.response ? e.response.status : "CONN_ERROR",
        body: truncate(e && e.response && e.response.data ? JSON.stringify(e.response.data) : e && e.message ? e.message : ""),
        ts: getTimestamp()
      }
      console.error(JSON.stringify(errObj))
      console.error(`[TURBOTIC_INCIDENT] Problem fetching session ${sid}`)
      return null
    }
  }

  async function batchRecentSessionIds(minutes) {
    // Placeholder: in real usage, would query a Turbotic store or search endpoint.
    // Here, just simulate with error
    console.error(JSON.stringify({ error: "BATCH MODE NOT IMPLEMENTED: Please connect to session store (Turbotic source) for SINCE_MINUTES support", since_minutes: minutes, ts: getTimestamp() }))
    return []
  }

  let processedSummaries = []
  if (sessionId) {
    // Single mode
    const summary = await fetchSessionSummary(sessionId)
    if (summary) processedSummaries.push(summary)
  } else if (sinceMinutesRaw) {
    // Batch mode: query recent session IDs (pseudo impl)
    const ids = await batchRecentSessionIds(sinceMinutesRaw)
    for (const id of ids) {
      const summary = await fetchSessionSummary(id)
      if (summary) processedSummaries.push(summary)
    }
  } else {
    console.error(JSON.stringify({ error: "Neither SESSION_ID nor SINCE_MINUTES provided", ts: getTimestamp() }))
    process.exit(1)
  }
  for (const summary of processedSummaries) {
    if (partnerEndpoint && /^https?:\/\//.test(partnerEndpoint)) {
      try {
        await requestWithRetry({
          method: "POST",
          url: partnerEndpoint,
          headers: { "Content-Type": "application/json" },
          data: summary,
          timeout: 4000
        })
        console.log(JSON.stringify({ delivered: true, to: "PARTNER_ENDPOINT", session_id: summary.session_id, ts: getTimestamp() }))
      } catch (e) {
        console.error(
          JSON.stringify({
            error: "Failed to POST summary to partner",
            session_id: summary.session_id,
            code: e && e.response ? e.response.status : "CONN_ERROR",
            ts: getTimestamp()
          })
        )
        console.error("[TURBOTIC_INCIDENT] Case summary POST to partner failed")
      }
    } else {
      // Fallback: log the summary
      console.log(JSON.stringify({ summary, delivered: false, reason: "No PARTNER_ENDPOINT (logged only)", ts: getTimestamp() }))
    }
  }
})()
