# Скрипт для загрузки проекта на GitHub
# Использование: .\upload_to_github.ps1

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     Загрузка BotRabota на GitHub                        ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

$REPO_NAME = "naumrabota"
$GITHUB_USERNAME = Read-Host "Введите ваш GitHub username"

if ([string]::IsNullOrWhiteSpace($GITHUB_USERNAME)) {
    Write-Host "❌ Username не может быть пустым!" -ForegroundColor Red
    exit 1
}

$REPO_URL = "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

Write-Host "Репозиторий: $REPO_URL" -ForegroundColor Cyan
Write-Host ""

# Проверка что git установлен
$gitPath = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitPath) {
    Write-Host "❌ Git не установлен!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Установите Git: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# Проверка что мы в git репозитории
if (-not (Test-Path ".git")) {
    Write-Host "❌ Это не git репозиторий!" -ForegroundColor Red
    Write-Host "Инициализация git..." -ForegroundColor Yellow
    git init
    git config user.email "vnaum0134@gmail.com"
    git config user.name "Naum"
    git add .
    git commit -m "Initial commit: BotRabota Telegram bot"
}

# Проверка remote
$remoteExists = git remote get-url origin -ErrorAction SilentlyContinue
if ($remoteExists) {
    Write-Host "⚠️  Remote 'origin' уже настроен: $remoteExists" -ForegroundColor Yellow
    $change = Read-Host "Изменить на $REPO_URL? (y/n)"
    if ($change -eq "y" -or $change -eq "Y") {
        git remote set-url origin $REPO_URL
        Write-Host "✅ Remote обновлен" -ForegroundColor Green
    }
} else {
    Write-Host "Добавление remote репозитория..." -ForegroundColor Cyan
    git remote add origin $REPO_URL
    Write-Host "✅ Remote добавлен" -ForegroundColor Green
}

# Переименование ветки в main (если нужно)
Write-Host ""
Write-Host "Переименование ветки в main..." -ForegroundColor Cyan
git branch -M main 2>$null
Write-Host "✅ Ветка переименована" -ForegroundColor Green

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  ВАЖНО: Для загрузки на GitHub нужен Personal Access Token!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Как получить токен:" -ForegroundColor Cyan
Write-Host "1. Откройте: https://github.com/settings/tokens" -ForegroundColor White
Write-Host "2. Generate new token (classic)" -ForegroundColor White
Write-Host "3. Выберите scope: repo" -ForegroundColor White
Write-Host "4. Скопируйте токен" -ForegroundColor White
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

$proceed = Read-Host "Готовы загрузить проект? (y/n)"
if ($proceed -ne "y" -and $proceed -ne "Y") {
    Write-Host "Отменено" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Загрузка проекта на GitHub..." -ForegroundColor Cyan
Write-Host ""

# Push на GitHub
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Проект успешно загружен на GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Откройте: https://github.com/$GITHUB_USERNAME/$REPO_NAME" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Ошибка при загрузке!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "1. Репозиторий не создан на GitHub" -ForegroundColor White
    Write-Host "2. Неверный username или токен" -ForegroundColor White
    Write-Host "3. Проблемы с подключением" -ForegroundColor White
    Write-Host ""
    Write-Host "Создайте репозиторий: https://github.com/new" -ForegroundColor Cyan
    Write-Host "Название: $REPO_NAME" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Нажмите Enter для выхода..."
Read-Host
