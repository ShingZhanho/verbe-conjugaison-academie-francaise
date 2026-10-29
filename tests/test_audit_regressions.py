"""Source-shaped regressions for the v0.4.0 manual-audit findings."""
import unittest
from bs4 import BeautifulSoup

from verbe_af.parser import (
    _participle_forms, _parse_active_passe, _parse_imperative_rows,
    parse_conjugation_table, _restore_missing_singular_participles,
)
from verbe_af.transformer import transform_verb, create_reformed_entry
from verbe_af.cache import merge_homonyms


def cell(text):
    return BeautifulSoup(f'<td class="conj_verb">{text}</td>', 'html.parser').td


class AuditRegressions(unittest.TestCase):
    def test_lexical_alternatives_preserve_grammatical_circumflexes(self):
        raw = {"h_aspire": False, "_circumflex_alternatives": True,
               "voix_active_avoir": {"indicatif": {"passe_simple": {
                   "nous": "abîmâmes", "il": "eût abîmé"}},
                   "participe": {"passe": {"simple": {"sm": "abîmé"}}}}}
        result = transform_verb("abîmer", raw)
        tense = result["voix_active_avoir"]["indicatif"]["passe_simple"]
        self.assertEqual(tense["1pm;1pf"], "abîmâmes;abimâmes")
        self.assertEqual(tense["3sm"], "eût abîmé;eût abimé")
        self.assertNotIn("_circumflex_alternatives", result)
        name, reformed = create_reformed_entry("abîmer", result)
        self.assertEqual(name, "abimer")
        self.assertEqual(reformed["voix_active_avoir"]["participe"]["passe"]["sm"],
                         "abimé;abîmé")
        raw["_circumflex_alternatives"] = False
        self.assertEqual(transform_verb("abîmer", raw)["voix_active_avoir"]
                         ["indicatif"]["passe_simple"]["1pm;1pf"], "abîmâmes")

    def test_participle_alternatives_repeat_complete_prefix(self):
        td = cell('étant absous<span class="or"> ou </span>'
                  '<span class="forme_rectif">absout</span>, absoute, '
                  'absous<span class="or"> ou </span>'
                  '<span class="forme_rectif">absouts</span>, absoutes')
        self.assertEqual(_participle_forms(td, compound=True), {
            "sm": "étant absous;étant absout", "sf": "étant absoute",
            "pm": "étant absous;étant absouts", "pf": "étant absoutes"})
        self.assertEqual(_participle_forms(cell('ayant mû ou mu'), compound=True)["sf"],
                         "ayant mû;ayant mu")

    def test_partial_lists_do_not_invent_singular_forms(self):
        for prefix in ("étant", "ayant été", "s’étant"):
            self.assertEqual(_participle_forms(cell(f"{prefix} dus, dues"), compound=True),
                             {"pm": f"{prefix} dus", "pf": f"{prefix} dues"})

    def test_singular_corrections_are_limited_to_confirmed_families(self):
        for verb, masculine, feminine, plural, feminine_plural in (
            ("croître", "crû", "crue", "crus", "crues"),
            ("recroître", "recrû", "recrue", "recrus", "recrues"),
            ("devoir", "dû", "due", "dus", "dues"),
            ("redevoir", "redû", "redue", "redus", "redues"),
        ):
            voice = "voix_active_etre" if "croître" in verb else "voix_passive"
            forms = {"pm": f"étant {plural}", "pf": f"étant {feminine_plural}"}
            data = {voice: {"participe": {"passe": {"compound": forms}}}}
            if voice == "voix_passive":
                data[voice]["participe"]["present"] = forms
            _restore_missing_singular_participles(verb, data)
            self.assertEqual(forms["sm"], f"étant {masculine}")
            self.assertEqual(forms["sf"], f"étant {feminine}")
            # Already complete lists must be preserved, including source changes.
            forms["sm"] = "explicit source singular"
            _restore_missing_singular_participles(verb, data)
            self.assertEqual(forms["sm"], "explicit source singular")
        forms = {"pm": "étant dus", "pf": "étant dues"}
        data = {"voix_passive": {"participe": {"present": forms}}}
        _restore_missing_singular_participles("autre", data)
        self.assertEqual(set(forms), {"pm", "pf"})

    def test_invariant_simple_without_compound(self):
        soup = BeautifulSoup('<tr><td class="conj_verb">entre-nui (invariable)</td></tr>',
                             'html.parser')
        raw = {"passe": _parse_active_passe(soup.find_all("tr"))}
        result = transform_verb("entre-nuire", {"voix_prono": {"participe": raw}})
        self.assertEqual(result["voix_prono"]["participe"]["passe"],
                         dict.fromkeys(("sm", "sf", "pm", "pf"), "entre-nui"))

    def test_prefixed_imperative_reform_is_masculine_only(self):
        soup = BeautifulSoup('<tr><td class="conj_auxil">sois</td>'
                             '<td class="conj_verb">mû<span class="or"> ou </span>'
                             '<span class="forme_rectif">mu</span>, mue</td></tr>',
                             'html.parser')
        result = _parse_imperative_rows(soup.find_all("tr"))
        self.assertEqual(result["tu_m"], "sois mû,sois mu")
        self.assertEqual(result["tu_f"], "sois mue")

    def test_homonym_references_follow_merge_and_renumber(self):
        def entry(variant, form):
            return {"h_aspire": False, "rectification_1990": True,
                    "rectification_1990_variante": variant,
                    "voix_active_avoir": {"indicatif": {"present": {"3sm": form}}}}
        data = {"giter_1": entry("gîter_1", "gîte"),
                "giter_2": entry("gîter_2", "gîte"),
                "gîter_1": entry("giter_1", "gîte"),
                "gîter_2": entry("giter_2", "gîte")}
        merged = merge_homonyms(data)
        self.assertEqual(merged["giter"]["rectification_1990_variante"], "gîter")
        self.assertEqual(merged["gîter"]["rectification_1990_variante"], "giter")
        self.assertEqual(data["giter_1"]["rectification_1990_variante"], "gîter_1")
        data["giter_3"] = entry("gîter_3", "autre")
        data["gîter_3"] = entry("giter_3", "autre")
        merged = merge_homonyms(data)
        self.assertEqual(merged["giter_2"]["rectification_1990_variante"], "gîter_2")

    def test_explicit_disjunction_and_narrow_source_correction(self):
        root = BeautifulSoup('<div><p>H aspiré</p><div id="voix_prono"></div></div>',
                             'html.parser').div
        for verb in ("ululer", "yoyoter", "hacher"):
            parsed = parse_conjugation_table(root, verb)[verb]
            self.assertEqual(parsed["h_aspire"], verb == "hacher")
            self.assertTrue(transform_verb(verb, parsed)["bloque_elision_liaison"])
        self.assertIsNone(parse_conjugation_table(root, "suraller"))
        self.assertIsNone(parse_conjugation_table(root, "sur-aller"))
        root = BeautifulSoup('<div><div id="voix_prono"><td class="conj_verb">'
                             'allons <span class="or">ou</span> sur-aller</td></div></div>',
                             'html.parser').div
        parse_conjugation_table(root, "aller")
        self.assertEqual(root.td.text, "allons")


if __name__ == "__main__":
    unittest.main()
