# Book Keeper - PDF Contradiction Detector 📚🔍

소프트웨어 설계 책의 PDF 파일들을 분석하여 챕터 간 논리적 모순을 자동으로 검출하는 AI 기반 검수 도구입니다.

## 주요 기능

- 📄 **PDF 챕터 자동 추출**: 다양한 형식의 챕터 구분 패턴 지원 (영어/한국어)
- 🧠 **벡터 임베딩**: OpenAI Embeddings API를 사용한 의미론적 텍스트 분석
- 🗄️ **벡터 DB**: Qdrant를 활용한 효율적인 유사도 검색
- 🤖 **LLM 기반 모순 검출**: GPT-4o 또는 Claude Sonnet 4를 활용한 정교한 논리적 모순 분석
- 📊 **다양한 리포트 형식**: JSON, Markdown 형식의 상세 분석 리포트

## 시스템 요구사항

- Python 3.10+
- Conda (Anaconda 또는 Miniconda)
- Docker (Qdrant 실행용)
- API Keys:
  - ANTHROPIC_API_KEY (Claude Sonnet 4 사용 시 - 기본값)
  - OPENAI_API_KEY (GPT-4o 사용 시 - 선택사항)

## 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/book-keeper.git
cd book-keeper
```

### 2. 환경 설정
```bash
# Setup 스크립트 실행
./setup.sh

# 또는 수동으로 conda 환경 생성
conda env create -f environment.yml
conda activate book-keeper
```

### 3. 환경 변수 설정
```bash
cp .env_example .env
# .env 파일을 열어 API 키 추가
# - ANTHROPIC_API_KEY (Claude Sonnet 4 사용 시 - 기본값)
# - OPENAI_API_KEY (GPT-4o 사용 시 - 선택사항)
```

### 4. Qdrant 실행

#### 옵션 1: Docker Compose 사용 (추천)
```bash
# Docker Compose로 Qdrant 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f qdrant

# 중지
docker-compose down
```

#### 옵션 2: Docker 직접 실행
```bash
# Docker를 사용하여 Qdrant 시작
docker run -p 6345:6333 -p 6346:6334 \
  -v $(pwd)/data/qdrant:/qdrant/storage:z \
  qdrant/qdrant
```

### 5. PDF 검수 실행

#### 테스트 모드 (추천 - Rate Limit 방지)
```bash
# Claude Sonnet 4 사용 (기본)
./run_test.sh

# GPT-4o 사용
./run_test.sh --openai

# 또는 직접 실행
python rag_pdf_checker.py --test          # Claude Sonnet 4 (기본값)
python rag_pdf_checker.py --test --openai # GPT-4o
python rag_pdf_checker.py --test --gpt    # GPT-4o (동일)
```

#### 전체 실행
```bash
# Claude Sonnet 4로 모든 챕터 쌍 확인 (기본)
python rag_pdf_checker.py

# GPT-4o로 모든 챕터 쌍 확인
python rag_pdf_checker.py --openai
```

## 사용 방법

### 기본 사용법

1. 검수할 PDF 파일들을 `pdf/` 폴더에 넣습니다.
2. 스크립트를 실행하면 자동으로:
   - 각 PDF에서 챕터를 추출
   - 챕터별 임베딩 생성 및 벡터 DB 저장
   - 모든 챕터 쌍에 대해 모순 검사
   - 결과 리포트 생성

### 지원하는 챕터 패턴

- `Chapter 1`, `CHAPTER I` (영어)
- `1장`, `제1장` (한국어)
- `1. 제목` (숫자 형식)
- `PART 1` (파트 구분)

## 출력 결과

### 1. contradictions.json
```json
{
  "generated_at": "2024-01-01T10:00:00",
  "total_contradictions": 2,
  "contradictions": [
    {
      "doc1_id": "book_1_hash",
      "doc2_id": "book_4_hash",
      "type": "definition",
      "confidence": 0.85,
      "explanation": "두 문서에서 데이터 레이크의 정의가 상충됩니다."
    }
  ]
}
```

### 2. contradictions_report.md
마크다운 형식의 상세한 분석 리포트

### 3. 콘솔 출력
색상이 적용된 요약 정보

### 4. contradictions_detailed_report.md (show_results.py로 생성)
```bash
# 결과 확인 및 상세 보고서 생성
python show_results.py
```
- 콘솔에 결과를 표시하고 동시에 상세한 마크다운 보고서 생성
- 이모지와 구조화된 섹션으로 가독성 향상
- 모순별 상세 분석, 유형별 통계, 결론 포함

## 프로젝트 구조

```
book-keeper/
├── pdf/                        # PDF 파일 저장 폴더
├── rag_pdf_checker.py         # 메인 스크립트
├── environment.yml            # Conda 환경 설정
├── requirements.txt           # Python 패키지 목록
├── setup.sh                   # 설정 자동화 스크립트
├── run_test.sh               # 테스트 모드 실행 스크립트
├── show_results.py           # 결과 확인 및 상세 보고서 생성
├── monitor_results.py        # 실시간 결과 모니터링
├── analyze_chapters.py       # 추출된 챕터 분석
├── test_system.py            # 시스템 테스트
├── .env_example              # 환경 변수 예시
├── docker-compose.yml        # Qdrant Docker 설정
├── contradictions.json       # JSON 결과 (생성됨)
├── contradictions_report.md  # 간단한 Markdown 리포트 (생성됨)
└── contradictions_detailed_report.md  # 상세 Markdown 리포트 (show_results.py로 생성)
```

## 고급 설정

### 커스텀 임베딩 모델 사용
```python
# HuggingFace 모델 사용 시 (현재 미구현)
embedding_manager = EmbeddingManager(model_type="huggingface")
```

### 모순 검출 임계값 조정
```python
# _detect_all_contradictions 메서드에서
if contradiction and contradiction.confidence_score > 0.6:  # 기본값 0.6
```

## UI 인터페이스 (선택사항)

### Gradio UI
```bash
python ui_gradio.py
```

### Streamlit UI
```bash
streamlit run ui_streamlit.py
```

## 주의사항

- OpenAI API 사용량에 따른 비용이 발생할 수 있습니다.
- 대용량 PDF 처리 시 시간이 오래 걸릴 수 있습니다.
- Qdrant는 로컬에서 실행되어야 합니다.

## 문제 해결

### Qdrant 연결 오류
```bash
# Qdrant가 실행 중인지 확인
docker ps | grep qdrant

# 포트가 사용 중인 경우
lsof -i :6345
```

### OpenAI API 오류
- API 키가 올바르게 설정되었는지 확인
- API 사용량 한도 확인

## 기여하기

버그 리포트, 기능 제안, PR은 언제나 환영합니다!

## 라이선스

MIT License

---

Made with ❤️ by Mentat Alpha - 멘타트 시스템의 첫 실행 요원 