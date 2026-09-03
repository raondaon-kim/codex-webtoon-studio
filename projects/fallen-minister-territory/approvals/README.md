# Approvals

`tools/approve_stage.py`가 승인한 JSON의 SHA-256 fingerprint를 여기에 기록합니다. 산출물이 바뀌면 승인은 자동으로 stale 상태가 됩니다.

이미지 실행 승인은 별도입니다. 승인 파일이 있어도 실제 외부 호출에는 `tools/run_image_tasks.py --execute`가 필요합니다.
