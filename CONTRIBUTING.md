# Contributing

Thanks for helping people organize card notes with AI and reuse their collection across agents. Start with the [README](README.md), [installation guide](docs/INSTALL.md) and [roadmap](ROADMAP.md).

## Useful first contributions

1. Try one documented host route and report host/version, OS, Python, bundle and whether discovery → write → retrieve worked.
2. Improve a confusing installation step using a reproducible example.
3. Report a small bug using synthetic cards; include expected and actual results.
4. Share a practical capture/search/review workflow without exposing private notes.

Host reports become verification evidence only when the environment and steps are recorded. Standalone CLI checks are not host certifications.

## Work on the code

Python 3.10+, no third-party runtime dependencies. Use a fresh temporary `SLIPBOX_HOME` for experiments.

```sh
python -m unittest discover -s tests -v
python scripts/verify_release.py
python scripts/package_skill.py --language en
git diff --check
```

Describe the problem, behavior change and verification in the PR. Keep all relevant tests; add a regression when fixing a concrete bug. Discuss new dependencies, storage formats, synchronization or new public APIs before implementing them.

This public repository accepts issues and PRs. Maintainers bring accepted changes back to their private development source before preparing a new public release, so contributions are not overwritten by later exports. Contributors do not need access to the private repository.

## Privacy, attribution and conduct

Do not upload a personal library, credentials or machine configuration. Report vulnerabilities through [SECURITY.md](SECURITY.md). Verify licenses and retain attribution before importing any code or assets. Contributions use the repository's MIT license. Follow the [code of conduct](CODE_OF_CONDUCT.md).

欢迎中文 issue、PR 和安装反馈。请优先提供可以复现的具体问题；不需要为了贡献先使用英文。
