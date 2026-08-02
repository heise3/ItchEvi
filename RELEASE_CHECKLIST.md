# ItchEvi release checklist

## Required before public release

- [ ] Final software authors and maintainer approved.
- [ ] Public repository URL approved.
- [ ] MIT licensing confirmed by all rights holders.
- [ ] `CITATION.cff` updated with final authors and repository URL.
- [ ] Hosted Python 3.11/3.12 CI passes from a clean checkout.
- [ ] Docker image builds and all tests, demo, and normalize smoke test pass.
- [ ] Immutable Docker image digest recorded.
- [ ] Source distribution and wheel metadata validated.
- [ ] No participant-level data, secrets, local absolute paths, or large data
  objects are present.
- [ ] Version tag and release notes approved.
- [ ] Archival DOI plan approved and executed only after repository release.

No checklist item may be marked complete from a static file inspection alone.
