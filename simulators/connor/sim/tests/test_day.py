"""The simulated day and the parametric lateral behind the Chapter 1 screen."""
import json

import pytest

from sim.constants import (
    CAP_BANK_KVAR_PER_NODE, DAY_INITIAL_SOC, DAY_STEPS, INVERTER_KVAR_FRACTION, RESERVE_FLOOR, STEP_MINUTES,
    TIER_NAMEPLATE_PCT, VOLT_VAR_ABSORB_START_PU, VOLT_VAR_INJECT_FULL_PU, VOLT_VAR_INJECT_START_PU,
)
from sim.devices import Battery
from sim.feeder import Feeder, four_node, lateral
from sim.profiles import load_factor, price, solar_factor
from sim.reactive import cap_bank_wanted, volt_var, volt_var_kvar
from sim.scenarios.day import base_point, build_day, day_steps


@pytest.fixture(scope="module")
def day(tmp_path_factory):
    out = tmp_path_factory.mktemp("replays") / "day.json"
    return build_day(out=out, quiet=True), out


class TestLateral:
    @pytest.mark.parametrize("n", [1, 2, 6])
    def test_any_city_size_builds_and_solves(self, n):
        f = Feeder(lateral(n))
        assert len(f.transformers) == n and len(f.homes) == n
        assert f.topology.capacitor["kvar"] == pytest.approx(CAP_BANK_KVAR_PER_NODE * n)
        f.load(1.0)
        f.pv(0.0)
        f.battery({})
        s = f.solve()
        assert s["voltageViolations"] == 0 and s["overNameplate"] == 0
        assert len(s["tfVoltage"]) == n

    def test_four_node_is_the_four_node_lateral(self):
        a, b = four_node(), lateral(4)
        assert a.commands == b.commands and a.name == "four-node"
        assert [h.distance_km for h in a.homes] == [h.distance_km for h in b.homes]

    def test_far_node_keeps_the_long_drop_at_any_size(self):
        for n in (2, 6):
            t = lateral(n)
            assert t.edges[-1]["id"] == f"svc{n}"
            assert t.homes[-1].distance_km - t.transformers[-1].coordinates[0] == pytest.approx(0.09, abs=1e-6)

    def test_solar_backfeeds_and_capacitor_supplies_vars(self):
        f = Feeder(four_node())
        f.load(0.5)
        f.pv(1.0)
        f.battery({})
        s = f.solve()
        assert s["feederKW"] < 0 and s["solarKW"] == pytest.approx(4 * 7.5)
        q_open = s["feederKVAr"]
        f.capacitor(True)
        s = f.solve()
        assert s["capKVAr"] == pytest.approx(6.0) and s["feederKVAr"] < q_open

    def test_inverter_kvar_reaches_the_feeder_head(self):
        f = Feeder(four_node())
        f.load(1.0)
        f.pv(0.0)
        f.battery({})
        q0 = f.solve()["feederKVAr"]
        f.inverter_kvar = {"h4": 5.0}
        f.battery({})
        s = f.solve()
        assert s["inverterKVAr"] == pytest.approx(5.0)
        assert s["feederKVAr"] == pytest.approx(q0 - 5.0, abs=0.2)


class TestProfiles:
    def test_shapes_are_bounded_and_dark_at_night(self):
        factors = [load_factor(m / 60) for m in range(0, 24 * 60, STEP_MINUTES)]
        assert max(factors) == pytest.approx(1.0) and min(factors) > 0.2
        assert solar_factor(0.0) == 0.0 and solar_factor(23.0) == 0.0
        assert 0.9 < solar_factor(13.3) <= 1.0
        assert price(17.5) > price(2.0)

    def test_base_point_branches(self):
        fleet = 80.0
        assert base_point(145.0, 30.0, 0.0, fleet) == (-fleet * 0.35, "peak discharge")
        assert base_point(12.0, 12.0, 27.0, fleet) == (15.0, "solar soak")
        assert base_point(18.0, 9.0, 0.0, fleet) == (fleet * 0.05, "cheap charge")
        assert base_point(40.0, 12.0, 0.0, fleet) == (0.0, "idle")

    def test_volt_var_follows_the_1547_curve(self):
        assert volt_var_kvar(1.0, 8.8) == 0.0
        assert volt_var_kvar(VOLT_VAR_INJECT_FULL_PU - 0.05, 8.8) == pytest.approx(8.8)
        mid = (VOLT_VAR_INJECT_START_PU + VOLT_VAR_INJECT_FULL_PU) / 2
        assert volt_var_kvar(mid, 8.8) == pytest.approx(4.4)
        assert volt_var_kvar(VOLT_VAR_ABSORB_START_PU + 0.03, 8.8) == pytest.approx(-4.4)

    def test_volt_var_skips_islanded_units(self):
        f = Feeder(four_node())
        devices = {h.id: Battery(0.5) for h in f.homes}
        f.islanded.add("h4")
        q = volt_var(f, devices, {"voltage": [0.95, 1.0, 1.0, 0.95]})
        assert q["h1"] > 0 and "h4" not in q and q["h1"] <= INVERTER_KVAR_FRACTION * 20

    def test_cap_bank_has_hysteresis(self):
        f = Feeder(four_node())
        assert cap_bank_wanted(f, {"feederKVAr": 8.0, "capKVAr": 0.0}) is True
        f.cap_on = True
        assert cap_bank_wanted(f, {"feederKVAr": 5.5, "capKVAr": 0.0}) is True  # between thresholds: hold
        assert cap_bank_wanted(f, {"feederKVAr": 3.0, "capKVAr": 0.0}) is False


class TestDay:
    def test_a_full_day_of_five_minute_steps(self, day):
        replay, _ = day
        for frames in replay["runs"].values():
            assert len(frames) == DAY_STEPS == 288
            assert frames[0]["clock"] == "00:00" and frames[-1]["clock"] == "23:55"
            for v in frames[0]["soc"].values():  # one step after the initial state
                assert v == pytest.approx(DAY_INITIAL_SOC, abs=0.02)
        assert replay["schedule"] is None and replay["steps"] == 288 and replay["startMinute"] == 0
        assert len(day_steps(four_node())) == 288

    def test_reserve_holds_and_referee_is_clean(self, day):
        replay, _ = day
        for policy, s in replay["summary"].items():
            assert s["minSoc"] >= RESERVE_FLOOR
            assert s["stepsOverNameplate"] == 0 and s["voltageViolationSteps"] == 0, policy

    def test_the_day_reads_like_the_story(self, day):
        replay, _ = day
        frames = replay["runs"]["naive"]
        at = {f["clock"]: f for f in frames}
        fleet = lambda f: sum(f["soc"].values()) / len(f["soc"])
        assert fleet(at["06:00"]) > fleet(at["00:00"])  # slow overnight top-up
        assert at["03:00"]["phase"] == "cheap charge"
        assert at["12:00"]["phase"] == "solar soak" and at["12:00"]["solarKW"] > at["12:00"]["loadKW"]
        assert fleet(at["15:00"]) > 0.9  # soaked
        assert at["18:00"]["phase"] == "peak discharge" and at["18:00"]["fleetKW"] < 0
        assert fleet(at["21:00"]) == pytest.approx(RESERVE_FLOOR, abs=0.02)
        assert at["00:00"]["solarKW"] == 0.0 and at["23:00"]["solarKW"] == 0.0

    def test_reactive_fields_are_live(self, day):
        replay, _ = day
        frames = replay["runs"]["aware"]
        keys = {"feederKVAr", "capKVAr", "inverterKVAr", "inverterKVArCapacity", "inverterKVArReserve", "capOn",
                "tfVoltage", "loadKW", "solarKW", "fleetKW", "hour", "solarFactor"}
        assert keys <= frames[0].keys()
        closed = [f["clock"] for f in frames if f["capOn"]]
        assert closed and closed[0] != "00:00" and not frames[-1]["capOn"]  # closes in the evening, opens again
        assert any(f["inverterKVAr"] != 0 for f in frames)
        assert all(0 <= f["inverterKVArReserve"] <= f["inverterKVArCapacity"] for f in frames)

    def test_aware_pins_the_far_node_under_the_export_ceiling(self, day):
        replay, _ = day
        s = replay["summary"]["aware"]
        assert s["maxVoltagePu"] < 1.05 and s["maxVoltagePu"] > 1.045

    def test_a_bigger_city_runs_the_same_day(self, tmp_path):
        replay = build_day(6, ("aware",), out=tmp_path / "day6.json", quiet=True)
        frames = replay["runs"]["aware"]
        assert replay["topology"]["nodes"] == 6 and len(frames) == 288 and len(frames[0]["loading"]) == 6
        assert replay["summary"]["aware"]["minSoc"] >= RESERVE_FLOOR
        assert replay["summary"]["aware"]["stepsOverNameplate"] == 0

    def test_replay_round_trips(self, day):
        replay, out = day
        loaded = json.loads(out.read_text())
        assert loaded["name"] == "day" and loaded["provenance"]["controller"].startswith("base_point()")
        assert loaded["assumptions"]["capacitor"]["kvar"] == 6.0
