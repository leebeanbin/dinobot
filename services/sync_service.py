"""
Notion 동기화 서비스 모듈
- 페이지 삭제 감지
- 스레드 비활성화
- 실시간 동기화
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from core.database import get_meetup_collection, mongodb_connection
from core.logger import get_logger
from core.exceptions import safe_execution
from core.config import settings
from .notion import notion_service
from .discord_service import discord_service

# Module logger
logger = get_logger("services.sync")


class SyncService:
    """Notion 동기화 서비스"""

    def __init__(self):
        self.sync_interval = 180  # 3분마다 동기화 (성능 향상)
        self.is_running = False
        self.sync_task = None
        # 성능 최적화를 위한 캐시
        self._page_cache = {}  # 페이지 ID -> 마지막 수정 시간
        self._last_sync_time = None

    @safe_execution("start_sync_monitor")
    async def start_sync_monitor(self):
        """동기화 모니터링 시작"""
        if self.is_running:
            logger.warning("⚠️ 동기화 모니터링이 이미 실행 중입니다")
            return

        self.is_running = True
        logger.info("🔄 Notion 동기화 모니터링 시작")

        # 백그라운드에서 동기화 실행
        self.sync_task = asyncio.create_task(self._sync_loop())

    @safe_execution("stop_sync_monitor")
    async def stop_sync_monitor(self):
        """동기화 모니터링 중지"""
        if not self.is_running:
            return

        self.is_running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Notion 동기화 모니터링 중지")

    @safe_execution("clean_deleted_pages")
    async def clean_deleted_pages(self):
        """삭제된 페이지 정리 (개선된 버전)"""
        try:
            logger.info("🧹 삭제된 페이지 정리 시작")

            # DB에서 모든 페이지 ID 가져오기
            collection = get_meetup_collection("notion_pages")
            db_pages = await collection.find({}, {"page_id": 1, "title": 1, "database_id": 1}).to_list(
                length=None
            )

            if not db_pages:
                logger.info("📭 정리할 페이지가 없습니다")
                return 0

            deleted_count = 0
            batch_size = 10
            semaphore = asyncio.Semaphore(batch_size)

            async def check_and_clean_page(page):
                async with semaphore:
                    try:
                        page_id = page.get("page_id")
                        if not page_id:
                            return False

                        # check_page_exists 메서드를 사용하여 페이지 존재 확인
                        page_exists = await notion_service.check_page_exists(page_id)
                        
                        if not page_exists:
                            # 페이지가 존재하지 않으면 DB에서 삭제
                            await collection.delete_one({"page_id": page_id})
                            logger.info(
                                f"🗑️ 삭제된 페이지 정리: {page.get('title', 'Unknown')} (ID: {page_id})"
                            )
                            return True
                        return False
                    except Exception as e:
                        logger.warning(f"⚠️ 페이지 확인 실패: {page_id} - {e}")
                        return False

            # 배치로 병렬 처리
            for i in range(0, len(db_pages), batch_size * 2):
                batch = db_pages[i:i + batch_size * 2]
                tasks = [check_and_clean_page(page) for page in batch]
                
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    deleted_count += sum(1 for result in results if result is True)
                    
                    # API 레이트 리밋 방지를 위한 지연
                    await asyncio.sleep(1)
                except Exception as batch_error:
                    logger.warning(f"⚠️ 배치 처리 중 오류: {batch_error}")

            logger.info(f"✅ 삭제된 페이지 정리 완료: {deleted_count}개 페이지 제거")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ 삭제된 페이지 정리 실패: {e}")
            return 0

    @safe_execution("sync_loop")
    async def _sync_loop(self):
        """동기화 루프"""
        while self.is_running:
            try:
                await self.sync_notion_pages()
                # 주기적으로 삭제된 페이지 정리 (1시간마다)
                if (
                    not self._last_sync_time
                    or (datetime.now() - self._last_sync_time).seconds > settings.cleanup_interval
                ):
                    await self.clean_deleted_pages()
                    self._last_sync_time = datetime.now()
                await asyncio.sleep(self.sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 동기화 루프 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기

    @safe_execution("sync_notion_pages")
    async def sync_notion_pages(self):
        """Notion 페이지 동기화"""
        try:
            # MongoDB 연결 상태 확인 및 재연결
            if (
                not mongodb_connection.connection_status
                or mongodb_connection.mongo_client is None
            ):
                await mongodb_connection.connect_database()

            collection = get_meetup_collection("notion_pages")

            # 저장된 모든 페이지 조회
            stored_pages = await collection.find({}).to_list(None)

            # MongoDB에 페이지가 없으면 Notion에서 기존 페이지들을 가져옴
            if not stored_pages:
                logger.info(
                    "📭 MongoDB에 페이지가 없습니다. Notion에서 기존 페이지들을 가져오는 중..."
                )
                await self._import_existing_notion_pages()
                stored_pages = await collection.find({}).to_list(None)

            logger.debug(f"🔄 동기화 시작: {len(stored_pages)}개 페이지 확인")

            deleted_pages = []
            updated_pages = []
            processed_count = 0

            # 병렬 처리로 페이지 동기화 (개선된 버전)
            import asyncio

            # 페이지 수에 따라 동적으로 세마포어 크기 조정
            max_concurrent = min(10, max(3, len(stored_pages) // 20))  # 3-10 사이
            semaphore = asyncio.Semaphore(max_concurrent)
            logger.debug(f"🔧 동시 처리 제한: {max_concurrent}개")

            async def process_page(page):
                async with semaphore:
                    return await self._process_single_page(
                        page, notion_service, collection
                    )

            # 배치 단위로 처리하여 메모리 효율성 향상
            batch_size = 50
            all_results = []
            
            for i in range(0, len(stored_pages), batch_size):
                batch = stored_pages[i:i + batch_size]
                logger.debug(f"📦 배치 처리 중: {i + 1}-{min(i + batch_size, len(stored_pages))}/{len(stored_pages)}")
                
                tasks = [process_page(page) for page in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_results.extend(batch_results)
                
                # 배치 간 짧은 대기로 API 레이트 리밋 방지
                if i + batch_size < len(stored_pages):
                    await asyncio.sleep(0.5)
            
            results = all_results

            # 결과 처리
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"⚠️ 페이지 처리 중 오류: {result}")
                    processed_count += 1
                    continue

                if result and isinstance(result, tuple) and len(result) == 5:
                    page_id, title, thread_id, page_type, created_by = result
                    if page_id:  # 삭제된 페이지
                        deleted_pages.append(
                            {
                                "page_id": page_id,
                                "title": title,
                                "thread_id": thread_id,
                                "created_by": created_by,
                                "page_type": page_type,
                            }
                        )
                    else:  # 업데이트된 페이지
                        updated_pages.append(title)
                elif result:
                    logger.warning(f"⚠️ 예상치 못한 결과 형식: {result}")

            # 3. 삭제된 페이지에 대한 스레드 처리
            if deleted_pages:
                await self._handle_deleted_pages(deleted_pages)

            # 4. 동기화 결과 로깅
            logger.info(f"✅ 동기화 완료: {processed_count}개 페이지 처리")
            if deleted_pages:
                logger.info(f"🗑️ 삭제된 페이지: {len(deleted_pages)}개")
            if updated_pages:
                logger.info(f"🔄 업데이트된 페이지: {len(updated_pages)}개")
            if not deleted_pages and not updated_pages:
                logger.info("📝 변경사항 없음")

        except Exception as e:
            logger.error(f"❌ 동기화 실패: {e}")
        # finally 블록 제거 - MongoDB 연결을 유지해야 함

    async def _process_single_page(self, page, notion_service, collection):
        """단일 페이지 처리 (병렬 처리용, 최적화됨)"""
        try:
            page_id = page.get("page_id")
            title = page.get("title", "제목 없음")
            thread_id = page.get("thread_id")
            last_synced = page.get("last_synced", 0)
            
            # 최근 30분 내에 동기화했다면 간단 체크만 수행
            current_time = datetime.now().timestamp()
            if last_synced and (current_time - last_synced) < settings.sync_recent_threshold:
                logger.debug(f"⏭️ 최근 동기화됨, 간단 체크만 수행: {title}")
                # 간단한 존재 여부만 확인
                page_exists = await notion_service.check_page_exists(page_id)
                if not page_exists:
                    await collection.delete_one({"page_id": page_id})
                    return (page_id, title, thread_id, page.get("page_type"), page.get("created_by"))
                return None  # 변경사항 없음

            # 1. 페이지 내용 업데이트 확인 (존재 여부와 함께)
            try:
                # extract_page_text로 존재 여부와 내용을 한 번에 확인
                logger.debug(f"📄 페이지 내용 업데이트 확인: {title}")
                new_content = await notion_service.extract_page_text(page_id, use_cache=True)
                
                # 내용 변경 여부 확인
                current_content = page.get("content", "")
                content_changed = new_content != current_content
                
                if content_changed or not last_synced:
                    # 내용이 변경되었으면 MongoDB 업데이트
                    await collection.update_one(
                        {"page_id": page_id},
                        {
                            "$set": {
                                "content": new_content,
                                "content_length": len(new_content),
                                "last_synced": current_time,
                                "search_text": f"{title} {new_content}",
                            }
                        }
                    )
                    logger.debug(f"🔄 내용 업데이트됨: {title}")
                    return (None, title, None, None, None)  # 업데이트됨
                else:
                    # 내용은 같지만 동기화 시간 업데이트
                    await collection.update_one(
                        {"page_id": page_id},
                        {"$set": {"last_synced": current_time}}
                    )
                    return None  # 변경사항 없음
            except Exception as update_error:
                logger.warning(f"⚠️ 페이지 내용 추출 실패: {title} - {update_error}")
                # extract_page_text 실패는 페이지 삭제가 아님 - 그냥 스킵
                logger.info(f"⏭️ 페이지 내용 추출 실패로 인한 스킵: {title}")
                return None

        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                # 404 오류는 페이지 내용 삭제로 간주 (MongoDB에서만 제거)
                await collection.delete_one({"page_id": page_id})
                return (
                    page_id,
                    title,
                    thread_id,
                    page.get("page_type"),
                    page.get("created_by"),
                )
            else:
                logger.warning(f"⚠️ 페이지 확인 실패: {title} - {e}")
                return None

    async def _import_existing_notion_pages(self):
        """Notion DB에서 기존 페이지들을 MongoDB로 가져오기"""
        try:
            logger.info("📥 Notion DB에서 기존 페이지들을 가져오는 중...")

            # 데이터베이스 연결 확인 및 연결
            if (
                not mongodb_connection.connection_status
                or mongodb_connection.mongo_client is None
            ):
                await mongodb_connection.connect_database()

            # Factory Tracker DB에서 페이지들 가져오기
            factory_pages = await self._get_notion_database_pages("factory_tracker")
            logger.info(f"📊 Factory Tracker에서 {len(factory_pages)}개 페이지 발견")

            # Board DB에서 페이지들 가져오기
            board_pages = await self._get_notion_database_pages("board")
            logger.info(f"📋 Board에서 {len(board_pages)}개 페이지 발견")

            # 모든 페이지를 MongoDB에 저장
            all_pages = factory_pages + board_pages
            if all_pages:
                collection = get_meetup_collection("notion_pages")
                await collection.insert_many(all_pages)
                logger.info(f"✅ {len(all_pages)}개 페이지를 MongoDB에 저장했습니다.")
            else:
                logger.info("📭 Notion DB에서 가져올 페이지가 없습니다.")

        except Exception as e:
            logger.error(f"❌ 기존 페이지 가져오기 실패: {e}")

    async def _get_notion_database_pages(self, db_type: str) -> List[Dict[str, Any]]:
        """특정 Notion DB에서 페이지들을 가져오기"""
        try:
            if db_type == "factory_tracker":
                db_id = settings.factory_tracker_db_id
                page_type = "task"
            elif db_type == "board":
                db_id = settings.board_db_id
                page_type = "meeting"
            else:
                return []

            # Notion DB에서 페이지들 조회
            response = notion_service.notion_client.databases.query(
                database_id=db_id, page_size=100
            )

            logger.info(
                f"🔍 {db_type} DB 응답: {len(response.get('results', []))}개 페이지 발견"
            )

            # 비동기 병렬 처리로 페이지들 처리
            pages = await self._process_pages_parallel(
                response.get("results", []), db_type, db_id, page_type
            )

            return pages

        except Exception as e:
            logger.error(f"❌ {db_type} DB에서 페이지 가져오기 실패: {e}")
            return []

    async def _process_pages_parallel(
        self,
        page_data_list: List[Dict[str, Any]],
        db_type: str,
        db_id: str,
        page_type: str,
    ) -> List[Dict[str, Any]]:
        """페이지들을 비동기 병렬로 처리"""
        try:
            # 동시 처리할 페이지 수 제한 (API 레이트 리미트 고려)
            BATCH_SIZE = 5
            semaphore = asyncio.Semaphore(BATCH_SIZE)

            async def process_single_page(
                page_data: Dict[str, Any],
            ) -> Optional[Dict[str, Any]]:
                """단일 페이지 처리"""
                async with semaphore:
                    try:
                        # 페이지 기본 정보 추출
                        page_id = page_data["id"]
                        title = self._extract_page_title(page_data, db_type)

                        if not title:
                            logger.warning(f"⚠️ 제목이 없는 페이지 스킵: {page_id}")
                            return None

                        # 페이지 내용 추출 시도 (병렬 처리)
                        try:
                            content = await notion_service.extract_page_text(page_id)
                        except:
                            content = ""

                        # MongoDB에 저장할 데이터 구성
                        page_doc = {
                            "page_id": page_id,
                            "database_id": db_id,
                            "title": title,
                            "content": content,
                            "content_length": len(content),
                            "page_type": page_type,
                            "database_type": db_type,
                            "created_time": page_data.get("created_time", ""),
                            "last_edited_time": page_data.get("last_edited_time", ""),
                            "created_by": str(
                                page_data.get("created_by", {}).get("id", "unknown")
                            ),
                            "last_edited_by": str(
                                page_data.get("last_edited_by", {}).get("id", "unknown")
                            ),
                            "url": page_data.get("url", ""),
                            "thread_id": None,
                            "last_synced": datetime.now().timestamp(),
                            "search_text": f"{title} {content}",
                        }

                        return page_doc

                    except Exception as page_error:
                        logger.warning(f"⚠️ 페이지 처리 실패: {page_error}")
                        return None

            # 모든 페이지를 병렬로 처리
            tasks = [process_single_page(page_data) for page_data in page_data_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 성공한 결과만 필터링
            pages = [
                page
                for page in results
                if page is not None and not isinstance(page, Exception)
            ]

            logger.info(f"✅ {db_type} 병렬 처리 완료: {len(pages)}개 페이지")
            return pages

        except Exception as e:
            logger.error(f"❌ 병렬 페이지 처리 실패: {e}")
            return []

    def _extract_page_title(self, page_data: Dict[str, Any], db_type: str) -> str:
        """페이지에서 제목 추출"""
        try:
            properties = page_data.get("properties", {})

            if db_type == "factory_tracker":
                # Factory Tracker의 Task name 속성 (여러 가능한 이름 시도)
                for title_key in ["Task name", "Title", "Name", "title", "name"]:
                    title_prop = properties.get(title_key, {})
                    if title_prop.get("type") == "title":
                        title_blocks = title_prop.get("title", [])
                        if title_blocks:
                            return title_blocks[0].get("plain_text", "")

            elif db_type == "board":
                # Board의 Name 속성 (Title이 아니라 Name)
                name_prop = properties.get("Name", {})
                if name_prop.get("type") == "title":
                    title_blocks = name_prop.get("title", [])
                    if title_blocks:
                        return title_blocks[0].get("plain_text", "")

            return ""

        except Exception as e:
            logger.warning(f"⚠️ 제목 추출 실패: {e}")
            return ""

    async def _update_page_content(self, page: Dict[str, Any]) -> bool:
        """페이지 내용 업데이트"""
        try:
            page_id = page.get("page_id")
            current_content = page.get("content", "")
            current_sync_time = page.get("last_synced", 0)

            # 최근 1시간 내에 동기화했다면 스킵
            if (
                current_sync_time
                and (datetime.now().timestamp() - current_sync_time) < 3600
            ):
                return False

            # 페이지 내용 추출
            try:
                new_content = await notion_service.extract_page_text(page_id)
            except Exception as extract_error:
                # 404 오류는 페이지 내용 삭제로 간주하고 예외를 다시 발생시킴
                if (
                    "404" in str(extract_error)
                    or "not found" in str(extract_error).lower()
                ):
                    logger.info(f"🔍 404 오류 감지하여 예외 재발생: {extract_error}")
                    raise extract_error
                else:
                    # 다른 오류는 로깅하고 False 반환
                    logger.warning(f"⚠️ 페이지 내용 추출 실패: {extract_error}")
                    return False

            if new_content != current_content:
                # 내용이 변경됨
                collection = get_meetup_collection("notion_pages")
                await collection.update_one(
                    {"page_id": page_id},
                    {
                        "$set": {
                            "content": new_content,
                            "content_length": len(new_content),
                            "last_synced": datetime.now().timestamp(),
                            "search_text": f"{page.get('title', '')} {new_content}",
                        }
                    },
                )
                return True

            return False

        except Exception as e:
            logger.warning(f"⚠️ 페이지 내용 업데이트 실패: {e}")
            return False

    @safe_execution("handle_deleted_pages")
    async def _handle_deleted_pages(self, deleted_pages: List[Dict[str, Any]]):
        """삭제된 페이지에 대한 스레드 처리"""
        for page in deleted_pages:
            try:
                thread_id = page.get("thread_id")
                title = page.get("title", "제목 없음")
                page_type = page.get("page_type", "unknown")
                created_by = page.get("created_by", "unknown")

                if not thread_id:
                    logger.warning(f"⚠️ 스레드 ID가 없는 삭제된 페이지: {title}")
                    continue

                # 스레드에 삭제 알림 메시지 전송
                await self._send_deletion_notification(thread_id, page)

                # 스레드는 비활성화하지 않음 (페이지 자체는 삭제되지 않았으므로)
                # 개별 로그 제거 - 요약에서만 표시

            except Exception as e:
                logger.error(f"❌ 삭제된 페이지 처리 실패: {e}")

    @safe_execution("send_deletion_notification")
    async def _send_deletion_notification(self, thread_id: int, page: Dict[str, Any]):
        """삭제 알림 메시지 전송"""
        try:
            title = page.get("title", "제목 없음")
            page_type = page.get("page_type", "unknown")
            created_by = page.get("created_by", "unknown")

            # 삭제 알림 메시지 구성
            embed = {
                "title": "🗑️ 페이지 내용 삭제됨",
                "description": f"**{title}** 페이지의 내용이 Notion에서 삭제되었습니다.",
                "color": 0xFF6B6B,  # 빨간색
                "fields": [
                    {
                        "name": "📄 페이지 정보",
                        "value": f"**제목**: {title}\n**타입**: {page_type}\n**생성자**: User {created_by[-4:]}",
                        "inline": False,
                    },
                    {
                        "name": "⚠️ 주의사항",
                        "value": "이 페이지는 더 이상 내용을 가져올 수 없습니다.\n새로운 페이지를 생성하려면 `/meeting`, `/task`, `/document` 명령어를 사용하세요.",
                        "inline": False,
                    },
                ],
                "timestamp": datetime.now().isoformat(),
                "footer": {"text": "MeetupLoader 동기화 시스템"},
            }

            # Discord 스레드에 메시지 전송
            await discord_service.send_thread_message(
                thread_id=thread_id, content="", embed=embed
            )

            logger.info(f"📢 삭제 알림 전송: {title}")

        except Exception as e:
            logger.error(f"❌ 삭제 알림 전송 실패: {e}")

    @safe_execution("deactivate_thread")
    async def _deactivate_thread(self, thread_id: int, page: Dict[str, Any]):
        """스레드 비활성화"""
        try:
            # Discord 스레드 비활성화 (archived 상태로 변경)
            thread = discord_service.bot.get_channel(thread_id)
            if thread and hasattr(thread, "edit"):
                await thread.edit(archived=True, locked=True)
                logger.info(f"🔒 스레드 비활성화: {thread_id}")
            else:
                logger.warning(f"⚠️ 스레드를 찾을 수 없음: {thread_id}")

        except Exception as e:
            logger.error(f"❌ 스레드 비활성화 실패: {e}")

    @safe_execution("manual_sync")
    async def manual_sync(self) -> Dict[str, Any]:
        """수동 동기화 실행"""
        try:
            # MongoDB 연결 상태 확인 및 재연결
            if (
                not mongodb_connection.connection_status
                or mongodb_connection.mongo_client is None
            ):
                await mongodb_connection.connect_database()

            collection = get_meetup_collection("notion_pages")

            # 저장된 페이지 수
            total_pages = await collection.count_documents({})

            # 동기화 실행
            await self.sync_notion_pages()

            # 결과 반환
            return {
                "success": True,
                "message": "동기화가 완료되었습니다.",
                "total_pages": total_pages,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ 수동 동기화 실패: {e}")
            return {
                "success": False,
                "message": f"동기화 실패: {e}",
                "timestamp": datetime.now().isoformat(),
            }
        # finally 블록 제거 - MongoDB 연결을 유지해야 함

    @safe_execution("get_sync_status")
    async def get_sync_status(self) -> Dict[str, Any]:
        """동기화 상태 조회"""
        try:
            # MongoDB 연결 상태 확인 및 재연결
            if (
                not mongodb_connection.connection_status
                or mongodb_connection.mongo_client is None
            ):
                await mongodb_connection.connect_database()

            collection = get_meetup_collection("notion_pages")

            # 전체 페이지 수
            total_pages = await collection.count_documents({})

            # 최근 동기화된 페이지 수
            recent_sync = await collection.count_documents(
                {
                    "last_synced": {
                        "$gte": datetime.now().timestamp() - 3600
                    }  # 최근 1시간
                }
            )

            # 페이지 타입별 분포
            type_distribution = {}
            cursor = collection.aggregate(
                [{"$group": {"_id": "$page_type", "count": {"$sum": 1}}}]
            )

            async for doc in cursor:
                type_distribution[doc["_id"]] = doc["count"]

            return {
                "is_running": self.is_running,
                "total_pages": total_pages,
                "recent_sync": recent_sync,
                "type_distribution": type_distribution,
                "sync_interval": self.sync_interval,
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ 동기화 상태 조회 실패: {e}")
            return {
                "is_running": False,
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }
        # finally 블록 제거 - MongoDB 연결을 유지해야 함


# Global sync service instance
sync_service = SyncService()
