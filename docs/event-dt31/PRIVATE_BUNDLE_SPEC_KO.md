# Private restore bundle 및 receiver DT binding 설계 — 미적용

2026-10-22. 실제 비공개 복원 bundle은 아직 생성·봉인·실기 검증하지 않았다. 아래는 격리 시험으로 보강한 설계다. 공개 Git에는 setfile/SDK/실제 register dump/원시 영상/자격정보를 넣지 않는다.

## 신뢰 경계와 snapshot 구성

- private 저장소에 capture-id별 새 디렉터리를 만들고, 승인된 별도 위치에 root manifest digest를 고정한다. 같은 디렉터리에 있는 자기서명 digest만 신뢰하지 않는다. 암호화된 별도 복사본 또는 쓰기불가 snapshot/WORM 계층과 독립 검토가 필요하며, 이번에는 어떤 저장매체·권한·운영 파일도 변경하지 않았다.
- kernel/boot-id/장비·sensor fwnode·media endpoint identity, capture 시간 범위, 현재 module 경로/hash/loaded srcversion/모듈 파라미터, boot config/DTBO/live FDT identity를 포함한다. loaded srcversion 일치는 파일 hash보다 보강된 관측이나 실행 중 get_frame_desc의 DT 증명 자체는 아니다.
- 생산 binary/server/Python·probe·setfile·profile 및 RAW2 override 순서, systemd unit와 **모든 개별 drop-in**, service active/enabled/Restart 정책, pending/timer/watchdog 상태를 파일별 hash로 보존한다. 복구 때 현재 운영 파일을 삭제하거나 다른 버전으로 교체하는 것을 기본 전략으로 삼지 않는다.
- media graph/format/VC/수신 DT/Word Count/packet count/stride/sizeimage와 실제 정상 이미지·지표·CSI 오류 baseline을 연결한다. 현재 live sensor readback과 정상 시각/CSI baseline은 **NOT TESTED**이며 저장된12행으로 대체하지 않는다. I2C readback은 별도 위험 평가·승인 절차에서만 수행한다.
- private register manifest는 주소/값/폭·수신 시점·sensor identity·출처·검증 상태를 기록하고 중복·잘린 행·범위 밖 값·예상 주소 누락을 거부한다. 공개 결과는 row 수·hash·검증 상태만 남긴다.

## 무결성과 허용 실행

`bundle_startup.py`는 합성 bundle에 대해 외부 root SHA pin, 엄격한 schema/role 집합, 상대 경로, descriptor-relative O_NOFOLLOW, bounded regular-file read, file hash 및 saved12행 형식/DT·geometry를 검증한다. stage마다 재확인하며 marker/timer 충돌·파일 변경 시 중단한다. manifest에 shell command/legacy script/live proof를 주입하면 거부한다. 이전 성공 JSON도 검사 생략 권한이 아니다.

현재 prototype의 role fixture(예: unit_dropins)는 합성 단일 payload다. 실제 private bundle schema는 모든 하위 파일을 개별 봉인하고 복원 dependency closure를 검증하도록 확장해야 한다. readonly chmod만으로 root-proof immutable이라고 부르지 않는다. 외부 신뢰 pin·보관 매체·서명/접근 관리의 실배치는 미검증이다.

## Safe startup 통합 조건

격리 startup은 기존 start/installer/validate/rollback을 호출하는 경로가 없으므로 marker가 나타나도 destructive firstboot timer를 예약할 수 없다. 이 구조와 marker flip/concurrent installer/restart 실패를 mock에서 검증했다. 그러나 현재 production unit은 여전히 기존 start를 사용한다. **새 격리 구조를 운영 unit에 통합하거나 marker를 차단/삭제하는 변경은 하지 않았다.**

향후 하드웨어 backend는 고정된 최소 primitive만 지원해야 하며 임의 명령 문자열을 실행하지 않아야 한다. audited initializer/검증된 binary 실행, 장치 소유권·종료, 후속 RAW2 health 검증을 분리하고 legacy timer의 생성 권한/호출 자체를 제거한 non-production integration을 먼저 검증한다. 현재 start 직전 marker 확인 한 번 또는 별도 lock만으로 비협조적인 기존 installer와의 race가 해결됐다고 주장하지 않는다. production service로 되돌리는 handover도 별도 검토 대상이다.

## Module re-probe / get_frame_desc 계획

소스 근거: sensor `s5k->csi2_dt = csi2_dt`는 probe 때 복사되고, `get_frame_desc`는 그 instance 필드를 반환한다. CFE는 descriptor의 VC/DT를 채널 필터에 넣는다. 따라서 sysfs parameter42라는 관측만으로 active instance와 CSI 필터가 이미42라고 보장할 수 없다.

non-production 하드웨어에서 다음 증거가 필요하다:

1. 동일 kernel/module 파일/hash·loaded identity 및 실제 sensor subdev/fwnode/pad/VC·receiver 연결을 확정한다. 파일 source와 현재 실행 동작의 provenance도 구분한다.
2. 승인된 실험 pipeline을 quiesce하고 FD/DMA/reference를 정리하는 절차를 검증한다. 지금 production은 건드리지 않는다. CFE의 refcount가 남아 있는데 무리하게 unload하거나 force unbind하지 않는다.
3. persistent module/config/DT 변경 없이 허용된 runtime 재probe 방식이 baseline DT를 실제 sensor instance에 복사하는지 검증한다. 정확한 안전한 명령/backend는 아직 미구현이다.
4. `get_frame_desc` 실제 호출/결과의 VC/DT와 CFE 수신 필터를 승인된 진단 수단으로 확인한다. 존재하지 않는 userspace ioctl/도구 옵션을 가정하지 않는다. 필요 진단이 kernel 변경을 요구하면 현재 범위 밖이므로 중단한다.
5. sensor 송신 profile과 수신 DT 일치, 실제 packet geometry·byte order·bytesused/CSI/error/영상 복원까지 검증한다. descriptor/parameter만 맞는 경우를 실제 복구 성공으로 취급하지 않는다.

이 계획은 실행 명령이나 GO 승인이 아니다. 실패 시 legacy rollback·서비스 disable·reboot·override 삭제 fallback은 금지하며 증거 보존/수동 보고로 끝낸다.
