#!/usr/bin/env python3
"""Fault-injection tests. Only OS temp fixtures and fake JSON state are modified."""
import argparse,copy,json,pathlib,subprocess,sys,tempfile,time
from restore_current_raw2 import fixture,mock_restore,read_json,write_state,dry_run,STEPS,REQUIRED_HASHES,EXPECTED_PARAMETERS


def run_tests():
    results=[]
    with tempfile.TemporaryDirectory(prefix='rp5-restore-tests-') as directory:
        base=pathlib.Path(directory)
        def setup(name,changes=None):
            root=base/name;state=fixture(root)
            if changes:state.update(changes);write_state(root,state)
            return root
        root=setup('happy');r=mock_restore(root);assert r['restored'] and not r['watchdog_armed'] and r['actions']==list(STEPS)
        results.append({'case':'successful-mock-restore','pass':True,'real_actions':r['real_actions']})
        actions=r['actions'][:];r=mock_restore(root);assert r['phase']=='VERIFIED_NOOP_MOCK' and r['actions']==actions
        results.append({'case':'idempotent-repeat','pass':True})
        for fault in ('sensor-restore','service-start','stalled-stream','error-growth','visual-failure','pending-race','timer-race','deadline'):
            root=setup(fault);r=mock_restore(root,fault)
            assert not r['restored'] and r['watchdog_armed'] and r['real_actions']==0 and 'DISARM_OWN_WATCHDOG' not in r['actions']
            results.append({'case':fault,'pass':True,'observed_phase':r['phase'],'error':r['error'],'watchdog_preserved':True})
        for name,change in (('pending-present',{'pending':True}),('timer-active',{'firstboot_timer':True}),('hash-drift',{'files_match':False}),('kernel-drift',{'kernel_matches':False}),('enable-state-drift',{'service_enabled':False}),('watchdog-missing',{'watchdog_armed':False})):
            root=setup(name,change);r=mock_restore(root);assert not r['restored'] and not r['actions']
            results.append({'case':name,'pass':True,'writes_before_refusal':0})
        # A short-lived mock SSH client spawns a separate local watchdog worker.
        # No ssh command, network outage or real systemd unit is used.
        root=setup('ssh-disconnect',{'ssh_connected':False})
        script=str(pathlib.Path(__file__).with_name('restore_current_raw2.py').resolve())
        launcher='import subprocess,sys; p=subprocess.Popen([sys.executable,sys.argv[1],"--mock-worker",sys.argv[2],"--hold","0.1"],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid)'
        child_pid=int(subprocess.check_output([sys.executable,'-c',launcher,script,str(root)],text=True))
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            r=read_json(root/'state.json')
            if r['restored']:break
            time.sleep(.02)
        assert r['restored'] and not r['ssh_connected'] and r['real_actions']==0
        results.append({'case':'mock-ssh-client-exits-independent-worker-finishes','pass':True,'real_ssh_disconnect_tested':False})
        root=setup('concurrent')
        p=subprocess.Popen([sys.executable,script,'--mock-worker',str(root),'--hold','0.3'],stdout=subprocess.DEVNULL)
        deadline=time.monotonic()+3
        while read_json(root/'state.json')['phase']!='LOCKED' and time.monotonic()<deadline:time.sleep(.01)
        assert mock_restore(root)['phase']=='BUSY';assert p.wait(timeout=5)==0
        results.append({'case':'concurrent-worker-lock','pass':True})
        before=copy.deepcopy(read_json(root/'state.json'));plan=dry_run({});assert not plan['production_ready'] and plan['real_actions']==0 and read_json(root/'state.json')==before
        results.append({'case':'dry-run-no-state-write-fail-closed','pass':True})
        observation={'files':{p:{'exists':True,'sha256':h} for p,h in REQUIRED_HASHES.items()},'module_parameters':EXPECTED_PARAMETERS.copy(),'service':{'stdout':'ActiveState=active\nUnitFileState=enabled'},'firstboot':{'returncode':0,'stdout':'ActiveState=inactive\nActiveState=inactive'}}
        observation['files']['/home/philip/dvs_raw2_production/pending_first_boot_validation']={'exists':False}
        plan=dry_run(observation);assert all(plan['checks'][k] for k in ('pinned_files_match','receiver_parameters_match','service_observed_active','service_observed_enabled')) and not plan['production_ready']
        results.append({'case':'known-current-hashes-still-not-live-ready','pass':True})
        changed=copy.deepcopy(observation);changed['module_parameters']['s5krc1s_min/csi2_dt']='49';assert not dry_run(changed)['checks']['receiver_parameters_match']
        results.append({'case':'dry-run-detects-runtime-dt-drift','pass':True})
        changed=copy.deepcopy(observation);changed['files'][next(iter(REQUIRED_HASHES))]['sha256']='0'*64;assert not dry_run(changed)['checks']['pinned_files_match']
        results.append({'case':'dry-run-detects-module-hash-drift','pass':True})
        bad=subprocess.run([sys.executable,script,'--apply-live'],capture_output=True);assert bad.returncode!=0
        results.append({'case':'live-mode-unavailable','pass':True})
        for target in (pathlib.Path('/'),pathlib.Path('/home/philip')):
            try:mock_restore(target)
            except ValueError:pass
            else:raise AssertionError('non-temp root accepted')
        results.append({'case':'reject-production-root','pass':True})
    return {'pass':True,'simulation_only':True,'real_production_actions':0,'cases':results,'case_count':len(results)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=pathlib.Path,required=True);args=p.parse_args()
    r=run_tests();args.results.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'pass':True,'case_count':r['case_count']}))
