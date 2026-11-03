# Research and scope

Primary documentation checked on 2026-11-03; implementation is original Python
standard-library code, not copied from an upstream implementation.

## Documented facts

- [Git diff format](https://git-scm.com/docs/diff-format) describes patch text
  with Git headers and extended metadata, and a separate combined diff format.
  Those formats carry information beyond this tool's plain unified subset.
- [git apply](https://git-scm.com/docs/git-apply) documents `--check` as testing
  applicability without applying. Its options cover index checks, binary
  patches, path selection, and other broader Git workflows.
- [GNU unified format](https://www.gnu.org/software/diffutils/manual/html_node/Unified-Format.html)
  is an additional format reference. Its page timed out during this run; no
  new factual claim here depends on having fetched its contents.

## Design inference

A small offline checker can provide useful evidence when a caller already has
one trusted base file and wants exact-position context validation without
following patch filenames. Fixed reports also avoid copying source text into
routine logs. This is a proposed workflow benefit, not measured demand or proof
of confidentiality against every operating-system observer.

The deliberate tradeoff is refusing useful features: Git metadata, multiple
files, fuzzy offsets, binary content, and end-of-file newline markers. Logical
line normalization limits what success means. An insertion-only hunk proves
only that its coordinates and structure fit; there are no old lines to compare.

## Alternatives

Use `git apply --check` for broader Git patch applicability. GNU `patch` is a
different established application workflow; it is not used or benchmarked here.
A general diff parser may expose richer metadata but still needs an explicit
matching and filesystem policy. This project only checks bounded offline
evidence against one named local file and makes no superiority claim.
