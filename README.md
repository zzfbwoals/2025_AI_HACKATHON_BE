<div align="center">
  
# [2025 캡스톤 디자인 및 AI 해커톤]  4팀 - ROUTY 👪

루틴 관리 Flutter 애플리케이션

<img width="1212" height="682" alt="image" src="https://github.com/user-attachments/assets/b047d5bd-2216-4e5b-9a2a-dfdbf01cdf50" />

**"AI 챗봇 기반 소아 ADHD 아동 일상·수면 관리 및 부모 지원 플랫폼"**
</div>

---
## 서비스 배경

<img width="70%" height="70%" alt="image" src="https://github.com/user-attachments/assets/15b0cc85-1b95-4791-810b-5e429b6aa950" />

- 대부분의 부모들은 약물을 통한 아이의 ADHD 치료를 꺼림
- ADHD 아동청소년은 정상 아동에 비해 2~3배 많은 수면 관련 문제를 보임 <br>(https://www.sleep.or.kr/html/?pmode=UserAddon&smode=ajax&fn=ViewFile&fileSeq=6966)
- 미국 신시내티 아동 병원 연구진은 ADHD인 10대들을 대상으로 일주일 동안 6.5시간 수면을 취한 그룹과 9.5시간 취한 그룹을 비교 <br>→ 그 결과 9.5시간 수면을 취한 그룹이 작업기억, 계획 및 조직, 감정 조절, 결단성면에서 더 좋은 결과 성취 <br>(https://pubmed.ncbi.nlm.nih.gov/30768404/)

---
## 문제 해결 목표
본 프로젝트에서 AI를 활용하여 사용자의 하루 패턴, 감정, 관심사를 기반으로 실행 가능한 작은 단위의 루틴을 자동 설계하고 아동 맞춤 챗봇 캐릭터와 보상 시스템을 통해 과제 이행 동기를 높이며 부모/교사에게 코칭 리포트를 제공하여 소아 청소년의 주의력 향상 및 일상생활 루틴 관리를 지원하는 서비스를 개발한다.

---
## 주요 기능

- 🏠 **홈화면**: 모던한 디자인의 대시보드
- 👤 **마이페이지**: 사용자 정보 및 설정 관리
- 📅 **루틴 관리**: 루틴 목록 및 생성 기능
- 🔐 **인증 시스템**: 로그인/회원가입 페이지
- 🎨 **통일된 디자인**: IonIcons 사용으로 일관된 UI/UX

---
## 기술스택

<img width="273" height="282" alt="제목 없음1" src="https://github.com/user-attachments/assets/51354d5b-6d3c-43f5-a07b-deb2096aa950" />

---
## 프로젝트 시작하기

### 1. 환경 설정

#### 1.1 Python 패키지 설치
```bash
pip install flask flask-cors bcrypt mysql-connector-python openai
```

#### 1.2 데이터베이스 설정 (MySQL Workbench)

1. MySQL Workbench 실행 후 root 계정으로 로컬 연결
2. `DB/init.sql` 스크립트 실행:
   - `File` → `Open SQL Script` → `DB/init.sql` 선택
   - 전체 스크립트 실행 (⌘+⇧+Enter 또는 ⚡ 버튼)
   - 생성된 테이블 확인: `users`, `routine`, `characters` 등

3. **중요**: `app.py`의 DB 연결 정보 수정:
   ```python
   DB_CONFIG = {
       'host': '127.0.0.1',
       'user': 'root',  # 또는 본인이 사용하는 계정
       'password': 'YOUR_MYSQL_PASSWORD',  # 본인의 MySQL 비밀번호
       'database': 'myapp'
   }
   ```

#### 1.3 백엔드 서버 실행
```bash
cd 2025_AI_HACKATHON_BE-main
python3 app.py
```
서버가 `http://0.0.0.0:5001`에서 실행됩니다.

#### 1.4 환경 변수 설정 (선택사항)
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. 프론트엔드 설정

#### 2.1 Flutter 앱 실행
```bash
cd flutter_hackathon_project
flutter run
```

#### 2.2 API 연결 확인
- `lib/constants/app_constants.dart`에서 `baseUrl`이 `http://localhost:5001`로 설정되어 있는지 확인

---
## 팀원 소개

<table>
<tr>
<td align="center">
<a href="https://github.com/fufckddl" target="_blank">
<img src="https://avatars.githubusercontent.com/fufckddl" width="60px;" alt="김태현"/><br />
<b>이창렬</b>
</a><br/>
팀장 / 프론트
</td>
<td align="center">
<a href="https://github.com/minjini-sys" target="_blank">
<img src="https://avatars.githubusercontent.com/minjini-sys" width="60px;" alt="최희우"/><br />
<b>김민진</b>
</a><br/>
백엔드
</td>
<td align="center">
<a href="https://github.com/rhehdud" target="_blank">
<img src="https://avatars.githubusercontent.com/rhehdud" width="60px;" alt="김사랑"/><br />
<b>고도영</b>
</a><br/>
백엔드
</td>
<td align="center">
<a href="https://github.com/ujieeemin" target="_blank">
<img src="https://avatars.githubusercontent.com/ujieeemin" width="60px;" alt="유한솔"/><br />
<b>유지민</b>
</a><br/>
기획 / 자료
</td>
<td align="center">
<a href="https://github.com/zzfbwoals" target="_blank">
<img src="https://avatars.githubusercontent.com/zzfbwoals" width="60px;" alt="류재민"/><br />
<b>류재민</b>
</a><br/>
기획 / 자료
</td>
</tr>
</table>

---

## 프로젝트 링크

- [Notion 기획서 (MVP)](https://www.notion.so/2025-AI-4-ROUTY-296087d76afe80128dcee38b384e2962)  
- [GitHub FE 리포지토리](https://github.com/zzfbwoals/2025_AI_HACKATHON_FE)  
- [GitHub BE 리포지토리](https://github.com/zzfbwoals/2025_AI_HACKATHON_BE)

---

© 2025 AI HACKATHON Team 4
