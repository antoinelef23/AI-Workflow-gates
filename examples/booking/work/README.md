# work/

One directory per unit of work: `work/<feature>/` holds the three artifacts `spec.md` (the WHAT),
`design.md` (the HOW) and `tasks.md` (the DO). Read them in that order.

`_templates/` holds the starting points (`spec.template.md`, `design.template.md`,
`tasks.template.md`). They are deliberately **not** named `spec.md` / `design.md` / `tasks.md`:
a directory holding one of those is treated as a feature by the hooks and CI checks, and the raw
template does not pass plan-lint. To start a feature, copy each template into
`work/<feature>/` under its real name and fill it in.

Raw client inputs that feed a feature go in `work/<feature>/assets/` (not versioned by default).
