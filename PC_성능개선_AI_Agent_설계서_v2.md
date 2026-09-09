# PC 성능 점검·개선 AI Agent

**2차 분석/설계서 (개정판) — MVP 핵심 기능 + 보안/안정성 보완 및 구현 완료 반영**

> v2 대비 변경사항: 보안(인증/프라이버시), 실패 대응(롤백/재개), 로컬 사용자 보호, 측정 신뢰성, 운영 항목을 신규 반영. 신규/변경 섹션은 **[v2]** 표시. 또한 실제 프로그램 구현 완료에 따른 아키텍처 및 LLM 연동(Google Gemini) 현행화 반영.

아래 설계의 핵심은 OpenClaw가 중앙의 AI Orchestrator 역할을 하고, 각 원격 Windows PC에는 PC Performance AI Agent가 설치되어 실제 진단과 개선 작업을 수행하는 구조입니다.

초기 버전에서는 모든 Windows 최적화를 자동화하기보다,

① 상태 수집 → ② 병목 분석 → ③ 개선안 결정 → ④ 안전한 개선 실행 → ⑤ 검증 → ⑥ 결과 보고

라는 폐쇄 루프를 먼저 완성하는 것이 좋습니다.

---

## 1. 시스템 목표

### 1.1 최종 목표

사용자가 OpenClaw에 다음과 같이 요청합니다.

> "A-PC의 최근 성능이 느려졌어. 원인을 분석하고 가능한 범위에서 최적화해줘."

그러면 OpenClaw가 원격 PC의 AI Agent에 MCP를 통해 작업을 지시합니다.

```
PC 상태 수집
    ↓
성능 병목 분석
    ↓
개선 가능 항목 식별
    ↓
개선 작업 계획
    ↓
안전성 검증
    ↓
개선 작업 실행
    ↓
결과 재측정
    ↓
Self-Correction Loop
    ↓
최종 결과 OpenClaw 보고
```

---

## 2. 1차 MVP 범위

처음부터 너무 많은 Windows 튜닝 기능을 넣으면 위험하고 복잡도가 급격히 증가합니다.

따라서 1차 버전은 **진단 + 제한된 안전한 개선 작업**에 집중하고, **보안/안전 뼈대는 처음부터 최소 수준으로 포함**하는 것을 권장합니다. *(v2: 보안·롤백 항목은 나중에 추가하기 어려운 유형이므로 MVP 범위에 최소 뼈대로 포함)*

### 2.1 MVP 핵심 기능

| 구분 | 기능 |
|---|---|
| 원격 제어 | OpenClaw → MCP → AI Agent 작업 지시 |
| **[v2] 상호 인증** | **Agent ↔ OpenClaw 간 별도 인증 토큰 검증 (mTLS 또는 사전 발급 토큰)** |
| 인증(세션) | API Key를 OpenClaw에서 세션 단위 전달 |
| 시스템 진단 | CPU, Memory, Disk, Process, Startup, Service |
| 성능 분석 | 병목 원인 및 이상 상태 판단 |
| 개선 계획 | 실행 가능한 개선 Action 생성 |
| 개선 실행 | 허용된 안전한 작업만 수행 |
| **[v2] 롤백/복구** | **Level 2 이상 작업은 실행 전 스냅샷 저장, 실패 시 자동 복구** |
| 결과 검증 | 작업 전/후 성능 비교 (**[v2] 순간값이 아닌 구간 평균**) |
| Self-Correction | 실패 또는 효과 부족 시 재분석 (**[v2] 재시도 간 Backoff 적용**) |
| 결과 보고 | 성공/실패/부분성공 결과 OpenClaw 보고 |
| **[v2] 오프라인 버퍼링** | **네트워크 단절 시 결과를 로컬에 임시 저장 후 재연결 시 전송** |
| **[v2] 로컬 사용자 보호** | **저장되지 않은 작업 종료 방지, 알림/확인 절차** |
| **[v2] 민감정보 필터링** | **LLM 전송 전 프로세스명/타이틀 등 개인정보 마스킹** |
| 감사 로그 | 모든 진단 및 변경 작업 기록 (**[v2] 보존기간·무결성 명시**) |

---

## 3. 전체 아키텍처 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       OpenClaw                              │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 AI Orchestrator                       │  │
│  │                                                       │  │
│  │  - 사용자 요청 해석                                   │  │
│  │  - 대상 PC 선택                                      │  │
│  │  - 작업 계획                                         │  │
│  │  - LLM API Key 관리                                  │  │
│  │  - AI Agent 호출                                     │  │
│  │  - 결과 수집 / 사용자 보고                           │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                  │
│                          │ MCP (mTLS / Agent Auth Token) ★v2│
│                          │ Streamable HTTP                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                     (사내망/VPN 경유 권장) ★v2
                           ▼
╔═════════════════════════════════════════════════════════════╗
║                  Remote Windows PC                          ║
║                                                             ║
║  ┌───────────────────────────────────────────────────────┐  ║
║  │              PC Performance AI Agent                  │  ║
║  │                                                       │  ║
║  │       ┌────────────────────────────────────┐          │  ║
║  │       │         MCP Server Layer           │          │  ║
║  │       │  Streamable HTTP Endpoint          │          │  ║
║  │       │  + Auth Middleware (★v2)           │          │  ║
║  │       └────────────────┬───────────────────┘          │  ║
║  │                        │                              │  ║
║  │       ┌────────────────▼───────────────────┐          │  ║
║  │       │       Agent Controller             │          │  ║
║  │       │  - Task 관리 (영속화 ★v2)          │          │  ║
║  │       │  - 상태 관리                       │          │  ║
║  │       │  - Workflow 제어                   │          │  ║
║  │       │  - Task Queue/Lock (★v2)           │          │  ║
║  │       └────────────────┬───────────────────┘          │  ║
║  │                        │                              │  ║
║  │       ┌────────────────▼───────────────────┐          │  ║
║  │       │       AI Reasoning Engine          │          │  ║
║  │       │  - Privacy Filter (★v2)            │          │  ║
║  │       │  - LLM 호출 (Timeout/Retry ★v2)    │          │  ║
║  │       │  - 원인 분석                       │          │  ║
║  │       │  - 개선안 생성                     │          │  ║
║  │       │  - Self-Correction Loop (Backoff)  │          │  ║
║  │       └───────────────┬────────────────────┘          │  ║
║  │                       │                               │  ║
║  │          ┌────────────┴────────────┐                  │  ║
║  │          ▼                         ▼                  │  ║
║  │ ┌────────────────┐      ┌────────────────────┐        │  ║
║  │ │ Diagnostic     │      │ Optimization       │        │  ║
║  │ │ Engine         │      │ Engine             │        │  ║
║  │ │                │      │                    │        │  ║
║  │ │ CPU (구간평균) │      │ Startup 정리       │        │  ║
║  │ │ Memory         │      │ Temp 파일 정리     │        │  ║
║  │ │ Disk           │      │ 안전한 Process 종료│        │  ║
║  │ │ Process        │      │ Service 조정       │        │  ║
║  │ │ Startup        │      │ 스냅샷/롤백 (★v2) │        │  ║
║  │ └────────────────┘      └────────────────────┘        │  ║
║  │                                                        │  ║
║  │             ┌────────────────────────┐                 │  ║
║  │             │ Windows System Layer   │                 │  ║
║  │             │                        │                 │  ║
║  │             │ PowerShell             │                 │  ║
║  │             │ WMI / CIM              │                 │  ║
║  │             │ Performance Counters   │                 │  ║
║  │             │ Windows API            │                 │  ║
║  │             └────────────────────────┘                 │  ║
║  │                                                        │  ║
║  │       [사용자 알림 Tray] (★v2)                          │  ║
║  │       [로컬 결과 버퍼 DB] (★v2)                          │  ║
╚═════════════════════════════════════════════════════════════╝
```

---

## 4. 핵심 설계 원칙

### 4.1 OpenClaw와 AI Agent의 역할 분리

가장 중요한 설계 원칙입니다.

**OpenClaw** — 중앙 지휘자(Control Plane) 역할

```
사용자 요청 → OpenClaw → 어떤 PC에 어떤 작업을 어떤 정책으로 수행할지 결정 → AI Agent 호출
```

**PC Performance AI Agent** — 실제 작업 수행자(Execution Plane)

```
작업 지시 수신 → 현재 PC 상태 확인 → 실제 Windows 환경 분석 → 개선 작업 수행 → 결과 검증 → OpenClaw 보고
```

즉, **OpenClaw = Brain + Commander**, **AI Agent = Local Brain + Hands**로 볼 수 있습니다.

### 4.2 [v2] 신뢰 경계(Trust Boundary) 원칙

Agent는 관리자 권한에 준하는 작업(Service 조정, Startup 변경, Process 종료)을 수행하므로, 다음을 원칙으로 둡니다.

- Agent와 OpenClaw는 서로를 **암묵적으로 신뢰하지 않는다** — 모든 요청은 인증·인가를 거친다.
- Agent의 MCP 엔드포인트는 **기본적으로 사내망/VPN 내부에만 노출**하고, 인터넷 직접 노출을 금지한다.
- Agent 실행 계정은 **최소 권한 원칙**을 따르며, 반드시 필요한 작업(예: Service 제어)에 한해서만 상승된 권한을 사용한다.

---

## 5. MCP 통신 구조

요구사항에 따라 Streamable HTTP 기반 MCP를 사용합니다.

```
┌──────────────┐
│   OpenClaw   │
│  MCP Client  │
└──────┬───────┘
       │ MCP / Streamable HTTP
       │ [v2] Authorization: Bearer <Agent Auth Token>
       │ [v2] mTLS (선택, 권장)
       ▼
┌──────────────────────┐
│ Remote PC             │
│ Performance Agent     │
│ MCP Server            │
│ /mcp                  │
└──────────────────────┘
```

### 5.1 [v2] 인증/인가 설계

MCP Streamable HTTP는 기본적으로 전송 계층 인증을 강제하지 않으므로, 별도 레이어가 필요합니다.

| 구성요소 | 설계 |
|---|---|
| Agent 식별 | PC별 고유 Agent ID + 사전 발급된 정적 Registration Token |
| 요청 인증 | 매 요청 `Authorization: Bearer <token>` 검증 (세션 API Key와는 별개) |
| 전송 암호화 | TLS 필수, 가능하면 mTLS(상호 인증서) 적용 |
| 네트워크 노출 범위 | 기본값: 사내망/VPN 전용. 외부 노출 시 별도 Gateway + WAF 경유 |
| Rate Limit | 동일 Agent에 대한 비정상적 요청 폭주 방지 |

> Agent 인증 토큰과 세션 단위 LLM API Key(7장)는 **별개의 개념**입니다. 전자는 "누가 이 Agent를 호출할 자격이 있는가", 후자는 "이번 작업에서 어떤 LLM 자격증명을 쓸 것인가"를 다룹니다.

---

## 6. AI Agent MCP Tool 설계

1차 버전에서는 다음 5개 Tool이면 충분합니다.

| MCP Tool | 기능 |
|---|---|
| `get_system_status` | 현재 시스템 상태 조회 |
| `diagnose_performance` | 성능 저하 원인 분석 |
| `create_optimization_plan` | 개선 계획 생성 |
| `execute_optimization` | 개선 작업 실행 |
| `get_task_result` | 작업 결과 조회 |

실제 Agent 내부에서는 더 세분화된 모듈을 사용합니다.

---

## 7. API Key 처리 설계

AI Agent는 로컬 PC에 LLM API Key를 저장하지 않는 것이 원칙입니다.

```
OpenClaw
   │ Task Request + Session Token + LLM API Credential
   ▼
AI Agent
   │ Memory Only → LLM API 호출 → 작업 완료 → Memory Clear
```

다음 위치에는 절대 저장하지 않습니다: `.env`, `config.yaml`, Registry, File System, Database, Log File, Windows Credential Manager.

```python
class SessionContext:
    task_id: str
    llm_api_key: str
    connection_id: str
    expires_at: datetime
```

작업 종료 또는 연결 종료 시:

```python
context.llm_api_key = None
del context
```

Python 메모리 특성상 완전한 물리적 삭제를 보장하기 어려우므로 다음 원칙을 적용합니다.

- 장기 저장 금지 / 로그 출력 금지 / Exception 출력 금지 / Prompt 포함 금지
- 가능하면 OpenClaw가 API 호출을 대행하는 구조도 향후 검토

### 7.1 향후 권장 구조

```
AI Agent → Analysis Request → OpenClaw / LLM Gateway (API Key 사용) → LLM Provider
```

1차 버전에서는 요구사항대로 세션 단위 메모리 전달 방식으로 구현합니다.

### 7.2 [v2] LLM 전송 데이터 프라이버시 필터링

진단 데이터(Top Process, Window Title, 파일 경로 등)에는 사용자의 개인 정보가 포함될 수 있습니다. LLM 호출 전 다음 필터링 계층을 거칩니다.

| 항목 | 처리 방식 |
|---|---|
| 프로세스 실행 파일명 | 알려진 시스템/일반 프로그램은 그대로, 사용자 지정 실행파일 경로는 사용자 폴더명 등 마스킹 |
| 윈도우 타이틀 | 기본적으로 LLM에 전달하지 않음 (필요 시 옵션으로만 활성화) |
| 파일 경로/파일명 | 사용자 프로필 경로(`C:\Users\<name>\...`)는 `<user>`로 치환 |
| 네트워크 정보(IP 등) | 기본 미전송 |

> 원칙: **LLM에게는 "분석에 필요한 최소한의 구조화된 지표"만 전달**하고, 식별 가능한 개인정보는 로컬 필터를 거친 뒤에만 전달합니다.

---

## 8. 처리 프로세스 흐름도

### 8.1 전체 처리 흐름

```
User Request
   ↓
OpenClaw 작업 요청 분석
   ↓
Target PC 선택
   ↓
MCP Task Request (Streamable HTTP + Agent Auth Token + API Key) ★v2
   ↓
AI Agent 인증 검증 (★v2) → 실패 시 즉시 Reject
   ↓
Session 생성 (API Key → Memory)
   ↓
[동시 요청 확인 → Task Queue/Lock] ★v2
   ↓
System Diagnostic (구간 평균 측정) ★v2
   (CPU / Memory / Disk / Process / Startup / Service)
   ↓
문제 발견? ──No──→ 정상 보고 후 종료
   │Yes
   ▼
Root Cause Analysis (Privacy Filter 적용 후 LLM 호출) ★v2
   ↓
Optimization Plan
   ↓
Safety Validation (+ 로컬 사용자 영향도 체크) ★v2
   ↓
실행 가능? ──No──→ Error / 승인 요청
   │Yes
   ▼
[Level 2 이상] 실행 전 스냅샷 저장 ★v2
   ↓
개선 실행 ── 실행 중 연결 끊김? ★v2 → 결과 로컬 버퍼 저장 → 재연결 시 전송
   ↓
재측정 (구간 평균) ★v2
   ↓
효과 확인 → 목표 달성? ──Yes──→ Final Report
   │No
   ▼
Self-Correction (재분석/재시도, Backoff 적용) ★v2
   ↓
Retry Limit 도달? ──No──→ 재시도
   │Yes
   ▼
[실패 시] 스냅샷 기반 롤백 실행 ★v2
   ↓
Final Report (성공/부분성공/실패 + 롤백 여부) → OpenClaw
```

---

## 9. Self-Correction Loop 설계

단순한 Script 실행 시스템이 아니라, **실행 결과를 다시 측정하고 결과가 좋지 않으면 원인을 다시 분석하는 Agent**가 되어야 합니다.

```
Observe → Analyze → Plan → Act → Verify → Evaluate
                                             │
                              ┌──────────────┴──────────────┐
                          Success                       Failure
                              │                              │
                           Report                        Reflect
                                                              │
                                                          New Plan
                                                              │
                                                       [Backoff 대기] ★v2
                                                              │
                                                            Retry
```

```python
import time

MAX_RETRY = 3
BASE_BACKOFF_SEC = 5  # ★v2: 재시도 간 대기 (지수 백오프 권장: 5s, 15s, 45s ...)

retry_count = 0
while retry_count < MAX_RETRY:

    observation = diagnostic_engine.collect(window_sec=30)  # ★v2: 순간값 대신 구간 평균

    # ★v2: LLM 호출 전 개인정보 필터링 + 타임아웃/재시도 처리
    try:
        analysis = reasoning_engine.analyze(
            privacy_filter.sanitize(observation),
            timeout=15
        )
    except LLMTimeoutError:
        analysis = reasoning_engine.analyze_with_fallback(observation)  # ★v2 규칙 기반 폴백

    plan = planning_engine.create(analysis)

    validated = action_policy.validate(plan)  # Level 분류 + 승인 필요 여부 판단
    if validated.requires_approval:
        report_pending_approval(validated)
        break

    if validated.risk_level >= 2:
        snapshot = snapshot_manager.capture(plan)  # ★v2 스냅샷

    result = executor.execute(plan)
    verification = verifier.check(result, window_sec=30)  # ★v2 구간 평균 재측정

    if verification.success:
        break

    if validated.risk_level >= 2:
        snapshot_manager.rollback(snapshot)  # ★v2 실패 시 롤백

    correction_context = {
        "previous_plan": plan,
        "result": result,
        "verification": verification,
    }

    retry_count += 1
    time.sleep(BASE_BACKOFF_SEC * (2 ** (retry_count - 1)))  # ★v2 지수 백오프
```

---

## 10. Self-Correction 예시

Disk 사용률이 98%인 경우:

```
1차 분석: C Drive 98% 사용 → Temp 파일 과다 → Temp Cleanup 실행
실행 후: 98% → 96%   (효과 부족)

Self-Correction 동작:
효과 부족 → Disk 재분석 → Large Files Scan → Windows Update Cache 확인 → Recycle Bin 확인

새로운 개선 계획:
1. Windows Temp
2. User Temp
3. Windows Update Cache
4. Recycle Bin

실행 후: 98% → 72%  → SUCCESS
```

> **[v2]** 이 과정에서 재측정 값(96%, 72%)은 단일 시점이 아니라 30초~1분 구간 평균이어야 하며, 만약 최종 실행 후에도 목표 미달로 3회 재시도가 모두 실패했다면 Level 2 작업(Windows Update Cache 정리 등)은 스냅샷 기준으로 롤백 여부를 판단 후 보고합니다.

---

## 11. 안전한 개선 작업 정책

AI Agent가 Windows 설정을 무분별하게 변경하면 안 됩니다. Action을 위험도별로 분류합니다.

### Level 1 — 자동 실행 가능

- Temp 파일 정리
- Recycle Bin 정리
- Performance Data 수집
- ~~불필요한 User Process 종료~~ → **[v2] 재분류 권장**: 저장되지 않은 문서가 있을 수 있으므로 **Level 2(정책 기반, 사전 확인 필요)**로 이동
- Disk 상태 조회
- Startup 정보 조회

### Level 2 — 정책 기반 자동 실행

- Startup Program Disable
- 특정 Service Stop
- Windows Cache 정리
- **[v2] 불필요한 User Process 종료** (변경 저장 여부 확인 API 존재 시에만, 없으면 사용자 알림 후 진행)

Whitelist 또는 Policy 검증 후 실행하며, **[v2] 실행 전 스냅샷(예: 종료 대상 프로세스 목록/서비스 상태) 저장**을 필수로 합니다.

### Level 3 — 사용자/OpenClaw 승인 필요

- Registry 변경
- Driver 변경
- Pagefile 변경
- Windows Service Disable
- Power Plan 변경
- 시스템 파일 삭제

1차 MVP에서는 Level 1과 일부 Level 2까지만 구현하는 것을 권장합니다.

### 11.1 [v2] 로컬 사용자 보호 정책

| 항목 | 정책 |
|---|---|
| Process 종료 전 확인 | 저장 안 된 변경사항이 있을 수 있는 프로세스는 종료 전 트레이 알림 표시 (가능한 경우 사용자 응답 대기, 타임아웃 시 스킵) |
| 작업 가시성 | Agent가 활성 작업을 수행 중일 때 트레이 아이콘/알림으로 표시 |
| Opt-out | 사용자가 특정 시간대(예: 근무 중) 자동 최적화를 일시 중지할 수 있는 로컬 설정 제공 |
| 보안 소프트웨어 오탐 대응 | Agent 실행파일/동작에 대한 EDR/백신 화이트리스트 등록 가이드 문서 별도 제공 |

---

## 12. 시퀀스 다이어그램

> (별도 다이어그램 첨부 예정 — 인증 핸드셰이크, 정상 흐름, 롤백 흐름 3종 권장)

---

## 13. 프로그램 구성

```
pc-performance-agent/
│
├── main.py
│
├── server/
│   ├── mcp_server.py
│   ├── session_manager.py
│   └── auth_middleware.py        # ★v2 Agent 인증
│
├── agent/
│   ├── agent_controller.py
│   ├── workflow_engine.py
│   ├── task_manager.py
│   └── task_queue.py              # ★v2 동시 요청 Lock/Queue
│
├── diagnostic/
│   ├── system_info.py
│   ├── cpu_monitor.py
│   ├── memory_monitor.py
│   ├── disk_monitor.py
│   ├── process_monitor.py
│   ├── startup_monitor.py
│   └── metric_aggregator.py       # ★v2 구간 평균/베이스라인
│
├── reasoning/
│   ├── llm_client.py              # ★v2 timeout/backoff/fallback 포함
│   ├── performance_analyzer.py
│   ├── optimization_planner.py
│   ├── self_correction.py
│   └── privacy_filter.py          # ★v2 개인정보 마스킹
│
├── optimizer/
│   ├── optimizer_executor.py
│   ├── temp_cleaner.py
│   ├── process_optimizer.py
│   ├── startup_optimizer.py
│   ├── disk_optimizer.py
│   └── snapshot_manager.py        # ★v2 스냅샷/롤백
│
├── verification/
│   └── performance_verifier.py
│
├── security/
│   ├── api_key_manager.py
│   └── action_policy.py
│
├── resilience/                    # ★v2 신규 모듈
│   ├── task_persistence.py        # 진행 중 Task 디스크 영속화/재개
│   └── result_buffer.py           # 네트워크 단절 시 결과 로컬 버퍼링
│
├── notification/                  # ★v2 신규 모듈
│   └── tray_notifier.py           # 로컬 사용자 알림
│
├── reporting/
│   └── result_reporter.py
│
├── models/
│   ├── task.py
│   ├── diagnostic_result.py
│   ├── optimization_plan.py
│   └── task_result.py
│
└── config/
    ├── agent_config.yaml
    └── action_whitelist.yaml      # ★v2 허용 Action 명시적 관리
```

---

## 14. 프로그램 기능 명세서

### 14.1 main.py

| 항목 | 내용 |
|---|---|
| 프로그램 | main.py |
| 역할 | AI Agent 실행 진입점 |
| 주요 기능 | Configuration Load, MCP Server 시작, **[v2] 미완료 Task 복구 시도** |
| 입력 | config |
| 출력 | Agent Process |

### 14.2 mcp_server.py

| 항목 | 내용 |
|---|---|
| 역할 | MCP Server |
| 통신 | Streamable HTTP |
| 주요 기능 | OpenClaw 요청 수신, **[v2] Auth Middleware 통과 후 라우팅** |
| MCP Tools | Diagnostic, Optimization, Result |

```python
from fastmcp import FastMCP

mcp = FastMCP("PC Performance Agent")

@mcp.tool()
async def diagnose_performance():
    ...
```

1차 버전에서는 FastMCP를 사용하는 것이 개발 효율상 적절합니다.

### 14.3 session_manager.py

| 기능 | 설명 |
|---|---|
| Session 생성 | 작업 요청 시 생성 |
| API Key 보관 | Memory Only |
| TTL 관리 | 일정 시간 후 폐기 |
| Connection 감시 | 연결 종료 감지 |
| Memory Clear | 작업/연결 종료 시 삭제 |

핵심 책임: **API Key는 Session 외부에 존재하지 않는다.**

### 14.4 [v2] auth_middleware.py (신규)

| 기능 | 설명 |
|---|---|
| Agent Auth Token 검증 | 요청 헤더의 Bearer Token을 사전 등록된 값과 비교 |
| mTLS 검증(선택) | 클라이언트 인증서 검증 |
| Rate Limiting | 단시간 다량 요청 차단 |
| 실패 처리 | 인증 실패 시 상세 사유 노출 없이 401/403 반환, 감사 로그에 기록 |

### 14.5 agent_controller.py

```
MCP Request → Agent Controller → Task 생성 → [Task Queue 확인] ★v2 → Workflow Engine 실행 → Result 생성
```

주요 기능: Task 생성, Task 상태 관리(디스크 영속화 ★v2), Workflow 호출, 예외 처리, 최종 결과 반환, **[v2] 동일 PC 대상 동시 Task 직렬화**

### 14.6 diagnostic_engine

성능 상태를 수집합니다.

```
CPU: Usage / Load / Top Process
Memory: Total / Available / Used / Commit / Page Fault
Disk: Usage / Free Space / IO / Large Files
Process: CPU Top / Memory Top / Zombie / Abnormal
Startup: Startup Programs
```

Windows에서는 PowerShell, WMI, CIM, Get-Counter, Performance Counter, psutil을 활용합니다.

**[v2] metric_aggregator.py**: 순간값을 그대로 쓰지 않고, `window_sec`(기본 30~60초) 동안 샘플링한 값의 평균/중앙값을 사용하여 노이즈를 줄입니다. 장기적으로는 PC별 정상 범위(baseline)를 누적하여 절대 임계값(예: 98%)과 상대 임계값(평소 대비 편차)을 함께 판단 근거로 사용합니다.

---

## 15. Optimization Planner

진단 결과를 기반으로 Action Plan을 생성합니다.

```json
{
  "problem": "High Memory Usage",
  "root_cause": "Chrome processes consuming excessive memory",
  "actions": [
    {
      "action": "cleanup_memory",
      "target": "chrome",
      "risk_level": 1
    }
  ]
}
```

LLM이 직접 Windows 명령어를 생성해서 바로 실행하지 않는 것이 중요합니다.

```
LLM → Structured Action → Action Validator → Allowed Tool → Windows
```

```
LLM
   │
   ├── ❌ PowerShell 문자열 직접 생성
   │
   └── ⭕ Action ID 생성
             ↓
       optimizer.execute(action_id)
```

이 구조가 훨씬 안전합니다.

---

## 16. Action Policy Engine

```
Optimization Plan → Action Policy Engine → Allowed / Approval Required / Denied
```

```python
ALLOWED_ACTIONS = {
    "clean_temp",
    "clean_recycle_bin",
    "collect_diagnostics",
    # "stop_user_process",  # ★v2: Level 2로 재분류, 조건부 허용
}

APPROVAL_REQUIRED_ACTIONS = {
    "stop_user_process",       # ★v2
    "disable_startup_program",
    "stop_service",
    "clean_windows_update_cache",
}
```

**[v2]** Action Policy Engine은 승인 여부 판단과 함께, Level 2 이상 Action에 대해 `snapshot_manager`를 호출해 실행 전 상태를 기록하도록 강제합니다.

---

## 17. 최종 결과 데이터 모델

OpenClaw에 반환하는 결과는 구조화된 JSON을 권장합니다.

```json
{
  "task_id": "task-20260831-001",
  "status": "SUCCESS",
  "summary": "Disk usage optimization completed",
  "before": {
    "cpu_usage": 72,
    "memory_usage": 88,
    "disk_usage": 96,
    "measurement_window_sec": 30
  },
  "after": {
    "cpu_usage": 45,
    "memory_usage": 72,
    "disk_usage": 71,
    "measurement_window_sec": 30
  },
  "actions": [
    { "name": "clean_temp_files", "status": "SUCCESS", "risk_level": 1 },
    { "name": "clean_windows_update_cache", "status": "SUCCESS", "risk_level": 2, "snapshot_id": "snap-0912" }
  ],
  "self_correction": {
    "attempt_count": 2,
    "final_result": "SUCCESS"
  },
  "rollback": {
    "occurred": false
  }
}
```

실패한 경우:

```json
{
  "task_id": "task-20260831-002",
  "status": "PARTIAL_SUCCESS",
  "problem": "High CPU Usage",
  "root_cause": "Unknown third-party process",
  "attempted_actions": ["process_analysis", "safe_cleanup"],
  "failed_reason": "Process cannot be safely terminated",
  "rollback": {
    "occurred": true,
    "snapshot_id": "snap-0913",
    "result": "RESTORED"
  },
  "recommendation": [
    "User approval required",
    "Detailed process investigation recommended"
  ]
}
```

> **[v2]** `before`/`after`에 `measurement_window_sec` 필드를 추가하여 순간값이 아닌 구간 평균임을 명시하고, `rollback` 필드를 추가하여 실패 시 복구 여부를 항상 보고합니다.

---

## 18. 1차 MVP의 핵심 클래스 구조

```
                    ┌───────────────────┐
                    │   MCP Server      │
                    │  + Auth (★v2)     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ AgentController   │
                    │ + Task Queue ★v2  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │ WorkflowEngine    │
                    └─────────┬─────────┘
                              │
          ┌───────────────────┼──────────────────┐
          │                   │                  │
          ▼                   ▼                  ▼
┌────────────────┐   ┌────────────────┐  ┌─────────────────┐
│ Diagnostic     │   │ Reasoning      │  │ Optimizer       │
│ Engine         │   │ Engine         │  │ Executor        │
│ (Aggregator)   │   │ (Privacy★v2)   │  │ (Snapshot★v2)   │
└────────────────┘   └────────────────┘  └─────────────────┘
          │                   │                  │
          └───────────────────┼──────────────────┘
                              ▼
                    ┌───────────────────┐
                    │ Verification      │
                    │ Engine            │
                    └─────────┬─────────┘
                              ▼
                    ┌───────────────────┐
                    │ Result Reporter   │
                    │ + Result Buffer   │ ★v2
                    └───────────────────┘
```

---

## 19. 추천 1차 개발 순서

### Phase 0 — [v2] 보안/신뢰 기반 (신규, 최우선)

```
Agent Auth Token 발급/검증
    ↓
TLS 적용 (mTLS는 선택)
    ↓
사내망/VPN 제한 네트워크 구성
```

가장 먼저 통신 경로 자체를 안전하게 만든 뒤 나머지 기능을 얹습니다.

### Phase 1 — MCP 연결

```
OpenClaw → Streamable HTTP (인증 포함) → Windows PC Agent
```

구현: FastMCP Server, `get_system_status()`

### Phase 2 — PC 진단

```
CPU / Memory / Disk / Process   (구간 평균 수집 ★v2)
```

이 단계에서는 아직 최적화하지 않습니다.

```
OpenClaw → Agent → PC 상태 → OpenClaw
```

### Phase 3 — 분석 Agent

```
Metrics → [Privacy Filter ★v2] → LLM → Root Cause → Optimization Action
```

### Phase 4 — 안전한 최적화

처음에는 3~5개 Action만 구현합니다.

1. `clean_temp_files`
2. `clean_recycle_bin`
3. `find_high_cpu_process`
4. `find_high_memory_process`
5. `disable_noncritical_startup` (**실행 전 스냅샷 ★v2**)

### Phase 5 — Verification

```
Before Metrics(구간평균) → Optimization → After Metrics(구간평균) → Improvement Score
```

### Phase 6 — Self-Correction

```
실행 → 효과 없음 → 원인 재분석 → 새로운 Plan → [Backoff 대기 ★v2] → 재실행
```

`MAX_RETRY = 3` 권장.

### Phase 7 — [v2] 복원력(Resilience) 강화 (신규)

```
Task 상태 디스크 영속화
    ↓
Agent 재시작 시 미완료 Task 복구
    ↓
네트워크 단절 시 결과 로컬 버퍼링 → 재연결 시 전송
    ↓
Level 2 작업 실패 시 스냅샷 롤백
```

MVP 출시 전 필수로 검증할 것을 권장합니다 (사용자 PC에서 상시 동작하는 Agent이므로 실패 복원력이 신뢰도에 직결됩니다).

---

## 20. 최종 1차 MVP 아키텍처 제안

```
                     ┌────────────────────┐
                     │     OpenClaw       │
                     │ AI Orchestrator    │
                     │ LLM API Key        │
                     └─────────┬──────────┘
                               │ MCP / Streamable HTTP
                               │ + Agent Auth (★v2)
                               ▼
          ┌────────────────────────────────────────┐
          │       PC Performance AI Agent          │
          │                                        │
          │ ┌────────────────────────────────────┐ │
          │ │ FastMCP Server + Auth Middleware   │ │ ★v2
          │ └─────────────────┬──────────────────┘ │
          │                   ▼                    │
          │ ┌────────────────────────────────────┐ │
          │ │ Agent Controller + Task Queue      │ │ ★v2
          │ └─────────────────┬──────────────────┘ │
          │                   ▼                    │
          │ ┌────────────────────────────────────┐ │
          │ │ Workflow Engine                    │ │
          │ │ Diagnose → Analyze → Plan → Act    │ │
          │ │     ↑                      ↓       │ │
          │ │     └── Self Correction ──┘        │ │
          │ │        (Backoff ★v2)               │ │
          │ └─────────────────┬──────────────────┘ │
          │                   │                    │
          │        ┌──────────┴──────────┐         │
          │        ▼                     ▼         │
          │ ┌───────────────┐   ┌────────────────┐ │
          │ │ Diagnostic    │   │ Optimization   │ │
          │ │ Engine        │   │ Engine         │ │
          │ │ (구간평균★v2) │   │ (Snapshot★v2)  │ │
          │ └───────┬───────┘   └────────┬───────┘ │
          │         │                    │         │
          │         └─────────┬──────────┘         │
          │                   ▼                    │
          │        ┌──────────────────────┐        │
          │        │ Windows / PowerShell│         │
          │        │ WMI / Perf Counter  │         │
          │        └──────────────────────┘        │
          │                                        │
          │   [Resilience: Task 영속화/결과버퍼] ★v2 │
          │   [Tray Notifier: 사용자 알림] ★v2        │
          └────────────────────────────────────────┘
```

---

## 21. [v2] 운영(Operations) 항목

MVP 이후에도 지속 운영을 위해 미리 정의해두어야 할 항목입니다.

| 항목 | 내용 |
|---|---|
| Agent 배포/업데이트 | 다수 PC에 설치된 Agent의 버전 관리 방식 (예: OpenClaw가 배포 트리거, 단계적 롤아웃) |
| 감사 로그 스펙 | 보존 기간(예: 90일), 위변조 방지(append-only), 필수 필드(task_id, actor, action, timestamp, before/after, 결과) |
| 모니터링 | Agent 자체의 헬스체크(생존 여부, 마지막 통신 시각)를 OpenClaw가 주기적으로 확인 |
| 장애 대응 | Agent 응답 없음 지속 시 알림 및 재설치 가이드 |

---

## 결론

이 프로젝트에서 1차 버전의 가장 중요한 목표는 "AI가 Windows 명령어를 마음대로 생성하는 시스템"이 아니라, 다음 구조를 **안전하고 복원력 있게** 만드는 것입니다.

```
OpenClaw
   ↓
[인증된] Task                      ★v2
   ↓
MCP Agent
   ↓
Diagnostic (구간 평균)             ★v2
   ↓
LLM Analysis (개인정보 필터링 후)  ★v2
   ↓
Structured Optimization Plan
   ↓
Policy Validation (+ 로컬 사용자 보호) ★v2
   ↓
Predefined Safe Action (필요 시 스냅샷) ★v2
   ↓
Verification (구간 평균)           ★v2
   ↓
Self-Correction (Backoff)          ★v2
   ↓
Structured Report (+ 롤백 여부)    ★v2
   ↓
OpenClaw
```

이 구조가 완성되면 2차 단계에서 장기 모니터링, 성능 이력 DB, 이상 탐지, 사용자 승인 Workflow, 자동 스케줄 최적화, 다수 PC 중앙 관리 등을 자연스럽게 확장할 수 있습니다.

**MVP 착수 전 최소 확인 체크리스트**

- [ ] Agent ↔ OpenClaw 인증 방식 확정 (토큰 발급 절차 포함)
- [ ] Agent 네트워크 노출 범위(VPN/사내망 전용 여부) 확정
- [ ] LLM 전송 데이터 프라이버시 필터 규칙 1차 정의
- [ ] Level 2 Action의 스냅샷/롤백 방식 최소 구현
- [ ] 진행 중 Task 실패 시 사용자 데이터(문서 등) 보호 정책 확정
- [ ] 감사 로그 필드 및 보존기간 확정
