# Security Notes

DataPilot v1.1 is designed as a public portfolio demo, not a confidential multi-tenant analytics service.

Implemented safeguards include bounded CSV size/rows/columns, strict dataset identifiers, escaped user-visible values in the browser, constrained analytics tools, no arbitrary SQL/Python execution, same-origin production UI, CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, a restrictive permissions policy, and `Cache-Control: no-store` for API responses.

The optional LLM receives dataset metadata and derived tool outputs instead of the complete raw CSV, but column names and aggregates can still leave the server. Do not enable it for sensitive data without a privacy review.

Before accepting confidential data or multiple real users, add authentication, authorization, durable per-user storage, retention/deletion controls, rate limiting, audit logging, secret management, monitoring, dependency scanning and a formal threat model.
