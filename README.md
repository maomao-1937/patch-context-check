# patch-context-check

[![tests](https://github.com/maomao-1937/patch-context-check/actions/workflows/tests.yml/badge.svg)](https://github.com/maomao-1937/patch-context-check/actions/workflows/tests.yml)

Check whether a **plain, single-file unified diff** matches the exact old-line
positions of one explicitly named local file. The tool does not apply patches.
Its result is bounded context evidence, not a guarantee of Git applicability.

## Run from source

Requires Python 3.11 or later and its standard library. Download the project,
open a terminal in its directory, and run the source directly. There is no
package installation, configuration, environment variable, account, Git runtime,
network access, or third-party dependency.

```console
python patch_context_check.py fixtures/clean.patch fixtures/base.txt
{"code": "CLEAN", "files": 1, "hunks": 1}
python patch_context_check.py fixtures/mismatch.patch fixtures/base.txt
{"base_line": 1, "code": "MISMATCH", "file": 1, "hunk": 1, "patch_line": 4}
python patch_context_check.py fixtures/unsupported.patch fixtures/base.txt
{"code": "INVALID"}
```

| Exit | Meaning |
| --- | --- |
| 0 | All specified old context/deletion lines match at their stated positions. |
| 1 | An old context/deletion line differs at its stated position. |
| 2 | Malformed, unsupported, unreadable, invalid path, or over-limit input. |

`python patch_context_check.py --help` prints fixed help. Reports contain only
fixed codes, ordinal counts, and line indices as deterministic JSON. Names, headers, hunk labels,
content, and filesystem error messages are never echoed. A closed output pipe
is handled without a traceback or interpreter shutdown exit 120; the computed
status is retained even if the report cannot be delivered.

## Accepted subset and exactness

- Start with exactly one `--- NAME` / `+++ NAME` header pair and at least one
  hunk. Names must be nonempty; they are opaque labels, never opened. A second
  file section is rejected. Header-looking text inside a correctly counted
  deletion/addition body remains body content.
- Hunk syntax: `@@ -start[,count] +start[,count] @@` with an optional space and
  label. Omitted count means 1. Counts must exactly equal body lines, counting
  a space for both sides, `-` for old, and `+` for new.
- A zero count identifies the boundary after `start` lines; `-0,0` inserts at
  the beginning. Positive counts cannot start at zero. Empty-to-empty hunks
  are rejected. Old starts must increase strictly and ranges cannot overlap.
  New positions must equal old positions plus the cumulative earlier delta.
  Any old range outside the supplied base is invalid (exit 2).
- Every context and deleted line must match at its exact old position. There
  is no offset search, whitespace tolerance, or fuzzy matching. Added lines
  are checked structurally; their meaning is not evaluated.
- Both inputs must be UTF-8 without BOM or NUL. CRLF is normalized to LF;
  lone CR is rejected. The final newline is deliberately ignored on both
  inputs: `alpha` and `alpha\n` compare equal. **This is not byte equivalence.**
  The `\ No newline at end of file` marker is explicitly unsupported (exit 2),
  so this tool cannot verify end-of-file newline changes.
- Only plain unified text is supported. Git `diff --git` / `index` headers,
  multiple files, combined diffs, binary patches, renames, copies, modes,
  creation/deletion metadata, mail wrappers, and extra text are rejected.
  `/dev/null` in an opaque header carries no filesystem semantics.

## Limits and local-file boundary

Each input is limited to 2,097,152 bytes and 20,000 logical lines; at most 1,000
hunks are accepted. Numeric fields are ASCII decimal, at most five digits and
40,000; counts are at most 20,000. These limits are inclusive.

Both arguments must name regular files. URI syntax, UNC/device paths, mixed
slash/backslash spellings, Windows reserved device components, alternate data
streams, and drive-relative paths are lexically rejected before either input
is opened. Ordinary Windows absolute drive paths and local relative paths are
accepted. Final-component symlinks/reparse points are refused.

This is a local workflow boundary, not a filesystem sandbox: parent-directory
symlinks, mount points, and concurrent replacement can affect what is read.
Use trusted, stable local directories. The program opens only the two named
inputs for reading and creates no output files. It neither invokes Git or
subprocesses nor accesses the network. OS access-time updates may still occur.

Verified locally on CPython 3.11.15, Windows 10 build 26300, on 2026-11-03.
Other supported Python/platform combinations have not been locally verified.
See [TESTING.md](TESTING.md) and [RESEARCH.md](RESEARCH.md).

## 中文说明

这是一个只读检查器：把一个普通、单文件 unified diff 与你明确指定的本地文件比较，
确认上下文行和删除行是否位于补丁写明的位置。它不会应用补丁，也不会搜索其他位置。

无需安装依赖或配置；在项目目录用 Python 3.11+ 运行：

```console
python patch_context_check.py fixtures/clean.patch fixtures/base.txt
{"code": "CLEAN", "files": 1, "hunks": 1}
```

退出码：`0` 表示范围内的旧行准确匹配，`1` 表示内容不匹配，`2` 表示格式、路径、
读取或资源限制问题。输出只含固定状态和行号，不输出文件内容、路径或头部名称。

仅支持一对 `---` / `+++` 头部和至少一个 hunk；头部名称只是标签，不会被打开。
支持零长度范围的插入与删除，并检查行数、顺序、重叠和累计新行偏移。拒绝 Git 元数据、
多文件、二进制、合并、重命名及无末尾换行标记。请勿把 `CLEAN` 当成 Git 可应用保证。

输入须为无 BOM 的 UTF-8；CRLF 与 LF 归一化，忽略末尾换行差异。每个输入最多
2 MiB、20,000 行，最多 1,000 个 hunk。只读取两个明确指定的普通本地文件；
URI、UNC、设备路径及混用分隔符会被拒绝。末级符号链接被拒绝，但父目录链接、
挂载点和并发文件替换不属于隔离保证。已在 Windows 的 CPython 3.11.15 实测。
