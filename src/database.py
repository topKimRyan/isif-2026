import psycopg2
from psycopg2.extras import Json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
from datetime import datetime

class DatabaseManager:
    """Supabase PostgreSQL 데이터베이스 연결 및 관리 클래스"""
    
    def __init__(self):
        # .env 파일에서 환경 변수 로드
        load_dotenv()
        
        self.connection_params = {
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT", "5432"),
            "dbname": os.getenv("DB_NAME")
        }
        
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """데이터베이스 연결"""
        self.connection = psycopg2.connect(**self.connection_params)
        self.cursor = self.connection.cursor()
        self.cursor.execute("SET TIME ZONE 'Asia/Seoul'")
        print(f"✅ 데이터베이스 연결 성공: {self.connection_params['host']}")
    
    def disconnect(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("✅ 데이터베이스 연결 종료")
    
    def create_tables(self):
        """results.json 데이터를 저장할 테이블 생성"""
        
        # gambling_urls 테이블 생성
        create_table_query = """
        CREATE TABLE IF NOT EXISTS gambling_urls (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            keyword_used TEXT NOT NULL,
            collected_at TIMESTAMP WITH TIME ZONE NOT NULL,
            is_illegal BOOLEAN NOT NULL,
            gemini_confidence NUMERIC(3, 2),
            gemini_reason TEXT,
            gemini_error TEXT,
            detected_keywords JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # URL에 대한 인덱스 생성 (검색 성능 향상)
        create_index_url = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_url 
        ON gambling_urls(url);
        """
        
        # is_illegal 필드에 대한 인덱스 생성 (필터링 성능 향상)
        create_index_illegal = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_is_illegal 
        ON gambling_urls(is_illegal);
        """
        
        # collected_at 필드에 대한 인덱스 생성 (시간순 정렬 성능 향상)
        create_index_collected = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_collected_at 
        ON gambling_urls(collected_at DESC);
        """
        
        # detected_keywords JSONB 필드에 대한 GIN 인덱스 생성 (키워드 검색 성능 향상)
        create_index_keywords = """
        CREATE INDEX IF NOT EXISTS idx_gambling_urls_detected_keywords 
        ON gambling_urls USING GIN(detected_keywords);
        """
        
        # updated_at 자동 업데이트 트리거 함수 생성
        create_trigger_function = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
        
        # updated_at 트리거 생성
        create_trigger = """
        DROP TRIGGER IF EXISTS update_gambling_urls_updated_at ON gambling_urls;
        CREATE TRIGGER update_gambling_urls_updated_at
            BEFORE UPDATE ON gambling_urls
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        self.cursor.execute(create_table_query)
        self.cursor.execute(create_index_url)
        self.cursor.execute(create_index_illegal)
        self.cursor.execute(create_index_collected)
        self.cursor.execute(create_index_keywords)
        self.cursor.execute(create_trigger_function)
        self.cursor.execute(create_trigger)
        self.connection.commit()
        
        print("✅ 테이블 및 인덱스 생성 완료: gambling_urls")
    
    def insert_url_data(self, url_data: Dict[str, Any]) -> bool:
        """
        URL 데이터를 삽입하거나 업데이트합니다.
        - 새로운 URL인 경우: INSERT
        - 기존 URL이 있고, '수동 신고'가 아닌 경우: UPDATE
        - 기존 URL이 '수동 신고'인 경우: 새로 INSERT
        """
        url = url_data.get("url")

        # 1. '수동 신고'가 아닌, 업데이트 가능한 기존 행을 찾습니다.
        find_query = """
        SELECT id FROM gambling_urls 
        WHERE url = %s AND keyword_used != '수동 신고'
        LIMIT 1;
        """
        self.cursor.execute(find_query, (url,))
        result = self.cursor.fetchone()

        # collected_at 문자열을 datetime 객체로 변환
        collected_at = url_data.get("collected_at")
        if isinstance(collected_at, str):
            collected_at = datetime.fromisoformat(collected_at)

        if result:
            # 2A. 업데이트 가능한 행이 존재하면, 해당 행을 업데이트합니다.
            entry_id_to_update = result[0]
            update_query = """
            UPDATE gambling_urls SET
                keyword_used = %s,
                collected_at = %s,
                is_illegal = %s,
                gemini_confidence = %s,
                gemini_reason = %s,
                gemini_error = %s,
                detected_keywords = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
            """
            self.cursor.execute(update_query, (
                url_data.get("keyword_used"),
                collected_at,
                url_data.get("is_illegal"),
                url_data.get("gemini_confidence"),
                url_data.get("gemini_reason"),
                url_data.get("gemini_error"),
                Json(url_data.get("detected_keywords", [])),
                entry_id_to_update
            ))
        else:
            # 2B. 업데이트 가능한 행이 없으면, 새로운 행으로 삽입합니다.
            insert_query = """
            INSERT INTO gambling_urls (
                url, keyword_used, collected_at, is_illegal, 
                gemini_confidence, gemini_reason, gemini_error, detected_keywords
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            self.cursor.execute(insert_query, (
                url_data.get("url"),
                url_data.get("keyword_used"),
                collected_at,
                url_data.get("is_illegal"),
                url_data.get("gemini_confidence"),
                url_data.get("gemini_reason"),
                url_data.get("gemini_error"),
                Json(url_data.get("detected_keywords", []))
            ))
        
        self.connection.commit()
        return True
    
    def insert_bulk_url_data(self, url_data_list: List[Dict[str, Any]]) -> int:
        """여러 URL 데이터 일괄 삽입"""
        inserted_count = 0
        
        for url_data in url_data_list:
            try:
                self.insert_url_data(url_data)
                inserted_count += 1
            except Exception as e:
                print(f"❌ URL 삽입 실패 ({url_data.get('url')}): {e}")
                self.connection.rollback()
        
        return inserted_count
    
    def get_illegal_urls(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """불법 도박 사이트 URL 조회"""
        query = """
        SELECT url, keyword_used, collected_at, is_illegal, 
               gemini_confidence, gemini_reason, detected_keywords
        FROM gambling_urls
        WHERE is_illegal = TRUE
        ORDER BY collected_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        self.cursor.execute(query)
        
        results = []
        for row in self.cursor.fetchall():
            results.append({
                "url": row[0],
                "keyword_used": row[1],
                "collected_at": row[2],
                "is_illegal": row[3],
                "gemini_confidence": row[4],
                "gemini_reason": row[5],
                "detected_keywords": row[6]
            })
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        stats_query = """
        SELECT 
            COUNT(*) as total_urls,
            SUM(CASE WHEN is_illegal = TRUE THEN 1 ELSE 0 END) as illegal_count,
            SUM(CASE WHEN is_illegal = FALSE THEN 1 ELSE 0 END) as legal_count,
            AVG(CASE WHEN is_illegal = TRUE THEN gemini_confidence END) as avg_illegal_confidence,
            MIN(collected_at) as first_collected,
            MAX(collected_at) as last_collected
        FROM gambling_urls;
        """
        
        self.cursor.execute(stats_query)
        row = self.cursor.fetchone()
        
        return {
            "total_urls": row[0],
            "illegal_count": row[1],
            "legal_count": row[2],
            "avg_illegal_confidence": float(row[3]) if row[3] else 0.0,
            "first_collected": row[4],
            "last_collected": row[5]
        }


def import_from_json(json_file_path: str, delete_after_import: bool = True):
    """
    results.json 파일의 데이터를 데이터베이스에 임포트
    
    Args:
        json_file_path: JSON 파일 경로
        delete_after_import: 임포트 성공 후 JSON 파일 삭제 여부 (기본값: True)
    """
    import json
    
    # JSON 파일 존재 확인
    if not os.path.exists(json_file_path):
        print(f"⚠️ 파일이 존재하지 않습니다: {json_file_path}")
        return
    
    # JSON 파일 읽기
    with open(json_file_path, 'r', encoding='utf-8') as f:
        url_data_list = json.load(f)
    
    if not url_data_list:
        print(f"⚠️ 파일이 비어있습니다: {json_file_path}")
        return
    
    print(f"📄 {len(url_data_list)}개의 URL 데이터를 읽었습니다.")
    
    # 데이터베이스에 삽입
    db = DatabaseManager()
    db.connect()
    
    # 테이블이 없으면 생성
    db.create_tables()
    
    # 데이터 삽입
    inserted_count = db.insert_bulk_url_data(url_data_list)
    print(f"✅ {inserted_count}개의 URL 데이터를 데이터베이스에 저장했습니다.")
    
    # 통계 출력
    stats = db.get_statistics()
    print("\n📊 데이터베이스 통계:")
    print(f"  - 전체 URL 수: {stats['total_urls']}")
    print(f"  - 불법 사이트: {stats['illegal_count']}")
    print(f"  - 합법 사이트: {stats['legal_count']}")
    print(f"  - 불법 사이트 평균 신뢰도: {stats['avg_illegal_confidence']:.2f}")
    
    db.disconnect()
    
    # 임포트 성공 후 JSON 파일 삭제
    if delete_after_import and inserted_count > 0:
        os.remove(json_file_path)
        print(f"\n🗑️ JSON 파일 삭제 완료: {json_file_path}")
        print("   (다음 크롤링 시 새로운 results.json이 생성됩니다)")


if __name__ == "__main__":
    # 테스트: results.json 데이터 임포트
    import_from_json("results.json")

