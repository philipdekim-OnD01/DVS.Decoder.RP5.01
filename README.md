# DVS.Decoder.RP5.01

Samsung S5KRC1S DVS를 Raspberry Pi 5 CAM0에서 읽고 RAW2를 디코딩하여 HDMI(ffplay + 우측 설정 패널)와 웹으로 표시하는 **2026-10-12 동작 상태 백업 / 일괄 설치 패키지**입니다.

## 지원 환경

- Raspberry Pi 5, aarch64, Debian 13.2 기반 Raspberry Pi OS 데스크톱
- **커널 `6.12.47+rpt-rpi-2712` 전용**. 다른 커널에서는 설치를 거부합니다. 다른 커널 지원 및 DKMS 자동 재빌드는 제공하지 않습니다.
- 사용자 **`philip`, UID 1000, 홈 `/home/philip`**, Wayland 데스크톱 + Xwayland `DISPLAY=:0`
- S5KRC1S CAM0 4-lane, I2C bus 10 / address `0x10`, link frequency 625 MHz
- 설치 시 인터넷(apt/PyPI) 필요. 암호나 사용자 계정은 패키지에 포함되지 않습니다.

## 한 번에 설치

위 환경이 준비된 Pi에서 실행합니다. 기존 DVS 관련 파일은 `/var/backups/dvs/날짜-PID/`에 먼저 보관합니다.

```bash
git clone https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01.git
cd DVS.Decoder.RP5.01
sudo ./install.sh
sudo reboot
```

또는 Releases의 `dvs-rp5-2026.10.12.tar.gz`와 `SHA256SUMS`를 내려받아 `sha256sum -c SHA256SUMS`, 압축 해제 후 `sudo ./install.sh`를 실행합니다.

설치는 의존성, 드라이버 2개, 오버레이, 센서 setfile, 디코더, Python 환경, 웹/HDMI 앱 및 systemd 서비스를 함께 설치합니다. 커널을 자동 변경하거나 재부팅하지 않습니다. 설치 완료 시 기존 앱은 중지 상태이며 재부팅 후 자동 실행됩니다. apt 패키지 설치와 video/render/i2c 그룹 추가는 복원 시 제거하지 않습니다.

재부팅 후 `philip` 데스크톱에 로그인하세요. 무인 부팅은 OS에서 해당 사용자의 데스크톱 자동 로그인을 설정해야 합니다. 이 버전은 데스크톱 세션이 필요한 현재 동작 상태를 그대로 복원합니다.

```bash
sudo systemctl status dvs-raw2-production.service
sudo systemctl restart dvs-raw2-production.service
```

- 웹: `http://<Pi-IP>:8082/`, WebSocket `8765`
- 실행 파일: `/home/philip/dvs_raw2_production/raw2_producer`
- 통합 실행 스크립트: `/home/philip/dvs_raw2_production/raw2_production_start.sh`
- 로컬 설정 패널: 같은 폴더의 `hdmi_controls.py`
- 로그: `/home/philip/dvs_raw2_production/logs/`
- 레지스터 제어 서버에는 인증이 없으므로 신뢰하는 로컬 네트워크용입니다.

서비스가 센서 초기화와 웹/로컬 앱을 함께 관리합니다. 디코더 바이너리만 단독 실행하면 초기화와 IPC 서버가 준비되지 않습니다.

## 사전 검사 / 복원

```bash
sudo ./install.sh --check
# 실제 시스템에 설치하지 않고 payload 파일만 새 디렉터리에 풀기
./install.sh --stage-root /tmp/dvs-stage
# 설치 시 출력된 정확한 백업 경로 사용
sudo ./install.sh --restore /var/backups/dvs/<날짜-PID>
sudo reboot
```

복원은 해당 설치 직전의 파일·가상환경·부팅 설정·서비스 상태를 되돌립니다. 커널 모듈 적용에는 재부팅이 필요합니다. 백업 이후 별도로 수정한 대상 파일은 그 백업 시점으로 돌아갑니다.

## 포함 내용

- `payload/`: 장비에서 추출한 실제 설치 경로 기준 파일, 동작 확인된 바이너리와 소스
- `drivers/`: 센서 드라이버, 수정 RP1 CFE 및 CAM0 오버레이 소스
- `SNAPSHOT_SHA256SUMS`: 원본 스냅샷 파일별 SHA-256
- `metadata/`: 백업 당시 플랫폼과 성능 측정 한 시점
- `scripts/`, `tests/`: 설치/복원, 분리된 빌드 및 회귀 검사

센서 매뉴얼 PDF, 영상 캡처, 비밀번호, 전체 OS/사용자 홈은 포함하지 않습니다. 이 패키지는 SD 카드 전체 이미지가 아닌 DVS 소프트웨어 백업입니다. 원본 파일은 `payload/`에 보존하며 설치 도구는 별도로 제공합니다.

## 소스 빌드 및 검사

같은 커널의 Pi에서 헤더와 컴파일러가 필요합니다. 결과는 `build/`에만 생성하며 실행 중인 드라이버를 교체하지 않습니다.

```bash
sudo apt-get install build-essential linux-headers-$(uname -r) device-tree-compiler python3-numpy
./scripts/build.sh
python3 -m unittest discover -s tests -p 'test_installer.py' -v
```

새로 빌드한 바이너리는 자동으로 payload를 덮어쓰지 않습니다. 릴리스에 반영하려면 명시적으로 교체하고 스냅샷 체크섬을 다시 생성해야 합니다.

## 현재 성능과 검증 범위

손 윤곽과 반응 개선을 사용자 실기 테스트로 확인한 설정입니다. 앞선 6회 측정 평균 캡처 약 **946회/초**, 새 영상 약 **59회/초**이며 상황에 따라 변합니다. `Delta_10_2000FPS.txt`는 센서 설정 이름으로, 실제 2,000회/초 캡처 달성을 의미하지 않습니다. 누적 정렬 오류 약 1.35%가 관찰되었으며 해당 입력은 버립니다.

현재 Pi에서 두 드라이버·디코더·오버레이의 소스 빌드, 디코더/표면 렌더링 회귀 검사 및 설치 사전 검사를 수행했습니다. 설치 파일의 스테이징과 백업/복원 검사를 수행했으며, 별도의 새 SD 카드에서 전체 설치 후 부팅 테스트는 수행하지 않았습니다. 실행 중인 장비는 이 패키지 제작 과정에서 재설치하거나 재부팅하지 않았습니다.

자세한 설정과 측정은 [최적화 보고서](payload/home/philip/dvs_raw2_production/OPTIMIZATION_REPORT.md)를 참고하세요.

## 저장된 RAW 원본 재생

프레임을 합치거나 건너뛰지 않는 [RAW 재생기](player/README.md)를 추가했습니다. Python 표준 라이브러리와 브라우저만 사용합니다.

```bash
python3 player/raw_player.py /파일경로/mipi-raw2-10s.dvsraw.gz
```
