# Shared palette compatibility

Pinned DDA/BN roof and sewer palettes plus the DDA nested rooftop chunks are preserved in SOURCE_EVIDENCE.json with SHA256 and Git blob checksums. The original paths are data/json/mapgen_palettes/{roof_palette,sewers_palette}.json and data/json/mapgen/nested/nested_chunks_roof.json. Pins match the main project.

bn_shared_palettes.py fills only glyph bindings actually used by a ported map but absent from both the local object and its stock BN shared palette. Existing bindings and BN palettes remain unchanged. The eldercare sites require the roof v ladder-down binding, the sewer < ladder-up binding and the roof 1 solar chunk selector. All nine source solar layouts are retained, using existing BN f_solar_unit/f_solar_unit_v2 with source geometry, probabilities and variants. Hardware behavior/output follows BN; source layout names are not claims of identical kW output. Native source/installed generation remains pending.
