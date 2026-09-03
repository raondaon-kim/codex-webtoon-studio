# Codex Webtoon Studio

Codex와 대화하며 **바이블 → 영지/세계 기반 → 에피소드 스크립트 → 세로 스크롤 연출 → 컷 디렉터 브리프 → 이미지 생성 → 레터링/조립 → QC**를 반복하는 저장소형 웹툰 제작 스튜디오입니다. 영지물에서는 개별 재난보다 지리·자원·인프라·고질적 문제를 먼저 JSON으로 확정합니다.

## 무엇이 가능한가

- Codex와 대화해 원작 아이디어를 스토리/비주얼 바이블로 발전
- 캐릭터 삼면도·표정표·의상/소품표와 배경 기준 시트 생성 계획 작성
- 회차 대본을 세로 스크롤의 호흡, 여백, 리빌 타이밍으로 분해
- 샷 크기, 카메라, 정규화 bbox, 배경 크롭을 포함한 컷 브리프 작성
- 브리프를 독립적인 이미지 프롬프트/편집 작업으로 컴파일
- Codex 인증을 활용하는 외부 이미지 실행기로 생성/편집 호출
- 생성 컷을 세로 마스터로 조립하고 업로드용 슬라이스 및 QC 리포트 생성

## 빠른 시작

```powershell
python -m pip install -e .
python tools/validate_artifacts.py examples/project
python tools/compile_render_tasks.py examples/project/episodes/ep001/briefs --project-root examples/project
python tools/run_image_tasks.py examples/project/episodes/ep001/render-tasks --project-root examples/project
```

마지막 명령은 기본적으로 드라이런입니다. 실제 유료 이미지 호출은 이미지 실행기 설치와 인증 상태 확인을 마친 뒤 `--execute`를 명시해야 합니다.

인증 파일은 복사하거나 저장소에 넣지 않습니다. 실행기가 Codex의 사용자 자격 증명 저장소 또는 `~/.codex/auth.json`을 직접 찾습니다.

## 대화로 제작하는 순서

저장소 루트에서 Codex에게 다음처럼 요청하면 됩니다.

1. “이 아이디어로 스토리 바이블 초안을 만들고 검증해 줘.”
2. “주인공 캐릭터 시트를 만들 render task로 컴파일해 줘.”
3. “1화 대본을 쓰고 세로 스크롤 플랜까지 만들어 줘.”
4. “승인된 플랜으로 컷 브리프를 만들고 드라이런해 줘.”
5. “내가 승인한 task만 실제 생성하고, 조립 후 QC해 줘.”

Codex가 읽는 단계별 절차는 [`.agents/skills`](.agents/skills)에, 데이터 계약은 [`schemas/v1`](schemas/v1)에 있습니다. 프로젝트 작업 규칙은 [`AGENTS.md`](AGENTS.md)를 따릅니다.

## 디렉터리

```text
.agents/skills/          Codex 단계별 제작 skill
config/                  프로젝트·이미지 실행기·출판 프로필
schemas/v1/              기준 JSON Schema
territory/               영지의 지리·환경·인프라·고질 문제 프로필
prompt-templates/        캐릭터/배경/컷 프롬프트 구성요소
webtoon_studio/          검증·컴파일·실행·조립·QC 라이브러리
tools/                   사람이 직접 실행할 CLI
examples/project/        비용 없이 검증 가능한 예제
third_party/             가져온 설계/코드의 출처와 라이선스
```

## 핵심 원칙

- 한 컷을 거대한 완성 페이지로 생성하지 않습니다. 모델 제약 안의 컷/스크롤 블록을 생성해 긴 세로 마스터로 조립합니다.
- 대사와 캡션은 기본적으로 이미지 생성에서 제외하고 레터링 단계에서 합성합니다. 이미지 안의 글자는 교정과 현지화가 어렵기 때문입니다.
- 캐릭터 일관성은 텍스트 묘사만으로 맡기지 않습니다. 승인된 기준 시트를 이후 편집 작업의 첫 번째 레퍼런스로 고정합니다.
- 생성 작업은 입력 파일의 SHA-256을 기록합니다. 바뀐 브리프를 예전 승인으로 실행하지 않습니다.
- `auth.json`, 토큰, API 키는 산출물과 로그에 기록하지 않습니다.

## 라이선스

프로젝트 자체는 MIT 라이선스를 사용합니다.
