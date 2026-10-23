"""Check shipped Russian text and exercise the UI using the real Lua callbacks."""
import gettext
import json
import re
from pathlib import Path

from lupa.lua54 import LuaRuntime

MOD = Path(__file__).resolve().parents[1] / "mods/trkv_raid_core"


def main():
    with (MOD / "lang/ru.mo").open("rb") as stream:
        ru = gettext.GNUTranslations(stream)
    messages = set()
    for filename in ("furniture.json", "items.json", "modinfo.json", "overmap.json", "world_types.json", "npcs.json"):
        for entry in json.loads((MOD / filename).read_text(encoding="utf-8")):
            for key in ("name", "description", "job_description", "name_suffix"):
                if key not in entry:
                    continue
                value = entry[key]
                messages.add(value["str"] if isinstance(value, dict) else value)
    source = (MOD / "main.lua").read_text(encoding="utf-8")
    messages.update(re.findall(r'_\("([^"\n]+)"\)', source))
    errors = (MOD / "trkv_lifecycle.lua").read_text(encoding="utf-8")
    messages.update(msg for msg in re.findall(r'"([^"\n]*)"', errors) if ";" in msg or msg.endswith("."))
    for msg in messages:
        translated = ru.gettext(msg)
        assert translated != msg, msg
        assert re.findall(r'%[0-9]*[sd]', msg) == re.findall(r'%[0-9]*[sd]', translated), msg
    for n in (1, 2, 5, 11, 21):
        assert "пакет" in ru.ngettext("sealed raid test package", "sealed raid test packages", n)
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().translate = ru.gettext
    lua.execute('''
        locale = { gettext = translate }
        local mod, storage = {}, {}
        game = { current_mod = "trkv_raid_core", mod_runtime = { trkv_raid_core = mod },
                 mod_storage = { trkv_raid_core = storage } }
        local clock, where = 100, "home"
        messages, entries = {}, {}
        gapi = { add_msg = function(s) messages[#messages + 1] = s end,
                 add_on_every_x_hook = function(_, f) tick = f end }
        TimeDuration = { from_seconds = function(v) return v end }
        UiList = { new = function() return {
          title = function(_, s) menu_title = s end,
          add = function(_, id, s) entries[id] = s end,
          query = function() return 2 end,
        } end }
        package.loaded.trkv_bn = {
          check_capabilities = function() end,
          at_home = function() return where == "home" end,
          at_raid = function() return where == "raid" end,
          now = function() return clock end,
        }
        function pending_entry()
          storage.raid.phase = "entering"
          mod.start()
          tick()
        end
        function failed_state()
          storage.raid.phase, where = "active", "unrelated"
          mod.start()
          return storage.raid.last_error
        end
        function warning()
          messages = {}
          storage.raid.phase, storage.raid.deadline = "active", 160
          where = "raid"
          tick()
        end
    ''')
    lua.globals().package.loaded.trkv_lifecycle = lua.execute((MOD / "trkv_lifecycle.lua").read_text())
    lua.globals().package.loaded.trkv_patrol = lua.execute((MOD / "trkv_patrol.lua").read_text())
    lua.globals().package.loaded.trkv_participants = lua.execute((MOD / "trkv_participants.lua").read_text())
    lua.globals().package.loaded.trkv_deployment = lua.execute((MOD / "trkv_deployment.lua").read_text())
    lua.globals().package.loaded.trkv_loadouts = lua.execute((MOD / "trkv_loadouts.lua").read_text())
    lua.globals().package.loaded.trkv_encounter = lua.execute((MOD / "trkv_encounter.lua").read_text())
    lua.execute(source)
    lua.execute('game.mod_runtime.trkv_raid_core.start()')
    assert lua.globals().entries[3] == "Войти в тестовый рейд с патрулями (3 нейтральных НПС)"
    assert lua.globals().entries[4] == "Войти в боевой тестовый рейд (1 враждебный стрелок)"
    assert lua.globals().entries[6] == "Войти в рейд с разными комплектами (3 варианта снаряжения)"
    assert lua.globals().entries[5] == "Войти в тестовый рейд с группой (3 враждебных НПС)"
    assert lua.globals().entries[1] == ru.gettext("Enter test raid (30 game minutes)")
    assert lua.globals().menu_title == ru.gettext("Tarkov DEV0.1: departure terminal")
    lua.eval("pending_entry")()
    assert lua.globals().entries[1] == ru.gettext("Retry pending raid entry")
    raw_error = lua.eval("failed_state")()
    assert raw_error == "Active raid dimension mismatch; automatic changes stopped."
    assert lua.globals().messages[2] == ru.gettext(raw_error)
    lua.eval("warning")()
    assert "До конца рейда: 1:00" in lua.globals().messages[1]
    print("PASS Russian JSON, menus, retry and countdown; format arguments and plurals")


if __name__ == "__main__":
    main()
