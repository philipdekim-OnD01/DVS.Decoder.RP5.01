# S5KRC1S Event Packet RP5 포팅 가능성 — Phase 1·2

2026-10-21 KST. 소스 정적 분석만 수행. 운영 Pi에 접속하거나 레지스터 읽기/쓰기, V4L2 open/STREAMON, 서비스 조작, 커널/DT 설치, 재부팅을 수행하지 않았다. C++ 빌드 및 오프라인 재생 구현·실행도 Phase 3 승인 전에는 수행하지 않았다.

## 결론

**보관된 커스텀 RP1 CFE 소스는 DT 0x31 선택 경로를 이미 갖고 있다. 기본 실험안에는 CFE 패치나 새 V4L2 FOURCC가 필요하지 않을 가능성이 높다. 실제 0x31 수신 성공은 미확인이다.**

센서 subdev는 Y8_1X8과 CSI-2 frame descriptor의 VC0/가변 DT를 별도로 제공한다. CFE는 descriptor의 DT를 6비트 채널 필터에 넣는다. 따라서 GREY는 메모리의 8비트 바이트 컨테이너로 사용하고 DT는 0x31로 선택할 수 있다. GREY를 고르는 것만으로 DT가 바뀌지는 않는다. descriptor가 없으면 포맷 표의 RAW8(0x2A)로 fallback한다.

같은 센서/CSI 포트를 RAW2와 Event 모드로 동시에 변경 없이 운용할 수 있다고 가정해서는 안 된다. 별도 디렉터리·프로세스만으로 하드웨어는 격리되지 않는다. Production 중단 금지 조건에서는 별도 Pi/센서/저장매체를 확보하는 것이 실기 시험의 선행 조건이다. 동일 장비의 모드 전환 시험은 별도 중단 승인 없이는 진행할 수 없다.

## 근거와 접근 범위

- 로컬 저장소: `philipdekim-OnD01/DVS.Decoder.RP5.01`. 분석 시작 HEAD `2c3b2f124d8f3ad3fb049bb207147c32adf60f3f`; 보고서 브랜치는 origin/main에서 분기하여 기존 분석 PR 변경을 포함하지 않는다.
- `metadata/platform.txt`: 2026-10-18 보관 환경은 Pi 5 Model B Rev 1.0, Debian 13.2, Linux `6.12.47+rpt-rpi-2712`, aarch64. 현재 가동 장비의 실시간 상태로 재확인한 값은 아니다.
- `metadata/source-provenance.json`: 설치 당시 소스와 실행 바이너리 소스 차이를 기록한다. canonical producer는 trace-shadow 소스이며, `metadata/installed-stale-producer.cpp`를 현재 실행 소스로 오인하지 않는다.
- 민수 패키지: `/Users/PhilipKim/Downloads/nrv-dvs-jetson-20261014.tar.gz` 접근 성공. SHA256 `3e7bc2c35d8860fda70879ced04dcea9edbc7ff7daa3f41dcc44c94b2b9946b6`. `/private/tmp/dvs-event-audit`에 분석용으로 풀었으며 스크립트는 실행하지 않았다. private SDK 원문과 샘플은 이 공개 가능 보고서에 복사하지 않는다.
- [Orin PR #1](https://github.com/philipdekim-OnD01/nrv-dvs-Orin01/pull/1) 접근 성공. PR의 처리량·큐 손실 수치는 모델이며 RP5 실측치가 아니다. PR이 기술한 8 MiB 샘플/1,558 프레임 등의 결과는 기존 보고값이며 이번에 재현한 결과가 아니다.

## 현재 RAW2 경로

`payload/etc/modprobe.d/s5krc1s_min.conf`는 `link_freq_hz=625000000 csi2_dt=0x2a`를 설정한다. 센서 소스 기본값은 0x31이지만 운영 옵션이 덮어쓴다. `dvs-raw2-production-rp1.conf`는 stride zero와 pack bytes를 켠다.

`payload/home/philip/dvs_raw2_production/raw2_production_start.sh`는 setfile을 적용한 뒤 RAW2 override를 쓴다: 3901=2A, 3902=40, 3903=0B, 3906=12, 3907=10, 3908=10, 391A=3C, 391B=00, 3260의 bit1 설정. 3915 등은 저장된 값을 복원한다. 이는 소스에 명시된 쓰기를 문서화한 것이며 현재 레지스터 덤프가 아니다. 기본 setfile의 8192-byte/127 payload 주석을 운영 override 이후의 패킷 기하로 그대로 쓰면 안 된다.

미디어 경로는 `s5krc1s_min → csi2 sink0 → source4 → rp1-cfe-csi2_ch0 → V4L2 → raw2_producer → IPC/viewer`. 미디어 버스는 Y8_1X8, 요청 캡처 크기는 8192×128이다. 이 크기는 DMA 컨테이너이며 960×720 센서 좌표와 구별한다. 운영 서비스 포트는 HTTP 8082/WS 8765. 시작 스크립트는 센서 쓰기와 media graph reset을 포함하므로 분석/실험 편의 목적으로 실행하면 안 된다.

## RP1 CFE 판정 근거

| 파일·심볼 | 소스에서 확인한 동작 | 의미 |
|---|---|---|
| `drivers/sensor/s5krc1s_min.c`, `s5krc1s_get_frame_desc` | CSI2, 단일 entry, Y8, BLOB/LEN_MAX, VC0, s5k->csi2_dt | 0x31 광고 경로가 이미 있음 |
| `drivers/rp1_cfe/csi2.c`, `csi2_get_vc_dt` | get_frame_desc 성공 시 entry DT 사용, 미지원 시 fallback | 기존 GREY 매핑과 수신 DT 분리 가능 |
| 같은 파일 `DT_MASK`, `csi2_start_channel` | GENMASK(12,7), set_field(ctrl,dt,DT_MASK) | 0x31이 필터 필드에 들어감; 하드웨어 처리 성공 증명은 아님 |
| `drivers/rp1_cfe/cfe_fmts.h` | GREY/Y8 depth8의 csi_dt=RAW8 | fallback만 사용하면 0x2A; 표 전체를 0x31로 바꾸지 않을 것 |
| `drivers/rp1_cfe/cfe.c` | CSI2_MODE_NORMAL, sizeimage/bytesperline로 DMA 예약 | remap/compressed/PiSP 경로를 피한 바이트 캡처 후보 |
| `csi2.c` | PACK_LINE, 옵션 PACK_BYTES, FS/FE_ACK IRQ, EOP_IS_EOL | packet/line/frame 및 stride 검증 필요 |

보관된 커스텀 드라이버에 대한 판정이며 모든 upstream 커널이나 현재 실행 모듈과 동일하다는 주장은 아니다. `V4L2_META_FMT_SENSOR_DATA`는 기존 embedded DT용 경로다. 이름만 보고 UD 0x31을 자동 수신한다고 가정하지 않는다.

실기에서 남은 질문: DT discard/CRC/ECC, FS/FE와 FE_ACK, 패킷 word count와 실제 유효 DMA 길이, stride/padding, short/timeout frame, 버퍼 overflow, byte order. payload 내부 Frame End와 CSI-2 FE와 V4L2 DQBUF 완료는 서로 다른 경계다. 특히 고정 sizeimage가 유효 payload 길이와 같다고 가정하지 말고 bytesused의 드라이버 산출 경로까지 검증해야 한다.

## 민수 SDK 분석과 분리 범위

패키지 내부 기준 경로는 `nrv-dvs-jetson/sdk/`이다. `src/decoder.cpp`는 4바이트 big-endian 배치 단어를 해석하고 CID별 Context와 frame-building 상태를 멤버로 유지한다. Timestamp(22bit ms reference + 0..999 us sub), Column(x/mo/8bit frame count/epoch), 두 8픽셀 Event Group, Frame End를 처리한다. 좌표는 960×720, 출력은 CID0이고 CID1 이벤트는 별도 통계다. 22bit reference wrap은 주기 계산에서 처리한다. timestamp_us 자체의 단조 증가 보장이 필요한 소비자는 wrap epoch 정책을 추가 검토해야 한다.

**경계 결함 후보:** Produce의 `for (i=0; i+4<=raw_.size(); i+=4)`는 1~3바이트 잔여를 다음 입력에 넘기지 않는다. 4바이트 정렬된 프레임 분할은 Context가 유지되지만 임의 바이트 분할은 안전하지 않다. 승인 후 0~3byte carry와 discontinuity 시 carry/context reset을 구현하고 분할 불변성을 검증해야 한다. EOF의 불완전 단어와 미완성 프레임도 카운터로 드러낼 것.

`src/nrv_dvs/decoder.cpp`는 공개 API 래퍼다. `src/stream.cpp`는 Linux V4L2 MMAP이며 8192×128 SRGGB8을 요청한다. Pi용 어댑터는 GREY/Y8 및 실제 협상 결과를 검증해야 한다. `src/device.cpp`의 tegra register-control 이름과 초기화·preset 쓰기 경로는 디코더에서 분리하여 사용하지 않는다. Jetson kernel/tegra-camera/boot/extlinux 코드는 RP5에 이식하지 않는다. `.cmake/architecture.cmake`는 Linux aarch64 제한이고 C++20이 필요하다. 현재 macOS 호스트에서 전체 SDK가 그대로 빌드된다고 볼 수 없다.

## 최소 변경안 — 미실행

1. 우선안: 기존 커스텀 CFE/센서 모듈을 사용 가능한지 확인 후 실험 장비에서만 DT=0x31 설정과 검증된 Event setfile을 적용한다. **초기 CFE 코드 수정 0개, DT 소스 수정 0개가 후보**다. 운영 modprobe 파일은 변경하지 않는다. 센서 DT 파라미터는 수신 필터 광고일 뿐 센서 송신 설정을 대신하지 않는다.
2. SDK 작업 후보: `sdk/src/decoder.cpp`(carry), decoder 내부 헤더(잔여 상태), 신규 isolated CMake target(플랫폼 독립 코어), 신규 RP5 V4L2 adapter, offline replay/tests, 960×720 viewer/metrics. 이는 원본 RAW2 디코더 수정과 별개다.
3. 필요할 때만 `drivers/rp1_cfe/csi2.c`/`cfe.c`의 byte packing·stride·completion/유효 길이 경로를 최소 수정한다. DMA 증거 없이 패치를 미리 확정하지 않는다. `cfe_fmts.h`의 글로벌 RAW8→0x31 변경은 제안하지 않는다.
4. `drivers/sensor/s5krc1s_min.c`는 현재 descriptor 경로로 충분한지 먼저 확인한다. instance별 설정이 필요한 경우에만 신규 실험용 드라이버/DT binding 설계를 검토한다. `drivers/overlay/s5krc1s-cam0-overlay.dts`의 400MHz와 운영 module option 625MHz 차이는 실기 link 검증 대상이며 임의로 수정하지 않는다.

센서 레지스터/DT/커널 변경과 설치는 이 보고서에서 승인 요청 대상으로 남긴다. 구체 Event 레지스터 diff는 승인된 센서 문서 및 RAW2 override와 대조해 확정해야 하므로 여기에는 실행 가능한 레지스터 쓰기 명령을 제공하지 않는다.

## 승인 후 검증·복구 절차

Phase 3의 첫 단계는 **로컬/격리 환경에서만** decoder 코어 빌드와 샘플 오프라인 재생이다. 현재 빌드 결과=미실행, 오프라인 검증 결과=미실행, RP5 처리량/CPU/수신 성공=미측정. 패키지 내 prebuilt 바이너리는 신규 빌드 증거가 아니다.

오프라인 acceptance: 동일 샘플을 1MiB/4byte/1byte/비정렬·무작위 chunk로 주어 출력 이벤트·프레임 hash와 전체 카운터가 일치해야 한다. truncated word/frame, invalid x/y/sub timestamp, CID 분리, timestamp wrap, frame-count 255→0, discontinuity 후 재동기화를 포함한다. SDK 원본과 수정 코어의 정렬 입력 결과도 비교한다. PR #1의 수치는 참고 baseline일 뿐 이번 통과 판정으로 쓰지 않는다.

실험 엔진 설계: capture thread는 MMAP 유효 데이터를 bounded queue에 소유권 이전/복사 후 QBUF; decode thread는 상태 유지 parser; viewer는 960×720 surface만 소비한다. 무제한 큐와 운영 서비스/장치의 동시 open은 금지한다. Event/s, buffers/s, CPU process/thread time, 큐 occupancy/high-water/drop, invalid/unknown/unsynced, frame gaps/discontinuities, CSI 오류와 sequence/bytesused를 기록한다. DQBUF 버퍼 수와 센서 프레임 수를 혼동하지 않는다.

실기 전 별도 승인: 시험 장비 식별, Production과의 물리적 격리, Event setfile diff, module/DT/boot 변경 목록, 백업 hash 및 복구 매체 확보. 먼저 현재 kernel/module/config/DT/서비스/센서 설정·정상 영상·counter baseline을 읽기 전용으로 확보한다. debugfs 파일은 read-to-clear 여부 확인 전 읽지 않는다. 이후 승인한 실험 장비에서만 짧은 수신→오프라인 대조→장시간·부하 시험 순으로 진행한다.

복구는 승인된 시험 장비에서 실험 프로세스를 종료하고 저장해 둔 모듈/DT/boot/설정과 정확한 센서 초기화 절차를 복원한 뒤 RAW2 정상 영상·커널·counter를 baseline과 비교한다. 필요 재부팅도 사전 승인 범위에 포함해야 한다. Production 장비는 이번 작업으로 바뀐 항목이 없으므로 복구 작업 자체를 실행하지 않는다.
