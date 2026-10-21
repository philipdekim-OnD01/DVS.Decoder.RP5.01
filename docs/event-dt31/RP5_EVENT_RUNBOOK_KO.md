# S5KRC1S / RP5 — Event Packet DT 0x31 실험 실행 지침

작성: 2026-10-21. 대상: Raspberry Pi 5 한 대, 운영 중인 RAW2 캡처와 동일 센서.
이 문서는 실험 계획·중단 조건·검증 기준을 고정하며, **그 자체로 장래의 무제한 실행 승인을 의미하지 않는다.**
작업자는 이 문서와 [PROGRESS.md](./PROGRESS.md)를 단계마다 참조하고 GitHub에 진척을 남긴다.

## 0. 목표와 출발 상태

목표는 기존 Raspberry Pi 5 RAW2 (`CSI-2 DT=0x2A`) 운영 환경을 보존하면서, S5KRC1S Event Packet (`DT=0x31`)을 기존 RP1 CFE와 GREY/Y8 DMA 컨테이너로 받아 민수 C++ 이벤트 디코더가 복원할 수 있는지 검증하는 것이다.

- [PR #2 — Phase 1·2 분석](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/2): 보관된 커스텀 센서 `get_frame_desc`, `csi2_dt` 설정 경로, CFE DT 필터와 기본 GREY 수신 가능성을 검토한 **정적 분석**.
- [PR #3 — Phase 3 첫 결과](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/3): macOS arm64 C++20 코어 빌드 및 **8 MiB 저장 샘플** 재생. 1,557 *완성 출력 프레임*, 1,469,217 SDK 통계상의 이벤트, invalid/unknown/frame_gaps 0. 1/4/4093/1048576바이트 입력 청크 분할에서 carry 수정 후 프레임 출력 해시 일치. 원래 SDK는 4093바이트 청크에서 결과가 망가짐.
- 1,558 센서 Frame End 단어 수와 1,557 완성 출력 프레임 수는 별개 카운터다. 차이 1개를 임의로 손실이라고 판정하지 않는다.
- macOS C++20 빌드 ≠ RP5 네이티브 빌드. 저장 파일 재생 ≠ MIPI `DT=0x31` 실시간 수신. 현재까지 RP5 실제 수신 검증은 없음.
- 민수의 비공개 SDK 원본/샘플은 GitHub에 커밋하지 않는다. 필요시 승인된 별도 저장 위치에서 접근하거나 작업 중단 원인으로 기록한다.

## 1. 기술적으로 확인된 경로와 아직 가설인 부분

`drivers/sensor/s5krc1s_min.c`의 기본 `csi2_dt=0x31`와 `get_frame_desc`는 수신기로 DT를 알릴 수 있다. `drivers/rp1_cfe/csi2.c`는 descriptor를 읽어 채널 DT 필터를 설정한다. `drivers/rp1_cfe/cfe_fmts.h`의 GREY는 기본 RAW8(`0x2A`)이며 descriptor가 없으면 fallback 역시 RAW8이다.

**운영 중 모듈 옵션**은 `payload/etc/modprobe.d/s5krc1s_min.conf`에서 `csi2_dt=0x2a`이다. 운영 시작 스크립트는 센서 `0x3901=0x2A` 등 RAW2 관련 값을 명시적으로 쓴다. 수신 DT 파라미터와 **실제 센서가 보내는 DT**는 별개이며 서로 일치해야 한다. 모듈 값은 probe 시 드라이버 구조체로 복사되므로 단순 sysfs parameter 쓰기가 실행 중 상태에 반영된다고 가정하지 않는다.

`GREY/Y8`은 바이트 저장 컨테이너 후보일 뿐, `0x31` 지원이나 손실 없는 DMA를 보증하지 않는다. 실제로는 FS/FE, 패킷 Word Count, DMA geometry, stride, `bytesused`, `sequence`, CSI CRC/ECC와 드롭을 측정해야 한다. **별도 프로세스는 물리적 센서/CSI 포트 격리가 아니다.** 기존 RAW2와 동시 실시간 테스트를 시도하지 않는다.

## 긴급 안전 차단 — RAW2 rollback 경로 오용 위험 (2026-10-21)

**상태: Phase C BLOCKED / RAW2 운영 중단 금지.** Codex의 Pi 조사에 따르면 기존 `raw2_production_rollback.sh`는 Event Packet에서 RAW2 운영 상태를 회복하는 스크립트가 아니라 RP1 override를 제거하고 서비스를 비활성화한 뒤 재부팅한다. 이 스크립트는 **복구 수단으로 실행·예약·재사용 금지**. 실제 Pi 상의 전체 스크립트 본문과 호출 관계는 읽기 전용으로 확인하고 증거를 남겨야 한다.

운영 `raw2_production_start.sh`는 시작 시 setfile 적용, RAW2 레지스터 설정, media graph 재설정, 프로세스 시작을 수행하며 `pending_first_boot_validation` 존재 시 기존 rollback 스크립트를 타이머로 예약할 수 있다. 따라서 `systemctl restart dvs-raw2-production`과 watchdog 스케줄링은 운영 환경에서 안전한 dry-run이 아니다.

**Phase B는 file/mock만으로 계속한다. Phase C preflight에서 다음 항목을 모두 검증하기 전에는 기존 운영 서비스를 정지하거나 센서/모듈/DT를 변경할 수 없다.**

1. 기존 rollback/validate/start/systemd/timer 호출 그래프와 `pending_first_boot_validation` 조건을 읽기 전용 확인한다. 특히 예상치 못한 reboot, disable, RP1 override 삭제 경로를 식별한다.
2. 운영 상태(서비스 활성화 여부, module·DT·override 파일/해시/옵션, I2C 설정, media graph, 정상 RAW2 시각 출력 및 수신·오류 지표)를 재현 가능한 방식으로 확보한다. 접근 제어나 영업상 비공개 설정은 공개 Git에 올리지 않는다.
3. **별도** `restore-to-current-RAW2` 스크립트/검증기를 작업 폴더에 설계한다. 프로덕션 스크립트는 수정/실행하지 않고, mock/fake 환경에서 상태 복원, 멱등성, 오류 처리, 실패 주입, SSH 단절, 타이머 충돌과 제한 시간 초과를 테스트한다.
4. 독립 watchdog이 금지된 기존 rollback을 호출하지 않으며, restore 검증에 실패할 경우 장비의 삭제/disable/reboot를 자동 실행하지 않음을 확인한다.
5. 모듈 설정과 센서 설정이 **실제 실행 상태에서** 일치하도록 하는 복구 절차를 문서화한다. 정적 코드 분석이나 무해한 dry-run 성공만으로 실제 복구 보증을 주장하지 않는다.
6. Gate B 통과, Gate C 모든 preflight, 자동 복구 준비의 충분한 검증, 운영 중단의 경계 조건이 충족되지 않으면 **STOP 후 PROGRESS에 위험·증거·미해결 항목을 기록**한다.

해당 정지 조건은 이전의 제한적 실험 승인보다 우선하며, Codex가 Phase B 개발을 완료하더라도 자동으로 해제되지 않는다. 준비된 복구 절차는 사용자가 명시한 기존 실험의 10초 × 최대 3회/운영 중단 15분 이내 제한을 그대로 따른다.

## 2. 권한 및 절대 제한

사용자가 현재 대화에서 제한적인 *첫 번째* RP5 실기 검증의 자동 진행을 요청했다. 아래 조건 내에서 불필요한 단계별 승인 질문 없이 진행하되, 이 문서는 별도 세션·다른 기기 또는 범위 확대에 대한 포괄적 권한으로 재해석하지 않는다. 접근통제/OS 권한을 우회하지 않는다.

- 신규 브랜치와 별도 실험 디렉터리를 사용. `main`에 직접 커밋하거나 RAW2 production 파일을 영구적으로 변경하지 않는다.
- 오프라인 빌드·샘플 테스트는 즉시 가능. 실기 시험은 **모든 preflight 체크를 만족한 경우에만**.
- 실기 한 회당 최대 10초 캡처, 총 3회 이내, 운영 중단 총 15분 이내. 시간을 초과할 우려가 보이면 중단 후 복구.
- 제한적으로 허용: 운영 서비스 일시 중단, **출처와 검증이 확인된** Event setfile 적용, 센서 송신 DT·기존 모듈의 수신 DT 설정, 필요한 경우 기존 모듈의 안전한 재바인드/재적재, 비파괴 10초 캡처와 Viewer 실행.
- 금지: 저장매체 포맷/데이터 삭제, bootloader/firmware flashing, 재부팅, 커널·DT/overlay 영구 설치, 미검증 레지스터 추측 적용, 보호되지 않은 운영 상태에서 실험, 원본 로그 및 RAW 데이터 삭제.
- 복구 불확실, SSH 불안정, 검증된 Event setfile 부재, 현재 커널/모듈이 백업된 버전과 불일치, watchdog 실패, 원본 영상 baseline 확보 실패 또는 기존 오류 증가 시 **실기 시작하지 않거나 즉시 복구**.
- 개인/비공개 SDK·setfile·샘플 원본·자격정보·내부 회로/레지스터 자료를 공개 PR에 올리지 않는다.

## 3. Phase A — Pi5 네이티브 빌드 및 독립 오프라인 검증

1. [PR #3](https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01/pull/3)의 `experiments/event-offline/` 재현 코드를 확인. 버전 및 SDK 파일 체크섬을 기록.
2. RP5로 **읽기 전용 환경 조사** 후, 별도 폴더에서 aarch64 C++20 네이티브 코어 빌드. 디바이스·센서·운영 서비스 불필요. SDK가 Pi에 없으면 원본 접근 경로를 확인할 것. 없는데도 성공했다고 보고하지 말 것.
3. 승인된 8 MiB 샘플의 체크섬·완성 프레임·이벤트·출력 해시 재현. 1, 4, 4093, 1 MiB 및 랜덤 분할에서 동일한 의미 카운터와 프레임 출력 해시 확인.
4. carry 0~3바이트 보관, discontinuity 이후 partial word 상태/파서 context 리셋, EOF의 불완전 단어 명시 카운팅 구현 및 테스트.
5. 손상 단어, 잘린 EOF/Frame End, frame counter 255→0, timestamp wrap, CID0/1 분리, 좌표 초과, 재동기화 테스트. 기존 샘플 0오류로 전체 프로토콜이 입증되었다고 오인하지 말 것.
6. 완료 증거: 빌드 명령·컴파일러/OS/커널, 테스트 명령·코드, sample hash, 출력 hash, 프레임·이벤트·오류 수, 실패 케이스.

**Gate A**: native build 및 deterministic split invariance에 실패하면 실시간 수신 이전에 원인 분석. 성급하게 센서 모드 변경 금지.

## 4. Phase B — 실험 전용 V4L2 수신 및 계측 구조

1. GREY/Y8 협상 검증 코드, `bytesused`, `sequence`, stride/sizeimage, `DQBUF`/재큐잉 시간, V4L2 오류 통계 작성. 장치는 운영 중인 상태에서 강제로 STREAMON하지 말 것.
2. V4L2 수신 스레드는 짧게 데이터를 복사/전달한 뒤 QBUF, bounded queue와 독립 decoding thread 및 optional async writer/Viewer를 사용.
3. 파서 상태는 입력 buffer 경계 전체에서 지속, discontinuity 시 명시적 리셋. 4-byte alignment를 수신 버퍼마다 가정하지 말 것.
4. 960×720 Viewer는 이벤트 좌표를 표시하는 레이어이며 8192×128 등의 V4L2 DMA 바이트 기하와 구분.
5. 정상/오류 지표: V4L2 buffers/s 및 sequence gaps, CSI FS/FE/CRC/ECC, 센서 Frame End/count/gaps, event/s 및 CID, invalid coordinate, byte stream MB/s, CPU usage, queue occupancy/high-water/drops, bytesused/sized image. `0 x losses`는 관측한 범위에만 한정.
6. 실제 디바이스 대신 파일 또는 mock producer로 검증하고 결과를 저장.

**Gate B**: 확실한 장치 선택·메모리 안전·bounded queue·계측 및 종료 시 resource cleanup 없이는 Phase C 금지.

## 5. Phase C — 센서 DT 0x31 최초 수신 실기 시험

**시작하기 전에 매 조건을 결과와 함께 체크:**
- [ ] 테스트 장비·접속/복구 권한 및 현재 서비스 확인. SSH 접속이 불안정하지 않음.
- [ ] 실제 운영 kernel, `rp1_cfe`/`s5krc1s_min` 모듈 경로/해시/파라미터, overlay/DT, media graph, V4L2 캡처 형식, 시스템 서비스 상태를 **읽기 전용** 백업.
- [ ] 센서 I2C 레지스터 상태·정상 RAW2 이미지·데이터율·오류 카운터 baseline 확보. debugfs 오류 카운터는 read-to-clear 동작 확인 전 읽지 않음.
- [ ] 신뢰할 수 있는 Event setfile과 운영 RAW2 override 간 차이, 링크 주파수/레인, DT, Word Count, packet count, V4L2 geometry 검토.
- [ ] 원상복구에 필요한 설정/바이너리·모듈과 복구 명령을 검증. watchdog을 독립 예약하고 dry-run·종료 시나리오 확인. **원격 연결만 믿지 말 것.**
- [ ] 서비스 watchdog/자동 재시작과 실험의 충돌 확인. 운영 서비스 재시작 시 센서에 쓰는 RAW2 설정을 알고 있어야 함.
- [ ] 다운타임 15분 이내의 제한을 확실히 지킬 수 있음.

위 전제 중 하나라도 실패하면 STOP: **운영 서비스 변경 없이 보고**.

통과 시에만 순서대로 작업:
1. 사전 등록된 복구 watchdog이 살아 있는지 확인.
2. RAW2 운영 서비스를 정지(필수 시간 기록). 변경 전 상태 보존.
3. 사전에 승인된 Event 송신 설정 및 수신 DT `0x31`을 적용. 드라이버 `get_frame_desc` 수신 DT를 실제 재바인드/probe로 검증. 검증되지 않은 전역 `cfe_fmts.h` 수정·영구 설치를 하지 않음.
4. `GREY` byte container와 매칭되는 패킷 기하를 검증 후 짧은 수신, 최대 10초 × 3회.
5. 원시 바이트 일부·`bytesused`·timestamp·buffer seq·CSI CRC/ECC·sensor frame gaps·decode output·CPU·queue·Viewer 영상을 기록. SENSOR Frame End / CSI FE / V4L2 completed buffer를 다른 카운터로 집계.
6. 수신 실패, geometry mismatch, CRC 상승, watchdog failure, 유효 좌표 이상 또는 시간 초과 시 더 밀어붙이지 않고 원상복구.

**Gate C**: 정해진 10초 시험에서 실제 이벤트가 수신·디코딩·검증되었는지 수치로 판정. 성공 또는 실패에 관계없이 복구를 먼저 완료한다.

## 6. Phase D — 복구 및 종료

1. 이벤트 수신/Viewer 중단, 장치 close, 임시 프로세스/모듈 상태 확인.
2. 백업된 초기화 절차와 설정을 정확히 사용해 DT=0x2A RAW2로 복원. 운영 스크립트의 레지스터 쓰기·media graph reconfigure를 고려.
3. 원래 RAW2 서비스를 재개하고 정상 영상/프레임 수신·오류 통계·서비스 활성화 및 로그 확인. 원본 baseline과 비교.
4. 복구 검증에 성공한 경우에만 예약 watchdog 해제. 실패 시 감추지 말고 사용자에게 즉시 알려 추가 위험 명령 실행을 중단.
5. 마지막으로 코드/테스트/결과를 실험 브랜치에 커밋하고 별도 PR로 제출. 비공개 원문은 제외.

**Done**: RP5 native build 결과 + DT0x31 수신 성공/실패의 실측 근거 + RAW2 production 원상복구 증거가 모두 남아 있어야 한다.

## 7. 재개와 기록 규칙

새로운 Codex 작업이 시작될 때:
```
git status --short
cat AGENTS.md
cat docs/event-dt31/RP5_EVENT_RUNBOOK_KO.md
cat docs/event-dt31/PROGRESS.md
```

단, 이 문서가 현재 체크아웃 브랜치에 없으면 먼저 GitHub의 문서 PR에서 내용을 확인해야 한다. 다른 작업 브랜치의 문서를 자동으로 읽는다고 가정하지 않는다.

**단계마다** `PROGRESS.md`를 갱신: 현재 phase, 확인된 장비와 브랜치/커밋, 수행한 명령·로그, 수치, 주의/블로커, 다음 명령과 롤백 여부. 임의의 테스트 통과 추측이나 PR 녹색 표시만으로 상태를 통과로 바꾸지 말 것.


## 8. 2026-10-21 오프라인 restore 설계 검증 결과 / 현재 허용 범위

**Phase C = BLOCKED. 이 절은 과거 §2의 제한적 실기 허용보다 우선한다. 현재는 운영 서비스/센서/I2C/모듈/DT/media graph 변경을 하지 않는다.** 기존 `raw2_production_rollback.sh`를 실행·예약·간접 호출하지 않으며 start/validate/installer도 dry-run 도구로 사용하지 않는다. engine --device 경로는 코드에서도 PHASE_C_BLOCKED로 차단했다.

- [상세 복구 계획·호출 그래프·사전 점검](./RESTORE_PLAN_KO.md): 실제 Pi 파일·모듈·설정 hash 및 pending/watchdog 관측, destructive firstboot 경로, timer/restart race를 기록했다.
- 별도 `experiments/event-restore/restore_current_raw2.py`는 **dry-run/mock 전용**이며 실제 backend가 없다. `--dry-run`은 계획 JSON과 hardware-blocked exit2를 반환한다. `--mock-worker`는 OS temp sentinel fixture만 처리한다. 기존 rollback/start를 수정하거나 호출하지 않는다.
- Phase B adapter mock22건(Pi ASan/UBSan) 및 restore 실패 주입24건(로컬/Pi) 통과. 저장 샘플/native/Viewer의 기존 통과 결과는 보존. 성공으로 보고할 수 있는 범위는 이 파일/mock 시험뿐이다.
- SSH 단절은 mock client exit + 독립 session worker로 모사했으며 실제 SSH/logind/systemd watchdog 생존 시험이 아니다. mock watchdog flag 유지가 실제 watchdog 가동 증명은 아니다.
- 향후 live backend·현재 RAW2 private baseline·safe startup/firstboot race·실제 watchdog·실기 복구 검증이 모두 해결되고 운영 변경이 명시적으로 승인되기 전에는 실기 재시도/서비스 재시작을 하지 않는다. 현재 pending absent와 expiry inactive는 순간 관측이며 미래 start 안전 보장이 아니다.


## 9. Issue #7 readiness 결과 — 2026-10-22 / NO-GO

최신 지침의 허용 범위에서 [readiness 보고서](./READINESS_20261022_KO.md)와 [private bundle/receiver binding 설계](./PRIVATE_BUNDLE_SPEC_KO.md)를 작성했다. 신규 synthetic startup/bundle/proc-watchdog33건, 실제 **marker-only 격리 systemd unit5건**과 시험소유 SSH client 종료/cgroup 생존, C++ fileguard7건/engine guard6건을 검증했다. 기존17/22/24건 증거는 보존한다.

실제 unit은 새 rp5-dvs-rdy-*에 한정하며 ProtectSystem/Home, PrivateDevices/Network, NoNewPrivileges, 비특권 사용자/자기tmp만 쓰기, resource/runtime 제한이 적용된다. 기존 firstboot/camera watchdog과 RAW2 서비스는 호출하지 않는다. deadline 동작은 NOOP alert marker이고 실제 복구 backend가 아니다. **marker-only 독립 실행 PASS는 실기 복구 또는 모든 SSH/logind 장애 검증 PASS가 아니다.**

파일 입력도 ext-family/tmpfs의 pinned regular inode로 제한해 --file 특수/virtual file 우회를 거부한다. --device hard-block과 production_ready=false를 유지한다. 실제 production unit/start 통합·현재 sensor readback/영상/CSI·private snapshot·runtime DT re-probe·hardware backend·복구와 watchdog 연동·GO sign-off가 모두 남아 있으므로 Phase C HARD BLOCKED를 해제하지 않는다. 현재 단계에서 RAW2 운영 환경 변경은 금지다.
