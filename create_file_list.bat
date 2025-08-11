@echo off
setlocal

set "OUT_FILE=project_contents.txt"

if exist %OUT_FILE% del %OUT_FILE%

for /r %%F in (*.py *.yml *.txt *.md Dockerfile) do (
    if /i not "%%~dpF"=="%CD%\.git\" (
        echo # %%~F>> %OUT_FILE%
        type "%%F">> %OUT_FILE%
        echo.>> %OUT_FILE%
    )
)

endlocal
