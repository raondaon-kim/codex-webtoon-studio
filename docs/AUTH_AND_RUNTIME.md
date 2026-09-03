# Image authentication and runtime

## 책임 분리

이 프로젝트는 토큰을 읽거나 갱신하지 않는다. 외부 `gpt-image-2-skill` 실행기가 provider 선택, Codex 자격 증명 탐색, 토큰 갱신, 이미지 응답 저장을 담당한다.

기본 설치:

```powershell
npm install -g gpt-image-2-skill
```

또는 실행 파일의 절대 경로를 `GPT_IMAGE_2_SKILL_BIN` 환경 변수로 지정할 수 있다.

## Codex provider

```powershell
gpt-image-2-skill --json --provider codex doctor
gpt-image-2-skill --json auth inspect
```

실행기는 Codex의 자격 증명 저장소 설정 및 기본 `CODEX_HOME/auth.json` 위치를 사용한다. 프로젝트에는 파일을 복사하지 않는다. `auth.json`은 평문 비밀로 취급하고 이메일, 채팅, 이슈, 로그, 저장소에 올리지 않는다.

이 provider는 서드파티 실행기가 Codex/ChatGPT 인증과 이미지 도구 호출을 연결하는 방식이다. 외부 동작이 바뀌어도 나머지 파이프라인에 영향이 퍼지지 않도록 어댑터 뒤에 격리했다.

## OpenAI provider

공식 API 기반 자동화가 필요하면 `config/image-provider.json`의 provider를 `openai`로 바꾸고 실행기가 지원하는 안전한 비밀 저장소나 `OPENAI_API_KEY`를 사용한다. 이 경우 모델은 `gpt-image-2`로 명시된다.

provider는 자동 fallback하지 않는다. 어느 계정/과금 경로를 썼는지 모호해지는 것을 막기 위해 사용자가 설정을 직접 바꿔야 한다.

## 실행 순서

```powershell
python tools/compile_render_tasks.py episodes/ep001/briefs --project-root .
python tools/run_image_tasks.py episodes/ep001/render-tasks --project-root .
python tools/run_image_tasks.py episodes/ep001/render-tasks --project-root . --execute
```

두 번째 줄은 명령과 preflight warning만 보여 준다. 세 번째 줄만 외부 호출을 수행한다. 실행 직전에 다음을 검사한다.

- render task schema
- 원본 브리프의 content hash
- 모든 edit 레퍼런스 파일
- 실행기 존재 여부
- provider doctor/auth 상태

stdout의 알려진 민감 키는 저장/표시 전에 제거한다. 그래도 터미널과 CI 로그는 비밀 자료로 다룬다.
