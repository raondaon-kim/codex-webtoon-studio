# Codex Webtoon Studio 작업 규칙

이 저장소에서 Codex는 사용자의 공동 작가이자 제작 오케스트레이터로 행동한다.

## 기준 파이프라인

1. 작품 루트(`<project-root>`, 기본 위치 `projects/<project-id>/`)의 `story-bible/story-bible.json`을 먼저 확정하고, 영지가 서사의 핵심이면 `territory/*-profile.json`으로 지리·환경·고질 문제를 개별 재난보다 먼저 정한다.
2. `<project-root>/visual-bible/**`를 확정한다.
3. 회차별 `script.json`을 작성한다.
4. `scroll-plan.json`에서 세로 리듬, 여백, 리빌을 설계한다.
5. 각 컷을 `briefs/*.json`으로 작성한다.
6. `brief-to-image-prompt` skill과 컴파일러로 `render-tasks/*.json`을 만든다.
7. 사용자의 실행 승인이 있을 때만 이미지 생성기를 `--execute`로 호출한다.
8. 레터링/조립/슬라이싱 후 `qc-report.json`을 생성한다.

앞 단계가 바뀌면 뒤 단계의 입력 해시를 다시 계산하고 재검토한다. 빈 승인 마커는 사용하지 않는다.

## 데이터 규칙

- 기준 산출물은 JSON이며 `schema_version`은 현재 `1.0`이다.
- 모든 정규화 좌표는 좌상단 원점의 `0..1` 값이다.
- bbox는 `x`, `y`, `width`, `height`이며 `x + width <= 1`, `y + height <= 1`이어야 한다.
- 배경 크롭도 같은 좌표계를 쓴다.
- 생성 캔버스는 각 변 16의 배수, 최대 변 3840, 최대 8,294,400 픽셀, 최대 종횡비 3:1을 지킨다.
- 컷 ID는 `shot-001`, 시퀀스 ID는 `seq-001`처럼 안정적으로 유지한다.
- 이미 승인/생성된 ID를 재사용해 다른 내용을 덮지 않는다.
- `territory_profile`의 재난 노출은 발생 후보일 뿐이다. 특정 재난과 발생 시점은 작품 루트의 에피소드 스크립트에서 확정한다.

## 이미지 및 일관성

- 캐릭터 최초 시트는 정면/측면/후면, 표정, 의상/소품, 팔레트를 포함한다.
- 이후 시트와 컷은 승인된 캐릭터 기준 이미지를 편집 레퍼런스로 사용한다.
- 여러 레퍼런스는 배열 순서와 역할을 모두 명시한다. 캐릭터 기준 시트를 먼저 둔다.
- 프롬프트에는 유지할 정체성 특징과 변경할 내용을 분리해서 쓴다.
- 살아 있는 작가의 화풍 복제를 요구하지 말고, 선·명암·색·재질·시대감 같은 일반 속성으로 표현한다.
- 기본 텍스트 모드는 `deterministic_lettering`이다. 이미지 프롬프트에는 대사/캡션/말풍선을 넣지 않는다.

## 실행 안전

- 이미지 생성은 비용과 외부 상태 변경이 있으므로 사용자의 명시적 승인 없이 `--execute`하지 않는다.
- 실행 전 `doctor`와 `auth inspect`를 사용하되 인증 원문을 출력하거나 파일에 복사하지 않는다.
- `auth.json`, API 키, 액세스/리프레시 토큰을 커밋하지 않는다.
- Codex provider에서 지원하지 않는 옵션은 전달하지 않는다. provider fallback은 자동으로 켜지 않는다.
- 생성 실패 시 동일 task ID의 결과를 성공으로 표시하지 않는다.

## 변경 후 검증

```powershell
python -m unittest discover -s tests -v
python tools/validate_artifacts.py examples/project
python tools/compile_render_tasks.py examples/project/episodes/ep001/briefs --project-root examples/project --check
```

## New-PC bootstrap

Open the cloned repository at its root and keep project-specific artifacts
under `projects/<project-id>/`; do not introduce PC-specific absolute paths.

1. Install Python 3.11 or later, then run `python -m pip install -e .` from
   the repository root.
2. Start Codex where it can read the repository-local `.agents/skills/`.
   Keep `.agents/skills/`, `assets/`, `schemas/`, and `config/` in the clone;
   they are the portable studio contract and must not be copied into a user
   home directory.
3. Install the image CLI once on the new PC: `npm install --global
   gpt-image-2-skill` (or `cargo install gpt-image-2-skill --locked` when
   using Rust). Confirm it with `gpt-image-2-skill --provider codex doctor`
   and `gpt-image-2-skill auth inspect`; redact their output and never save it
   to the repository. `python tools/run_image_tasks.py ...` stays dry-run
   until the user explicitly approves `--execute`.
4. Let Codex sign in on the new PC. Its credentials stay in
   `$CODEX_HOME/auth.json`; never copy `auth.json`, API keys, or tokens into
   this repository.
5. Prove the local setup before creating art:

```powershell
python -m unittest discover -s tests -v
python tools/validate_artifacts.py examples/project
python tools/compile_render_tasks.py examples/project/episodes/ep001/briefs --project-root examples/project --check
python tools/generate_lettering_reference_sheet.py
```

### Approved lettering contract

- Use the bundled `NanumGothic-Regular.ttf` for dialogue, thought, and
  narration. Use `NanumGothic-Bold.ttf` only for emphasized SFX. Never depend
  on a system-installed font.
- Render ordinary dialogue balloons text-first, then add a short, broad tail
  as part of the same outer contour. Do not leave a line at the tail join or
  use a long needle-like tail for routine dialogue.
- `assets/lettering/lettering-standard-v2.json` is the single source of truth
  for the approved numeric limits and exceptions. A change requires an updated
  reference sheet, renderer tests, and recomposition of affected episodes.
