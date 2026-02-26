# Compliance Baseline Checklist

Last updated: 2026-02-26

This checklist captures minimum release-compliance expectations for
`discogs_player` as a public personal project.

## 1) Open-Source And Attribution

- [x] Include repository license file.
- [ ] Keep third-party dependency licenses reviewable for distributed builds.
- [ ] Ensure notices/attribution remain accurate when dependencies change.

## 2) Secrets And Personal Data Hygiene

- [ ] Verify no API tokens/secrets are committed in source or docs.
- [ ] Verify no personal collection exports are committed unintentionally.
- [ ] Keep `.gitignore` protections for `.env`, `*.db`, exports, and logs.

## 3) Third-Party API Terms

- [ ] Use provider APIs according to documented terms.
- [ ] Avoid unsupported scraping or prohibited automation.
- [ ] Re-check provider policy constraints before mobile/store submissions.

## 4) Distribution Readiness

- [ ] Publish release notes with install/setup expectations per OS.
- [ ] Attach checksums/signature metadata for release artifacts where possible.
- [ ] Document support boundaries and known limitations.

## 5) Privacy And User Communication

- [x] Provide project-level privacy policy.
- [x] Provide usage terms/disclaimer.
- [x] Provide trademark/non-affiliation notice.
- [ ] Keep docs updated if telemetry or hosted services are introduced.

## 6) App Store Preparation (Future Track)

- [ ] Define mobile privacy disclosures per store requirements.
- [ ] Define account-deletion/data-deletion messaging if cloud features are added.
- [ ] Validate monetization approach against platform policy before rollout.

## Notes

- This file is a project operations checklist, not legal advice.
- For implementation strategy context, see:
  - `docs/STRATEGIC_EXPANSION_NOTES_2026-02-26.md`
  - `PRODUCT_STATE.md`
