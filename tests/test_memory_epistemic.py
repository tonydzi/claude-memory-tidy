# -*- coding: utf-8 -*-
"""Регресс-сетка для memory_epistemic.py -- эпистемический слой памяти.

ЗАЧЕМ: прибор, который никогда не краснел, ничего не доказывает. Каждый кейс
сторожит КЛАСС, уже стоивший нам крови, а не «строчку кода»:
  1  пустой вход                 -- сетка не должна зеленеть на нуле данных
  2  отсутствующий путь          -- «не нашёл» != «упал»
  3  кривой UTF-8                -- один битый файл не роняет проход по 799
  4  SELF-TOMBSTONE              -- запись хоронит себя + замена по «см. [[X]]»
  5  CORRECTION-NOTE             -- ГЛАВНЫЙ кейс: запись, ФИКСИРУЮЩАЯ чужое
                                   опровержение, НЕ надгробие. На живых данных
                                   chatgpt-deep-research-dead-2026-07 ложно
                                   попадал в надгробия (жирный абзац читался как
                                   баннер) -- закрыли бы ЖИВУЮ верную запись.
  6  B-TWIN-CLUSTER              -- закрытая запись + живой тёзка
  7  C-POLARITY, маскировка «не» -- «не работает» не смеет читаться как «works»
  8  --close пишет поля          -- YAML валиден, ТЕЛО не тронуто, бэкап есть
  9  идемпотентность             -- второй прогон не пишет и не плодит Книгу
 10  все копии слага             -- ровно тот баг, ради которого всё писалось:
                                   опровержение обязано доехать до ВСЕХ копий
 11  чужая схема в Книге         -- книга ОБЩАЯ и append-only (recall_eval пишет
                                   evidence словарём); чужая строка не роняет
 12  файл без frontmatter        -- не крэш
 13  протухшие копии .stversions -- не судим версии Syncthing, иначе запись
                                   «противоречит» своей же вчерашней версии
 14a семья chatgpt-dr НА ФИКСТУРЕ -- ПОВЕДЕНИЕ детектора на заранее известном
                                   содержимом: надгробие, коррекция, тёзка
 14b закрытие полями             -- закрытая запись УХОДИТ из класса A и
                                   остаётся в B как [frontmatter]
 14c живой корпус, МЯГКО         -- инварианты, которые не протухают от штатной
                                   работы: скан не пуст, коррекция никогда не
                                   надгробие, запись с маркером либо закрыта,
                                   либо видна в A
 16  ПЕРЕВОРОТ ПОЛЯРНОСТИ        -- «не жив» / «not alive» / «не works» обязаны
                                   читаться как NEG. Дефект найден бисекцией
                                   02.09: сторожилась РОВНО одна форма
                                   («не работает»), смена глагола переворачивала
                                   вывод в pos
 17  РОСТЕР не утверждение       -- HUB/инвентарь не участвует в спорах
 18  ДВЕ ОСИ                     -- «нельзя» (запрет) не спорит с «жив» (состояние)
 19  ПОХОЖИЕ СЛОВА != ПРЕДМЕТ    -- предмет = терм в ОБОИХ слагах, а не общее
                                   слово в description
 20  СОСЕДНИЙ ПРЕДМЕТ            -- полярное слово в другой клаузе, чем предмет,
                                   утверждением о предмете не является
 21  ВСЁ ИЛИ НИЧЕГО              -- копия с битым frontmatter в середине списка
                                   не смеет оставлять «закрыли 1 копию из 4»:
                                   --close сперва проверяет ВСЕ копии, потом
                                   пишет; отказ = не записано НИЧЕГО
 22  --dry-run считает копии     -- печатает ЧИСЛО копий, которые затронет
                                   («would close N of M copies»), не пишет
 23  битый frontmatter в --lint  -- честная строка с ИМЕНЕМ файла (и в --json
                                   поле broken_frontmatter), не тихий скип
 24  нечитаемый файл             -- I/O-отказ не тихий скип: --lint называет
                                   файл вслух, --close по этому слагу
                                   отказывается писать вообще (невидимая копия
                                   пережила бы закрытие)

⚠️ ПОЧЕМУ 14 РАСПАЛСЯ НА ТРИ. Старый кейс 14 гонял ЖИВОЙ корпус и требовал, чтобы
в нём лежало НЕЗАКРЫТОЕ самонадгробие chatgpt-dr-zero-searches-fake-report.
02.09 систему применили по назначению -- запись закрыли полями (status: refuted,
valid_to 2026-08-04, superseded_by chatgpt-dr-mini-counter-lies; рядом лежит
.epibak-20260902-113036) -- и она честно ушла из класса A, потому что A это
«маркер в тексте, frontmatter МОЛЧИТ». Тест покраснел на ШТАТНОЙ РАБОТЕ
СИСТЕМЫ: он сторожил СОСТОЯНИЕ КОРПУСА вместо ПОВЕДЕНИЯ ДЕТЕКТОРА. Детектор был
исправен -- улика в 14b, где то же закрытие воспроизведено на фикстуре.

⚠️ КЕЙСЫ 17 и 19 ПРОВЕРЯЮТ ДВЕРЬ НАПРЯМУЮ. Мутационный замер 02.09: с
выпотрошенным ростер-гейтом и выпотрошенным subject_terms сетка давала 22/22
PASS -- сквозную пару добивали СОСЕДНИЕ ворота. Поэтому кейсы зовут is_roster и
subject_terms сами и требуют, чтобы НАСТОЯЩАЯ пара (railgun alpha/beta) при этом
осталась на месте: «ложных пар нет» на мёртвом find_c -- фальшивая зелень.

ВХОД: нет. ВЫХОД: PASS/FAIL построчно, exit 0 = всё зелено, exit 1 = есть красное.
Побочных эффектов нет: и корпус, и Книга ошибок, и счётчик уводятся в tempdir.
РЕЛЬСА: чистый stdlib, локальный диск. 0 LLM, 0 сети.
КТО ДЁРГАЕТ: scripts/regress_run.py (ночная сетка подхватывает _test_*.py сама),
             /tt Шаг 2 при правке memory_epistemic.py.
МУТАЦИОННЫЙ ЗАМЕР: ядро ломалось 6 способами на КОПИИ в скретчпаде (снят
             _neg_of; снят ростер-гейт; слиты оси; выпотрошен subject_terms;
             снята привязка к клаузе; T2 надгробия ослаблен до жирного абзаца).
             Убито 6/6, каждая мутация красит свой кейс; после отката 22/22.
updated: 2026-09-02
"""
import io
import json
import os
import shutil
import sys
import tempfile
import traceback
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import memory_epistemic as M  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    sys.stdout.write("%-46s %s%s\n" % (
        name, "PASS" if cond else "FAIL",
        ("  <- " + detail) if (detail and not cond) else ""))


def note(path, name, desc, body, meta_extra=""):
    """Пишет запись памяти в РЕАЛЬНОМ формате корпуса (включая 'metadata: '
    с висячим пробелом -- он есть во всех живых файлах)."""
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    txt = (u"---\n"
           u"name: %s\n"
           u"description: \"%s\"\n"
           u"metadata: \n"
           u"  node_type: memory\n"
           u"  type: project\n"
           u"  modified: 2026-07-26T00:58:05.850Z\n"
           u"%s"
           u"---\n\n%s\n" % (name, desc, meta_extra, body))
    io.open(path, "w", encoding="utf-8", newline="").write(txt)
    return path


def run_cli(argv):
    """Гоняет main() и возвращает (exit_code, stdout)."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = M.main(argv)
    except SystemExit as e:                       # argparse
        rc = e.code
    return rc, buf.getvalue()


def build_corpus(root):
    m = os.path.join(root, "projA", "memory")
    n2 = os.path.join(root, "projB", "memory")

    # 4: надгробие -- маркер в НАЧАЛЕ description + blockquote-баннер + «см. [[X]]»
    note(os.path.join(m, "widget-counter-lies.md"), "widget-counter-lies",
         u"⛔ ОПРОВЕРГНУТО 04.08: счётчик виджета пуст у всех connector-прогонов",
         u"> ⛔ **ОПРОВЕРГНУТО 04.08.2026 разбором backend'а** — "
         u"см. [[widget-counter-truth]]. Симптом реален, причина неверна.\n\n"
         u"Старый текст оставлен как след ошибки, connector widget backend.")

    # 6: живой тёзка того же предмета
    note(os.path.join(m, "widget-counter-truth.md"), "widget-counter-truth",
         u"Счётчик виджета не доказательство: судить по citations в backend "
         u"widget_state у connector-прогонов",
         u"Разбор backend connector widget_state citations.")

    # 5: КОРРЕКЦИЯ -- жирный абзац, а не blockquote; маркер в СЕРЕДИНЕ description
    note(os.path.join(m, "counter-correction-note.md"), "counter-correction-note",
         u"«0 citations» у виджета — НЕ доказательство отсутствия поиска "
         u"(опровергнуто 04.08); судить по citations в metadata",
         u"**⛔ Вывод от 26.07 «канал dead» ОПРОВЕРГНУТ 04.08 разбором "
         u"backend'а.** Классический [[prichina-kak-claim]]: причину объявил, "
         u"опровергнуть не пытался.")

    # 7: полярность
    note(os.path.join(m, "railgun-vendor-alpha.md"), "railgun-vendor-alpha",
         u"railgun вендор мёртв, канал не работает и не отвечает",
         u"Замер показал отказ railgun vendor.")
    note(os.path.join(m, "railgun-vendor-beta.md"), "railgun-vendor-beta",
         u"railgun вендор жив и работает, канал доступен",
         u"Замер показал живой railgun vendor.")

    # 10: тот же слаг во ВТОРОМ проекте (копия, до которой обязано доехать)
    note(os.path.join(n2, "widget-counter-lies.md"), "widget-counter-lies",
         u"⛔ ОПРОВЕРГНУТО 04.08: счётчик виджета пуст у всех connector-прогонов",
         u"> ⛔ **ОПРОВЕРГНУТО 04.08.2026** — см. [[widget-counter-truth]].")

    # 3: кривой UTF-8
    bad = os.path.join(m, "broken-bytes.md")
    io.open(bad, "wb").write(
        b"---\nname: broken-bytes\ndescription: \"x\"\nmetadata: \n"
        b"  node_type: memory\n---\n\n\xff\xfe \xc3\x28 invalid tail\n")

    # 12: файл вообще без frontmatter
    io.open(os.path.join(m, "no-frontmatter.md"), "w",
            encoding="utf-8").write(u"just prose, no yaml at all\n")

    # 13: протухшая копия в .stversions -- судить нельзя
    note(os.path.join(m, ".stversions", "widget-counter-lies.md"),
         "widget-counter-lies", u"stale syncthing version", u"stale copy")

    # 17: РОСТЕР -- инвентарь, а не утверждение (одно слово в заголовке списка)
    note(os.path.join(m, "hub-railgun-fleet.md"), "hub-railgun-fleet",
         u"HUB живых railgun вендоров: alpha (API, no auto-record), beta "
         u"(QR-pairing), gamma (3 ящика), delta (whitelist draft-first), "
         u"epsilon (ежедневный health watchdog), zeta (RED→alert), eta",
         u"Оглавление рельс railgun vendor.")

    # 18: ОСЬ РАЗРЕШЕНИЯ -- «нельзя» не спорит с «жив»
    note(os.path.join(m, "railgun-vendor-policy.md"), "railgun-vendor-policy",
         u"railgun вендор: врать про источник нельзя, запрещено слать "
         u"черновик без апрува",
         u"Политика railgun vendor.")

    # 19: ПОХОЖИЕ СЛОВА, РАЗНЫЕ ПРЕДМЕТЫ -- предмет назван только у одной
    note(os.path.join(m, "coilgun-probe-alpha.md"), "coilgun-probe-alpha",
         u"замер railgun-стенда: сам coilgun-пробник мёртв и не отвечает",
         u"Разбор coilgun probe.")

    # 20: ОБЩИЙ предмет, но полярное слово -- про СОСЕДНИЙ предмет той же
    # записи (стоит в другой клаузе, чем предмет). Единственный кейс, который
    # держится ТОЛЬКО на привязке к клаузе.
    note(os.path.join(m, "railgun-vendor-sidecar.md"), "railgun-vendor-sidecar",
         u"railgun вендор: замер стенда; отдельный sidecar-процесс сборки "
         u"мёртв и не отвечает",
         u"Разбор sidecar railgun vendor.")
    return m, n2


def build_family(root):
    """ФИКСТУРА семьи chatgpt-dr с ЗАРАНЕЕ ИЗВЕСТНЫМ содержимым.

    Кейс 14 раньше судил ЖИВОЙ корпус и требовал, чтобы в нём лежало НЕЗАКРЫТОЕ
    самонадгробие. 02.09 система отработала штатно -- запись закрыли полями
    (status: refuted, valid_to, superseded_by; рядом лежит .epibak-20260902) --
    и кейс покраснел на СОБСТВЕННОЙ УДАЧЕ. Проверять надо ПОВЕДЕНИЕ детектора,
    а состояние корпуса пусть меняется: живой корпус сторожит мягкий кейс 14b.
    """
    m = os.path.join(root, "fam", "memory")
    note(os.path.join(m, "chatgpt-dr-zero-searches-fake-report.md"),
         "chatgpt-dr-zero-searches-fake-report",
         u"⛔ ОПРОВЕРГНУТО 04.08: «0 citations · 0 searches» НЕ значит «писал "
         u"по памяти» — счётчик пуст у всех connector-прогонов",
         u"> ⛔ **ОПРОВЕРГНУТО 04.08.2026 разбором backend'а** — "
         u"см. [[chatgpt-dr-mini-counter-lies]]. Симптом реален, причина "
         u"названа неверно.\n\nСтарый текст оставлен как след ошибки: "
         u"widget_state citations searches connector backend.")
    note(os.path.join(m, "chatgpt-deep-research-dead-2026-07.md"),
         "chatgpt-deep-research-dead-2026-07",
         u"«0 citations · 0 searches» у ChatGPT DR — НЕ доказательство "
         u"отсутствия поиска (опровергнуто 04.08); судить по citations в "
         u"metadata",
         u"**⛔ Вывод от 26.07 «ChatGPT DR не ищет, канал dead» ОПРОВЕРГНУТ "
         u"04.08 разбором backend'а.** Симптом был реален, причина названа "
         u"неверно: widget_state citations searches connector.")
    note(os.path.join(m, "chatgpt-dr-mini-counter-lies.md"),
         "chatgpt-dr-mini-counter-lies",
         u"Счётчик над виджетом врёт: citations лежат в backend widget_state, "
         u"настоящая деградация — deep-research-mini и обрыв плана",
         u"Разбор backend widget_state citations searches connector.")
    return m


def main():
    tmp = tempfile.mkdtemp(prefix="epi_test_")
    real_usage = M.USAGE_LOG
    M.USAGE_LOG = os.path.join(tmp, "_usage.jsonl")   # не пачкаем живой счётчик
    book = os.path.join(tmp, "book.jsonl")
    try:
        # --- 1: пустой вход ------------------------------------------------
        empty = os.path.join(tmp, "empty")
        os.makedirs(empty)
        rc, out = run_cli(["--lint", "--root", empty, "--book-file", book])
        check("01 empty root -> exit 0, no crash",
              rc == 0 and "0 notes" in out, "rc=%s out=%r" % (rc, out[:120]))

        # --- 2: отсутствующий путь ----------------------------------------
        rc, out = run_cli(["--lint", "--root", os.path.join(tmp, "nope"),
                           "--book-file", book])
        check("02 missing root -> exit 0, no traceback",
              rc == 0 and "Traceback" not in out, "rc=%s" % rc)

        m, n2 = build_corpus(tmp)

        # --- 3: кривой UTF-8 -----------------------------------------------
        notes, skipped, pruned = M.scan(tmp)
        slugs = [n.slug for n in notes]
        check("03 broken utf-8 survives scan",
              "broken-bytes" in slugs and len(notes) >= 7,
              "slugs=%s" % slugs)

        # --- 13: .stversions отсеян ----------------------------------------
        stale = [n for n in notes if ".stversions" in n.path]
        check("13 .stversions pruned (not judged)",
              not stale and pruned >= 1, "stale=%s pruned=%s" % (stale, pruned))

        # --- 12: без frontmatter -------------------------------------------
        check("12 no-frontmatter file does not crash",
              "no-frontmatter" in slugs, "slugs=%s" % slugs)

        df, per = M.build_index(notes)
        a = M.find_a(notes)
        by = dict((f["slug"], f) for f in a)

        # --- 4: SELF-TOMBSTONE + замена ------------------------------------
        t = by.get("widget-counter-lies")
        check("04 self-tombstone detected + replacement",
              t and t["sub"] == "SELF-TOMBSTONE"
              and t["replacement"] == "widget-counter-truth",
              "got=%r" % ((t and (t["sub"], t["replacement"])),))

        # --- 5: CORRECTION-NOTE не путается с надгробием --------------------
        c = by.get("counter-correction-note")
        check("05 correction-note is NOT a tombstone",
              c and c["sub"] == "CORRECTION-NOTE",
              "got=%s" % (c and c["sub"]))

        # --- 6: B-TWIN-CLUSTER ---------------------------------------------
        b = M.find_b(notes, df, per)
        twins = []
        for f in b:
            if f["refuted"] == "widget-counter-lies":
                twins = [t2["slug"] for t2 in f["twins"]]
        check("06 twin cluster finds the OPEN sibling",
              "widget-counter-truth" in twins, "twins=%s" % twins)

        # --- 7: полярность + маскировка отрицания ---------------------------
        pol = M.find_c(notes, df, per)
        pair = set()
        for f in pol:
            pair.add(tuple(sorted([f["a"]["slug"], f["b"]["slug"]])))
        ok_pair = ("railgun-vendor-alpha", "railgun-vendor-beta") in pair
        neg_ok = M.polarity(u"канал не работает и не отвечает") == "neg"
        check("07 polarity pair + 'ne rabotaet' masked as NEG",
              ok_pair and neg_ok, "pairs=%s neg=%s" % (pair, neg_ok))

        # --- 8: --close пишет поля, YAML валиден, тело цело ------------------
        target = os.path.join(m, "widget-counter-lies.md")
        before_body = io.open(target, encoding="utf-8").read().split("---", 2)[2]
        rc, out = run_cli(["--close", "widget-counter-lies",
                           "--superseded-by", "widget-counter-truth",
                           "--date", "2026-08-04", "--root", tmp,
                           "--book-file", book])
        after = io.open(target, encoding="utf-8").read()
        after_body = after.split("---", 2)[2]
        fm_ok = True
        try:
            import yaml
            d = yaml.safe_load(after.split("---")[1])
            fm_ok = (isinstance(d, dict)
                     and d["metadata"]["status"] == "refuted"
                     and str(d["metadata"]["valid_to"]) == "2026-08-04"
                     and d["metadata"]["superseded_by"] == "widget-counter-truth"
                     and str(d["metadata"]["valid_from"]) == "2026-07-26"
                     and d["metadata"]["node_type"] == "memory")
        except ImportError:
            fm_ok = "status: refuted" in after
        baks = [f for f in os.listdir(m) if ".epibak-" in f]
        check("08 close writes fields, yaml ok, body untouched, backup",
              rc == 0 and fm_ok and before_body == after_body and baks,
              "rc=%s fm=%s body_same=%s baks=%d"
              % (rc, fm_ok, before_body == after_body, len(baks)))

        # --- 10: доехало до ВСЕХ копий слага --------------------------------
        other = io.open(os.path.join(n2, "widget-counter-lies.md"),
                        encoding="utf-8").read()
        check("10 refutation reached the OTHER project copy",
              "status: refuted" in other and "valid_to: 2026-08-04" in other,
              "second copy not updated")

        # --- 9: идемпотентность ---------------------------------------------
        lines_before = len(io.open(book, encoding="utf-8").readlines())
        sha_before = io.open(target, encoding="utf-8").read()
        rc2, out2 = run_cli(["--close", "widget-counter-lies",
                             "--superseded-by", "widget-counter-truth",
                             "--date", "2026-08-04", "--root", tmp,
                             "--book-file", book])
        lines_after = len(io.open(book, encoding="utf-8").readlines())
        sha_after = io.open(target, encoding="utf-8").read()
        baks2 = [f for f in os.listdir(m) if ".epibak-" in f]
        check("09 second close: no write, no new book line, no new backup",
              rc2 == 0 and sha_before == sha_after
              and lines_before == lines_after and len(baks) == len(baks2),
              "rc=%s file_same=%s book %s->%s baks %s->%s"
              % (rc2, sha_before == sha_after, lines_before, lines_after,
                 len(baks), len(baks2)))

        # --- 11: чужая схема в общей Книге не роняет рендер -------------------
        with io.open(book, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": "2026-09-02T08:44:19Z", "source": "recall_eval",
                "kind": "atom-mismatch", "topic": u"чужая строка",
                "evidence": {"frame_overlap": 0.67},
                "confidence": "candidate"}, ensure_ascii=False) + "\n")
        rc3, out3 = run_cli(["--book", "--book-file", book])
        md = io.open(M.book_md_of(book), encoding="utf-8").read()
        check("11 foreign-schema row renders, does not crash",
              rc3 == 0 and "recall_eval" in out3 and "frame_overlap" in md,
              "rc=%s" % rc3)

        # --- 14a: семья chatgpt-dr НА ФИКСТУРЕ (жёстко) -----------------------
        fam_root = os.path.join(tmp, "family")
        build_family(fam_root)
        fnotes, _s, _p = M.scan(fam_root)
        fdf, fper = M.build_index(fnotes)
        fa = M.find_a(fnotes)
        fb = M.find_b(fnotes, fdf, fper)
        tomb = [f for f in fa
                if f["slug"] == "chatgpt-dr-zero-searches-fake-report"
                and f["sub"] == "SELF-TOMBSTONE"]
        corr = [f for f in fa
                if f["slug"] == "chatgpt-deep-research-dead-2026-07"
                and f["sub"] == "CORRECTION-NOTE"]
        ftw = []
        for f in fb:
            if f["refuted"] == "chatgpt-dr-zero-searches-fake-report":
                ftw = [t2["slug"] for t2 in f["twins"]]
        check("14a fixture: chatgpt-dr family read exactly right",
              len(tomb) == 1 and len(corr) == 1
              and tomb[0]["replacement"] == "chatgpt-dr-mini-counter-lies"
              and "chatgpt-dr-mini-counter-lies" in ftw,
              "tomb=%d corr=%d repl=%s twins=%s"
              % (len(tomb), len(corr),
                 tomb[0]["replacement"] if tomb else None, ftw))

        # --- 14b: закрытие полями УБИРАЕТ находку из A и оставляет её в B -----
        # Ровно то, что 02.09 произошло с живой записью и от чего покраснел
        # старый кейс 14: исчезновение из A -- ПРАВИЛЬНОЕ поведение, а не слепота.
        rcf, _o = run_cli(["--close", "chatgpt-dr-zero-searches-fake-report",
                           "--superseded-by", "chatgpt-dr-mini-counter-lies",
                           "--date", "2026-08-04", "--root", fam_root,
                           "--book-file", book])
        f2, _s, _p = M.scan(fam_root)
        df2, per2 = M.build_index(f2)
        a2 = [f for f in M.find_a(f2)
              if f["slug"] == "chatgpt-dr-zero-searches-fake-report"]
        b2 = [f for f in M.find_b(f2, df2, per2)
              if f["refuted"] == "chatgpt-dr-zero-searches-fake-report"]
        check("14b closing by fields removes it from A, keeps it in B",
              rcf == 0 and not a2 and len(b2) == 1
              and b2[0]["refuted_state"] == "frontmatter",
              "rc=%s A=%d B=%d state=%s"
              % (rcf, len(a2), len(b2),
                 b2[0]["refuted_state"] if b2 else None))

        # --- 14c: ЖИВОЙ корпус -- мягкие инварианты ПОВЕДЕНИЯ -----------------
        # Не «в корпусе лежит вот такая запись» (это протухает от штатной работы
        # системы), а «детектор не ослеп и не путает классы, что бы там ни лежало».
        live = M.DEFAULT_ROOT
        if not os.path.isdir(live):
            check("14c live corpus: detector not blind, classes not mixed", True)
            sys.stdout.write("   (14c SKIPPED: live corpus absent on this node)\n")
        else:
            lnotes, _s, _p = M.scan(live)
            lby = {}
            for n in lnotes:
                lby.setdefault(n.slug, n)
            la = M.find_a(lnotes)
            seen_a = set((f["slug"], f["sub"]) for f in la)
            bad = []
            if not lnotes:
                bad.append("scan returned 0 notes")
            # корректирующая заметка НИКОГДА не надгробие (класс, стоивший крови)
            for slug in ("chatgpt-deep-research-dead-2026-07",
                         "counter-correction-note"):
                if slug in lby and (slug, "SELF-TOMBSTONE") in seen_a:
                    bad.append(slug + " read as SELF-TOMBSTONE")
            # запись с маркером обязана быть ЛИБО закрыта полями, ЛИБО видна в A
            for slug, n in lby.items():
                if n.markers and not n.is_closed() and slug not in \
                        set(f["slug"] for f in la):
                    bad.append(slug + " has markers but is invisible")
            check("14c live corpus: detector not blind, classes not mixed",
                  not bad, "; ".join(bad[:3]))

        # --- 16: ОТРИЦАНИЕ ПОЛОЖИТЕЛЬНОГО (дефект, найденный бисекцией) -------
        inv = [(u"канал не работает", "neg"), (u"канал не живой", "neg"),
               (u"коннектор больше не жив", "neg"),
               (u"the rail is not alive", "neg"),
               (u"это не works", "neg"), (u"рельса жива", "pos"),
               (u"не только жив, но и отвечает", "pos")]
        wrong = [(M.ascii_term(t), M.polarity(t), w)
                 for t, w in inv if M.polarity(t) != w]
        check("16 negated POSITIVE reads as NEG (no inversion)",
              not wrong, "%s" % (wrong[:3],))

        # Ниже 17-19: каждый кейс требует, чтобы НАСТОЯЩАЯ пара осталась НА
        # МЕСТЕ. Иначе «ложных пар нет» зеленело бы и на выпотрошенном find_c.
        pol2 = set(tuple(sorted([f["a"]["slug"], f["b"]["slug"]]))
                   for f in M.find_c(notes, df, per))
        TRUE_PAIR = ("railgun-vendor-alpha", "railgun-vendor-beta")

        # --- 17: РОСТЕР не судится -------------------------------------------
        # Сквозной кейс мало что доказывает: пару всё равно добивают другие
        # ворота (мутационный замер 02.09 -- выключенный ростер-гейт давал
        # 22/22 PASS). Поэтому здесь ЕЩЁ И прямая проверка самой двери,
        # ОБЕИХ её веток: короткий HUB (по слагу) и длинное перечисление.
        short_hub = M.Note()
        short_hub.slug, short_hub.desc, short_hub.meta = \
            "hub-railgun", u"HUB railgun: alpha, beta", {}
        long_list = M.Note()
        long_list.slug, long_list.meta = "railgun-vendor-alpha", {}
        long_list.desc = (u"railgun вендор жив: alpha (official API, no "
                          u"auto-record), beta (QR-pairing, ручной вход), "
                          u"gamma (3 ящика a/a2/bb), delta (whitelist "
                          u"draft-first), epsilon (ежедневный health "
                          u"watchdog), zeta (RED alert в шину), eta "
                          u"(draft-first), theta (ban/FloodWait), iota "
                          u"(SSE-демон), kappa (stdio), lambda (архив)")
        claim = M.Note()
        claim.slug, claim.desc, claim.meta = \
            "railgun-vendor-beta", u"railgun вендор жив и работает", {}
        check("17 roster/HUB inventory is not a claim",
              TRUE_PAIR in pol2
              and not any("hub-railgun-fleet" in p for p in pol2)
              and M.is_roster(short_hub) and M.is_roster(long_list)
              and not M.is_roster(claim),
              "pairs=%s short=%s long=%s claim=%s"
              % (pol2, M.is_roster(short_hub), M.is_roster(long_list),
                 M.is_roster(claim)))

        # --- 18: разные ОСИ не спорят ----------------------------------------
        check("18 permission axis never pairs with state axis",
              TRUE_PAIR in pol2
              and not any("railgun-vendor-policy" in p for p in pol2)
              and M.polarity_hits(u"врать нельзя").get("perm", (None,))[0]
              == "neg" and M.polarity(u"врать нельзя") is None,
              "pairs=%s" % (pol2,))

        # --- 19: похожие слова != общий предмет ------------------------------
        # Та же беда, что у 17: сквозная пара умирает и без этих ворот, поэтому
        # дверь проверяется НАПРЯМУЮ -- иначе выпотрошенный subject_terms
        # зеленел (мутационный замер 02.09).
        subj_ok = (
            M.subject_terms(set(["railgun", "vendor", "alpha"]),
                            set(["railgun", "vendor", "beta"]))
            == set(["railgun", "vendor"])
            # грамматика в слаге -- НЕ предмет
            and M.subject_terms(set(["probe", "must", "not"]),
                                set(["stand", "must", "not"])) == set()
            # короткий хвост слага -- НЕ предмет
            and M.subject_terms(set(["dr2", "api"]), set(["dr2", "api"])) == set()
            # разные предметы с похожими словами
            and M.subject_terms(set(["coilgun", "probe", "alpha"]),
                                set(["railgun", "vendor", "beta"])) == set())
        check("19 similar words, different subject -> no pair",
              TRUE_PAIR in pol2
              and not any("coilgun-probe-alpha" in p for p in pol2)
              and subj_ok,
              "pairs=%s subject_terms_ok=%s" % (pol2, subj_ok))

        # --- 20: полярное слово про СОСЕДНИЙ предмет той же записи -----------
        check("20 polarity word in another clause -> not about the subject",
              TRUE_PAIR in pol2
              and not any("railgun-vendor-sidecar" in p for p in pol2),
              "pairs=%s" % (pol2,))

        # --- 21: КОПИЯ С БИТЫМ FRONTMATTER -- close = ВСЁ ИЛИ НИЧЕГО ----------
        # Класс «закрыли одну копию из четырёх»: раньше отказ на 2-й копии
        # оставлял 1-ю ЗАКРЫТОЙ, остальные живыми, Книгу пустой (замер 02.09
        # probe1: projA closed / projB-D open, exit 1).
        aor = os.path.join(tmp, "allornothing")
        for proj in ("p1", "p2", "p3"):
            note(os.path.join(aor, proj, "memory", "dead-rail.md"), "dead-rail",
                 u"⛔ ОПРОВЕРГНУТО 04.08: вывод неверен",
                 u"> ⛔ **ОПРОВЕРГНУТО 04.08.2026** — см. [[live-rail]].")
        brk = os.path.join(aor, "p2broken", "memory", "dead-rail.md")
        os.makedirs(os.path.dirname(brk))
        broken_txt = (u"---\nname: dead-rail\ndescription: \"x\"\nmetadata: \n"
                      u"  node_type: memory\n\nтело; закрывающего --- нет\n")
        io.open(brk, "w", encoding="utf-8", newline="").write(broken_txt)
        blines = (len(io.open(book, encoding="utf-8").readlines())
                  if os.path.isfile(book) else 0)
        rc, out = run_cli(["--close", "dead-rail",
                           "--superseded-by", "live-rail",
                           "--date", "2026-08-04", "--root", aor,
                           "--book-file", book])
        touched = [p for p in ("p1", "p2", "p3")
                   if "status: refuted" in io.open(
                       os.path.join(aor, p, "memory", "dead-rail.md"),
                       encoding="utf-8").read()]
        blines2 = (len(io.open(book, encoding="utf-8").readlines())
                   if os.path.isfile(book) else 0)
        check("21 broken copy -> close refuses ALL (all-or-nothing)",
              rc == 1 and "REFUSED" in out and not touched
              and blines == blines2,
              "rc=%s touched=%s out=%r" % (rc, touched, out[-250:]))

        # --- 22: --dry-run печатает ЧИСЛО копий, которые затронет -------------
        os.remove(brk)
        rc, out = run_cli(["--close", "dead-rail",
                           "--superseded-by", "live-rail",
                           "--date", "2026-08-04", "--root", aor,
                           "--book-file", book, "--dry-run"])
        untouched = all("status: refuted" not in io.open(
            os.path.join(aor, p, "memory", "dead-rail.md"),
            encoding="utf-8").read() for p in ("p1", "p2", "p3"))
        check("22 dry-run names the copy count, writes nothing",
              rc == 0 and "would close 3 of 3 copies" in out and untouched,
              "rc=%s out=%r" % (rc, out[-250:]))

        # --- 23: битый frontmatter -- честная строка с ИМЕНЕМ файла в --lint --
        io.open(brk, "w", encoding="utf-8", newline="").write(broken_txt)
        rc, out = run_cli(["--lint", "--root", aor, "--book-file", book])
        rcj, outj = run_cli(["--lint", "--root", aor, "--book-file", book,
                             "--json"])
        try:
            j = json.loads(outj)
        except ValueError:
            j = {}
        check("23 lint names the broken-frontmatter file out loud",
              "BROKEN frontmatter" in out and brk in out
              and j.get("broken_frontmatter") == [brk],
              "json=%s out=%r" % (j.get("broken_frontmatter"), out[:400]))

        # --- 24: нечитаемый файл -- не тихий скип, а заглушка с именем --------
        # Настоящий I/O-лок на Windows дёшево не воспроизвести -- поднимаем его
        # руками: read_text падает ровно на одной копии. Невидимая копия --
        # ровно та, что раньше «переживала» закрытие молча.
        os.remove(brk)
        locked = os.path.join(aor, "p3", "memory", "dead-rail.md")
        real_read = M.read_text
        def _boom(path, _lock=os.path.abspath(locked)):
            if os.path.abspath(path) == _lock:
                raise IOError("simulated lock")
            return real_read(path)
        M.read_text = _boom
        try:
            rc, out = run_cli(["--lint", "--root", aor, "--book-file", book])
            rc2, out2 = run_cli(["--close", "dead-rail",
                                 "--superseded-by", "live-rail",
                                 "--date", "2026-08-04", "--root", aor,
                                 "--book-file", book])
        finally:
            M.read_text = real_read
        still_open = all("status: refuted" not in io.open(
            os.path.join(aor, p, "memory", "dead-rail.md"),
            encoding="utf-8").read() for p in ("p1", "p2", "p3"))
        check("24 unreadable copy: lint names it, close refuses all",
              "could NOT be read" in out and locked in out
              and rc2 == 1 and "REFUSED" in out2 and still_open,
              "rc2=%s still_open=%s out=%r out2=%r"
              % (rc2, still_open, out[:400], out2[-250:]))

        # --- счётчик пишется -------------------------------------------------
        check("15 usage counter written",
              os.path.isfile(M.USAGE_LOG)
              and len(io.open(M.USAGE_LOG, encoding="utf-8").readlines()) >= 5,
              "counter missing")

    except Exception:
        traceback.print_exc()
        check("XX unexpected exception", False, "see traceback")
    finally:
        M.USAGE_LOG = real_usage
        shutil.rmtree(tmp, ignore_errors=True)

    bad = [n for n, ok, _d in RESULTS if not ok]
    sys.stdout.write("\n%d/%d PASS\n" % (len(RESULTS) - len(bad), len(RESULTS)))
    if bad:
        sys.stdout.write("FAILED: %s\n" % ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
