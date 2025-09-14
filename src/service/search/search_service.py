"""
검색 서비스 모듈
- 제목 및 내용 기반 페이지 검색
- 타입 및 사용자 필터링
- MongoDB 텍스트 검색 활용
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.core.database import get_meetup_collection, mongodb_connection
from src.core.logger import get_logger
from src.core.exceptions import safe_execution

# notion_service는 ServiceManager를 통해 접근
# from services.notion import notion_service

logger = get_logger("services.search")


class SearchService:
    """페이지 검색 서비스"""

    def __init__(self):
        # 검색 서비스 초기화 (로그 제거)
        pass

    @safe_execution("search_pages")
    async def search_pages(
        self,
        query: str,
        page_type: str = None,
        user_filter: str = None,
        days_limit: int = 90,
        days: int = None,  # 호환성을 위한 파라미터 추가
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        페이지 검색

        Args:
            query: 검색 키워드
            page_type: 페이지 타입 필터 (meeting, task, note)
            user_filter: 사용자 ID 필터
            days_limit: 검색 기간 제한 (일)
            limit: 결과 개수 제한
        """
        # 호환성을 위한 days 파라미터 처리
        if days is not None:
            days_limit = days

        if not query or len(query.strip()) < 2:
            return {
                "total_results": 0,
                "results": [],
                "query": query,
                "filters": {"type": page_type, "user": user_filter, "days": days_limit},
            }

        # 데이터베이스 연결 확인 및 연결
        if (
            not mongodb_connection.connection_status
            or mongodb_connection.mongo_client is None
        ):
            await mongodb_connection.connect_database()

        collection = get_meetup_collection("notion_pages")

        # 검색 조건 설정
        search_conditions = []

        # 날짜 범위 필터 (임시로 비활성화 - 모든 페이지 검색)
        # if days_limit is None:
        #     days_limit = 90  # 기본값 설정
        # since_date = datetime.now() - timedelta(days=days_limit)
        # # created_at이 None이거나 날짜 범위에 포함되는 경우
        # search_conditions.append(
        #     {
        #         "$or": [
        #             {"created_at": {"$gte": since_date}},
        #             {"created_at": None},
        #             {"created_at": {"$exists": False}},
        #             {"created_at": {"$type": "null"}},
        #         ]
        #     }
        # )

        # 타입 필터
        if page_type and page_type != "all":
            search_conditions.append({"page_type": page_type})

        # 사용자 필터
        if user_filter and user_filter != "all":
            search_conditions.append({"created_by": user_filter})

        # MongoDB 쿼리 실행 (정규식 제외)
        if len(search_conditions) > 1:
            mongo_query = {"$and": search_conditions}
        else:
            mongo_query = search_conditions[0] if search_conditions else {}

        # 모든 페이지 가져오기 (Python 레벨에서 필터링)
        all_pages = await collection.find(mongo_query).to_list(None)

        # Python 레벨에서 제목 검색 (정확 매칭 + 유사도 검색)
        title_results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for page in all_pages:
            title = page.get("title", "")
            title_lower = title.lower()
            title_words = set(title_lower.split())

            # 1. 정확한 부분 문자열 매칭 (높은 우선순위)
            if query_lower in title_lower:
                page["_match_score"] = 100
                title_results.append(page)
            # 2. 단어 단위 유사도 검색
            elif query_words and title_words:
                # 공통 단어 수 계산
                common_words = query_words.intersection(title_words)
                if common_words:
                    # 유사도 점수 = (공통 단어 수 / 전체 검색어 수) * 50
                    similarity_score = (len(common_words) / len(query_words)) * 50
                    page["_match_score"] = similarity_score
                    title_results.append(page)

            if len(title_results) >= limit * 2:  # 더 많은 후보를 수집
                break

        # 점수 순으로 정렬
        title_results.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
        title_results = title_results[:limit]

        logger.info(f"🔍 제목 검색 완료: '{query}' -> {len(title_results)}개 결과")

        # 내용 검색 (Notion API 활용)
        content_results = []
        if len(title_results) < limit:
            content_results = await self._search_in_content(
                query, page_type, user_filter, days_limit, limit - len(title_results)
            )

        # 결과 합치기 및 중복 제거
        all_results = title_results + content_results
        unique_results = []
        seen_page_ids = set()

        for result in all_results:
            page_id = result.get("page_id")
            if page_id not in seen_page_ids:
                seen_page_ids.add(page_id)
                # 검색 결과에 추가 정보 포함
                enhanced_result = self._enhance_search_result(result)
                unique_results.append(enhanced_result)

        # 결과를 생성 날짜 순으로 정렬 (최신순)
        unique_results.sort(
            key=lambda x: x.get("created_at", datetime.min), reverse=True
        )

        # 결과 개수 제한
        final_results = unique_results[:limit]

        logger.info(f"🔍 전체 검색 완료: '{query}' -> {len(final_results)}개 최종 결과")

        # 검색 제안 생성 (검색 결과가 적거나 없을 때)
        suggestions = {}
        if len(final_results) < 10:
            suggestions = await self.get_search_suggestions(query)

        return {
            "total_results": len(final_results),
            "results": final_results,
            "query": query,
            "filters": {"type": page_type, "user": user_filter, "days": days_limit},
            "suggestions": suggestions,
        }

    @safe_execution("search_in_content")
    async def _search_in_content(
        self,
        query: str,
        page_type: str = None,
        user_filter: str = None,
        days_limit: int = 90,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """페이지 내용에서 키워드 검색"""
        try:
            # 데이터베이스 연결 확인 및 연결
            if (
                not mongodb_connection.connection_status
                or mongodb_connection.mongo_client is None
            ):
                await mongodb_connection.connect_database()

            collection = get_meetup_collection("notion_pages")

            # 검색 조건 설정 (제목 검색과 동일)
            search_conditions = []

            # since_date = datetime.now() - timedelta(days=days_limit)
            # # created_at이 None이거나 날짜 범위에 포함되는 경우
            # search_conditions.append(
            #     {
            #         "$or": [
            #             {"created_at": {"$gte": since_date}},
            #             {"created_at": None},
            #             {"created_at": {"$exists": False}},
            #             {"created_at": {"$type": "null"}},
            #         ]
            #     }
            # )

            if page_type and page_type != "all":
                search_conditions.append({"page_type": page_type})

            if user_filter and user_filter != "all":
                search_conditions.append({"created_by": user_filter})

            # 기본 쿼리
            if len(search_conditions) > 1:
                mongo_query = {"$and": search_conditions}
            else:
                mongo_query = search_conditions[0] if search_conditions else {}

            # 최근 페이지들 가져오기 (내용 검색 대상)
            pages = await collection.find(mongo_query).limit(100).to_list(None)

            content_matches = []
            query_lower = query.lower()

            for page in pages:
                try:
                    # Notion에서 페이지 내용 가져오기
                    page_content = await notion_service.extract_page_text(
                        page_id=page["page_id"]
                    )

                    # 내용에서 키워드 검색
                    if page_content and query_lower in page_content.lower():
                        # 매칭된 부분 찾기 (컨텍스트와 함께)
                        content_preview = self._extract_search_context(
                            page_content, query
                        )

                        # 페이지 정보에 검색 컨텍스트 추가
                        page_with_context = page.copy()
                        page_with_context["search_context"] = content_preview
                        page_with_context["match_type"] = "content"

                        content_matches.append(page_with_context)

                        if len(content_matches) >= limit:
                            break

                except Exception as e:
                    logger.warning(
                        f"⚠️ 페이지 내용 검색 실패 ({page.get('page_id')}): {e}"
                    )
                    continue

            logger.info(
                f"🔍 내용 검색 완료: '{query}' -> {len(content_matches)}개 결과"
            )
            return content_matches

        except Exception as e:
            logger.error(f"❌ 내용 검색 중 오류: {e}")
            return []

    def _extract_search_context(
        self, content: str, query: str, context_length: int = 100
    ) -> str:
        """검색어 주변 컨텍스트 추출"""
        try:
            query_lower = query.lower()
            content_lower = content.lower()

            # 첫 번째 매칭 위치 찾기
            match_pos = content_lower.find(query_lower)
            if match_pos == -1:
                return (
                    content[:context_length] + "..."
                    if len(content) > context_length
                    else content
                )

            # 컨텍스트 범위 계산
            start = max(0, match_pos - context_length // 2)
            end = min(len(content), match_pos + len(query) + context_length // 2)

            context = content[start:end]

            # 앞뒤에 ... 추가
            if start > 0:
                context = "..." + context
            if end < len(content):
                context = context + "..."

            return context

        except Exception as e:
            logger.warning(f"⚠️ 컨텍스트 추출 실패: {e}")
            return (
                content[:context_length] + "..."
                if len(content) > context_length
                else content
            )

    def _enhance_search_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """검색 결과에 추가 정보 포함"""
        try:
            enhanced = result.copy()

            # Notion 페이지 링크 생성
            page_id = result.get("page_id", "")
            if page_id:
                enhanced["notion_url"] = f"https://notion.so/{page_id.replace('-', '')}"

            # 주요 프로퍼티 추출 (기존 필드들 사용)
            main_properties = {}

            # 기본 정보들
            if result.get("page_type"):
                main_properties["페이지 타입"] = result.get("page_type")
            if result.get("database_type"):
                main_properties["데이터베이스"] = result.get("database_type")
            if result.get("created_by"):
                main_properties["생성자"] = result.get("created_by")
            if result.get("created_time"):
                main_properties["생성일"] = result.get("created_time")
            if result.get("last_edited_time"):
                main_properties["수정일"] = result.get("last_edited_time")

            # Notion properties가 있는 경우 추가
            properties = result.get("properties", {})
            for key, value in properties.items():
                if value is not None and value != "" and value != []:
                    # 값이 너무 길면 잘라내기
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    main_properties[key] = value

            enhanced["main_properties"] = main_properties

            # 검색 매칭 타입 표시
            if "search_context" in result:
                enhanced["match_type"] = "content"
            elif result.get("_match_score", 0) > 0:
                enhanced["match_type"] = "title"
            else:
                enhanced["match_type"] = "unknown"

            return enhanced

        except Exception as e:
            logger.warning(f"⚠️ 검색 결과 강화 실패: {e}")
            return result

    @safe_execution("get_related_keywords")
    async def get_related_keywords(self, query: str, limit: int = 5) -> List[str]:
        """연관 검색어 추천"""
        try:
            collection = get_meetup_collection("notion_pages")

            # 현재 검색어와 관련된 페이지들에서 키워드 추출
            query_regex = re.compile(re.escape(query), re.IGNORECASE)
            related_pages = (
                await collection.find({"title": {"$regex": query_regex}})
                .limit(20)
                .to_list(None)
            )

            # 제목에서 키워드 추출
            keywords = set()
            for page in related_pages:
                title = page.get("title", "")
                # 제목을 단어로 분리하고 2글자 이상인 것만 추출
                words = re.findall(r"\b\w{2,}\b", title)
                for word in words:
                    if word.lower() != query.lower() and len(word) >= 2:
                        keywords.add(word)

            # 최근에 많이 사용된 키워드들을 우선순위로
            keyword_freq = {}
            for keyword in keywords:
                count = await collection.count_documents(
                    {"title": {"$regex": re.compile(re.escape(keyword), re.IGNORECASE)}}
                )
                keyword_freq[keyword] = count

            # 빈도순으로 정렬
            sorted_keywords = sorted(
                keyword_freq.items(), key=lambda x: x[1], reverse=True
            )

            return [keyword for keyword, _ in sorted_keywords[:limit]]

        except Exception as e:
            logger.warning(f"⚠️ 연관 검색어 생성 실패: {e}")
            return []

    @safe_execution("get_search_suggestions")
    async def get_search_suggestions(self, query: str) -> Dict[str, Any]:
        """검색 제안 및 추천"""
        try:
            collection = get_meetup_collection("notion_pages")

            suggestions = {
                "did_you_mean": [],
                "related_keywords": [],
                "popular_searches": [],
                "recent_activity": [],
            }

            # 1. 오타 교정 제안 (간단한 방식)
            if len(query) > 3:
                # 비슷한 제목들 찾기
                similar_titles = (
                    await collection.find(
                        {
                            "title": {
                                "$regex": re.compile(f".*{query[:-1]}.*", re.IGNORECASE)
                            }
                        }
                    )
                    .limit(3)
                    .to_list(None)
                )

                for page in similar_titles:
                    title_words = re.findall(r"\b\w+\b", page.get("title", ""))
                    for word in title_words:
                        if len(word) > 2 and word.lower() != query.lower():
                            if self._is_similar(query, word):
                                suggestions["did_you_mean"].append(word)

            # 2. 연관 검색어
            suggestions["related_keywords"] = await self.get_related_keywords(query)

            # 3. 인기 검색어 (최근 활동이 많은 키워드들)
            recent_pages = (
                await collection.find({}).sort("created_at", -1).limit(20).to_list(None)
            )
            word_counts = {}
            for page in recent_pages:
                words = re.findall(r"\b\w{2,}\b", page.get("title", ""))
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1

            popular = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            suggestions["popular_searches"] = [
                word for word, _ in popular if word.lower() != query.lower()
            ]

            # 4. 최근 활동
            recent_activity = (
                await collection.find({}).sort("created_at", -1).limit(5).to_list(None)
            )
            suggestions["recent_activity"] = [
                {
                    "title": page.get("title", ""),
                    "type": page.get("page_type", "unknown"),
                    "created_at": page.get("created_at"),
                }
                for page in recent_activity
            ]

            return suggestions

        except Exception as e:
            logger.warning(f"⚠️ 검색 제안 생성 실패: {e}")
            return {
                "did_you_mean": [],
                "related_keywords": [],
                "popular_searches": [],
                "recent_activity": [],
            }

    def _is_similar(self, word1: str, word2: str, threshold: float = 0.7) -> bool:
        """두 단어의 유사도 검사 (간단한 편집 거리 기반)"""
        if abs(len(word1) - len(word2)) > 2:
            return False

        # 간단한 유사도 검사
        common_chars = set(word1.lower()) & set(word2.lower())
        similarity = len(common_chars) / max(len(word1), len(word2))
        return similarity >= threshold

    def format_search_results(self, search_data: Dict[str, Any]) -> str:
        """검색 결과를 Discord 메시지 형식으로 포맷팅 (연관 검색어 포함)"""
        query = search_data.get("query", "")
        total = search_data.get("total_results", 0)
        results = search_data.get("results", [])
        filters = search_data.get("filters", {})
        suggestions = search_data.get("suggestions", {})

        if total == 0:
            msg = f"🔍 **검색 결과 없음**\n"
            msg += f"검색어: `{query}`\n\n"

            # 검색 결과가 없을 때 제안 표시
            if suggestions:
                if suggestions.get("did_you_mean"):
                    msg += f"🤔 **이것을 찾으셨나요?**: {', '.join(suggestions['did_you_mean'][:3])}\n\n"

                if suggestions.get("related_keywords"):
                    msg += f"💡 **연관 검색어**: {', '.join(suggestions['related_keywords'][:5])}\n\n"

                if suggestions.get("popular_searches"):
                    msg += f"🔥 **인기 검색어**: {', '.join(suggestions['popular_searches'][:5])}\n\n"

                if suggestions.get("recent_activity"):
                    msg += "📋 **최근 활동**:\n"
                    for activity in suggestions["recent_activity"][:3]:
                        msg += f"   • {activity['title']} ({activity['type']})\n"
            else:
                msg += "다른 키워드로 다시 시도해보세요."

            return msg

        msg = f"🔍 **검색 결과** (`{query}`)\n"
        msg += f"📊 총 {total}개 결과"

        # 필터 정보 표시
        filter_info = []
        if filters.get("type") and filters["type"] != "all":
            filter_info.append(f"타입: {filters['type']}")
        if filters.get("user") and filters["user"] != "all":
            filter_info.append(f"사용자: {filters['user'][-4:]}")
        if filters.get("days"):
            filter_info.append(f"최근 {filters['days']}일")

        if filter_info:
            msg += f" ({', '.join(filter_info)})"

        msg += "\n\n"

        # 결과 목록
        for i, result in enumerate(results[:8], 1):  # 8개로 줄여서 제안 공간 확보
            title = result.get("title", "제목 없음")
            page_type = result.get("page_type", "unknown")
            created_at = result.get("created_at")
            user_id = result.get("created_by", "unknown")

            # 타입 이모지
            type_emoji = (
                "📝"
                if page_type == "note"
                else (
                    "📅"
                    if page_type == "meeting"
                    else ("✅" if page_type == "task" else "📄")
                )
            )

            # 날짜 포맷
            date_str = "날짜 미상"
            if created_at:
                if isinstance(created_at, datetime):
                    date_str = created_at.strftime("%m/%d %H:%M")
                else:
                    date_str = str(created_at)[:10]  # YYYY-MM-DD만

            # 노션 페이지 링크 추가
            notion_url = result.get("notion_url", "")

            msg += f"{type_emoji} **{title}**\n"
            msg += f"   📅 {date_str} | 👤 User {user_id[-4:]} | 📂 {page_type}\n"
            if notion_url:
                msg += f"   🔗 [노션에서 보기]({notion_url})\n"

            # 검색 컨텍스트 표시 (내용 검색인 경우)
            if result.get("search_context"):
                context = result["search_context"][:120]  # 길이 제한 줄임
                msg += f"   💬 {context}\n"

            msg += "\n"

        # 더 많은 결과가 있는 경우
        if total > 8:
            msg += f"... 그 외 {total - 8}개 결과 더 있음\n\n"

        # 검색 제안 추가 (결과가 있어도 표시)
        if suggestions and total < 15:  # 결과가 적을 때만 제안 표시
            suggestion_parts = []

            if suggestions.get("related_keywords"):
                suggestion_parts.append(
                    f"🔗 **연관**: {', '.join(suggestions['related_keywords'][:4])}"
                )

            if suggestions.get("popular_searches"):
                popular = [
                    s
                    for s in suggestions["popular_searches"][:3]
                    if s.lower() != query.lower()
                ]
                if popular:
                    suggestion_parts.append(f"🔥 **인기**: {', '.join(popular)}")

            if suggestion_parts:
                msg += "---\n" + " | ".join(suggestion_parts)

        return msg


# Global search service instance
search_service = SearchService()
