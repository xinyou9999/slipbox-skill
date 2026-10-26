# Security and privacy

The CLI stores local Markdown cards and tag vocabulary. It does not call model APIs. The host agent may send content to its configured model; check its privacy policy and execution environment.

Use a private local directory. Local locking is not distributed synchronization, collaborative conflict resolution or multi-user access control. Read the [storage boundaries](references/data-format.md).

For vulnerabilities, use GitHub **Security → Report a vulnerability** if the repository enables it. If no private reporting channel is available, request one from the maintainer without posting the details. Do not publish private data or an exploit in a normal issue.

Include the affected version/commit, OS/Python and a synthetic reproduction. There is no promised response SLA or bounty. Installation bugs can use the ordinary issue template.
