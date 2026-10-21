# Phase C 복구 preflight — BLOCKED (2026-10-21)

업데이트23:14 KST: 별도 restore dry-run/mock 후보와 실패시험24건은 완료했다. 실제 backend·복구/watchdog 검증은 여전히 미완료다. [현재 상세 설계](./RESTORE_PLAN_KO.md)를 참조한다. 아래 최초 STOP 근거는 보존한다.

Phase A native17건 및 Phase B native file/mock/ASan/UBSan 검증 후, 실기 시작 조건을 통과하지 못했다. 실기 시도0회, Production stop0회, downtime0초. **DT0x31 수신과 RAW2 복구 시험은 미실행**이다. 서비스가 계속 정상 가동한 관측과 실제 모드 전환 후 복구 성공은 구분한다.

## 실제 확인한 중단 사유

Pi의 `/home/philip/dvs_raw2_production/raw2_production_rollback.sh`는 현재 RAW2로 돌아오는 절차가 아니다. 읽기 전용으로 확인한 내용에 따르면 서비스 정지/비활성화, 설치 센서 모듈 교체, 현재 RP1 override·modprobe 설정 삭제, depmod, `REFERENCE_B3_RESTORE_REBOOT_PENDING` 기록 및 `systemctl reboot --no-block`를 수행한다. 현재 승인 범위의 무재부팅·운영 환경 보존 조건에 맞지 않는다. 이 스크립트와 validate 스크립트는 **실행하지 않았다**.

확인 해시:

- rollback SHA256 `6f45ec60a21e573226fcf403285c23af28e7e30b80e0156cd37b8c71a7f52661`
- validate SHA256 `795a8d880deb03ae793b27489263e25e995254ab6cd199cfdec660218be08e95`

`validate.sh`는 센서 I2C 읽기 외에도 marker 삭제와 timer 정지를 포함하므로 단순 무부작용 점검 도구로 실행하지 않는다. 파일 존재만으로 현재 RAW2 복구 검증을 통과시킬 수 없다.

Runbook §2의 “복구 불확실 … 실기 시작하지 않거나 즉시 복구”와 §5의 “위 전제 중 하나라도 실패하면 STOP: 운영 서비스 변경 없이 보고”를 적용했다. 새 rollback을 추측해서 바로 실행하거나 기존 스크립트를 수정하지 않았다.

## 체크리스트 상태

| 조건 | 관측/판정 |
|---|---|
| SSH/실제 환경 | 읽기 전용 반복 접속 성공; kernel6.12.47, GCC14.2 |
| 현재 모듈 파일 hash | 보관된 rp1/sensor hash와 일치; DT parameter42/link625MHz |
| 서비스 유지 | MainPID683775/NRestarts0/active; 마지막 2초 sequence107291681→107293804 |
| V4L2 오류 | dequeue/buffer/sequence-gap 각각0; CSI debugfs는 읽지 않음 |
| 현재 RAW2 정상 영상 baseline | web/HDMI fps telemetry만 확인; 실제 영상 baseline 확보 미완료 |
| 센서/DT/media/현재 상태 전체 백업 | 완료하지 않음; 센서 register I2C 명령 없음 |
| 검증된 Event setfile + geometry | 아직 확정/검증하지 않음; RAW2와 동일하다고 추정하지 않음 |
| 현재 상태용 무재부팅 복구 | **FAIL: 기존 rollback이 현재 목적과 불일치** |
| 독립 watchdog dry-run/종료 검증 | 미실행/미통과 |
| 실기 캡처/복구 | 실행하지 않음; D gate 완료 아님 |

최종 상태 증거는 `evidence/raw2-preserved-20261021.json`이다. 오류0은 해당 서비스 지표와 관측 구간에 한정하며 CSI error-free나 RAW2 boundary 문제 해결을 뜻하지 않는다.

## 재개에 필요한 구체 작업

먼저 현재 RAW2 모듈/DT/서비스/미디어/송신 설정을 원상복원하는 **실험 전용 무재부팅 복구안**을 별도로 작성·검토해야 한다. 센서 수신 DT가 probe 시 복사되는 구조와 현재 동작 모듈을 재바인드/재적재할 때의 복원을 포함하고, 기존 reference-B3 rollback을 호출해서는 안 된다. 이 단계의 새 위험 동작은 현재 STOP을 해제한 뒤 승인 범위 안에서 검증해야 한다.

이후 운영 상태를 바꾸지 않는 dry-run에서 필요한 파일·hash·root 권한·명령 경로를 점검하고, 무해한 marker만 쓰는 독립 watchdog의 발화/취소를 입증해야 한다. 실제 모드 변경 전 정상 영상·데이터율·CSI 오류 baseline과 Event setfile/geometry/DT binding을 확정한다. 모든 preflight가 PASS인 경우에만 10초×최대3회/총 downtime15분 제한의 실기와 RAW2 복구 검증을 진행한다.
