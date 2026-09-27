"""Deliverable D on the root feeder: the covert channel and an honest detector (milestone M6').

    attack.py    Carrier (the fictional adversary's hidden schedule) and CompromisedDevice
    detector.py  PeerDetector: residual size and oscillation, corroborated by the home's own AMI voltage at the
                 carrier frequency. It builds the peer sets docs/design.md §5.6 asks for and records each unit's
                 amplitude against its peers' at the flag, but does not gate on it: measured on this feeder, that
                 baseline is blind to this attack (detector.py's docstring, resilience/docs/measurements.md §B3).
    build.py     python -m resilience.detect.build [--quick | --fixture]: resilience/out/p3/covert.json

The adversary is fictional. Detection reads what a field system has (telemetry, setpoints, AMI voltages at the
homes), never the legitimate-command solve the prototype compared against.
"""
