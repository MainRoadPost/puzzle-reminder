import asyncio
import os
import sys
import tempfile
from getpass import getuser
import dotenv
from datetime import datetime, timedelta
from puzzle import Client
from puzzle.input_types import UserBy, UserWithoutDomain

# Platform-specific imports
if sys.platform == "win32":
    import subprocess
else:
    import notify2
    import fcntl


def get_desktop_manager():
    # Try to get the desktop environment from environment variables
    desktop_manager = os.environ.get("XDG_CURRENT_DESKTOP")
    if desktop_manager:
        return desktop_manager

    desktop_manager = os.environ.get("DESKTOP_SESSION")
    if desktop_manager:
        return desktop_manager

    # If the desktop manager could not be determined
    return "Unknown"


def get_weekday_by_date(date_str):
    # Parse the date string to a datetime object
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    # Get the weekday number
    weekday_num = date_obj.weekday()
    return weekday_num


def show_notification(title, message):
    try:
        if sys.platform == "win32":
            # Windows notification using PowerShell
            # Escape quotes in the message for PowerShell
            ps_title = title.replace('"', '\\"')
            ps_message = message.replace('"', '\\"').replace("\n", " ")
            ps_command = f'''
$notificationTitle = "{ps_title}"
$notificationMessage = "{ps_message}"
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

$APP_ID = 'PuzzleReminder'
$template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">$notificationTitle</text>
            <text id="2">$notificationMessage</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
'''
            subprocess.run(["powershell", "-Command", ps_command], capture_output=True)
        else:
            # Linux notification using notify2
            notify2.init("Puzzle")
            n = notify2.Notification(title, message, "puzzle.png")
            n.set_urgency(notify2.URGENCY_CRITICAL)
            n.set_timeout(10000)
            n.show()
    except Exception as e:
        print(f"Notification error: {e}")
        pass


def days_str(n):
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    elif n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
        return "дня"
    else:
        return "дней"


def hours_str(n):
    if n % 10 == 1 and n % 100 != 11:
        return "час"
    elif n % 10 in [2, 3, 4] and n % 100 not in [12, 13, 14]:
        return "часа"
    else:
        return "часов"


async def check_reports():
    username = os.environ.get("PUZZLE_USERNAME", getuser())
    reports = {}
    async with Client(os.environ.get("PUZZLE_API", "")) as client:
        try:
            result = await client.user_summary(
                user_by=UserBy(withoutDomain=UserWithoutDomain(login=username))
            )
            reports = {rec.date: (rec.hours, rec.ack) for rec in result.user_summary}
        except Exception as e:
            print(e)

    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now().replace(day=1)

    current_date = start_date
    _reports = {}

    # Fill in the missing days
    while current_date >= end_date:
        current_date_str = current_date.strftime("%Y-%m-%d")
        if current_date_str not in reports:
            _reports[current_date_str] = [0, True]
        else:
            _reports[current_date_str] = reports[current_date_str]
        current_date -= timedelta(days=1)

    # Calculate total reported hours
    reported_hours = 0
    total_hours = 0
    days = 0
    days_info = ""
    for date in sorted(_reports):
        hours, confirmed = _reports[date]
        if confirmed:
            reported_hours += hours
        if get_weekday_by_date(date) in range(5):
            total_hours += 8
            if hours == 0:
                days_info += f"{date}: нет отчета\n"
                days += 1
            elif hours < 8 and confirmed:
                days_info += f"{date}: отчет меньше 8 часов\n"
                days += 1
            elif hours < 8 and not confirmed:
                days_info += f"{date}: меньше 8 часов, отчет не подтвержден\n"
                days += 1
            elif not confirmed:
                days_info += f"{date}: отчет не подтвержден\n"
                days += 1

    if reported_hours < total_hours:
        reports_link = os.environ.get("PUZZLE_API", "").replace("/api/graphql", "/reports")
        message = f'{username}\n\n с {end_date.strftime("%Y-%m-%d")} по {start_date.strftime("%Y-%m-%d")} не хватает {total_hours - reported_hours} {hours_str(total_hours - reported_hours)}\n<a href="{reports_link}">Puzzle reports</a>\n'
        if days > 0:
            message += days_info
        show_notification("Незаполненные отчеты в Puzzle", message)


async def run():
    try:
        # use lock file to prevent multiple messages
        lock_file = os.path.join(tempfile.gettempdir(), "pzl_reports.lock")
        if sys.platform == "win32":
            try:
                with open(lock_file, "x") as f:
                    try:
                        await check_reports()
                    finally:
                        pass
            except FileExistsError:
                sys.exit()
            finally:
                # Clean up lock file
                try:
                    os.remove(lock_file)
                except FileNotFoundError:
                    pass
        else:
            with open(lock_file, "w") as f:
                fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    await check_reports()
                finally:
                    fcntl.lockf(f, fcntl.LOCK_UN)
    except (IOError, OSError):
        sys.exit()


if __name__ == "__main__":
    dotenv.load_dotenv()
    asyncio.run(run())
