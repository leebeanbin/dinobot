"""
간단한 통계 분석 서비스 모듈
- 일별/주별/월별 활동 통계
- 사용자별 작업 분석
- 회의 참석 패턴 분석
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from src.core.database import get_meetup_collection, mongodb_connection
from src.core.logger import get_logger
from src.core.exceptions import safe_execution
from .chart_service import ChartGeneratorService

logger = get_logger("services.analytics")


class SimpleStatsService:
    """간단한 통계 분석 서비스"""

    def __init__(self):
        # 통계 분석 서비스 초기화 (로그 제거)
        pass

    @safe_execution("get_daily_stats")
    async def get_daily_stats(
        self, date: datetime = None, user_filter: str = None
    ) -> Dict[str, Any]:
        """특정 날짜의 활동 통계 (Notion created_time 기준)"""
        if not date:
            date = datetime.now()

        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        collection = get_meetup_collection("notion_pages")

        # Notion created_time 기준으로 쿼리 (ISO 문자열 형식)
        query = {
            "created_time": {
                "$gte": start_time.isoformat() + "Z",
                "$lt": end_time.isoformat() + "Z",
            }
        }

        # 사용자 필터 적용
        if user_filter and user_filter != "all":
            query["created_by"] = user_filter

        # 해당 날짜의 모든 페이지 조회
        daily_pages = await collection.find(query).to_list(None)

        stats = {
            "date": date.strftime("%Y-%m-%d"),
            "total_pages": len(daily_pages),
            "by_type": defaultdict(int),
            "by_user": defaultdict(int),
            "by_hour": defaultdict(int),
            "pages": [],
        }

        for page in daily_pages:
            page_type = page.get("page_type", "unknown")
            user_id = page.get("created_by", "unknown")
            created_at = page.get("created_at")
            hour = created_at.hour if created_at else 0

            stats["by_type"][page_type] += 1
            stats["by_user"][user_id] += 1
            stats["by_hour"][hour] += 1

            stats["pages"].append(
                {
                    "title": page.get("title", "No title"),
                    "type": page_type,
                    "user": user_id,
                    "time": created_at.strftime("%H:%M") if created_at else "unknown",
                }
            )

        # defaultdict를 일반 dict로 변환
        stats["by_type"] = dict(stats["by_type"])
        stats["by_user"] = dict(stats["by_user"])
        stats["by_hour"] = dict(stats["by_hour"])

        logger.info(
            f"📅 일별 통계 조회 완료: {date.strftime('%Y-%m-%d')} ({stats['total_pages']}개 활동)"
        )
        return stats

    @safe_execution("get_weekly_stats")
    async def get_weekly_stats(
        self, start_date: datetime = None, user_filter: str = None
    ) -> Dict[str, Any]:
        """주별 활동 통계 (월요일 시작)"""
        if not start_date:
            start_date = datetime.now()

        # 주의 시작(월요일) 계산
        days_since_monday = start_date.weekday()
        monday = start_date - timedelta(days=days_since_monday)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

        end_time = monday + timedelta(days=7)

        collection = get_meetup_collection("notion_pages")

        # Notion created_time 기준으로 쿼리 (ISO 문자열 형식)
        query = {
            "created_time": {
                "$gte": monday.isoformat() + "Z",
                "$lt": end_time.isoformat() + "Z",
            }
        }

        # 사용자 필터 적용
        if user_filter and user_filter != "all":
            query["created_by"] = user_filter

        weekly_pages = await collection.find(query).to_list(None)

        stats = {
            "week_start": monday.strftime("%Y-%m-%d"),
            "week_end": (end_time - timedelta(days=1)).strftime("%Y-%m-%d"),
            "total_pages": len(weekly_pages),
            "by_type": defaultdict(int),
            "by_user": defaultdict(int),
            "by_day": defaultdict(int),
            "daily_breakdown": {},
        }

        for page in weekly_pages:
            page_type = page.get("page_type", "unknown")
            user_id = page.get("created_by", "unknown")
            created_at = page.get("created_at")

            if created_at:
                day_name = created_at.strftime("%A")  # Monday, Tuesday, etc.
                date_str = created_at.strftime("%Y-%m-%d")

                stats["by_type"][page_type] += 1
                stats["by_user"][user_id] += 1
                stats["by_day"][day_name] += 1

                if date_str not in stats["daily_breakdown"]:
                    stats["daily_breakdown"][date_str] = {"count": 0, "pages": []}

                stats["daily_breakdown"][date_str]["count"] += 1
                stats["daily_breakdown"][date_str]["pages"].append(
                    {
                        "title": page.get("title", "No title"),
                        "type": page_type,
                        "user": user_id,
                        "time": created_at.strftime("%H:%M"),
                    }
                )

        # defaultdict를 일반 dict로 변환
        stats["by_type"] = dict(stats["by_type"])
        stats["by_user"] = dict(stats["by_user"])
        stats["by_day"] = dict(stats["by_day"])

        logger.info(
            f"📊 주별 통계 조회 완료: {stats['week_start']} ~ {stats['week_end']} ({stats['total_pages']}개 활동)"
        )
        return stats

    @safe_execution("get_monthly_stats")
    async def get_monthly_stats(
        self, year: int = None, month: int = None
    ) -> Dict[str, Any]:
        """월별 활동 통계"""
        now = datetime.now()
        if not year:
            year = now.year
        if not month:
            month = now.month

        start_time = datetime(year, month, 1)

        # 다음 달 첫날 계산
        if month == 12:
            end_time = datetime(year + 1, 1, 1)
        else:
            end_time = datetime(year, month + 1, 1)

        collection = get_meetup_collection("notion_pages")

        # Notion created_time 기준으로 쿼리 (ISO 문자열 형식)
        query = {
            "created_time": {
                "$gte": start_time.isoformat() + "Z",
                "$lt": end_time.isoformat() + "Z",
            }
        }

        monthly_pages = await collection.find(query).to_list(None)

        stats = {
            "year": year,
            "month": month,
            "month_name": start_time.strftime("%B"),
            "total_pages": len(monthly_pages),
            "by_type": defaultdict(int),
            "by_user": defaultdict(int),
            "by_week": defaultdict(int),
            "daily_breakdown": {},
        }

        for page in monthly_pages:
            page_type = page.get("page_type", "unknown")
            user_id = page.get("created_by", "unknown")
            created_time_str = page.get("created_time")

            if created_time_str:
                # ISO 문자열을 datetime으로 변환
                created_at = datetime.fromisoformat(
                    created_time_str.replace("Z", "+00:00")
                )

                # 주차 계산
                week_num = (created_at.day - 1) // 7 + 1
                date_str = created_at.strftime("%Y-%m-%d")

                stats["by_type"][page_type] += 1
                stats["by_user"][user_id] += 1
                stats["by_week"][f"Week {week_num}"] += 1

                if date_str not in stats["daily_breakdown"]:
                    stats["daily_breakdown"][date_str] = {"count": 0, "pages": []}

                stats["daily_breakdown"][date_str]["count"] += 1
                stats["daily_breakdown"][date_str]["pages"].append(
                    {
                        "title": page.get("title", "No title"),
                        "type": page_type,
                        "user": user_id,
                        "time": created_at.strftime("%H:%M"),
                    }
                )

        # defaultdict를 일반 dict로 변환
        stats["by_type"] = dict(stats["by_type"])
        stats["by_user"] = dict(stats["by_user"])
        stats["by_week"] = dict(stats["by_week"])

        # 일별 차트용 데이터 형식 추가
        stats["date"] = start_time.strftime("%Y-%m-%d")
        stats["by_hour"] = defaultdict(int)

        # 시간별 분포 계산
        for page in monthly_pages:
            created_time_str = page.get("created_time")
            if created_time_str:
                created_at = datetime.fromisoformat(
                    created_time_str.replace("Z", "+00:00")
                )
                hour = created_at.hour
                stats["by_hour"][f"{hour:02d}:00"] += 1

        stats["by_hour"] = dict(stats["by_hour"])

        # pages 키 추가 (일별 차트용)
        stats["pages"] = []
        for page in monthly_pages:
            created_time_str = page.get("created_time")
            if created_time_str:
                created_at = datetime.fromisoformat(
                    created_time_str.replace("Z", "+00:00")
                )
                stats["pages"].append(
                    {
                        "title": page.get("title", "No title"),
                        "type": page.get("page_type", "unknown"),
                        "user": page.get("created_by", "unknown"),
                        "time": created_at.strftime("%H:%M"),
                    }
                )

        logger.info(
            f"📅 월별 통계 조회 완료: {year}년 {month}월 ({stats['total_pages']}개 활동)"
        )
        return stats

    @safe_execution("get_user_productivity_stats")
    async def get_user_productivity_stats(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """사용자별 생산성 분석"""
        since_date = datetime.now() - timedelta(days=days)

        collection = get_meetup_collection("notion_pages")

        user_pages = await collection.find(
            {
                "created_by": user_id,
                "created_time": {"$gte": since_date.isoformat() + "Z"},
            }
        ).to_list(None)

        stats = {
            "user_id": user_id,
            "period_days": days,
            "total_pages": len(user_pages),
            "by_type": defaultdict(int),
            "by_day_of_week": defaultdict(int),
            "by_hour": defaultdict(int),
            "daily_activity": defaultdict(int),
            "most_productive_day": None,
            "most_productive_hour": None,
            "avg_pages_per_day": 0,
        }

        for page in user_pages:
            page_type = page.get("page_type", "unknown")
            created_at = page.get("created_at")

            if created_at:
                day_of_week = created_at.strftime("%A")
                hour = created_at.hour
                date_str = created_at.strftime("%Y-%m-%d")

                stats["by_type"][page_type] += 1
                stats["by_day_of_week"][day_of_week] += 1
                stats["by_hour"][hour] += 1
                stats["daily_activity"][date_str] += 1

        # 가장 생산적인 요일과 시간 계산
        if stats["by_day_of_week"]:
            stats["most_productive_day"] = max(
                stats["by_day_of_week"], key=stats["by_day_of_week"].get
            )

        if stats["by_hour"]:
            stats["most_productive_hour"] = max(
                stats["by_hour"], key=stats["by_hour"].get
            )

        # 일평균 페이지 수 계산
        active_days = len([d for d in stats["daily_activity"].values() if d > 0])
        if active_days > 0:
            stats["avg_pages_per_day"] = round(stats["total_pages"] / active_days, 2)

        # defaultdict를 일반 dict로 변환
        stats["by_type"] = dict(stats["by_type"])
        stats["by_day_of_week"] = dict(stats["by_day_of_week"])
        stats["by_hour"] = dict(stats["by_hour"])
        stats["daily_activity"] = dict(stats["daily_activity"])

        logger.info(
            f"👤 사용자 생산성 분석 완료: {user_id} (최근 {days}일, {stats['total_pages']}개 활동)"
        )
        return stats

    @safe_execution("get_team_comparison_stats")
    async def get_team_comparison_stats(self, days: int = 30) -> Dict[str, Any]:
        """팀 멤버별 활동 비교"""
        since_date = datetime.now() - timedelta(days=days)

        collection = get_meetup_collection("notion_pages")

        all_pages = await collection.find(
            {"created_time": {"$gte": since_date.isoformat() + "Z"}}
        ).to_list(None)

        team_stats = {
            "period_days": days,
            "total_team_pages": len(all_pages),
            "members": defaultdict(
                lambda: {
                    "total_pages": 0,
                    "by_type": defaultdict(int),
                    "most_active_day": None,
                    "activity_score": 0,
                }
            ),
        }

        user_daily_activity = defaultdict(lambda: defaultdict(int))

        for page in all_pages:
            user_id = page.get("created_by", "unknown")
            page_type = page.get("page_type", "unknown")
            created_at = page.get("created_at")

            team_stats["members"][user_id]["total_pages"] += 1
            team_stats["members"][user_id]["by_type"][page_type] += 1

            if created_at:
                date_str = created_at.strftime("%Y-%m-%d")
                user_daily_activity[user_id][date_str] += 1

        # 각 사용자의 가장 활발한 날과 활동 점수 계산
        for user_id, member_data in team_stats["members"].items():
            daily_counts = user_daily_activity[user_id]
            if daily_counts:
                most_active_day = max(daily_counts, key=daily_counts.get)
                member_data["most_active_day"] = {
                    "date": most_active_day,
                    "pages": daily_counts[most_active_day],
                }

                # 활동 점수: 총 페이지 수 + 활동 일수
                active_days = len([d for d in daily_counts.values() if d > 0])
                member_data["activity_score"] = member_data["total_pages"] + active_days

            # defaultdict를 일반 dict로 변환
            member_data["by_type"] = dict(member_data["by_type"])

        # defaultdict를 일반 dict로 변환
        team_stats["members"] = dict(team_stats["members"])

        logger.info(
            f"👥 팀 활동 비교 완료: 최근 {days}일, {len(team_stats['members'])}명, {team_stats['total_team_pages']}개 활동"
        )
        return team_stats

    @safe_execution("get_task_completion_stats")
    async def get_task_completion_stats(
        self, days: int = 30, status_filter: str = None, user_filter: str = None
    ) -> Dict[str, Any]:
        """Task 완료 통계 (Notion API와 연동하여 실제 상태 확인)"""
        from src.core.config import settings
        # notion_service는 ServiceManager를 통해 접근

        since_date = datetime.now() - timedelta(days=days)

        collection = get_meetup_collection("notion_pages")

        # 쿼리 조건 설정 (Notion created_time 기준)
        query = {
            "page_type": "task",
            "created_time": {"$gte": since_date.isoformat() + "Z"},
        }

        # 사용자 필터 적용
        if user_filter and user_filter != "all":
            query["created_by"] = user_filter

        # Task 타입 페이지만 조회
        task_pages = await collection.find(query).to_list(None)

        stats = {
            "period_days": days,
            "total_tasks": len(task_pages),
            "by_status": defaultdict(int),
            "by_user": defaultdict(
                lambda: {
                    "total": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "not_started": 0,
                    "completion_rate": 0,
                }
            ),
            "tasks_details": [],
        }

        # 각 Task의 현재 상태를 Notion에서 확인
        for task in task_pages:
            try:
                # ServiceManager를 통해 notion_service 접근
                from src.core.service_manager import service_manager
                notion_service = service_manager.get_service("notion")

                # Notion API로 현재 상태 확인
                notion_page = await notion_service.notion_client.pages.retrieve(
                    page_id=task["page_id"]
                )

                # Status 속성에서 현재 상태 가져오기
                properties = notion_page.get("properties", {})
                status_prop = properties.get("Status", {})
                current_status = "unknown"

                if status_prop.get("type") == "status" and status_prop.get("status"):
                    current_status = status_prop["status"]["name"]

                user_id = task.get("created_by", "unknown")

                # 통계 업데이트
                stats["by_status"][current_status] += 1
                stats["by_user"][user_id]["total"] += 1

                if current_status == "Done":
                    stats["by_user"][user_id]["completed"] += 1
                elif current_status == "In progress":
                    stats["by_user"][user_id]["in_progress"] += 1
                elif current_status == "Not started":
                    stats["by_user"][user_id]["not_started"] += 1

                # 상세 정보 추가
                stats["tasks_details"].append(
                    {
                        "title": task.get("title", "No title"),
                        "status": current_status,
                        "user": user_id,
                        "created_at": task.get("created_at"),
                        "page_id": task["page_id"],
                    }
                )

            except Exception as e:
                logger.warning(
                    f"⚠️ Task 상태 확인 실패 (페이지 ID: {task.get('page_id')}): {e}"
                )
                # 실패한 경우 unknown으로 처리
                stats["by_status"]["unknown"] += 1

        # 완료율 계산
        for user_id, user_data in stats["by_user"].items():
            if user_data["total"] > 0:
                user_data["completion_rate"] = round(
                    (user_data["completed"] / user_data["total"]) * 100, 1
                )

        # 상태 필터 적용 (Notion API에서 상태를 가져온 후)
        if status_filter and status_filter != "all":
            # 필터링된 task_details
            filtered_tasks = [
                task
                for task in stats["tasks_details"]
                if task["status"].lower() == status_filter.lower()
            ]

            # 통계 재계산
            stats["tasks_details"] = filtered_tasks
            stats["total_tasks"] = len(filtered_tasks)
            stats["by_status"] = defaultdict(int)
            stats["by_user"] = defaultdict(
                lambda: {
                    "total": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "not_started": 0,
                    "completion_rate": 0,
                }
            )

            # 필터링된 데이터로 다시 집계
            for task in filtered_tasks:
                current_status = task["status"]
                user_id = task["user"]

                stats["by_status"][current_status] += 1
                stats["by_user"][user_id]["total"] += 1

                if current_status == "Done":
                    stats["by_user"][user_id]["completed"] += 1
                elif current_status == "In progress":
                    stats["by_user"][user_id]["in_progress"] += 1
                elif current_status == "Not started":
                    stats["by_user"][user_id]["not_started"] += 1

            # 완료율 재계산
            for user_id, user_data in stats["by_user"].items():
                if user_data["total"] > 0:
                    user_data["completion_rate"] = round(
                        (user_data["completed"] / user_data["total"]) * 100, 1
                    )

        # defaultdict를 일반 dict로 변환
        stats["by_status"] = dict(stats["by_status"])
        stats["by_user"] = dict(stats["by_user"])

        filter_info = ""
        if status_filter and status_filter != "all":
            filter_info = f" (상태: {status_filter})"
        if user_filter and user_filter != "all":
            filter_info += f" (사용자: {user_filter[-4:]})"

        logger.info(
            f"📊 Task 완료 통계 조회 완료: 최근 {days}일, {stats['total_tasks']}개 Task{filter_info}"
        )
        return stats

    @safe_execution("get_activity_trends_stats")
    async def get_activity_trends_stats(self, days: int = 14) -> Dict[str, Any]:
        """활동 트렌드 분석 (최근 N일)"""
        since_date = datetime.now() - timedelta(days=days)

        collection = get_meetup_collection("notion_pages")

        recent_pages = await collection.find(
            {"created_at": {"$gte": since_date}}
        ).to_list(None)

        trends = {
            "period_days": days,
            "total_pages": len(recent_pages),
            "daily_trend": {},
            "busiest_day": None,
            "quietest_day": None,
            "avg_daily_pages": 0,
            "growth_rate": 0,
        }

        # 일별 활동 수집
        daily_counts = defaultdict(int)
        for page in recent_pages:
            created_at = page.get("created_at")
            if created_at:
                date_str = created_at.strftime("%Y-%m-%d")
                daily_counts[date_str] += 1

        # 모든 날짜에 대해 0으로 초기화 (빈 날짜도 표시)
        current_date = since_date
        while current_date < datetime.now():
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in daily_counts:
                daily_counts[date_str] = 0
            current_date += timedelta(days=1)

        trends["daily_trend"] = dict(sorted(daily_counts.items()))

        if daily_counts:
            # 가장 바쁜/조용한 날
            trends["busiest_day"] = {
                "date": max(daily_counts, key=daily_counts.get),
                "pages": max(daily_counts.values()),
            }
            trends["quietest_day"] = {
                "date": min(daily_counts, key=daily_counts.get),
                "pages": min(daily_counts.values()),
            }

            # 일평균 페이지 수
            trends["avg_daily_pages"] = round(
                sum(daily_counts.values()) / len(daily_counts), 2
            )

            # 성장률 계산 (첫 주 vs 둘째 주)
            if days >= 14:
                dates = sorted(daily_counts.keys())
                mid_point = len(dates) // 2

                first_half_avg = (
                    sum(daily_counts[date] for date in dates[:mid_point]) / mid_point
                )
                second_half_avg = sum(
                    daily_counts[date] for date in dates[mid_point:]
                ) / (len(dates) - mid_point)

                if first_half_avg > 0:
                    trends["growth_rate"] = round(
                        ((second_half_avg - first_half_avg) / first_half_avg) * 100, 2
                    )

        logger.info(
            f"📈 활동 트렌드 분석 완료: 최근 {days}일, 평균 {trends['avg_daily_pages']}개/일"
        )
        return trends

    def format_stats_message(self, stats: Dict[str, Any], stats_type: str) -> str:
        """통계 데이터를 Discord 메시지 형식으로 포맷팅"""

        if stats_type == "daily":
            msg = f"📅 **{stats['date']} 일별 활동 통계**\n\n"
            msg += f"🔢 **총 활동**: {stats['total_pages']}개\n\n"

            if stats["by_type"]:
                msg += "📊 **타입별 분포**:\n"
                for ptype, count in stats["by_type"].items():
                    msg += f"  • {ptype}: {count}개\n"
                msg += "\n"

            if stats["by_user"]:
                msg += "👥 **사용자별 분포**:\n"
                for user, count in stats["by_user"].items():
                    msg += f"  • User {user[-4:]}: {count}개\n"  # 마지막 4자리만 표시
                msg += "\n"

            if stats.get("pages"):
                msg += "📋 **상세 활동**:\n"
                for page in stats["pages"]:
                    msg += f"  • {page['time']} - {page['title']} ({page['type']})\n"

        elif stats_type == "weekly":
            msg = f"📊 **주별 활동 통계** ({stats['week_start']} ~ {stats['week_end']})\n\n"
            msg += f"🔢 **총 활동**: {stats['total_pages']}개\n\n"

            if stats["by_day"]:
                msg += "📅 **요일별 분포**:\n"
                for day, count in stats["by_day"].items():
                    msg += f"  • {day}: {count}개\n"
                msg += "\n"

            if stats["by_type"]:
                msg += "📊 **타입별 분포**:\n"
                for ptype, count in stats["by_type"].items():
                    msg += f"  • {ptype}: {count}개\n"

        elif stats_type == "monthly":
            msg = f"📅 **{stats['year']}년 {stats['month']}월 활동 통계**\n\n"
            msg += f"🔢 **총 활동**: {stats['total_pages']}개\n\n"

            if stats["by_type"]:
                msg += "📊 **타입별 분포**:\n"
                for ptype, count in stats["by_type"].items():
                    msg += f"  • {ptype}: {count}개\n"
                msg += "\n"

            if stats["by_user"]:
                msg += "👥 **사용자별 분포**:\n"
                for user, count in stats["by_user"].items():
                    msg += f"  • User {user[-4:]}: {count}개\n"

        elif stats_type == "user":
            msg = f"👤 **사용자 생산성 분석** (최근 {stats['period_days']}일)\n\n"
            msg += f"🔢 **총 활동**: {stats['total_pages']}개\n"
            msg += f"📈 **일평균**: {stats['avg_pages_per_day']}개\n\n"

            if stats["most_productive_day"]:
                msg += f"🌟 **가장 활발한 요일**: {stats['most_productive_day']}\n"
            if stats["most_productive_hour"]:
                msg += f"⏰ **가장 활발한 시간**: {stats['most_productive_hour']}시\n\n"

            if stats["by_type"]:
                msg += "📊 **타입별 분포**:\n"
                for ptype, count in stats["by_type"].items():
                    msg += f"  • {ptype}: {count}개\n"

        elif stats_type == "team":
            msg = f"👥 **팀 활동 비교** (최근 {stats['period_days']}일)\n\n"
            msg += f"🔢 **총 팀 활동**: {stats['total_team_pages']}개\n\n"

            if stats["members"]:
                msg += "👤 **멤버별 활동**:\n"
                # 활동 점수 기준으로 정렬
                sorted_members = sorted(
                    stats["members"].items(),
                    key=lambda x: x[1]["activity_score"],
                    reverse=True,
                )
                for user, data in sorted_members:
                    msg += f"  • User {user[-4:]}: {data['total_pages']}개 (점수: {data['activity_score']})\n"

        elif stats_type == "trends":
            msg = f"📈 **활동 트렌드** (최근 {stats['period_days']}일)\n\n"
            msg += f"🔢 **총 활동**: {stats['total_pages']}개\n"
            msg += f"📊 **일평균**: {stats['avg_daily_pages']}개\n"

            if stats["growth_rate"] != 0:
                trend_emoji = "📈" if stats["growth_rate"] > 0 else "📉"
                msg += f"{trend_emoji} **성장률**: {stats['growth_rate']:+.1f}%\n\n"

            if stats["busiest_day"]:
                msg += f"🔥 **가장 바쁜 날**: {stats['busiest_day']['date']} ({stats['busiest_day']['pages']}개)\n"
            if stats["quietest_day"]:
                msg += f"😴 **가장 조용한 날**: {stats['quietest_day']['date']} ({stats['quietest_day']['pages']}개)\n"

        elif stats_type == "task_completion":
            msg = f"✅ **Task 완료 통계** (최근 {stats['period_days']}일)\n\n"
            msg += f"🔢 **총 Task**: {stats['total_tasks']}개\n\n"

            if stats["by_status"]:
                msg += "📊 **상태별 분포**:\n"
                for status, count in stats["by_status"].items():
                    status_emoji = (
                        "✅"
                        if status == "Done"
                        else ("🔄" if status == "In progress" else "📋")
                    )
                    msg += f"  {status_emoji} {status}: {count}개\n"
                msg += "\n"

            if stats["by_user"]:
                msg += "👤 **사용자별 완료율**:\n"
                sorted_users = sorted(
                    stats["by_user"].items(),
                    key=lambda x: x[1]["completion_rate"],
                    reverse=True,
                )
                for user, data in sorted_users:
                    msg += f"  • User {user[-4:]}: {data['completed']}/{data['total']} ({data['completion_rate']}%)\n"
                msg += "\n"

            # 최근 완료된 Task들
            completed_tasks = [
                t for t in stats["tasks_details"] if t["status"] == "Done"
            ]
            if completed_tasks:
                msg += "🎉 **최근 완료된 Task**:\n"
                for task in completed_tasks[-3:]:  # 최근 3개만
                    msg += f"  ✅ {task['title']}\n"

        return msg

    # ===== 차트 생성 메서드들 =====

    @safe_execution("generate_stats_chart")
    async def generate_stats_chart(
        self, stats: Dict[str, Any], stats_type: str
    ) -> Optional[str]:
        """통계 데이터로 차트 이미지 생성"""
        try:
            if stats_type == "daily":
                chart_service = ChartGeneratorService()
                return await chart_service.generate_daily_stats_chart(stats)
            elif stats_type == "weekly":
                chart_service = ChartGeneratorService()
                return await chart_service.generate_weekly_stats_chart(stats)
            elif stats_type == "monthly":
                chart_service = ChartGeneratorService()
                return await chart_service.generate_monthly_stats_chart(stats)
            elif stats_type == "user":
                chart_service = ChartGeneratorService()
                return await chart_service.generate_user_productivity_chart(stats)
            elif stats_type == "team":
                chart_service = ChartGeneratorService()
                return await chart_service.generate_team_comparison_chart(stats)
            elif stats_type == "task_completion":
                chart_service = ChartGeneratorService()
                return await chart_service.generate_task_completion_chart(stats)
            elif stats_type == "trends":
                chart_service = ChartGeneratorService()
                return await chart_service.generate_trends_chart(stats)
            else:
                logger.warning(f"⚠️ 지원하지 않는 차트 타입: {stats_type}")
                return None

        except Exception as e:
            logger.error(f"❌ 차트 생성 실패 ({stats_type}): {e}")
            return None

    async def get_stats_with_chart(
        self, stats_method, *args, stats_type: str, **kwargs
    ) -> Dict[str, Any]:
        """통계 데이터와 차트 이미지를 함께 생성"""
        try:
            # 통계 데이터 생성
            stats = await stats_method(*args, **kwargs)

            # 차트 이미지 생성
            chart_path = await self.generate_stats_chart(stats, stats_type)

            # 텍스트 메시지 생성
            text_message = self.format_stats_message(stats, stats_type)

            return {
                "stats": stats,
                "chart_path": chart_path,
                "text_message": text_message,
                "has_chart": chart_path is not None,
            }

        except Exception as e:
            logger.error(f"❌ 통계+차트 생성 실패: {e}")
            return {
                "stats": {},
                "chart_path": None,
                "text_message": "❌ 통계 생성 중 오류가 발생했습니다.",
                "has_chart": False,
            }


# Global analytics service instance
analytics_service = SimpleStatsService()
