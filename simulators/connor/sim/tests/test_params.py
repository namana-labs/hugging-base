"""Params: every knob is listed, coerced, bounded, and actually changes the run."""
import pytest

from sim.constants import RESERVE_FLOOR
from sim.params import Params, markdown_table, schema
from sim.scenarios.day import build_day
from sim.scenarios.four_node import build_mechanics
from sim.server import run_request


class TestParams:
    def test_schema_lists_every_field_with_label_group_and_tag(self):
        rows = schema()
        assert {r["name"] for r in rows} == set(Params().to_json())
        assert all(r["label"] and r["group"] and r["tag"] in ("SOURCED", "DERIVED", "ASSUMPTION", "UNVERIFIED") for r in rows)
        assert "| `nodes` |" in markdown_table()

    def test_overrides_are_coerced_and_validated(self):
        p = Params.from_overrides({"nodes": "6", "node_load_kw": "12", "initial_soc": "", "offline_unit": "h2",
                                   "price_by_hour": ",".join(["10"] * 24)})
        assert p.nodes == 6 and p.node_load_kw == 12.0 and p.initial_soc is None and p.offline_unit == "h2"
        assert p.price_by_hour == tuple([10.0] * 24)
        with pytest.raises(KeyError):
            Params.from_overrides({"not_a_knob": 1})
        with pytest.raises(ValueError):
            Params.from_overrides({"nodes": 40})
        with pytest.raises(ValueError):
            Params.from_overrides({"price_by_hour": [1, 2, 3]})

    def test_defaults_reproduce_the_shipped_replays(self):
        assert build_day(out=None, quiet=True)["summary"]["naive"]["peakLoadingPct"] == pytest.approx(23.37, abs=0.05)
        m = build_mechanics(Params.from_overrides({"offline_unit": "h3"}), out=None)
        assert m["summary"]["naive"]["sustainedViolationSteps"] == 5

    def test_knobs_change_the_physics(self):
        base = build_day(out=None, quiet=True)["summary"]["naive"]
        hot = build_day(out=None, quiet=True, params=Params.from_overrides({"peak_load_factor": 3}))["summary"]["naive"]
        assert hot["peakLoadingPct"] > 3 * base["peakLoadingPct"] * 0.9
        no_solar = build_day(out=None, quiet=True, params=Params.from_overrides({"pv_kw_per_node": 0}))["runs"]["naive"]
        assert all(f["solarKW"] == 0 for f in no_solar) and not any(f["phase"] == "solar soak" for f in no_solar)
        no_var = build_day(out=None, quiet=True, params=Params.from_overrides({"inverter_kvar_fraction": 0}))["runs"]["naive"]
        assert all(f["inverterKVAr"] == 0 for f in no_var)
        wide = build_mechanics(Params.from_overrides({"offline_unit": "h3", "sustained_window_minutes": 10}), out=None)
        assert wide["summary"]["naive"]["sustainedViolationSteps"] > 5

    def test_reserve_floor_knob_is_honoured(self):
        r = build_day(out=None, quiet=True, params=Params.from_overrides({"reserve_floor": 0.3}))
        assert r["summary"]["naive"]["minSoc"] >= 0.3 > RESERVE_FLOOR
        assert r["params"]["reserve_floor"] == 0.3


class TestServer:
    def test_run_request_builds_both_scenarios(self):
        day = run_request({"scenario": "day", "params": {"nodes": 2}, "policies": ["aware"]})
        assert day["name"] == "day" and list(day["runs"]) == ["aware"] and day["topology"]["nodes"] == 2
        mech = run_request({"scenario": "mechanics", "params": {"backup_unit": "h4"}})
        assert mech["name"] == "four_node" and mech["steps"] == 24 and any(f["islanded"] for f in mech["runs"]["aware"])

    def test_run_request_rejects_bad_input(self):
        with pytest.raises(ValueError):
            run_request({"scenario": "storm"})
        with pytest.raises(ValueError):
            run_request({"policies": ["clever"]})
        with pytest.raises(KeyError):
            run_request({"params": {"bogus": 1}})
