# PC 성능 점검·개선 AI Agent — v3 설계서

**멀티 OS (Windows & Linux) 지원 확대 및 모듈러 가독성 중심 설계서 (구현 완료 현행화)**

> v2 대비 주요 변경사항:
> 1. **멀티 OS 아키텍처 도입**: 단일 OS(Windows) 종속 구조에서 벗어나, OS별 전용 진단 및 최적화 모듈 분리
> 2. **가독성 최우선 원칙(Clean Code & Separation of Concerns)**: 조건문(`if/else`) 난무를 방지하기 위해 파일 및 클래스를 OS별로 완전히 분리
> 3. **Linux 환경 지원 추가**: Lubuntu/Ubuntu 등 리눅스 환경에서의 시스템 지표 수집 및 안전한 최적화 액션 정의 (구현 완료)

---

## 1. 시스템 목표 및 확장 방향

v3 설계의 핵심 목표는 **"하나의 OpenClaw 오케스트레이터 아래에서 Windows PC와 Linux(Lubuntu/Ubuntu) PC를 동시에 진단하고 최적화할 수 있는 멀티 OS 에이전트 구축"**입니다.

이를 위해 코드가 복잡해지는 것을 막고 사람이 읽기 쉽도록 **전략 패턴(Strategy Pattern)과 OS별 전용 모듈 분리 방식**을 채택하여 성공적으로 구현을 완료했습니다.

---

## 2. v3 멀티 OS 패키지 구조 (가독성 중심 구현 완료)

```
pcp_ai_agent/
│
├── main.py                          # Agent 서버 진입점 (FastAPI + MCP)
├── client_test.py                   # 멀티 OS 테스트 클라이언트
├── requirements.txt                 # 필수 패키지 명세
│
├── config/
│   └── agent_config.yaml            # 설정 파일 (OS 무관 공통)
│
├── server/
│   ├── session_manager.py           # 메모리 전용 API Key 관리
│   └── auth_middleware.py           # Bearer Token 인증 미들웨어
│
├── diagnostic/                      # 🔍 진단 모듈 (OS별 완전 분리)
│   ├── metric_aggregator.py         # 공통 총괄 (OS 판별 후 전용 진단기 위임)
│   ├── windows_diagnostic.py        # Windows 전용 수집 (WMI, PowerShell, psutil)
│   └── linux_diagnostic.py          # Linux 전용 수집 (Procfs, systemctl, psutil)
│
├── reasoning/                       # 🧠 추론 및 보안 모듈
│   ├── privacy_filter.py            # 민감정보 마스킹 (<user>)
│   └── llm_client.py                # Google Gemini API 연동 (Timeout/Retry/Fallback)
│
├── optimizer/                       # ⚙️ 최적화 실행 모듈 (OS별 완전 분리)
│   ├── optimizer_executor.py        # 공통 총괄 (정책 검증 및 전용 실행기 위임)
│   ├── windows_optimizer.py         # Windows 전용 최적화 (Temp, 휴지통, 서비스)
│   ├── linux_optimizer.py           # Linux 전용 최적화 (/tmp, Trash, Apt clean)
│   └── snapshot_manager.py          # Level 2 이상 작업 스냅샷 및 롤백
│
├── security/
│   └── action_policy.py             # Action Policy Engine (Level 1 / Level 2 분류)
│
├── verification/
│   └── performance_verifier.py      # 작업 전/후 성능 비교 및 검증
│
└── resilience/
    └── task_persistence.py          # Task 영속화 및 결과 버퍼링
```

---

## 3. 모듈별 상세 구현 현황

### 3.1 진단 총괄 및 OS별 전용 모듈 (`diagnostic/`)

- **`metric_aggregator.py` (총괄 관리자)**: `platform.system()`을 통해 OS를 감지하고 `WindowsDiagnostic` 또는 `LinuxDiagnostic`으로 깨끗하게 위임합니다.
- **`windows_diagnostic.py` (Windows 전용)**: CPU/Memory/Disk 구간 평균, Top 프로세스, WMI 시작 프로그램 및 중요 서비스 수집.
- **`linux_diagnostic.py` (Linux 전용)**: CPU/Memory/Disk 구간 평균, Top 프로세스, Systemd 서비스 상태(`systemctl`) 수집.

---

### 3.2 최적화 총괄 및 OS별 전용 모듈 (`optimizer/`)

- **`optimizer_executor.py` (총괄 관리자)**: 현재 OS에 따라 `WindowsOptimizer` 또는 `LinuxOptimizer`의 `execute()` 메서드를 호출합니다.
- **`windows_optimizer.py` (Windows 전용)**: `clean_temp`, `clean_recycle_bin` (PowerShell Clear-RecycleBin), `disable_startup_program`, `stop_service`, `clean_windows_update_cache`.
- **`linux_optimizer.py` (Linux 전용)**: `/tmp` 정리, 사용자 캐시 및 휴지통(`~/.local/share/Trash`) 정리, Systemd 서비스 중지(`sudo systemctl stop`), 패키지 캐시 정리(`sudo apt-get clean`).

---

## 4. 보안 및 복원력 유지 원칙 (v2 계승 및 검증 완료)
- **인증**: Bearer Token 검증 미들웨어 (`server/auth_middleware.py`)
- **프라이버시**: LLM 전송 전 사용자 경로 마스킹 (`reasoning/privacy_filter.py`)
- **스냅샷 & 롤백**: Level 2 이상 작업 전 백업 및 자동 복구 (`optimizer/snapshot_manager.py`)
- **LLM 연동**: Google Gemini API 및 규칙 기반 폴백 (`reasoning/llm_client.py`)
- **구문 검사**: 모든 모듈 리팩토링 후 `main.py` 구문 검사(Syntax Check) 성공 완료 (`Syntax check passed successfully!`)
