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
`__pycache__`. It does not alter `raw/` content in the source vault.
