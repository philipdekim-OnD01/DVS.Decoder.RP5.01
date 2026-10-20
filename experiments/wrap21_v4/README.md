# S5KRC1S / Raspberry Pi 5 — RAW2 Wrap21 v4 (experimental)

이 폴더는 **2026-10-18 정상 운영 스냅샷**을 훼손하지 않고 1.239% 버퍼 경계 정렬 오판을 재현·수정한 **2026-10-20 검증 코드**입니다.

### 구성
- `raw2_producer_wrap21.cpp`: v4 최소 수정이 통합된 **실제 Producer C++ 소스**, 기본값은 기존 로직
- `raw2_wrap21.hpp`: strict 21-block circular-wrap 복구 함수
- `test_wrap21.cpp`: Synthetic 13케이스 + DVSRAW01 10초 전체 재생 검사
- `build_offline.sh`: 본 저장소의 기존 `dvs_renderer.cpp`와 드라이버 스냅샷은 바꾸지 않고 별도 컴파일
- `validation_20261020.md`: 오프라인·실시간 A/B 측정 수치와 한계

**포함된 기존 구성:** `../../drivers/rp1_cfe`(RP1 CSI/CFE), `../../drivers/sensor`(S5KRC1S), `../../drivers/overlay`(CAM0 Device Tree), `../../payload/home/philip/dvs_raw2_production`(기존 RAW2 Producer/HDMI/서버), `../../install.sh`(기존 2026-10-18 배포 전용).

### 컴파일·오프라인 검증 (Pi 5에서 기존 서비스 중단 없음)
```bash
git clone --branch wrap21-v4-20261020 https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01.git
cd DVS.Decoder.RP5.01
bash experiments/wrap21_v4/build_offline.sh /home/philip/mipi-raw2-10s.dvsraw.gz
```

위 명령은 `build/wrap21-v4/raw2_producer_wrap21`에 실험 바이너리를 생성합니다. RAW 파일을 지정하지 않으면 컴파일 + Synthetic 테스트만 수행합니다.

**주의:** 실행 파일을 생성해도 기본 센서·`/dev/video0`·systemd·웹/HDMI를 변경하지 않습니다. 기존 `install.sh`는 **옛 운영본 설치 도구**로 v4 자동 적용 기능이 아닙니다. 실시간 시험에는 별도의 테스트 전용 IPC와 자동 복구가 필요하며, 운영 바이너리의 임의 덮어쓰기·동시 카메라 열기는 금지합니다.

### 결과 요약
- 10초 오프라인 16,140레코드: Wrap21 200건 복구, 남은 정렬 거부 0건, 기존 정상 15,940건 판정 변경 0.
- 20초 Pi5 Live A/B: Wrap21 303건 복구, 남은 정렬 거부 0건, 1,188프레임 수신, 기존 서비스 자동 복구 성공.
- 미해결: 물리 960컬럼/955블록 차이, 기타 Marker 이상, Embedded Frame Header 인증, H/W 노이즈; 10분/1시간 시험 미실시.

[상세 검증 보고서](validation_20261020.md)
