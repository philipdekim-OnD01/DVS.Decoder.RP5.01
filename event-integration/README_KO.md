# 별도 Event 센서 통합 빌드

사용자 요청: 기존 버전은 Git에 보존하고 별도 Event 구성을 개발한다. 기준 소스는
`4d832730f8c34a21ad38f14eb0d6840e8af9c7e5`, 보존 태그는
`codex/before-event-integration-20261027`이다. 원본 checkout은 clean 상태였으며 미커밋 변경은 없었다.
이 태그는 저장소 소스를 보존한다. 현재 Pi 센서·서비스·커널의 실제 상태를 백업했다는 뜻은 아니다.

## 재사용 경로

1. 센서 송신: 출처가 확인된 비공개 Event setfile 필요. 이 패키지는 레지스터를 생성하거나 적용하지 않는다.
2. 수신: 기존 `s5krc1s_min.c`의 `csi2_dt=0x31` → `get_frame_desc()` → RP1 CFE DT 필터.
3. 처리: 기존 `v4l2_capture.hpp` → queue → 민수 SDK의 `delta::Decoder` → 기존 Viewer.

새 decoder/driver를 복제하지 않고 고정된 기존 소스를 별도 출력 폴더로 staging해 빌드한다.
기존 `event-b`의 file-only 빌드는 그대로다. 새 빌드는 V4L2 adapter도 포함하여 컴파일하되
기존 engine의 `PHASE_C_BLOCKED`를 유지한다. 모듈 설치·로드, 서비스 조작, 센서 전환,
캡처 또는 디코더 실행을 자동으로 수행하지 않는다.

## 소스 준비와 네이티브 빌드

저장소 루트에서, 아직 없는 출력 폴더를 지정한다. 출력은 checkout 밖이어야 한다.

```sh
python3 event-integration/build.py --stage-only --output /tmp/event-integration-sources-UNIQUE
```

이 명령은 공개 source와 수신 설정 **예시** 및 hash manifest만 만든다. private SDK는 읽지 않는다.
Linux에서 승인된 로컬 민수 SDK와 실제 대상 커널의 준비된 build tree가 확보되면:

```sh
python3 event-integration/build.py --sdk /private/path/to/SDK --kernel-build /path/to/target/kernel/build --output /private/path/to/new-event-build
```

기존 `prepare_core.py`가 SDK의 별도 복사본에 기존 carry/EOF 패치를 적용한다.
engine과 센서 모듈을 출력 폴더에만 컴파일한다. `modules_install`, `insmod`, `modprobe`,
`systemctl`, I2C 또는 `/dev/video*` 실행 경로는 빌더에 없다. 출력 폴더는 SDK 원문과 바이너리를
포함하므로 Git에 추가하거나 외부에 전송하지 않는다. kernel build tree의 적합성과 기존
RP1 수신기 버전은 빌드 성공만으로 인증되지 않는다.

준비된 kernel tree의 `include/config/kernel.release`를 manifest에 기록한다. profile에
kernel release가 있으면 불일치 시 SDK 준비·컴파일 전에 거부한다. null이면 일치 상태는
UNKNOWN이다. build tree의 버전 일치도 실행 중 Pi 커널·모듈과의 일치를 보증하지 않는다.
SDK patch/파일 준비 또는 컴파일 실패 시 manifest에 FAILED와 실패 단계를 보존한다.

`profile.json`의 DT는 수신 의도이며 센서 TX 완료 증거가 아니다. setfile SHA, transport,
kernel release는 아직 null이다. transport에는 width/height/payload_bytes/stride/sizeimage/
virtual_channel을 기록한다. 960×720은 표시 좌표이며 DMA geometry로 사용하지 않는다.
필드의 모양·범위 검사 통과는 패킷 의미·padding·시간축 인증이 아니다. 모든 필드를 채우거나
빌드가 성공해도 `live_ready=false` 및 `sensor_tx_applied=false`는 유지한다.

## 검증 범위와 다음 작업

2026-10-27 실제 결과:

- 신규 packaging 테스트 10건 PASS, 별도 코드 검토 ACCEPT. 첫 시험에서 Python host 정보 수집의
  내부 subprocess 호출을 발견해 무실행 방식으로 수정했다. SDK 실패 기록과 커널 mismatch 검사를 보완했다.
- Mac에서 공개 소스 staging 완료. 민수 SDK를 사용하는 전체 통합 wrapper의 네이티브 빌드는 NOT RUN.
- 별도 Pi 임시 폴더에서 기존 공개 sensor source/Makefile만으로 **드라이버 모듈 컴파일 성공**.
  커널/vermagic은 `6.12.47+rpt-rpi-2712`, aarch64. [실행·해시·로그](evidence/rp5-driver-build-20261027.json).
  wrapper 전체 실행과 분리한 driver-only `make modules` 결과다. 설치·로드·센서 변경은 하지 않았다.
- 메타데이터 수집 첫 시도에서 `modinfo`가 SSH PATH에 없어 실패했다. 절대경로로 메타데이터만
  재수집했고 컴파일은 반복하지 않았다. 실패 이력을 evidence에 보존한다.
- RAW2 서비스는 전후 active/running, PID1715, NRestarts0으로 동일했다. 이 상태값은 영상 품질이나
  물리 CSI 무손실 검증이 아니다.
- 과거 Pi SDK 경로는 없고, 기록된 Mac SDK 경로에는 디렉터리만 있으며 필요한 source 파일이 없다.
  신규 SDK 전송·기존 RAW 재생은 수행하지 않았다.

`python3 event-integration/test_build.py`는 새 packaging의 입력 거부, 원본 바이트 보존,
덮어쓰기 방지, 실행 없는 staging만 검사한다. 기존 decoder/native17/8MiB 샘플은 재실행하지 않는다.
실제 SDK/engine 통합 빌드·센서 출력·CSI 수신·RAW2 복귀는 이 로컬 staging 시험으로 검증되지 않는다.

다음은 대상 Pi의 승인된 SDK 위치, 커널 build tree, 검증된 Event TX 설정 식별자를 연결하는 것이다.
공유 센서에서 A→B 전환은 Git 소스 보관만으로 복구가 보장되지 않는다. 기존 Issue #7의 실제
복귀 조건과 장비 전환 범위를 확인한 뒤 수행한다. RAW2 A UNTOUCHED / Phase C HARD BLOCKED.
