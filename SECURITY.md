# Security Policy

## Supported versions

`bookreader-tui` follows semantic versioning. Security fixes land on
the latest minor; only the latest minor is supported.

| Version | Supported          |
|---------|--------------------|
| 0.4.x   | :white_check_mark: |
| < 0.4   | :x:                |

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue.

Use GitHub Private Vulnerability Reporting:
**https://github.com/prajwalmahajan101/BookReader/security/advisories/new**

You'll get an acknowledgement within **5 business days**. Once a fix
is ready, we'll coordinate disclosure with you.

## What's in scope

`bookreader-tui` is a local-only TUI. It does not run a server, open a
network socket, or accept untrusted RPC. The realistic attack surface
is:

- **Malicious EPUB files** — the parser uses `ebooklib` + `lxml` +
  `beautifulsoup4`. We rely on those projects for malformed-input
  hardening; if you find a crash or path-traversal triggered by a
  crafted EPUB, that's in scope.
- **SQLite library file tampering** — opening a maliciously crafted
  `library.db` (e.g. an attacker who already has filesystem access to
  your home directory). In scope at the parser level; out of scope as
  a privilege boundary.
- **Image rendering** — bytes from EPUB images flow through `Pillow`
  and `textual-image`. Crashes or memory issues triggered by
  pathological PNGs/JPEGs are in scope.

## What's out of scope

- Anything that requires the attacker to already have shell access as
  your user.
- Vulnerabilities in upstream libraries (report those upstream); we
  bump dependencies promptly when CVEs surface.
- The terminal emulator itself (kitty, iTerm2, sixel implementations).
