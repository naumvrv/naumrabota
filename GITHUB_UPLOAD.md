# Загрузка проекта на GitHub

## Шаг 1: Создайте репозиторий на GitHub

1. Откройте https://github.com/new
2. **Repository name:** `naumrabota`
3. **Description:** `Telegram bot for job search in Russia`
4. Выберите **Public** или **Private**
5. **НЕ** добавляйте README, .gitignore или лицензию (у нас уже есть)
6. Нажмите **Create repository**

## Шаг 2: Загрузите проект

### Вариант A: Через командную строку (PowerShell)

Выполните эти команды в PowerShell:

```powershell
# Добавьте remote репозиторий (замените YOUR_USERNAME на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/naumrabota.git

# Переименуйте ветку в main (если нужно)
git branch -M main

# Загрузите проект
git push -u origin main
```

Вас попросят ввести логин и пароль GitHub. Используйте:
- **Username:** ваш GitHub username
- **Password:** Personal Access Token (не обычный пароль!)

### Как получить Personal Access Token:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Выберите scope: `repo` (полный доступ к репозиториям)
4. Скопируйте токен (он показывается только один раз!)

### Вариант B: Через GitHub Desktop

1. Скачайте GitHub Desktop: https://desktop.github.com/
2. File → Add Local Repository
3. Выберите папку `C:\Users\Ruman\Desktop\BotRabota`
4. Publish repository → выберите `naumrabota`
5. Нажмите Publish

### Вариант C: Используйте готовый скрипт

Откройте `upload_to_github.ps1` и замените `YOUR_USERNAME` на ваш GitHub username, затем запустите:

```powershell
.\upload_to_github.ps1
```

## Шаг 3: Проверка

Откройте https://github.com/YOUR_USERNAME/naumrabota

Вы должны увидеть все файлы проекта!

## Обновление проекта на GitHub

После изменений в проекте:

```powershell
git add .
git commit -m "Описание изменений"
git push
```

## Полезные команды

```powershell
# Проверить статус
git status

# Посмотреть историю коммитов
git log

# Посмотреть remote репозитории
git remote -v

# Изменить remote URL (если нужно)
git remote set-url origin https://github.com/YOUR_USERNAME/naumrabota.git
```
