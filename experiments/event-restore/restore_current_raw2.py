#!/usr/bin/env python3
"""Restore design with read-only dry-run and a filesystem-contained mock backend.

There is intentionally NO live backend, shell runner, I2C, systemd or module API.
Mock PASS does not authorize production restoration or release Phase C HOLD.
"""
import argparse
import fcntl
import json
import pathlib
import tempfile
import time

STEPS = ('STOP_OWN_EXPERIMENT', 'RESTORE_RECEIVER_RUNTIME',
         'RESTORE_SENSOR_PROFILE', 'RESTORE_MEDIA_PROFILE',
         'START_CURRENT_RAW2', 'VERIFY_FRESH_RAW2', 'DISARM_OWN_WATCHDOG')
SENTINEL = 'RP5_RESTORE_SIMULATION_ONLY_V1'
# Pinned known-current files: hashes only, no private register or setfile data.
REQUIRED_HASHES = {
 '/lib/modules/6.12.47+rpt-rpi-2712/updates/rp1-cfe.ko': '0d09dbeaee5fda45bc3e24407254d19dd454c2f4fbb2a26c356b93bf47bfa3dd',
 '/lib/modules/6.12.47+rpt-rpi-2712/extra/s5krc1s_min.ko': '474d02b06165804310e91ee16dca70de691664f1b806783e3f4eda2dd6584153',
 '/home/philip/dvs_raw2_production/raw2_production_start.sh': 'ac7b6b0340a58fcd28b91c457738e12f9ed7532916906f239a538b503845fc12',
 '/home/philip/dvs_raw2_production/raw2_producer': '5c2a88249aca8c3e3af0e0c3ec6ad772cad902ef215bc531a635f9c7af16776b',
 '/boot/firmware/overlays/s5krc1s-cam0.dtbo': '03d0ac9dde5529fcd8194c831eb33c271a24ddd74d7052cbc6cec21bf63699f1',
}
EXPECTED_PARAMETERS = {'s5krc1s_min/csi2_dt':'42', 's5krc1s_min/link_freq_hz':'625000000',
                       'rp1_cfe/diag_pack_bytes':'1', 'rp1_cfe/diag_stride_zero':'Y'}


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def write_state(root, state):
    target = root / 'state.json'
    temporary = root / 'state.next'
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(target)


def fixture(root):
    root = pathlib.Path(root).resolve()
    if not root.is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()):
        raise ValueError('mock root must be under OS temp directory')
    root.mkdir(exist_ok=False)
    (root / 'SIMULATION_ONLY').write_text(SENTINEL)
    state = dict(schema=1, kernel_matches=True, files_match=True, pending=False,
                 firstboot_timer=False, receiver_dt=49, sensor_profile='event',
                 media_profile='event', service_active=False, service_enabled=True,
                 sequence=100, errors=0, visual_ok=True, experiment_running=True,
                 watchdog_armed=True, phase='INITIAL', actions=[],
                 restored=False, real_actions=0, ssh_connected=True)
    write_state(root, state)
    return state


def checked_root(root):
    original = pathlib.Path(root)
    resolved = original.resolve()
    if original.is_symlink() or not resolved.is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve()):
        raise ValueError('invalid simulation root')
    for name in ('SIMULATION_ONLY', 'state.json', 'state.next', 'lock'):
        if (resolved / name).is_symlink():
            raise ValueError('mock files must not be symlinks')
    if (resolved / 'SIMULATION_ONLY').read_text() != SENTINEL:
        raise ValueError('not a simulation root')
    return resolved


def guard(state, deadline):
    if time.monotonic() > deadline:
        raise RuntimeError('restore deadline exceeded')
    if state['pending'] or state['firstboot_timer']:
        raise RuntimeError('first-boot destructive path is possible; refuse')
    if not state['kernel_matches'] or not state['files_match']:
        raise RuntimeError('kernel/file baseline mismatch; refuse')
    if not state['service_enabled']:
        raise RuntimeError('service enable state drift; no enable/disable action permitted')


def healthy(state):
    return (state['receiver_dt'] == 42 and state['sensor_profile'] == 'raw2'
            and state['media_profile'] == 'raw2' and state['service_active']
            and state['errors'] == 0 and state['visual_ok'])


def mock_restore(root, fault='', hold=0):
    root = checked_root(root)
    with (root / 'lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'restored': False, 'phase': 'BUSY', 'real_actions': 0}
        state = read_json(root / 'state.json')
        state['phase'] = 'LOCKED'
        write_state(root, state)
        if hold:
            time.sleep(hold)
        deadline = time.monotonic() + 2
        try:
            guard(state, deadline)
            if state['restored'] and healthy(state):
                state['phase'] = 'VERIFIED_NOOP_MOCK'
                write_state(root, state)
                return state
            if not state['watchdog_armed']:
                raise RuntimeError('independent restore watchdog is not armed')
            for step in STEPS:
                guard(state, deadline)
                if fault == 'deadline':
                    raise RuntimeError('restore deadline exceeded (injected)')
                state['phase'] = step
                state['actions'].append(step)
                if step == 'STOP_OWN_EXPERIMENT':
                    state['experiment_running'] = False
                elif step == 'RESTORE_RECEIVER_RUNTIME':
                    state['receiver_dt'] = 42
                    if fault == 'pending-race':
                        state['pending'] = True
                    if fault == 'timer-race':
                        state['firstboot_timer'] = True
                elif step == 'RESTORE_SENSOR_PROFILE':
                    if fault == 'sensor-restore':
                        raise RuntimeError('sensor profile restore failed (injected)')
                    state['sensor_profile'] = 'raw2'
                elif step == 'RESTORE_MEDIA_PROFILE':
                    state['media_profile'] = 'raw2'
                elif step == 'START_CURRENT_RAW2':
                    if fault == 'service-start':
                        raise RuntimeError('service did not start (injected)')
                    state['service_active'] = True
                elif step == 'VERIFY_FRESH_RAW2':
                    previous = state['sequence']
                    for _ in range(3):
                        if fault != 'stalled-stream':
                            state['sequence'] += 1
                        if fault == 'error-growth':
                            state['errors'] += 1
                        if fault == 'visual-failure':
                            state['visual_ok'] = False
                        if not healthy(state) or state['sequence'] <= previous:
                            raise RuntimeError('RAW2 fresh-frame/health verification failed')
                        previous = state['sequence']
                elif step == 'DISARM_OWN_WATCHDOG':
                    if not healthy(state):
                        raise RuntimeError('health lost before watchdog cancellation')
                    state['watchdog_armed'] = False
                write_state(root, state)
            state['restored'] = True
            state['phase'] = 'VERIFIED_MOCK'
        except RuntimeError as error:
            state['restored'] = False
            state['phase'] = 'MANUAL_INTERVENTION_REQUIRED_MOCK'
            state['error'] = str(error)
            # Preserve the simulated watchdog and all evidence. No fallback.
        write_state(root, state)
        return state


def dry_run(observation):
    blockers = ['LIVE_BACKEND_NOT_IMPLEMENTED', 'PHASE_C_HARD_HOLD',
                'LIVE_REGISTERS_NOT_VERIFIED', 'RESTORE_NOT_PROVEN_ON_HARDWARE',
                'INDEPENDENT_WATCHDOG_NOT_PROVEN_ON_HARDWARE']
    marker = '/home/philip/dvs_raw2_production/pending_first_boot_validation'
    if observation.get('files', {}).get(marker, {}).get('exists', True):
        blockers.append('PENDING_MARKER_PRESENT_OR_UNKNOWN')
    firstboot = observation.get('firstboot', {})
    text = firstboot.get('stdout', '')
    if firstboot.get('returncode') != 0 or text.count('ActiveState=inactive') != 2:
        blockers.append('FIRSTBOOT_UNITS_NOT_CONFIRMED_INACTIVE')
    files = observation.get('files', {})
    checks = {
        'pinned_files_match': all(files.get(p, {}).get('exists') and files[p].get('sha256') == digest for p, digest in REQUIRED_HASHES.items()),
        'receiver_parameters_match': all(observation.get('module_parameters', {}).get(k) == v for k, v in EXPECTED_PARAMETERS.items()),
        'service_observed_active': 'ActiveState=active' in observation.get('service', {}).get('stdout', ''),
        'service_observed_enabled': 'UnitFileState=enabled' in observation.get('service', {}).get('stdout', ''),
        'live_registers_verified': False,
    }
    for name in ('pinned_files_match', 'receiver_parameters_match', 'service_observed_active', 'service_observed_enabled'):
        if not checks[name]:
            blockers.append(name.upper())
    return dict(mode='READ_ONLY_PLAN', production_ready=False, checks=checks,
                allowed_now=['read-only-inspection', 'dry-run', 'mock'],
                steps=list(STEPS), blockers=blockers, real_actions=0,
                existing_rollback_permitted=False,
                observed_at=observation.get('observed_at'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--dry-run', type=pathlib.Path, metavar='OBSERVATION_JSON')
    choice.add_argument('--mock-worker', type=pathlib.Path, metavar='TEMP_MOCK_ROOT')
    parser.add_argument('--fault', default='')
    parser.add_argument('--hold', type=float, default=0)
    args = parser.parse_args()
    if args.dry_run:
        result = dry_run(read_json(args.dry_run))
        print(json.dumps(result, indent=2))
        return 2  # Planned, but hardware readiness is BLOCKED, not success.
    result = mock_restore(args.mock_worker, args.fault, args.hold)
    print(json.dumps(result, indent=2))
    return 0 if result['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
