# GEN-231 · Cloud credential issuance (stage 3)

The cloud sign-in port now calls the canonical `YouGileClient.request()`
operation IDs instead of importing the upstream HTTP client. Logic modeled
on Indalo's AGPL-licensed `signin.py` / `yougile_auth.py` at
`ea88a0d5c5c055262cba9cf9741fd51828481ba5`, but
implemented independently against our canonical operation contracts.

Sequence:

1. Host authenticates login/password against `getCompanies` and presents the
   vendor-owned company choices in the imported Indalo HTML form.
2. When a user chooses a company, the server **rechecks** that the chosen ID
   belongs to the credentials before issuing a key.
3. `AuthKeyController_create` issues a per-user/per-company key.
4. `CompanyController_get` called *with that key* must return the
   selected company ID; `UserController_getMe` identifies the user.
5. The return value is a `Secret` object and must be persisted only after
   encryption. On verification/profile failure, the just-issued key is
   revoked via `AuthKeyController_delete`.

No passwords are persisted in this module and no user-supplied company
identifier becomes a grant without the vendor check. The HTTP form
handler still needs CSRF, rate limiting, temporary encrypted flow state,
OAuth provider/token storage and access-token revocation. This stage does
**not** open an HTTP listener and is not a working OAuth login.

The upstream Indalo workflow also deletes previous per-user keys on
successful re-login; that lifecycle will be connected to our durable
account store in the upcoming persistence stage.
