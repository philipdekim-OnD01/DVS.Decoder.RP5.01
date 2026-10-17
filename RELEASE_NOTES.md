# 2026.10.18 Final

현재 라즈베리에서 정상 동작 중인 버전을 기준으로 갱신했습니다.

- 현재 실행 중인 trace/shadow 디코더 바이너리와 정확히 대응하는 소스·헤더 포함
- 실제 적용 중인 Jetson 화면 모드, denoise=1, persistence_ms=50 보존
- 활성 systemd 추가 설정 4개와 외부 화면 설정 파일 포함
- 설치 시 기존 서비스 추가 설정 전체 백업·교체 및 복원 지원
- 재빌드 산출물과 실행 중인 바이너리의 SHA-256 완전 일치 확인
- 드라이버·오버레이 빌드, 디코더·화면·alignment·boundary/trace·JSON 회귀 검사 통과
- 실행 서비스, HTTP, WebSocket 영상과 프레임 진행 확인

지원: Raspberry Pi 5 / aarch64 / 커널 6.12.47+rpt-rpi-2712 / philip UID 1000 / Wayland+Xwayland 데스크톱.

별도 새 SD 카드에서 전체 설치·재부팅 검사는 수행하지 않았습니다. 현재 장비는 재설치·서비스 재시작·재부팅하지 않았습니다.
