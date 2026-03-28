# .c9 디렉토리 설명

AWS Cloud9 IDE의 환경 설정 파일들이 저장된 디렉토리입니다.

## 파일 구조

```
.c9/
├── project.settings          # Cloud9 프로젝트 설정
├── launch.json               # 실행 구성 (비어있음)
├── tasks.json                # 태스크 구성 (비어있음)
├── .nakignore                # Cloud9 파일 탐색기 무시 패턴
├── out_of_memory             # 메모리 부족 감지 파일
├── ajuuniv-10-c9-kiro/
│   └── meta.json             # Cloud9 환경 메타데이터 (환경 ID, 이름)
├── amazonwebservices.aws-toolkit-vscode/
│   ├── devfile.schema.json   # AWS Toolkit DevFile JSON 스키마
│   └── sam.schema.json       # AWS SAM 템플릿 JSON 스키마
└── metadata/                 # 파일별 에디터 메타데이터 (열린 탭, 커서 위치 등)
```

## 주요 파일 설명

### project.settings
Cloud9 IDE 프로젝트 전역 설정입니다.
- `@automaticShutdown: 30` - 30분 비활성 시 자동 종료
- `@aws.samcli.lambdaTimeout: 90000` - Lambda 로컬 실행 타임아웃 90초
- JavaScript Tern 자동완성 설정 (browser, ecma5, jQuery)
- Python 라이브러리 경로 설정

### ajuuniv-10-c9-kiro/meta.json
현재 Cloud9 환경 정보입니다.
- 환경 ID: `ajuuniv-10-c9-kiro`
- 환경 이름: `ajuuniv-10-c9-kiro`

### amazonwebservices.aws-toolkit-vscode/
AWS Toolkit 확장의 JSON 스키마 파일들입니다.
- `devfile.schema.json` - AWS DevFile 형식 검증용 스키마
- `sam.schema.json` - AWS SAM(Serverless Application Model) 템플릿 검증용 스키마

### metadata/
각 파일의 에디터 상태(열린 탭, 커서 위치, 스크롤 위치 등)를 저장합니다.

## 참고사항
- 이 디렉토리는 Cloud9 IDE 전용 설정으로, 다른 환경에서는 사용되지 않습니다.
- `sam.schema.json`은 12MB로 AWS SAM 전체 스키마를 포함합니다.
- 실제 프로젝트 코드는 `tournament/` 디렉토리에 있습니다.
