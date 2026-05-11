# Phase 3 Design: RBAC and Azure AD SSO Integration
**Status:** Design complete — implementation pending IT ticket confirmation  
**Target:** Gate 2 (Week 7 of Project Delivery Plan)  
**Dependencies:** Azure AD IT ticket, Accenture internal tenant access  
**Effort estimate:** 3–4 weeks from IT ticket confirmation

---

## Problem

Cerna currently has no authentication layer. Any user with network access to the Streamlit URL can submit queries, view responses, and access admin endpoints (`?admin=1`, `?health=1`). For UAT and any production deployment, the Project Delivery Plan defines four roles with distinct permissions:

| Role | Access |
|------|--------|
| Clinician | Query execution; Clinical and FHIR modules only; no admin panel |
| Admin | Full query + admin panel (`?admin=1`); can view logs and cache stats |
| Read-only | Query execution; no admin panel; rate-limited to 10 queries/session |
| Superuser | All access including health check, trace log download, cache wipe |

Without enforcement, there is no way to gate UAT access, no audit trail tied to individual users, and no module-level permission boundary. Any demo to clinical stakeholders where patient data could flow through the system requires authentication as a precondition.

---

## Proposed Approach

### Authentication: Azure AD SSO via MSAL

Use the Microsoft Authentication Library (`msal`) with the Accenture Azure AD tenant. The Streamlit app redirects unauthenticated users to Azure AD login. After authentication, the identity token is validated at the application entry point.

Implementation point: `app.py`, before any query processing or admin gating. The check runs before `Orchestrator.prepare()` is called.

```python
# Pseudocode — actual implementation in Phase 3
token = get_token_from_session_or_redirect()
claims = validate_jwt(token, tenant_id=AZURE_TENANT_ID, app_id=CERNA_APP_ID)
role = map_group_to_role(claims["groups"])
if not role_allows(role, current_action):
    st.error("Access denied.")
    st.stop()
```

Token validation: standard JWT signature verification against Azure AD public keys (available from `https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys`). Expiry check included. No custom cryptography.

### Role Mapping: Azure AD Groups

Group-to-role mapping via Azure AD group membership claims. Groups are pre-configured in Azure AD by the IT owner. The app reads `claims["groups"]` from the decoded token and maps to an internal Cerna role constant.

| Azure AD Group | Cerna Role |
|----------------|------------|
| `cerna-clinicians` | Clinician |
| `cerna-admins` | Admin |
| `cerna-readonly` | Read-only |
| `cerna-superusers` | Superuser |

Default for any authenticated user not in a named group: Read-only. Default for unauthenticated: redirect to login.

Reason for groups over custom claims: groups require no directory extension attributes and can be managed by the IT owner without application code changes. The tradeoff is that group membership is a coarser signal — it cannot encode per-module permissions without a group per module, which is manageable at four roles but not at scale.

### Enforcement Layer: Orchestrator Entry Point

Role checks happen at two boundaries:

1. **UI boundary:** Module selector availability and admin panel visibility are gated by role in `app.py`. Clinician role sees Clinical/FHIR only; Read-only sees all modules but cannot clear cache or view logs.

2. **Orchestrator boundary:** `Orchestrator.prepare()` receives a `user_role` parameter. If the role does not permit the requested module, the call returns a `PreparedQuery` with `refusal="You do not have access to this module."` This prevents UI bypass via direct API calls.

Reason for enforcing at orchestrator (not just UI): a determined user who POSTs directly to the Streamlit backend or builds a client against the Python API would bypass a UI-only gate. The orchestrator gate is the durable boundary.

---

## Trade-offs Considered

**Azure AD groups vs. custom claims via directory extension attributes**

Groups are simpler to configure and manageable by the IT owner without code changes. Custom claims (via Azure AD optional claims or extension attributes) allow more granular per-module permissions but require directory schema extensions and IT coordination for every permission change. Given four fixed roles, groups are the correct choice. If the permission model expands to per-module access control, revisit custom claims.

**Session duration vs. MFA frequency**

Streamlit does not maintain persistent server-side sessions; tokens must be stored in browser session storage or a short-lived cache. Long session tokens (24h) reduce MFA friction for daily users but increase the window for token theft. Recommendation: 8-hour session tokens aligned with a clinical shift, with MFA required on first login per day. Clinical staff should not be required to MFA every query.

**UI enforcement vs. orchestrator enforcement**

UI-only enforcement is easier to implement and sufficient for low-risk internal demos. Orchestrator enforcement is required for any deployment where the application is accessible outside a trusted network. Phase 3 should implement orchestrator enforcement as the canonical gate; the UI check is additive, not the primary control.

**MSAL Python vs. Streamlit-native OAuth**

The `streamlit-msal` community package provides a simpler OAuth integration but is not officially maintained. Using `msal` directly gives full control over token lifecycle and is the Accenture-endorsed approach for Azure AD integrations. Small additional implementation effort (~1 day) for a more maintainable result.

---

## Effort Estimate

| Phase | Work | Duration |
|-------|------|----------|
| IT ticket: Azure AD app registration | IT owner creates app registration, configures redirect URIs, creates groups | 2+ weeks (confirmed lead time per Project Delivery Plan) |
| Token validation and session management | Implement JWT validation, session storage, redirect flow | 3 days |
| Orchestrator role parameter | Add `user_role` to `prepare()`, module permission gate | 1 day |
| UI role gating | Admin panel, module selector, query controls | 1 day |
| Testing (3 roles, token expiry, bypass attempts) | Integration test per role + edge cases | 2 days |
| **Total from IT confirmation** | | **~1 week of dev work** |

The IT ticket lead time (2+ weeks) is the binding constraint. Dev work can be done in parallel with the ticket processing once the app registration details are confirmed.

---

## Open Questions (Require Human Resolution)

1. **Has the IT ticket been filed?** The Project Delivery Plan references a 2+ week lead time. If the ticket was not filed by 2026-04-22, Gate 2 (Week 7) is at risk. Confirm with the IT owner.

2. **Which Accenture Azure AD tenant?** Accenture runs multiple tenants. The correct tenant for an Oracle Health POV project is likely the client-delivery tenant, not the internal tools tenant. Confirm before configuring the app registration.

3. **Who is the Azure AD admin on the Accenture side?** The IT owner who creates the app registration and manages group membership needs to be identified. This is not a developer task.

4. **Authentication scope for demo vs. UAT.** For the mid-review demo (internal, no patient data), no-auth is acceptable. For UAT with actual Cerner clinical staff, authentication is required as a baseline. Confirm the UAT scope before Gate 2.

---

*Design doc: Phase 3 RBAC / Azure AD SSO · Cerna · 2026-04-22*
