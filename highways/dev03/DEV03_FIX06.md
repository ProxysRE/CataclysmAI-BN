# DEV0.3 fix06

Run 37974445726 compiled the source but failed linking the game and tests: the generic JSON enum reader required the absent io::enum_to_string<oter_flags> specialization.

The nested neighbor reader now uses BN’s canonical oter_flags_map, matching the terrain loader. Unknown names still throw JSON errors; OR/AND direction behavior stays intact. Existing native direction tests remain enabled.

Local checks: patch application and C++23 header syntax passed. The Windows workflow builds game and tests before packaging; the replacement run is pending.
