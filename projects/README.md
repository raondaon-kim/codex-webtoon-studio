# Projects

각 웹툰은 `projects/<project-id>/`를 독립된 작품 루트로 사용합니다. 작품 루트는 다음을 가집니다.

```text
config/project.json       작품 제목·언어·화면 규격·작업 정책
source/                   원작과 조사 자료
story-bible/              스토리 바이블
territory/                영지·지역 환경 프로필 (필요한 작품만)
visual-bible/             캐릭터·배경·소품 기준 시트와 승인 이미지
episodes/                 회차별 대본·플랜·브리프·렌더·QC
approvals/                내용 승인 fingerprint
logs/                     비밀이 제거된 실행 기록
```

공통 스키마, prompt template, 이미지 실행기 설정, 플랫폼 프로필, CLI는 저장소 루트에만 둡니다. 새 작품은 이 구조를 복사한 뒤 `config/project.json`의 `project_id`와 제목을 먼저 바꿉니다.
