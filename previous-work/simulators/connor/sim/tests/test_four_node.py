"""Mechanics checks on the four-node feeder: physics, devices, comms loss, tiers, replay."""
import json

import pytest

from sim.constants import (
    BACKUP_SOC_FLOOR, COMMS_LOSS_POWER_KW, CORE_POWER_KW, RESERVE_FLOOR, STEP_MINUTES, SUSTAINED_WINDOW_MINUTES,
    TIER_NAMEPLATE_PCT, TIER_NORMAL_PCT, VOLTAGE_MAX_PU, VOLTAGE_MIN_PU,
)
from sim.devices import Battery
from sim.feeder import Feeder, four_node, tier
from sim.scenarios.four_node import DEFAULT_SCHEDULE, build, expand, run


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    out = tmp_path_factory.mktemp("replays") / "four_node.json"
    return build(out=out, quiet=True), out


class TestFeeder:
    def test_topology_shape(self):
        f = Feeder(four_node())
        assert [h.id for h in f.homes] == ["h1", "h2", "h3", "h4"]
        assert [t.kva for t in f.transformers] == [25.0] * 4
        assert f.homes[3].distance_km > f.homes[0].distance_km

    def test_idle_feeder_is_inside_limits(self):
        f = Feeder(four_node())
        f.load(1.0)
        f.battery({})
        s = f.solve()
        assert s["voltageViolations"] == 0 and s["overNameplate"] == 0
        assert 25 < s["maxLoading"] < 40  # ~7.5 kW at 0.95 pf on 25 kVA
        assert all(t == "ok" for t in s["tier"])

    def test_full_charge_exceeds_normal_tier_on_every_transformer(self):
        f = Feeder(four_node())
        f.load(1.0)
        f.battery({h.id: CORE_POWER_KW for h in f.homes})
        s = f.solve()
        assert s["overNormal"] == 4
        assert s["overEmergency"] == 0
        assert s["voltage"][3] == min(s["voltage"])  # far node sags most

    def test_full_export_breaks_voltage_at_far_node_only(self):
        f = Feeder(four_node())
        f.load(1.0)
        f.battery({h.id: -CORE_POWER_KW for h in f.homes})
        s = f.solve()
        assert s["voltageViolations"] == 1
        assert s["voltageMax"][3] > VOLTAGE_MAX_PU
        assert s["overNameplate"] == 0

    def test_battery_draws_no_reactive_power(self):
        from opendssdirect import dss
        f = Feeder(four_node())
        f.load(1.0)
        f.battery({"h1": 10.0})
        f.solve()
        dss.Circuit.SetActiveElement("Load.bat_h1")
        p, q = dss.CktElement.Powers()[:2]
        assert p == pytest.approx(10.0, abs=1e-3)
        assert q == pytest.approx(0.0, abs=1e-3)

    def test_tier_boundaries(self):
        assert tier(100.0) == "ok"
        assert tier(100.01) == "over_nameplate"
        assert tier(110.01) == "normal_exceeded"
        assert tier(150.01) == "emergency"

    def test_sustained_window_needs_the_full_thirty_minutes(self):
        f = Feeder(four_node())
        f.load(1.0)
        f.battery({h.id: CORE_POWER_KW for h in f.homes})
        steps_needed = SUSTAINED_WINDOW_MINUTES // STEP_MINUTES
        for i in range(steps_needed):
            s = f.solve(track_thermal=True)
            assert (s["sustainedViolations"] == list(range(4))) == (i == steps_needed - 1)
        f.battery({})
        assert f.solve(track_thermal=True)["sustainedViolations"] == []


class TestDevices:
    def test_reserve_floor_and_full_charge(self):
        b = Battery(0.21)
        for _ in range(12):
            b.advance(-20)
        assert b.soc == pytest.approx(RESERVE_FLOOR)
        assert b.limit(-20) == 0
        for _ in range(100):
            b.advance(20)
        assert b.soc == pytest.approx(1.0)
        assert b.limit(20) == 0

    def test_round_trip_loses_energy(self):
        b = Battery(0.5)
        b.advance(10)
        b.advance(-10)
        assert b.soc < 0.5

    def test_comms_lost_holds_power_and_soc(self):
        b = Battery(0.5)
        b.lose_comms()
        assert b.limit(20) == COMMS_LOSS_POWER_KW
        assert b.advance(20) == COMMS_LOSS_POWER_KW
        assert b.soc == 0.5 and b.state == "COMMS_LOST"
        b.restore()
        assert b.online


class TestScenario:
    def test_schedule_length(self):
        assert len(expand(DEFAULT_SCHEDULE)) == 24

    def test_offline_unit_delivers_nothing_and_others_carry_on(self, replay):
        frames = replay[0]["runs"]["aware"]
        for f in frames[8:12]:
            assert f["state"]["h3"] == "COMMS_LOST"
            assert f["powers"]["h3"] == COMMS_LOSS_POWER_KW
            assert f["soc"]["h3"] == frames[7]["soc"]["h3"]
            assert "h3" not in f["online"]
            assert f["powers"]["h1"] > 0 and f["powers"]["h2"] > 0
        assert "COMMS_LOST" in frames[8]["events"][0]
        assert frames[12]["state"]["h3"] != "COMMS_LOST"
        assert frames[12]["powers"]["h3"] > 0  # rejoins the charge on the restore step
        assert frames[8]["shortfallKW"] > frames[7]["shortfallKW"]

    def test_soc_rises_on_charge_and_falls_on_discharge(self, replay):
        frames = replay[0]["runs"]["aware"]
        assert all(frames[13]["soc"][u] > frames[3]["soc"][u] for u in ("h1", "h2", "h4"))
        assert all(frames[23]["soc"][u] < frames[15]["soc"][u] for u in frames[0]["soc"])

    def test_reserve_floor_holds_everywhere(self, replay):
        for frames in replay[0]["runs"].values():
            assert all(f["minSoc"] >= RESERVE_FLOOR for f in frames)
            assert all(abs(p) <= CORE_POWER_KW + 1e-6 for f in frames for p in f["powers"].values())

    def test_aware_never_exceeds_nameplate_or_voltage(self, replay):
        for f in replay[0]["runs"]["aware"]:
            assert f["overNameplate"] == 0, f["step"]
            assert f["voltageViolations"] == 0, f["step"]
            assert VOLTAGE_MIN_PU <= f["minVoltage"] and f["maxVoltage"] <= VOLTAGE_MAX_PU
        assert replay[0]["summary"]["aware"]["shortfallKWh"] > 0  # position given up, reported

    def test_naive_breaches_the_normal_tier_for_thirty_minutes(self, replay):
        frames = replay[0]["runs"]["naive"]
        assert max(f["maxLoading"] for f in frames) > TIER_NORMAL_PCT
        assert any(f["sustainedViolations"] for f in frames)
        assert all(not f["emergencyViolations"] for f in frames)

    def test_headroom_is_published_each_step(self, replay):
        f = replay[0]["runs"]["aware"][0]
        assert set(f["headroomUpKW"]) == {"tf1", "tf2", "tf3", "tf4"}
        assert all(0 < v < TIER_NAMEPLATE_PCT / 100 * 25 for v in f["headroomUpKW"].values())

    def test_replay_file_round_trips(self, replay):
        data = json.loads(replay[1].read_text())
        assert set(data["runs"]) == {"aware", "naive"}
        assert len(data["runs"]["aware"]) == 24
        assert len(data["topology"]["homes"]) == 4
        assert data["provenance"]["referee"].startswith("OpenDSS")

    def test_no_offline_event_is_a_clean_run(self):
        frames = run("aware", offline=None)
        assert all(len(f["online"]) == 4 for f in frames)
        assert all(not f["events"] for f in frames)


@pytest.fixture(scope="module")
def frames():
    return run("aware", offline=None, backup="h4", backup_at=4, reconnect_at=16)


class TestBackupIslanding:
    def test_device_serves_home_down_to_backup_floor(self):
        b = Battery(0.30)
        b.island()
        assert not b.online and b.limit(20) == 0
        served = b.serve_backup(7.5)
        assert served == pytest.approx(-7.5)
        assert b.soc < 0.30
        for _ in range(200):
            b.serve_backup(7.5)
        assert b.soc == pytest.approx(BACKUP_SOC_FLOOR)
        assert b.serve_backup(7.5) == 0.0  # empty: the home browns out, nothing is invented
        b.reconnect()
        assert b.online

    def test_islanded_home_disappears_from_the_feeder(self, frames):
        for f in frames[4:16]:
            assert f["state"]["h4"] == "BACKUP_ISLANDED"
            assert f["islanded"] == ["h4"]
            assert f["powers"]["h4"] == 0.0  # nothing crosses the service point
            assert f["homeServedKW"]["h4"] == pytest.approx(-7.5)
            assert f["loading"][3] == pytest.approx(0.0, abs=0.05)  # tf4 sees no load at all
            assert f["voltageViolations"] == 0
        assert "BACKUP_ISLANDED" in frames[4]["events"][0]

    def test_soc_falls_by_the_home_load_while_islanded(self, frames):
        # 12 steps of 7.5 kW = 7.5 kWh out of 37 kWh usable, plus discharge losses.
        drop = frames[3]["soc"]["h4"] - frames[15]["soc"]["h4"]
        assert 7.5 / 37 < drop < 7.5 / 37 / 0.9

    def test_other_units_keep_the_base_point_going(self, frames):
        for f in frames[4:14]:
            assert all(f["powers"][u] > 0 for u in ("h1", "h2", "h3"))
            assert f["shortfallKW"] > 0  # h4's share is reported as position given up

    def test_reconnect_restores_load_and_dispatch(self, frames):
        f = frames[16]
        assert f["state"]["h4"] != "BACKUP_ISLANDED" and f["islanded"] == []
        assert f["loading"][3] > 30  # tf4 carries the home again
        assert f["powers"]["h4"] < 0  # and h4 joins the discharge order
        assert "reconnected" in f["events"][0]
        assert all(x["minSoc"] >= 0.2 for x in frames)  # grid-connected reserve never breached
