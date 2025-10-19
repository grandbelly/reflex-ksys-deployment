"""
Alarms State - Unified rule-based alarm management
- Uses AlarmService with proper connection pool
- Direct rx.State inheritance (no BaseState)
- Background events for async operations
"""
import reflex as rx
from typing import List, Dict, Any
from reflex.utils import console

from ksys_app.db_orm import get_async_session
from ksys_app.services.alarm_service import AlarmService


class AlarmsState(rx.State):
    """Unified alarm state for RULE_BASE alarms"""

    # Data storage
    alarms: List[Dict] = []

    # Statistics - individual fields for Reflex reactivity
    stat_total: int = 0
    stat_critical: int = 0
    stat_warning: int = 0
    stat_info: int = 0
    stat_unacknowledged: int = 0
    
    # ISA-18.2 Priority Statistics
    stat_priority_1_low: int = 0        # Priority 1: Advisory (Level 1-2)
    stat_priority_2_medium: int = 0     # Priority 2: Caution (Level 3)
    stat_priority_3_high: int = 0       # Priority 3: Warning (Level 4)
    stat_priority_4_critical: int = 0   # Priority 4: Emergency (Level 5)

    # UI control
    loading: bool = False
    error_message: str = ""
    last_update: str = ""
    view_mode: str = "active"  # "active" or "history"

    # Filters
    selected_hours: int = 24  # 24 hours default (show recent ISA-18.2 alarms)
    show_acknowledged: bool = False  # ISA-18.2 Standard: Real-time view shows unacknowledged only
    search_query: str = ""
    severity_filter: str = "all"  # all, CRITICAL, WARNING, INFO
    status_filter: str = "all"  # all, UNACKNOWLEDGED, ACKNOWLEDGED

    # Pagination
    page: int = 1
    page_size: int = 20
    total_count: int = 0

    # Selection
    selected_alarms: List[str] = []  # List of event_ids

    # Sensor-level status (like AlarmRTState and Dashboard)
    all_sensors: List[Dict] = []
    total_sensors_count: int = 0
    normal_sensors_count: int = 0
    warning_sensors_count: int = 0
    critical_sensors_count: int = 0

    # Computed Properties
    # =========================================================================

    @rx.var(cache=True)
    def filtered_alarms(self) -> List[Dict]:
        """Filter alarms based on search, severity, status"""
        result = self.alarms

        # Search filter
        if self.search_query:
            query = self.search_query.lower()
            result = [
                a for a in result
                if query in a.get("message", "").lower()
                or query in a.get("tag_name", "").lower()
                or query in a.get("cause", "").lower()
            ]

        # Severity filter
        if self.severity_filter != "all":
            severity_map = {
                "CRITICAL": 5,
                "WARNING": 3,
                "INFO": 2,
            }
            level = severity_map.get(self.severity_filter.upper())
            if level:
                result = [a for a in result if a.get("level") == level]

        # Status filter
        if self.status_filter == "UNACKNOWLEDGED":
            result = [a for a in result if not a.get("acknowledged", False)]
        elif self.status_filter == "ACKNOWLEDGED":
            result = [a for a in result if a.get("acknowledged", False)]

        # Legacy show_acknowledged filter
        if not self.show_acknowledged:
            result = [a for a in result if not a.get("acknowledged", False)]

        return result

    @rx.var
    def paginated_alarms(self) -> List[Dict]:
        """Get alarms for current page"""
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return self.filtered_alarms[start:end]

    @rx.var
    def active_alarms(self) -> List[Dict]:
        """Get active alarms for current page - same as paginated_alarms for now"""
        # TODO: Later implement DISTINCT ON (tag_name) for sensor-level status
        return self.paginated_alarms

    @rx.var
    def history_alarms(self) -> List[Dict]:
        """Get history alarms for current page - same as paginated_alarms"""
        return self.paginated_alarms

    @rx.var
    def active_count(self) -> int:
        """Count of active alarms - same as filtered_count for now"""
        return self.filtered_count

    @rx.var
    def history_count(self) -> int:
        """Count of history alarms - same as filtered_count"""
        return self.filtered_count

    @rx.var
    def active_total_pages(self) -> int:
        """Total pages for active alarms - same as total_pages"""
        return self.total_pages

    @rx.var
    def history_total_pages(self) -> int:
        """Total pages for history alarms - same as total_pages"""
        return self.total_pages

    @rx.var
    def total_pages(self) -> int:
        """Total number of pages"""
        total = len(self.filtered_alarms)
        return max(1, (total + self.page_size - 1) // self.page_size)

    @rx.var
    def filtered_count(self) -> int:
        """Number of filtered alarms"""
        return len(self.filtered_alarms)

    @rx.var
    def selected_count(self) -> int:
        """Number of selected alarms"""
        return len(self.selected_alarms)

    # Computed properties for reactive stats (alternative approach)
    @rx.var
    def total_display(self) -> int:
        """Total count for display"""
        return self.stat_total

    @rx.var
    def critical_display(self) -> int:
        """Critical count for display"""
        return self.stat_critical

    @rx.var
    def warning_display(self) -> int:
        """Warning count for display"""
        return self.stat_warning

    @rx.var
    def info_display(self) -> int:
        """Info count for display"""
        return self.stat_info

    @rx.var
    def unacked_display(self) -> int:
        """Unacknowledged count for display"""
        return self.stat_unacknowledged

    # Event Handlers
    # =========================================================================

    @rx.event(background=True)
    async def initialize(self):
        """Initialize - load data on mount"""
        console.info("AlarmsState.initialize() called")

        async with self:
            self.loading = True
        yield  # Update UI with loading state

        try:
            # Load sensor status first (yield to call background event)
            yield AlarmsState.load_sensor_status

            # Then load alarm data
            await self._fetch_data()
            # _fetch_data already does async with self and updates state
            yield  # Update UI with new data

        except Exception as e:
            console.error(f"Initialize failed: {e}")
            async with self:
                self.error_message = str(e)
            yield
        finally:
            async with self:
                self.loading = False
            yield  # Final UI update

    async def _fetch_data(self):
        """Internal data fetch without yield (for initialize)"""
        selected_hours = self.selected_hours

        console.info(f"Fetching alarms for last {selected_hours} hours (view_mode: {self.view_mode})")

        try:
            async with get_async_session() as session:
                service = AlarmService(session)

                # Fetch alarms based on view_mode
                if self.view_mode == "active":
                    # Active view: Sensor-level status (DISTINCT ON tag_name)
                    result = await service.get_active_sensor_alarms(
                        hours=selected_hours,
                        page=self.page,
                        page_size=self.page_size
                    )
                    console.info(f"📊 Active view: Loaded {result.get('total', 0)} sensors")
                else:
                    # History view: All alarms chronologically
                    result = await service.get_rule_based_alarms(
                        hours=selected_hours,
                        page=self.page,
                        page_size=self.page_size
                    )
                    console.info(f"📜 History view: Loaded {result.get('total', 0)} alarms")

                # Get statistics (same for both views)
                stats = await service.get_alarm_statistics(hours=selected_hours)

            # Extract alarms list from result
            if isinstance(result, dict) and 'alarms' in result:
                alarms = result['alarms']
            else:
                alarms = result if isinstance(result, list) else []

            async with self:
                self.alarms = alarms
                # Update individual stat fields
                # ISA-18.2: Merge Level 4 (ERROR) + Level 5 (CRITICAL) as "위험 알람"
                self.stat_total = stats.get("total", 0)
                self.stat_critical = stats.get("critical", 0) + stats.get("error", 0)  # L5 + L4
                self.stat_warning = stats.get("warning", 0)  # L3
                self.stat_info = stats.get("info", 0) + stats.get("caution", 0)  # L2 + L1
                self.stat_unacknowledged = stats.get("unacknowledged", 0)
                
                # ISA-18.2 priorities
                self.stat_priority_1_low = stats.get("priority_1_low", 0)
                self.stat_priority_2_medium = stats.get("priority_2_medium", 0)
                self.stat_priority_3_high = stats.get("priority_3_high", 0)
                self.stat_priority_4_critical = stats.get("priority_4_critical", 0)
                self.last_update = "Just now"
                self.loading = False

                # Log inside async with self to ensure values are correct
                console.info(f"Loaded {len(self.alarms)} alarms, {self.stat_critical} critical (L5={stats.get('critical', 0)} + L4={stats.get('error', 0)})")
                console.info(f"⚡ Stats fields updated: total={self.stat_total}, critical={self.stat_critical}, warning={self.stat_warning}, unacked={self.stat_unacknowledged}")

        except Exception as e:
            console.error(f"Fetch data failed: {e}")
            async with self:
                self.error_message = str(e)
                self.loading = False

    @rx.event(background=True)
    async def load_sensor_status(self):
        """Load all sensor status (like Dashboard and /alarms_rt)"""
        try:
            from ..db import q

            query = """
                SELECT
                    l.tag_name,
                    ROUND(l.value::numeric, 2) as value,
                    TO_CHAR(l.ts AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI:SS') as timestamp,
                    COALESCE(t.description, t.meta->>'description', l.tag_name) as description,
                    COALESCE(t.unit, t.meta->>'unit', '') as unit,
                    COALESCE(q.min_val, 0.0) as min_val,
                    COALESCE(q.max_val, 100.0) as max_val,
                    COALESCE(q.warning_low, 20.0) as warning_low,
                    COALESCE(q.warning_high, 80.0) as warning_high,
                    CASE
                        WHEN l.value IS NULL OR q.min_val IS NULL THEN 'NORMAL'
                        WHEN l.value < q.min_val OR l.value > q.max_val THEN 'CRITICAL'
                        WHEN l.value < q.warning_low OR l.value > q.warning_high THEN 'WARNING'
                        ELSE 'NORMAL'
                    END as status
                FROM influx_latest l
                LEFT JOIN influx_qc_rule q ON l.tag_name = q.tag_name
                LEFT JOIN influx_tag t ON l.tag_name = t.tag_name
                WHERE l.value IS NOT NULL
                ORDER BY l.tag_name
            """

            rows = await q(query, ())

            all_sensors = []
            normal_count = 0
            warning_count = 0
            critical_count = 0

            for row in rows:
                sensor_data = {
                    "tag_name": row["tag_name"],
                    "description": row["description"],
                    "value": round(float(row["value"]), 2) if row["value"] is not None else 0.0,
                    "unit": row["unit"],
                    "timestamp": row["timestamp"],
                    "status": row["status"],
                    "min_val": round(float(row["min_val"]), 2),
                    "max_val": round(float(row["max_val"]), 2),
                    "warning_low": round(float(row["warning_low"]), 2),
                    "warning_high": round(float(row["warning_high"]), 2),
                }
                all_sensors.append(sensor_data)

                if sensor_data["status"] == "CRITICAL":
                    critical_count += 1
                elif sensor_data["status"] == "WARNING":
                    warning_count += 1
                else:
                    normal_count += 1

            async with self:
                self.all_sensors = all_sensors
                self.total_sensors_count = len(all_sensors)
                self.normal_sensors_count = normal_count
                self.warning_sensors_count = warning_count
                self.critical_sensors_count = critical_count

            console.info(f"Loaded {len(all_sensors)} sensors: {normal_count} normal, {warning_count} warning, {critical_count} critical")

        except Exception as e:
            console.error(f"Error loading sensor status: {e}")
            async with self:
                self.all_sensors = []
                self.total_sensors_count = 0
                self.normal_sensors_count = 0
                self.warning_sensors_count = 0
                self.critical_sensors_count = 0


    @rx.event(background=True)
    async def refresh_data(self):
        """Refresh alarm data (with yield for UI updates)"""
        console.info("Refreshing alarm data")

        async with self:
            self.loading = True
        yield

        try:
            await self._fetch_data()
            # _fetch_data already does async with self
            yield  # Update UI

        except Exception as e:
            console.error(f"Refresh failed: {e}")
            async with self:
                self.error_message = str(e)
                self.loading = False
            yield

    @rx.event(background=True)
    async def set_hours_filter(self, hours):
        """Change hour filter and refresh"""
        # Handle both string and list from segmented_control
        if isinstance(hours, list):
            hours_int = int(hours[0]) if hours else 24
        else:
            hours_int = int(hours) if hours else 24

        async with self:
            self.selected_hours = hours_int

        return AlarmsState.refresh_data

    @rx.event
    def toggle_show_acknowledged(self):
        """Toggle show acknowledged alarms"""
        self.show_acknowledged = not self.show_acknowledged

    # Search & Filter Event Handlers
    # =========================================================================

    @rx.event
    def set_search_query(self, query: str):
        """Set search query and reset to page 1"""
        self.search_query = query
        self.page = 1

    @rx.event
    def set_severity_filter(self, severity: str):
        """Set severity filter"""
        self.severity_filter = severity
        self.page = 1

    @rx.event
    def set_status_filter(self, status: str):
        """Set status filter"""
        self.status_filter = status
        self.page = 1

    @rx.event(background=True)
    async def set_view_mode(self, mode: str):
        """Switch between active and history view"""
        async with self:
            self.view_mode = mode
            self.page = 1  # Reset to first page

        # Refresh data with new view_mode
        return AlarmsState.refresh_data

    # Pagination Event Handlers
    # =========================================================================

    @rx.event
    def set_page(self, page: int):
        """Set current page"""
        self.page = max(1, min(page, self.total_pages))

    @rx.event
    def next_page(self):
        """Go to next page"""
        if self.page < self.total_pages:
            self.page += 1

    @rx.event
    def prev_page(self):
        """Go to previous page"""
        if self.page > 1:
            self.page -= 1

    # Selection Event Handlers
    # =========================================================================

    @rx.event
    def toggle_alarm_selection(self, event_id: str):
        """Toggle alarm selection"""
        if event_id in self.selected_alarms:
            self.selected_alarms.remove(event_id)
        else:
            self.selected_alarms.append(event_id)

    @rx.event
    def select_all_visible(self):
        """Select all alarms on current page"""
        for alarm in self.paginated_alarms:
            event_id = alarm.get("event_id")
            if event_id and event_id not in self.selected_alarms:
                self.selected_alarms.append(event_id)

    @rx.event
    def clear_selection(self):
        """Clear all selections"""
        self.selected_alarms = []

    @rx.event(background=True)
    async def acknowledge_selected(self):
        """Acknowledge all selected alarms"""
        if not self.selected_alarms:
            return

        console.info(f"Acknowledging {len(self.selected_alarms)} selected alarms")

        try:
            async with get_async_session() as session:
                service = AlarmService(session)

                for event_id in self.selected_alarms:
                    await service.acknowledge_alarm(event_id, "user")

            # Refresh data
            await self.refresh_data()

            # Clear selection
            async with self:
                self.selected_alarms = []
                yield

        except Exception as e:
            console.error(f"Acknowledge selected failed: {e}")
            async with self:
                self.error_message = str(e)

    @rx.event(background=True)
    async def acknowledge_alarm(self, event_id: str):
        """Acknowledge an alarm"""
        console.info(f"Acknowledging alarm: {event_id}")

        try:
            async with get_async_session() as session:
                service = AlarmService(session)
                success = await service.acknowledge_alarm(event_id, "user")

            if success:
                # Update local state
                async with self:
                    for alarm in self.alarms:
                        if alarm.get("event_id") == event_id:
                            alarm["acknowledged"] = True
                            alarm["acknowledged_by"] = "user"
                            break
                    yield  # Update UI

                console.info(f"Successfully acknowledged alarm {event_id}")
            else:
                console.error(f"Failed to acknowledge alarm {event_id}")

        except Exception as e:
            console.error(f"Acknowledge alarm failed: {e}")
            async with self:
                self.error_message = str(e)