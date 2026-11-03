---
name: check-tenant-isolation
description: Verify a new or changed resource is properly tenant-isolated (org A cannot read/write org B's data). Use for any new model, route, or service touching organization-scoped data.
---

Tenant isolation is the single most safety-critical property of this
multi-tenant app. Verify it the same way
`tests/security/test_tenant_isolation.py` does, for every new resource
type:

1. **Write (or extend) a test**, not just a manual check:
   ```python
   def test_user_cannot_read_another_organizations_<resource>(client):
       register_and_login(client, email="owner-a@example.com")
       org_a = create_org(client, name="Org A")
       # ... create the resource under org_a ...
       client.post("/api/v1/auth/logout")

       register_and_login(client, email="owner-b@example.com")
       org_b = create_org(client, name="Org B")

       # org B's user must get 403 reading/writing org A's resource
       resp = client.get(f"/api/v1/organizations/{org_a['id']}/<resource>/...")
       assert resp.status_code == 403

       # and org B's OWN data must still work — a blanket 403 everywhere
       # is a different (also real, but different) bug
       resp = client.get(f"/api/v1/organizations/{org_b['id']}/<resource>")
       assert resp.status_code == 200
   ```

2. **Check every query touching the new model filters by
   `organization_id`.** Grep the service file for the model's `.query` /
   `db.session.get(...)` calls — every one that isn't already scoped by a
   parent object that was itself org-checked needs an explicit
   `.filter_by(organization_id=organization_id)` or equivalent.

3. **Check the route calls `get_membership_or_403(organization_id)` before
   calling the service** — not after, not only on the write path but also
   on every read path.

4. **Check role-gated actions check the role server-side**, not just the
   org membership — e.g. approval decisions require
   `can_approve_external_actions()`, not just "any member of this org."

5. **Check error responses don't leak existence.** A 403 for "you're not a
   member of org A" and a 403 for "org A doesn't exist" should be
   identical — don't let a 404-vs-403 distinction reveal whether a
   resource ID is valid to someone with no access to it.

Run the new/extended test and paste its actual result. "I reviewed the
code and it looks scoped correctly" is not sufficient for this category —
this project's existing tests exist because reviewing-by-reading is not
how the cross-tenant bugs usually get caught.
