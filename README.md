# DVS.Decoder.RP5.01 — 최종 실행본 2026.10.18

## Wrap21 v4 실험 검증판 — 2026-10-20

**운영 배포가 아닌 별도 검증 브랜치:** 이 브랜치는 아래의 기존 `v2026.10.18-final` 드라이버·디코더·웹/HDMI 스냅샷을 유지하고, `experiments/wrap21_v4/`에 **Wrap21 정렬 오판 최소 수정**을 추가합니다. 현재 Pi의 기존 운영 서비스와 바이너리는 변경되지 않았습니다.

| 검증 | 입력 | Wrap21 복구 | 남은 정렬 거부 | 비고 |
|---|---:|---:|---:|---|
| 10초 RAW 오프라인 | 16,140 레코드 | **200건 / 200건** | **0건** | 기존 정상 15,940건 판정 변경 0 |
| Pi5 실시간 A/B 20초 | 22,474 버퍼 | **303건** | **0건** | 1,188프레임 수신, 57.993fps 출력, 기존 서비스 자동 복구 성공 |

**범위 한정:** 이 결과는 소프트웨어의 Wrap21 정렬 거부 복구에 관한 것입니다. **955/960컬럼 차이, 센서 실제 무손실, H/W 노이즈, 장시간 10분·1시간 안정성은 해결·검증되지 않았습니다.** H/W 신호 안정화는 별도 작업으로 분리합니다. 기본 Producer와 기존 설치 절차는 여전히 2026-10-18 운영본이며 v4가 자동 적용되지 않습니다.

**소스·컴파일·상세 결과:** [`experiments/wrap21_v4/`](experiments/wrap21_v4/README.md) · [상세 검증 보고서](experiments/wrap21_v4/validation_20261020.md)

---

**2026년 10월 18일 라즈베리에서 실제 동작 중인 S5KRC1S DVS 드라이버·RAW2 디코더·웹/HDMI 앱을 보존한 최종 스냅샷입니다.** 기존 10월 12일 백업에서 현재 실행 중인 10월 16일 디코더 및 화면·진단 설정으로 갱신했습니다.

## 실제 실행본과 소스

실행 중인 프로세스 `/proc/<PID>/exe`, 설치된 `raw2_producer`, trace/shadow 빌드 산출물의 SHA-256이 모두 같습니다.

```text
5c2a88249aca8c3e3af0e0c3ec6ad772cad902ef215bc531a635f9c7af16776b
```

장비의 `dvs_raw2_production/raw2_producer.cpp`는 이전 소스가 남아 있었습니다. 이 저장소의 같은 경로에는 **실행 바이너리와 일치하는 `raw2_producer_trace_shadow.cpp` 소스**를 넣었습니다. 설치된 이전 소스는 `metadata/installed-stale-producer.cpp`에 별도 보존했습니다. 출처와 파일별 해시는 `metadata/source-provenance.json`, 전체 스냅샷 무결성은 `SNAPSHOT_SHA256SUMS`로 확인할 수 있습니다.

현재 적용된 구성도 포함합니다.

- HDMI 표시: `mode=jetson`, `denoise=1`, `persistence_ms=50`
- 화면 설정 파일: `/home/philip/dvs_raw2_visual_candidate_20261016/viewer_settings.conf`
- systemd 추가 설정 4개: 화면 설정 경로, alignment audit 비활성, boundary shadow/histogram/trace 활성
- 센서·수정 RP1 CFE 드라이버, CAM0 오버레이, 센서 setfile, 초기화 및 손 윤곽 설정
- 웹/HDMI 앱, 현재 디코더 바이너리, 대응 소스·헤더·회귀 검사

설정 이름의 `candidate`와 `shadow`는 장비에 존재하는 경로를 그대로 보존한 것입니다. `shadow` 통계는 진단용이며 별도의 복원 디코더가 출력 영상을 대체한다는 뜻이 아닙니다.

## 지원 환경

- Raspberry Pi 5, aarch64, Debian 13 기반 Raspberry Pi OS 데스크톱
- **커널 `6.12.47+rpt-rpi-2712` 전용**. 다른 커널은 설치를 거부하며 DKMS 자동 재빌드는 제공하지 않습니다.
- 사용자 **`philip`, UID 1000, 홈 `/home/philip`**
- Wayland 데스크톱, Xwayland `DISPLAY=:0`, 해당 사용자의 데스크톱 로그인 필요
- S5KRC1S CAM0 4-lane, I2C bus 10 / address `0x10`, link frequency 625 MHz
- 설치 시 인터넷(apt/PyPI) 필요. 사용자 계정이나 비밀번호는 만들거나 포함하지 않습니다.

다른 Pi에도 위 환경과 센서 연결이 같아야 합니다. 모든 라즈베리 기종·커널에서 설치 즉시 동작하는 범용 패키지는 아닙니다.

## 설치

```bash
git clone https://github.com/philipdekim-OnD01/DVS.Decoder.RP5.01.git
cd DVS.Decoder.RP5.01
sudo ./install.sh --check
sudo ./install.sh
sudo reboot
```

또는 GitHub Releases에서 `dvs-rp5-2026.10.18.tar.gz`와 `SHA256SUMS`를 받습니다.

```bash
sha256sum -c SHA256SUMS
tar xzf dvs-rp5-2026.10.18.tar.gz
cd dvs-rp5-2026.10.18
sudo ./install.sh --check
sudo ./install.sh
sudo reboot
```

설치는 의존성·드라이버 2개·오버레이·센서 설정·디코더·Python 환경·웹/HDMI 앱·systemd 서비스와 추가 설정을 함께 배치합니다. 기존 대상 파일과 서비스 추가 설정 디렉터리를 `/var/backups/dvs/<날짜-PID>/`에 먼저 보관하며 실패 시 복원합니다. 기존 추가 설정은 백업 후 이 스냅샷의 4개 파일로 교체합니다.

커널을 자동 변경하거나 재부팅하지 않습니다. 설치 완료 시 기존 앱은 중지 상태이고 재부팅 후 자동 실행됩니다. 재부팅 후 `philip` 데스크톱에 로그인하세요. 무인 부팅은 OS에서 해당 사용자의 데스크톱 자동 로그인을 설정해야 합니다.

```bash
sudo systemctl status dvs-raw2-production.service
sudo systemctl restart dvs-raw2-production.service
```

- 웹: `http://<Pi-IP>:8082/`, WebSocket `8765`
- 실행 파일: `/home/philip/dvs_raw2_production/raw2_producer`
- 통합 실행: `/home/philip/dvs_raw2_production/raw2_production_start.sh`
- 로그: `/home/philip/dvs_raw2_production/logs/`

서비스가 센서 초기화와 웹/로컬 앱을 함께 관리합니다. 디코더 바이너리만 단독 실행하면 초기화와 IPC 서버가 준비되지 않습니다. 레지스터 제어 서버에는 인증이 없으므로 신뢰하는 로컬 네트워크용입니다.

## 복원과 분리 검사

```bash
# 실제 설치 없이 새 디렉터리에 payload만 풀기
./install.sh --stage-root /tmp/dvs-stage
# 설치 시 출력된 정확한 백업 경로 사용
sudo ./install.sh --restore /var/backups/dvs/<날짜-PID>
sudo reboot
```

복원은 해당 설치 직전의 파일·가상환경·부팅 설정·서비스 추가 설정과 서비스 상태를 되돌립니다. 커널 모듈 적용에는 재부팅이 필요합니다. apt 패키지 설치와 video/render/i2c 그룹 추가는 제거하지 않습니다.

## 소스 빌드와 검증

같은 커널의 Pi에서 헤더와 컴파일러가 필요합니다. 빌드는 임시 디렉터리에서 수행하고 결과는 `build/`에만 저장합니다. 실행 중인 파일이나 드라이버는 교체하지 않습니다.

```bash
sudo apt-get install build-essential linux-headers-$(uname -r) device-tree-compiler python3-numpy
./scripts/build.sh
python3 -m unittest discover -s tests -p 'test_installer.py' -v
```

빌드 스크립트는 디코더를 실제 실행본과 같은 옵션으로 빌드해 **바이트 단위 일치**를 검사합니다. 드라이버 2개·오버레이 빌드와 RAW2·화면·alignment·boundary/trace·JSON 통계 검사를 수행합니다. 실행본의 현재 성능과 이번 검증 결과는 [VALIDATION.md](VALIDATION.md)를 참고하세요.

별도의 새 SD 카드에 전체 설치한 뒤 부팅하는 검사는 아직 수행하지 않았습니다. 센서 매뉴얼, 비밀번호, 전체 OS/홈과 진단 캡처 영상은 설치 패키지에 포함하지 않습니다.

## 이전 자료

10월 12일 최적화 보고서는 `payload/home/philip/dvs_raw2_production/OPTIMIZATION_REPORT.md`에 이력으로 보존했습니다. 저장된 원본의 순차 재생기는 [player/README.md](player/README.md)에 있습니다.
