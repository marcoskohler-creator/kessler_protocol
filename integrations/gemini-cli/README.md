# Gemini CLI Adapter

Install via the Kessler CLI so existing `settings.json` content is preserved:

```bash
kessler install --target gemini --scope user
```

The installer adds three uniquely named hooks (`kessler-before-tool`, `kessler-after-tool`, `kessler-after-agent`) and copies the skill under the selected Gemini scope. Uninstall removes only those named Kessler entries.
