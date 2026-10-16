# GitHub community administration checklist

The repository contains community documents, issue/PR templates, CODEOWNERS, roadmap and GitHub Actions. **Administrative GitHub settings must be configured separately**: documentation does not enforce branch protection by itself.

## 1. Remain private until release review

Repository **Settings → General**: keep **Private** until the maintainer explicitly approves public release. Confirm license, final project name and security audit first.

## 2. Enable Discussions (optional)

**Settings → General → Features → Discussions**. Suggested categories: Ideas, Q&A, Announcements. Use Issues for actionable bugs and features, Discussions for open questions.

## 3. Protect main

**Settings → Rules → Rulesets → New branch ruleset** (or **Settings → Branches → Add branch protection rule** depending on interface and plan):

- Target `main`; activate enforcement when available.
- Require a Pull Request before merging; add reviewer approval once there are other reviewers.
- Block force pushes and deletion of `main`.
- Require conversation resolution.
- After the first successful Actions run, require Windows and Android checks by their reported job names.
- Avoid locking out the only maintainer.

On some GitHub plan/repository combinations rulesets for private repositories may not enforce. If unavailable, reduce direct write access and use PRs by convention.

## 4. Security

Enable private vulnerability reporting in the GitHub Security / Code security settings if available. Never request pairing keys, private videos or personal logs in Issues.

## 5. Confirm CI in Actions

After pushing, look at **Actions** and check **Windows tests** and **Android debug build**. Their status is not known until GitHub actually runs them. Do not declare them passing before the run completes.

## 6. Before public V1

Review [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md), [AI disclosure](../AI_DISCLOSURE.md), [LICENSE](../LICENSE), signed Android release packaging and product naming. Then deliberately switch from Private to Public.

_Le dépôt reste privé jusqu'à ta décision explicite._