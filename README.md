# ЕГЭ ИИ Автомат

Локальный инструмент для решения задач ЕГЭ по информатике с помощью LLM (llama.cpp + Qwen2.5-Coder).

## Что умеет

- Задание 8 — комбинаторика (itertools.product)
- Задание 15 — логика, перебор
- Задание 17 — обработка файлов
- Задание 24 — графы (Дейкстра)
- OCR режим — скинь скрин задачи, текст распознаётся автоматически

## Установка

1. Скачай [WinPython 3.11](https://winpython.github.io/) в папку `WinPython/`
2. Скачай [llama.cpp](https://github.com/ggerganov/llama.cpp/releases) в папку `llama.cpp/`
3. Положи модель `.gguf` в папку `models/` (рекомендуется `qwen2.5-coder-3b-instruct-q5_k_m.gguf`)
4. Установи [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (для OCR режима)
5. Установи зависимости:
   ```
   WinPython\python-3.11.9.amd64\python.exe -m pip install pytesseract pillow
   ```

## Запуск

Двойной клик на `start.bat`

## Использование

```
0 — OCR скрина | 8/15/17/24 — задания | exit
```

После генерации:
```
1 — Новое задание | 2 — Переделать | 3 — Ещё вариант
```
