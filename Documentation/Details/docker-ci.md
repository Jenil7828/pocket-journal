Overview
--------
This document describes the GitHub Actions workflow used to build and push the project's Docker image to GitHub Container Registry (ghcr.io). The workflow is intentionally minimal and focused on producing reproducible, SHA-tagged images suitable for production pipelines.

Overview
--------
This document describes the GitHub Actions workflow used to build and push the project's Docker image to GitHub Container Registry (ghcr.io). The workflow is minimal, secure, and produces SHA-tagged immutable images suitable for production.

Branch triggers
---------------
- The workflow triggers only on push to:
  - `main`
  - `feature/mood_detection`

SHA-only tagging
----------------
- Images are tagged using the short commit SHA (git rev-parse --short HEAD). The tag format is:

  ghcr.io/<owner>/<repo>:<short-sha>

- The workflow does not use `latest` or other floating tags to ensure immutability and reproducibility.

Pre-flight secret validation
----------------------------
- The workflow includes a pre-flight step that validates required GitHub Secrets exist and fails early with a clear error message if any are missing. This prevents accidental builds without required credentials.

Secrets required (repository secrets)
------------------------------------
- SONG_ID
- SONG_SECRET
- TMDB_API_KEY
- GEMINI_API_KEY
- FIREBASE_WEB_API_KEY
- FIREBASE_CREDENTIALS_JSON (full Firebase service account JSON blob)

Secret handling (BuildKit secrets)
---------------------------------
- The workflow passes secrets to BuildKit as ephemeral secrets via the build action's `secrets` input. Secrets are not exposed as environment variables in the workflow and are not written to disk by CI steps.
- Inside the build, BuildKit mounts each secret at `/run/secrets/<id>` for the duration of the build step. The secret is available only in the ephemeral build environment.

Dockerfile secret usage pattern (safe, single-layer use)
------------------------------------------------------
- Use the following pattern to read the Firebase JSON during build and delete it in the same RUN layer to avoid persistence in image layers:

  RUN --mount=type=secret,id=firebase \
      mkdir -p /app/secrets && \
      cat /run/secrets/firebase > /app/secrets/firebase.json && \
      # perform one-shot operations that require the file && \
      rm -f /app/secrets/firebase.json

- Important: Keep the read/use/remove sequence in a single RUN instruction so the secret content is not persisted in any intermediate layer.

File locations
--------------
- Workflow: `.github/workflows/docker-build-push.yml`
- Dockerfile: project root (adjust workflow `file:` if located elsewhere)
- Secrets: configured in GitHub repository (or organization) Secrets

How the workflow works (high level)
----------------------------------
1. Checkout repository.
2. Compute short commit SHA and normalize repo name to lowercase for GHCR.
3. Validate required secrets exist (pre-flight).
4. Set up Docker Buildx.
5. Log in to GHCR using `GITHUB_TOKEN`.
6. Build and push the image with BuildKit ephemeral secrets and GHA cache enabled.

Troubleshooting
---------------
- Pre-flight fails with "Missing required secret": ensure the listed secrets are set in the repository settings.
- BuildKit secret not available inside Dockerfile:
  - Confirm the secret id in the Dockerfile (`--mount=type=secret,id=firebase`) matches the workflow mapping `firebase=${{ secrets.FIREBASE_CREDENTIALS_JSON }}`.
- Push denied or authentication errors:
  - Verify `GITHUB_TOKEN` has package write permission; organization policies may require a PAT with packages:write.
- Secrets appearing in image or logs:
  - Ensure the Dockerfile does not write secret content into final image layers or echo secret values. Use the single-RUN pattern above.

Notes on large Docker images and optimization
-------------------------------------------
- Large images increase build time and reduce cache effectiveness. Consider:
  - Multi-stage builds to keep the final runtime image small.
  - Separating heavy ML dependencies/models into a separate image or downloading models at runtime from a secure store.
  - Ordering Dockerfile layers so stable layers are at the top and frequently-changing code is lower to maximize cache hits.
  - Pinning dependency versions to improve cache stability.

Contact
-------
If you need changes (example: multi-arch builds, alternate cache strategy, or integration with a deployment pipeline), update the workflow and documentation accordingly.
- Job fails to authenticate to GHCR:
  - Ensure `GITHUB_TOKEN` is available (it is provided automatically by Actions). For organization-level packages, you may need to configure permissions or a personal access token.

- Image push fails with `denied`:
  - Confirm the repository owner has permission to push packages to ghcr.io.
  - Check package-level visibility and organization policies.

- Build is slow even with cache enabled:
  - Cache effectiveness depends on Dockerfile layering. Consider optimizing the Dockerfile to maximize cache hits for early layers.

- Secrets unexpectedly appear in image layers:
  - Inspect Dockerfile for use of `ARG` or `ENV` that interpolate secrets. Do not use secrets as build args. Use BuildKit secret mounts (`RUN --mount=type=secret`) if a secret must be available only during build and not stored in layers.

Contact
-------
For further assistance, review the workflow file in `.github/workflows/docker-build-push.yml` and verify the secrets configured in the repository settings.




