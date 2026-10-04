# Security Policy

## Supported versions

IA Director Core is experimental software. Security fixes are applied to the current `main` branch. No older release line is currently maintained as a supported security branch.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities through public issues, pull requests, discussions, or other public channels.

Use GitHub's private vulnerability reporting for this repository when available:

1. Open the repository's **Security** tab.
2. Choose **Advisories**.
3. Select **Report a vulnerability**.
4. Include a concise description, affected component or version, reproduction conditions, security impact, and any evidence needed to validate the report.

If private vulnerability reporting is unavailable, do not publish exploit details in a public issue. Use the repository owner's private contact channel instead.

Please avoid including credentials, tokens, personal data, customer data, or unrelated sensitive information in a report.

## Scope and expectations

A report should describe a security property of IA Director Core itself. Vulnerabilities in third-party services, operating systems, user environments, or intentionally unsafe downstream integrations are outside the core project's scope unless IA Director Core creates or materially worsens the condition.

The project is experimental. A passing test suite or automated security gate does not constitute a security, privacy, compliance, or production certification.

## Coordinated disclosure

Please allow reasonable time to reproduce, assess, remediate, and validate a reported vulnerability before public disclosure. Confirmed issues may be documented through a GitHub Security Advisory or another appropriate public release note after remediation.

Do not perform testing that accesses data or systems you are not authorized to test.
