import os
import re
import sys
import threading
import subprocess
import pytesseract
from PIL import Image, ImageGrab

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

ROOT = os.path.dirname(os.path.abspath(__file__))
LLAMA_EXE = os.path.join(ROOT, "Llama.cpp", "llama-cli.exe")
MODELS_DIR = os.path.join(ROOT, "models")
MODEL_PATH = ""
if os.path.exists(MODELS_DIR):
    for f in os.listdir(MODELS_DIR):
        if f.endswith(".gguf"):
            MODEL_PATH = os.path.join(MODELS_DIR, f)
            break

NOISE_SUBSTRINGS = [
    "llama_", "system_info", "llm_load", "ggml_", "gguf_",
    "sampling:", "sampled token", "[end of text]", "ms per token",
    "tokens per second", "Loading model", "available commands",
    "/exit or", "/regen", "/clear", "/read <", "/glob <",
    "stop or exit", "regenerate the last", "clear the chat",
    "add a text file", "add text files", "t/s ]", "Ctrl+C",
    "<|im_", "llama.cpp",
]
NOISE_HEADER_RE = re.compile(r"^(build|model|modalities|clip|main)\s*:", re.I)
NOISE_STAT_RE   = re.compile(r"^\[.*t/s.*\]")

PYTHON_STARTERS = (
    "import ", "from ", "# ", "#!", "def ", "class ", "for ", "while ",
    "if ", "with ", "try:", "count", "result", "ans", "n =", "n=",
    "alphabet", "letters", "words", "print(", "a =", "a=",
    "max_", "min_", "graph", "dist", "total", "data",
)

EXAMPLES = {
    "8": (
        "Задача 8 ЕГЭ.\nАлфавит: ['А', 'Б', 'В']\nДлина слова: 3\n"
        "Условие: начинается на «А», не содержит «ВВ».\n"
        "Используй itertools.product(['А', 'Б', 'В'], repeat=3).",

        "import itertools\n"
        "alphabet = ['А', 'Б', 'В']\n"
        "count = 0\n"
        "for word in itertools.product(alphabet, repeat=3):\n"
        "    s = ''.join(word)\n"
        "    if s[0] == 'А' and 'ВВ' not in s:\n"
        "        count += 1\n"
        "print(count)\n",
    ),
    "15": (
        "Задача 15 ЕГЭ. Логика.\n"
        "Выражение: (X or Y) and not Z\n"
        "Найти максимальное целое X методом перебора.",

        "max_x = -1\n"
        "for x in range(256):\n"
        "    for y in range(2):\n"
        "        for z in range(2):\n"
        "            if (x or y) and not z:\n"
        "                if x > max_x:\n"
        "                    max_x = x\n"
        "print(max_x)\n",
    ),
    "17": (
        "Задача 17 ЕГЭ по информатике:\n"
        "Дан файл numbers.txt с числами. Найти количество чисел, делящихся на 3 и на 5.",

        "count = 0\n"
        "with open('numbers.txt') as f:\n"
        "    for line in f:\n"
        "        for num in line.split():\n"
        "            n = int(num)\n"
        "            if n % 3 == 0 and n % 5 == 0:\n"
        "                count += 1\n"
        "print(count)\n",
    ),
    "24": (
        "Задача 24 ЕГЭ по информатике:\n"
        "Дан взвешенный граф (список рёбер u v w). Найти минимальный путь от вершины 1 до N.",

        "import heapq\n"
        "n, m = map(int, input().split())\n"
        "graph = {i: [] for i in range(1, n+1)}\n"
        "for _ in range(m):\n"
        "    u, v, w = map(int, input().split())\n"
        "    graph[u].append((v, w))\n"
        "    graph[v].append((u, w))\n"
        "dist = {v: float('inf') for v in range(1, n+1)}\n"
        "dist[1] = 0\n"
        "pq = [(0, 1)]\n"
        "while pq:\n"
        "    d, v = heapq.heappop(pq)\n"
        "    if d > dist[v]:\n"
        "        continue\n"
        "    for u, w in graph[v]:\n"
        "        if dist[v] + w < dist[u]:\n"
        "            dist[u] = dist[v] + w\n"
        "            heapq.heappush(pq, (dist[u], u))\n"
        "print(dist[n])\n",
    ),
}


def build_prompt(task_num, user_task):
    system = (
        "Ты решаешь задачи ЕГЭ по информатике на Python. "
        "Пиши ТОЛЬКО Python-код без объяснений и без markdown. "
        "Используй ТОЧНО те данные которые даны в задаче."
    )
    parts = [f"<|im_start|>system\n{system}<|im_end|>"]
    ex = EXAMPLES.get(task_num)
    if ex:
        ex_user, ex_code = ex
        parts.append(f"<|im_start|>user\n{ex_user}<|im_end|>")
        parts.append(f"<|im_start|>assistant\n{ex_code}<|im_end|>")
    parts.append(f"<|im_start|>user\n{user_task}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


def is_noise(line):
    if NOISE_HEADER_RE.match(line.strip()):
        return True
    if NOISE_STAT_RE.match(line.strip()):
        return True
    return any(x in line for x in NOISE_SUBSTRINGS)


def get_answer_to_file(task_num, prompt, temp=0.1):
    if not MODEL_PATH:
        print("Ошибка: Модель не найдена в папке models!")
        return
    full_prompt = build_prompt(task_num, prompt)
    prompt_file = os.path.join(ROOT, "prompt_tmp.txt")
    with open(prompt_file, "w", encoding="utf-8") as pf:
        pf.write(full_prompt)
    cmd = [
        LLAMA_EXE, "-m", MODEL_PATH,
        "-f", prompt_file,
        "-n", "700",
        "--temp", str(temp),
        "--threads", "4",
        "--no-mmap",
    ]
    answer_path = os.path.join(ROOT, "answer.py")
    print("\n[ГЕНЕРАЦИЯ...]\n" + "=" * 40)
    code_lines = []
    code_started = False
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        import time as _time
        last_t = [_time.monotonic()]
        reader_done = threading.Event()

        def reader():
            nonlocal code_started
            for line in process.stdout:
                stripped = line.strip()
                if is_noise(line) or stripped == ">":
                    continue
                if stripped.startswith('```'):
                    continue
                if not code_started:
                    if stripped and any(stripped.startswith(kw) for kw in PYTHON_STARTERS):
                        code_started = True
                    else:
                        continue
                cleaned = line.replace("<|im_end|>", "").replace("<|im_start|>", "")
                code_lines.append(cleaned)
                last_t[0] = _time.monotonic()
                print(cleaned, end="", flush=True)
            reader_done.set()

        t = threading.Thread(target=reader, daemon=True)
        t.start()

        while True:
            if reader_done.wait(timeout=1):
                break
            if code_started and _time.monotonic() - last_t[0] > 3:
                break

        try:
            process.kill()
            process.wait()
        except Exception:
            pass

        t.join(timeout=3)

    except FileNotFoundError:
        print(f"\nОшибка: llama-cli.exe не найден:\n{LLAMA_EXE}")
        return
    except Exception as e:
        print(f"\nОшибка: {e}")
        return
    finally:
        try:
            os.remove(prompt_file)
        except Exception:
            pass
    while code_lines and not code_lines[0].strip():
        code_lines.pop(0)
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()
    with open(answer_path, "w", encoding="utf-8") as f:
        f.write("".join(code_lines))
    print("\n" + "=" * 40)
    print("--- ГОТОВО! Код сохранён в answer.py ---")


def ocr_task():
    print("\n[ОЦР РЕЖИМ]")
    print("Нажми Enter — взять скрин из буфера обмена (PrtSc)")
    path = input("Или введи путь к файлу: ").strip()
    try:
        if path:
            img = Image.open(path)
        else:
            img = ImageGrab.grabclipboard()
            if img is None:
                print("Буфер обмена пуст — сначала сделай скриншот (PrtSc или Win+Shift+S)")
                return None
        print("Распознаю...")
        text = pytesseract.image_to_string(img, lang="rus+eng").strip()
        if not text:
            print("Текст не распознан — попробуй более чёткий скрин")
            return None
        print("\n--- Распознанный текст ---")
        print(text)
        print("---")
        fix = input("\nПодправить вручную? (Enter — оставить): ").strip()
        return fix if fix else text
    except Exception as e:
        print(f"Ошибка OCR: {e}")
        return None


def main():
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    print("=== Е Г Э   А В Т О М А Т ===")
    print("0 — OCR скрина | 8/15/17/24 — задания | exit")
    while True:
        num = input("\nНомер задания: ").strip()
        if num.lower() == "exit":
            break
        if num == "0":
            task_text = ocr_task()
            if not task_text:
                continue
            num = input("Номер задания (8/15/17/24): ").strip()
            prompt = f"Задача {num} ЕГЭ:\n{task_text}"
        elif num == "8":
            abc = input("Алфавит (слитно, рус): ").strip()
            length = input("Длина слова: ").strip()
            cond = input("Условие: ").strip()
            letters = list(abc)
            letters_repr = str(letters)
            prompt = (
                f"Задача 8 ЕГЭ.\n"
                f"Алфавит: {letters_repr}\n"
                f"Длина слова: {length}\n"
                f"Условие: {cond}\n"
                f"Используй itertools.product({letters_repr}, repeat={length})."
            )
        elif num == "15":
            expr = input("Логическое выражение: ").strip()
            goal = input("Найти A (min/max): ").strip()
            prompt = (
                f"Задача 15 ЕГЭ. Логика.\n"
                f"Выражение: {expr}\n"
                f"Найти {goal} целое А методом перебора."
            )
        elif num in ("17", "24"):
            task = input("Вставь условие полностью: ").strip()
            prompt = f"Задача {num} ЕГЭ по информатике:\n{task}"
        else:
            task = input("Вставь условие полностью: ").strip()
            prompt = f"Задача {num} ЕГЭ по информатике:\n{task}"
        get_answer_to_file(num, prompt)
        while True:
            print("\n1 — Новое задание | 2 — Переделать | 3 — Ещё вариант")
            ch = input("Выбор (Enter — новое): ").strip()
            if ch == "2":
                extra = input("Доп. условие: ").strip()
                prompt += "\nДоп. условие: " + extra
                get_answer_to_file(num, prompt)
            elif ch == "3":
                get_answer_to_file(num, prompt, temp=0.5)
            else:
                break


if __name__ == "__main__":
    main()
