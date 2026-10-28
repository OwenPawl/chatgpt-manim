# Data handling

A deployment stores submitted scene specifications, titles, descriptions, editing
instructions, job metadata and rendered MP4s on its operator-controlled filesystem.
It derives an owner identifier from the authenticated identity and isolates reads
and cache lookups by that identifier. It does not send scenes to another LLM or
allow worker network access. No analytics or third-party scripts run in the player.

Defaults retain jobs for seven days, with cleanup triggered by a new submission.
Operators must add scheduled cleanup if deletion at a precise time is required,
and must separately define backup retention. Signed video URLs expire after fifteen
minutes but any recipient can access that specific video until expiry. Downloaded
copies are outside service control. Ask your service operator to delete retained
records or rotate credentials. Do not send sensitive personal data to an untrusted
deployment.

This technical data-handling description is not a production operator's legal
privacy policy. Public directory submission requires the actual operator's policy,
contact details, terms and retention commitments.
