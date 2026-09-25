# Production Readiness Checklist

Work through this list in order. Do not deploy while any **Release blocker** item is unchecked.

## 1. Release blockers

- [ ] Fix DynamoDB permissions for the posts table.
  - Add `dynamodb:GetItem` to the posts-table IAM statement in `infrastructure/iam.tf`.
  - Keep the permission scoped to the posts table ARN.
  - After deploying to staging, manually verify a published post can be read through `GET /api/v1/posts/{uuid}` using the deployed Lambda execution role.
  - Acceptance: the deployed Lambda can read, update, delete, publish, and attach files to an existing post without `AccessDenied`.

- [ ] Decide and implement the attachment access model.
  - Private S3 and stable API download links redirecting to one-hour signed URLs are implemented; verify the deployed behavior in staging.
  - Confirm uploads work with the production role, stable links redirect and retrieve the uploaded object, and anonymous users cannot list the bucket or read objects directly.
  - Existing buckets retain ACL support for migration; the bucket ACL is private and all public access blocks are enabled. Review legacy object ACLs before switching to ACL-disabled ownership.

- [ ] Move the SSH password out of Terraform variables and Lambda environment variables.
  - Runtime lookup through `/${stage}/${app_name}/ssh/password` as an SSM SecureString is implemented; only the parameter name is passed to Lambda, and IAM access is scoped to its exact ARN.
  - Provision the SecureString outside Terraform, deploy, then rotate the SFTP password and update the parameter to invalidate the value that may remain in prior state snapshots.
  - Verify the post-deploy plan/state and Lambda environment contain no plaintext password.

- [ ] Add a production smoke test that uses the real Lambda execution role.
  - Cover health, create, UUID read, update, attachment upload/read, publish, and delete.
  - Do not replace JWT validation with a dependency override in this test.
  - Acceptance: the smoke test passes against a staging stack configured like production.

## 2. Authentication and request security

- [x] Remove JWT query-parameter authentication.
  - Accept tokens only through `Authorization: Bearer`.
  - Remove query-string token references from code, OpenAPI descriptions, README examples, and tests.
  - Acceptance: query tokens are rejected and header tokens continue to work.

- [x] Ensure credentials are never logged.
  - Remove the `credentials` object from invalid-token log messages in `app/jwt_bearer.py`.
  - Review API Gateway, application, and exception logs for headers, query strings, and request bodies containing secrets.
  - Add a test that captures logs and asserts the submitted token is absent.

- [x] Tighten JWT validation.
  - Require `exp`, `iat`, `aud`, `sub`, and `jti` during decoding. No trusted issuer is configured, and the existing token producer omits `iss`, so issuer validation needs an auth-service contract first.
  - Preserve the existing `403` auth response contract, which is declared by the OpenAPI responses and asserted by API tests.

- [ ] Replace wildcard CORS with the production frontend origins.
  - Configure origins per environment.
  - Allow only required methods and headers.
  - Verify credentialed and non-credentialed browser requests.

## 3. Availability and abuse controls

- [x] Make rate limiting atomic.
  - Replace the read/check/write sequence with a conditional DynamoDB update or an edge-managed rate limit.
  - Test simultaneous requests at and above the threshold.
  - Acceptance: concurrent requests cannot exceed the configured allowance.

- [x] Stop using the raw URL path as an unbounded DynamoDB key.
  - Map requests to a small set of route templates or rate-limit buckets.
  - Exclude `/health` from application rate limiting.
  - Add protection against random-path storage/cost amplification.

- [x] Move country filtering out of application middleware.
  - Recommended: implement it with AWS WAF or CloudFront geographic restrictions.
  - Remove the per-client call to `country.is` from the request path.
  - Document the privacy basis for processing client IP addresses.
  - Acceptance: `/health` and normal API requests do not depend on a third-party geolocation service.

- [x] Make the health endpoint dependency-free.
  - Ensure `/health` does not call DynamoDB, SSM, S3, SSH, or external HTTP services.
  - If dependency checks are required, expose a separate readiness endpoint.

## 4. API correctness

- [x] Make `publishedAt` genuinely optional on create.
  - Give `CreatePost.published_at` a default of `None`.
  - Add an API regression test that creates a draft without the field.
  - Acceptance: the documented draft request returns `201`, not `422`.

- [x] Allow authenticated attachment uploads to draft and scheduled posts.
  - Load the post with the internal UUID lookup rather than the public-only post reader.
  - Keep public attachment reads restricted by the post's publication state.
  - Add draft, scheduled, published, deleted, and missing-post tests.

- [x] Return `404` when a post has no attachments.
  - Handle `attachments is None` before iterating in `get_attachment_by_id`.
  - Add a regression test for this exact case.

- [x] Validate attachment input before uploading.
  - Decode with strict base64 validation and translate failures to a structured `422` response.
  - Reject empty files unless explicitly supported.
  - Bound the encoded request size before decoding to avoid unnecessary memory usage.
  - Sanitize or replace user-controlled object names and URL-encode generated URLs.
  - Persist the correct `Content-Type` and safe `Content-Disposition` metadata in S3.

- [x] Make attachment updates resilient.
  - Prevent concurrent attachment additions from overwriting each other.
  - Delete the uploaded S3 object if the DynamoDB update fails, or use an explicit recoverable workflow.
  - Add tests for database failure after upload and concurrent additions.

- [ ] Enforce title uniqueness atomically if uniqueness is a requirement.
  - Do not rely on a read from the eventually consistent `TitleIndex` followed by `PutItem`.
  - Use a transaction/uniqueness item or relax and document the constraint.
  - Add a concurrent-create test.

- [x] Validate real calendar dates in date-based routes.
  - Reject values such as `2026/02/31` as `400` rather than treating them as a missing post.

- [ ] Standardize all error responses.
  - Make the `429` body use the documented `{status, id, message}` envelope.
  - Ensure correlation IDs are present on middleware-generated `403` and `429` responses.
  - Avoid `logger.exception` when there is no active exception.

## 5. Deployment and infrastructure hardening

- [ ] Enable DynamoDB point-in-time recovery and deletion protection for production.
- [ ] Add explicit CloudWatch log groups with retention and encryption settings.
- [ ] Add alarms for Lambda errors/throttles/duration, API 5xx responses, and publish failures.
- [x] Scope `ssm:GetParameter` instead of granting `Resource = "*"`.
- [ ] Remove unused EC2/ENI permissions unless Lambda is actually configured for a VPC.
- [ ] Add API Gateway or WAF throttling as the first line of abuse protection.
- [ ] Pin the Terraform `random` provider and commit the provider lock file.
- [ ] Run `tofu fmt` and make `tofu fmt -check`, `tofu validate`, and `tflint` required CI gates.
- [ ] Produce and review a production `tofu plan` before applying it.

## 6. Build and dependency cleanup

- [ ] Move `boto3-stubs` and `httpx2-pytest` out of runtime dependencies and into the dev dependency group.
- [ ] Confirm whether Lambda's managed `boto3` is used; package it only when an application-pinned version is required.
- [ ] Make `aws-lambda-powertools` ownership explicit: package it in the project layer or pin and verify the external layer in every target region.
- [ ] Exclude `__pycache__`, `*.pyc`, tests, and development tooling from release artifacts.
- [ ] Add artifact assertions for maximum compressed/uncompressed size and required imports.
- [ ] Build without downloading an installer through `curl | sh`; use a pinned builder image/tool version.
- [ ] Test importing `app.api_handler` from the exact assembled Lambda artifact in CI.

## 7. Static analysis and test gaps

- [ ] Resolve all `ty check` diagnostics; do not blanket-ignore them.
- [ ] Add `make ty` to the required CI workflow.
- [ ] Add tests for IAM-sensitive behavior rather than relying only on Moto, which does not enforce the deployed role policy.
- [ ] Run integration authentication without overriding `get_jwt_bearer` for at least one success and failure flow.
- [ ] Add concurrency tests for rate limiting, title creation, and attachment mutation.
- [ ] Add failure-path tests for SSM, S3, DynamoDB conditional writes, and SSH timeouts.
- [ ] Add a dependency vulnerability scan and a secret scan to CI.

## 8. Final release gate

- [ ] Confirm production uses `DEBUG=false`.
- [ ] Confirm JWT and SSH secrets have been rotated and resolve from the intended secret store.
- [ ] Run `uv sync --locked` from a clean checkout.
- [ ] Run Ruff lint and formatting checks.
- [ ] Run `ty check` with zero diagnostics.
- [ ] Run Bandit and the dependency/secret scanners.
- [ ] Run the complete unit, integration, and end-to-end suites.
- [ ] Build the Lambda API and dependency layer from a clean checkout.
- [ ] Run `tofu fmt -check`, `tofu validate`, `tflint`, and review the production plan.
- [ ] Deploy to staging and execute the production-role smoke test.
- [ ] Verify logs contain no JWTs, passwords, or sensitive request data.
- [ ] Verify alarms, dashboards, rollback steps, and a database recovery procedure.
- [ ] Deploy production and repeat the read-only smoke checks.

## Review baseline

Initial review results:

- `pytest`: 163 passed, 95% coverage.
- Ruff lint and format checks: passed.
- Bandit high-severity/high-confidence scan: passed.
- Lambda build: passed.
- `ty check`: failed with 32 diagnostics.
- `tflint`: failed because the `random` provider is not version constrained.
- `tofu fmt -check`: failed on infrastructure files.
- `tofu validate`: not completed because providers were not initialized locally.
