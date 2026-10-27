# Security

The component performs read-only operations using the Streamlit process's OS permissions. Configured roots, their ancestors, and application configuration must be trusted. This package is not an authentication layer or a substitute for OS isolation. See the README access model before deploying a shared app.

## Reporting a vulnerability

If the repository's **Security → Report a vulnerability** option is enabled, use it for a private report. If that option is unavailable, open an issue asking the maintainer for a private reporting channel without including exploit details, credentials, personal data or private file contents. Do not post sensitive details in a public issue.

Include the package/Streamlit/Python versions, affected platform, a synthetic reproduction and the impact. There is no promised response-time SLA during the initial 0.x development phase.
