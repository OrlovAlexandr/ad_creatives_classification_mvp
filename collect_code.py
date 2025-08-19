import os
import sys
from datetime import datetime
from pathlib import Path

def collect_code_to_file(root_dir, output_filename=None, exclude_dirs=None, exclude_files=None, allowed_extensions=None):
    """
    Собирает код из всех файлов в указанной директории (рекурсивно),
    исключая указанные папки и файлы, и сохраняет в один текстовый файл.

    :param root_dir: Корневая директория проекта (строка или Path)
    :param output_filename: Имя выходного файла (без расширения). Если None — будет использовано имя проекта.
    :param exclude_dirs: Список имён директорий, которые нужно исключить (например, ['venv', 'dataset'])
    :param exclude_files: Список имён файлов, которые нужно исключить (например, ['requirements.txt'])
    :param allowed_extensions: Список разрешённых расширений (например, ['.py', '.txt', '.dockerfile']). Если None — все текстовые.
    """
    root_path = Path(root_dir).resolve()
    project_name = root_path.name

    # Настройки по умолчанию
    exclude_dirs = set(exclude_dirs or [])
    exclude_files = set(exclude_files or [])
    allowed_extensions = set(allowed_extensions or None)  # None означает "все"

    # Расширения, которые явно не бинарные и можно читать как текст
    default_text_extensions = {
        '.py', '.txt', '.md', '.json', '.yaml', '.yml', '.toml',
        '.ini', '.cfg', '.env', '.dockerfile', 'dockerfile',
        '.sh', '.bash', '.zsh', '.html', '.css', '.js', '.ts',
        '.xml', '.csv', '.sql'
    }

    # Если не заданы разрешённые расширения, используем стандартные
    if allowed_extensions is None:
        allowed_extensions = default_text_extensions

    # Определяем имя выходного файла
    timestamp = datetime.now().strftime("%m%d_%H%M")
    output_filename = output_filename or f"{project_name}_{timestamp}"
    output_path = root_path / f"{output_filename}.txt"

    # Собираем все файлы
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for file_path in root_path.rglob('*'):
            # Пропускаем, если это директория
            if file_path.is_dir():
                continue

            # Пропускаем, если путь содержит исключённую директорию
            if any(part in exclude_dirs for part in file_path.parts):
                continue

            # Пропускаем исключённые файлы по имени
            if file_path.name in exclude_files:
                continue

            # Пропускаем скрытые файлы (начинающиеся с .)
            if file_path.name.startswith('.') and file_path.name not in ['.dockerfile']:  # можно адаптировать
                continue

            # Проверяем расширение
            ext = file_path.suffix.lower()
            # Обработка файлов без расширения, например Dockerfile
            if ext == '' and file_path.name.lower() != 'dockerfile':
                continue
            if ext not in allowed_extensions and file_path.name.lower() not in ['dockerfile']:
                continue

            try:
                # Попробуем прочитать как текст
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Относительный путь
                rel_path = file_path.relative_to(root_path)

                # Записываем в файл
                outfile.write(f"### {rel_path}\n\n")
                outfile.write(f"{content}\n\n")
                print(f"Добавлен: {rel_path}")

            except (UnicodeDecodeError, PermissionError) as e:
                print(f"Пропущен (ошибка чтения): {file_path} — {e}")
                continue

    print(f"\nСборка завершена. Результат сохранён в: {output_path}")


# Пример использования
if __name__ == "__main__":
    # Текущая директория как корень проекта
    current_dir = Path(__file__).parent

    collect_code_to_file(
        root_dir=current_dir,
        output_filename=None,  # Автоимя: projectname_mmdd_HHMM
        exclude_dirs={'venv', '__pycache__', '.git', 'dataset', 'node_modules', 'dist', 'build', '.vscode', 'mocks'},
        exclude_files={'README.md', '.gitignore', 'collect_code.py'},
        allowed_extensions={'.py', '.txt', '.dockerfile', 'dockerfile', '.sh', '.yml', '.yaml', '.json', '.md'}
    )