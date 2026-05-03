# Research Sources – TFG DAST Steamworks

This document compiles the official sources that will be used as the theoretical and technical foundation of the project.

# READING ORDER

- OWASP API Top 10
- JWT
- OAuth2 + Bearer
- Steamworks docs
- WSTG (API sections)
- ASVS (checklist)
- HTTP semantics
- Cheat Sheets (specific support)
- INCIBE/CERT

---

# API SECURITY FOUNDATIONS

## OWASP API Security Top 10
Main document on critical API vulnerabilities.

https://owasp.org/API-Security/

---

## OWASP Web Security Testing Guide (WSTG)
Practical security testing guide.

https://owasp.org/www-project-web-security-testing-guide/

Focus on:

- API Testing
- Authentication Testing
- Authorization Testing
- Session Management
- Rate Limiting

---

## OWASP Application Security Verification Standard (ASVS) 4.0.3
Security verification standard.

https://owasp.org/www-project-application-security-verification-standard/

Official releases:
https://github.com/OWASP/ASVS/releases

---

## OWASP Cheat Sheet Series
Concrete technical best practices.

https://cheatsheetseries.owasp.org/

Especially:

- REST Security Cheat Sheet
- JSON Web Token Cheat Sheet
- Authentication Cheat Sheet
- Logging Cheat Sheet

---

# PROTOCOLS AND TOKENS

## HTTP Semantics (RFC 9110)

https://www.rfc-editor.org/rfc/rfc9110

---

## OAuth 2.0 (RFC 6749)

https://www.rfc-editor.org/rfc/rfc6749

More accessible guide:
https://oauth.net/2/

---

## Bearer Token Usage (RFC 6750)

https://www.rfc-editor.org/rfc/rfc6750

---

## JSON Web Token (JWT) – RFC 7519

https://www.rfc-editor.org/rfc/rfc7519

OWASP JWT Cheat Sheet:
https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html

---

## OpenAPI Specification 3.1.x

https://spec.openapis.org/oas/latest.html

Practical version:
https://swagger.io/specification/

---

# STEAMWORKS

## Official Steamworks Documentation

Home:
https://partner.steamgames.com/doc/home

Authentication:
https://partner.steamgames.com/doc/features/auth

Web API Overview:
https://partner.steamgames.com/doc/webapi_overview

Inventory Service:
https://partner.steamgames.com/doc/features/inventory

Microtransactions:
https://partner.steamgames.com/doc/features/microtransactions

---

# NATIONAL CONTEXT

## INCIBE

https://www.incibe.es/

Search under:

- Technical publications
- Security guides
- INCIBE-CERT

---

# Note

These sources will serve as the basis for:

- Mapping vulnerabilities
- Designing the DAST lab
- Justifying technical decisions in the TFG report
