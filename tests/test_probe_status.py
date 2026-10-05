"""Execute the generated browser probe against bounded, synthetic responses."""

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from szl_vertical_forge.forge import load_verticals, render_vertical  # noqa: E402

SOURCE = "https://szlholdings-a11oy.hf.space/api/a11oy/v1/vert/realestate/feed"
COUNSEL_SOURCE = "https://szlholdings-a11oy.hf.space/api/a11oy/v1/vert/legal/feed"
FINANCE_SOURCE = "https://szlholdings-a11oy.hf.space/api/a11oy/v1/finance/overview"
NODE = r"""
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const pill={textContent:'PROBING',className:'pill'};
const detail={textContent:'waiting'};
const response={ok:input.http>=200&&input.http<300,status:input.http,
  headers:{get:()=>input.mime||'application/json'},
  json:async()=>input.body,text:async()=>input.text||''};
const context={document:{getElementById:id=>id==='livepill'?pill:detail},
  fetch:async()=>response,Date,JSON,Number,String};
const script=input.script.replace(/probe\(\);\s*$/,'probe()');
(async()=>{await vm.runInNewContext(script,context);
  process.stdout.write(JSON.stringify({badge:pill.textContent,className:pill.className,detail:detail.textContent}));
})().catch(error=>{console.error(error);process.exitCode=1});
"""


def source(status="live", *, age=5, value=None):
    if value is None and status != "unavailable":
        value = {"items": [{"id": "observed-row"}]}
    import time
    return {"value": value, "freshness": {"status": status, "fetched_at": time.time() - age}}


def terra_body(**changes):
    body = {"status": "REACHABLE", "http_status": 200, "source": SOURCE,
            "data": {"vertical": "realestate", "hpd_litigations": source(),
                     "dob_violations": source(), "rates": source()}}
    body.update(changes)
    return body


@unittest.skipUnless(shutil.which("node"), "Node.js is required for generated script tests")
class ProbeStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scripts = {}
        for vertical in load_verticals():
            page = render_vertical(vertical)
            cls.scripts[vertical["id"]] = re.search(r"<script>(.*?)</script>", page, re.S).group(1)

    def probe(self, body, *, http=200, vertical="terra", mime="application/json", text=""):
        result = subprocess.run([shutil.which("node"), "-e", NODE],
            input=json.dumps({"script": self.scripts[vertical], "body": body,
                              "http": http, "mime": mime, "text": text}),
            text=True, capture_output=True, timeout=15, check=True)
        return json.loads(result.stdout)

    def test_outer_200_with_upstream_503_is_unavailable_in_badge_and_detail(self):
        body = terra_body(status="UNAVAILABLE", http_status=503, data={"detail": "upstream failed"})
        result = self.probe(body)
        self.assertEqual(result["badge"], "UNAVAILABLE")
        self.assertIn("unavailable", result["className"])
        self.assertIn("Upstream unavailable", result["detail"])
        self.assertIn('"http_status": 503', result["detail"])

    def test_valid_upstream_is_only_reachable(self):
        result = self.probe(terra_body())
        self.assertEqual(result["badge"], "REACHABLE")
        self.assertNotIn("observed", result["className"])
        self.assertIn('"vertical": "realestate"', result["detail"])

    def test_missing_and_malformed_payload_fail_closed(self):
        for body in (None, [], {}, {"status": "REACHABLE"}, terra_body(data=None),
                     terra_body(data={"vertical": "realestate"})):
            with self.subTest(body=body):
                self.assertEqual(self.probe(body)["badge"], "UNAVAILABLE")
        self.assertEqual(self.probe(None, mime="text/html", text="error")["badge"], "UNAVAILABLE")

    def test_upstream_and_outer_failures(self):
        self.assertEqual(self.probe(terra_body(http_status=503))["badge"], "UNAVAILABLE")
        self.assertEqual(self.probe(terra_body(), http=503)["badge"], "UNAVAILABLE")
        self.assertEqual(self.probe(terra_body(data={"status": "UNAVAILABLE"}))["badge"], "UNAVAILABLE")

    def test_stale_value_and_missing_observation_clock(self):
        stale = terra_body()
        stale["data"]["rates"] = source("cached", age=7200)
        self.assertEqual(self.probe(stale)["badge"], "STALE")
        old_live = terra_body()
        old_live["data"]["rates"] = source("live", age=7200)
        self.assertEqual(self.probe(old_live)["badge"], "STALE")
        unclocked = terra_body()
        unclocked["data"]["rates"]["freshness"].pop("fetched_at")
        self.assertEqual(self.probe(unclocked)["badge"], "UNAVAILABLE")

    def test_source_vertical_and_revision_mismatch(self):
        self.assertEqual(self.probe(terra_body(source="https://wrong.example/feed"))["badge"], "UNAVAILABLE")
        wrong_vertical = terra_body()
        wrong_vertical["data"]["vertical"] = "finance"
        self.assertEqual(self.probe(wrong_vertical)["badge"], "UNAVAILABLE")
        mismatch = terra_body(source_revision="a" * 40)
        mismatch["data"]["source_revision"] = "b" * 40
        self.assertEqual(self.probe(mismatch)["badge"], "UNAVAILABLE")
        unbound = terra_body(source_revision="a" * 40)
        self.assertEqual(self.probe(unbound)["badge"], "UNAVAILABLE")

    def test_partial_source_and_fixture_or_modeled_are_not_live(self):
        partial = terra_body()
        partial["data"]["rates"] = source("unavailable")
        self.assertEqual(self.probe(partial)["badge"], "PARTIAL")
        self.assertEqual(self.probe(terra_body(data_kind="SAMPLE"))["badge"], "SAMPLE")
        self.assertEqual(self.probe(terra_body(data_kind="FIXTURE"))["badge"], "SAMPLE")
        self.assertEqual(self.probe(terra_body(truth_label="MODELED"))["badge"], "MODELED")

    def test_lyte_html_is_reachability_only(self):
        result = self.probe(None, vertical="lyte", mime="text/html", text="<html>sample</html>")
        self.assertEqual(result["badge"], "REACHABLE")
        self.assertNotIn("observed", result["className"])

    def test_finance_and_counsel_use_their_existing_live_state_contract(self):
        for vertical, source_url in (("finance", FINANCE_SOURCE), ("counsel", COUNSEL_SOURCE)):
            with self.subTest(vertical=vertical):
                self.assertIn("/api/live", self.scripts[vertical])
                failed = {"status": "UNAVAILABLE", "http_status": 503,
                          "source": source_url, "data": {"error": "upstream unavailable"}}
                self.assertEqual(self.probe(failed, vertical=vertical)["badge"], "UNAVAILABLE")
                reachable = {"status": "SNAPSHOT" if vertical == "finance" else "REACHABLE", "http_status": 200,
                             "source": source_url, "data": {"state": "REPORTED", "ok": True}}
                self.assertEqual(self.probe(reachable, vertical=vertical)["badge"], "REACHABLE")
                if vertical == "finance":
                    self.assertEqual(self.probe({**reachable, "data": {"ok": False}},
                                                vertical=vertical)["badge"], "UNAVAILABLE")
                self.assertEqual(self.probe({**reachable, "source": "https://wrong.example"},
                                            vertical=vertical)["badge"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
