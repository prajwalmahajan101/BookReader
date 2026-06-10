# Architecture decision records

Each phase of the project came with a short ADR capturing the decision,
its alternatives, and the consequences. Files live at
[`docs/adr/`](https://github.com/prajwalmahajan101/BookReader/tree/main/docs/adr)
in the repo.

| # | Decision |
|---|---|
| [0001](https://github.com/prajwalmahajan101/BookReader/blob/main/docs/adr/0001-stack-choice.md) | Stack choice — Textual + ebooklib + SQLite |
| [0002](https://github.com/prajwalmahajan101/BookReader/blob/main/docs/adr/0002-library-screen.md) | Library screen — SQLite, repository + service pattern |
| [0003](https://github.com/prajwalmahajan101/BookReader/blob/main/docs/adr/0003-textual-theme-system.md) | Migrate to Textual's first-class theme system |
| [0004](https://github.com/prajwalmahajan101/BookReader/blob/main/docs/adr/0004-phase3-data-model.md) | Phase 3 data model — phantom books and sessions |

When to write a new one: change a persistence schema, a protocol between
layers (epub ↔ library ↔ ui), a dependency choice, or a user-visible
behaviour that's not obvious from the code. Pattern is **Context ·
Decision · Consequences**.
