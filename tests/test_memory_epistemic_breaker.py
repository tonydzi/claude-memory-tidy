# -*- coding: utf-8 -*-
"""Регресс-сетка ЛОМАТЕЛЯ для memory_epistemic.py -- классы, найденные 02.09.

ЗАЧЕМ ОТДЕЛЬНЫЙ ФАЙЛ: _test_memory_epistemic.py -- сетка автора, она сторожит
ЗАМЫСЕЛ (находит ли линтер семью chatgpt-dr, доезжает ли --close до всех копий).
Эта сторожит то, что автор проверял на удобных данных и что зеленело на
выпотрошенном коде. Мутационный замер 02.09 по авторской сетке: выпотрошенные
verify_yaml и quote_if_needed давали 15/15 PASS -- то есть обе заявленные
страховки записи не были прикрыты НИ ОДНИМ тестом.

КЛАССЫ (каждый = реальный прогон, который до починки падал или врал):
  B1 CP1251-запись            --close переписывал ТЕЛО ромбиками U+FFFD и
                              рапортовал CLOSED (bad_utf8 знали и не смотрели)
  B2 BOM                      lines[0] == '\ufeff---' => frontmatter не найден:
                              надгробие деградировало в correction-note, а
                              --close врал «idempotent» (PowerShell Out-File
                              по умолчанию пишет UTF-8 с BOM -- это наш флот)
  B3 нет frontmatter          «нечего писать» и «НЕКУДА писать» были одним
                              ответом => ложная зелень «all copies already
                              carry these fields» на файле без единого поля
  B4 идемпотентность значений strip_q снимает кавычки, но не разэкранирует =>
                              refuted_by с '\' или ':' переписывался КАЖДЫЙ
                              прогон, плодя .epibak-* и дубли в Книге
  B5 чужая строка Книги       json-массив / скаляр / ts эпохой-числом роняли
                              рендер. Книга ОБЩАЯ, той же дверью ходит
                              recall_eval (он импортирует book_append отсюда)
  B6 крах внутри book_append  рендер зовётся ИЗ append => --close успевал
                              переписать заметки и jsonl, а потом падал:
                              без зеркала, без счётчика, exit 1
  B7 --json на пустом корне   печаталась проза вместо JSON => потребитель ловил
                              JSONDecodeError; опечатка в --root была
                              неотличима от «чисто»
  B8 verify_yaml -- страховка отказ писать невалидный YAML обязан РАБОТАТЬ,
                              а не только быть описанным в docstring
  B9 quote_if_needed          значение с ':' обязано уехать в кавычках, иначе
                              frontmatter перестаёт быть mapping

ВХОД: нет. ВЫХОД: PASS/FAIL построчно, exit 0 = зелено, exit 1 = есть красное.
Побочных эффектов нет: корпус, Книга и счётчик уводятся в tempdir.
РЕЛЬСА: чистый stdlib, локальный диск. 0 LLM, 0 сети, 0 токенов.
КТО ДЁРГАЕТ: scripts/regress_run.py (ночная сетка ловит _test_*.py сама),
             /tt Шаг 2 при правке memory_epistemic.py.
updated: 2026-09-02
"""
import io
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
    sys.stdout.write("%-52s %s%s\n" % (
        name, "PASS" if cond else "FAIL",
        ("  <- " + detail) if (detail and not cond) else ""))


def run_cli(argv):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = M.main(argv)
    except SystemExit as e:
        rc = e.code
    return rc, buf.getvalue()


def plain(path, name, desc=u"x", extra=u""):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(path, "w", encoding="utf-8", newline="").write(
        u"---\nname: %s\ndescription: \"%s\"\nmetadata: \n"
        u"  node_type: memory\n  modified: 2026-07-26T00:58:05.850Z\n"
        u"%s---\n\nbody\n" % (name, desc, extra))
    return path


def main():
    tmp = tempfile.mkdtemp(prefix="epi_brk_")
    real_usage = M.USAGE_LOG
    M.USAGE_LOG = os.path.join(tmp, "_usage.jsonl")
    book = os.path.join(tmp, "book.jsonl")
    m = os.path.join(tmp, "p", "memory")
    os.makedirs(m)
    try:
        # --- B1: запись не в UTF-8 -----------------------------------------
        cp = os.path.join(m, "cp1251-note.md")
        io.open(cp, "wb").write(
            (u"---\nname: cp1251-note\ndescription: \"\u0437\u0430\u043f\u0438"
             u"\u0441\u044c\"\nmetadata: \n  node_type: memory\n---\n\n"
             u"\u0422\u0435\u043b\u043e \u0432 CP1251.\n").encode("cp1251"))
        before = io.open(cp, "rb").read()
        rc, out = run_cli(["--close", "cp1251-note", "--superseded-by", "x",
                           "--root", tmp, "--book-file", book])
        after = io.open(cp, "rb").read()
        check("B1 close REFUSES a non-UTF-8 note (no U+FFFD wipe)",
              rc == 1 and "REFUSED" in out and before == after
              and b"\xef\xbf\xbd" not in after,
              "rc=%s bytes_same=%s" % (rc, before == after))

        # --- B2: BOM -------------------------------------------------------
        bom = os.path.join(m, "bom-note.md")
        io.open(bom, "wb").write(b"\xef\xbb\xbf" + (
            u"---\nname: bom-note\ndescription: \"\u26d4 \u041e\u041f\u0420"
            u"\u041e\u0412\u0415\u0420\u0413\u041d\u0423\u0422\u041e 04.08: "
            u"bom widget connector\"\nmetadata: \n  node_type: memory\n"
            u"  modified: 2026-07-26T00:58:05.850Z\n---\n\n"
            u"> \u26d4 \u041e\u041f\u0420\u041e\u0412\u0415\u0420\u0413\u041d"
            u"\u0423\u0422\u041e bom body\n").encode("utf-8"))
        n = M.load_note(bom)
        check("B2a BOM note: frontmatter parsed, not swallowed",
              n.front["meta_line"] is not None and n.slug == "bom-note",
              "meta_line=%s slug=%s" % (n.front["meta_line"], n.slug))
        tomb = [f for f in M.find_a([n]) if f["sub"] == "SELF-TOMBSTONE"]
        check("B2b BOM note still reads as SELF-TOMBSTONE", bool(tomb),
              "got=%s" % [f["sub"] for f in M.find_a([n])])
        rc, out = run_cli(["--close", "bom-note", "--superseded-by", "y",
                           "--date", "2026-08-04", "--root", tmp,
                           "--book-file", book])
        raw = io.open(bom, "rb").read()
        check("B2c BOM note actually written, BOM preserved",
              rc == 0 and raw[:3] == b"\xef\xbb\xbf"
              and b"status: refuted" in raw,
              "rc=%s bom=%s" % (rc, raw[:3]))
        md5a = io.open(bom, "rb").read()
        run_cli(["--close", "bom-note", "--superseded-by", "y",
                 "--date", "2026-08-04", "--root", tmp, "--book-file", book])
        check("B2d BOM note close is byte-idempotent",
              md5a == io.open(bom, "rb").read(), "second run changed bytes")

        # --- B3: нет frontmatter -------------------------------------------
        bare = os.path.join(m, "bare.md")
        io.open(bare, "w", encoding="utf-8").write(u"just prose\n")
        rc, out = run_cli(["--close", "bare", "--superseded-by", "x",
                           "--root", tmp, "--book-file", book])
        check("B3 no-frontmatter REFUSES, never claims 'idempotent'",
              rc == 1 and "REFUSED" in out and "idempotent" not in out,
              "rc=%s out=%r" % (rc, out[-160:]))

        # --- B4: идемпотентность на значении с '\' и ':' --------------------
        plain(os.path.join(m, "winpath-note.md"), "winpath-note")
        argv = ["--close", "winpath-note", "--status", "refuted",
                "--refuted-by", u"E:\\Obsidian\\Anton-Knowledge\\note.md",
                "--root", tmp, "--book-file", book]
        run_cli(argv)
        b1 = len(io.open(book, encoding="utf-8").readlines())
        f1 = io.open(os.path.join(m, "winpath-note.md"), "rb").read()
        k1 = len([x for x in os.listdir(m) if ".epibak-" in x])
        rc, out = run_cli(argv)
        f2 = io.open(os.path.join(m, "winpath-note.md"), "rb").read()
        b2 = len(io.open(book, encoding="utf-8").readlines())
        k2 = len([x for x in os.listdir(m) if ".epibak-" in x])
        check("B4 backslash/colon value: 2nd close writes nothing",
              f1 == f2 and b1 == b2 and k1 == k2 and "idempotent" in out,
              "file_same=%s book %s->%s baks %s->%s" % (f1 == f2, b1, b2, k1, k2))

        # --- B5: чужие строки Книги ----------------------------------------
        hostile = os.path.join(tmp, "hostile.jsonl")
        io.open(hostile, "w", encoding="utf-8").write(
            u'{"ts": 1756800000, "source": "peer_x", "kind": "drift"}\n'
            u'["a","b"]\n'
            u'42\n'
            u'{"date": 20260902, "subject": 12345, "participants": {"a":1}}\n'
            u'not json at all\n')
        rc, out = run_cli(["--book", "--book-file", hostile])
        check("B5 foreign rows (int ts / array / scalar) do not crash",
              rc == 0 and "Traceback" not in out, "rc=%s" % rc)

        # --- B6: крах внутри book_append -----------------------------------
        plain(os.path.join(m, "victim.md"), "victim")
        poisoned = os.path.join(tmp, "poisoned.jsonl")
        io.open(poisoned, "w", encoding="utf-8").write(
            u'{"ts": 1756800000, "source": "peer_x"}\n')
        rc, out = run_cli(["--close", "victim", "--superseded-by", "z",
                           "--root", tmp, "--book-file", poisoned])
        mirror = M.book_md_of(poisoned)
        check("B6 close into a poisoned shared book completes + mirrors",
              rc == 0 and os.path.isfile(mirror), "rc=%s mirror=%s"
              % (rc, os.path.isfile(mirror)))

        # --- B7: --json на пустом/несуществующем корне -----------------------
        import json as _json
        empty = os.path.join(tmp, "empty")
        os.makedirs(empty)
        rc, out = run_cli(["--lint", "--json", "--root", empty,
                           "--book-file", book])
        ok_json = False
        try:
            ok_json = _json.loads(out).get("root_exists") is True
        except ValueError:
            ok_json = False
        rc2, out2 = run_cli(["--lint", "--json", "--root",
                             os.path.join(tmp, "nope"), "--book-file", book])
        ok_json2 = False
        try:
            ok_json2 = _json.loads(out2).get("root_exists") is False
        except ValueError:
            ok_json2 = False
        check("B7 --json on empty/missing root emits parsable JSON",
              ok_json and ok_json2 and rc == 0 and rc2 == 0,
              "empty=%s missing=%s" % (ok_json, ok_json2))

        # --- B8: страховка verify_yaml реально отказывает --------------------
        bad_ok, _why = M.verify_yaml(u"---\nname: x\n  bad: [unclosed\n---\nb",
                                     "x")
        no_fm_ok, _w2 = M.verify_yaml(u"no frontmatter here", "x")
        check("B8 verify_yaml refuses broken YAML and missing frontmatter",
              (not bad_ok) and (not no_fm_ok),
              "broken=%s nofm=%s" % (bad_ok, no_fm_ok))

        # --- B9: quote_if_needed защищает значения с ':' ---------------------
        q = M.quote_if_needed(u"backend widget_state: 40 urls")
        check("B9 value with ':' is quoted (frontmatter stays a mapping)",
              q.startswith('"') and q.endswith('"'), "got=%r" % q)

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
