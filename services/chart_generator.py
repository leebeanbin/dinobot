"""
차트 이미지 생성 서비스
- matplotlib와 seaborn을 사용해서 서버에서 차트 이미지 생성
- Discord로 이미지 파일 전송
"""

import os
import tempfile
import matplotlib

matplotlib.use("Agg")  # GUI 없는 환경에서 사용
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List

from core.logger import get_logger
from core.exceptions import safe_execution

logger = get_logger("services.chart_generator")

# 한글 폰트 설정 (시스템에 따라 다를 수 있음)
plt.rcParams["font.family"] = ["DejaVu Sans", "Liberation Sans", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

# 컬러 팔레트 설정
COLORS = {
    "primary": "#4F46E5",  # 보라색
    "success": "#10B981",  # 초록색
    "warning": "#F59E0B",  # 주황색
    "danger": "#EF4444",  # 빨간색
    "info": "#3B82F6",  # 파란색
    "secondary": "#6B7280",  # 회색
}


class ChartGeneratorService:
    """차트 이미지 생성 서비스"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"📊 차트 생성 서비스 초기화: {self.temp_dir}")

    def _setup_plot_style(self):
        """플롯 스타일 설정"""
        sns.set_style("whitegrid")
        plt.style.use("default")

    @safe_execution("generate_daily_stats_chart")
    async def generate_daily_stats_chart(self, stats: Dict[str, Any]) -> Optional[str]:
        """일별 통계 차트 생성"""
        try:
            self._setup_plot_style()

            by_type = stats.get("by_type", {})
            if not by_type:
                logger.warning("⚠️ 일별 통계 데이터가 비어있습니다")
                return None

            # 차트 생성 (더 큰 크기로)
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

            # 1. 타입별 파이 차트
            labels = list(by_type.keys())
            sizes = list(by_type.values())
            colors = [
                COLORS["primary"],
                COLORS["success"],
                COLORS["warning"],
                COLORS["danger"],
            ][: len(labels)]

            wedges, texts, autotexts = ax1.pie(
                sizes,
                labels=labels,
                autopct="%1.1f%%",
                colors=colors,
                startangle=90,
                explode=[0.05] * len(sizes),  # 파이 조각 분리
                shadow=True,  # 그림자 효과
                textprops={"fontsize": 12, "fontweight": "bold"},
            )
            # 파이 차트 제목과 설명
            total_activities = sum(sizes)
            ax1.set_title(
                f"Activity Distribution by Type\n{stats.get('date', 'Unknown')}\nTotal: {total_activities} activities",
                fontsize=16,
                fontweight="bold",
                pad=20,
            )

            # 범례 추가
            ax1.legend(
                wedges,
                [f"{label}: {size}" for label, size in zip(labels, sizes)],
                title="Activity Types",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
            )

            # 2. 시간별 막대 차트
            by_hour = stats.get("by_hour", {})
            if by_hour:
                hours = sorted(by_hour.keys())
                counts = [by_hour[h] for h in hours]

                bars = ax2.bar(hours, counts, color=COLORS["info"], alpha=0.7)

                # 막대 위에 값 표시
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + 0.1,
                        f"{count}",
                        ha="center",
                        va="bottom",
                        fontweight="bold",
                    )

                # 피크 시간 찾기
                max_count = max(counts)
                peak_hour = hours[counts.index(max_count)]

                ax2.set_title(
                    f"Activity Distribution by Hour\nPeak: {max_count} activities at {peak_hour}",
                    fontsize=16,
                    fontweight="bold",
                    pad=20,
                )
                ax2.set_xlabel("Hour of Day", fontsize=12, fontweight="bold")
                ax2.set_ylabel("Number of Activities", fontsize=12, fontweight="bold")
                ax2.set_xticks(hours)
                ax2.grid(True, alpha=0.3)

                # Y축 범위 조정
                ax2.set_ylim(0, max_count * 1.2)
            else:
                ax2.text(
                    0.5,
                    0.5,
                    "No hourly data",
                    ha="center",
                    va="center",
                    transform=ax2.transAxes,
                    fontsize=12,
                )
                ax2.set_title(
                    "Activity Distribution by Hour", fontsize=16, fontweight="bold"
                )

            # 전체 제목 추가
            fig.suptitle(
                f"Daily Activity Analysis - {stats.get('date', 'Unknown')}",
                fontsize=20,
                fontweight="bold",
                y=0.95,
            )

            plt.tight_layout()

            # 파일로 저장
            filename = (
                f"daily_stats_{stats.get('date', 'unknown').replace('-', '')}.png"
            )
            filepath = os.path.join(self.temp_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="white")
            plt.close()

            logger.info(f"✅ 일별 통계 차트 생성 완료: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ 일별 통계 차트 생성 실패: {e}")
            return None

    @safe_execution("generate_weekly_stats_chart")
    async def generate_weekly_stats_chart(self, stats: Dict[str, Any]) -> Optional[str]:
        """주별 통계 차트 생성"""
        try:
            self._setup_plot_style()

            by_day = stats.get("by_day", {})
            if not by_day:
                logger.warning("⚠️ 주별 통계 데이터가 비어있습니다")
                return None

            # 요일 순서 정렬
            days_order = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            days_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            # 데이터 준비
            day_counts = [by_day.get(day, 0) for day in days_order]

            # 차트 생성 (더 큰 크기로)
            fig, ax = plt.subplots(figsize=(18, 10))

            bars = ax.bar(
                days_short,
                day_counts,
                color=COLORS["primary"],
                alpha=0.8,
                edgecolor="white",
                linewidth=2,
            )

            # 막대 위에 값 표시
            for bar, count in zip(bars, day_counts):
                if count > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.1,
                        str(count),
                        ha="center",
                        va="bottom",
                        fontweight="bold",
                    )

            # 총 활동 수와 최고 활동일 계산
            total_activities = sum(day_counts)
            max_day_idx = day_counts.index(max(day_counts))
            busiest_day = days_short[max_day_idx]
            max_count = max(day_counts)

            ax.set_title(
                f"Weekly Activity Distribution\n{stats.get('week_start')} ~ {stats.get('week_end')}\nTotal: {total_activities} activities | Busiest: {busiest_day} ({max_count})",
                fontsize=16,
                fontweight="bold",
                pad=20,
            )
            ax.set_ylabel("Number of Activities", fontsize=12, fontweight="bold")
            ax.set_xlabel("Day of Week", fontsize=12, fontweight="bold")
            ax.grid(True, alpha=0.3, axis="y")

            # Y축 범위 조정
            if max_count > 0:
                ax.set_ylim(0, max_count * 1.2)

            plt.tight_layout()

            # 파일로 저장
            filename = f"weekly_stats_{stats.get('week_start', 'unknown').replace('-', '')}.png"
            filepath = os.path.join(self.temp_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="white")
            plt.close()

            logger.info(f"✅ 주별 통계 차트 생성 완료: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ 주별 통계 차트 생성 실패: {e}")
            return None

    @safe_execution("generate_monthly_stats_chart")
    async def generate_monthly_stats_chart(
        self, stats: Dict[str, Any]
    ) -> Optional[str]:
        """월별 통계 차트 생성"""
        try:
            self._setup_plot_style()

            by_type = stats.get("by_type", {})
            by_hour = stats.get("by_hour", {})

            if not by_type and not by_hour:
                logger.warning("⚠️ 월별 통계 데이터가 비어있습니다")
                return None

            # 차트 생성 (더 큰 크기로)
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 12))

            # 1. 타입별 파이 차트
            if by_type:
                labels = list(by_type.keys())
                sizes = list(by_type.values())
                colors = [
                    COLORS["primary"],
                    COLORS["success"],
                    COLORS["warning"],
                    COLORS["danger"],
                ][: len(labels)]

                wedges, texts, autotexts = ax1.pie(
                    sizes,
                    labels=labels,
                    autopct="%1.1f%%",
                    colors=colors,
                    startangle=90,
                    explode=[0.05] * len(sizes),  # 파이 조각 분리
                    shadow=True,  # 그림자 효과
                    textprops={"fontsize": 12, "fontweight": "bold"},
                )

                # 파이 차트 제목과 설명
                total_activities = sum(sizes)
                ax1.set_title(
                    f"Monthly Activity Distribution by Type\n{stats.get('year', 'Unknown')} Year {stats.get('month', 'Unknown')} Month\nTotal: {total_activities} activities",
                    fontsize=16,
                    fontweight="bold",
                    pad=20,
                )

                # 범례 추가
                ax1.legend(
                    wedges,
                    [f"{label}: {size}" for label, size in zip(labels, sizes)],
                    title="Activity Types",
                    loc="center left",
                    bbox_to_anchor=(1, 0, 0.5, 1),
                )
            else:
                ax1.text(
                    0.5,
                    0.5,
                    "No type data available",
                    ha="center",
                    va="center",
                    transform=ax1.transAxes,
                    fontsize=14,
                    fontweight="bold",
                )
                ax1.set_title(
                    "Activity Distribution by Type", fontsize=16, fontweight="bold"
                )

            # 2. 사용자별 생성 통계 막대 차트
            by_user = stats.get("by_user", {})
            if by_user:
                users = list(by_user.keys())
                counts = list(by_user.values())

                bars = ax2.bar(
                    users,
                    counts,
                    color=COLORS["success"],
                    alpha=0.8,
                    edgecolor="white",
                    linewidth=2,
                )

                # 막대 위에 값 표시
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + 0.1,
                        f"{count}",
                        ha="center",
                        va="bottom",
                        fontweight="bold",
                    )

                # 최고 생성자 찾기
                max_count = max(counts)
                top_user = users[counts.index(max_count)]

                ax2.set_title(
                    f"Monthly Activity Distribution by User\nTop Creator: {top_user} ({max_count} activities)",
                    fontsize=16,
                    fontweight="bold",
                    pad=20,
                )
                ax2.set_xlabel("Users", fontsize=12, fontweight="bold")
                ax2.set_ylabel("Number of Activities", fontsize=12, fontweight="bold")
                ax2.set_xticks(users)
                ax2.grid(True, alpha=0.3)

                # Y축 범위 조정
                ax2.set_ylim(0, max_count * 1.2)
            else:
                ax2.text(
                    0.5,
                    0.5,
                    "No user data available",
                    ha="center",
                    va="center",
                    transform=ax2.transAxes,
                    fontsize=14,
                    fontweight="bold",
                )
                ax2.set_title(
                    "Activity Distribution by User", fontsize=16, fontweight="bold"
                )

            # 전체 제목 추가
            fig.suptitle(
                f"Monthly Activity Analysis - {stats.get('year', 'Unknown')} Year {stats.get('month', 'Unknown')} Month",
                fontsize=20,
                fontweight="bold",
                y=0.95,
            )

            plt.tight_layout()

            # 파일로 저장
            filename = f"monthly_stats_{stats.get('year', 'unknown')}{stats.get('month', 'unknown'):02d}.png"
            filepath = os.path.join(self.temp_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="white")
            plt.close()

            logger.info(f"✅ 월별 통계 차트 생성 완료: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ 월별 통계 차트 생성 실패: {e}")
            return None

    @safe_execution("generate_user_productivity_chart")
    async def generate_user_productivity_chart(
        self, stats: Dict[str, Any]
    ) -> Optional[str]:
        """사용자 생산성 차트 생성"""
        try:
            self._setup_plot_style()

            by_hour = stats.get("by_hour", {})
            if not by_hour:
                logger.warning("⚠️ 사용자 생산성 데이터가 비어있습니다")
                return None

            # 24시간 데이터 준비
            hours = list(range(24))
            hour_counts = [by_hour.get(h, 0) for h in hours]

            # 차트 생성
            fig, ax = plt.subplots(figsize=(12, 6))

            ax.plot(
                hours,
                hour_counts,
                color=COLORS["success"],
                linewidth=3,
                marker="o",
                markersize=6,
            )
            ax.fill_between(hours, hour_counts, alpha=0.3, color=COLORS["success"])

            ax.set_title(
                f"👤 Hourly Activity Pattern (Last {stats.get('period_days', 'N/A')} days)",
                fontsize=16,
                fontweight="bold",
                pad=20,
            )
            ax.set_xlabel("Hour of Day")
            ax.set_ylabel("Activity Count")
            ax.set_xticks(range(0, 24, 2))
            ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)])
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            # 파일로 저장
            filename = f"user_productivity_{datetime.now().strftime('%Y%m%d')}.png"
            filepath = os.path.join(self.temp_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches="tight", facecolor="white")
            plt.close()

            logger.info(f"✅ 사용자 생산성 차트 생성 완료: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ 사용자 생산성 차트 생성 실패: {e}")
            return None

    # 간단한 기본 차트들만 구현 (나머지는 나중에 필요할 때 추가)

    async def generate_team_comparison_chart(
        self, stats: Dict[str, Any]
    ) -> Optional[str]:
        """간단한 팀 비교 차트"""
        # 향후 구현 예정
        return None

    async def generate_task_completion_chart(
        self, stats: Dict[str, Any]
    ) -> Optional[str]:
        """간단한 Task 완료 차트"""
        # 향후 구현 예정
        return None

    async def generate_trends_chart(self, stats: Dict[str, Any]) -> Optional[str]:
        """간단한 트렌드 차트"""
        # 향후 구현 예정
        return None

    def cleanup_temp_files(self):
        """임시 파일들 정리"""
        try:
            import shutil

            shutil.rmtree(self.temp_dir)
            logger.info(f"🧹 임시 파일 정리 완료: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ 임시 파일 정리 실패: {e}")


# Global chart generator instance
chart_generator = ChartGeneratorService()
