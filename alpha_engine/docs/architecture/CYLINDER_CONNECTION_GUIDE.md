# Cylinder Connection Guide

A cylinder builder starts in `WORKSTREAM_MODE: PLUGIN` and receives this repository plus the frozen PDK/contract. It owns only its plugin directory, fixtures/tests, namespaced persistence if explicitly approved, manifest, and declared UI/CLI contributions.

The normal connection points are:
1. provider adapter registrations;
2. normalizers returning `ObservationCandidate`;
3. signal detectors returning `SignalCandidate`;
4. opportunity detectors returning `OpportunityCandidate`;
5. scoring feature providers returning named canonical features;
6. future paper action/instrument translators;
7. outcome evaluators;
8. declarative dashboard/CLI contribution descriptors.

The plugin never writes core records directly. If the core contract is insufficient, create a Core Compatibility Request.
