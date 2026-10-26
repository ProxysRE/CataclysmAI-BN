# Factory client geometry tools

`inspect_tarkov_client.py` inventories selected containers using Python's
standard library. It is not a complete file listing: extensionless bundles are
not covered by its original selection policy.

`audit_factory_scenes.py` reads flat ZIPs of selected level/sharedassets files
and reports geometry availability. Dependency ZIPs can be repeated with
`--dependency-zip`. It does not resolve external vertex streams in these ZIPs.

## Local collision export

`export_factory_colliders.py` reads an installed client's Data directory and
exports just serialized collider components and the Mesh geometry they reference.
Keep `audit_factory_scenes.py` beside it for the shared transform implementation.

For the user's installation:

```powershell
py -m pip install UnityPy==1.25.4
py .\export_factory_colliders.py "D:\tarkov" --output ".\factory_collision_export.zip"
```

The game Data directory itself is also accepted. The output must be new; an
existing export is not overwritten. No game process, DLL or launcher is run.
Only selected game files are read. No account data, textures or audio is exported.
Dependency installation is separate from running this offline exporter.

Scene numbers come from this client's BuildSettings, selected by the exact
Factory_Rework directory segment. The current client's selection has 18 scenes,
including its office, laboratory and day/night auxiliary scenes. Old Factory
scenes elsewhere in the build are excluded. The script then resolves every
standard serialized collider's Transform chain and its referenced Mesh, including
external vertex streams. Parent activation and component flags are retained;
inactive/disabled/trigger colliders are included with those flags, not silently
made solid. Built-in mesh references map only to the known Resources file.

ZIP contents:

- `colliders.jsonl`: scene/component identity, object name, layer, state flags,
  world matrix, Mesh reference or primitive shape parameters.
- `meshes.jsonl`: each referenced Mesh once, indexed vertices/triangles, source ID.
- `report.json`: versions, selected scenes, collision layers/matrix, source hashes,
  missing data/errors and completeness for selected **serialized** colliders.

64-bit object IDs are JSON strings. A partially available installation produces a
partial report; read `issues` and `complete_for_selected_serialized_colliders`.
An interrupted export without report.json is incomplete and must not be accepted.
This completeness flag does not validate runtime activation, custom behaviour,
door states, character clearance, navigation, falling or a BN conversion.

## Verification

The exporter was run on the supplied real-client subset: three of the eighteen
selected scenes were available, and the others remained explicitly missing.
An export with collider records and 1000 decoded unique Mesh resources was
read back. Tests cover transform composition, invalid parent graphs, ZIP source
identity, build-specific scene indices, external-file indexing, 64-bit IDs and
source-directory selection. Windows execution and full-installation coverage
still require the user's run; the development environment is Linux.

```sh
python tarkov/tests/locations/client_transform_test.py -v
python tarkov/tests/locations/client_export_test.py -v
```

The user's full Windows export has subsequently been read and independently
validated: all 18 selected scenes, 53546 colliders, 2666 unique Mesh resources,
48112 resolved non-null Mesh references, no reported issues, and matching hashes
for all thirteen previously supplied source files. This confirms this export's
serialized-data integrity, not gameplay or runtime completeness.

`validate_factory_export.py` needs only standard Python. It verifies CRCs,
identities, references, finite geometry, triangle ranges and report totals; the
optional baseline checks source identity. It rejects incomplete exports.

```sh
python tarkov/tools/client_data/validate_factory_export.py factory_collision_export.zip --baseline tarkov/locations/factory_01/reference/client_structure_audit.json --output validated.json
python tarkov/tests/locations/client_export_validation_test.py -v
```
