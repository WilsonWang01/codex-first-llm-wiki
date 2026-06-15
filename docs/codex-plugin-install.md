# Codex Plugin Install

This vault includes a local Codex plugin manifest at
`.codex-plugin/plugin.json`.

Validate the plugin bundle:

```bash
python3 tools/install_plugin.py --check
```

Install a copy into the default local plugin directory:

```bash
python3 tools/install_plugin.py --install
```

Install into a custom plugin directory:

```bash
python3 tools/install_plugin.py --install --target ~/some/plugin-dir
```

The install script copies the vault and ignores transient files such as
`__pycache__`. When the vault is a Git checkout, it installs only tracked files
so private `raw/` sources and generated wiki pages ignored by `.gitignore` do
not get copied into the plugin bundle. It does not alter `raw/` content in the
source vault.
