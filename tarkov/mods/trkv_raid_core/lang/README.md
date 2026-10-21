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

The Windows workflow also builds the official BN Russian catalog from the pinned
base's `lang/po/ru.po`; that larger catalog is not duplicated here.
