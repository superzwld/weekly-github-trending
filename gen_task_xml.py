#!/usr/bin/env python3
"""Generate Windows Task Scheduler XML with proper UTF-16LE encoding."""

import os

xml = (
    '<?xml version="1.0" encoding="UTF-16"?>\n'
    '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
    '  <RegistrationInfo>\n'
    '    <Date>2026-04-30T17:00:00</Date>\n'
    '    <Author>Miao</Author>\n'
    '    <Description>GitHub Weekly Trending Reporter - runs every Monday 8AM via WSL. '
    'Missed schedules run immediately after next boot.</Description>\n'
    '    <URI>\\GitHubWeeklyReport</URI>\n'
    '  </RegistrationInfo>\n'
    '  <Triggers>\n'
    '    <CalendarTrigger>\n'
    '      <StartBoundary>2026-05-04T08:00:00</StartBoundary>\n'
    '      <Enabled>true</Enabled>\n'
    '      <ScheduleByWeek>\n'
    '        <DaysOfWeek>\n'
    '          <Monday />\n'
    '        </DaysOfWeek>\n'
    '        <WeeksInterval>1</WeeksInterval>\n'
    '      </ScheduleByWeek>\n'
    '    </CalendarTrigger>\n'
    '  </Triggers>\n'
    '  <Settings>\n'
    '    <AllowStartIfOnBatteries>true</AllowStartIfOnBatteries>\n'
    '    <DontStopIfGoingOnBatteries>true</DontStopIfGoingOnBatteries>\n'
    '    <StartWhenAvailable>true</StartWhenAvailable>\n'
    '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
    '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
    '    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n'
    '    <AllowHardTerminate>true</AllowHardTerminate>\n'
    '    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n'
    '    <Enabled>true</Enabled>\n'
    '    <Hidden>false</Hidden>\n'
    '    <RunOnlyIfIdle>false</RunOnlyIfIdle>\n'
    '    <WakeToRun>false</WakeToRun>\n'
    '    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>\n'
    '    <DeleteExpiredTaskAfter>PT0S</DeleteExpiredTaskAfter>\n'
    '  </Settings>\n'
    '  <Actions Context="Author">\n'
    '    <Exec>\n'
    '      <Command>wsl.exe</Command>\n'
    '      <Arguments>-- bash /home/laomeo/weekly_github/run.sh</Arguments>\n'
    '    </Exec>\n'
    '  </Actions>\n'
    '  <Principals>\n'
    '    <Principal id="Author">\n'
    '      <UserId>MIAO\\Miao</UserId>\n'
    '      <LogonType>InteractiveToken</LogonType>\n'
    '      <RunLevel>LeastPrivilege</RunLevel>\n'
    '    </Principal>\n'
    '  </Principals>\n'
    '</Task>\n'
)

wsl_path = "/mnt/c/Users/Miao/Documents/github_weekly_task.xml"

with open(wsl_path, "w", encoding="utf-16-le") as f:
    f.write(xml)

print(f"Written {os.path.getsize(wsl_path)} bytes to {wsl_path}")
print("Task XML ready for import.")
