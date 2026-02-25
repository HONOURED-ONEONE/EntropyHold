try {
  // Required env vars
  const requiredVars = ["HONEYPOT_BASE_URL", "HONEYPOT_ADMIN_KEY", "P95_FINALIZE_WARN", "CB_SUCCESS_WARN", "CB_P95_WARN"]
  // Downstream analysis: Evidence Export/Forward step requires PARTNER_ENDPOINT if forwarding; EVIDENCE_STORE_ENDPOINT if archiving. Both are fatal if missing & operator action matches. REDIS_URL not used.
  let fatalOptionals = []
  let warnOptionals = []
  const operatorAction = process.env.OPERATOR_ACTION ? String(process.env.OPERATOR_ACTION).toLowerCase() : ""
  // Check if Evidence Export/Forward relevant vars MUST be present
  if (operatorAction === "forward") {
    fatalOptionals.push("PARTNER_ENDPOINT")
  } else if (operatorAction === "archive") {
    fatalOptionals.push("EVIDENCE_STORE_ENDPOINT")
  } else {
    // If present but not required, warn if absent but do not fatal
    warnOptionals.push("PARTNER_ENDPOINT", "EVIDENCE_STORE_ENDPOINT")
  }
  // Validate all required
  const missingRequired = requiredVars.filter(k => !(process.env[k] && String(process.env[k]).trim() !== ""))
  if (missingRequired.length > 0) {
    const err = `Fatal: Missing required env vars: ${missingRequired.join(", ")}`
    console.error(err)
    throw new Error(err)
  }
  // Validate conditionally fatal optionals
  const missingFatalOptionals = fatalOptionals.filter(k => !(process.env[k] && String(process.env[k]).trim() !== ""))
  if (missingFatalOptionals.length > 0) {
    const err = `Fatal: Operator action '${operatorAction}' requires env var(s): ${missingFatalOptionals.join(", ")}`
    console.error(err)
    throw new Error(err)
  }
  // Warn for missing optionals (never fatal)
  warnOptionals.forEach(k => {
    if (!(process.env[k] && String(process.env[k]).trim() !== "")) {
      console.warn(`[env]: Optional variable not found: ${k}`)
    }
  })
  // Emit a compact JSON summary with variable names only
  const logObj = {
    env_verified: true,
    vars: [...requiredVars, ...fatalOptionals, ...warnOptionals].filter((v, i, arr) => arr.indexOf(v) === i)
  }
  console.log(JSON.stringify(logObj))
} catch (e) {
  console.error(e)
  process.exit(1)
}
