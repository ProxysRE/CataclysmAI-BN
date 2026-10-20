# Tarkov project development

- This directory is independent of the root Mantella/Narrative roadmap and DDA-port branches.
- Read README, docs/DECISIONS, docs/ARCHITECTURE, docs/ROADMAP and docs/VERIFICATION first.
- Pin BN by full SHA; don't upgrade it while debugging project behavior.
- Distinguish fixture tests, real bound-object integration, and full process reload.
- Never claim runtime success from fast-checks or from compilation alone.
- Native CMake builds without translations require `LANGUAGES=none`; `LOCALIZE=OFF`
  alone does not stop compilation of language files in this BN baseline.
- Native tests normally disable mapgen. Explicitly enable it for generated-map tests
  and restore the setting with the existing scope guard.
- Use typed terrain IDs for map bindings (`TerId.new(...):int_id()`).
- Dimension reset saves before clearing data; saved cleanup must be replayable.
- Don't cancel an expensive native build for documentation-only changes.
- Save only plain data in mod_storage. Keep Item/Npc/Map references out of saves.
- BN deserialization replaces nested storage tables. Resolve `storage.raid` inside
  each callback; never capture its pre-load identity. Test registered callbacks as
  well as the engine-independent controller.
