# -*- coding: utf-8 -*-
"""memory_epistemic.py -- temporal edges for memory notes + a Book of Contradictions.

WHAT (English summary; the detailed design notes below are in Russian, kept verbatim
because they are the working documentation of the machine this was built on):

  A memory note is never UPDATED in place. When a fact is refuted or replaced, the old
  note is CLOSED by fields inside its frontmatter `metadata:` block:

      status: active | refuted | superseded | stale-suspect   (absent == active)
      valid_from / valid_to: YYYY-MM-DD                        (valid_to empty == in force)
      superseded_by: <slug>      refuted_on: YYYY-MM-DD      refuted_by: <slug|source>

  --lint   finds notes whose body says "refuted/dead/superseded" while the frontmatter
           still reads active (A), sibling notes on the same subject where only one is
           closed (B), and same-subject opposite-polarity pairs (C, candidates only).
  --close  <old> --superseded-by <new> writes the closure into EVERY copy of the note
           the scanner can find (multi-project memory dirs), backs each file up first,
           refuses unreadable/BOM-broken files instead of corrupting them, and appends
           one line to the Book of Contradictions (~/.claude/contradiction_book.jsonl).
  --book   renders the Book.

WHY: on 2026-08-04 a verdict ("vendor X's research rail is dead") lived in four memory
notes; the refutation was written into one. Three sessions worked from the dead verdict
for nine more days. Supersession that does not fan out to every copy is supersession the
reader never sees.

Built for one Claude Code fleet -- adapt paths: DEFAULT_ROOT / BOOK_JSONL / USAGE_LOG
below. stdlib only, 0 LLM, 0 network. Tests: tests/test_memory_epistemic*.py (red-first).

---- original working notes (ru) ----
Эпистемический слой памяти: временные рёбра у записей + Книга ошибок.

НАЗНАЧЕНИЕ. Замер, ради которого написан: вывод «ChatGPT DR мёртв» жил в ЧЕТЫРЁХ
записях памяти. Опровержение 04.08 написали в ОДНУ, и оно не доехало до трёх
остальных — потому что у записи памяти нет ни срока годности, ни машинной ссылки
на то, что её отменило. Девять дней три сессии работали по мёртвому правилу.
Идея из DR26-07-26-ZB-03 (Gemini): вместо UPDATE — ТЕМПОРАЛЬНЫЕ РЁБРА
valid_from/valid_to. Старое утверждение не стирается, а ЗАКРЫВАЕТСЯ по времени;
найденное противоречие не проглатывается, а пишется в отдельную Книгу ошибок.

КОНТРАКТ FRONTMATTER (все поля живут ВНУТРИ блока `metadata:`, рядом с node_type/
type/modified — так harness-парсер памяти не ломается, YAML остаётся валидным):
    status: active | refuted | superseded | stale-suspect
            поле НЕОБЯЗАТЕЛЬНОЕ; отсутствует == active (обратная совместимость
            со всеми 1119 существующими записями — миграция не нужна)
    valid_from: YYYY-MM-DD   по умолчанию = дата создания записи
                             (metadata.modified, иначе ctime файла)
    valid_to:   YYYY-MM-DD   ставится, когда запись отменена; ПУСТО = действует
    superseded_by: <slug>    чем заменено; допускается список [a, b]
    refuted_on: YYYY-MM-DD   когда опровергнуто
    refuted_by: <slug|источник>  чем опровергнуто
Пустая строка valid_to и отсутствие ключа значат одно и то же — «действует».

ВХОД:  --lint [--root DIR]        — все memory/*.md всех локальных проектов
       --close <slug> --superseded-by <slug> [--date] [--status] [--evidence]
       --book [--limit N]
ВЫХОД: exit 0 = чисто / операция выполнена
       exit 2 = --lint нашёл находки (fail-closed ОТЧЁТ, не блокировщик)
       exit 1 = ошибка вызова / запись не удалась
       stdout строго ASCII (Windows-консоль). Кириллица уходит в --json
       (ensure_ascii) и в UTF-8 зеркало Книги ошибок.

ЧТО ИЩЕТ --lint (0 LLM, 0 сети, только диск, детерминированно):
  A-BODY-ONLY   в ТЕЛЕ/description есть маркер опровержения, а в frontmatter нет
                ни status, ни valid_to => опровержение известно ЧЕЛОВЕКУ и
                невидимо МАШИНЕ. Делится на два подвида, потому что «разбор» и
                «заявление» — разные вещи (та же грабля, что RETRO_MARK в
                dead_claim_guard):
                  SELF-TOMBSTONE  запись хоронит САМУ СЕБЯ: маркер в НАЧАЛЕ
                                  description (<=40 симв.) ЛИБО первая непустая
                                  строка тела -- blockquote '>' с маркером.
                                  Кандидат на --close; замена вытаскивается,
                                  только если стоит сразу после «см.»/«see».
                  CORRECTION-NOTE запись ФИКСИРУЕТ чужое опровержение и сама
                                  жива. Закрывать её НЕЛЬЗЯ. Линтер их не путает
                                  и НИЧЕГО не закрывает сам.
  B-TWIN-CLUSTER  кластеры-тёзки: один файл про предмет помечен опровергнутым, а
                другие про тот же предмет — нет. Ровно случай chatgpt-dr-*.
                Родство считается по РЕДКИМ терминам (df<=MAX_DF) слага и
                description, а не по подстроке.
  C-POLARITY    у двух записей ОДИН предмет и ПРОТИВОПОЛОЖНОЕ утверждение
                ОДНОЙ оси. Осей ДВЕ и смешивать их нельзя: 'state'
                (жив/мёртв, работает/не работает) и 'perm' (можно/нельзя).
                Отрицание строится ИЗ положительного ядра, поэтому «не жив»,
                «больше не жив», «not alive» читаются как NEG (дефект ниже).
                Пара доживает до отчёта только через ЧЕТВЕРО ворот:
                  1. ростер не судится   -- HUB/инвентарь перечисляет десятки
                     предметов, слово в заголовке списка не есть утверждение;
                  2. ось одна и та же    -- запрет не спорит с состоянием;
                  3. предмет назван в ОБОИХ слагах -- «похожие слова» в
                     description общим предметом НЕ являются;
                  4. полярное слово стоит в ТОЙ ЖЕ клаузе, что и предмет --
                     иначе оно про соседний предмет той же записи.
                Закрытая запись (valid_to/refuted) в пары не берётся: спор
                уже рассужен, ему место в классе B.

⚠️ ЧЕГО C-POLARITY НЕ УМЕЕТ (честно, замер 02.09):
  * отличить УТВЕРЖДЕНИЕ о предмете от УПОМИНАНИЯ предмета. «алярм не зависит
    от dead коннектора» для него -- neg про коннектор. Ворота 1 и 4 срезают
    массовый случай, но остаток есть и будет: это словарный детектор, а не
    понимание текста.
  * увидеть предмет, названный ТОЛЬКО в слаге и ни разу в description:
    ворота 4 такую пару отбросят. Это ЦЕНА ворот 4, названа вслух.
  * судить спор, где обе записи правы в своих условиях («жив на хабе, мёртв
    на ноуте»). Условие он не читает вовсе.
  Поэтому класс C -- КАНДИДАТЫ ЧЕЛОВЕКУ, а не вердикт. Замер по живому корпусу
  02.09: ДО ворот -- 2 пары на пороге score>=4 и 6 пар на пороге 3, ВСЕ ложные
  (точность 0/6); ПОСЛЕ -- 0 пар на обоих порогах, класс держится фикстурами
  (кейсы 07/17/18/19/20 сетки), а не удачей корпуса.

ЧЕГО --lint НЕ ДЕЛАЕТ: не судит, кто прав. Он поднимает СТОЛКНОВЕНИЕ; вердикт
выносит человек или сессия через --close с ДВУМЯ явными слагами. Автозакрытия
нет by design — детектор, который сам чинит по догадке, портит данные молча.

КНИГА ОШИБОК: ~/.claude/contradiction_book.jsonl (истина) + .md (зеркало,
перегенерируется целиком из jsonl). Одна строка = одно столкновение
УТВЕРЖДЕНИЙ: дата, предмет, участники, что победило, чем доказано, кто закрыл.
Это НЕ лог ошибок скрипта.

⚠ КНИГА ОБЩАЯ И APPEND-ONLY. В неё пишет не только этот скрипт — замер 02.09:
сосед recall_eval кладёт туда atom-mismatch со СВОЕЙ схемой (evidence словарём,
subject назван topic), и мой рендер на этом падал. Поэтому три правила:
jsonl НИКОГДА не перезаписывается целиком (перезаписывается только .md-зеркало);
чужая строка не роняет рендер и показывается как есть; свои строки помечены
`source: memory_epistemic`, а дедуп живёт в стабильном `conflict_id` = якорь
конфликта БЕЗ списка участников (список меняется — конфликт тот же).

ДЕФЕКТ ДЕТЕКТОРА, найденный бисекцией 02.09 (класс «переворот полярности»):
перечень отрицаний был ЗАКРЫТЫМ списком «не + глагол», и сетка сторожила РОВНО
ОДНУ форму — «не работает». Достаточно было поменять глагол, чтобы детектор
ПЕРЕВЕРНУЛ смысл: «канал не живой», «больше не жив», «not alive», «не works» —
все четыре давали **pos**. Цена: живая запись «рельса больше не жива» читалась
как «жива», настоящее противоречие пропускалось, а ложное рождалось. Починка:
отрицание СТРОИТСЯ из того же положительного ядра (_neg_of), поэтому новое
слово в POS автоматически закрыто и в отрицательной форме; «не только жив»
исключено явно. Сторожит кейс 16 (семь форм), мутация M1 гасит его красным.

ПАНЕЛЬ ЛОМАТЕЛЕЙ 02.09 — найдено и закрыто (тесты в _test_memory_epistemic_breaker.py):
  * --close по записи в CP1251 переписывал ТЕЛО ромбиками U+FFFD и рапортовал
    «CLOSED», хотя bad_utf8 уже был известен -> теперь REFUSED, exit 1.
  * BOM (UTF-8 with BOM = дефолт PowerShell Out-File) ронял разбор frontmatter:
    надгробие деградировало в correction-note, а --close врал «idempotent» ->
    BOM снимается при чтении и возвращается при записи.
  * «нечего писать» и «НЕКУДА писать» возвращались одинаково -> запись без
    frontmatter получала вердикт «all copies already carry these fields».
    Теперь REFUSED, exit 1.
  * идемпотентность держалась только на значениях без кавычек: refuted_by с
    '\\' или ':' (путь E:\\Obsidian\\...) переписывался КАЖДЫЙ прогон, плодя
    .epibak-* и дубли в Книге -> сравниваем рендер строки, а не strip_q.
  * чужая строка Книги роняла рендер на трёх формах (json-массив, скаляр,
    ts эпохой-числом). Падало ИЗ book_append, т.е. после записи заметок и
    jsonl -- без зеркала и без счётчика; той же дверью ходит recall_eval.
  * --lint --json на пустом/несуществующем корне печатал прозу вместо JSON,
    и опечатка в --root была неотличима от «чисто».

ВЕЕР 5 02.09 — класс «ЗАКРЫЛИ ОДНУ КОПИЮ ИЗ ЧЕТЫРЁХ» добит в трёх дверях:
  * --close писал копии ПО ХОДУ проверки: отказ на 2-й копии (битый
    frontmatter) оставлял 1-ю закрытой, остальные живыми, Книгу пустой,
    exit 1. Теперь ВСЁ ИЛИ НИЧЕГО: фаза 1 проверяет все копии (unreadable /
    bad_utf8 / no-frontmatter / yaml), фаза 2 пишет только когда отказов нет;
    --dry-run печатает ЧИСЛО копий («would close N of M copies»).
  * файл, который не прочитался (I/O), исчезал из списка молча -> при
    залоченной копии close отвечал «idempotent: all 2 copies», exit 0, и
    невидимая копия ПЕРЕЖИВАЛА закрытие. Теперь заглушка unreadable_stub:
    --lint называет файл вслух, --close по этому слагу отказывает целиком.
  * битый frontmatter ('---' открыт и не закрыт) судился молча как проза:
    поля невидимы, SELF-TOMBSTONE деградировал, честной строки не было.
    Теперь --lint печатает WARNING с именем файла + --json поля
    broken_frontmatter / unreadable_files.

КТО ДЁРГАЕТ: сессия руками при разборе противоречия; /retro и /intake — перед
записью нового правила (не отменяет ли оно старое); кандидат в ночную сетку.
⚠️ ДВЕРИ НЕТ: ни скилл, ни хук, ни задача его пока не зовут (§8.6).
РЕЛЬСА: чистый stdlib, локальный диск. 0 LLM, 0 токенов, 0 сети.
СЧЁТЧИК: scripts/_memory_epistemic_usage.jsonl (одна строка на прогон).
ТЕСТЫ: scripts/_test_memory_epistemic.py (26 проверок, сетка автора; кейсы
       21-24 = веер 5, каждый показан КРАСНЫМ на копии до-фиксного кода)
       scripts/_test_memory_epistemic_breaker.py (12 проверок, сетка ломателя: по одной
       красной проверке на каждый закрытый класс выше; ревертни фикс -- она краснеет)
МУТАЦИОННЫЙ ЗАМЕР 02.09 (на КОПИИ в скретчпаде, живой файл не трогался): ядро
       ломалось шестью способами -- снят _neg_of, снят ростер-гейт, слиты оси,
       выпотрошен subject_terms, снята привязка к клаузе, ослаблен признак T2
       надгробия. Сетка убила 6/6 (каждая мутация красит СВОЙ кейс), после
       восстановления 22/22 PASS. До усиления кейсы 17 и 19 зеленели на
       выпотрошенных воротах -- их пару добивали соседние ворота, поэтому обе
       двери теперь проверяются ещё и НАПРЯМУЮ (is_roster, subject_terms).

⚠️ НЕ ПРИМЕНЁН К ЖИВОЙ ПАМЯТИ (замер 02.09): --lint по реальному корпусу видит 832 записи,
    3 действующих SELF-TOMBSTONE и 52 CORRECTION-NOTE. Класс, ради которого написан
    инструмент, ОБНАРУЖИВАЕТСЯ, но остаётся ОТКРЫТ: вердикт по каждому столкновению
    выносит человек через --close с двумя явными слагами.
⚠️ КОРПУС МЕНЯЕТСЯ ПОД ТЕСТОМ. Семья chatgpt-dr-* закрыта полями 02.09
    (chatgpt-dr-zero-searches-fake-report: status refuted, valid_to 2026-08-04,
    superseded_by chatgpt-dr-mini-counter-lies; рядом .epibak-20260902-113036).
    Из класса A она после этого ПРОПАЛА — и это ПРАВИЛЬНО: A по определению
    «маркер в тексте, frontmatter молчит». Старый кейс 14 требовал от ЖИВОГО
    корпуса незакрытого самонадгробия и покраснел на штатной работе системы.
    Теперь поведение сторожит фикстура (14a/14b), а живой корпус — мягкий 14c.

ЗЕРКАЛО ДЛЯ ЧЕЛОВЕКА: волт 00-System/Contradiction-Book.md -- та же Книга ошибок, но
    написанная словами (машинная истина по-прежнему jsonl рядом с этим скриптом).
ПАСПОРТ (меж-файловая картина четырёх деталей): волт
    00-System/Parts/alpha-memory-eval-2026-09-02.md
updated: 2026-09-02
"""
import argparse
import datetime
import io
import json
import os
import re
import socket
import sys

HOME = os.path.expanduser("~")
DEFAULT_ROOT = os.path.join(HOME, ".claude", "projects")
BOOK_JSONL = os.path.join(HOME, ".claude", "contradiction_book.jsonl")
BOOK_MD = os.path.join(HOME, ".claude", "contradiction_book.md")
USAGE_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "_memory_epistemic_usage.jsonl")

VALID_STATUS = ("active", "refuted", "superseded", "stale-suspect")
EPI_KEYS = ("status", "valid_from", "valid_to", "superseded_by",
            "refuted_on", "refuted_by")

# Индексы/бэкапы памяти -- это НЕ записи-утверждения, судить их нечего.
SKIP_BASENAMES = re.compile(
    r"^(MEMORY|MEMORY-archive|MEMORY\.v\d+|memory-focus-hints)"
    r"([~.\-].*)?\.md$", re.IGNORECASE)
# Протухшие копии: версии Syncthing и конфликт-корзины. Замер 02.09 -- 292 файла.
SKIP_DIRS = re.compile(
    r"^(\.stversions|\.stfolder|_drafts|_conflict-fix-bak.*|"
    r"_resolved-conflict-trash|\.git)$", re.IGNORECASE)

# --- маркеры опровержения -------------------------------------------------
# Сильные словесные: замер 02.09 по живому корпусу -- 66 файлов из 1119 (5.9%).
# Голый U+26D4 давал 294 из 1119 (26%) = сирена, поэтому он засчитывается ТОЛЬКО
# рядом с датой (спека: "⛔ ... 202") или рядом со словесным маркером.
MARKERS = [
    ("REFUTED_RU", re.compile(u"ОПРОВЕРГНУТ(?:О|Ы|)\\b", re.UNICODE)),
    ("REFUTED_RU_LC", re.compile(u"опроверг(?:нут|ло|ает)", re.UNICODE)),
    ("REFUTED_EN", re.compile(r"\bREFUTED\b")),
    ("SUPERSEDED_EN", re.compile(r"\bSUPERSEDED\b")),
    ("CANCELLED_RU", re.compile(u"ОТМЕН[ЁЕ]Н(?:О|)\\b", re.UNICODE)),
    ("WRONG_CONCLUSION", re.compile(
        u"вывод[^.\\n]{0,80}?(?:неверен|неверн|оказался ложн|ошибочен)",
        re.UNICODE | re.IGNORECASE)),
    # "⛔ ... 202x" -- запрет/отмена с годом в пределах одной строки.
    ("STOP_DATED", re.compile(u"⛔[^\\n]{0,120}?\\b20\\d\\d\\b", re.UNICODE)),
]
WIKILINK = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]")
# «см. [[X]]» / «see [[X]]» / «-> [[X]]» -- явный указатель на ЗАМЕНУ.
# ⚠️ ТОЛЬКО raw-строка: в обычной u"" последовательность \b -- это BACKSPACE,
# а не граница слова (грабля, уже оплаченная мёртвым --words в status_claim_lint).
REPLACE_POINTER = re.compile(
    r"(?:\bсм\.?|\bsee\b|->|=>)[^\[\n]{0,12}"
    r"\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]",
    re.UNICODE | re.IGNORECASE)

# --- полярность (класс C) -------------------------------------------------
# ДВЕ ОСИ, а не одна. Смешивать их нельзя: «нельзя врать» -- это ЗАПРЕТ, а
# «канал жив» -- СОСТОЯНИЕ, и пара из разных осей никогда не противоречие.
# Замер 02.09 по живому корпусу: hub-leads-outreach («живой тред», ось
# состояния) вставал в пару с vip-leads-no-robot-text («врать нельзя», ось
# разрешения) -- ложная пара ровно по этой причине.
STATE_POS_CORE = (u"(?:\\bработает\\b|\\bжив\\w*|\\bдоступ[ен]\\w*|\\bищет\\b"
                  u"|\\balive\\b|\\bworks\\b|\\bworking\\b)")
STATE_NEG_CORE = (u"(?:\\bм[ёе]ртв\\w*|\\bсд[ох]\\w*|\\bпроту[хш]\\w*"
                  u"|\\bнедоступ\\w*|\\bотключ[её]н\\w*"
                  u"|\\bdead\\b|\\bbroken\\b|\\bdoes\\s+not\\s+work\\b)")
PERM_POS_CORE = u"(?:\\bможно\\b|\\bразреш[ае]\\w*|\\ballowed\\b)"
PERM_NEG_CORE = u"(?:\\bнельзя\\b|\\bзапрещ\\w*|\\bforbidden\\b)"

# ОТРИЦАНИЕ ПОЛОЖИТЕЛЬНОГО -- дефект, доказанный бисекцией 02.09.
# Было: перечень отрицаний -- ЗАКРЫТЫЙ список «не + глагол», и сторожилась
# РОВНО ОДНА форма, «не работает» (кейс 07 сетки). Стоило поменять глагол --
# детектор ПЕРЕВОРАЧИВАЛ смысл: «канал не живой», «больше не жив»,
# «not alive», «не works» -- все четыре давали **pos**. Теперь отрицание
# СТРОИТСЯ ИЗ того же положительного ядра, поэтому новое слово в POS
# автоматически закрыто и в отрицательной форме. «не только жив» исключено
# явно -- это усиление, а не отрицание.
NEGATOR = u"(?:\\b(?:больше\\s+)?не\\b|\\bnot\\b|\\bno\\s+longer\\b)"
_SKIP_WORD = u"(?:(?!(?:только|лишь|only|just)\\b)[\\w-]+\\s+)?"
_FLAGS = re.UNICODE | re.IGNORECASE


def _rx(core):
    return re.compile(core, _FLAGS)


def _neg_of(pos_core):
    """«не / not / больше не [слово] <положительное>» -- это ОТРИЦАНИЕ."""
    return re.compile(NEGATOR + u"\\s+" + _SKIP_WORD + pos_core, _FLAGS)


# (имя оси, POS, NEG-слова, отрицание-POS)
AXES = (
    ("state", _rx(STATE_POS_CORE), _rx(STATE_NEG_CORE), _neg_of(STATE_POS_CORE)),
    ("perm", _rx(PERM_POS_CORE), _rx(PERM_NEG_CORE), _neg_of(PERM_POS_CORE)),
)

# Совместимость со старыми именами (кейс 07 сетки и внешние пробы).
NEG_PHRASES = _rx(u"(?:" + STATE_NEG_CORE + u"|" + PERM_NEG_CORE
                  + u"|" + NEGATOR + u"\\s+" + _SKIP_WORD + STATE_POS_CORE + u")")
POS_PHRASES = _rx(u"(?:" + STATE_POS_CORE + u"|" + PERM_POS_CORE + u")")

# РОСТЕР -- не утверждение. HUB/инвентарь перечисляет ДЕСЯТКИ предметов, и одно
# слово в его заголовке («HUB ЖИВЫХ коннекторов: Granola, WhatsApp, Gmail, ...»)
# не есть утверждение о конкретном предмете. Та же логика, что у SKIP_BASENAMES:
# индекс судить нечего. Замер 02.09: 24 hub-* слага на 832 записи.
ROSTER_SLUG = re.compile(r"^hub[-_]", re.IGNORECASE)
ROSTER_MIN_LEN = 260      # замер: hub-connectors 323, connector-health-watchdog 157
ROSTER_MIN_ITEMS = 4      # длинный текст + 4 разделителя перечисления = список
ENUM_SEP = re.compile(u"(?:,\\s|;\\s|\\s·\\s)", re.UNICODE)

# ПРЕДМЕТ пары = терм, названный в ОБОИХ слагах. Верхнюю границу df тут НЕ
# ставим (в отличие от rare(): та про СИЛУ улики, а эта про ТОЖДЕСТВО предмета).
# Замер 02.09: df['chatgpt'] = 13 при MAX_DF = 12, то есть на rare() настоящая
# пара chatgpt-dr-* была бы отброшена как «разные предметы».
SUBJ_MIN_TOK = 4
SUBJ_STOP = frozenset((
    "must", "cannot", "keeps", "beats", "needs", "does", "done", "with",
    "without", "this", "that", "then", "than", "from", "into", "only",
    "just", "when", "what", "which", "your", "our", "the", "and", "not",
    "but", "for", "was", "were", "been", "have", "has",
))

# Граница КЛАУЗЫ: полярное слово обязано стоять в том же куске фразы, что и
# ОБЩИЙ терм пары. Иначе это слово про ДРУГОЙ предмет той же записи.
CLAUSE_SPLIT = re.compile(u"[.;:!?\\n·•()\\[\\]]|\\s—\\s|\\s--\\s|\\s\\+\\s",
                          re.UNICODE)

TOKEN = re.compile(u"[0-9a-zA-Zа-яёА-ЯЁ]+", re.UNICODE)
KV = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_.\-]*)\s*:\s?(.*)$")

MAX_DF = 12          # терм в >12 записях -- общий, для родства бесполезен
MIN_SLUG_TOK = 3     # "dr" отбрасываем, "chatgpt" оставляем
MIN_TEXT_TOK = 4


# ===================== ввод/вывод =========================================

def read_text(path):
    """Читает файл. -> (text, bad_utf8, had_bom).

    Кривой UTF-8 не роняет прогон: replace + флаг. Флаг НЕ косметика --
    по нему --close отказывается писать (иначе replace-символы затирают тело).
    BOM снимается ДО разбора и возвращается на место при записи: с ним
    lines[0] == '\\ufeff---' и frontmatter молча не находился, надгробие
    деградировало в correction-note, а --close врал «idempotent»
    (ломатель 02.09, PowerShell Out-File по умолчанию пишет UTF-8 с BOM).
    """
    with io.open(path, "rb") as fh:
        raw = fh.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    if bom:
        raw = raw[3:]
    try:
        return raw.decode("utf-8"), False, bom
    except UnicodeDecodeError:
        return raw.decode("utf-8", "replace"), True, bom


def write_text_atomic(path, text):
    """Пишет UTF-8 через временный файл + os.replace (атомарно на одном томе)."""
    tmp = path + ".epitmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)


def say(msg):
    """stdout строго ASCII -- Windows-консоль иначе рвёт кириллицу."""
    sys.stdout.write(msg.encode("ascii", "replace").decode("ascii") + "\n")


# ===================== frontmatter ========================================

def strip_q(val):
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    return val


def quote_if_needed(val):
    """YAML-безопасное значение: свободный текст с ':' обязан быть в кавычках."""
    s = str(val)
    if s == "":
        return '""'
    if re.search(r"[:#\[\]{}&*!|>%@`]", s) or s[0] in "-? " or s != s.strip():
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def split_front(text):
    """-> (lines, close_idx) где lines -- ВЕСЬ файл построчно, close_idx --
    индекс закрывающего '---'. None, если frontmatter нет."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, min(len(lines), 400)):
        if lines[i].strip() == "---":
            return lines, i
    return None


def parse_front(lines, close_idx):
    """Разбирает frontmatter вручную (без yaml -- --help обязан отвечать мгновенно).

    -> dict(top, meta, meta_line, meta_indent, meta_last, meta_key_line)
    meta_line   -- индекс строки 'metadata:' (или None)
    meta_last   -- индекс ПОСЛЕДНЕЙ строки подблока metadata
    meta_key_line -- {ключ: индекс строки} для правки на месте
    """
    top, meta, key_line = {}, {}, {}
    meta_line = meta_indent = meta_last = None
    in_meta = False
    for idx in range(1, close_idx):
        raw = lines[idx]
        if not raw.strip():
            continue
        m = KV.match(raw)
        if not m:
            if in_meta and raw.startswith(" "):
                meta_last = idx
            continue
        ind, key, val = m.group(1), m.group(2), m.group(3)
        if len(ind) == 0:
            in_meta = (key == "metadata")
            top[key] = strip_q(val)
            if in_meta:
                meta_line, meta_last = idx, idx
        elif in_meta:
            if meta_indent is None:
                meta_indent = ind
            meta[key] = strip_q(val)
            key_line[key] = idx
            meta_last = idx
    return {"top": top, "meta": meta, "meta_line": meta_line,
            "meta_indent": meta_indent or "  ", "meta_last": meta_last,
            "meta_key_line": key_line}


# ===================== модель записи ======================================

class Note(object):
    __slots__ = ("path", "slug", "desc", "body", "meta", "front", "lines",
                 "close_idx", "bad_utf8", "bom", "markers", "self_tomb", "repl",
                 "broken_front", "unreadable")

    def status(self):
        st = (self.meta.get("status") or "").strip().lower()
        return st if st in VALID_STATUS else ("active" if not st else st)

    def is_closed(self):
        """Машинно закрыта? status refuted/superseded ИЛИ непустой valid_to."""
        return (self.status() in ("refuted", "superseded")
                or bool((self.meta.get("valid_to") or "").strip()))

    def has_epi(self):
        return any((self.meta.get(k) or "").strip() for k in EPI_KEYS)


def load_note(path):
    text, bad, bom = read_text(path)
    sp = split_front(text)
    if sp is None:
        front = {"top": {}, "meta": {}, "meta_line": None,
                 "meta_indent": "  ", "meta_last": None, "meta_key_line": {}}
        lines, close_idx, body = text.split("\n"), -1, text
    else:
        lines, close_idx = sp
        front = parse_front(lines, close_idx)
        body = "\n".join(lines[close_idx + 1:])
    n = Note()
    n.path, n.lines, n.close_idx, n.bad_utf8 = path, lines, close_idx, bad
    n.bom = bom
    # Файл ОТКРЫЛ frontmatter ('---'), но так его и не закрыл: все поля
    # невидимы машине, а сам файл раньше молча судился как «прозы кусок».
    # Тихий скип тут = класс «закрыли одну копию из четырёх»: --close по
    # такому файлу обязан отказаться, --lint -- назвать его вслух.
    n.broken_front = (sp is None and bool(text)
                      and text.split("\n", 1)[0].strip() == "---")
    n.unreadable = False
    n.front, n.meta = front, front["meta"]
    n.slug = (front["top"].get("name")
              or os.path.splitext(os.path.basename(path))[0])
    n.desc = front["top"].get("description", "")
    n.body = body
    n.markers, n.self_tomb, n.repl = detect_markers(n)
    return n


def unreadable_stub(path):
    """Файл ЕСТЬ, но не читается (лок/права). Тихий `skipped += 1` был классом
    «закрыли одну копию из четырёх»: невидимая копия не попадала в targets
    --close, три видимых закрывались, четвёртая жила дальше -- и прогон честно
    рапортовал зелёным (замер 02.09: close при залоченной копии отвечал
    «idempotent: all 2 copies», exit 0). Заглушка держит файл В СПИСКЕ:
    --lint называет его вслух, --close по его слагу отказывается писать
    ЧТО-ЛИБО. В суждениях A/B/C заглушка не участвует (нет ни desc, ни маркеров)."""
    n = Note()
    n.path = path
    n.slug = os.path.splitext(os.path.basename(path))[0]
    n.desc, n.body, n.meta = "", "", {}
    n.front = {"top": {}, "meta": {}, "meta_line": None,
               "meta_indent": "  ", "meta_last": None, "meta_key_line": {}}
    n.lines, n.close_idx = [], -1
    n.bad_utf8 = n.bom = False
    n.markers, n.self_tomb, n.repl = [], False, None
    n.broken_front, n.unreadable = False, True
    return n


def first_body_line(body):
    for ln in body.split("\n"):
        if ln.strip():
            return ln.strip()
    return ""


def detect_markers(n):
    """-> (labels, self_tombstone_bool, replacement_slug_or_None)

    Разделение «ЗАПИСЬ МЕРТВА» и «ЗАПИСЬ ФИКСИРУЕТ ЧУЖУЮ СМЕРТЬ» -- та же грабля,
    что RETRO_MARK в dead_claim_guard: разбор != заявление. Замер 02.09 по живому
    корпусу дал ДВА признака-конвенции, и оба нужны (по одному не хватает):

      T1  маркер стоит В НАЧАЛЕ description (первые TOMB_DESC символов) --
          собственная аннотация записи открывается надгробием
          (chatgpt-dr-zero-searches-fake-report: "⛔ ОПРОВЕРГНУТО 04.08: ...").
      T2  первая непустая строка тела -- BLOCKQUOTE '>' с маркером
          (cowork-feedback-loop, telegram-signals-inventory). Именно '>' , а не
          жирный абзац: chatgpt-deep-research-dead-2026-07 открывается
          "**⛔ Вывод от 26.07 ... ОПРОВЕРГНУТ**" -- это КОРРЕКЦИЯ чужого вывода,
          сама запись жива, и по жирному абзацу она ложно попадала в надгробия.

    Всё прочее = CORRECTION-NOTE: запись фиксирует чужое опровержение и жива.
    Это ЭВРИСТИКА, поэтому --close ничего не закрывает сам: два слага всегда
    называет человек.
    """
    TOMB_DESC, NEAR = 40, 300
    labels = []
    for label, rx in MARKERS:
        if rx.search(n.desc) or rx.search(n.body):
            labels.append(label)
    if not labels:
        return labels, False, None

    head_line = first_body_line(n.body)
    banner = head_line if head_line.startswith(">") else ""
    tomb, repl, zone = False, None, ""
    for _label, rx in MARKERS:
        m = rx.search(n.desc or "")
        if m and m.start() <= TOMB_DESC:
            tomb, zone = True, (n.desc + " " + banner)
            break
        if banner and rx.search(banner):
            tomb, zone = True, (banner + " " + (n.desc or ""))
            break
    if tomb:
        # Замену берём ТОЛЬКО по явному указателю «см.»/«see»/«->». Первый
        # попавшийся wikilink -- это чаще всего related-ссылка: замер 02.09,
        # cowork-vs-cc-division отдавал check-all-places-not-one вместо замены.
        m = REPLACE_POINTER.search(zone)
        if m:
            cand = m.group(1).strip()
            if cand and cand != n.slug:
                repl = cand
    return labels, tomb, repl


def scan(root):
    """Все memory/*.md всех локальных проектов.

    ЯВНО отсекаем и СЧИТАЕМ отсеянное -- «не просканировал» обязано быть
    названным решением, а не тихой потерей (замер 02.09: под projects\\ лежит
    1119 файлов *.md в путях с memory, из них 292 -- Syncthing-версии
    .stversions и конфликт-корзины, то есть ПРОТУХШИЕ КОПИИ; судить их нельзя,
    иначе линтер найдёт «противоречие» записи с её же вчерашней версией).
    -> (notes, skipped_index_files, pruned_dirs)
    """
    notes, skipped, pruned = [], 0, 0
    if not os.path.isdir(root):
        return notes, skipped, pruned
    for dirpath, dirnames, filenames in os.walk(root):
        for d in list(dirnames):
            if SKIP_DIRS.match(d):
                dirnames.remove(d)
                pruned += 1
        if os.path.basename(dirpath).lower() != "memory":
            continue
        for fn in sorted(filenames):
            if not fn.lower().endswith(".md"):
                continue
            if SKIP_BASENAMES.match(fn):
                skipped += 1
                continue
            try:
                notes.append(load_note(os.path.join(dirpath, fn)))
            except (IOError, OSError):
                # НЕ тихий скип: файл остаётся в списке заглушкой, чтобы
                # --lint назвал его, а --close не закрыл соседей без него.
                notes.append(unreadable_stub(os.path.join(dirpath, fn)))
    return notes, skipped, pruned


TRANSLIT = {
    u"а": "a", u"б": "b", u"в": "v", u"г": "g",
    u"д": "d", u"е": "e", u"ё": "e", u"ж": "zh",
    u"з": "z", u"и": "i", u"й": "y", u"к": "k",
    u"л": "l", u"м": "m", u"н": "n", u"о": "o",
    u"п": "p", u"р": "r", u"с": "s", u"т": "t",
    u"у": "u", u"ф": "f", u"х": "h", u"ц": "c",
    u"ч": "ch", u"ш": "sh", u"щ": "sch", u"ъ": "",
    u"ы": "y", u"ь": "", u"э": "e", u"ю": "yu",
    u"я": "ya",
}


def ascii_term(s):
    """stdout строго ASCII, но общие термины -- главная улика родства, терять их
    нельзя. Кириллица -> транслит, всё прочее не-ASCII -> '.'."""
    out = []
    for ch in s:
        if ord(ch) < 128:
            out.append(ch)
        elif ch.lower() in TRANSLIT:
            t = TRANSLIT[ch.lower()]
            out.append(t.upper() if ch.isupper() else t)
        else:
            out.append(".")
    return "".join(out)


# ===================== родство по редким термам ===========================

def tokens_of(n):
    slug = set(t.lower() for t in re.split(r"[-_]+", n.slug)
               if len(t) >= MIN_SLUG_TOK)
    text = set(t.lower() for t in TOKEN.findall(n.desc)
               if len(t) >= MIN_TEXT_TOK)
    return slug, text


def build_index(notes):
    """Document frequency по СЛАГАМ (копии одной записи в разных проектах не
    должны раздувать df -- иначе редкий терм ложно станет общим)."""
    df, per = {}, {}
    seen_slug = {}
    for n in notes:
        s, t = tokens_of(n)
        per[n.path] = (s, t)
        seen_slug.setdefault(n.slug, s | t)
    for _slug, terms in seen_slug.items():
        for term in terms:
            df[term] = df.get(term, 0) + 1
    return df, per


def rare(terms, df):
    return set(t for t in terms if 2 <= df.get(t, 0) <= MAX_DF)


def kinship(a_slug, a_text, b_slug, b_text, df):
    """-> (score, shared_terms). Родство = общие РЕДКИЕ термы.
    Совпадение слаг-терма весит больше: слаг задаёт предмет записи."""
    sa, sb = rare(a_slug, df), rare(b_slug, df)
    ta, tb = rare(a_text, df), rare(b_text, df)
    shared_slug = sa & sb
    shared_text = (ta | sa) & (tb | sb)
    score = 2 * len(shared_slug) + len(shared_text - shared_slug)
    return score, sorted(shared_slug | shared_text)


# ===================== находки ============================================

def find_a(notes):
    """A-BODY-ONLY: маркер в тексте, frontmatter молчит."""
    out = []
    for n in notes:
        if not n.markers or n.is_closed():
            continue
        out.append({
            "kind": "A-BODY-ONLY",
            "sub": "SELF-TOMBSTONE" if n.self_tomb else "CORRECTION-NOTE",
            "slug": n.slug, "path": n.path,
            "markers": n.markers,
            "replacement": n.repl,
            "description": n.desc,
        })
    out.sort(key=lambda d: (d["sub"] != "SELF-TOMBSTONE", d["slug"]))
    return out


def find_b(notes, df, per, min_score=3):
    """B-TWIN-CLUSTER: закрытая (или самохоронящая) запись + живые тёзки."""
    closed = [n for n in notes if n.is_closed() or n.self_tomb]
    out, seen = [], set()
    for r in closed:
        rs, rt = per[r.path]
        # Единица утверждения -- СЛАГ, а не файл: один и тот же слаг живёт
        # копиями в нескольких проектах (замер 02.09:
        # chatgpt-deep-research-dead-2026-07 лежит в двух), и печатать его
        # дважды -- врать про число тёзок.
        by_slug = {}
        for n in notes:
            if (n.slug == r.slug or n.is_closed() or n.self_tomb
                    or n.unreadable):
                continue
            score, shared = kinship(rs, rt, per[n.path][0], per[n.path][1], df)
            if score < min_score:
                continue
            cur = by_slug.get(n.slug)
            if cur is None:
                by_slug[n.slug] = {"slug": n.slug, "paths": [n.path],
                                   "score": score, "shared": shared[:6]}
            else:
                cur["paths"].append(n.path)
                if score > cur["score"]:
                    cur["score"], cur["shared"] = score, shared[:6]
        twins = list(by_slug.values())
        if not twins:
            continue
        twins.sort(key=lambda d: (-d["score"], d["slug"]))
        key = (r.slug, tuple(sorted(t["slug"] for t in twins)))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "kind": "B-TWIN-CLUSTER",
            "refuted": r.slug, "refuted_path": r.path,
            "refuted_state": "frontmatter" if r.is_closed() else "body-only",
            "twins": twins,
        })
    out.sort(key=lambda d: (-len(d["twins"]), d["refuted"]))
    return out


def _blank(m):
    """Замена совпадения пробелами ТОЙ ЖЕ длины: смещения не должны съезжать,
    иначе привязка полярного слова к клаузе указывает не туда."""
    return u" " * (m.end() - m.start())


def polarity_hits(text):
    """-> {ось: (знак, [(start, end), ...])}. Пусто, если ось молчит или спорит.

    Разбор по ОСЯМ: 'state' (работает/мёртв) и 'perm' (можно/нельзя). Каждая
    ось судится независимо; ось, где нашлись И плюс И минус, не судится вовсе
    (запись говорит про две разные вещи).
    """
    res = {}
    if not text:
        return res
    for axis, pos_rx, neg_rx, negpos_rx in AXES:
        neg_spans = ([m.span() for m in neg_rx.finditer(text)]
                     + [m.span() for m in negpos_rx.finditer(text)])
        masked = negpos_rx.sub(_blank, neg_rx.sub(_blank, text))
        pos_spans = [m.span() for m in pos_rx.finditer(masked)]
        if neg_spans and not pos_spans:
            res[axis] = ("neg", sorted(neg_spans))
        elif pos_spans and not neg_spans:
            res[axis] = ("pos", sorted(pos_spans))
    return res


def polarity(text):
    """-> 'neg' | 'pos' | None по оси СОСТОЯНИЯ (совместимость со старым API).

    Ось разрешения ('можно'/'нельзя') здесь НЕ отражается: это другой предмет
    разговора, и раньше она молча подмешивалась в те же 'pos'/'neg'.
    """
    hit = polarity_hits(text).get("state")
    return hit[0] if hit else None


def is_roster(n):
    """Ростер/инвентарь (HUB, длинное перечисление) -- НЕ утверждение.

    Одно слово в заголовке списка не есть заявление о предмете: 'HUB живых
    коннекторов: Granola, WhatsApp, Gmail, ...' -- это оглавление, а не claim
    'коннекторы живы'. Судить такое нельзя (замер 02.09: обе ложные пары
    класса C держались ровно на ростере).
    """
    if ROSTER_SLUG.match(n.slug or ""):
        return True
    d = n.desc or ""
    return len(d) >= ROSTER_MIN_LEN and len(ENUM_SEP.findall(d)) >= ROSTER_MIN_ITEMS


def subject_terms(a_slug_toks, b_slug_toks):
    """Общий ПРЕДМЕТ: терм, стоящий в слаге ОБЕИХ записей.

    Слаг задаёт предмет записи; совпадение только по словам description --
    это «похожие слова», а не общий предмет, и именно оно рождало ложные пары.
    """
    return set(t for t in (a_slug_toks & b_slug_toks)
               if len(t) >= SUBJ_MIN_TOK and t not in SUBJ_STOP)


def _clauses(text):
    """-> [(start, end, set(токенов))] по границам CLAUSE_SPLIT."""
    out, pos = [], 0
    for m in CLAUSE_SPLIT.finditer(text):
        if m.start() > pos:
            out.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        out.append((pos, len(text)))
    return [(s, e, set(t.lower() for t in TOKEN.findall(text[s:e])))
            for s, e in out]


def anchored(text, spans, shared):
    """Полярное слово стоит В ТОЙ ЖЕ клаузе, что и общий терм пары?

    Это и есть ответ на «разные предметы с похожими словами»: слово 'dead' в
    хвосте 'alarm that doesn't depend on the dead connector' говорит не о том
    предмете, по которому запись пересеклась с соседкой.
    """
    if not shared:
        return False
    cls = _clauses(text or "")
    want = set(shared)
    for s, e in spans:
        for cs, ce, toks in cls:
            if cs <= s < ce and (toks & want):
                return True
    return False


def find_c(notes, df, per, min_score=4):
    """C-POLARITY: ОДИН предмет + противоположные утверждения ОДНОЙ оси.

    Четыре ворот, каждые закрывают названный класс ложных пар (замер 02.09):
      1. ростер не судится                 -- инвентарь не утверждение;
      2. ось одна и та же                  -- запрет != состояние;
      3. предмет назван в ОБОИХ слагах     -- «похожие слова» != общий предмет;
      4. полярное слово рядом с общим термом -- иначе оно про другой предмет.
    Закрытая пара (у любой стороны стоит valid_to/refuted) не находка: спор уже
    рассужен, ей место в классе B, а не в открытых противоречиях.
    """
    tagged = []
    for n in notes:
        if is_roster(n):
            continue
        hits = polarity_hits(n.desc)
        if hits:
            tagged.append((n, hits))
    out, seen = [], set()
    for i in range(len(tagged)):
        a, ha = tagged[i]
        for j in range(i + 1, len(tagged)):
            b, hb = tagged[j]
            if a.slug == b.slug or a.is_closed() or b.is_closed():
                continue
            axes = [ax for ax in ha if ax in hb and ha[ax][0] != hb[ax][0]]
            if not axes:
                continue
            score, shared = kinship(per[a.path][0], per[a.path][1],
                                    per[b.path][0], per[b.path][1], df)
            if score < min_score:
                continue
            subject = subject_terms(per[a.path][0], per[b.path][0])
            if not subject:
                continue
            axis = axes[0]
            # Якорь -- ТОЛЬКО термы предмета. Брать сюда ещё и общие слова
            # description нельзя: замер 02.09 показал, что именно они держали
            # последнюю ложную пару (claude-desktop-updates-blocked-hosts VS
            # desktop-staged-update-corpse: «при ЖИВЫХ процессах» стояло рядом
            # с общим словом «апдейт», но не рядом с предметом «desktop»).
            if not (anchored(a.desc, ha[axis][1], subject)
                    and anchored(b.desc, hb[axis][1], subject)):
                continue
            key = tuple(sorted([a.slug, b.slug]))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "kind": "C-POLARITY", "score": score, "shared": shared[:6],
                "axis": axis, "subject": sorted(subject)[:4],
                "a": {"slug": a.slug, "path": a.path, "polarity": ha[axis][0],
                      "closed": a.is_closed()},
                "b": {"slug": b.slug, "path": b.path, "polarity": hb[axis][0],
                      "closed": b.is_closed()},
            })
    out.sort(key=lambda d: -d["score"])
    return out


# ===================== Книга ошибок =======================================

def book_md_of(jsonl):
    return re.sub(r"\.jsonl$", "", jsonl) + ".md"


def _cell(v):
    """Книга -- ОБЩИЙ append-only файл с НЕСКОЛЬКИМИ писателями, и чужая
    схема не обязана совпадать с моей (замер 02.09: recall_eval кладёт evidence
    словарём и subject называет topic -- рендер падал на .replace()).
    Падать на чужой строке запрещено: это журнал, а не моя база."""
    if v is None:
        return u""
    if isinstance(v, (dict, list, tuple)):
        v = json.dumps(v, ensure_ascii=False, sort_keys=True)
    return unicode_str(v).replace(u"|", u"/").replace(u"\n", u" ")


def unicode_str(v):
    return v if isinstance(v, str) else str(v)


def book_row(raw):
    """Любая строка Книги -> dict, с которым безопасно работать.

    Книга ОБЩАЯ и append-only, писателей несколько (recall_eval импортирует
    book_append прямо отсюда), и чужая строка не обязана быть объектом с
    моими типами. Раньше тут падало на трёх реальных формах (ломатель 02.09):
    json-массив/скаляр вместо объекта (`r.get` -> AttributeError) и `ts`
    эпохой-числом (`int[:10]` -> TypeError). Падение было не косметическим:
    book_render зовётся ИЗ book_append, поэтому --close успевал переписать
    заметки и дописать jsonl, а потом падал -- без зеркала и без счётчика.
    """
    if isinstance(raw, dict):
        return raw
    return {"_foreign": True, "subject": _cell(raw)}


def book_date(r):
    """Дата строки. Числовой ts/date у чужого писателя -- не повод падать."""
    for k in ("date", "ts"):
        v = r.get(k)
        if v in (None, ""):
            continue
        return _cell(v)[:10]
    return u""


def book_subject(r):
    """Своё поле subject, чужое topic, иначе хотя бы kind."""
    for k in ("subject", "topic", "kind"):
        if r.get(k):
            return _cell(r[k])
    return u""


def book_participants(r):
    p = r.get("participants")
    if isinstance(p, (list, tuple)):
        return u", ".join(_cell(x) for x in p)
    return _cell(p)


def book_append(entry, jsonl=None):
    jsonl = jsonl or BOOK_JSONL
    d = os.path.dirname(jsonl)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(jsonl, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    book_render(jsonl)


def book_read(jsonl=None):
    jsonl = jsonl or BOOK_JSONL
    if not os.path.isfile(jsonl):
        return []
    rows = []
    with io.open(jsonl, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(book_row(json.loads(line)))
            except ValueError:
                rows.append({"_unparsed": line})
    return rows


def book_render(jsonl=None):
    """Зеркало .md перегенерируется ЦЕЛИКОМ из jsonl (один источник истины)."""
    jsonl = jsonl or BOOK_JSONL
    rows = book_read(jsonl)
    out = [u"# Книга ошибок — журнал столкновений УТВЕРЖДЕНИЙ",
           u"",
           u"Автогенерация из `contradiction_book.jsonl` "
           u"(`memory_epistemic.py --book`). Руками не править.",
           u"",
           u"Одна строка = один конфликт: что с чем столкнулось, что победило, "
           u"чем доказано, кто закрыл.",
           u"", u"| дата | предмет | участники | победило | чем доказано | кто закрыл |",
           u"|---|---|---|---|---|---|"]
    for r in rows:
        if "_unparsed" in r:
            continue
        out.append(u"| %s | %s | %s | %s | %s | %s |" % (
            book_date(r),
            book_subject(r), book_participants(r),
            _cell(r.get("winner")), _cell(r.get("evidence")),
            _cell(r.get("closed_by") or r.get("source"))))
    out.append(u"")
    out.append(u"_записей: %d_" % len([r for r in rows if "_unparsed" not in r]))
    write_text_atomic(book_md_of(jsonl), u"\n".join(out))


# ===================== запись контракта ===================================

def default_valid_from(n):
    mod = (n.meta.get("modified") or "").strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", mod)
    if m:
        return m.group(1)
    try:
        ts = os.path.getctime(n.path)
    except OSError:
        ts = os.path.getmtime(n.path)
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def apply_fields(n, fields):
    """Хирургическая правка блока metadata. Ничего кроме нужных строк не трогает.

    -> (new_text, changed_bool, reason). reason:
        "ok"           есть что писать
        "nochange"     файл УЖЕ в нужном состоянии (идемпотентность)
        "no-frontmatter"  frontmatter не разобран -- писать НЕКУДА

    ⚠️ «нечего писать» и «некуда писать» -- РАЗНЫЕ вещи, и раньше они
    возвращались одинаково: файл без разобранного frontmatter молча получал
    вердикт «idempotent: all copies already carry these fields», хотя не нёс
    НИ ОДНОГО поля (ломатель 02.09). Ложная зелень такого рода хуже отказа.

    ⚠️ Сравниваем РЕНДЕР строки, а не разобранное значение: strip_q снимает
    кавычки, но не разэкранирует, поэтому у значения с '\\' или ':' (живой
    пример -- refuted_by = путь E:\\Obsidian\\...) прочитанное НИКОГДА не
    совпадало с задуманным, и каждый прогон переписывал файл, плодил
    .epibak-* и лишнюю строку в Книге (ломатель 02.09).
    """
    want = dict((k, v) for k, v in fields.items() if v not in (None, ""))
    front, indent = n.front, n.front["meta_indent"]
    meta_line, meta_last = front["meta_line"], front["meta_last"]
    key_line = front["meta_key_line"]

    if meta_line is None and n.close_idx < 0:
        return None, False, "no-frontmatter"

    rendered = dict((k, "%s%s: %s" % (indent, k, quote_if_needed(want[k])))
                    for k in want)
    if meta_line is not None and all(
            k in key_line and n.lines[key_line[k]] == rendered[k] for k in want):
        return None, False, "nochange"

    lines = list(n.lines)
    if meta_line is None:
        # metadata-блока нет -- создаём перед закрывающим '---'
        block = ["metadata:"] + [rendered[k] for k in EPI_KEYS if k in want]
        lines[n.close_idx:n.close_idx] = block
        return "\n".join(lines), True, "ok"

    inserts = []
    for k in EPI_KEYS:
        if k not in want:
            continue
        if k in key_line:
            lines[key_line[k]] = rendered[k]       # правка на месте
        else:
            inserts.append(rendered[k])            # добавка в конец подблока
    if inserts:
        at = (meta_last if meta_last is not None else meta_line) + 1
        lines[at:at] = inserts
    return "\n".join(lines), True, "ok"


def verify_yaml(text, path_hint):
    """Пере-парсит frontmatter. yaml импортируется ЛЕНИВО (--help мгновенный).
    Нет PyYAML -> структурная проверка своим парсером, честно об этом говорим."""
    sp = split_front(text)
    if sp is None:
        return False, "frontmatter lost"
    lines, close_idx = sp
    block = "\n".join(lines[1:close_idx])
    try:
        import yaml
    except ImportError:
        f = parse_front(lines, close_idx)
        ok = bool(f["top"].get("name")) or bool(f["meta"])
        return ok, "structural only (PyYAML absent)"
    try:
        data = yaml.safe_load(block)
    except Exception as exc:                       # noqa: BLE001 - любой YAML-сбой
        return False, "YAML error: %s" % exc
    if not isinstance(data, dict):
        return False, "frontmatter is not a mapping"
    return True, "yaml ok"


def backup(path):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = "%s.epibak-%s" % (path, stamp)
    with io.open(path, "rb") as src, io.open(dst, "wb") as out:
        out.write(src.read())
    return dst


# ===================== счётчик использования ==============================

def log_usage(event, outcome, actor="session"):
    try:
        row = {"ts": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
               "node": socket.gethostname(), "actor": actor,
               "event": event, "outcome": outcome}
        with io.open(USAGE_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except (IOError, OSError):
        pass                                        # счётчик не роняет работу


# ===================== команды ============================================

def cmd_lint(args):
    notes, skipped, pruned = scan(args.root)
    if not notes:
        # «0 записей» != «чисто»: чаще всего это опечатка в --root. Говорим
        # ОТДЕЛЬНО, существует ли корень, и в --json отдаём JSON, а не прозу
        # (ломатель 02.09: --lint --json на пустом корне печатал человеческую
        # строку, и потребитель ловил JSONDecodeError вместо пустого отчёта).
        exists = os.path.isdir(args.root)
        if args.json:
            sys.stdout.write(json.dumps(
                {"root": args.root, "root_exists": exists, "notes": 0,
                 "skipped": skipped, "pruned_dirs": pruned,
                 "undecodable": [], "broken_frontmatter": [],
                 "unreadable_files": [],
                 "findings": {"A": [], "B": [], "C": []},
                 "verdict": "no-notes"},
                ensure_ascii=True, indent=1, sort_keys=True) + "\n")
        else:
            say("memory_epistemic --lint: root=%s -- 0 notes (nothing to judge;"
                " root %s)"
                % (args.root, "exists but holds no memory/*.md"
                   if exists else "DOES NOT EXIST -- check --root"))
        log_usage("lint", "empty" if exists else "empty-root-missing",
                  args.actor)
        return 0
    df, per = build_index(notes)
    a, b, c = find_a(notes), find_b(notes, df, per), find_c(notes, df, per)
    total = len(a) + len(b) + len(c)
    # Запись, которая не декодируется, судится по мусору: маркеры в ней найти
    # нельзя, и «маркеров нет» читалось бы как «чисто». Называем её вслух.
    # Та же честность для битого frontmatter ('---' открыт и не закрыт: поля
    # невидимы машине) и для нечитаемых файлов (I/O): тихий скип любого из
    # них = невидимая копия, которая переживёт --close.
    undecodable = [n.path for n in notes if n.bad_utf8]
    broken_front = [n.path for n in notes if n.broken_front]
    unreadable = [n.path for n in notes if n.unreadable]

    if args.json:
        sys.stdout.write(json.dumps(
            {"root": args.root, "root_exists": True, "notes": len(notes),
             "skipped": skipped, "pruned_dirs": pruned,
             "undecodable": undecodable,
             "broken_frontmatter": broken_front,
             "unreadable_files": unreadable,
             "findings": {"A": a, "B": b, "C": c}},
            ensure_ascii=True, indent=1, sort_keys=True) + "\n")
        log_usage("lint", "findings=%d" % total, args.actor)
        return 2 if total else 0

    cap = None if args.all else 12
    say("memory_epistemic --lint")
    say("  root    : %s" % args.root)
    say("  notes   : %d judged, %d skipped (indexes/backups), "
        "%d stale-copy dirs pruned (.stversions/conflict trash)"
        % (len(notes), skipped, pruned))
    tombs = len([f for f in a if f["sub"] == "SELF-TOMBSTONE"])
    say("  findings: A=%d files / %d slugs (tomb=%d actionable, "
        "correction=%d)  B=%d  C=%d"
        % (len(a), len(set(f["slug"] for f in a)), tombs,
           len(a) - tombs, len(b), len(c)))
    if undecodable:
        say("  WARNING : %d note(s) are not valid UTF-8 -- judged on replacement"
            " chars, markers CANNOT be trusted there (--close refuses them):"
            % len(undecodable))
        for p in undecodable[:5]:
            say("      %s" % p)
    if broken_front:
        say("  WARNING : %d note(s) have BROKEN frontmatter ('---' opened, "
            "never closed) -- fields are invisible to the machine, "
            "--close refuses to write there:" % len(broken_front))
        for p in broken_front[:5]:
            say("      %s" % p)
    if unreadable:
        say("  WARNING : %d note(s) could NOT be read (I/O error) -- not "
            "judged at all; an invisible copy would survive --close:"
            % len(unreadable))
        for p in unreadable[:5]:
            say("      %s" % p)
    say("")

    say("[A-BODY-ONLY] refutation is in the TEXT, frontmatter is silent")
    if not a:
        say("  (none)")
    for f in (a if cap is None else a[:cap]):
        say("  - %-14s %s" % (f["sub"], f["slug"]))
        say("      markers : %s" % ",".join(f["markers"]))
        if f["replacement"]:
            say("      replaced-by(candidate): %s" % f["replacement"])
        say("      %s" % f["path"])
    if cap and len(a) > cap:
        say("  ... +%d more (use --all)" % (len(a) - cap))
    say("")

    say("[B-TWIN-CLUSTER] one note closed, same-subject twins still open")
    if not b:
        say("  (none)")
    for f in (b if cap is None else b[:cap]):
        say("  - closed: %s  [%s]" % (f["refuted"], f["refuted_state"]))
        for t in f["twins"][:6]:
            say("      OPEN twin: %-42s x%d copies score=%d shared=%s"
                % (t["slug"], len(t["paths"]), t["score"],
                   ascii_term(",".join(t["shared"]))))
    if cap and len(b) > cap:
        say("  ... +%d more (use --all)" % (len(b) - cap))
    say("")

    say("[C-POLARITY] same subject, opposite claims")
    if not c:
        say("  (none)")
    for f in (c if cap is None else c[:cap]):
        say("  - %s(%s)  VS  %s(%s)  axis=%s subject=%s score=%d shared=%s" % (
            f["a"]["slug"], f["a"]["polarity"],
            f["b"]["slug"], f["b"]["polarity"],
            f.get("axis", "state"),
            ascii_term(",".join(f.get("subject", []))),
            f["score"], ascii_term(",".join(f["shared"]))))
    if cap and len(c) > cap:
        say("  ... +%d more (use --all)" % (len(c) - cap))
    say("")

    if args.record and total:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d")
        # Книга ОБЩАЯ и append-only: перезаписывать её нельзя, значит дедуп
        # обязан жить в ключе. Ключ = ЯКОРЬ конфликта, без списка тёзок:
        # список меняется (появился тёзка, схлопнулись копии) и id вместе с
        # ним, а конфликт тот же. Префикс ловит и legacy-строки со старым id.
        existing = set()
        for r in book_read(args.book_file):
            cid0 = r.get("conflict_id") or ""
            if cid0:
                existing.add(cid0.split(":")[0] + ":" + cid0.split(":")[1]
                             if cid0.count(":") >= 1 else cid0)
        added = 0
        for f in b:
            cid = "B:%s" % f["refuted"]
            if cid in existing:
                continue
            existing.add(cid)
            book_append({
                "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "date": stamp, "conflict_id": cid, "kind": "B-TWIN-CLUSTER",
                "subject": f["refuted"],
                "participants": [f["refuted"]] + [t["slug"] for t in f["twins"]],
                "winner": "", "evidence": "detected by --lint, not yet judged",
                "resolution": "open", "closed_by": "",
                "source": "memory_epistemic",
                "node": socket.gethostname()}, args.book_file)
            added += 1
        say("  book: +%d open conflicts recorded" % added)

    say("verdict: %s" % ("FINDINGS (exit 2)" if total else "CLEAN (exit 0)"))
    log_usage("lint", "findings=%d" % total, args.actor)
    return 2 if total else 0


def cmd_close(args):
    notes, _skipped, _pruned = scan(args.root)
    targets = [n for n in notes if n.slug == args.close]
    if args.only_path:
        targets = [n for n in targets
                   if os.path.abspath(n.path) == os.path.abspath(args.only_path)]
    if not targets:
        say("close: slug not found: %s (root=%s)" % (args.close, args.root))
        log_usage("close", "not-found", args.actor)
        return 1
    if args.status not in VALID_STATUS:
        say("close: bad --status %s (allowed: %s)"
            % (args.status, "|".join(VALID_STATUS)))
        log_usage("close", "bad-status", args.actor)
        return 1

    date = args.date or datetime.datetime.now().strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        say("close: --date must be YYYY-MM-DD")
        log_usage("close", "bad-date", args.actor)
        return 1

    say("close: slug=%s status=%s date=%s copies=%d"
        % (args.close, args.status, date, len(targets)))

    # ФАЗА 1 -- проверить ВСЕ копии, НИЧЕГО не записав. Раньше запись шла по
    # ходу проверки, и отказ на 2-й копии оставлял 1-ю закрытой, остальные
    # живыми, Книгу пустой -- ровно класс «закрыли одну копию из четырёх»,
    # против которого инструмент написан (замер 02.09: probe1 -- projA closed,
    # projB-D open, exit 1). Теперь close = ВСЁ ИЛИ НИЧЕГО.
    plans, unchanged, refused = [], [], []
    for n in targets:
        fields = {
            "status": args.status,
            "valid_from": (n.meta.get("valid_from") or "").strip()
                          or default_valid_from(n),
            "valid_to": date,
            "superseded_by": args.superseded_by,
            "refuted_on": date if args.status == "refuted" else None,
            "refuted_by": (args.refuted_by or args.superseded_by)
                          if args.status == "refuted" else None,
        }
        if n.unreadable:
            # Файл не прочитался (лок/права): закрыть его нельзя, а закрыть
            # СОСЕДЕЙ без него -- значит молча оставить живую копию.
            refused.append((n.path, "cannot read the file (I/O error)"))
            continue
        if n.bad_utf8:
            # Запись не декодируется как UTF-8: write_text_atomic положил бы
            # обратно U+FFFD вместо текста, то есть СТЁР бы тело (ломатель
            # 02.09: файл в CP1251 после --close остался с одними ромбиками).
            refused.append((n.path,
                            "not valid UTF-8; would replace text with U+FFFD"))
            continue
        new_text, changed, why_change = apply_fields(n, fields)
        if not changed and why_change == "no-frontmatter":
            refused.append((n.path, "no parsable frontmatter, nowhere to write"))
            continue
        if not changed:
            unchanged.append(n.path)
            say("  = unchanged: %s" % n.path)
            continue
        ok, why = verify_yaml(new_text, n.path)
        if not ok:
            refused.append((n.path, why))
            continue
        plans.append((n, new_text, why))

    if refused:
        for path, why in refused:
            say("  ! REFUSED (%s): %s" % (why, path))
        say("verdict: REFUSED -- %d of %d copies cannot be written; NOTHING "
            "written (all-or-nothing: a partial close is the "
            "'closed 1 copy of 4' defect)" % (len(refused), len(targets)))
        log_usage("close", "refused=%d" % len(refused), args.actor)
        return 1

    if args.dry_run:
        for n, _new_text, why in plans:
            say("  ~ would write (%s): %s" % (why, n.path))
        say("dry-run: nothing written; would close %d of %d copies "
            "(%d already ok)" % (len(plans), len(targets), len(unchanged)))
        log_usage("close", "dry-run", args.actor)
        return 0

    # ФАЗА 2 -- все копии проверены, пишем все.
    changed_paths = []
    for n, new_text, why in plans:
        bak = backup(n.path)
        # BOM снят при чтении -- возвращаем его на место, иначе --close молча
        # менял бы кодировку файла заодно с полями.
        write_text_atomic(n.path, (u"﻿" + new_text) if n.bom else new_text)
        say("  + written (%s): %s" % (why, n.path))
        say("      backup: %s" % bak)
        changed_paths.append(n.path)

    if not changed_paths:
        say("idempotent: all %d copies already carry these fields; "
            "book NOT touched" % len(unchanged))
        log_usage("close", "idempotent", args.actor)
        return 0

    book_append({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "date": date,
        "conflict_id": "CLOSE:%s->%s" % (args.close, args.superseded_by or "-"),
        "kind": "CLOSED",
        "subject": args.subject or args.close,
        "participants": [args.close] + ([args.superseded_by]
                                        if args.superseded_by else []),
        "winner": args.superseded_by or "",
        "loser": args.close,
        "evidence": args.evidence or "",
        "resolution": args.status,
        "closed_by": args.actor,
        "node": socket.gethostname(),
        "source": "memory_epistemic",
        "files": changed_paths,
    }, args.book_file)
    say("book: +1 entry -> %s" % args.book_file)
    say("verdict: CLOSED %d copies" % len(changed_paths))
    log_usage("close", "closed=%d" % len(changed_paths), args.actor)
    return 0


def cmd_book(args):
    rows = book_read(args.book_file)
    if not rows:
        say("contradiction book is empty: %s" % args.book_file)
        log_usage("book", "empty", args.actor)
        return 0
    book_render(args.book_file)
    say("Contradiction book: %d entries" % len(rows))
    say("  jsonl : %s" % args.book_file)
    say("  mirror: %s" % book_md_of(args.book_file))
    say("")
    shown = rows[-args.limit:] if args.limit else rows
    for r in shown:
        if "_unparsed" in r:
            say("  ? unparsed line")
            continue
        say("  %s  [%s] %s" % (
            book_date(r) or u"?",
            _cell(r.get("resolution") or r.get("confidence") or "?"),
            ascii_term(book_subject(r))[:90]))
        parts = book_participants(r)
        if parts:
            say("      participants: %s" % ascii_term(parts)[:140])
        if r.get("source") and r.get("source") != "memory_epistemic":
            say("      written by: %s (foreign schema, shown as-is)"
                % _cell(r["source"]))
        if r.get("winner"):
            say("      winner: %s   closed_by: %s"
                % (_cell(r["winner"]), _cell(r.get("closed_by"))))
    log_usage("book", "entries=%d" % len(rows), args.actor)
    return 0


# ===================== main ===============================================

def build_parser():
    p = argparse.ArgumentParser(
        prog="memory_epistemic.py",
        description="Temporal edges for memory notes + contradiction book "
                    "(0 LLM, 0 network, disk only).")
    p.add_argument("--lint", action="store_true",
                   help="scan all memory notes for machine-invisible refutations")
    p.add_argument("--close", metavar="SLUG",
                   help="close a note: set status/valid_to/superseded_by")
    p.add_argument("--book", action="store_true", help="show contradiction book")
    p.add_argument("--superseded-by", dest="superseded_by", metavar="SLUG",
                   help="what replaces the closed note")
    p.add_argument("--refuted-by", dest="refuted_by", metavar="SLUG|SOURCE",
                   help="what refuted it (default: --superseded-by)")
    p.add_argument("--date", metavar="YYYY-MM-DD", help="closing date (default: today)")
    p.add_argument("--status", default="refuted",
                   help="active|refuted|superseded|stale-suspect (default refuted)")
    p.add_argument("--evidence", default="", help="proof text for the book entry")
    p.add_argument("--subject", default="", help="conflict subject for the book")
    p.add_argument("--only-path", dest="only_path",
                   help="close ONE copy instead of every copy of the slug")
    p.add_argument("--root", default=DEFAULT_ROOT, help="projects root to scan")
    p.add_argument("--book-file", dest="book_file", default=BOOK_JSONL,
                   help="contradiction book jsonl (tests/sandboxes override "
                        "it so they never write into the real book)")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="show what would be written, write nothing")
    p.add_argument("--json", action="store_true", help="--lint output as JSON")
    p.add_argument("--all", action="store_true", help="do not cap the report")
    p.add_argument("--record", action="store_true",
                   help="--lint also records open conflicts into the book")
    p.add_argument("--limit", type=int, default=20, help="--book: last N entries")
    p.add_argument("--actor", default="session", help="session|routine (counter)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.book:
        return cmd_book(args)
    if args.close:
        return cmd_close(args)
    if args.lint:
        return cmd_lint(args)
    build_parser().print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
