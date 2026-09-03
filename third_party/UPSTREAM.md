# Upstream attribution

이 저장소는 아래 MIT 프로젝트의 설계와 일부 구현 아이디어를 개작했습니다.

## codex-novel-to-comic-studio

- Repository: https://github.com/lhfer/codex-novel-to-comic-studio
- Reviewed revision: `7c64ef96b0ccb28a55ae514e185e92cb2364daac`
- Used concepts: staged pipeline, explicit approvals, source ingestion, assembly and QC command layout
- Changes here: A4/page workflow를 vertical-scroll/shot workflow로 교체하고, Markdown marker validation 대신 versioned JSON contracts와 content hashes를 사용합니다. EPUB 내부 경로는 Windows에서도 POSIX ZIP 경로로 처리합니다.

## gpt-image-2-skill

- Repository: https://github.com/wangnov/gpt-image-2-skill
- Reviewed revision: `05f46b0b1cdf2b6bd4cfe2ad85df6b2aafb4de7a`
- Used concepts/API: CLI JSON envelope, provider selection, `images generate`, `images edit`, repeated `--ref-image`, `doctor`, `auth inspect`, Codex credential resolution
- Integration: 코드를 복제하지 않고 외부 CLI 어댑터 경계로 연결합니다.

## GPT-Image2-Skill prompt gallery

- Repository: https://github.com/wuyoscar/GPT-Image2-Skill
- Reviewed revision: `068dd9e24aadc8731e46f38548ca4dcd94515d35`
- Used concepts: character turnaround/expression/equipment sheet layout, manga panel structure, multi-reference role declaration, edit prompts that separate changes from invariants
- Changes here: 특정 저작물·캐릭터·작가 화풍 예시는 복사하지 않고 오리지널 웹툰용 일반 프롬프트 계약으로 재작성했습니다.

각 업스트림의 MIT 라이선스 고지는 동일 디렉터리의 라이선스 파일에 보존합니다.
