# 🧪 Cosmetics Formulation AI

AI 기반의 화장품 제형 설계 및 단가 분석/공정 엔지니어링 웹 애플리케이션입니다.

기존 화장품 라벨의 전성분을 OCR 이미지 분석(Google Gemini Vision)으로 추출하거나 인공지능 신규 설계를 통해 1,000g 조제 기준 최적 배합비와 총 원가를 계산하고, 맞춤형 제조 공정 가이드와 제품 스펙 시트까지 한 번에 자동 생성합니다.

---

## 🌟 주요 기능

1. **AI 기반 제형 설계**: 세럼, 로션, 크림, 토너, 앰플, 클렌저 등 6가지 대표 제형 중 선택하여 배합 설계
2. **라벨 영역 지정 분석**: 라벨 업로드 후 성분표 부위만 드래그하여 정확하게 지정(Cropping)해 전성분 자동 추출 및 처방 연동
3. **인터랙티브 시각화**: 마우스 오버로 성분 상세 정보를 확인하고 휠/드래그로 제어가 가능한 동적 도넛 차트 제공
4. **원료 단가 DB 관리**: CSV 형식의 데이터베이스 파일 내보내기/가져오기(업로드) 기능 및 실시간 데이터 편집 지원
5. **처방 커스텀 수정 피드백 루프**: 생성된 배합에 대화식 피드백(예: "보습력 향상", "단가 20% 인하")을 입력하여 처방 및 공정을 실시간 재구성
6. **상세 리포트 자동 생성**: 배합표와 차트가 포함된 Excel 파일 다운로드, 단계별 제조 공정 가이드, 제형 효능 스펙 시트 생성

---

## 🚀 로컬 실행 방법

로컬 터미널에서 아래 지침에 따라 손쉽게 애플리케이션을 구동할 수 있습니다.

### 1. 패키지 설치
프로젝트 루트 폴더에서 다음 명령을 실행하여 의존성 패키지를 설치합니다.
```bash
pip install -r requirements.txt
```

### 2. Gemini API 키 설정 (선택)
실행 전에 환경 변수로 API 키를 등록하면 웹앱 내부에서 입력 단계를 건너뛰고 즉시 사용 가능합니다.
- **Windows (PowerShell)**:
  ```powershell
  $env:GEMINI_API_KEY="본인의_API_키"
  ```
- **Windows (cmd)**:
  ```cmd
  set GEMINI_API_KEY=본인의_API_키
  ```
- **macOS / Linux**:
  ```bash
  export GEMINI_API_KEY="본인의_API_키"
  ```

### 3. 애플리케이션 실행
```bash
streamlit run app.py
```
명령어를 실행하면 웹 브라우저 창(`http://localhost:8501`)이 자동으로 열립니다.

💡 **빠른 시작**: 제공되는 [run_local.bat](run_local.bat) 배치 파일을 더블클릭하거나 터미널에서 실행하면 가상환경 생성, 패키지 설치 및 실행까지 자동으로 처리됩니다.

---

## ☁️ GitHub 및 Streamlit Cloud 배포 방법

이 저장소를 GitHub에 업로드한 뒤 Streamlit Cloud를 활용해 전 세계 어디서나 URL 접속이 가능하게 배포할 수 있습니다.

### 1. GitHub 리포지토리 생성 및 업로드
1. GitHub 계정에 새 저장소(Public 또는 Private)를 생성합니다.
2. 아래 명령어로 로컬 코드를 리포지토리에 푸시합니다.
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Cosmetics Formulation AI"
   git branch -M main
   git remote add origin <GitHub_리포지토리_URL>
   git push -u origin main
   ```

### 2. Streamlit Community Cloud 배포
1. [Streamlit Community Cloud](https://share.streamlit.io/)에 접속하여 로그인합니다.
2. 우측 상단의 **"New app"** 버튼을 클릭합니다.
3. 생성한 GitHub 리포지토리, 브랜치(`main`), 그리고 실행 파일 파일명(`app.py`)을 입력합니다.
4. **Advanced settings**를 클릭한 후, **Secrets** 입력 란에 아래와 같이 Gemini API 키를 등록합니다:
   ```toml
   GEMINI_API_KEY = "본인의_Gemini_API_키"
   ```
5. **"Deploy!"** 버튼을 누르면 배포가 완료되며, 생성된 URL을 통해 웹 서비스 접속이 가능해집니다.
