#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
더미 루틴 데이터를 DB에 삽입하는 스크립트
"""

import mysql.connector
from datetime import datetime, timedelta

# app.py에서 DB_CONFIG 가져오기
import sys
sys.path.append('.')
from app import DB_CONFIG

def insert_dummy_routines():
    """더미 루틴 데이터를 routine 테이블에 삽입"""
    
    try:
        # DB 연결
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # user_id = 6으로 설정
        user_id = 6
        
        # user_id가 존재하는지 확인
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ user_id={user_id} 사용")
        else:
            print(f"❌ user_id={user_id}가 users 테이블에 존재하지 않습니다.")
            return
        
        # 데이터 정리
        routines = [
            {
                'name': '아침 기상',
                'content': '매일 7시에 일어나기',
                'time': '07:00:00',
                'is_success': 1,
                'options': [
                    {'minutes': 10, 'text': '기상 알림', 'timing': '전'},
                    {'minutes': 5, 'text': '준비 완료 체크', 'timing': '후'}
                ]
            },
            {
                'name': '학교 준비',
                'content': '도시락 챙기기',
                'time': '08:00:00',
                'is_success': 1,
                'options': [
                    {'minutes': 5, 'text': '준비 시작', 'timing': '전'}
                ]
            },
            {
                'name': '학교 가기',
                'content': '가방 확인하고 버스 타기',
                'time': '08:30:00',
                'is_success': 1,
                'options': []
            },
            {
                'name': '저녁 식사',
                'content': '6시에 가족과 함께 식사',
                'time': '18:00:00',
                'is_success': 1,
                'options': []
            },
            {
                'name': '숙제하기',
                'content': '오늘 배운 내용 복습하기',
                'time': '19:00:00',
                'is_success': 0,
                'options': []
            },
            {
                'name': '저녁 독서',
                'content': '책 30분 읽기',
                'time': '19:30:00',
                'is_success': 0,
                'options': []
            },
            {
                'name': '이 닦기',
                'content': '잠자기 전 양치',
                'time': '21:00:00',
                'is_success': 1,
                'options': []
            },
            {
                'name': '정리 시간',
                'content': '장난감 정리',
                'time': '21:10:00',
                'is_success': 0,
                'options': []
            },
            {
                'name': '목욕하기',
                'content': '저녁에 목욕하기',
                'time': '20:00:00',
                'is_success': 1,
                'options': []
            },
            {
                'name': '옷 입기',
                'content': '내일 입을 옷 준비하기',
                'time': '21:20:00',
                'is_success': 1,
                'options': []
            },
            {
                'name': '거실 정리',
                'content': '사용한 물건 제자리에 두기',
                'time': '21:30:00',
                'is_success': 0,
                'options': []
            },
            {
                'name': '잠자리 준비',
                'content': '이불 정리하고 자리 누기',
                'time': '22:00:00',
                'is_success': 1,
                'options': []
            }
        ]
        
        # 날짜 범위 설정 (10월 19일 ~ 10월 23일, 5일간)
        start_date = datetime(2025, 10, 19)
        end_date = datetime(2025, 10, 23)
        
        inserted_count = 0
        
        # 각 날짜마다 루틴 삽입
        current_date = start_date
        while current_date <= end_date:
            print(f"\n📅 {current_date.strftime('%Y-%m-%d')} 루틴 삽입 중...")
            
            for routine in routines:
                # 각 날짜의 해당 시간으로 routine_time 생성
                routine_time_str = f"{current_date.strftime('%Y-%m-%d')} {routine['time']}"
                routine_time = datetime.strptime(routine_time_str, '%Y-%m-%d %H:%M:%S')
                
                # routine 테이블에 삽입
                cursor.execute("""
                    INSERT INTO routine (user_id, routin, routine_time, routine_content, is_success)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, routine['name'], routine_time, routine['content'], routine['is_success']))
                
                routine_id = cursor.lastrowid
                print(f"  ✅ {routine['name']} (ID: {routine_id})")
                
                # routine_options 테이블에 삽입
                for option in routine['options']:
                    cursor.execute("""
                        INSERT INTO routine_options (routine_id, minut, option_content, timing_type)
                        VALUES (%s, %s, %s, %s)
                    """, (routine_id, option['minutes'], option['text'], option['timing']))
                
                inserted_count += 1
            
            # 다음 날로 이동
            current_date += timedelta(days=1)
        
        # 커밋
        conn.commit()
        print(f"\n✅ 총 {inserted_count}개의 루틴이 성공적으로 삽입되었습니다.")
        
        # 삽입된 데이터 확인
        cursor.execute("""
            SELECT COUNT(*) FROM routine WHERE user_id = %s
        """, (user_id,))
        total_count = cursor.fetchone()[0]
        print(f"📊 user_id={user_id}의 총 루틴 수: {total_count}")
        
        # 성공/실패 통계
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_success = 1 THEN 1 ELSE 0 END) as completed
            FROM routine 
            WHERE user_id = %s
        """, (user_id,))
        stats = cursor.fetchone()
        completion_rate = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
        print(f"📈 완료율: {stats[1]}/{stats[0]} ({completion_rate:.1f}%)")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("\n🔌 DB 연결 종료")

if __name__ == '__main__':
    print("="*80)
    print("더미 루틴 데이터 삽입 시작")
    print("="*80)
    insert_dummy_routines()
