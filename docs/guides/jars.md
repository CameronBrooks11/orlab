# Getting an OpenRocket jar

orlab drives a real OpenRocket jar; you need one on disk (plus a JDK 17 or
21 — that part stays a prerequisite, see
[Getting started](../getting-started.md)). The fastest path on a bare
machine:

```
pip install orlab
python -m orlab fetch
```

`fetch` downloads the default OpenRocket release from GitHub into a local
cache, verifies its sha256 against a pin shipped with orlab, and prints the
jar's path — the path is the only stable, scriptable output of the CLI.
After that, `OpenRocketInstance()` finds the cached jar on its own.

The same thing in Python:

```python
import orlab

jar = orlab.fetch_jar()          # -> Path to the verified, cached jar
jar = orlab.fetch_jar("22.02")   # any pinned version
```

Fetching is always explicit. `OpenRocketInstance` itself never touches the
network — it only ever reads jars that are already on disk.

## How the default jar is resolved

When `OpenRocketInstance()` is constructed without `jar_path=`, the first
hit wins:

1. `ORLAB_JAR` — a path to a specific jar.
2. The legacy `CLASSPATH` variable (first existing `.jar` entry).
3. The newest supported `OpenRocket-*.jar` in the current directory.
   Only versions with an exact checked-in profile count here, so a stray
   `OpenRocket-26.xx-SNAPSHOT.jar` never outranks a supported release —
   name such a jar explicitly to use it.
4. The newest pinned version already in the fetch cache, re-verified.
   Nothing is downloaded at this step.

`python -m orlab which` prints the jar this chain would pick and which step
found it (the output is informational — script against `fetch`, not
`which`).

## The cache

Jars land in `$ORLAB_JAR_CACHE` if set, else `$XDG_CACHE_HOME/orlab-jars`,
else `~/.cache/orlab-jars`. Every use re-verifies the file against its pin;
a corrupt entry is evicted and re-downloaded. The cache is just files —
delete the directory (or single jars) to reclaim space; the next `fetch`
restores what you need.

## Versions orlab doesn't pin

orlab ships sha256 pins for the versions it supports (see the
[version matrix](../index.md#supported-openrocket-versions)). For any other
version, `fetch_jar` refuses to download unverified — there is no bypass
flag. Compute the digest yourself from a source you trust and pass it:

```python
orlab.fetch_jar("26.00", sha256="...")
```

```
python -m orlab fetch 26.00 --sha256 ...
```

The refusal error includes the release URL, how to compute the digest, and
the digest of any file already cached for that version. A newer orlab
release may simply pin the version — upgrading is usually the easier fix.

## Worth knowing about the default version

`python -m orlab fetch` currently fetches OpenRocket 24.12. On its headless
startup path, OpenRocket 24.12 does not load the *component preset*
database (an upstream gap in `OpenRocketCore`); simulations, motors, and
everything orlab's API touches are unaffected, but code reaching into
component presets via raw Java will find them empty.
