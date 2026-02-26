try {
  const requiredVars = ["HONEYPOT_BASE_URL", "HONEYPOT_ADMIN_KEY", "P95_FINALIZE_WARN", "CB_SUCCESS_WARN", "CB_P95_WARN"]

  // Optionally check these if desired (delete if not needed)
  const optionalVars = ["REDIS_URL", "EVIDENCE_STORE_ENDPOINT", "PARTNER_ENDPOINT"]

  // Only require optionalVars if they are actually used elsewhere
  const missing = requiredVars.filter(name => {
    const val = process.env[name]
    return typeof val === "undefined" || val === null || String(val).trim() === ""
  })

  if (missing.length > 0) {
    console.error(
      JSON.stringify({
        env_verified: false,
        missing_variables: missing
      })
    )
    process.exit(1)
  }

  // List all variables that passed for success log (names only)
  const allChecked = [...requiredVars /*, ...optionalVars*/]
  console.log(
    JSON.stringify({
      env_verified: true,
      variables: allChecked
    })
  )
  // If using context in bigger workflow: setContext('env_verification', allChecked);
} catch (e) {
  console.error(e)
  process.exit(1)
}
