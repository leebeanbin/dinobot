"""
고성능 검색 서비스 모듈
- MongoDB 텍스트 인덱스 활용
- 가중치 기반 검색
- 성능 최적화
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.core.database import get_meetup_collection, mongodb_connection
from src.core.logger import get_logger
from src.core.exceptions import safe_execution

# Module logger
logger = get_logger("services.enhanced_search")


class EnhancedSearchService:
    """고성능 검색 서비스"""

    def __init__(self):
        self.cache = {}  # 검색 결과 캐시
        self.cache_ttl = 300  # 5분 캐시 TTL

    @safe_execution("search_pages_enhanced")
    async def search_pages_enhanced(
        self,
        query: str,
        page_type: str = None,
        user_filter: str = None,
        days_limit: int = 90,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        고성능 페이지 검색

        Args:
            query: 검색 키워드
            page_type: 페이지 타입 필터
            user_filter: 사용자 ID 필터
            days_limit: 검색 기간 제한 (일)
            limit: 결과 개수 제한
        """
        if not query or len(query.strip()) < 2:
            return {
                "total_results": 0,
                "results": [],
                "query": query,
                "filters": {"type": page_type, "user": user_filter, "days": days_limit},
                "search_time_ms": 0,
            }

        start_time = datetime.now()

        try:
            await mongodb_connection.connect_database()
            collection = get_meetup_collection("notion_pages")

            # 1. MongoDB 텍스트 검색 (가장 빠름)
            text_results = await self._text_search(collection, query, limit)

            # 2. 가중치 기반 검색 (제목 우선)
            weighted_results = await self._weighted_search(
                collection, query, page_type, user_filter, days_limit, limit
            )

            # 3. 결과 합치기 및 중복 제거
            all_results = self._merge_results(text_results, weighted_results)

            # 4. 최종 결과 정렬 및 제한
            final_results = self._rank_and_limit_results(all_results, query, limit)

            search_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"🔍 고성능 검색 완료: '{query}' -> {len(final_results)}개 결과 ({search_time:.1f}ms)"
            )

            return {
                "total_results": len(final_results),
                "results": final_results,
                "query": query,
                "filters": {"type": page_type, "user": user_filter, "days": days_limit},
                "search_time_ms": search_time,
            }

        except Exception as e:
            logger.error(f"❌ 고성능 검색 실패: {e}")
            raise e
        finally:
            await mongodb_connection.disconnect()

    @safe_execution("text_search")
    async def _text_search(
        self, collection, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """MongoDB 텍스트 인덱스 검색 (가장 빠름)"""
        try:
            # MongoDB 텍스트 검색 사용
            cursor = (
                collection.find(
                    {"$text": {"$search": query}}, {"score": {"$meta": "textScore"}}
                )
                .sort([("score", {"$meta": "textScore"})])
                .limit(limit)
            )

            results = await cursor.to_list(None)

            # 검색 점수 추가
            for result in results:
                result["search_score"] = result.get("score", 0)
                result["search_type"] = "text_index"

            logger.debug(f"📊 텍스트 인덱스 검색: {len(results)}개 결과")
            return results

        except Exception as e:
            logger.warning(f"⚠️ 텍스트 인덱스 검색 실패: {e}")
            return []

    @safe_execution("weighted_search")
    async def _weighted_search(
        self,
        collection,
        query: str,
        page_type: str,
        user_filter: str,
        days_limit: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """가중치 기반 검색 (제목 > 내용)"""

        # 검색 조건 구성
        search_conditions = []

        # 날짜 범위 필터
        if days_limit:
            since_date = datetime.now() - timedelta(days=days_limit)
            search_conditions.append({"created_at": {"$gte": since_date}})

        # 타입 필터
        if page_type and page_type != "all":
            search_conditions.append({"page_type": page_type})

        # 사용자 필터
        if user_filter and user_filter != "all":
            search_conditions.append({"created_by": user_filter})

        # MongoDB 쿼리 구성
        if search_conditions:
            mongo_query = {"$and": search_conditions}
        else:
            mongo_query = {}

        # 모든 페이지 가져오기 (Python 레벨에서 가중치 계산)
        all_pages = await collection.find(mongo_query).to_list(None)

        # 가중치 기반 검색
        weighted_results = []
        query_lower = query.lower()

        for page in all_pages:
            score = 0
            search_type = "none"

            title = page.get("title", "")
            content = page.get("content", "")
            search_text = page.get("search_text", "")

            # 제목 검색 (가중치 높음)
            if query_lower in title.lower():
                title_matches = len(re.findall(re.escape(query_lower), title.lower()))
                score += title_matches * 10  # 제목 가중치 10
                search_type = "title"

            # 내용 검색 (가중치 중간)
            if content and query_lower in content.lower():
                content_matches = len(
                    re.findall(re.escape(query_lower), content.lower())
                )
                score += content_matches * 3  # 내용 가중치 3
                if search_type == "title":
                    search_type = "title_content"
                else:
                    search_type = "content"

            # 통합 검색 텍스트 (가중치 낮음)
            if search_text and query_lower in search_text.lower():
                search_matches = len(
                    re.findall(re.escape(query_lower), search_text.lower())
                )
                score += search_matches * 1  # 통합 검색 가중치 1
                if search_type == "none":
                    search_type = "search_text"

            # 점수가 있는 결과만 추가
            if score > 0:
                page["search_score"] = score
                page["search_type"] = search_type
                weighted_results.append(page)

        # 점수순 정렬
        weighted_results.sort(key=lambda x: x.get("search_score", 0), reverse=True)

        logger.debug(f"📊 가중치 검색: {len(weighted_results)}개 결과")
        return weighted_results[:limit]

    def _merge_results(
        self, text_results: List[Dict], weighted_results: List[Dict]
    ) -> List[Dict]:
        """검색 결과 합치기 및 중복 제거"""
        seen_page_ids = set()
        merged_results = []

        # 텍스트 인덱스 결과 우선 (MongoDB가 계산한 점수)
        for result in text_results:
            page_id = result.get("page_id")
            if page_id not in seen_page_ids:
                seen_page_ids.add(page_id)
                merged_results.append(result)

        # 가중치 검색 결과 추가 (중복 제외)
        for result in weighted_results:
            page_id = result.get("page_id")
            if page_id not in seen_page_ids:
                seen_page_ids.add(page_id)
                merged_results.append(result)

        return merged_results

    def _rank_and_limit_results(
        self, results: List[Dict], query: str, limit: int
    ) -> List[Dict]:
        """결과 정렬 및 제한"""
        # 검색 점수순 정렬
        results.sort(key=lambda x: x.get("search_score", 0), reverse=True)

        # 결과 제한
        final_results = results[:limit]

        # 검색 컨텍스트 추가
        for result in final_results:
            result["search_context"] = self._extract_search_context(
                result.get("content", ""), query
            )

        return final_results

    def _extract_search_context(
        self, content: str, query: str, context_length: int = 150
    ) -> str:
        """검색 컨텍스트 추출"""
        if not content:
            return ""

        query_lower = query.lower()
        content_lower = content.lower()

        # 검색어 위치 찾기
        query_pos = content_lower.find(query_lower)
        if query_pos == -1:
            return (
                content[:context_length] + "..."
                if len(content) > context_length
                else content
            )

        # 검색어 주변 컨텍스트 추출
        start = max(0, query_pos - context_length // 2)
        end = min(len(content), query_pos + context_length // 2)

        context = content[start:end]
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context

    @safe_execution("get_search_suggestions_enhanced")
    async def get_search_suggestions_enhanced(self, query: str) -> Dict[str, Any]:
        """향상된 검색 제안"""
        try:
            await mongodb_connection.connect_database()
            collection = get_meetup_collection("notion_pages")

            suggestions = {
                "did_you_mean": [],
                "related_keywords": [],
                "popular_searches": [],
                "recent_activity": [],
            }

            # 1. 연관 검색어 (키워드 기반)
            if len(query) > 2:
                # 최근 페이지들에서 키워드 추출
                recent_pages = (
                    await collection.find({})
                    .sort("created_at", -1)
                    .limit(20)
                    .to_list(None)
                )

                keywords = set()
                for page in recent_pages:
                    title = page.get("title", "")
                    content = page.get("content", "")

                    # 제목과 내용에서 키워드 추출
                    words = re.findall(r"\b\w{2,}\b", f"{title} {content}")
                    for word in words:
                        if word.lower() != query.lower() and len(word) >= 2:
                            keywords.add(word)

                # 키워드 빈도 계산
                keyword_freq = {}
                for keyword in keywords:
                    count = await collection.count_documents(
                        {
                            "$or": [
                                {"title": {"$regex": keyword, "$options": "i"}},
                                {"content": {"$regex": keyword, "$options": "i"}},
                            ]
                        }
                    )
                    keyword_freq[keyword] = count

                # 상위 키워드 선택
                suggestions["related_keywords"] = sorted(
                    keyword_freq.items(), key=lambda x: x[1], reverse=True
                )[:5]

            # 2. 인기 검색어
            recent_pages = (
                await collection.find({}).sort("created_at", -1).limit(50).to_list(None)
            )
            word_counts = {}

            for page in recent_pages:
                title = page.get("title", "")
                words = re.findall(r"\b\w{2,}\b", title)
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1

            suggestions["popular_searches"] = sorted(
                word_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]

            # 3. 최근 활동
            suggestions["recent_activity"] = [
                {
                    "title": page.get("title", ""),
                    "type": page.get("page_type", "unknown"),
                    "created_at": page.get("created_at"),
                }
                for page in recent_pages[:5]
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
        finally:
            await mongodb_connection.disconnect()

    def format_search_results_enhanced(self, search_data: Dict[str, Any]) -> str:
        """향상된 검색 결과 포맷팅"""
        query = search_data.get("query", "")
        total = search_data.get("total_results", 0)
        results = search_data.get("results", [])
        filters = search_data.get("filters", {})
        search_time = search_data.get("search_time_ms", 0)
        suggestions = search_data.get("suggestions", {})

        if total == 0:
            msg = f"🔍 **검색 결과 없음**\n"
            msg += f"검색어: `{query}`\n\n"

            if suggestions:
                if suggestions.get("related_keywords"):
                    keywords = [kw for kw, _ in suggestions["related_keywords"][:3]]
                    msg += f"💡 **연관 검색어**: {', '.join(keywords)}\n\n"

                if suggestions.get("popular_searches"):
                    popular = [kw for kw, _ in suggestions["popular_searches"][:3]]
                    msg += f"🔥 **인기 검색어**: {', '.join(popular)}\n\n"
            else:
                msg += "다른 키워드로 다시 시도해보세요."

            return msg

        msg = f"🔍 **검색 결과** (`{query}`)\n"
        msg += f"📊 총 {total}개 결과"

        if search_time > 0:
            msg += f" ({search_time:.1f}ms)"

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
        for i, result in enumerate(results[:10], 1):
            title = result.get("title", "제목 없음")
            page_type = result.get("page_type", "unknown")
            created_at = result.get("created_at")
            user_id = result.get("created_by", "unknown")
            search_type = result.get("search_type", "unknown")
            search_score = result.get("search_score", 0)

            # 타입 이모지
            type_emoji = {
                "meeting": "📅",
                "task": "✅",
                "document": "📄",
                "note": "📝",
            }.get(page_type, "📄")

            # 날짜 포맷
            date_str = "날짜 미상"
            if created_at:
                if isinstance(created_at, datetime):
                    date_str = created_at.strftime("%m/%d %H:%M")
                else:
                    date_str = str(created_at)[:10]

            msg += f"{type_emoji} **{title}**\n"
            msg += f"   📅 {date_str} | 👤 User {user_id[-4:]} | 📂 {page_type}"

            # 검색 타입 표시
            if search_type != "unknown":
                msg += f" | 🔍 {search_type}"

            msg += "\n"

            # 검색 컨텍스트 표시
            if result.get("search_context"):
                context = result["search_context"][:120]
                msg += f"   💬 {context}\n"

            msg += "\n"

        # 더 많은 결과가 있는 경우
        if total > 10:
            msg += f"... 그 외 {total - 10}개 결과 더 있음\n\n"

        return msg


# Global enhanced search service instance
enhanced_search_service = EnhancedSearchService()
