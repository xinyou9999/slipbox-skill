# slipbox for DeepSeek Harness

Native bundle with an installed plugin item, permanent **卡片笔记** navigation, real Markdown card UI and the host's default-model AI conversation. The Python standard-library core is shared with the portable Skill; no separate model credential is required.

Download the prebuilt archive from the [DSH plugin release](https://github.com/xinyou9999/slipbox-skill/releases/tag/dsh-v0.1.1). Build from the public repository root with `node scripts/package_harness_plugin.mjs`. Install the resulting local `.tgz` with `dsh plugin --profile desktop add <absolute-tgz-path> --ignore-scripts`. Select the profile you actually run, then fully quit and reopen Harness. See [installation and market discovery](../../docs/HARNESS_PLUGIN.md). GitHub publication does not register the plugin in a marketplace.

Plugin settings: `libraryPath` is the actual local library (default `SLIPBOX_HOME` or `~/.slipbox`); `pythonPath` is a Python 3.10+ executable accessible to the host. Using the same local library across agents requires the same accessible filesystem. Removing the plugin preserves the library.

AI actions open a new host conversation and queue the requested task using the default model. The conversation shows progress and errors. Returning to the card page and refreshing shows committed changes; queuing a request is not proof that the model finished.

Version0.1.1 was validated on Windows Harness0.2.1-rc.3: installed item, persistent navigation, create/search/edit/tag controls, two themes and a real default-model tag-list/add/show cycle. Other operating systems and host versions remain untested. The public repository contains source files; the release archive additionally bundles the core/Skill files required for standalone installation. Do not install this source subdirectory alone as a complete Git package.
