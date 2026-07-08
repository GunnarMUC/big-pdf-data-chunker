# Security Audit Master Report — All Public Repos

**Date:** 2026-07-08  
**Scope:** 19 public repos under `github.com/GunnarMUC`  
**Tools:** Gitleaks 8.30.1, Semgrep 1.168.0, Trivy 0.72.0, pip-audit 2.9.0, cargo audit (attempted)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Repos scanned | 19 |
| Secrets found (Gitleaks) | 24 (in 1 repo: `development_rules`) |
| SAST findings (Semgrep) | 96 total across 13 repos |
| SCA CVEs (Trivy) | 178 total across 4 repos |
| 🚨 Critical findings | 6 repos with ERROR-level issues |
| ✅ Clean repos | 4 (no findings at all) |

---

## 🚨 Critical Attention Required (Top 3)

### 1. `development_rules` — Exposed API Key in Git History

**Severity:** CRITICAL  
**Finding:** A live API key (`sk-0XciF7LtK12t9TogOD37Zlz9TFJYRXf4`) is hardcoded in `html/classes/Settings.php` and logged in `nohup.out`, both committed to public Git history (8 commits visible).

**Files:**
- `html/classes/Settings.php:156` — hardcoded `x-api-key` header
- `nohup.out` (multiple lines) — runtime log containing same key
- `config.php` — contains `$key = 'YourSecretKey123'` (placeholder, also caught)

**Required Action:**
1. 🚨 **Immediately revoke this key** on the service side (appears to be an API key for a service at `code.edhonour.com`)
2. Remove key from `Settings.php` — use `getenv('API_KEY')` instead
3. Add `nohup.out` to `.gitignore`
4. Rotate the key to a new one stored in environment variable

**ISO 27001:** A.9.2 (Access control) / **SOC 2:** CC6.1 (Logical access)

---

### 2. `nebenkosten-app-2026` — Multiple Flask Security Issues + 19 CVE Dependencies

**Severity:** HIGH (5 ERRORs + 15 WARNINGs)  
**Findings:**
- `Dockerfile:30` — Missing USER instruction (runs as root)
- `app.py:190,237,239,259` — NaN injection via user-controlled input
- `app.py:1132` — Flask `debug=True` + `host='0.0.0.0'` (production exposure)
- `app.py:302,1080-1096` — Raw HTML returned via format strings (XSS)
- `templates/login.html:10` — Missing CSRF token
- 19 known CVEs in Python dependencies

**Recommended Fixes:**
- Add `USER 1000` to Dockerfile after package installation
- Disable debug mode; bind to `127.0.0.1` if behind reverse proxy
- Use `render_template` with auto-escaping instead of raw HTML format
- Add `{% csrf_token %}` to all POST forms
- Run `pip install --upgrade` for all dependencies; Trivy shows 19 CVEs

**ISO 27001:** A.14.2 (Secure development) / **SOC 2:** CC7.1 (Vulnerability detection)

---

### 3. `ats-bewerbungstool` — Missing CSRF Protection on 4 Forms

**Severity:** HIGH  
**Finding:** 4 POST forms in Django templates lack CSRF tokens:
- `templates/generate_documents.html:161`
- `templates/manage_profiles.html:37`
- `templates/optimize_resume.html:16,53`

**Fix:** Add `{% csrf_token %}` inside each `<form method="POST">` tag.

**ISO 27001:** A.9.4 (System access control) / **SOC 2:** CC6.3 (Security roles)

---

## Full Finding Inventory (by Repo)

### ✅ Already Audited (2 repos — no new findings)

| Repo | Status |
|------|--------|
| `security-vulnerability-auto-check` | ✅ Prior audit complete, all CI green |
| `Dependency-Vulnerability-Checker` | ✅ Prior audit complete, all CI green |

---

### 🔴 High-Risk Repos

#### `development_rules` (PHP)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1 | 🚨 CRITICAL | Gitleaks | `Settings.php:156` | Hardcoded API key `sk-0XciF7LtK12t9TogOD37Zlz9TFJYRXf4` |
| 2 | 🚨 CRITICAL | Gitleaks | `nohup.out` | Log file contains API key (should be .gitignored) |
| 3 | 🚨 CRITICAL | Gitleaks | `config.php` | Placeholder key `YourSecretKey123` in code |
| 4 | ⚠️ ERROR | Semgrep | `create_activities.sql:30-34` | 5 bcrypt hashes in SQL seed data |
| 5 | ⚠️ WARNING | Semgrep | `Settings.php:157` | `openssl_decrypt` return value not checked for false |

#### `nebenkosten-app-2026` (Python/Flask)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1 | ⚠️ ERROR | Semgrep | `Dockerfile:30` | Missing USER (runs as root) |
| 2-5 | ⚠️ ERROR | Semgrep | `app.py:190-259` | 4x NaN injection |
| 6 | ⚠️ WARNING | Semgrep | `app.py:302,1080-1132` | Raw HTML format (XSS) + debug mode + 0.0.0.0 |
| 7 | ⚠️ WARNING | Semgrep | `templates/login.html:10` | Missing CSRF token |
| 8 | ⚠️ WARNING | Semgrep | `templates/properties/detail.html:108` | Missing CSRF token |
| 9-28 | ⚡ INFO | Trivy | `requirements*.txt` | 19 CVEs in dependencies |

#### `big-pdf-data-chunker` (Python/Docker)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1 | ⚠️ ERROR | Semgrep | `Dockerfile:27` | Missing USER (runs as root) |
| 2 | ⚠️ WARNING | Semgrep | `templates/index.html:7` | Missing integrity attribute on script tag |

#### `voice-agent-medspa-engdeu` (Python/FastAPI)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1 | ⚠️ ERROR | Semgrep | `security-audit-script.py:50` | Old copy of audit tool contains `shell=True` |
| 2 | ⚠️ WARNING | Semgrep | `booking/api.py:38` | CORS wildcard `allow_origins=["*"]` |
| 3 | ⚠️ WARNING | Semgrep | `dashboard/api.py:25` | CORS wildcard `allow_origins=["*"]` |

---

### 🟡 Medium-Risk Repos

#### `RAG-Indexer-Interface` (Python/Docker/Nginx)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1 | ⚠️ WARNING | Semgrep | `app.py:343` | Flask `host='0.0.0.0'` + `debug=True` |
| 2 | ⚠️ WARNING | Semgrep | `docker-compose.yml:35` | Missing `no-new-privileges` + writable filesystem |
| 3 | ⚠️ WARNING | Semgrep | `nginx.conf:51` | H2C smuggling risk |
| 4 | ⚠️ WARNING | Semgrep | `nginx.conf:94` | Security header redefinition |
| 5 | ⚠️ WARNING | Semgrep | `templates/index.html:7` | Missing integrity attribute |

#### `dogwalking-marketplace` (TypeScript/React Native)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1-34 | ⚠️ WARNING | Semgrep | `apps/mobile/*`, `apps/web/*` | 34x `window.postMessage("*")` — wildcard origin |
| 35-42 | ⚡ INFO | Semgrep | `apps/web/*` | 8x string concat in console.log |
| 43-177 | ⚡ INFO | Trivy | `package.json` | 135 CVEs in JS dependencies |

**Note:** The postMessage wildcards are mostly in dev tooling (HotReload, dev-error-overlay) — acceptable if these files are dev-only. Verify they're not included in production build.

#### `dogwalking-pro` (TypeScript)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1-10 | ⚡ INFO | Trivy | Dependency tree | 10 CVEs |

#### `weft-clinic-DE-complaintmgmt` (Rust)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1-14 | ⚡ INFO | Trivy | Rust dependencies | 14 CVEs in crate dependencies |

---

### 🟢 Low-Risk Repos

#### `zahnklinik-voice-agent` (Python)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1-2 | ⚠️ WARNING | Semgrep | `agent.py:163,169` | Dynamic `urllib` usage |

#### `deepseek-token-counter` (TypeScript)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1-2 | ⚠️ WARNING | Semgrep | `tokenizer.ts:12-13` | User input in `path.join` |

#### `retirement_calculator` (JS/HTML)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1-2 | ⚠️ WARNING | Semgrep | `index.html:7-8` | Missing integrity on CDN script tags |

#### `clinic-DE-maluDB` (Python/Nginx)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1 | ⚠️ WARNING | Semgrep | `maludb_reverse_proxy.conf:67` | H2C smuggling condition in Nginx |

#### `auto-mac-voice-recorder` (Swift)
| # | Severity | Tool | File | Finding |
|---|----------|------|------|---------|
| 1 | ⚠️ WARNING | Semgrep | `swift.yml:15` | Mutable GitHub Actions tag in dependency submodule |

---

### ✅ Clean Repos (0 findings across all tools)

| Repo | Stack | Notes |
|------|-------|-------|
| `5-agent-crew-lokal-llm` | Python, 9 KB | No findings from any tool |
| `weft-nebenkosten-B2B-rust` | Rust | No Git leaks, no Trivy CVEs, no Semgrep findings |
| `maludb-core-gm` | PL/pgSQL | No Git leaks, no Trivy CVEs |
| `security-vulnerability-auto-check` | Python | Previously fully audited and hardened |
| `Dependency-Vulnerability-Checker` | Python | Previously fully audited and hardened |

---

## Summary Statistics

| Repo | Gitleaks | Semgrep | Trivy CVEs | Risk Level |
|------|----------|---------|------------|------------|
| development_rules | 🚨 24 found | 6 (5 ERROR) | 0 | CRITICAL |
| nebenkosten-app-2026 | ✅ clean | 20 (5 ERROR) | 19 | HIGH |
| ats-bewerbungstool | ✅ clean | 7 | 0 | HIGH |
| big-pdf-data-chunker | ✅ clean | 2 (1 ERROR) | 0 | MEDIUM |
| voice-agent-medspa-engdeu | ✅ clean | 3 (1 ERROR) | 0 | MEDIUM |
| RAG-Indexer-Interface | ✅ clean | 8 | 0 | MEDIUM |
| dogwalking-marketplace | ✅ clean | 42 | 135 | MEDIUM |
| dogwalking-pro | ✅ clean | 0 | 10 | LOW |
| weft-clinic-DE-complaintmgmt | ✅ clean | 0 | 14 | LOW |
| zahnklinik-voice-agent | ✅ clean | 2 | 0 | LOW |
| deepseek-token-counter | ✅ clean | 2 | 0 | LOW |
| retirement_calculator | ✅ clean | 2 | 0 | LOW |
| clinic-DE-maluDB | ✅ clean | 1 | 0 | LOW |
| auto-mac-voice-recorder | ✅ clean | 1 | 0 | LOW |
| 5-agent-crew-lokal-llm | ✅ clean | 0 | 0 | CLEAN |
| weft-nebenkosten-B2B-rust | ✅ clean | 0 | 0 | CLEAN |
| maludb-core-gm | ✅ clean | 0 | 0 | CLEAN |

---

## Compliance Mapping

### ISO 27001 Annex A

| Control | Affected Repo(s) | Issue |
|---------|-----------------|-------|
| A.9.2 (Access control) | `development_rules` | Exposed API key — unauthorized access risk |
| A.9.4 (System access) | `ats-bewerbungstool` | Missing CSRF token — cross-site request forgery |
| A.14.2 (Secure dev) | `nebenkosten-app-2026`, `big-pdf-data-chunker` | Docker runs as root, debug mode in production |
| A.12.6 (Vuln mgmt) | `nebenkosten-app-2026`, `dogwalking-marketplace` | 19+135 known CVEs in dependencies |
| A.14.9 (Security testing) | All | Recommend adding CI security scans |

### SOC 2 Trust Services Criteria

| Criterion | Affected Repo(s) | Issue |
|-----------|-----------------|-------|
| CC6.1 (Logical access) | `development_rules` | API key exposure = broken access boundary |
| CC6.3 (Security roles) | `ats-bewerbungstool` | Missing CSRF = incomplete access enforcement |
| CC7.1 (Vuln detection) | Multiple | No automated CVE scanning in most repos |

---

## Remediation Priority (by urgency)

### 🚨 Same Day

1. **`development_rules`** — Revoke the exposed API key, remove from code, rotate

### ⚠️ This Week

2. **`ats-bewerbungstool`** — Add CSRF tokens to 4 Django forms
3. **`nebenkosten-app-2026`** — Disable debug mode + bind to localhost
4. **`big-pdf-data-chunker`** — Add USER to Dockerfile

### ⚡ This Month

5. **All repos** — Run `pip-audit` / `npm audit` and update vulnerable dependencies
6. **`nebenkosten-app-2026`** — Address NaN injection (input validation)
7. **`RAG-Indexer-Interface`** — Fix Docker compose security options
8. **`voice-agent-medspa-engdeu`** — Remove old security-audit-tool copy; restrict CORS

### 📋 Process Improvement

9. **All repos** — Add `.github/workflows/security-audit.yml` (Semgrep + Gitleaks + Trivy)
10. **All repos** — Add `SECURITY.md` + `CONTRIBUTING.md`
11. **All repos** — Add Dependabot with cooldown
12. **`development_rules`** — Add `.gitignore` entry for `nohup.out`, `*.log`

---

## Tools & Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Gitleaks | 8.30.1 | Git history + file system secrets scanning |
| Semgrep | 1.168.0 | SAST — static analysis, 329 rules per repo |
| Trivy | 0.72.0 | SCA — dependency CVE scanning |
| pip-audit | 2.9.0 | Python-specific CVE scanning |

---

*Generated 2026-07-08. All scan artifacts stored in `/tmp/audit-results-all/`.*
