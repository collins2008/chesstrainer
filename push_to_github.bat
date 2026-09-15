@echo off
echo ========================================================
echo Pushing AI Chess Coach to GitHub
echo ========================================================

:: Check if GitHub CLI is installed
where gh >nul 2>nul
if %errorlevel% neq 0 (
    echo GitHub CLI (gh) is not installed or not in PATH.
    echo Please download it from https://cli.github.com/ and restart your terminal.
    pause
    exit /b
)

:: Check if authenticated
gh auth status >nul 2>nul
if %errorlevel% neq 0 (
    echo You are not logged into GitHub CLI.
    echo Running 'gh auth login' - please follow the prompts in your browser!
    gh auth login
)

echo Creating a new private repository on your GitHub account...
gh repo create ai-chess-coach-pwa --private --source=. --remote=origin --push

if %errorlevel% equ 0 (
    echo.
    echo Success! The repository has been created and the code has been pushed!
    echo Check your GitHub account for the "ai-chess-coach-pwa" repository.
) else (
    echo.
    echo Hmm, something went wrong. Make sure you authenticated correctly.
)

pause
