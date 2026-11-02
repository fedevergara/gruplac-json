# Publishing to PyPI

GitHub Actions publishes **gruplac-json** to [PyPI](https://pypi.org) every time a version tag (`v0.1.0`, `v0.2.0`…) is pushed. No password or token is stored anywhere: PyPI trusts the workflow `release.yml` of this repository through Trusted Publishing (OpenID Connect).

## First time, in this order

1. Create an **empty** GitHub repository `restrepo/gruplac-json` (no README or licence; they are here): `gh repo create restrepo/gruplac-json --public`.
2. Push **only the branch**, without any tag yet:

   ```bash
   git remote add origin git@github.com:restrepo/gruplac-json.git
   git push -u origin main
   ```

3. **PyPI** (signed in, with two-factor authentication): <https://pypi.org/manage/account/publishing/> → *Add a new pending publisher* → GitHub:

   | Field | Value |
   | --- | --- |
   | PyPI Project Name | `gruplac-json` |
   | Owner | `restrepo` |
   | Repository name | `gruplac-json` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

4. **GitHub:** Settings → Environments → New environment `pypi`. Recommended: *Required reviewers* = yourself (every upload then waits for your approval), and *Deployment branches and tags* limited to tags `v*`.
5. Optional dry run on TestPyPI: repeat 3 on <https://test.pypi.org/manage/account/publishing/> with workflow `testpypi.yml` and environment `testpypi`, create the `testpypi` environment on GitHub, then Actions → TestPyPI → Run workflow.
6. Only now push the first tag (next section). A tag pushed before steps 3–4 makes `publish-pypi` fail without publishing anything; re-run the job once the setup is done.

If Trusted Publishing is impossible, use an API token instead: create it on PyPI (scoped to the project after the first upload), store it as an **environment secret** `PYPI_API_TOKEN` of `pypi`, and uncomment the `password:` lines in `release.yml`. Never put it in a file of the repository.

## Releasing a version

The version comes from the git tag (`hatch-vcs`); it is written in no file.

1. Move the `[Unreleased]` notes of `CHANGELOG.md` under `## [X.Y.Z] - YYYY-MM-DD`, update the links at the bottom, commit `Release X.Y.Z` on `main` and push.
2. Check that **CI** is green on `main`.
3. Tag and push:

   ```bash
   git tag -a vX.Y.Z -m "gruplac-json X.Y.Z"
   git push origin vX.Y.Z
   ```

4. Actions → Release runs `build` (builds, `twine check --strict`, wheel version = tag), `publish-pypi` (waits for your approval: **Review deployments → tick `pypi` → Approve and deploy**) and `github-release` (release page with the wheel and sdist).
5. Check: `pip install --upgrade gruplac-json && gruplac-json --version`.

A version published on PyPI can never be replaced or reused: if something goes wrong, release the next patch (`vX.Y.Z+1`).

## Building locally

```bash
python -m pip install build twine
python -m build
python -m twine check --strict dist/*
python -m pip install dist/*.whl && gruplac-json --version
```
