# --- START OF FILE popups/__init__.py ---

# MUDANÇA: EditCandidateWindow e UserManagementWindow foram removidos
from .task_management_window import TaskManagementWindow
from .global_tag_manager_window import GlobalTagManagerWindow
from .global_search_window import GlobalSearchWindow
from .birthday_windows import UpcomingBirthdaysWindow
from .dashboard_window import DashboardWindow
from .progress_windows import BackupProgressWindow, RestoreProgressWindow
from .info_windows import EditTagsWindow, ChangelogWindow
from .backup_options_window import BackupOptionsWindow
from .login_window import LoginWindow
# MUDANÇA: A importação de 'UserManagementWindow' foi removida daqui.
from .datepicker import DatePicker
from .app_params_window import AppParamsWindow

# MUDANÇA: EditCandidateWindow e UserManagementWindow removidos da lista __all__
__all__ = [
    "TaskManagementWindow", "GlobalTagManagerWindow",
    "GlobalSearchWindow", "UpcomingBirthdaysWindow",
    "DashboardWindow", "BackupProgressWindow", "RestoreProgressWindow",
    "EditTagsWindow", "ChangelogWindow", "BackupOptionsWindow",
    "LoginWindow", "DatePicker","AppParamsWindow"
]
# --- END OF FILE popups/__init__.py ---