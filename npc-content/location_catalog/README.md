# DDA / BN location gap audit

The seven source parts preserve 159 exact upstream JSON files plus a complete mapgen filename/blob index for both project pins. Every upstream JSON blob was verified against its pinned Git tree before the bundle was built. The source manifest records SHA256 and Git blob identities. Mods are excluded.

`compare_location_catalog.py` reads only the multipart source bundle, manifest and reviewed groups; the raw sources directory is an optional local cache. `check_location_catalog.py` reconstructs the comparison without network access and checks typed identities, mutable template labels, literal cardinal-suffix IDs, placement constraints and reviewed exclusions.

MISSING_AND_PARTIAL.md is the human report. REVIEWED_REPORT.json contains evidence and counts. COMPARISON.json is a reproducible local intermediate with all 729 DDA registrations; it is intentionally not duplicated in Git.

The audit covers every core overmap_special, overmap_mutable and multitile_city_buildings registration in these pins, all overmap terrain declarations (58 DDA / 35 BN files), the complete mapgen file inventories and six selected mapgen files. It does not compare every nested map or every interior sharing an existing ID. An absent identifier does not establish absence of an entire semantic building category. Three groups remain excluded from the human list pending renamed-layout review.

An OMT placement count includes support terrain such as rock and fields; it is not a room/building count. Hub has 100 actual DDA terrain placements plus two placement constraints, versus 69 BN terrain placements. Earlier project notes that called all 102 records terrain cells were imprecise; the new report separates them.

This audit adds no locations to generation. It is an evidence-backed port queue, not a claim that the listed locations already run in BN.
