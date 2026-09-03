# Architecture

## 목표

이 저장소는 Codex가 채팅에서 얻은 창작 결정을 파일로 남기고, 다음 대화가 그 파일을 다시 읽어 이어 갈 수 있게 한다. 모델의 대화 기억이 아니라 저장소의 versioned artifact가 작품의 기준이다.

사용자가 보는 큰 단계는 단순하게 유지한다.

```text
Bible → Episode Script → Director Brief → Render/Assemble → QC
```

세로 스크롤 연출과 이미지 일관성을 위해 내부 단계는 조금 더 세분한다.

```text
source
  ↓
story bible ─────→ visual bible/reference sheets
  ↓                         ↓
episode script → scroll plan → shot director briefs
                                  ↓
                         brief-to-image-prompt
                                  ↓
                    render tasks → image runtime
                                  ↓
                    lettering → vertical master
                                  ↓
                         platform slices → QC
```

## 기준 산출물과 파생 산출물

기준(canonical):

- `story-bible/story-bible.json`
- `visual-bible/**/*.json`과 승인된 기준 이미지
- `episodes/<id>/script.json`
- `episodes/<id>/scroll-plan.json`
- `episodes/<id>/briefs/*.json`

파생(derived):

- `render-tasks/*.json`: 브리프에서 결정적으로 재생성
- `art/*`: 외부 이미지 모델 결과
- `renders/episode-master.png`: 컷과 텍스트에서 재조립
- `publish/*`: 플랫폼 프로필로 재슬라이싱
- `qc-report.json`: 현재 상태에서 재검사

파생물이 직접 수정되면 다음 컴파일/조립에서 덮일 수 있다. 창작 변경은 기준 산출물에 반영한다.

## 데이터 계약

모든 기준 JSON은 `artifact_type`과 `schema_version`을 가진다. `schemas/v1`이 계약의 단일 기준이다. Schema로 표현하기 어려운 제약은 `webtoon_studio.validation`이 추가 검사한다.

### 디렉터 브리프의 공간 계약

- `camera.shot_size`: 컷 사이의 거리 리듬을 명시한다.
- `subjects[].bbox_norm`: 최종 생성 캔버스에서 인물이 차지할 예상 사각형이다.
- `subjects[].depth`: foreground/midground/background를 분리한다.
- `background.source_crop_norm`: 승인된 배경 시트의 어느 범위를 공간 기준으로 삼는지 표시한다.
- `background.depth_layers`: 전경에서 후경까지 읽힐 레이어를 순서대로 적는다.
- `text.reserved_regions`: 생성 시 비워 둘 영역이다.
- `scroll.*`: 컷 내부 구도와 별개로 마스터에서의 폭/앞뒤 여백을 정의한다.

좌표는 모두 좌상단 원점의 정규화 값이다. 픽셀 좌표보다 모델 캔버스나 최종 폭 변경에 강하고, 프롬프트에서는 사람이 읽기 쉬운 백분율로 변환한다.

## 캐릭터와 배경 시트

### 최초 캐릭터 시트

최초 생성은 `generate`다. 정면/측면/후면 전신을 같은 비율로 배치하고 표정 행, 의상/장비 디테일, 팔레트를 한 장에 넣는다. 장식적인 장면보다 비교 가능한 중립 시트를 우선한다.

### 파생 시트와 본편 컷

최초 시트가 승인되면 이후 작업은 `edit`가 된다. 캐릭터 기준 시트를 첫 레퍼런스로 두고, 추가 레퍼런스는 의상·표정/포즈·구도·배경 역할로 제한한다. 프롬프트는 다음을 분리한다.

- 바꿀 것: 이번 표정, 포즈, 카메라, 빛, 장면 행동
- 유지할 것: 얼굴 기하, 머리 구조, 신체 비율, 시그니처 소품, 팔레트

배경도 같은 방식으로 최초 공간 시트를 만들고, 이후 컷에서는 고정 랜드마크와 크롭 영역을 유지한다.

## 이미지 생성 경계

`webtoon_studio.image_runtime`은 이미지를 직접 생성하지 않는다. 검증된 render task를 Wangnov의 `gpt-image-2-skill` CLI 인자로 변환한다.

이 경계를 둔 이유:

- 인증 파일을 프로젝트 코드가 해석하거나 복사하지 않는다.
- Codex/OpenAI provider 차이를 한 모듈에서 처리한다.
- 생성 비용이 없는 compile/dry-run과 외부 호출인 execute를 구분한다.
- 실행기를 바꾸더라도 스토리/연출 스키마는 유지된다.

모든 task 입출력은 프로젝트 루트 아래의 상대 경로만 허용한다. 외부 레퍼런스는 먼저 프로젝트로 가져와 provenance를 남긴다.
여러 task를 함께 실행하면 출력-레퍼런스 의존성을 계산해 기준 시트 생성이 파생 편집보다 먼저 오도록 정렬한다.

Codex provider의 모델 선택은 실행기 기본값을 따른다. OpenAI provider만 설정상 `gpt-image-2`를 명시할 수 있다. 자동 provider fallback은 꺼져 있다.

## 이미지 크기와 세로 마스터

외부 실행기의 현재 제한을 검증한다.

- 각 변은 16의 배수
- 최소 655,360 픽셀
- 최대 8,294,400 픽셀
- 최대 변 3840px
- 최대 종횡비 3:1

따라서 2480×3508 A4 페이지는 총 픽셀 제한을 넘는다. 웹툰은 `1536x2048` 같은 컷/블록을 만들고 1080px 폭의 긴 마스터로 조립한다. 긴 마스터는 이미지 모델의 입력 크기 제한과 별개의 로컬 합성 결과다.

## 텍스트

기본값은 `deterministic_lettering`이다. 대사/캡션은 브리프에 정확히 보존하지만 이미지 프롬프트에서는 생성하지 않는다. 대신 조용한 영역을 확보한 뒤 Pillow 기반 레터링 단계에서 합성한다.

현재 레터링 구현은 검증 가능한 기본 기능이다. 실제 연재에서는 폰트 라이선스, 말풍선 꼬리, 화자별 스타일, 세로쓰기, 의성어 왜곡을 담당하는 별도 템플릿/렌더러를 확장하는 편이 좋다.

## 승인과 stale 판정

`tools/approve_stage.py`는 승인 대상 JSON의 canonical SHA-256과 파일 목록을 기록한다. 파일 내용이 바뀌면 mtime과 무관하게 승인은 stale이다. Render task도 원본 브리프의 해시를 가지고 있어 오래된 task의 실행을 거부한다.

승인은 두 층이다.

1. 창작 승인: 바이블/대본/연출 내용이 확정됐는가
2. 실행 승인: 외부 이미지 호출과 비용을 지금 발생시켜도 되는가

첫 번째 승인만으로 두 번째를 추론하지 않는다.

## QC 범위

자동 QC:

- JSON/geometry 유효성
- beat/sequence/shot 연결
- 계획 컷, 브리프, render task, 이미지 누락
- 브리프와 task 해시 일치
- 이미지와 슬라이스 크기
- 이전 컷 링크
- 레터링 anchor가 예약 영역 안에 있는지

사람/비전 검토:

- 얼굴과 신체/의상 일관성
- 손, 소품, 배경 지리 오류
- 감정 전달과 시선
- 스크롤 리빌과 읽는 순서
- 말풍선이 얼굴/손/핵심 행동을 가리는지

기술 검사가 통과해도 사람의 시각 승인 항목은 QC 리포트에 남긴다.

## 확장 포인트

- 플랫폼별 최신 업로드 제한을 별도 profile로 추가
- 정식 말풍선/SFX 스타일 시스템
- 이미지 임베딩이나 비전 모델을 통한 캐릭터 drift 점수
- 회차 비용 예측과 batch 승인
- 실패한 컷의 variant/selection provenance
- 번역판의 대사 overflow 검사
