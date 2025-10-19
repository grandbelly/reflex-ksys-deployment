"""
JSON 기반 지식 동적 로더
TASK_005: AI_CREATE_KNOWLEDGE_LOADER
"""

import json
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class KnowledgeLoader:
    """JSON 파일에서 지식을 로드하고 DB에 저장"""
    
    def __init__(self, db_dsn: str, knowledge_dir: str = None):
        """
        초기화
        
        Args:
            db_dsn: 데이터베이스 연결 문자열
            knowledge_dir: 지식 파일 디렉토리 경로
        """
        self.db_dsn = db_dsn
        self.knowledge_dir = knowledge_dir or os.path.join(
            Path(__file__).parent.parent.parent, 'db', 'rag_knowledge'
        )
        self.loaded_files = {}  # 파일명: 마지막 로드 시간
        self.cache = {}  # 메모리 캐시
        self.cache_timestamps = {}  # 캐시 타임스탬프
        
    async def load_json_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        JSON 파일 로드
        
        Args:
            filepath: JSON 파일 경로
            
        Returns:
            지식 항목 리스트
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 단일 객체를 리스트로 변환
            if isinstance(data, dict):
                data = [data]
            
            # 각 항목 검증 및 정규화
            knowledge_items = []
            for item in data:
                normalized = self._normalize_knowledge_item(item)
                if normalized:
                    knowledge_items.append(normalized)
            
            return knowledge_items
            
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류 ({filepath}): {e}")
            return []
        except Exception as e:
            print(f"파일 로드 오류 ({filepath}): {e}")
            return []
    
    def _normalize_knowledge_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        지식 항목 정규화
        
        Args:
            item: 원본 지식 항목
            
        Returns:
            정규화된 지식 항목
        """
        # 필수 필드 확인
        if not item.get('content'):
            return None
        
        normalized = {
            'content': item['content'],
            'content_type': item.get('content_type', 'general'),
            'w5h1_data': {},
            'metadata': {},
            'tags': [],
            'priority': 5,
            'confidence_score': 1.0
        }
        
        # 6하원칙 데이터 처리
        if 'w5h1' in item or 'w5h1_data' in item:
            w5h1 = item.get('w5h1') or item.get('w5h1_data', {})
            normalized['w5h1_data'] = {
                'what': w5h1.get('what', ''),
                'why': w5h1.get('why', ''),
                'when': w5h1.get('when', ''),
                'where': w5h1.get('where', ''),
                'who': w5h1.get('who', ''),
                'how': w5h1.get('how', '')
            }
        
        # 메타데이터 처리
        if 'metadata' in item:
            normalized['metadata'] = item['metadata']
        
        # 태그 처리
        if 'tags' in item:
            if isinstance(item['tags'], str):
                normalized['tags'] = [tag.strip() for tag in item['tags'].split(',')]
            elif isinstance(item['tags'], list):
                normalized['tags'] = item['tags']
        
        # 우선순위 및 신뢰도
        normalized['priority'] = item.get('priority', 5)
        normalized['confidence_score'] = item.get('confidence_score', 1.0)
        
        return normalized
    
    async def load_to_database(self, knowledge_items: List[Dict[str, Any]], source: str = None) -> int:
        """
        지식을 데이터베이스에 저장
        
        Args:
            knowledge_items: 지식 항목 리스트
            source: 소스 파일명 (선택)
            
        Returns:
            저장된 항목 수
        """
        if not knowledge_items:
            return 0
        
        saved_count = 0
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    for item in knowledge_items:
                        try:
                            # 중복 확인 (content 기준)
                            await cur.execute("""
                                SELECT id FROM ai_knowledge_base
                                WHERE content = %s
                            """, (item['content'],))
                            
                            existing = await cur.fetchone()
                            
                            if existing:
                                # 업데이트
                                await cur.execute("""
                                    UPDATE ai_knowledge_base
                                    SET 
                                        content_type = %s,
                                        w5h1_data = %s,
                                        metadata = %s,
                                        tags = %s,
                                        priority = %s,
                                        confidence_score = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE id = %s
                                """, (
                                    item['content_type'],
                                    json.dumps(item['w5h1_data'], ensure_ascii=False),
                                    json.dumps(item['metadata'], ensure_ascii=False),
                                    item['tags'],
                                    item['priority'],
                                    item['confidence_score'],
                                    existing[0]
                                ))
                                print(f"  [UPDATE] ID {existing[0]}: {item['content'][:50]}...")
                            else:
                                # 삽입
                                await cur.execute("""
                                    INSERT INTO ai_knowledge_base 
                                    (content, content_type, w5h1_data, metadata, tags, priority, confidence_score)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    item['content'],
                                    item['content_type'],
                                    json.dumps(item['w5h1_data'], ensure_ascii=False),
                                    json.dumps(item['metadata'], ensure_ascii=False),
                                    item['tags'],
                                    item['priority'],
                                    item['confidence_score']
                                ))
                                print(f"  [INSERT] {item['content'][:50]}...")
                            
                            saved_count += 1
                            
                        except Exception as e:
                            print(f"  [ERROR] 항목 저장 실패: {e}")
                            continue
                    
                    await conn.commit()
                    
                    # 소스 기록
                    if source:
                        await cur.execute("""
                            INSERT INTO ai_knowledge_base 
                            (content, content_type, metadata)
                            VALUES (%s, 'system', %s)
                            ON CONFLICT (content) DO UPDATE
                            SET metadata = EXCLUDED.metadata,
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            f"[LOADER] Loaded from {source}",
                            json.dumps({
                                'source': source,
                                'loaded_at': datetime.now().isoformat(),
                                'item_count': saved_count
                            })
                        ))
                        await conn.commit()
                    
        except Exception as e:
            print(f"데이터베이스 저장 오류: {e}")
        
        return saved_count
    
    async def load_directory(self, directory: str = None) -> Dict[str, int]:
        """
        디렉토리의 모든 JSON 파일 로드
        
        Args:
            directory: 디렉토리 경로 (기본: knowledge_dir)
            
        Returns:
            파일별 로드 결과
        """
        directory = directory or self.knowledge_dir
        results = {}
        
        if not os.path.exists(directory):
            print(f"디렉토리가 존재하지 않습니다: {directory}")
            return results
        
        # JSON 파일 찾기
        json_files = list(Path(directory).glob('*.json'))
        
        print(f"\n[START] Knowledge loader started: {directory}")
        print(f"   Found JSON files: {len(json_files)}")
        
        for json_file in json_files:
            print(f"\n[FILE] Processing: {json_file.name}")
            
            # 파일 로드
            items = await self.load_json_file(str(json_file))
            print(f"   Loaded items: {len(items)}")
            
            # DB 저장
            if items:
                saved = await self.load_to_database(items, json_file.name)
                results[json_file.name] = saved
                print(f"   Saved: {saved} items")
            else:
                results[json_file.name] = 0
        
        # 요약
        total_loaded = sum(results.values())
        print(f"\n[COMPLETE] Load complete: Total {total_loaded} items")
        
        return results
    
    async def reload_modified(self) -> Dict[str, int]:
        """
        수정된 파일만 다시 로드
        
        Returns:
            파일별 로드 결과
        """
        results = {}
        directory = self.knowledge_dir
        
        if not os.path.exists(directory):
            return results
        
        for json_file in Path(directory).glob('*.json'):
            file_path = str(json_file)
            file_mtime = os.path.getmtime(file_path)
            
            # 이전 로드 시간과 비교
            if file_path in self.loaded_files:
                if file_mtime <= self.loaded_files[file_path]:
                    continue  # 변경 없음
            
            print(f"\n[RELOAD] Reloading modified file: {json_file.name}")
            
            # 파일 로드 및 저장
            items = await self.load_json_file(file_path)
            if items:
                saved = await self.load_to_database(items, json_file.name)
                results[json_file.name] = saved
                
                # 로드 시간 기록
                self.loaded_files[file_path] = file_mtime
        
        if results:
            print(f"\n[COMPLETE] Reload complete: {len(results)} files")
        
        return results


class KnowledgeFileWatcher(FileSystemEventHandler):
    """지식 파일 변경 감시자"""
    
    def __init__(self, loader: KnowledgeLoader):
        self.loader = loader
        self.loop = asyncio.new_event_loop()
    
    def on_modified(self, event):
        """파일 수정 이벤트 처리"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.json'):
            print(f"\n[CHANGE] File change detected: {os.path.basename(event.src_path)}")
            
            # 비동기 작업을 동기 컨텍스트에서 실행
            asyncio.run_coroutine_threadsafe(
                self._reload_file(event.src_path),
                self.loop
            )
    
    async def _reload_file(self, filepath: str):
        """파일 재로드 (비동기)"""
        items = await self.loader.load_json_file(filepath)
        if items:
            await self.loader.load_to_database(items, os.path.basename(filepath))
            print(f"   [OK] Reload complete: {len(items)} items")


def start_file_watcher(loader: KnowledgeLoader) -> Observer:
    """
    파일 감시자 시작
    
    Args:
        loader: KnowledgeLoader 인스턴스
        
    Returns:
        Observer 인스턴스
    """
    event_handler = KnowledgeFileWatcher(loader)
    observer = Observer()
    observer.schedule(event_handler, loader.knowledge_dir, recursive=False)
    observer.start()
    
    print(f"[WATCH] File watching started: {loader.knowledge_dir}")
    
    return observer