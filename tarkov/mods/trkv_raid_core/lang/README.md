# Russian catalog

BN loads `lang/ru.mo` when Russian is selected. JSON strings use the built-in
translation mechanism; Lua UI calls `locale.gettext`. Lifecycle save keys and
raw errors stay in English and are translated only when displayed.

After editing `ru.po`, regenerate the committed runtime catalog:

```sh
python -m pip install polib==1.2.0
python -c "import polib; polib.pofile('tarkov/mods/trkv_raid_core/lang/ru.po').save_as_mofile('tarkov/mods/trkv_raid_core/lang/ru.mo')"
python tarkov/tools/check.py
```

The pinned BN checkout does not contain `.po` translations. The Windows workflow
imports the platform-independent `.mo` catalog from official BN release 2026-10-19.
The source archive SHA256 is pinned in `tools/install_translations.py` and the
provenance is included in `lang/mo/ru_RU/SOURCE.json` and `TARKOV_BUILD.json`.
Only the translation is imported; the engine baseline stays unchanged.
