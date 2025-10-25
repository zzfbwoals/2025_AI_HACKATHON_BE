#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROUTY AI 코칭 인사이트 생성 - 프롬프트 테스트
"""

# 더미 데이터 (실제 DB 대신 사용)
DUMMY_ROUTINE_DATA = """
**전체 통계:**
- 총 루틴 수: 12개
- 완료된 루틴: 8개
- 완료율: 66.7%

**요일별 완료 상황:**
- 2025-10-19: 2/2 완료
- 2025-10-20: 2/3 완료
- 2025-10-21: 1/2 완료
- 2025-10-22: 2/2 완료
- 2025-10-23: 1/3 완료

**루틴 상세 내역:**
1. 아침 기상: 매일 7시에 일어나기 (✅ 완료)
2. 학교 준비: 도시락 챙기기 (✅ 완료)
3. 학교 가기: 가방 확인하고 버스 타기 (✅ 완료)
4. 저녁 식사: 6시에 가족과 함께 식사 (✅ 완료)
5. 숙제하기: 오늘 배운 내용 복습하기 (⏳ 미완료)
6. 저녁 독서: 책 30분 읽기 (⏳ 미완료)
7. 이 닦기: 잠자기 전 양치 (✅ 완료)
8. 정리 시간: 장난감 정리 (⏳ 미완료)
9. 목욕하기: 저녁에 목욕하기 (✅ 완료)
10. 옷 입기: 내일 입을 옷 준비하기 (✅ 완료)
11. 거실 정리: 사용한 물건 제자리에 두기 (⏳ 미완료)
12. 잠자리 준비: 이불 정리하고 자리 누기 (✅ 완료)
"""

CHILD_INFO = {
    'name': '민수',
    'age': 7
}

# System Prompt
SYSTEM_PROMPT = f"""당신은 ADHD 아동을 위한 전문 루틴 관리 앱 'ROUTY'의 AI 코치입니다.
아이의 이름: {CHILD_INFO['name']}
아이의 나이: {CHILD_INFO['age']}세

**주요 역할:**
1. 루틴 이행 데이터를 분석하여 맞춤형 인사이트 제공
2. 긍정적 강화와 부드러운 개선 제안 제공
3. ADHD 아동의 특성을 고려한 실용적인 코칭 제안

**응답 형식:**
다음 구조로 JSON 형식으로 응답해주세요:
{{
  "summary_insight": "1주일 데이터 요약 (2-3문장)",
  "custom_coaching_phrase": "아이를 격려하는 맞춤 코칭 문구 (1문장)",
  "adaptation_rate": "{CHILD_INFO['name']}의 1주일간 루틴 적응도 (0-100%)",
  "coaching_insights": {{
    "strengths": ["잘하고 있는 점 1", "잘하고 있는 점 2"],
    "improvements": ["개선할 점 1", "개선할 점 2"],
    "suggestions": ["코칭 제안 1", "코칭 제안 2"]
  }}
}}"""

# User Prompt
USER_PROMPT = f"""다음은 {CHILD_INFO['name']}({CHILD_INFO['age']}세)의 최근 7일간 루틴 이행 데이터입니다:

{DUMMY_ROUTINE_DATA}

위 데이터를 바탕으로 JSON 형식으로 코칭 인사이트를 제공해주세요."""

print("="*80)
print("ROUTY AI 코칭 인사이트 - 프롬프트")
print("="*80)
print("\n[System Prompt]")
print(SYSTEM_PROMPT)
print("\n" + "="*80 + "\n")
print("[User Prompt]")
print(USER_PROMPT)
print("\n" + "="*80)
