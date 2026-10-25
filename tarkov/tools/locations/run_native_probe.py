"""Run a built BN location test in separate disposable user directories.

Validates fresh JUnit reports, not just process exit status. A receipt exists
only if every seed completed the exact, nonempty testcase successfully.
Executable build provenance remains the responsibility of the build pipeline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CASE = 'industrial location generates nine matching BN tiles'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_report(path, case=CASE):
    root = ET.parse(path).getroot()
    suites = list(root.iter('testsuite'))
    cases = list(root.iter('testcase'))
    if len(cases) != 1 or cases[0].get('name') != case:
        raise ValueError('Expected exactly the location testcase')
    if any(e.tag in ('failure','error','skipped') for e in root.iter()):
        raise ValueError('Location testcase failed or was skipped')
    if not suites or sum(int(s.get('tests','0')) for s in suites) < 1:
        raise ValueError('Empty JUnit result')
    if any(int(s.get(attr,'0')) for s in suites for attr in ('failures','errors','skipped')):
        raise ValueError('Unsuccessful JUnit suite')


def run(bn, executable, output, seeds, location="industrial"):
    if location not in ("industrial", "factory"):
        raise ValueError("Unknown location probe")
    factory = location == "factory"
    mod_id = "trkv_factory_dev" if factory else "trkv_locations_dev"
    test_name = "trkv_factory_constructor_test.cpp" if factory else "trkv_location_constructor_test.cpp"
    source_name = "bn_factory_probe.cpp.inc" if factory else "bn_location_probe.cpp.inc"
    fixture_name = "trkv_factory_fixture.inc" if factory else "trkv_location_fixture.inc"
    case = "factory ground draft generates matching BN tiles" if factory else CASE
    tag = "[trkv_factory]" if factory else "[trkv_locations]"
    bn, executable, output = bn.resolve(), executable.resolve(), output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    receipt=output/'location-native-receipt.json'
    receipt.unlink(missing_ok=True)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('Seeds must be nonempty and distinct')
    if any(not isinstance(s,int) or not 0 <= s <= 2**32-1 for s in seeds):
        raise ValueError('Seeds must be unsigned 32-bit integers')
    installed_mod=bn/'data/mods'/mod_id
    for name in ['mapgen.json','modinfo.json','overmap.json']:
        if digest(installed_mod/name) != digest(ROOT/'mods'/mod_id/name):
            raise ValueError(f'Installed mod differs: {name}')
    if (bn/'tests'/test_name).read_bytes() != (ROOT/'tests/locations'/source_name).read_bytes():
        raise ValueError('Installed test source differs')
    # This is a source-input check, not proof that an arbitrary executable was rebuilt.
    from install_native_probe import BN_SHA, fixture
    if factory:
        from install_factory_probe import fixture
    if (bn/'tests'/fixture_name).read_text(encoding='utf-8') != fixture():
        raise ValueError('Installed fixture differs')
    sha=subprocess.check_output(['git','-C',str(bn),'rev-parse','HEAD'],text=True).strip()
    if sha != BN_SHA:
        raise ValueError('Wrong BN base')
    records=[]
    for seed in seeds:
        report=output/f'location-native-{seed}.xml'
        log=output/f'location-native-{seed}.log'
        report.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix='trkv-location-native-') as scratch:
            # BN test_main recursively deletes its user directory on start.
            # Give it a dedicated child, never the user's save/config folder.
            user=Path(scratch)/'user'
            args=[str(executable),f'--user-dir={user}', f'--mods={mod_id}',
                  tag,'--rng-seed',str(seed),'--reporter','junit','--out',str(report)]
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run(args,cwd=bn,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
            result.check_returncode()
            validate_report(report, case)
        records.append({'seed':seed,'report':report.name,'sha256':digest(report),'log':log.name})
    data={'evidence':'native_generation','location':location,'bn_commit':sha,'executable_sha256':digest(executable),
          'mapgen_sha256':digest(installed_mod/'mapgen.json'),
          'test_source_sha256':digest(bn/'tests'/test_name),
          'fixture_sha256':digest(bn/'tests'/fixture_name), 'runs':records,
          'limitations':['Сборочное происхождение executable подтверждает внешний pipeline',
                        'Не проверяет игровой lightmap, открывание дверей, НПС или Windows-интерфейс']}
    receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bn',type=Path,required=True)
    p.add_argument('--exe',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seeds',type=int,nargs='+',default=[20261025,20261026,20261027])
    p.add_argument('--location',choices=['industrial','factory'],default='industrial')
    a=p.parse_args()
    print(run(a.bn,a.exe,a.output,a.seeds,a.location))
