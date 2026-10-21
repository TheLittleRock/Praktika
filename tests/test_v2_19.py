"""
Comprehensive Automated Test Suite for Praktika v2.19.0
"""
import unittest
import pymupdf
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.version import VERSION
from app.database import get_db, init_db
from app.main import (
    app,
    normalize_latex_pdf_text,
    remove_accents,
    build_standard_export_filename,
)
from starlette.testclient import TestClient

class TestPraktikaV219(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = TestClient(app)

    def test_version(self):
        self.assertEqual(VERSION, "2.19.1")

    def test_v2_19_1_enhancements(self):
        from app.ai_service import get_candidate_models
        models = get_candidate_models()
        self.assertIn("gemini-3.6-flash", models)
        self.assertEqual(models[0], "gemini-3.6-flash")

        # Test redirect /student/{share_token} -> /v/{share_token}
        res = self.client.get("/student/test_share_token_123", follow_redirects=False)
        self.assertEqual(res.status_code, 307)
        self.assertEqual(res.headers["location"], "/v/test_share_token_123")

    def test_latex_normalization(self):
        # Raw LaTeX-extracted strings with separate accent combining characters
        raw_tex_1 = "jm´eno: Jakub Petrˇz´ılek"
        normalized_1 = normalize_latex_pdf_text(raw_tex_1)
        self.assertIn("Jakub Petržílek", normalized_1)
        self.assertIn("jméno:", normalized_1)

        raw_tex_2 = "Krouˇzek: stˇreda"
        normalized_2 = normalize_latex_pdf_text(raw_tex_2)
        self.assertEqual(normalized_2, "Kroužek: středa")

        raw_tex_3 = "´uhel, d´elka a k˚uˇn"
        normalized_3 = normalize_latex_pdf_text(raw_tex_3)
        self.assertEqual(normalized_3, "úhel, délka a kůň")

    def test_remove_accents(self):
        text = "Příliš žluťoučký kůň úpěl ďábelské ódy"
        cleaned = remove_accents(text)
        self.assertEqual(cleaned, "Prilis zlutoucky kun upel dabelske ody")

    def test_standard_export_filename(self):
        fn1 = build_standard_export_filename("FPRA1", 6, "Jakub Petržílek")
        self.assertEqual(fn1, "FPRA1_Uloha_06_Petrzilek_Jakub_opraveno.pdf")

        fn2 = build_standard_export_filename("FPRA2", 12, "Tadeáš Světlík")
        self.assertEqual(fn2, "FPRA2_Uloha_12_Svetlik_Tadeas_opraveno.pdf")

        fn3 = build_standard_export_filename("ZFM2", 3, "Karel Novák")
        self.assertEqual(fn3, "ZFM2_Uloha_03_Novak_Karel_opraveno.pdf")

        # Single name fallback
        fn4 = build_standard_export_filename("FPRA1", 1, "Novák")
        self.assertEqual(fn4, "FPRA1_Uloha_01_Novak_opraveno.pdf")

    def test_sqlite_unaccent_function(self):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT unaccent('Čeština bez háčků a čárek') as res")
        row = cur.fetchone()
        self.assertEqual(row["res"], "cestina bez hacku a carek")

        # Test querying student_name via unaccent
        cur.execute("SELECT id FROM protocols WHERE unaccent(student_name) LIKE ? LIMIT 1", ("%boril%",))
        # Query executes without sqlite operational error
        row_p = cur.fetchone()
        conn.close()

    def test_autodetect_on_sample_files(self):
        # 1. FPRA_Uloha_6 (2).pdf
        p1 = Path("FPRA_Uloha_6 (2).pdf")
        if p1.exists():
            doc = pymupdf.open(str(p1))
            text = normalize_latex_pdf_text(doc[0].get_text() if len(doc) > 0 else "")
            doc.close()
            m = re.search(r'(?:jméno|autor|student|vypracoval|jmeno)\s*[:=]\s*([^\n\r,]+)', text, re.I)
            self.assertIsNotNone(m)
            self.assertEqual(m.group(1).strip(), "Jakub Petržílek")

            # Test standard export filename
            fn = build_standard_export_filename("FPRA1", 6, m.group(1).strip())
            self.assertEqual(fn, "FPRA1_Uloha_06_Petrzilek_Jakub_opraveno.pdf")

        # 2. FPRA1_10-3.pdf
        p2 = Path("FPRA1_10-3.pdf")
        if p2.exists():
            doc = pymupdf.open(str(p2))
            text = normalize_latex_pdf_text(doc[0].get_text() if len(doc) > 0 else "")
            doc.close()
            m = re.search(r'(?:Autor(?:ka)?|Jm[ée]no)\s*[:=]?\s*\n\s*([^\n\r,]+)', text, re.I)
            self.assertIsNotNone(m)
            self.assertEqual(m.group(1).strip(), "Tadeáš Světlík")

            fn2 = build_standard_export_filename("FPRA1", 10, m.group(1).strip())
            self.assertEqual(fn2, "FPRA1_Uloha_10_Svetlik_Tadeas_opraveno.pdf")

if __name__ == "__main__":
    unittest.main()
